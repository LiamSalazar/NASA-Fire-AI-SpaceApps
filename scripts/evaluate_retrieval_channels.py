"""Paired source-document retrieval ablation on frozen provisional judgments."""

import argparse
import json
import sys
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nasa_fire_ai.services.search import ScientificSearchService


def recall(rows, source_ids, rank):
    if not source_ids:
        return None
    found = {r.removeprefix("local-") for r in rows[:rank]}
    return len(source_ids & found) / len(source_ids)


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--vector-directory", type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Do not overwrite a receipt")
    questions = json.loads((ROOT / "evals/phase56/recall_questions.json").read_text())
    judgments = json.loads((ROOT / "evals/phase56/recall_qrels_v1.json").read_text())["judgments"]
    engine = ScientificSearchService(args.snapshot, ROOT)
    if args.vector_directory:
        from nasa_fire_ai.config import Settings
        from nasa_fire_ai.retrieval.semantic import NvidiaEmbeddingProvider
        from nasa_fire_ai.retrieval.snapshot_vectors import SnapshotVectors

        settings = Settings()
        engine.semantic_candidates = SnapshotVectors(
            args.vector_directory,
            engine.registry,
            engine.manifest["snapshot_id"],
            NvidiaEmbeddingProvider(
                settings.nvidia_api_key,
                settings.nvidia_base_url or "https://integrate.api.nvidia.com/v1",
                settings.nvidia_embedding_model,
                retries=1,
            ),
        )
    cases = []
    try:
        for question in questions:
            q = question["question"]
            wanted = {
                row["source_id"].removeprefix("local-")
                for row in judgments
                if row["question_id"] == question["id"]
            }
            start = perf_counter()
            lexical = engine.registry.search(q, limit=100)
            lexical_ms = (perf_counter() - start) * 1000
            lexical_ids = [
                engine.registry.source_metadata(row["evidence_id"])["source_id"] for row in lexical
            ]
            vector_ids = []
            if engine.semantic_candidates:
                allowed = {
                    r[0] for r in engine.registry.db.execute("SELECT evidence_id FROM passages")
                }
                vector_ids = [
                    engine.registry.source_metadata(eid)["source_id"]
                    for eid, _ in engine.semantic_candidates(q, allowed, 100)
                ]
            start = perf_counter()
            result = engine.search(q, research=True, limit=100)
            hybrid_ms = (perf_counter() - start) * 1000
            hybrid = sorted(
                result.documentary + result.discovery,
                key=lambda row: row.get("candidate_rank", 100000),
            )
            hybrid_ids = [row["source"]["source_id"] for row in hybrid]
            cases.append(
                {
                    "id": question["id"],
                    "judged_source_ids": sorted(wanted),
                    "lexical": {str(k): recall(lexical_ids, wanted, k) for k in (5, 10, 20)},
                    "full_available_channels": {
                        str(k): recall(hybrid_ids, wanted, k) for k in (5, 10, 20)
                    },
                    "vector": {str(k): recall(vector_ids, wanted, k) for k in (5, 10, 20)},
                    "lexical_ms": lexical_ms,
                    "full_ms": hybrid_ms,
                    "structured_direct_count": len(result.direct),
                    "structured_related_count": len(result.related),
                }
            )
    finally:
        engine.close()
    judged = [case for case in cases if case["judged_source_ids"]]
    summary = {
        "questions": len(cases),
        "judged_questions": len(judged),
        "judged_source_question_pairs": sum(len(case["judged_source_ids"]) for case in judged),
        "macro_document_recall": {
            channel: {
                str(k): sum(case[channel][str(k)] for case in judged) / len(judged)
                for k in (5, 10, 20)
            }
            for channel in ("lexical", "vector", "full_available_channels")
        },
        "mean_latency_ms": {
            "lexical": sum(case["lexical_ms"] for case in cases) / len(cases),
            "full_available_channels": sum(case["full_ms"] for case in cases) / len(cases),
        },
        "vector": "CONNECTED" if engine.semantic_candidates else "NOT_PROVISIONED",
        "kg_structured_document_recall": "NOT_COMPARABLE_WITH_DOCUMENT_QRELS",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"summary": summary, "cases": cases}, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
