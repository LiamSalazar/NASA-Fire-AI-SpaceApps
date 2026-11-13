"""Source-complexity sizing and finite recovery, separate from scientific validity."""

import math
import os
import re
import time
from dataclasses import dataclass

from nasa_fire_ai.ingestion.abbreviations import segmentation_input_view
from nasa_fire_ai.ingestion.document_structure import identity
from nasa_fire_ai.ingestion.extraction_schema import CONTRACT
from nasa_fire_ai.llm.scientific_provider import ScientificTransportError


@dataclass(frozen=True)
class ProviderEnvelope:
    # Conservative usable envelope, not a claim that advertised 1M is verified.
    context_tokens: int = int(os.getenv("NVIDIA_SCIENCE_CONTEXT_TOKENS", "65536"))
    output_tokens: int = int(os.getenv("NVIDIA_SCIENCE_MAX_OUTPUT_TOKENS", "32768"))
    reasoning_tokens: int = int(os.getenv("NVIDIA_SCIENCE_REASONING_TOKENS", "8192"))
    throughput_tokens_per_second: float = float(os.getenv("NVIDIA_SCIENCE_TOKENS_PER_SECOND", "35"))
    request_timeout_seconds: float = float(os.getenv("NVIDIA_SCIENCE_REQUEST_TIMEOUT", "600"))

    def __post_init__(self):
        if (
            self.context_tokens < 4096
            or self.output_tokens < 256
            or self.output_tokens >= self.context_tokens
        ):
            raise ValueError("Invalid configured NVIDIA context/output envelope")
        if self.throughput_tokens_per_second <= 0 or self.request_timeout_seconds <= 0:
            raise ValueError("Invalid NVIDIA throughput/timeout envelope")


def complexity(text):
    """Scheduling hints only; these counts are never scientific gold/recall."""
    return {
        "characters": len(text),
        "numbers": len(re.findall(r"(?<![\w.])(?:\d+(?:\.\d+)?|\.\d+)", text)),
        "sentences": len(re.findall(r"[.!?](?!\d)(?=\s|$)", segmentation_input_view(text))),
        "table_lines": sum(
            line.count("|") > 2 or line.count("\t") > 2 for line in text.splitlines()
        ),
        "scientific_cues": len(
            re.findall(
                r"\b(?:run|test|sample|specimen|measured|observed|results?|conclu\w*|except|derived|fit)\b",
                text,
                re.IGNORECASE,
            )
        ),
    }


def segment_size(package, budget, envelope):
    if budget.segment_chars is not None:
        return budget.segment_chars
    text = "\n".join(e["text"] for e in package["evidence"])
    c = complexity(text)
    potential_output = max(1, c["sentences"] * 90 + c["numbers"] * 45 + c["table_lines"] * 140)
    capacity = min(budget.max_output_tokens or envelope.output_tokens, envelope.output_tokens)
    # Keep a whole coherent document where its estimated response fits; otherwise
    # divide by expected scientific structure, with room for context/schema.
    parts = max(1, math.ceil(potential_output / (capacity * 1.2)))
    # The conservative scheduling estimate is two text bytes per token.
    # Convert available input tokens to characters in the same direction.
    input_capacity = max(1000, (envelope.context_tokens - capacity - 12000) * 2)
    return max(1000, min(input_capacity, max(6000, math.ceil(len(text) / parts))))


def output_size(stage, text, entities, budget, envelope):
    if budget.max_output_tokens is not None:
        return min(budget.max_output_tokens, envelope.output_tokens)
    c = complexity(text)
    estimate = (
        1800 + c["scientific_cues"] * 80
        if stage == "identity"
        else 2200 + c["sentences"] * 120 + c["numbers"] * 90
        if stage == "propositions"
        else 1800 + entities * 180 + c["scientific_cues"] * 55
    )
    return min(envelope.output_tokens, max(4096, math.ceil(estimate / 1024) * 1024))


def reasoning_size(text, budget, envelope):
    explicit = budget.reasoning_tokens
    if explicit is not None:
        return min(explicit, envelope.output_tokens // 2)
    c = complexity(text)
    return min(
        envelope.reasoning_tokens,
        2048 + c["sentences"] * 16 + c["table_lines"] * 32,
        envelope.output_tokens // 2,
    )


def timeout_for(output_tokens, budget, envelope):
    base = budget.call_timeout_seconds
    if base is not None:
        return base
    return min(
        envelope.request_timeout_seconds,
        max(120, 45 + output_tokens / envelope.throughput_tokens_per_second),
    )


def split_window(window):
    """Split original spans at a structural/sentence boundary; never synthesize text."""
    from nasa_fire_ai.ingestion.document_structure import identity

    members = window["members"]
    total = sum(len(s["text"]) for s in members)
    if total <= 600:
        return []
    halfway = total // 2
    left, right, consumed = [], [], 0
    for s in members:
        length = len(s["text"])
        if consumed >= halfway:
            right.append(s)
        elif consumed + length <= halfway:
            left.append(s)
        else:
            target = halfway - consumed
            boundaries = [
                m.end()
                for m in re.finditer(
                    r"\n\s*\n|[.!?](?!\d)\s+|\n", segmentation_input_view(s["text"])
                )
            ]
            cuts = [p for p in boundaries if 150 <= p <= length - 150]
            if not cuts:
                if not left:
                    left.append(s)
                else:
                    right.append(s)
            else:
                cut = min(cuts, key=lambda p: abs(p - target))
                for collection, begin, end in ((left, 0, cut), (right, cut, length)):
                    start = s["start"] + begin
                    collection.append(
                        {
                            **s,
                            "text": s["text"][begin:end],
                            "start": start,
                            "end": s["start"] + end,
                            "id": "segment-"
                            + identity([s["evidence_id"], start, s["start"] + end])[:24],
                            "section_transitions": [
                                h
                                for h in s["section_transitions"]
                                if start <= h["start"] < s["start"] + end
                            ],
                        }
                    )
        consumed += length
    if not left or not right:
        return []
    return [
        {**window, "id": "window-" + identity([s["id"] for s in group])[:24], "members": group}
        for group in (left, right)
    ]


@dataclass(frozen=True)
class ExtractionBudget:
    # Optional operator ceilings. None delegates sizing to the source/provider.
    max_model_calls: int | None = None
    max_output_tokens: int | None = None
    max_total_tokens: int | None = None
    timeout_seconds: float | None = None
    recovery_only: bool = False
    call_timeout_seconds: float | None = None
    retries: int = 2
    segment_chars: int | None = None
    reasoning_tokens: int | None = None
    recovery_rounds: int = 2
    stream: bool = True

    def __post_init__(self):
        if any(v is not None and v < 0 for v in (self.max_model_calls, self.max_total_tokens)):
            raise ValueError("Scientific extraction ceilings must be nonnegative")
        if self.max_output_tokens is not None and self.max_output_tokens < 256:
            raise ValueError("Output token ceiling must be at least 256")
        if (self.timeout_seconds is not None and self.timeout_seconds <= 0) or (
            self.call_timeout_seconds is not None and self.call_timeout_seconds <= 0
        ):
            raise ValueError("Scientific extraction timeouts must be positive")
        if self.reasoning_tokens is not None and self.reasoning_tokens < 0:
            raise ValueError("Reasoning token allocation must be nonnegative")
        if self.retries < 0 or self.recovery_rounds < 0:
            raise ValueError("Scientific recovery limits must be nonnegative")
        if self.segment_chars is not None and self.segment_chars < 1000:
            raise ValueError("Document segments must retain readable source context")


def never_billed(error):
    """Whether a transport failure proves the request was never processed, so never billed.

    Refused before processing, or a connection that never opened (name resolution,
    refused, TLS before the body). "No response arrived" does not prove "not billed":
    a reset or a cut after sending, or a timeout, keeps the reservation.
    """
    return error.kind == "request_rejected" or (
        error.kind == "network" and bool(error.metadata.get("request_not_sent"))
    )


def record_discarded_prefetch(registry, stage, call, ahead):
    """Record a request sent ahead whose answer was not used; return how it settled.

    Returns None for a request still cancellable, which was never sent and is not
    recorded. Otherwise the request is waited for and recorded, and the result is
    ``{"usage_tokens": billed or None, "never_sent": bool}``: a failure keeps its
    reservation (it may have been billed) unless the error proves it never left.
    """
    if ahead.cancel():
        return None
    never_sent = False
    try:
        response = ahead.result()
        usage, transport = response.usage, response.metadata
    except ScientificTransportError as error:
        usage, transport = None, {**error.metadata, "error_type": error.kind}
        never_sent = bool(error.metadata.get("request_not_sent"))
    except Exception as error:  # noqa: BLE001 - any failure is recorded, never raised here
        usage, transport = None, {"error_type": type(error).__name__}
    registry.set_phase3_cache(
        identity(["prefetch-discarded", call, time.time_ns()]),
        "scientific_document_attempt",
        {
            "contract": CONTRACT,
            "stage": stage,
            "requested_model": call.get("model"),
            "state": "FINISHED",
            "outcome": {
                "model": "PREFETCH_DISCARDED",
                "prefetch": "DISCARDED",
                "usage": usage,
                "transport": transport,
            },
        },
    )
    return {"usage_tokens": (usage or {}).get("total_tokens"), "never_sent": never_sent}


ANTHROPIC_REQUEST_CONTEXT_CEILING = 131072


def request_context_limit(settings, envelope):
    """The largest request, in estimated context tokens, sent before a window is split.

    Anthropic's models take far more context than NVIDIA's conservative envelope,
    so their requests get their own limit (Diego, 2026-10-22: the largest Sonnet
    window so far was about 77,500 tokens). Windows, shared context and output
    sizes stay those of the provider envelope, so requests are unchanged except
    that fewer are split. NVIDIA keeps its envelope.
    """
    if getattr(settings, "science_provider", "nvidia") == "anthropic":
        limit = int(os.getenv("ANTHROPIC_SCIENCE_REQUEST_CONTEXT_TOKENS", "96000"))
        # A spending guard: past 131,072 one request could cost about 2 USD of input.
        if not 4096 <= limit <= ANTHROPIC_REQUEST_CONTEXT_CEILING:
            raise ValueError(
                "ANTHROPIC_SCIENCE_REQUEST_CONTEXT_TOKENS must be between 4096 and "
                f"{ANTHROPIC_REQUEST_CONTEXT_CEILING}, got {limit}"
            )
        return limit
    return envelope.context_tokens
