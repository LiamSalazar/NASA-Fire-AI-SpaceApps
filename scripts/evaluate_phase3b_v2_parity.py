"""Deterministic V1/V2 execution parity; no model calls and no corpus writes."""

from __future__ import annotations

import json
from pathlib import Path

from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.query.offline_parser import parse_query
from nasa_fire_ai.query.v2_execution import build_bundle_from_v1_as_v2
from nasa_fire_ai.services.pipeline import build_bundle

ROOT = Path(__file__).resolve().parents[1]


def ids(items):
    return sorted(item["id"] for item in items)


def main():
    gold = json.loads((ROOT / "evals/phase3_query_interpreter_gold_reviewed_v1.json").read_text())
    registry = EvidenceRegistry(Settings(root=ROOT).registry_path)
    rows = []
    for case in gold["cases"]:
        if case["review_status"] != "REVIEWED_SCORED":
            continue
        intent = parse_query(case["query"])
        v1 = build_bundle(intent, case["query"], ROOT, registry)
        v2 = build_bundle_from_v1_as_v2(intent, case["query"], ROOT, registry).bundle
        row = {
            "case_id": case["id"],
            "v1_direct": ids(v1.direct_evidence),
            "v2_direct": ids(v2.direct_evidence),
            "v1_related": ids(v1.related_evidence),
            "v2_related": ids(v2.related_evidence),
            "v1_evidence": sorted(x["evidence_id"] for x in v1.evidence_passages),
            "v2_evidence": sorted(x["evidence_id"] for x in v2.evidence_passages),
        }
        row["direct_equal"] = row["v1_direct"] == row["v2_direct"]
        row["related_equal"] = row["v1_related"] == row["v2_related"]
        row["evidence_equal"] = row["v1_evidence"] == row["v2_evidence"]
        rows.append(row)
    n = len(rows)
    result = {
        "cases": rows,
        "metrics": {
            "evaluated": n,
            "DIRECT_PARITY": sum(x["direct_equal"] for x in rows) / n if n else 0,
            "RELATED_PARITY": sum(x["related_equal"] for x in rows) / n if n else 0,
            "EVIDENCE_ELIGIBILITY_PARITY": sum(x["evidence_equal"] for x in rows) / n if n else 0,
        },
        "method": "both paths receive the same deterministic V1 parser result; V2 is evaluated as a retrieval/execution adapter, not as a language-interpreter benchmark",
    }
    output = ROOT / "artifacts/phase3b_v1_v2_parity.json"
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result["metrics"], indent=2))


if __name__ == "__main__":
    main()
