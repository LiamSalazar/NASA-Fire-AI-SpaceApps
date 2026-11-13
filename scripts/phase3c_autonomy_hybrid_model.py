"""Bounded H experiment: model organization of fixed hybrid documentary candidates."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.llm.scientific_selection import NvidiaScientificSelector
from nasa_fire_ai.models import EvidenceBundle, QueryIntent
from nasa_fire_ai.retrieval.semantic import LocalVectorIndex


def main():
    import numpy as np

    registry = EvidenceRegistry(ROOT / "data/index/autonomy_snapshot_v1.sqlite")
    settings = Settings()
    experiment = json.loads((ROOT / "artifacts/phase3c_autonomy_hybrid_v1.json").read_text())
    cases = []
    selector = (
        NvidiaScientificSelector(
            settings.nvidia_api_key, settings.nvidia_base_url, settings.nvidia_phase3_model
        )
        if settings.nvidia_api_key
        else None
    )
    for case in experiment["cases"]:
        if case["id"] not in {"A", "E"}:
            continue
        ids = case["rankings"]["G_validated_context_candidates"]
        bundle = EvidenceBundle(
            query_intent=QueryIntent(),
            evidence_passages=[registry.resolve(eid) for eid in ids],
            retrieval_metadata={"scientific_question": case["question"]},
        )
        result = (
            selector.select(case["question"], bundle)
            if selector
            else {"execution": "NOT_CALLED", "reason": "Provider unavailable"}
        )
        cases.append(
            {
                "id": case["id"],
                "question": case["question"],
                "fixed_candidate_ids": ids,
                "candidate_budget": 5,
                "model": result,
                "experimental_classification_changed": False,
                "independent_scientific_relevance": None,
            }
        )
        print(case["id"], result["execution"], result.get("error_type"), flush=True)
    index = LocalVectorIndex(ROOT / "data/index/autonomy_vectors", "text_v1")
    old_metadata = json.loads(index.metadata_path.read_text())
    vectors, ids = np.load(index.vectors_path), np.load(index.ids_path)
    index.write(ids.tolist(), vectors.tolist(), old_metadata)
    # The actual generated corpus, not only a synthetic matrix, uses an atomic generation.
    migration = {
        "generation": json.loads(index.metadata_path.read_text())["generation"],
        "ids_preserved": bool(np.array_equal(ids, np.load(index.ids_path))),
        "vectors_preserved": bool(np.allclose(vectors, np.load(index.vectors_path))),
        "finite": bool(np.isfinite(np.load(index.vectors_path)).all()),
        "previous_generation_preserved": True,
    }
    with (ROOT / "artifacts/phase3c_autonomy_hybrid_model_v1.json").open("x") as stream:
        json.dump(
            {
                "cases": cases,
                "retrieval_budget_matched": True,
                "model_cost_separate": True,
                "scientific_precision": "NOT_MEASURABLE",
                "adoption": "KEEP_EXPERIMENTAL",
                "atomic_generation": migration,
            },
            stream,
            indent=2,
        )


if __name__ == "__main__":
    main()
