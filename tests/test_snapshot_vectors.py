"""Synthetic index integrity and eligibility checks; no external model calls."""

import hashlib
import json

import pytest

from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.retrieval.semantic import LocalVectorIndex
from nasa_fire_ai.retrieval.snapshot_vectors import (
    SnapshotVectors,
    corpus_digest,
    documentary_passages,
)


class Provider:
    def model_identity(self):
        return "synthetic"

    def embed_queries(self, texts):
        return [[1.0, 0.0] for _ in texts]


@pytest.fixture
def assets(tmp_path):
    registry = EvidenceRegistry(tmp_path / "registry.sqlite")
    registry.add_document("doc", "report", "Synthetic report")
    registry.db.execute(
        "INSERT INTO passages(evidence_id,document_id,text) VALUES ('e1','doc','alpha')"
    )
    registry.db.execute(
        "INSERT INTO passages(evidence_id,document_id,text) VALUES ('e2','doc','beta')"
    )
    registry.db.commit()
    index = LocalVectorIndex(tmp_path / "vectors", "documentary")
    index.write(
        ["e1", "e2"],
        [[1.0, 0.0], [0.0, 1.0]],
        {
            "snapshot_id": "frozen",
            "model_id": "synthetic",
            "corpus_digest": corpus_digest(documentary_passages(registry)),
        },
    )
    metadata = json.loads(index.metadata_path.read_text())
    for kind in ("ids", "vectors"):
        metadata[kind + "_sha256"] = hashlib.sha256(
            getattr(index, kind + "_path").read_bytes()
        ).hexdigest()
    index.metadata_path.write_text(json.dumps(metadata))
    yield registry, index
    registry.db.close()


def test_snapshot_vectors_filter_before_ranking(assets):
    registry, index = assets
    adapter = SnapshotVectors(index.root, registry, "frozen", Provider())
    assert adapter("query", {"e2"}, 1)[0][0] == "e2"
    adapter.cache_registry.db.close()


@pytest.mark.parametrize("change", ["snapshot", "corpus", "artifact"])
def test_snapshot_vectors_reject_incompatible_assets(assets, change):
    registry, index = assets
    if change == "corpus":
        registry.db.execute("UPDATE passages SET text='changed'")
    if change == "artifact":
        index.vectors_path.write_bytes(b"corrupt")
    with pytest.raises(ValueError):
        SnapshotVectors(
            index.root, registry, "other" if change == "snapshot" else "frozen", Provider()
        )
