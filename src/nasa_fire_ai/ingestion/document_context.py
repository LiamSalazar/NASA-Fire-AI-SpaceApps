"""Explicit universal methods and local exceptions through the existing ScopeResolver."""

import re

from nasa_fire_ai.context import ContextStatement, ContextStatus, ScopeResolver, SourceLocation
from nasa_fire_ai.ingestion.abbreviations import segmentation_view
from nasa_fire_ai.ingestion.source_spans import normalized_with_offsets


def norm(text):
    return normalized_with_offsets(text)[0].lower().strip()


def has(label, text):
    return bool(re.search(r"(?<![\w-])" + re.escape(norm(label)) + r"(?![\w-])", norm(text)))


def gravity_binding(subject, obj, spans, entities, document, semantic):
    """Return source-supported applicability, conflict, or unknown; never approval."""
    run, condition = entities[subject], entities[obj]
    if run["class_id"] != "ExperimentalRun":
        return {"status": "UNKNOWN"}
    source = spans[0]["source_id"]
    groups = [
        e
        for e in entities.values()
        if e["class_id"] in {"Investigation", "ExperimentFamily"} and e["source_id"] == source
    ]
    members = []
    for group in groups:
        if any(
            has(run["label"], s["quote"])
            and has(group["label"], s["quote"])
            and re.search(
                r"\b(?:part\s+of|belongs?\s+to|belonged\s+to|in\s+group|member\s+of)\b",
                s["quote"],
                re.IGNORECASE,
            )
            for s in spans
        ):
            members.append(group)
    resolver = ScopeResolver()
    proof = []
    aliases = {
        canonical: meta.get("aliases", []) + [canonical]
        for canonical, meta in getattr(semantic, "entity_mentions", {}).items()
        if meta.get("relation") == "hasGravityCondition"
    }
    desired = next(
        (
            key
            for key, terms in aliases.items()
            if norm(condition["label"]) in {norm(t) for t in terms}
        ),
        norm(condition["label"]),
    )
    for segment in document["segments"]:
        if segment["source_id"] != source:
            continue
        for m in re.finditer(
            r".+?(?:[.!?](?!\d)(?=\s|$)|$)", segmentation_view(segment["text"]), re.DOTALL
        ):
            text = segment["text"][m.start() : m.end()].strip()
            if not re.search(r"\b(?:conducted|performed|tested)\b", text, re.IGNORECASE):
                continue
            values = [key for key, terms in aliases.items() if any(has(t, text) for t in terms)]
            if len(values) != 1:
                continue
            local = (
                has(run["label"], text)
                and bool(
                    re.search(
                        re.escape(run["label"]) + r".{0,100}\b(?:conducted|performed|tested)\b",
                        norm(text),
                        re.IGNORECASE,
                    )
                )
                and not re.search(r"\bexcept\b", text, re.IGNORECASE)
            )
            shared = (
                bool(members)
                and any(has(g["label"], text) for g in members)
                and bool(re.search(r"\ball\b.{0,120}\b(?:tests|experiments|runs)\b", norm(text)))
            )
            if not local and not shared:
                continue
            exception = bool(
                re.search(
                    r"\bexcept\b.{0,100}" + re.escape(run["label"]) + r"\b",
                    norm(text),
                    re.IGNORECASE,
                )
            )
            support = {
                "evidence_id": segment["evidence_id"],
                "quote": text,
                "start": segment["start"] + segment["text"].find(text),
            }
            statement = ContextStatement(
                statement_id="context:" + segment["id"] + ":" + str(m.start()),
                context_type="gravity",
                value=values[0],
                entity_ids=[subject],
                evidence_ids=[segment["evidence_id"]],
                original_text=text,
                source_location=SourceLocation(
                    document_id=source + ":document",
                    source_id=source,
                    page=segment["page"],
                    section=segment["section"],
                ),
                validation_status=ContextStatus.EXPLICIT_LOCAL
                if local
                else ContextStatus.VERIFIED_APPLICABLE_CONTEXT,
                scope="local" if local else "campaign",
                exceptions=[subject] if exception else [],
                support_spans=[support],
                canonical_review="PENDING",
            )
            resolver.add(statement)
            proof.append(support)
    resolved = resolver.resolve(subject, "gravity", desired)
    if desired in resolved.values and resolved.status in {
        ContextStatus.EXPLICIT_LOCAL,
        ContextStatus.VERIFIED_APPLICABLE_CONTEXT,
    }:
        return {
            "status": "SUPPORTED",
            "resolution": resolved.model_dump(mode="json"),
            "support": proof,
        }
    if resolved.values and desired not in resolved.values:
        return {
            "status": "CONTRADICTED",
            "resolution": resolved.model_dump(mode="json"),
            "support": proof,
        }
    return {"status": "UNKNOWN", "resolution": resolved.model_dump(mode="json"), "support": proof}
