"""Frozen open-query source routing across lexical, vector, structured, graph and fusion."""

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nasa_fire_ai.config import Settings
from nasa_fire_ai.retrieval.semantic import NvidiaEmbeddingProvider
from nasa_fire_ai.retrieval.snapshot_vectors import SnapshotVectors
from nasa_fire_ai.services.search import ScientificSearchService


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--vectors", type=Path, required=True)
    parser.add_argument(
        "--questions", type=Path, default=ROOT / "evaluation/psi_open_questions_v1.json"
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Receipts are append-only")
    settings = Settings()
    engine = ScientificSearchService(args.snapshot, ROOT)
    engine.semantic_candidates = SnapshotVectors(
        args.vectors,
        engine.registry,
        engine.manifest["snapshot_id"],
        NvidiaEmbeddingProvider(
            settings.nvidia_api_key,
            settings.nvidia_base_url or "https://integrate.api.nvidia.com/v1",
            settings.nvidia_embedding_model,
            retries=1,
        ),
    )
    questions = json.loads(args.questions.read_text())["questions"]
    allowed = {r[0] for r in engine.registry.db.execute("SELECT evidence_id FROM passages")}
    sources = {
        r[0]: r[1]
        for r in engine.registry.db.execute("SELECT evidence_id,source_id FROM evidence_refs")
    }
    cases = []
    for question in questions:
        started = perf_counter()
        q = question["question"]
        lexical = [r["evidence_id"] for r in engine.registry.search(q, limit=100)]
        vector = [eid for eid, _ in engine.semantic_candidates(q, allowed, 100)]
        result = engine.search(q, limit=100, research=True)
        structured = [
            e["evidence_id"] for row in result.direct + result.related for e in row["evidence"]
        ]
        graph = []
        for c in result.intent.entity_constraints:
            investigation = c.entity_id
            for relation in (
                "hasRun",
                "hasSourceRecord",
                "hasObjective",
                "hasHypothesis",
                "hasDocumentedMethod",
                "usesApparatus",
            ):
                for target in sorted(engine.store.relations(investigation, relation)):
                    graph.extend(engine.store.evidence(target))
        hybrid = structured + [
            r["evidence_id"]
            for r in sorted(
                result.documentary + result.discovery, key=lambda r: r.get("candidate_rank", 100000)
            )
            if r.get("evidence_id")
        ]
        scores = defaultdict(float)
        for ids in (lexical, vector):
            for rank, eid in enumerate(ids, 1):
                scores[eid] += 1 / (60 + rank)
        lexical_vector = sorted(scores, key=lambda eid: -scores[eid])
        channel_ids = {
            "lexical": lexical,
            "vector": vector,
            "structured": structured,
            "graph": graph,
            "lexical_vector": lexical_vector,
            "production_hybrid": hybrid,
        }
        wanted = set(question["expected_sources"])
        case = {**question, "latency_ms": (perf_counter() - started) * 1000, "channels": {}}
        for name, ids in channel_ids.items():
            source_ranks = [sources.get(eid) for eid in ids]
            case["channels"][name] = {
                "recall": {
                    str(k): len(wanted & set(source_ranks[:k])) / len(wanted) for k in (5, 10, 20)
                },
                "source_ids_at_20": source_ranks[:20],
            }
        cases.append(case)
        print(
            json.dumps({"completed": len(cases), "total": len(questions), "id": question["id"]}),
            flush=True,
        )
    summary = {
        partition: {
            channel: {
                str(k): sum(
                    c["channels"][channel]["recall"][str(k)]
                    for c in cases
                    if partition == "all" or c["partition"] == partition
                )
                / sum(partition == "all" or c["partition"] == partition for c in cases)
                for k in (5, 10, 20)
            }
            for channel in channel_ids
        }
        for partition in ["all", *dict.fromkeys(q["partition"] for q in questions)]
    }
    args.output.write_text(
        json.dumps(
            {
                "question_file_sha256": hashlib.sha256(args.questions.read_bytes()).hexdigest(),
                "snapshot_id": engine.manifest["snapshot_id"],
                "summary": summary,
                "cases": cases,
                "boundary": "Agent-authored frozen source-routing judgments. Does not measure scientific answer coverage, support precision or independently adjudicated usefulness. Structured/KG channels answer narrower needs than documentary channels; rates are not interchangeable.",
            },
            indent=2,
        )
        + "\n"
    )
    engine.close()


if __name__ == "__main__":
    main()
