from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.models import DiscoveryCandidate
from nasa_fire_ai.retrieval.semantic import (
    EmbeddingCache,
    EmbeddingProvider,
    LocalVectorIndex,
    discovery_candidates,
    rrf,
    semantic_resolve,
)


class FakeProvider(EmbeddingProvider):
    def __init__(self):
        self.calls = 0

    def model_identity(self):
        return "fake-v1"

    def dimensions(self):
        return 2

    def embed_queries(self, texts):
        self.calls += len(texts)
        return [[1.0, 0.0] for _ in texts]

    def embed_passages(self, texts):
        self.calls += len(texts)
        return [[1.0, 0.0] for _ in texts]


def test_embedding_cache_and_exact_vector_search(tmp_path):
    registry = EvidenceRegistry(tmp_path / "e.sqlite")
    cache = EmbeddingCache(registry)
    provider = FakeProvider()
    _, hits, misses = cache.embed_cached(provider, ["same text"], "passage")
    assert (hits, misses, provider.calls) == (0, 1, 1)
    _, hits, misses = cache.embed_cached(provider, ["same text"], "passage")
    assert (hits, misses, provider.calls) == (1, 0, 1)
    index = LocalVectorIndex(tmp_path, "passages")
    index.write(["a", "b"], [[1, 0], [0, 1]], {"model_id": "fake-v1"})
    assert index.search([1, 0], 1) == [("a", 1.0)]


def test_safe_alias_outranks_embedding_candidate(tmp_path):
    registry = EvidenceRegistry(tmp_path / "e.sqlite")
    index = LocalVectorIndex(tmp_path, "concepts")
    index.write(["phenomenon:extinction"], [[1, 0]], {"model_id": "fake-v1"})
    result = semantic_resolve("PMMA", index, FakeProvider(), EmbeddingCache(registry))
    assert result.status == "RESOLVED_SAFE_ALIAS"
    assert result.canonical_ids == ["material:pmma"]


def test_rrf_is_deterministic_and_discovery_is_system_suggested(tmp_path):
    registry = EvidenceRegistry(tmp_path / "e.sqlite")
    registry.add_document("d", "source", "title")
    registry.add_passage(
        {
            "evidence_id": "e",
            "document_id": "d",
            "page": 1,
            "section": "Results",
            "text": "NASA text",
            "start_offset": 0,
            "end_offset": 9,
            "raw_file": "x",
            "checksum": "c",
        }
    )
    ranked = rrf(["e"], ["e"])
    assert ranked[0]["bm25_rank"] == ranked[0]["vector_rank"] == 1
    item = discovery_candidates("query", ranked, registry, set())[0]
    assert isinstance(item, DiscoveryCandidate)
    assert item.authority == "SYSTEM_SUGGESTED"
    assert discovery_candidates("query", ranked, registry, {"e"}) == []
