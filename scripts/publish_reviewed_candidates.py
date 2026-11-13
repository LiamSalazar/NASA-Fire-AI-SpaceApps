#!/usr/bin/env python3
"""Publish only human-approved, evidence-resolvable LLM safety candidates."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry

r = EvidenceRegistry(Settings().registry_path)
out = ROOT / "data/canonical/phase1_reviewed.json"
existing = json.loads(out.read_text()) if out.exists() else []
ids = {x.get("statement_id") for x in existing}
types = {
    "CandidateSafetyImplication": "safety_implication",
    "CandidateNASAConclusion": "nasa_conclusion",
    "CandidateRequirement": "requirement",
    "CandidateGuidance": "guidance",
    "CandidateDesignCriterion": "design_criterion",
    "CandidateTestCriterion": "test_criterion",
    "CandidateOpenQuestion": "open_question",
}
added = 0
for row in r.db.execute(
    "select c.* from candidate_records c join review_queue q on q.candidate_id=c.candidate_id where q.status='APPROVED'"
):
    p = json.loads(row["payload_json"])
    kind = types.get(row["candidate_type"])
    sid = "reviewed-" + row["candidate_id"]
    if not kind or sid in ids or r.resolve(row["evidence_id"]) is None:
        continue
    existing.append(
        {
            "type": "SafetyStatementRecord",
            "statement_id": sid,
            "statement_type": kind,
            "normalized_text": p["normalized_text"],
            "source_document": p["source_document"],
            "source_page": p.get("page"),
            "source_section": p.get("section"),
            "scope_applicability": p.get("scope"),
            "evidence_refs": [
                {
                    "evidence_id": p["evidence_id"],
                    "source_id": p.get("source_document"),
                    "page": p.get("page"),
                    "section": p.get("section"),
                }
            ],
            "reviewed_from_candidate": row["candidate_id"],
            "evidence_span": p["evidence_span"],
            "modality": p.get("modality"),
            "uncertainty": p.get("uncertainty"),
        }
    )
    ids.add(sid)
    added += 1
out.write_text(json.dumps(existing, indent=2) + "\n")
print({"published": added})
