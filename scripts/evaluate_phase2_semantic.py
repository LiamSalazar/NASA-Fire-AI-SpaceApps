#!/usr/bin/env python3
"""Evaluate frozen semantic seed without converting vector candidates to identity."""

import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.retrieval.semantic import (
    EmbeddingCache,
    LocalVectorIndex,
    NvidiaEmbeddingProvider,
    semantic_resolve,
)


def main() -> None:
    settings = Settings()
    if not settings.nvidia_api_key:
        raise SystemExit("NVIDIA_API_KEY is required for live semantic evaluation")
    seed = yaml.safe_load((ROOT / "evals/phase1_5_semantic_resolution.yaml").read_text())[
        "examples"
    ]
    registry = EvidenceRegistry(settings.registry_path)
    provider = NvidiaEmbeddingProvider(
        settings.nvidia_api_key,
        settings.nvidia_base_url or "https://integrate.api.nvidia.com/v1",
        settings.nvidia_embedding_model,
    )
    index = LocalVectorIndex(ROOT / "data/index", "phase2-concepts")
    cache = EmbeddingCache(registry)
    rows = []
    for item in seed:
        result = semantic_resolve(item["phrase"], index, provider, cache, 5)
        ranked = result.canonical_ids or [x["canonical_id"] for x in result.candidates]
        expected = item["canonical_concept"]
        rows.append(
            {
                "phrase": item["phrase"],
                "ambiguous": item["ambiguous"],
                "expected": expected,
                "status": result.status,
                "ranked_candidates": result.candidates,
                "top1": ranked[:1] == [expected] if expected else None,
                "top3": expected in ranked[:3] if expected else None,
                "top5": expected in ranked[:5] if expected else None,
            }
        )
    unambiguous = [r for r in rows if not r["ambiguous"] and r["expected"]]

    def score(key):
        return (
            round(sum(r[key] for r in unambiguous) / len(unambiguous), 4) if unambiguous else None
        )

    out = {
        "model": provider.model_identity(),
        "cases": rows,
        "unambiguous_cases": len(unambiguous),
        "top1": score("top1"),
        "top3": score("top3"),
        "top5": score("top5"),
    }
    (ROOT / "data/eda/phase2_semantic_evaluation.json").write_text(json.dumps(out, indent=2) + "\n")
    print(
        json.dumps(
            {k: out[k] for k in ("model", "unambiguous_cases", "top1", "top3", "top5")}, indent=2
        )
    )


if __name__ == "__main__":
    main()
