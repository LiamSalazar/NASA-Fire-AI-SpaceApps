"""Measure a declared query set; source checks never become scientific inferences."""

import argparse
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nasa_fire_ai.ingestion.hackathon import digest
from nasa_fire_ai.ingestion.structured_provenance import round_trip
from nasa_fire_ai.services.search import ScientificSearchService


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument(
        "--snapshot", type=Path, default=ROOT / "data/snapshots/hackathon-20261105-v9"
    )
    parser.add_argument("--cases", type=Path, default=ROOT / "evals/hackathon_search_cases.json")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--assist-offline", action="store_true")
    args = parser.parse_args()
    engine = ScientificSearchService(args.snapshot, ROOT)
    results = []
    checked = set()
    attribution_errors = []
    false_direct = []
    try:
        for case in json.loads(args.cases.read_text()):
            result = engine.search(case["question"], limit=6, assist=args.assist_offline)
            if case["must_abstain"] and result.direct:
                false_direct.append(case["id"])
            references = [e for r in result.direct + result.related for e in r["evidence"]]
            references += result.documentary + result.discovery
            for evidence in references:
                eid = evidence["evidence_id"]
                if eid in checked:
                    continue
                resolved = engine.registry.resolve(eid)
                try:
                    if not resolved or digest(resolved["raw_file"]) != resolved["checksum"]:
                        raise ValueError("unresolvable bytes or checksum")
                    for cell in resolved.get("source_cells", []):
                        round_trip(cell, ROOT)
                except (OSError, ValueError) as exc:
                    attribution_errors.append({"evidence_id": eid, "error": str(exc)})
                checked.add(eid)
            results.append(
                {
                    "id": case["id"],
                    "question": case["question"],
                    "sufficiency": result.sufficiency,
                    "metrics": result.metrics,
                    "unresolved": result.intent.unresolved_mentions,
                    "returned_evidence": len(references),
                    "accepted_claims": len(result.claims),
                    "verification": result.verification,
                    "comparison": result.comparison,
                    "positive_control_missed": not case["must_abstain"] and not bool(result.direct),
                }
            )
    finally:
        engine.close()
    report = {
        "snapshot_id": engine.manifest["snapshot_id"],
        "cases_sha256": digest(args.cases),
        "queries": results,
        "unique_evidence_checked": len(checked),
        "query_count": len(results),
        "unverified_accepted_claims": sum(
            v["status"] not in {"SUPPORTED", "SUPPORTED_WITH_LIMITATIONS"}
            for r in results
            for v in r["verification"]
        ),
        "positive_controls_missed": [r["id"] for r in results if r["positive_control_missed"]],
        "attribution_errors": attribution_errors,
        "false_direct_on_abstention_cases": false_direct,
        "median_total_ms": statistics.median(r["metrics"]["total_ms"] for r in results),
        "max_total_ms": max(r["metrics"]["total_ms"] for r in results),
        "limitations": [
            "Declared regression cases, not independent expert adjudication",
            "No claim of improvement against another engine",
            "Case-level abstention checks do not measure general scientific precision",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k != "queries"}, indent=2))
    if attribution_errors or false_direct:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
