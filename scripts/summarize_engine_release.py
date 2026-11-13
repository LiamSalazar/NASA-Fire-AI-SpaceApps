"""Summarize preserved release receipts and explicit human-readable source reviews.

This performs bookkeeping only. It does not infer target truth, replace source
review with NLI, or modify any frozen question, target or previous receipt.
"""

import argparse
import gzip
import json
from collections import Counter
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    raw = path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix == ".gz" else raw)


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument(
        "--receipts", type=Path, default=ROOT / "artifacts/scientific_engine_release_v1"
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Preserve earlier summaries: output must be new")
    summary = {
        "scientific_adjudication": "Implementing-agent source review, not independent scientists",
        "runs": {},
    }
    for name, run_path, review_path in [
        ("development", "live-development.json.gz", "development-source-review.json"),
        ("holdout_v1", "live-holdout-v1.json.gz", "holdout-v1-source-review.json"),
        ("fresh_v2_experiment", "live-fresh-v2.json.gz", "fresh-v2-source-review.json"),
    ]:
        run, review = read(args.receipts / run_path), read(args.receipts / review_path)
        cases = run["cases"]
        checks = [
            v
            for c in cases
            for v in c["trace"].get("verification", [])
            if v.get("stage") != "fallback"
        ]
        citations = [v for c in cases for v in c["citation_checks"]]
        calls = [v for c in cases for v in c["trace"].get("provider_calls", [])]
        targets = review["targets"]
        row = {
            "turns": len(cases),
            "http_200": sum(c["http_status"] == 200 for c in cases),
            "response_modes": dict(
                Counter(c["response"]["provider_status"]["response_mode"] for c in cases)
            ),
            "citation_exact_span_checks": len(citations),
            "citation_checks_passed": sum(
                c["http_status"] == 200 and c["exact_span"] for c in citations
            ),
            "provider_calls": len(calls),
            "recorded_tokens": sum(c.get("usage", {}).get("total_tokens", 0) for c in calls),
            "calls_with_usage": sum(bool(c.get("usage")) for c in calls),
            "provider_errors": sum(bool(c.get("error_type")) for c in calls),
            "partial_provider_outputs": sum(bool(c.get("partial_generation")) for c in calls),
            "median_response_seconds": median(c["response_seconds"] for c in cases),
            "verifier_accepted_proposals": sum(v["supported"] for v in checks),
            "verifier_rejected_proposals": sum(not v["supported"] for v in checks),
            "communicated_generated_claims": sum(
                c["response"]["verification_status"]["communicated_generated_claim_count"]
                for c in cases
            ),
            "reviewed_targets": len(targets),
            "retrieved_exact_target_pages": sum(t["candidate_retrieved"] for t in targets),
            "supplied_exact_target_pages": sum(t["source_page_supplied"] for t in targets),
            "reviewed_targets_communicated": sum(
                t["faithfully_communicated_with_support"] for t in targets
            ),
            "target_communication_fraction": sum(
                t["faithfully_communicated_with_support"] for t in targets
            )
            / len(targets),
            "critical_errors": review.get("critical_scientific_errors", []),
            "boundary": "Verifier counts describe decisions, not scientific precision. Exact page hits are not content coverage. Different runs are not a controlled causal quality comparison.",
        }
        if name != "development":
            answerable = [c for c in review["cases"] if c["answerable"]]
            success = sum(c["useful_natural_explanation"] for c in answerable)
            row.update(
                answerable_turns=len(answerable),
                useful_natural_turns=success,
                useful_natural_fraction=success / len(answerable),
                judgments=dict(Counter(c["judgment"] for c in review["cases"])),
            )
        if name == "fresh_v2_experiment":
            row["essential_content_supplied_review"] = sum(
                t["essential_content_supplied_review"] for t in targets
            )
            row["source_pages_examined_for_routing"] = sum(
                t["source_examined_for_routing"] for t in targets
            )
        summary["runs"][name] = row
    summary["totals"] = {
        k: sum(v[k] for v in summary["runs"].values())
        for k in [
            "turns",
            "provider_calls",
            "recorded_tokens",
            "citation_exact_span_checks",
            "citation_checks_passed",
        ]
    }
    before = read(args.receipts / "context-baseline-reproduced.json")
    after = read(args.receipts / "context-release.json")
    summary["fixed_query_routing"] = {
        "before": before["summary"],
        "after": after["summary"],
        "boundary": "Offline fixed-query replay, no generation or proposition grading",
    }
    summary["recall_at_20"] = {
        name: read(args.receipts / path)["summary"]["revised"]["macro_recall_at"]["20"]
        for name, path in [("baseline", "baseline-recall.json"), ("final", "final-recall.json")]
    }
    args.output.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary["totals"]))


if __name__ == "__main__":
    main()
