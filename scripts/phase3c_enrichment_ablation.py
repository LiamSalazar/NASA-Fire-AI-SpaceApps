"""Objective canonical association coverage and bounded live A--E pilot."""

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
from nasa_fire_ai.query.v2 import QueryIntentV2

ART = ROOT / "artifacts"


def main():
    out = ART / "phase3c_enrichment_ablation_v1.jsonl"
    if out.exists():
        raise FileExistsError(out)
    settings = Settings()
    evidence = EvidenceRegistry(settings.registry_path)
    language = yaml.safe_load((ROOT / "domain/query_language_v2.yaml").read_text())
    os.environ["ONTOLOGY_GRAPH_ENRICHMENT_ENABLED"] = "true"
    os.environ["SOURCE_KNOWLEDGE_ENRICHMENT_ENABLED"] = "false"
    exact = project_legacy(ROOT, evidence)
    os.environ["SOURCE_KNOWLEDGE_ENRICHMENT_ENABLED"] = "true"
    enriched = project_legacy(ROOT, evidence)
    events = ART / "phase3c_enrichment_ablation_api_calls_v1.jsonl"

    def record_event(row):
        with events.open("a") as handle:
            handle.write(json.dumps(row) + "\n")

    def jev_advisor(passage):
        started = perf_counter()
        response = classify_epistemic(passage)
        label, confidence = decision_value(response, "epistemic_type")
        row = {
            "event_type": "jev_advisory",
            "new_calls": 1,
            "execution_mode": "NEW_INFERENCE",
            "evidence_id": passage["evidence_id"],
            "response": response,
            "latency_ms": (perf_counter() - started) * 1000,
        }
        record_event(row)
        return {"label": label, "confidence": confidence, "response": response}

    adapter = NvidiaStructuredClient(
        settings.nvidia_api_key, settings.nvidia_base_url, settings.nvidia_phase3_model
    )
    reasoner = NemotronControlledReasoner(
        adapter.client, settings.nvidia_phase3_model, enriched.registry, language, record_event
    )
    source_cases = json.loads((ART / "phase3c_related_cases_v1.json").read_text())
    # Source-backed objective identity regressions and one ambiguity case; unchanged frozen intent.
    cases = [c for c in source_cases if c["case_id"] in {"qi03", "qi14", "qi19"}]
    for case in cases:
        query, intent = case["query"], QueryIntentV2.model_validate(case["intent"])
        for variant in "ABCDE":
            flags = ControlledReasoningFlags(
                hierarchical_retrieval=variant != "A",
                relational_related=variant != "A",
                query_expansion=variant in "CDE",
                contextual_reranking=variant in "DE",
                selective_reranking=True,
                jev_advisory_triage=variant == "E",
            )
            started = perf_counter()
            result = run_ablation(
                query,
                intent,
                exact if variant == "A" else enriched,
                evidence,
                reasoner,
                flags,
                jev_advisor=jev_advisor,
                baseline_limit=40,
                per_query_limit=40,
            )
            elapsed = (perf_counter() - started) * 1000
            result.pop("_native_execution", None)
            result["bundle"] = result["bundle"].model_dump(mode="json")
            final = result["configurations"]["D"]
            ids = final["candidate_ids"][:40]
            row = {
                "case_id": case["case_id"],
                "variant": variant,
                "query": query,
                "candidate_budget": 40,
                "candidate_ids": ids,
                "required_identity_recovered": bool(
                    set(case.get("expected_evidence_ids", [])) & set(ids)
                )
                if case.get("objective_identity_case")
                else None,
                "false_direct_on_no_direct": bool(result["native_direct_ids"])
                if case.get("objective_no_direct")
                else None,
                "independent_relevance_label": None,
                "user_perceived_latency_ms": elapsed,
                "receipt": result,
            }
            with out.open("a") as handle:
                handle.write(json.dumps(row) + "\n")
            print(
                json.dumps({"case_id": case["case_id"], "variant": variant, "latency_ms": elapsed}),
                flush=True,
            )


if __name__ == "__main__":
    main()
