#!/usr/bin/env python3
"""Optional batch embeddings persisted for exact local cosine retrieval."""

import sys
from pathlib import Path

import numpy as np
from openai import OpenAI

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry


def main():
    s = Settings()
    if not s.api_key:
        print("Vector indexing skipped: OPENAI_API_KEY is not configured; FTS5 remains available.")
        return
    registry = EvidenceRegistry(s.registry_path)
    rows = registry.db.execute(
        "SELECT evidence_id, text FROM passages ORDER BY evidence_id"
    ).fetchall()
    client = OpenAI(api_key=s.api_key)
    vectors, ids = [], []
    for start in range(0, len(rows), 64):
        batch = rows[start : start + 64]
        response = client.embeddings.create(
            model=s.embedding_model, input=[row["text"] for row in batch]
        )
        vectors.extend(item.embedding for item in response.data)
        ids.extend(row["evidence_id"] for row in batch)
    out = s.root / "data/index"
    np.save(out / "passage_vectors.npy", np.asarray(vectors, dtype=np.float32))
    np.save(out / "vector_evidence_ids.npy", np.asarray(ids, dtype=object))
    print(f"Embedded {len(ids)} passages with {s.embedding_model}.")


if __name__ == "__main__":
    main()
