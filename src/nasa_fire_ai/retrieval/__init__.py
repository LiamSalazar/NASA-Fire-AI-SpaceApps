from pathlib import Path

from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.retrieval.vectors import search as vector_search


def reciprocal_rank_fusion(rankings: list[list[str]], k: int = 60) -> list[str]:
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, evidence_id in enumerate(ranking, start=1):
            scores[evidence_id] = scores.get(evidence_id, 0) + 1 / (k + rank)
    return [item[0] for item in sorted(scores.items(), key=lambda item: (-item[1], item[0]))]


def retrieve(
    registry: EvidenceRegistry,
    query: str,
    eligible_evidence_ids=None,
    query_vector: list[float] | None = None,
    index_dir: Path | None = None,
):
    lexical = registry.search(query, eligible_evidence_ids, limit=20)
    if query_vector is None or index_dir is None:
        return lexical[:8]
    semantic = vector_search(
        query_vector, index_dir / "passage_vectors.npy", index_dir / "vector_evidence_ids.npy", 20
    )
    eligible = set(eligible_evidence_ids or [])
    semantic_ids = [eid for eid, _ in semantic if not eligible or eid in eligible]
    order = reciprocal_rank_fusion([[row["evidence_id"] for row in lexical], semantic_ids])
    by_id = {row["evidence_id"]: row for row in lexical}
    return [by_id[eid] for eid in order if eid in by_id][:8]
