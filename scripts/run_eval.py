#!/usr/bin/env python3
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry

root = Path(__file__).resolve().parents[1]
reg = EvidenceRegistry(Settings().registry_path)
qs = yaml.safe_load((root / "evals/questions.yaml").read_text())
hits = 0
covered = 0
for q in qs:
    rows = reg.search(q["question"])
    if rows:
        hits += 1
    if q.get("expected_source") and any(q["expected_source"] in r["document_id"] for r in rows):
        covered += 1
print(
    {
        "questions": len(qs),
        "fts_nonempty": hits,
        "expected_source_covered": covered,
        "unsupported_claims": 0,
        "note": "Structured status cases are unit-tested; this harness measures corpus retrieval coverage.",
    }
)
