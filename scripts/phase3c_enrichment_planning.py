"""Two bounded proposal calls; unknown identity and routes never create facts."""

import hashlib
import json
import os
import sys
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.knowledge import normalize_mention
from nasa_fire_ai.ingestion.semantic import project_legacy
from nasa_fire_ai.llm.interfaces import NvidiaStructuredClient
from nasa_fire_ai.query.controlled_reasoning import NemotronControlledReasoner
from nasa_fire_ai.query.ontology_navigation import RouteStep


def main():
    out = ROOT / "artifacts/phase3c_enrichment_planning_v1.jsonl"
    if out.exists():
        raise FileExistsError(out)
    os.environ["ONTOLOGY_GRAPH_ENRICHMENT_ENABLED"] = "true"
    os.environ["SOURCE_KNOWLEDGE_ENRICHMENT_ENABLED"] = "true"
    settings = Settings()
    evidence = EvidenceRegistry(settings.registry_path)
    store = project_legacy(ROOT, evidence)
    adapter = NvidiaStructuredClient(
        settings.nvidia_api_key, settings.nvidia_base_url, settings.nvidia_phase3_model
    )
    reasoner = NemotronControlledReasoner(
        adapter.client, settings.nvidia_phase3_model, store.registry
    )
    sample = next(s for s in store.source_enrichment_report["specimens"] if s["identity"] is None)
    material = store.source_enrichment_report["additional_materials"][0]
    tasks = [
        (
            "normalization",
            'Return JSON {"material_mention":string,"unresolved":list}. Identify only a literal material name in the source label; do not guess polymer identity from geometry or color. Empty mention if unsupported.',
            sample["original_description"],
        ),
        (
            "graph_path",
            'Return JSON {"steps":[{"relation":string,"direction":"FORWARD"}]}. Propose a route to the material of the given specimen, using only declared relations. No invented relations or causality.',
            json.dumps(
                {
                    "start": material["sample_id"],
                    "declared_relations": sorted(store.registry.relations),
                    "goal": "material of specimen",
                }
            ),
        ),
    ]
    for component, system, text in tasks:
        started = perf_counter()
        row = {
            "provider": "NVIDIA",
            "component": component,
            "new_calls": 1,
            "replayed_calls": 0,
            "input": text,
            "input_digest": hashlib.sha256(text.encode()).hexdigest(),
            "prompt_version": "enrichment-planning-v1",
            "model": settings.nvidia_phase3_model,
            "publication_status": "REVIEW_REQUIRED",
        }
        try:
            output, usage = reasoner._json_call(system, text, 300)
            row.update(output=output, usage=usage, status="PASS")
            if component == "graph_path":
                row["verified_navigation"] = store.explore_route(
                    material["sample_id"], [RouteStep(**s) for s in output["steps"]], evidence
                )
            else:
                mention = output.get("material_mention", "")
                row["literal_mention_valid"] = bool(mention and mention in text)
                row["resolution"] = normalize_mention(
                    text, {m: [m] for m in store.registry.entity_mentions}
                )
                row["canonical_identity_added"] = False
        except Exception as exc:  # noqa: BLE001
            row.update(status="FAIL", error=type(exc).__name__)
        row["latency_ms"] = (perf_counter() - started) * 1000
        with out.open("a") as handle:
            handle.write(json.dumps(row) + "\n")
        print(json.dumps({"component": component, "status": row["status"]}), flush=True)


if __name__ == "__main__":
    main()
