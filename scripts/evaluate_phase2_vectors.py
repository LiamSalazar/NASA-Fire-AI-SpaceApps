#!/usr/bin/env python3
"""Evaluate frozen lexical gold with vector and deterministic RRF retrieval."""

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.retrieval.semantic import (
    EmbeddingCache,
    LocalVectorIndex,
    NvidiaEmbeddingProvider,
    rrf,
)


def metrics(rows: list[dict], key: str) -> dict:
    hits = {k: 0 for k in (1, 3, 5, 10)}
    reciprocal = 0.0
    for row in rows:
        rank = row[key]
        for cutoff in hits:
            hits[cutoff] += bool(rank and rank <= cutoff)
        reciprocal += 1 / rank if rank else 0
    n = len(rows)
    return {
        **{f"recall_at_{k}": round(hits[k] / n, 4) for k in hits},
        "mrr": round(reciprocal / n, 4),
        "questions": n,
    }


def main() -> None:
    settings = Settings()
    if not settings.nvidia_api_key:
        raise SystemExit("NVIDIA_API_KEY is required for live vector evaluation")
    registry = EvidenceRegistry(settings.registry_path)
    provider = NvidiaEmbeddingProvider(
        settings.nvidia_api_key,
        settings.nvidia_base_url or "https://integrate.api.nvidia.com/v1",
        settings.nvidia_embedding_model,
    )
    cache = EmbeddingCache(registry)
    index = LocalVectorIndex(ROOT / "data/index", "phase2-passages")
    if not index.vectors_path.exists():
        raise SystemExit("phase2 passage index is absent; run build_phase2_vectors.py")
    source_by_doc = {
        r["document_id"]: r["source_id"]
        for r in registry.db.execute("SELECT document_id,source_id FROM documents")
    }
    gold = json.loads((ROOT / "evals/phase1_5_retrieval_gold.json").read_text())["questions"]
    lexical = [q for q in gold if q["expected_source_ids"]]
    vectors, hits, misses = cache.embed_cached(provider, [q["question"] for q in lexical], "query")
    details = []
    for query, vector in zip(lexical, vectors):
        bm25_rows = registry.search(query["question"], limit=10)
        vector_rows = index.search(vector, 10)
        bm25_ids = [r["evidence_id"] for r in bm25_rows]
        vector_ids = [eid for eid, _ in vector_rows]
        fused = rrf(bm25_ids, vector_ids)
        targets = set(query["expected_source_ids"])

        def rank_of(ids, target_source_ids=targets):
            return next(
                (
                    i
                    for i, eid in enumerate(ids, 1)
                    if source_by_doc.get(registry.resolve(eid)["document_id"]) in target_source_ids
                ),
                None,
            )

        details.append(
            {
                "id": query["id"],
                "category": query["category"],
                "bm25_rank": rank_of(bm25_ids),
                "vector_rank": rank_of(vector_ids),
                "hybrid_rank": rank_of([x["evidence_id"] for x in fused]),
                "bm25": bm25_ids,
                "vector": [
                    {"evidence_id": eid, "semantic_similarity_score": score}
                    for eid, score in vector_rows
                ],
                "rrf": fused,
            }
        )
    by_category = defaultdict(list)
    for row in details:
        by_category[row["category"]].append(row)
    output = {
        "model": provider.model_identity(),
        "query_cache_hits": hits,
        "query_embeddings": misses,
        "vector": metrics(details, "vector_rank"),
        "hybrid_rrf": metrics(details, "hybrid_rank"),
        "bm25_reproduced": metrics(details, "bm25_rank"),
        "by_category": {
            k: {"vector": metrics(v, "vector_rank"), "hybrid": metrics(v, "hybrid_rank")}
            for k, v in by_category.items()
        },
        "details": details,
    }
    (ROOT / "data/eda/phase2_retrieval_evaluation.json").write_text(
        json.dumps(output, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                k: output[k]
                for k in (
                    "model",
                    "query_cache_hits",
                    "query_embeddings",
                    "vector",
                    "hybrid_rrf",
                    "bm25_reproduced",
                )
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
