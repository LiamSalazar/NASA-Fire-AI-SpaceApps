"""Build persistent documentary embeddings without modifying a frozen snapshot."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.hackathon import verify_snapshot
from nasa_fire_ai.retrieval.semantic import (
    EmbeddingCache,
    LocalVectorIndex,
    NvidiaEmbeddingProvider,
)
from nasa_fire_ai.retrieval.snapshot_vectors import corpus_digest, documentary_passages


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = verify_snapshot(args.snapshot, ROOT)
    settings = Settings()
    provider = NvidiaEmbeddingProvider(
        settings.nvidia_api_key,
        settings.nvidia_base_url or "https://integrate.api.nvidia.com/v1",
        settings.nvidia_embedding_model,
        retries=1,
    )
    registry = EvidenceRegistry(
        args.snapshot / "evidence.sqlite", read_only=True, evidence_root=ROOT
    )
    rows = documentary_passages(registry)
    cache_registry = EvidenceRegistry(args.output / "embedding-cache.sqlite")
    cache = EmbeddingCache(cache_registry)
    vectors = []
    for start in range(0, len(rows), 16):
        batch, hits, misses = cache.embed_cached(
            provider, [r["text"] for r in rows[start : start + 16]], "passage", batch_size=16
        )
        vectors.extend(batch)
        print(
            json.dumps(
                {
                    "completed": len(vectors),
                    "total": len(rows),
                    "cache_hits": hits,
                    "new_embeddings": misses,
                }
            ),
            flush=True,
        )
    index = LocalVectorIndex(args.output, "documentary")
    index.write(
        [r["evidence_id"] for r in rows],
        vectors,
        {
            "snapshot_id": manifest["snapshot_id"],
            "model_id": provider.model_identity(),
            "corpus_digest": corpus_digest(rows),
            "selection": "documentary-and-catalogue-v1",
            "chunking": "registered passages; phase2-v1 subsegment averaging",
        },
    )
    metadata = json.loads(index.metadata_path.read_text())
    for kind in ("vectors", "ids"):
        metadata[kind + "_sha256"] = hashlib.sha256(
            getattr(index, kind + "_path").read_bytes()
        ).hexdigest()
    index.metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")
    registry.db.close()
    cache_registry.db.close()


if __name__ == "__main__":
    main()
