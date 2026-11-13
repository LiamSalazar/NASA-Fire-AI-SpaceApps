#!/usr/bin/env python3
"""Build or incrementally sync local concept and passage vectors."""

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.retrieval.semantic import (
    EmbeddingCache,
    LocalVectorIndex,
    NvidiaEmbeddingProvider,
    concept_texts,
)


def digest(rows: list[tuple[str, str]]) -> str:
    return hashlib.sha256("\n".join(f"{key}|{value}" for key, value in rows).encode()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--warm-cache-only", type=int, metavar="N")
    args = parser.parse_args()
    settings = Settings()
    registry = EvidenceRegistry(settings.registry_path)
    provider = NvidiaEmbeddingProvider(
        api_key=settings.nvidia_api_key,
        base_url=settings.nvidia_base_url or "https://integrate.api.nvidia.com/v1",
        model=settings.nvidia_embedding_model,
    )
    cache = EmbeddingCache(registry)
    if not provider.api_key:
        raise SystemExit("NVIDIA_API_KEY is required for live Phase-2 vector indexing")
    started = time.monotonic()
    concepts = concept_texts()
    concept_vectors, concept_hits, concept_misses = cache.embed_cached(
        provider, [item["text"] for item in concepts], "passage"
    )
    concept_index = LocalVectorIndex(ROOT / "data/index", "phase2-concepts")
    concept_sync = concept_index.sync(
        dict(zip([item["id"] for item in concepts], concept_vectors)),
        {
            "index_id": "phase2-concepts",
            "model_id": provider.model_identity(),
            "embedding_preprocessing_version": settings.embedding_preprocessing_version,
            "corpus_snapshot_digest": digest([(item["id"], item["text"]) for item in concepts]),
            "creation_timestamp": time.time(),
            "index_kind": "canonical-controlled-concepts",
        },
    )
    passages = registry.db.execute(
        "SELECT evidence_id,text,checksum FROM passages ORDER BY evidence_id"
    ).fetchall()
    if args.warm_cache_only:
        missing = [
            row["text"]
            for row in passages
            if cache.get(provider.model_identity(), "passage", row["text"]) is None
        ]
        _, hits, misses = cache.embed_cached(provider, missing[: args.warm_cache_only], "passage")
        print(
            json.dumps(
                {
                    "warm_cache_only": True,
                    "requested": args.warm_cache_only,
                    "remaining_before": len(missing),
                    "cache_hits": hits,
                    "new_embeddings": misses,
                },
                indent=2,
            )
        )
        return
    passage_texts = [row["text"] for row in passages]
    passage_vectors, passage_hits, passage_misses = cache.embed_cached(
        provider, passage_texts, "passage"
    )
    passage_index = LocalVectorIndex(ROOT / "data/index", "phase2-passages")
    passage_sync = passage_index.sync(
        dict(zip([row["evidence_id"] for row in passages], passage_vectors)),
        {
            "index_id": "phase2-passages",
            "model_id": provider.model_identity(),
            "embedding_preprocessing_version": settings.embedding_preprocessing_version,
            "corpus_snapshot_digest": digest(
                [(row["evidence_id"], row["checksum"] or "") for row in passages]
            ),
            "creation_timestamp": time.time(),
            "index_kind": "canonical-evidence-passages",
        },
    )
    print(
        json.dumps(
            {
                "model": provider.model_identity(),
                "dimension": provider.dimensions()
                or (len(passage_vectors[0]) if passage_vectors else None),
                "concepts": len(concepts),
                "passages": len(passages),
                "cache_hits": concept_hits + passage_hits,
                "new_embeddings": concept_misses + passage_misses,
                "concept_sync": concept_sync,
                "passage_sync": passage_sync,
                "elapsed_seconds": round(time.monotonic() - started, 3),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
