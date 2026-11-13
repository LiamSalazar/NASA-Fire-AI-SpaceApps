"""Recover literal source offsets after reversible whitespace/NFC normalization."""

import copy
import re
import unicodedata
from functools import lru_cache


@lru_cache(maxsize=1 << 15)
def normalized_text(text):
    """The whitespace- and NFC-normalized text alone, cached: it is pure."""
    return normalized_with_offsets(text)[0]


def normalized_with_offsets(text):
    output, offsets = [], []
    for match in re.finditer(r"\s+|[^\s][\u0300-\u036f]*", text):
        token = match.group()
        normalized = " " if token.isspace() else unicodedata.normalize("NFC", token)
        output.extend(normalized)
        offsets.extend([(match.start(), match.end())] * len(normalized))
    return "".join(output), offsets


def recover_span(source, proposal, start_offset=None):
    if not proposal:
        raise ValueError("empty supporting span")
    exact = [m.start() for m in re.finditer(re.escape(proposal), source)]
    if start_offset is not None and start_offset in exact:
        exact = [start_offset]
    if len(exact) == 1:
        start = exact[0]
        return {"span": proposal, "start": start, "end": start + len(proposal), "method": "EXACT"}
    normalized, offsets = normalized_with_offsets(source)
    needle = normalized_with_offsets(proposal)[0].strip()
    if not needle:
        raise ValueError("empty supporting span")
    positions = [m.start() for m in re.finditer(re.escape(needle), normalized)]
    if start_offset is not None:
        positions = [p for p in positions if offsets[p][0] == start_offset]
    if len(positions) != 1:
        raise ValueError("span missing or ambiguous; explicit source offset required")
    start = offsets[positions[0]][0]
    end = offsets[positions[0] + len(needle) - 1][1]
    return {"span": source[start:end], "start": start, "end": end, "method": "WHITESPACE_NFC"}


def normalized(text):
    return normalized_text(text).lower().strip()


def mentions(label, text):
    return bool(
        re.search(r"(?<![\w-])" + re.escape(normalized(label)) + r"(?![\w-])", normalized(text))
    )


def locate(support, evidence):
    spans = []
    for span in support:
        ref = evidence.get(span["evidence_id"])
        if not ref:
            raise ValueError("UNKNOWN_EVIDENCE_ID")
        located = recover_span(ref["text"], span["quote"], span.get("start"))
        spans.append(
            {
                "evidence_id": span["evidence_id"],
                "source_id": ref["source_id"],
                "page": ref["page"],
                "checksum": ref["checksum"],
                "start": located["start"],
                "end": located["end"],
                "quote": located["span"],
                "locator": ref["locator"],
            }
        )
    if len({s["source_id"] for s in spans}) != 1:
        raise ValueError("CROSS_DOCUMENT_SUPPORT_REQUIRES_REVIEW")
    return spans


def contiguous_support(spans, evidence):
    """Join only overlapping spans or whitespace gaps in the same original page.

    This permits line-wrapped names without using an uncited intervening sentence
    as evidence. Returned text and offsets always come from the immutable source.
    """
    merged = []
    for span in sorted(spans, key=lambda s: (s["evidence_id"], s["start"])):
        if merged and merged[-1]["evidence_id"] == span["evidence_id"]:
            previous = merged[-1]
            text = evidence[span["evidence_id"]]["text"]
            if (
                span["start"] <= previous["end"]
                or not text[previous["end"] : span["start"]].strip()
            ):
                previous["end"] = max(previous["end"], span["end"])
                previous["quote"] = text[previous["start"] : previous["end"]]
                continue
        merged.append(copy.deepcopy(span))
    return merged
