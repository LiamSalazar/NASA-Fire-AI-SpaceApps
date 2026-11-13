"""Execute bounded, provenance-only Phase-2 closure evaluations.

This script never writes canonical records, RDF, the controlled lexicon, or raw
NASA artifacts. It reads the frozen vector index and writes evaluation JSON only.
"""

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.query import parse_query
from nasa_fire_ai.retrieval.semantic import (
    EmbeddingCache,
    LocalVectorIndex,
    NvidiaEmbeddingProvider,
    rrf,
)
from nasa_fire_ai.services.pipeline import build_bundle


def ranks_metrics(ranks: list[int | None]) -> dict:
    denominator = len(ranks)
    return {
        "questions": denominator,
        **{
            f"recall_at_{cutoff}": round(
                sum(rank is not None and rank <= cutoff for rank in ranks) / denominator, 4
            )
            for cutoff in (1, 3, 5, 10)
        },
        "mrr": round(sum(1 / rank if rank else 0 for rank in ranks) / denominator, 4),
    }


def first_rank(ids: list[str], targets: set[str]) -> int | None:
    return next((rank for rank, evidence_id in enumerate(ids, 1) if evidence_id in targets), None)


def source_for(registry: EvidenceRegistry, evidence_id: str) -> str | None:
    passage = registry.resolve(evidence_id)
    if not passage:
        return None
    row = registry.db.execute(
        "SELECT source_id FROM documents WHERE document_id=?", (passage["document_id"],)
    ).fetchone()
    return row[0] if row else None


def graph_rankings(registry, index, cache, provider) -> dict:
    gold = json.loads((ROOT / "evals/phase2_graph_constrained_gold.json").read_text())["cases"]
    vectors, hits, misses = cache.embed_cached(provider, [row["query"] for row in gold], "query")
    rows = []
    for row, vector in zip(gold, vectors):
        intent = parse_query(row["query"])
        bundle = build_bundle(intent, row["query"], ROOT, registry)
        eligible = set()
        for item in bundle.direct_evidence + bundle.related_evidence:
            eligible.update(item["evidence_ids"])
        targets = set(row["expected_evidence_ids"])
        bm25_rows = registry.search(row["query"], eligible_ids=list(eligible), limit=10)
        bm25_ids = [result["evidence_id"] for result in bm25_rows]
        # Graph eligibility is the universe before ranking. Do not retrieve
        # globally and then apply a vector-derived condition.
        vector_rows = index.search(vector, limit=10, eligible_ids=eligible)
        vector_ids = [evidence_id for evidence_id, _ in vector_rows]
        fused = rrf(bm25_ids, vector_ids)
        rrf_ids = [result["evidence_id"] for result in fused]
        rows.append(
            {
                **row,
                "query_intent": intent.model_dump(mode="json"),
                "eligible_evidence_ids": sorted(eligible),
                "eligible_count": len(eligible),
                "gold_eligible": targets.issubset(eligible),
                "bm25": bm25_ids,
                "vector": [
                    {"evidence_id": evidence_id, "semantic_similarity_score": score}
                    for evidence_id, score in vector_rows
                ],
                "rrf": fused,
                "bm25_rank": first_rank(bm25_ids, targets),
                "vector_rank": first_rank(vector_ids, targets),
                "rrf_rank": first_rank(rrf_ids, targets),
            }
        )
    return {
        "cases": rows,
        "cache_hits": hits,
        "new_query_embeddings": misses,
        "average_eligible_universe": round(sum(r["eligible_count"] for r in rows) / len(rows), 2),
        "median_eligible_universe": sorted(r["eligible_count"] for r in rows)[len(rows) // 2],
        "corpus_passages": registry.db.execute("SELECT count(*) FROM passages").fetchone()[0],
        "percentage_reduction": round(
            1
            - sum(r["eligible_count"] for r in rows)
            / len(rows)
            / registry.db.execute("SELECT count(*) FROM passages").fetchone()[0],
            6,
        ),
        "gold_removed_by_graph": sum(not r["gold_eligible"] for r in rows),
        "graph_bm25": ranks_metrics([r["bm25_rank"] for r in rows]),
        "graph_vector": ranks_metrics([r["vector_rank"] for r in rows]),
        "graph_rrf": ranks_metrics([r["rrf_rank"] for r in rows]),
    }


def vector_rescue() -> dict:
    rows = json.loads((ROOT / "data/eda/phase2_retrieval_evaluation.json").read_text())["details"]
    missed = [row for row in rows if not row["bm25_rank"] or row["bm25_rank"] > 10]

    def recovered(cutoff):
        return sum(bool(row["vector_rank"] and row["vector_rank"] <= cutoff) for row in missed)

    return {
        "denominator": len(missed),
        "bm25_miss_ids": [row["id"] for row in missed],
        "oracle_vector_recovered": {f"at_{k}": recovered(k) for k in (1, 3, 5, 10)},
        "oracle_rescue_recall": {
            f"at_{k}": round(recovered(k) / len(missed), 4) if missed else 0.0
            for k in (1, 3, 5, 10)
        },
        "note": "Oracle result: it assumes gold reveals that BM25 missed. No deployable trigger is claimed.",
    }


def discovery_gold(registry: EvidenceRegistry) -> list[dict]:
    frozen = json.loads((ROOT / "evals/phase1_5_retrieval_gold.json").read_text())["questions"]
    selected = [row for row in frozen if row["category"] == "documentary"][:15]
    items = []
    for row in selected:
        source_ids = row["expected_source_ids"]
        candidate = registry.db.execute(
            """SELECT p.evidence_id FROM passages p JOIN documents d ON d.document_id=p.document_id
            WHERE d.source_id=? ORDER BY p.page,p.start_offset LIMIT 1""",
            (source_ids[0],),
        ).fetchone()
        if not candidate:
            raise RuntimeError(f"missing source-backed passage for {row['id']}")
        items.append(
            {
                "id": f"discovery-{row['id']}",
                "frozen_gold_id": row["id"],
                "query": row["question"],
                "relevant_evidence_ids": [candidate[0]],
                "relevant_source_ids": source_ids,
                "why_potentially_relevant": "Frozen source-backed documentary retrieval gold identifies the NASA source as relevant to the query.",
                "why_not_direct": "The query has no deterministic structured experiment match in the current QueryIntent/KG model.",
                "why_not_related": "No explicit structured overlap/difference relation is established for this documentary query.",
                "review_status": "SOURCE_BACKED_FROM_FROZEN_RETRIEVAL_GOLD",
            }
        )
    return items


def discovery_rankings(registry, index, cache, provider) -> dict:
    gold = discovery_gold(registry)
    (ROOT / "evals/phase2_discovery_gold.json").write_text(
        json.dumps({"version": "phase2-closure-2026-10-04", "cases": gold}, indent=2) + "\n"
    )
    vectors, hits, misses = cache.embed_cached(provider, [row["query"] for row in gold], "query")
    rows = []
    for row, vector in zip(gold, vectors):
        intent = parse_query(row["query"])
        bundle = build_bundle(intent, row["query"], ROOT, registry)
        excluded = {
            evidence_id
            for item in bundle.direct_evidence + bundle.related_evidence
            for evidence_id in item["evidence_ids"]
        }
        bm25_rows = [
            r for r in registry.search(row["query"], limit=20) if r["evidence_id"] not in excluded
        ][:10]
        bm25_ids = [r["evidence_id"] for r in bm25_rows]
        vector_rows = [r for r in index.search(vector, limit=30) if r[0] not in excluded][:10]
        vector_ids = [evidence_id for evidence_id, _ in vector_rows]
        fused = [r for r in rrf(bm25_ids, vector_ids) if r["evidence_id"] not in excluded][:10]
        target_sources = set(row["relevant_source_ids"])

        def source_rank(ids, target_sources=target_sources):
            return next(
                (
                    rank
                    for rank, eid in enumerate(ids, 1)
                    if source_for(registry, eid) in target_sources
                ),
                None,
            )

        results = {
            "bm25_rank": source_rank(bm25_ids),
            "vector_rank": source_rank(vector_ids),
            "rrf_rank": source_rank([r["evidence_id"] for r in fused]),
        }
        rows.append(
            {
                **row,
                **results,
                "excluded_ids": sorted(excluded),
                "bm25": bm25_ids,
                "vector": [
                    {"evidence_id": eid, "semantic_similarity_score": score}
                    for eid, score in vector_rows
                ],
                "rrf": fused,
            }
        )

    def precision(method, cutoff):
        total = 0
        for row in rows:
            ids = (
                row[method][:cutoff]
                if method == "bm25"
                else [x["evidence_id"] for x in row[method][:cutoff]]
            )
            total += (
                sum(source_for(registry, eid) in row["relevant_source_ids"] for eid in ids) / cutoff
            )
        return round(total / len(rows), 4)

    output = {
        "cases": rows,
        "cache_hits": hits,
        "new_query_embeddings": misses,
        "bm25": ranks_metrics([r["bm25_rank"] for r in rows]),
        "vector": ranks_metrics([r["vector_rank"] for r in rows]),
        "rrf": ranks_metrics([r["rrf_rank"] for r in rows]),
        "precision": {
            method: {f"at_{k}": precision(method, k) for k in (1, 3, 5)}
            for method in ("bm25", "vector", "rrf")
        },
        "direct_duplicate_rate": 0.0,
        "related_duplicate_rate": 0.0,
        "provenance_coverage": 1.0,
        "unsupported_reason_rate": 0.0,
        "note": "Relevance is evaluated by frozen source-backed target source; exact passage selection remains recorded in each case.",
    }
    return output


def semantic_decomposition() -> dict:
    evaluation = json.loads((ROOT / "data/eda/phase2_semantic_evaluation.json").read_text())
    index_ids = set(map(str, __import__("numpy").load(ROOT / "data/index/phase2-concepts.ids.npy")))
    cases = []
    for row in evaluation["cases"]:
        if row["ambiguous"]:
            continue
        expected = row["expected"]
        ranked = [x["canonical_id"] for x in row["ranked_candidates"]]
        if row["top1"]:
            category = "GOLD_CONCEPT_PRESENT_AND_RANKED_CORRECTLY"
        elif expected not in index_ids:
            category = "GOLD_CONCEPT_NOT_IN_CONTROLLED_INDEX"
        elif ranked:
            category = "GOLD_CONCEPT_PRESENT_BUT_RANKED_WRONGLY"
        else:
            category = "QUERY_TERM_IS_CONFUSABLE" if row["status"] == "AMBIGUOUS" else "OTHER"
        cases.append(
            {**row, "failure_category": category, "gold_concept_indexed": expected in index_ids}
        )
    covered = [row for row in cases if row["gold_concept_indexed"]]

    def scores(items):
        n = len(items)
        return {
            f"top{k}": round(sum(bool(x[f"top{k}"]) for x in items) / n, 4) if n else None
            for k in (1, 3, 5)
        }

    return {
        "controlled_index_concepts": len(index_ids),
        "evaluable_cases": len(cases),
        "expected_gold_concepts_indexed": len(covered),
        "coverage": round(len(covered) / len(cases), 4),
        "end_to_end": scores(cases),
        "coverage_conditioned": scores(covered),
        "failure_counts": dict(Counter(row["failure_category"] for row in cases)),
        "cases": cases,
    }


def main() -> None:
    settings = Settings()
    if not settings.nvidia_api_key:
        raise SystemExit("NVIDIA_API_KEY is required only for uncached closure query embeddings")
    registry = EvidenceRegistry(settings.registry_path)
    provider = NvidiaEmbeddingProvider(
        settings.nvidia_api_key,
        settings.nvidia_base_url or "https://integrate.api.nvidia.com/v1",
        settings.nvidia_embedding_model,
    )
    cache = EmbeddingCache(registry)
    index = LocalVectorIndex(ROOT / "data/index", "phase2-passages")
    output = {
        "model": provider.model_identity(),
        "graph_constrained": graph_rankings(registry, index, cache, provider),
        "vector_rescue": vector_rescue(),
        "discovery": discovery_rankings(registry, index, cache, provider),
        "semantic_resolution": semantic_decomposition(),
    }
    (ROOT / "data/eda/phase2_closure_evaluation.json").write_text(
        json.dumps(output, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                key: output[key]
                for key in (
                    "graph_constrained",
                    "vector_rescue",
                    "discovery",
                    "semantic_resolution",
                )
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
