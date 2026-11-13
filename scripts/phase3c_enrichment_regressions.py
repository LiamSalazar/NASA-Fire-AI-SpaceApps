"""Fresh same-source objective evaluation, preserving interpreter gold and historical receipts."""

import importlib.util
import json
import os
import sys
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.semantic import project_legacy
from nasa_fire_ai.query.native import classify_native, execute_native
from nasa_fire_ai.query.ontology_navigation import RouteStep
from nasa_fire_ai.query.v2 import GenericValue, PropertyConstraintV2, QueryIntentV2


def main():
    art = ROOT / "artifacts"
    out = art / "phase3c_enrichment_regressions_v1.json"
    if out.exists():
        raise FileExistsError(out)
    evidence = EvidenceRegistry(ROOT / "data/index/evidence.sqlite")
    os.environ["ONTOLOGY_GRAPH_ENRICHMENT_ENABLED"] = "true"
    os.environ["SOURCE_KNOWLEDGE_ENRICHMENT_ENABLED"] = "false"
    before = project_legacy(ROOT, evidence)
    os.environ["SOURCE_KNOWLEDGE_ENRICHMENT_ENABLED"] = "true"
    after = project_legacy(ROOT, evidence)
    field_cases = []
    for row in after.source_enrichment_report["mapped"]:
        subject = after.payload(row["record_id"])["subject"]
        q = QueryIntentV2(
            property_constraints=[
                PropertyConstraintV2(
                    property_id=row["property_id"],
                    operator="EQ",
                    value=GenericValue(
                        reported_value=row["original"]["reported_value"],
                        reported_unit=row["original"]["reported_unit"],
                    ),
                )
            ]
        )
        status = classify_native(subject, q, after)[0]
        field_cases.append(
            {
                "record_id": row["record_id"],
                "subject": subject,
                "property_id": row["property_id"],
                "expected_value": row["original"]["reported_value"],
                "expected_unit": row["original"]["reported_unit"],
                "before_registered": row["property_id"] in before.registry.properties,
                "after_classification": status,
                "expected_role": row["qualifiers"]["role"],
                "evidence_ids": row["original"]["evidence_refs"],
                "is_observed_measurement": False,
            }
        )
    regressions = []
    for case in json.loads((art / "phase3c_related_cases_v1.json").read_text()):
        q = QueryIntentV2.model_validate(case["intent"])
        row = {
            "case_id": case["case_id"],
            "query": case["query"],
            "frozen_intent": case["intent"],
            "variants": {},
        }
        for label, store in [("A", before), ("B", after)]:
            os.environ["SOURCE_KNOWLEDGE_ENRICHMENT_ENABLED"] = "true" if label == "B" else "false"
            started = perf_counter()
            result = execute_native(
                q, case["query"], store, evidence, hierarchical=True, relational=True
            )
            ids = [p["evidence_id"] for p in result.bundle.evidence_passages]
            row["variants"][label] = {
                "direct": [i["id"] for i in result.bundle.direct_evidence],
                "related": [i["id"] for i in result.bundle.related_evidence],
                "evidence_ids": ids,
                "identity_recovered": bool(set(ids) & set(case.get("expected_evidence_ids", [])))
                if case.get("objective_identity_case")
                else None,
                "false_direct": bool(result.bundle.direct_evidence)
                if case.get("objective_no_direct")
                else None,
                "latency_ms": (perf_counter() - started) * 1000,
                "information_trace": result.bundle.retrieval_metadata.get("information_selection"),
            }
        regressions.append(row)
    sample = after.source_enrichment_report["additional_materials"][0]["sample_id"]
    route = after.explore_route(sample, [RouteStep("madeOf")], evidence)
    intervention = (
        after.explore_route("saffire-suppression-intervention", [RouteStep("observedIn")], evidence)
        if "observedIn" in after.registry.relations
        else {"status": "UNSUPPORTED_ROUTE_NO_NEW_EDGE"}
    )
    native_source = ROOT / "scripts/phase3c_native_benchmarks.py"
    spec = importlib.util.spec_from_file_location("fresh_enrichment_native", native_source)
    campaign = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(campaign)
    campaign.ART = art / "phase3c_enrichment_native_checks_v1"
    campaign.ART.mkdir()
    campaign.check_freeze = lambda: None
    os.environ["ONTOLOGY_GRAPH_ENRICHMENT_ENABLED"] = "false"
    os.environ["SOURCE_KNOWLEDGE_ENRICHMENT_ENABLED"] = "false"
    campaign.dynamic()
    campaign.dynamic(postfreeze=True)
    campaign.parity()
    campaign.ART = art / "phase3c_enrichment_native_checks_v2"
    campaign.ART.mkdir()
    os.environ["ONTOLOGY_GRAPH_ENRICHMENT_ENABLED"] = "true"
    os.environ["SOURCE_KNOWLEDGE_ENRICHMENT_ENABLED"] = "true"
    campaign.parity()
    out.write_text(
        json.dumps(
            {
                "field_cases": field_cases,
                "source_field_recovery": {
                    "numerator": sum(r["after_classification"] == "DIRECT" for r in field_cases),
                    "denominator": len(field_cases),
                    "scope": "Technical canonical source-field access; not independent scientific accuracy",
                },
                "cases": regressions,
                "graph_routes": {
                    "sample_material": route,
                    "unsupported_observation_route": intervention,
                },
                "gold_modified": False,
            },
            indent=2,
        )
    )
    print(json.dumps({"fields": len(field_cases), "cases": len(regressions)}))


if __name__ == "__main__":
    main()
