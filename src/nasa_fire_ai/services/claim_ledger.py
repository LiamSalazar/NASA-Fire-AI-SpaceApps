"""Small operational receipt, separate from immutable scientific evidence."""

import hashlib
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

from nasa_fire_ai.services.semantic_support import MODEL_REPOSITORY, MODEL_REVISION


def persist_claim_ledger(trace, *, conversation_id, response_id, question, answer, citations):
    """Persist a bounded, allowlisted decision history without source documents or secrets."""
    directory = Path(os.getenv("NASA_CLAIM_LEDGER_DIR", "data/index/claim_ledger"))
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    now = datetime.now(UTC)
    emitted = " ".join(answer.split())
    support_map = {
        anchor["support_id"]: {
            "evidence_ids": [span["evidence_id"] for span in anchor.get("spans", [])],
            "document_id": anchor.get("document_id"),
            "source_id": anchor.get("source_id"),
            "information_need_ids": anchor.get("information_need_ids", []),
        }
        for anchor in trace.get("support_inventory", [])
        if isinstance(anchor, dict) and anchor.get("support_id")
    }
    cited_by_text = {}
    for citation in citations:
        for support in citation.get("supports", []):
            cited_by_text.setdefault(support.get("claim_text"), set()).add(
                support.get("evidence_id")
            )
    literal_representations = [
        row
        for row in trace.get("redundancy_review", {}).get("omissions", [])
        if row.get("reason") == "source_scoped_literal_containment"
    ]
    final_evidence_ids = {eid for citation in citations for eid in citation.get("evidence_ids", [])}

    def representative(claim_text):
        pending, visited = [" ".join(claim_text.split())], set()
        while pending:
            text = pending.pop()
            if not text or text in visited:
                continue
            visited.add(text)
            for row in literal_representations:
                if text not in " ".join(row.get("text", "").split()):
                    continue
                target = row.get("represented_by", "")
                normalized = " ".join(target.split())
                if normalized and normalized in emitted:
                    return target
                pending.append(normalized)
        return None

    claims = []
    for item in trace.get("verification", []):
        claim_text = item.get("text") or ""
        matched = item.get("matched_support_ids") or []
        verified = item.get("support_ids") if item.get("supported") else []
        represented_by = representative(claim_text) if item.get("supported") else None
        represented_evidence = (
            {
                eid
                for sid in (verified or [])
                for eid in support_map.get(sid, {}).get("evidence_ids", [])
            }
            & final_evidence_ids
            if represented_by
            else set()
        )
        claims.append(
            {
                "claim_id": item.get("statement_id"),
                "stage": item.get("stage"),
                "repair_of": item.get("repair_of"),
                "proposed_text": claim_text[:4000],
                "original_text": str(item.get("original_text") or claim_text)[:4000],
                "proposed_support_ids": item.get("proposed_support_ids") or [],
                "matched_support_ids": matched,
                "matched_evidence_ids": sorted(
                    {
                        eid
                        for sid in matched
                        for eid in support_map.get(sid, {}).get("evidence_ids", [])
                    }
                ),
                "verified_support_ids": verified,
                "verified_evidence_ids": sorted(
                    {
                        eid
                        for sid in verified
                        for eid in support_map.get(sid, {}).get("evidence_ids", [])
                    }
                ),
                "information_need_ids": sorted(
                    {
                        nid
                        for sid in matched
                        for nid in support_map.get(sid, {}).get("information_need_ids", [])
                    }
                ),
                "supported": bool(item.get("supported")),
                "reason": item.get("errors") or item.get("reason"),
                "communicated": bool(
                    item.get("supported")
                    and claim_text
                    and (" ".join(claim_text.split()) in emitted or represented_by)
                ),
                "represented_by": represented_by,
                "cited_evidence_ids": sorted(
                    (cited_by_text.get(claim_text, set()) | represented_evidence) - {None}
                ),
                "parent_segment": item.get("parent_segment"),
                "original_parent_text": item.get("original_parent_text"),
                "contextual_subject": item.get("contextual_subject"),
                "resolved_entities": item.get("resolved_entities", {}),
                "subject_entity_id": item.get("subject_entity_id"),
                "object_entity_id": item.get("object_entity_id"),
                "ontology_predicates": item.get("ontology_predicates", []),
                "graph_assertion_id": item.get("graph_assertion_id"),
                "graph_evidence_ids": item.get("graph_evidence_ids", []),
                "scientific_status": item.get("scientific_status"),
                "verification_mechanism": item.get("verification_mechanism"),
            }
        )
    record = {
        "schema_version": "claim-evidence-ledger-v1",
        "created_at": now.isoformat(),
        "trace_id": trace["trace_id"],
        "conversation_id": conversation_id,
        "response_id": response_id,
        "question": question[:12000],
        "queries": trace.get("queries", []),
        "information_needs": trace.get("information_needs", []),
        "system_boundaries": trace.get("system_boundaries", []),
        "snapshot_id": trace.get("snapshot_id"),
        "implementation_sha256": {
            name: hashlib.sha256((Path(__file__).parent / name).read_bytes()).hexdigest()
            for name in (
                "conversation.py",
                "semantic_support.py",
                "structured_facts.py",
                "structured_alignment.py",
                "context_assembly.py",
                "search.py",
                "ontology_support.py",
                "source_definitions.py",
            )
        },
        "generation_contract_sha256": hashlib.sha256(
            (Path(__file__).parent.parent / "llm" / "conversation.py").read_bytes()
        ).hexdigest(),
        "provider_models": sorted(
            {call["model"] for call in trace.get("provider_calls", []) if call.get("model")}
        ),
        "verifier_contract": {"repository": MODEL_REPOSITORY, "revision": MODEL_REVISION},
        "retrieved_evidence_ids": trace.get("evidence_examination", {}).get(
            "retrieved_evidence_ids", []
        ),
        "available_evidence_ids": trace.get("evidence_examination", {}).get(
            "available_evidence_ids", []
        ),
        "exposed_evidence_ids": trace.get("evidence_examination", {}).get(
            "supplied_evidence_ids", []
        ),
        "support_map": support_map,
        "claims": claims,
        "citations": [
            {
                "number": c.get("number"),
                "evidence_ids": c.get("evidence_ids", []),
                "claim_texts": [s.get("claim_text") for s in c.get("supports", [])],
            }
            for c in citations
        ],
        "omitted_after_verification": [
            a.get("text")
            for a in trace.get("coverage_summary", {}).get("accepted_but_not_communicated", [])
        ],
        "answer_sha256": hashlib.sha256(answer.encode()).hexdigest(),
    }
    payload = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    record["receipt_sha256"] = hashlib.sha256(payload.encode()).hexdigest()
    target = directory / f"{trace['trace_id']}.json"
    temporary = directory / f".{trace['trace_id']}.tmp"
    fd = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(record, stream, ensure_ascii=False, sort_keys=True)
    os.replace(temporary, target)
    cutoff = now - timedelta(days=30)
    for old in directory.glob("*.json"):
        if datetime.fromtimestamp(old.stat().st_mtime, UTC) < cutoff:
            old.unlink()
    return target
