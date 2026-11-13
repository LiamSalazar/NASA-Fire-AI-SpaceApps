"""Snapshot-bound documentary vectors; similarity grants no scientific authority."""

import hashlib
import json
from pathlib import Path

from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.retrieval.semantic import EmbeddingCache, LocalVectorIndex


def documentary_passages(registry):
    return registry.db.execute(
        "SELECT p.evidence_id,p.text FROM passages p JOIN documents d USING(document_id) LEFT JOIN sources s USING(source_id) "
        "WHERE COALESCE(s.source_type,'') != 'NASA PSI' AND d.source_id NOT LIKE 'team-processed-%' "
        "ORDER BY p.evidence_id"
    ).fetchall()


def corpus_digest(rows):
    return hashlib.sha256(
        json.dumps([(r["evidence_id"], r["text"]) for r in rows], ensure_ascii=False).encode()
    ).hexdigest()


class SnapshotVectors:
    def __init__(self, directory: Path, registry, snapshot_id: str, provider):
        self.index = LocalVectorIndex(directory, "documentary")
        metadata = json.loads(self.index.metadata_path.read_text())
        if metadata.get("snapshot_id") != snapshot_id:
            raise ValueError("Vector snapshot identity mismatch")
        if metadata.get("model_id") != provider.model_identity():
            raise ValueError("Vector model mismatch")
        if metadata.get("corpus_digest") != corpus_digest(documentary_passages(registry)):
            raise ValueError("Vector documentary corpus mismatch")
        for kind in ("vectors", "ids"):
            path = getattr(self.index, kind + "_path")
            if hashlib.sha256(path.read_bytes()).hexdigest() != metadata.get(kind + "_sha256"):
                raise ValueError("Vector artifact integrity mismatch")
        self.provider = provider
        self.cache_registry = EvidenceRegistry(directory / "embedding-cache.sqlite")
        self.cache = EmbeddingCache(self.cache_registry)

    def __call__(self, query, eligible_ids, limit):
        vectors, _, _ = self.cache.embed_cached(self.provider, [query], "query")
        return self.index.search(vectors[0], limit=limit, eligible_ids=eligible_ids)

    def close(self):
        self.cache_registry.db.close()
