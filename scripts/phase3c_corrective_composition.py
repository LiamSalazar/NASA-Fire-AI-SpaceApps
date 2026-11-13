"""Intent-first novel compositions; frozen templates are not expert relevance gold."""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import yaml
from openai import OpenAI, OpenAIError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from phase3c_corrective_live import MODEL, check_freeze, rows
from phase3c_live import summarize

from nasa_fire_ai.evaluation.phase3c import append_result, digest, freeze_json
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.semantic import project_legacy
from nasa_fire_ai.query.native_interpreter import (
    SYSTEM_PROMPT,
    MinimalInterpretationV2,
    resolve_minimal,
)
from nasa_fire_ai.query.v2 import QueryIntentV2

GOLD = ROOT / "evals/phase3c_corrective_compositional_gold_v1.json"
VERSION = "v2" if "--retry-failures" in sys.argv else "v1"
OUT = ROOT / f"artifacts/phase3c_corrective_compositional_results_{VERSION}.jsonl"


def prepare(store):
    cases = []
    for variant in range(3):
        material = ["PMMA", "SIBAL Fabric", "PMMA"][variant]
        n = [0.08, 0.12, 0.2][variant]
        entity = {"relation": "hasMaterial", "entity_id": material}
        gravity = {"relation": "hasGravityCondition", "entity_id": "microgravity"}
        investigation = {"relation": "belongsToInvestigation", "entity_id": "psi-98"}
        numeric = {
            "property_id": "AirflowVelocity",
            "operator": "LTE",
            "value": {"reported_value": n, "reported_unit": "m/s"},
        }
        oxygen = {
            "property_id": "OxygenConcentration",
            "operator": "BETWEEN",
            "value": {"lower": 21.5, "upper": 21.7, "reported_unit": "%"},
        }
        approximate = {
            "property_id": "AirflowVelocity",
            "operator": "APPROX",
            "value": {"reported_value": n, "reported_unit": "m/s", "approximate": True},
        }
        patterns = [
            (
                "publication_material_gravity",
                {
                    "targets": ["Publication"],
                    "entity_constraints": [entity, gravity],
                    "requested_information": ["Publication"],
                },
                f"Find publications about {material} in microgravity",
            ),
            (
                "measurement_two_properties",
                {
                    "requested_information": ["Measurement"],
                    "entity_constraints": [entity],
                    "property_constraints": [numeric, oxygen],
                },
                f"Find measurements for {material} with airflow no greater than {n} m/s and oxygen between 21.5 and 21.7 percent",
            ),
            (
                "conclusion_investigation_material",
                {
                    "requested_information": ["NASAConclusion"],
                    "entity_constraints": [investigation, entity],
                },
                f"Find NASA conclusions for {material} in Saffire-I",
            ),
            (
                "requirement_numeric_material",
                {
                    "requested_information": ["Requirement"],
                    "entity_constraints": [entity],
                    "property_constraints": [numeric],
                },
                f"Find requirements for {material} at airflow no greater than {n} m/s",
            ),
            (
                "comparison_numeric_investigation",
                {
                    "operation": "COMPARE",
                    "entity_constraints": [investigation],
                    "property_constraints": [numeric],
                    "comparison": {"operands": ["psi-98-S1", "psi-98-S2"]},
                },
                f"Compare Saffire-I S1 and Saffire-I S2 at airflow no greater than {n} m/s",
            ),
            (
                "unknown_known_numeric",
                {
                    "entity_constraints": [entity, gravity],
                    "property_constraints": [numeric],
                    "unresolved_mentions": ["quasarcoat"],
                },
                f"Find {material} experiments in microgravity with airflow no greater than {n} m/s and quasarcoat",
            ),
            (
                "ambiguous_measurement_material",
                {
                    "entity_constraints": [entity],
                    "requested_information": ["Measurement"],
                    "clarification_required": True,
                    "ambiguities": ["velocity"],
                },
                f"Find measurements of velocity for {material}",
            ),
            (
                "approximate_observation_investigation",
                {
                    "entity_constraints": [investigation],
                    "requested_information": ["ReportedObservation"],
                    "property_constraints": [approximate],
                },
                f"Find reported observations in Saffire-I at roughly {n} m/s airflow",
            ),
            (
                "safety_two_properties_gravity",
                {
                    "entity_constraints": [gravity],
                    "requested_information": ["SafetyImplication"],
                    "property_constraints": [numeric, oxygen],
                },
                f"Find NASA safety implications in microgravity with airflow no greater than {n} m/s and oxygen between 21.5 and 21.7 percent",
            ),
            (
                "publication_unknown_material",
                {
                    "targets": ["Publication"],
                    "requested_information": ["Publication"],
                    "entity_constraints": [entity],
                    "unresolved_mentions": ["quasarcoat"],
                },
                f"Find publications about {material} and quasarcoat",
            ),
        ]
        for pattern, fields, query in patterns:
            # Serialize intended semantics first; surface is a fixed deterministic template.
            intent = QueryIntentV2.model_validate({"targets": ["ExperimentalRun"], **fields})
            store.registry.validate_intent(intent)
            cases.append(
                {
                    "id": f"newcomp{len(cases) + 1:02d}",
                    "kind": pattern,
                    "query": query,
                    "expected": intent.model_dump(mode="json"),
                    "supported": True,
                    "review_status": "DETERMINISTIC_TEMPLATE_NOT_EXPERT_REVIEWED",
                }
            )
    freeze_json(
        GOLD,
        {
            "version": "corrective-novel-compositions-v1",
            "cases": cases,
            "patterns": 10,
            "surface_variants": 30,
            "new_vocabulary": 0,
            "label_basis": "Existing approved registry identities and deterministic intended semantics. No model prediction defines gold. This is linguistic execution gold, not source relevance gold.",
        },
    )


def main(live):
    check_freeze()
    store = project_legacy(ROOT, EvidenceRegistry(ROOT / "data/index/evidence.sqlite"))
    if not GOLD.exists():
        prepare(store)
    gold = json.loads(GOLD.read_text())["cases"]
    if not live:
        print("30 intents validated and frozen before prediction")
        return
    language = yaml.safe_load((ROOT / "domain/query_language_v2.yaml").read_text())
    client = OpenAI(
        api_key=os.environ["NVIDIA_API_KEY"],
        base_url="https://integrate.api.nvidia.com/v1",
        timeout=40,
        max_retries=0,
    )
    done = {r["case_id"]: r for r in rows(OUT)}
    if VERSION == "v2":
        # One bounded retry only; preserve the complete first attempt unchanged.
        for row in rows(ROOT / "artifacts/phase3c_corrective_compositional_results_v1.jsonl"):
            if row["semantic_valid"] and row["case_id"] not in done:
                append_result(OUT, {**row, "reused_from": "v1"})
                done[row["case_id"]] = row
    for case in gold:
        if case["id"] in done:
            continue
        row = {
            "case_id": case["id"],
            "query": case["query"],
            "gold_digest": digest(GOLD),
            "model": MODEL,
            "schema_valid": False,
            "semantic_valid": False,
            "fallback": False,
        }
        start = time.perf_counter()
        try:
            response = client.chat.completions.create(
                model=MODEL,
                temperature=0,
                stream=False,
                max_tokens=1000,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": case["query"]},
                ],
                response_format={"type": "json_object"},
                extra_body={"chat_template_kwargs": {"enable_thinking": False}},
            )
            row["minimal_raw_output"] = response.choices[0].message.content
            row["tokens"] = response.usage.model_dump() if response.usage else None
            append_result(
                ROOT / f"artifacts/phase3c_corrective_compositional_receipts_{VERSION}.jsonl", row
            )
            proposal = MinimalInterpretationV2.model_validate_json(row["minimal_raw_output"])
            row["schema_valid"] = True
            intent = resolve_minimal(proposal, store.registry, language, query=case["query"])
            store.registry.validate_intent(intent)
            row["semantic_valid"] = True
            row["resolved_intent"] = intent.model_dump(mode="json")
        except (OpenAIError, ValueError, TypeError, LookupError) as error:
            row["error"] = {
                "type": type(error).__name__,
                "status": getattr(error, "status_code", None),
            }
            row["fallback"] = True
        row["latency_ms"] = (time.perf_counter() - start) * 1000
        append_result(OUT, row)
        print(json.dumps({"case": case["id"], "valid": row["semantic_valid"]}), flush=True)
    freeze_json(
        ROOT / f"artifacts/phase3c_corrective_compositional_summary_{VERSION}.json",
        summarize(gold, rows(OUT)),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--retry-failures", action="store_true")
    main(parser.parse_args().live)
