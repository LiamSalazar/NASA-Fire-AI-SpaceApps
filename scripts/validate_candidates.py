#!/usr/bin/env python3
"""Revalidate cached candidates without calling an external extractor."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.phase1 import CandidateRecord, stable_id, validate_candidate

registry = EvidenceRegistry(Settings().registry_path)
counts = {"VALIDATED": 0, "REVIEW_REQUIRED": 0, "REJECTED": 0}
for row in registry.db.execute("SELECT * FROM candidate_records").fetchall():
    payload = json.loads(row["payload_json"])
    candidate = CandidateRecord.model_validate(payload)
    status, error = validate_candidate(candidate, registry)
    registry.db.execute(
        "UPDATE candidate_records SET status=?, validation_error=? WHERE candidate_id=?",
        (status, error, candidate.candidate_id),
    )
    if status == "REVIEW_REQUIRED":
        registry.review(
            stable_id("review", candidate.candidate_id),
            row["batch_id"],
            candidate.candidate_id,
            error or "review",
            candidate.model_dump_json(),
        )
    counts[status] += 1
registry.db.commit()
print(json.dumps(counts, indent=2))
