"""Fixed-budget context reranking pilot; input support never changes eligibility."""

import json
import os
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from phase3c_fidelity_campaign import stores

from nasa_fire_ai.config import Settings
from nasa_fire_ai.evaluation.phase3c import append_result, freeze_json
from nasa_fire_ai.ingestion.semantic import project_legacy
from nasa_fire_ai.llm.interfaces import NvidiaStructuredClient
from nasa_fire_ai.query.controlled_reasoning import NemotronControlledReasoner
from nasa_fire_ai.query.native_interpreter import MinimalInterpretationV2, resolve_minimal


def main():
    path = ROOT / "artifacts/phase3c_fidelity_context_pilot_v2.json"
    if path.exists():
        print({"execution": "CACHED_REPLAY", "receipt": str(path.relative_to(ROOT))})
        return
    evidence, _ = stores()
    os.environ["NATIVE_SOURCE_CONTEXT_VALIDATION_ENABLED"] = "true"
    store = project_legacy(ROOT, evidence)
    language = yaml.safe_load((ROOT / "domain/query_language_v2.yaml").read_text())
    sources = json.loads(
        (ROOT / "artifacts/phase3c_fidelity_documentary_sources_v3.json").read_text()
    )
    query = "What has NASA reported about suppressing PMMA fires in microgravity?"
    intent = resolve_minimal(MinimalInterpretationV2(), store.registry, language, query=query)
    candidates = [
        {
            "evidence_id": eid,
            "text": r["exact_supporting_source_span"]["span"],
            "source_context": r["source_page_text"],
            "source_metadata": r["source"],
            "structured_location": evidence.resolve(eid).get("structured_location"),
            "epistemic_type": "UNADJUDICATED",
        }
        for eid, r in sources.items()
    ]
    settings = Settings()
    client = NvidiaStructuredClient(
        settings.nvidia_api_key, settings.nvidia_base_url, settings.nvidia_phase3_model
    )

    def log(event):
        append_result(ROOT / "artifacts/phase3c_fidelity_pilot_calls_v2.jsonl", event)

    reasoner = NemotronControlledReasoner(
        client.client, settings.nvidia_phase3_model, store.registry, language, log
    )
    output = reasoner.rerank(query, intent, candidates)
    freeze_json(
        path,
        {
            "query": query,
            "intent": intent.model_dump(mode="json"),
            "source_refs": list(sources),
            "candidate_budget": 4,
            "new_raw_sources": 0,
            "D_deterministic_order": [c["evidence_id"] for c in candidates],
            "E_contextual_model": output,
            "F_jev": "NOT_EXECUTED; existing rhetorical proposals do not resolve gravity applicability",
            "input_contains_original_page_context": True,
            "v1_harness_limitation": "v1 supplied source_context but the v4 adapter omitted that field; v1's context declaration was inaccurate. v2 passes registered source context through the actual adapter.",
            "scientific_incremental_precision": "NOT_MEASURABLE",
            "canonical_eligibility_changes": 0,
            "scientific_labels": 0,
        },
    )
    print(
        {
            "status": output.get("error") or "SUCCESS",
            "new_calls": output.get("new_calls"),
            "usage": output.get("usage"),
        },
        flush=True,
    )


if __name__ == "__main__":
    main()
