"""Observable NVIDIA scientific completion transport, without scientific authority.

Operational capabilities are configurable and observations are recorded separately
from advertised limits. Scientific validation lives in the ingestion service.
"""

import re
import socket
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx
from openai import APIConnectionError, APIError, APIStatusError, APITimeoutError

# A provider error names the caller's account ("Not found for account '<id>'");
# the identifier is the key owner's, so receipts never keep it.
ACCOUNT_IDENTIFIER = re.compile(r"""(\baccount\s*['"])([^'"\s]+)(['"])""", re.IGNORECASE)


def request_never_sent(error):
    """Whether a transport failure proves the request never left this machine.

    A failure to connect (name resolution, a refused connection, a TLS handshake
    that failed) happens before the request body is sent, so nothing can be billed.
    A reset, a read error or a timeout after connecting may follow a request the
    provider received and processed.
    """
    seen = set()
    while error is not None and id(error) not in seen:
        seen.add(id(error))
        name = f"{type(error).__module__}.{type(error).__name__}"
        if name in {"httpx.ConnectError", "httpcore.ConnectError"}:
            return True
        error = error.__cause__ or error.__context__
    return False


def redact_provider_text(text, key=None):
    """The provider text with the API key and any account identifier replaced."""
    if not text:
        return text
    if isinstance(key, str) and key:
        text = text.replace(key, "[REDACTED]")
    return ACCOUNT_IDENTIFIER.sub(r"\1[REDACTED]\3", text)


@dataclass(frozen=True)
class ScientificResponse:
    content: str
    finish_reason: str | None
    usage: dict | None
    metadata: dict


class ScientificTransportError(RuntimeError):
    def __init__(self, kind, *, content="", metadata=None, retry_after=None):
        super().__init__(kind)
        self.kind = kind
        self.content = content
        self.metadata = metadata or {}
        self.retry_after = retry_after


def observed_headers(response):
    headers = getattr(response, "headers", None)
    if not isinstance(headers, dict) and not type(headers).__module__.startswith("httpx"):
        return {}
    allowed = (
        "retry-after",
        "x-ratelimit-limit-requests",
        "x-ratelimit-remaining-requests",
        "x-ratelimit-reset-requests",
        "x-request-id",
        "nv-request-id",
    )
    return {name: headers.get(name) for name in allowed if isinstance(headers.get(name), str)}


@contextmanager
def stream_deadline(response, remaining, expired):
    """Interrupt a stalled SSE read even if comment heartbeats hide SDK events.

    httpx read timeouts measure inactivity, not total elapsed time. The response's
    network socket can be shut down without waiting for another parsed SSE event.
    """
    extensions = getattr(response, "extensions", {})
    network = extensions.get("network_stream") if isinstance(extensions, dict) else None
    connection = network.get_extra_info("socket") if network is not None else None

    def cancel():
        expired.set()
        if connection is not None:
            try:
                connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        if response is not None:
            try:
                response.close()
            except (OSError, RuntimeError):
                pass

    timer = threading.Timer(max(0, remaining), cancel)
    timer.daemon = True
    timer.start()
    try:
        yield
    finally:
        timer.cancel()


def complete_scientific(
    client,
    *,
    model,
    system,
    payload,
    max_tokens,
    timeout,
    stream=True,
    response_format=None,
    reasoning_budget=0,
    on_progress=None,
    images=None,
):
    """Preserve streamed prefixes and timing even when a connection fails.

    SDK retries are disabled: the caller owns observable, checkpointed recovery.
    Never persist headers containing credentials, cookies or account identifiers.
    """
    if getattr(client, "provider_identity", None) == "Anthropic":
        from nasa_fire_ai.llm.anthropic_provider import complete_scientific_anthropic

        return complete_scientific_anthropic(
            client,
            model=model,
            system=system,
            payload=payload,
            max_tokens=max_tokens,
            timeout=timeout,
            stream=stream,
            response_format=response_format,
            reasoning_budget=reasoning_budget,
            on_progress=on_progress,
            images=images,
        )
    started, first = time.monotonic(), None
    content, reasoning, finish, usage = [], 0, None, None
    served_models = set()
    expired = threading.Event()
    metadata = {
        "started_at": datetime.now(UTC).isoformat(),
        "requested_model": model,
        "stream": stream,
        "max_output_tokens": max_tokens,
        "thinking_enabled": reasoning_budget > 0,
        "reasoning_budget": reasoning_budget,
        "image_count": len(images or []),
    }
    try:
        request = {
            "model": model,
            "temperature": 0,
            "max_tokens": max_tokens,
            "response_format": response_format or {"type": "json_object"},
            "extra_body": {
                "chat_template_kwargs": {"enable_thinking": reasoning_budget > 0},
                "reasoning_budget": reasoning_budget,
            },
            "messages": [
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": payload},
                        *[{"type": "image_url", "image_url": {"url": url}} for url in images],
                    ]
                    if images
                    else payload,
                },
            ],
        }
        api = client.client.with_options(
            timeout=httpx.Timeout(timeout, connect=min(20, timeout), read=timeout),
            max_retries=0,
        ).chat.completions
        if stream:
            request.update(stream=True, stream_options={"include_usage": True})
            with (
                api.create(**request) as events,
                stream_deadline(
                    getattr(events, "response", None),
                    timeout - (time.monotonic() - started),
                    expired,
                ),
            ):
                metadata["response_headers"] = observed_headers(getattr(events, "response", None))
                for event in events:
                    if isinstance(getattr(event, "model", None), str):
                        served_models.add(event.model)
                    if time.monotonic() - started > timeout:
                        raise ScientificTransportError("deadline", content="".join(content))
                    if event.usage:
                        usage = event.usage.model_dump()
                    if not event.choices:
                        continue
                    choice = event.choices[0]
                    text = choice.delta.content
                    if text:
                        first = first or time.monotonic()
                        content.append(text)
                    thought = getattr(choice.delta, "reasoning_content", None) or getattr(
                        choice.delta, "reasoning", None
                    )
                    if thought:
                        reasoning += len(thought)
                    if choice.finish_reason:
                        finish = choice.finish_reason
                    if on_progress:
                        on_progress(
                            "".join(content), {**metadata, "finish_reason": finish, "usage": usage}
                        )
                if expired.is_set():
                    raise ScientificTransportError("deadline", content="".join(content))
        else:
            response = api.create(**request)
            if isinstance(getattr(response, "model", None), str):
                served_models.add(response.model)
            message = response.choices[0].message
            content = [message.content or ""]
            thought = getattr(message, "reasoning_content", None) or getattr(
                message, "reasoning", None
            )
            reasoning = len(thought) if isinstance(thought, str) else 0
            finish = response.choices[0].finish_reason
            usage = response.usage.model_dump() if response.usage else None
        metadata.update(
            duration_seconds=time.monotonic() - started,
            time_to_first_token_seconds=first - started if first else None,
            served_models=sorted(served_models),
            reasoning_characters=reasoning,
        )
        return ScientificResponse("".join(content), finish, usage, metadata)
    except (Exception, KeyboardInterrupt) as error:
        if expired.is_set():
            kind, retry_after = "deadline", None
        elif isinstance(error, KeyboardInterrupt):
            kind, retry_after = "interrupted", None
        elif isinstance(error, ScientificTransportError):
            kind, retry_after = error.kind, error.retry_after
        elif isinstance(error, APIStatusError):
            code = error.status_code
            kind = (
                "rate_limit"
                if code == 429
                else "transient_server"
                if code >= 500
                else "access_denied"
                if code in {401, 402, 403}
                else "request_rejected"
            )
            metadata["http_status"] = code
            retry_after = error.response.headers.get("retry-after")
            body = str(error.body) if error.body else ""
            body = redact_provider_text(body, getattr(client.client, "api_key", None))
            metadata["provider_message"] = body[:1600] or None
        elif isinstance(error, APIError) and not isinstance(
            error, (APIConnectionError, APITimeoutError)
        ):
            kind, retry_after = "provider_stream_error", None
            body = str(error.body or error.message)
            body = redact_provider_text(body, getattr(client.client, "api_key", None))
            metadata["provider_message"] = body[:1600]
        else:
            if not isinstance(
                error, (APITimeoutError, APIConnectionError, httpx.TransportError)
            ) and not type(error).__module__.startswith(("httpx", "httpcore")):
                raise
            kind, retry_after = (
                (
                    "timeout"
                    if isinstance(error, (APITimeoutError, httpx.TimeoutException))
                    or "Timeout" in type(error).__name__
                    else "network"
                ),
                None,
            )
            if kind == "network" and request_never_sent(error):
                metadata["request_not_sent"] = True
        metadata.update(
            duration_seconds=time.monotonic() - started,
            served_models=sorted(served_models),
            reasoning_characters=reasoning,
            usage=usage,
            finish_reason=finish,
        )
        if on_progress:
            on_progress("".join(content), {**metadata, "error_type": kind})
        raise ScientificTransportError(
            kind, content="".join(content), metadata=metadata, retry_after=retry_after
        ) from None
