"""Observable Anthropic scientific completion transport, without scientific authority.

Chosen only by SCIENCE_PROVIDER=anthropic; NVIDIA stays the default. It returns the
same ScientificResponse / ScientificTransportError as the NVIDIA transport, so the
ingestion service validates its output exactly as before.
"""

import copy
import json
import os
import re
import threading
import time
from datetime import UTC, datetime

import anthropic

from nasa_fire_ai.llm.interfaces import NotConfigured
from nasa_fire_ai.llm.scientific_provider import (
    ScientificResponse,
    ScientificTransportError,
    redact_provider_text,
    request_never_sent,
)

# Adaptive thinking spends output tokens before the JSON, so the stage's own
# output capacity is a floor, not the request's max_tokens.
# Configurable: the largest Sonnet output seen was 9,463 tokens with thinking, and
# below the stage capacity the truncation ladder (doubling max_tokens) can work.
MIN_MAX_TOKENS = int(os.getenv("ANTHROPIC_SCIENCE_MIN_MAX_TOKENS", "32768"))
FINISH = {"end_turn": "stop", "stop_sequence": "stop", "max_tokens": "length"}
# Constraints structured outputs does not accept; the service validates them itself.
UNSUPPORTED_SCHEMA_KEYS = {
    "minLength",
    "maxLength",
    "minimum",
    "maximum",
    "exclusiveMinimum",
    "exclusiveMaximum",
    "multipleOf",
    "minItems",
    "maxItems",
    "uniqueItems",
    "pattern",
    "default",
}


class AnthropicScientificClient:
    """Anthropic Messages client for scientific stages; it has no scientific authority."""

    provider_identity = "Anthropic"
    supports_streaming = True

    def __init__(self, api_key, model, effort="high", refusal_fallback=True):
        if not api_key:
            raise NotConfigured("ANTHROPIC_API_KEY is not configured")
        self.client = anthropic.Anthropic(api_key=api_key, max_retries=0)
        self.model_identity = model
        self.effort = effort
        # A safety decline is re-run by the API on the model it routes to; the
        # served model is recorded on every attempt.
        self.refusal_fallback = refusal_fallback


def structured_schema(schema):
    """The schema without the constraints structured outputs rejects."""

    def clean(node):
        if isinstance(node, dict):
            out = {k: clean(v) for k, v in node.items() if k not in UNSUPPORTED_SCHEMA_KEYS}
            if out.get("type") == "object" or "properties" in out:
                out["additionalProperties"] = False
            return out
        if isinstance(node, list):
            return [clean(v) for v in node]
        return node

    return clean(copy.deepcopy(schema))


def output_format(response_format):
    if not response_format or response_format.get("type") != "json_schema":
        return None
    definition = response_format.get("json_schema") or {}
    schema = definition.get("schema") or response_format.get("schema")
    return {"type": "json_schema", "schema": structured_schema(schema)} if schema else None


def image_block(url):
    match = re.match(r"data:(image/[\w.+-]+);base64,(.*)$", url, re.DOTALL)
    if match:
        source = {"type": "base64", "media_type": match.group(1), "data": match.group(2)}
    else:
        source = {"type": "url", "url": url}
    return {"type": "image", "source": source}


def usage_record(usage):
    if usage is None:
        return None
    read = usage.cache_read_input_tokens or 0
    written = usage.cache_creation_input_tokens or 0
    prompt = (usage.input_tokens or 0) + read + written
    completion = usage.output_tokens or 0
    return {
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "total_tokens": prompt + completion,
        "input_tokens": usage.input_tokens or 0,
        "cache_read_input_tokens": read,
        "cache_creation_input_tokens": written,
    }


def complete_scientific_anthropic(
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
    """One Messages call with the NVIDIA transport's timing, progress and error kinds.

    SDK retries are disabled: the caller owns observable, checkpointed recovery.
    """
    started, first = time.monotonic(), None
    content, finish, usage = [], None, None
    expired = threading.Event()
    request_tokens = max(max_tokens, MIN_MAX_TOKENS)
    fmt = output_format(response_format)
    metadata = {
        "started_at": datetime.now(UTC).isoformat(),
        "provider": "anthropic",
        "requested_model": model,
        "stream": True,
        "max_output_tokens": request_tokens,
        "stage_output_capacity": max_tokens,
        "effort": client.effort,
        "structured_output": bool(fmt),
        "image_count": len(images or []),
    }
    user = [image_block(url) for url in images or []] + [{"type": "text", "text": payload}]
    request = {
        "model": model,
        "max_tokens": request_tokens,
        # The stage instructions are the stable prefix shared across windows.
        "system": [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        "messages": [{"role": "user", "content": user}],
        "output_config": {"effort": client.effort, **({"format": fmt} if fmt else {})},
    }
    api = client.client.with_options(timeout=timeout, max_retries=0)
    if client.refusal_fallback:
        api = api.beta.messages
        request.update(betas=["server-side-fallback-2026-07-01"], fallbacks="default")
    else:
        api = api.messages
    metadata["refusal_fallback"] = client.refusal_fallback
    try:
        with api.stream(**request) as events:
            timer = threading.Timer(
                max(0, timeout - (time.monotonic() - started)),
                lambda: (expired.set(), events.close()),
            )
            timer.daemon = True
            timer.start()
            try:
                for event in events:
                    if expired.is_set() or time.monotonic() - started > timeout:
                        raise ScientificTransportError("deadline", content="".join(content))
                    if event.type == "content_block_delta" and event.delta.type == "text_delta":
                        first = first or time.monotonic()
                        content.append(event.delta.text)
                        if on_progress:
                            on_progress("".join(content), {**metadata, "finish_reason": None})
                final = events.get_final_message()
            finally:
                timer.cancel()
        if expired.is_set():
            raise ScientificTransportError("deadline", content="".join(content))
        usage = usage_record(final.usage)
        finish = FINISH.get(final.stop_reason, final.stop_reason)
        text = "".join(b.text for b in final.content if b.type == "text") or "".join(content)
        if not fmt:
            # Without a schema the JSON may come fenced as Markdown.
            text = re.sub(r"^\s*```(?:json)?\s*\n?|\n?\s*```\s*$", "", text)
        metadata.update(
            duration_seconds=time.monotonic() - started,
            time_to_first_token_seconds=first - started if first else None,
            served_models=[final.model],
            stop_reason=final.stop_reason,
            stop_details=final.stop_details.model_dump() if final.stop_details else None,
            request_id=getattr(final, "_request_id", None),
        )
        return ScientificResponse(text, finish, usage, metadata)
    except (Exception, KeyboardInterrupt) as error:
        key = getattr(client.client, "api_key", None)
        if expired.is_set():
            kind, retry_after = "deadline", None
        elif isinstance(error, KeyboardInterrupt):
            kind, retry_after = "interrupted", None
        elif isinstance(error, ScientificTransportError):
            kind, retry_after = error.kind, error.retry_after
        elif isinstance(error, anthropic.APIStatusError):
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
            body = json.dumps(error.body) if error.body else str(error.message or "")
            metadata["provider_message"] = redact_provider_text(body, key)[:1600] or None
        elif isinstance(error, anthropic.APITimeoutError):
            kind, retry_after = "timeout", None
        elif isinstance(error, anthropic.APIConnectionError):
            kind, retry_after = "network", None
            if request_never_sent(error):
                metadata["request_not_sent"] = True
        elif isinstance(error, anthropic.APIError):
            kind, retry_after = "provider_stream_error", None
            metadata["provider_message"] = redact_provider_text(str(error.message), key)[:1600]
        else:
            raise
        metadata.update(
            duration_seconds=time.monotonic() - started,
            usage=usage,
            finish_reason=finish,
        )
        if on_progress:
            on_progress("".join(content), {**metadata, "error_type": kind})
        raise ScientificTransportError(
            kind, content="".join(content), metadata=metadata, retry_after=retry_after
        ) from None
