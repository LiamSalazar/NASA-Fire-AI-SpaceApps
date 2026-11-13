"""Small-file exact cosine retrieval; vectors are optional and local to data/index."""

from pathlib import Path

import numpy as np


def search(query_vector: list[float], vectors_file: Path, ids_file: Path, limit=8):
    vectors = np.load(vectors_file)
    ids = np.load(ids_file, allow_pickle=True)
    q = np.asarray(query_vector, dtype=float)
    scores = (vectors @ q) / (np.linalg.norm(vectors, axis=1) * np.linalg.norm(q) + 1e-12)
    return [(str(ids[i]), float(scores[i])) for i in np.argsort(scores)[::-1][:limit]]
