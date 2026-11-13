#!/usr/bin/env python3
"""Measure frozen Phase-1.5 lexical and structured retrieval baselines.

The evaluator is read-only: it never changes the evidence registry, graph, or
canonical records.  DIRECT remains the existing deterministic matcher result.
"""

import json
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.query import parse_query
from nasa_fire_ai.services.pipeline import build_bundle


def ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def main() -> None:
    start = time.monotonic()
    gold = json.loads((ROOT / "evals/phase1_5_retrieval_gold.json").read_text())["questions"]
    registry = EvidenceRegistry(Settings().registry_path)
    source_by_document = {
        row["document_id"]: row["source_id"]
        for row in registry.db.execute("select document_id,source_id from documents")
    }
    lexical = [q for q in gold if q["expected_source_ids"]]
    hit_at = {k: 0 for k in (1, 3, 5, 10)}
    reciprocal = 0.0
    no_result = 0
    per_category: dict[str, dict] = defaultdict(
        lambda: {"n": 0, "r1": 0, "r3": 0, "r5": 0, "r10": 0, "rr": 0.0}
    )
    lexical_details = []
    for q in lexical:
        rows = registry.search(q["question"], limit=10)
        ranked = [source_by_document.get(row["document_id"]) for row in rows]
        targets = set(q["expected_source_ids"])
        rank = next((i for i, source in enumerate(ranked, 1) if source in targets), None)
        if not rows:
            no_result += 1
        cat = per_category[q["category"]]
        cat["n"] += 1
        for k in hit_at:
            if rank and rank <= k:
                hit_at[k] += 1
                cat[f"r{k}"] += 1
        if rank:
            reciprocal += 1 / rank
            cat["rr"] += 1 / rank
        lexical_details.append(
            {"id": q["id"], "rank": rank, "returned_sources": ranked, "category": q["category"]}
        )
    lexical_metrics = {
        "questions": len(lexical),
        **{f"recall_at_{k}": ratio(hit_at[k], len(lexical)) for k in hit_at},
        "mrr": round(reciprocal / len(lexical), 4) if lexical else None,
        "no_result_rate": ratio(no_result, len(lexical)),
        "by_category": {
            key: {
                "questions": value["n"],
                "recall_at_1": ratio(value["r1"], value["n"]),
                "recall_at_3": ratio(value["r3"], value["n"]),
                "recall_at_5": ratio(value["r5"], value["n"]),
                "recall_at_10": ratio(value["r10"], value["n"]),
                "mrr": round(value["rr"] / value["n"], 4) if value["n"] else None,
            }
            for key, value in per_category.items()
        },
    }
    structured = [q for q in gold if q["expected_direct"]]
    status_hits = {"DIRECT": 0, "RELATED": 0, "NO_DIRECT_EVIDENCE": 0}
    status_total = defaultdict(int)
    parser_mode = 0
    evidence_total = evidence_resolved = 0
    structured_details = []
    for q in structured:
        intent = parse_query(q["question"])
        bundle = build_bundle(intent, q["question"], ROOT, registry)
        actual = (
            "DIRECT"
            if bundle.direct_evidence
            else "RELATED"
            if bundle.related_evidence
            else "NO_DIRECT_EVIDENCE"
        )
        expected = q["expected_direct"]
        status_total[expected] += 1
        if actual == expected:
            status_hits[expected] += 1
        if intent.query_mode in {
            "experiment_search",
            "compare",
            "combined_search",
            "safety_search",
        }:
            parser_mode += 1
        ids = [
            eid
            for item in bundle.direct_evidence + bundle.related_evidence
            for eid in item.get("evidence_ids", [])
        ]
        evidence_total += len(ids)
        evidence_resolved += sum(registry.resolve(eid) is not None for eid in ids)
        structured_details.append(
            {
                "id": q["id"],
                "expected": expected,
                "actual": actual,
                "intent": intent.model_dump(),
                "evidence_ids": ids,
            }
        )
    structured_metrics = {
        "questions": len(structured),
        "overall_status_correctness": ratio(sum(status_hits.values()), len(structured)),
        "direct_correctness": ratio(status_hits["DIRECT"], status_total["DIRECT"]),
        "related_correctness": ratio(status_hits["RELATED"], status_total["RELATED"]),
        "abstention_correctness": ratio(
            status_hits["NO_DIRECT_EVIDENCE"], status_total["NO_DIRECT_EVIDENCE"]
        ),
        "deterministic_parser_supported_rate": ratio(parser_mode, len(structured)),
        "citation_evidence_coverage": ratio(evidence_resolved, evidence_total),
        "status_totals": dict(status_total),
    }
    output = {
        "gold_version": "phase1.5-frozen-2026-10-04",
        "fts_bm25": lexical_metrics,
        "kg_structured": structured_metrics,
        "combined_current_system": {
            "lexical_source_recall_at_10": lexical_metrics["recall_at_10"],
            "structured_status_correctness": structured_metrics["overall_status_correctness"],
            "direct_semantics": "unchanged deterministic canonical constraints",
        },
        "details": {"lexical": lexical_details, "structured": structured_details},
        "elapsed_seconds": round(time.monotonic() - start, 3),
    }
    output_path = ROOT / "data/eda/phase15_retrieval_baseline.json"
    output_path.write_text(json.dumps(output, indent=2) + "\n")
    print(
        json.dumps(
            {k: output[k] for k in ("fts_bm25", "kg_structured", "elapsed_seconds")}, indent=2
        )
    )


if __name__ == "__main__":
    main()
