"""One uncertain source-report query, bounded A-F corpus-explicit live pilot."""

import json
import os
import sys
from pathlib import Path
from time import perf_counter

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.semantic import project_legacy
from nasa_fire_ai.llm.interfaces import NvidiaStructuredClient
from nasa_fire_ai.llm.jev import classify_epistemic, decision_value
from nasa_fire_ai.query.controlled_reasoning import (
    ControlledReasoningFlags,
    NemotronControlledReasoner,
    run_ablation,
)
from nasa_fire_ai.query.native_interpreter import MinimalInterpretationV2, resolve_minimal


def main():
    out = ROOT / "artifacts/phase3c_targeted_ablation_v1.jsonl"
    assert not out.exists()
    event_path = ROOT / "artifacts/phase3c_targeted_ablation_calls_v1.jsonl"
    settings = Settings()
    existing = EvidenceRegistry(ROOT / "data/index/phase3c_targeted_existing_snapshot_v1.sqlite")
    current = EvidenceRegistry(settings.registry_path)
    language = yaml.safe_load((ROOT / "domain/query_language_v2.yaml").read_text())
    os.environ["ONTOLOGY_GRAPH_ENRICHMENT_ENABLED"] = "true"
    os.environ["FLEX_SOURCE_CORRECTIONS_ENABLED"] = "false"
    graphs = {}
    for name, source_enrichment, publish, registry in [
        ("A", False, False, existing),
        ("B", True, False, existing),
        ("C", True, True, current),
    ]:
        os.environ["SOURCE_KNOWLEDGE_ENRICHMENT_ENABLED"] = str(source_enrichment).lower()
        os.environ["PSI_STRUCTURED_PUBLICATION_ENABLED"] = str(publish).lower()
        graphs[name] = project_legacy(ROOT, registry)
    query = "What has NASA reported about suppressing PMMA fires in microgravity?"
    intent = resolve_minimal(MinimalInterpretationV2(), graphs["C"].registry, language, query=query)

    def log(event):
        with event_path.open("a") as handle:
            handle.write(json.dumps(event) + "\n")

    def jev(passage):
        started = perf_counter()
        response = classify_epistemic(passage)
        label, confidence = decision_value(response, "epistemic_type")
        log(
            {
                "event_type": "jev_advisory",
                "execution_mode": "NEW_INFERENCE",
                "new_calls": 1,
                "evidence_id": passage["evidence_id"],
                "response": response,
                "latency_ms": (perf_counter() - started) * 1000,
            }
        )
        return {"label": label, "confidence": confidence, "response": response}

    adapter = NvidiaStructuredClient(
        settings.nvidia_api_key, settings.nvidia_base_url, settings.nvidia_phase3_model
    )
    reasoner = NemotronControlledReasoner(
        adapter.client, settings.nvidia_phase3_model, graphs["C"].registry, language, log
    )
    for variant in "ABCDEF":
        flags = ControlledReasoningFlags(
            hierarchical_retrieval=True,
            relational_related=True,
            query_expansion=variant in "DEF",
            contextual_reranking=variant in "EF",
            selective_reranking=True,
            jev_advisory_triage=variant == "F",
        )
        graph = graphs[variant] if variant in "ABC" else graphs["C"]
        registry = existing if variant in "AB" else current
        started = perf_counter()
        result = run_ablation(
            query,
            intent,
            graph,
            registry,
            reasoner,
            flags,
            jev_advisor=jev,
            baseline_limit=20,
            per_query_limit=20,
        )
        result.pop("_native_execution", None)
        result["bundle"] = result["bundle"].model_dump(mode="json")
        row = {
            "variant": variant,
            "query": query,
            "intent": intent.model_dump(mode="json"),
            "candidate_budget": 20,
            "corpus": "pre-publication 6055 passages"
            if variant in "AB"
            else "existing plus validated PSI tables and PDF locators",
            "new_raw_sources": 0,
            "scientific_precision": "NOT_MEASURABLE",
            "latency_ms": (perf_counter() - started) * 1000,
            "receipt": result,
        }
        with out.open("a") as handle:
            handle.write(json.dumps(row) + "\n")
        print({"variant": variant, "latency_ms": row["latency_ms"]}, flush=True)


if __name__ == "__main__":
    main()
