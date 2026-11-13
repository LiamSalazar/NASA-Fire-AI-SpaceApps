"""Real corpus examples and component errors; no scientific authority from model scores."""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.semantic import project_legacy
from nasa_fire_ai.query.native import execute_native
from nasa_fire_ai.query.ontology_navigation import RouteStep
from nasa_fire_ai.query.v2 import (
    EntityConstraintV2,
    GenericValue,
    PropertyConstraintV2,
    QueryIntentV2,
)


def main():
    out = ROOT / "artifacts/phase3c_enrichment_scientific_examples_v1.json"
    if out.exists():
        raise FileExistsError(out)
    os.environ["ONTOLOGY_GRAPH_ENRICHMENT_ENABLED"] = "true"
    os.environ["SOURCE_KNOWLEDGE_ENRICHMENT_ENABLED"] = "true"
    evidence = EvidenceRegistry(ROOT / "data/index/evidence.sqlite")
    store = project_legacy(ROOT, evidence)
    row = next(
        r
        for r in store.source_enrichment_report["mapped"]
        if r["original"]["kind"] == "initial_droplet_diameter"
    )
    subject = store.payload(row["record_id"])["subject"]
    q = QueryIntentV2(
        targets=["ExperimentalRun"],
        entity_constraints=[EntityConstraintV2(relation="hasMaterial", entity_id="Methanol")],
        property_constraints=[
            PropertyConstraintV2(
                property_id=row["property_id"],
                operator="EQ",
                value=GenericValue(
                    reported_value=row["original"]["reported_value"],
                    reported_unit=row["original"]["reported_unit"],
                ),
            )
        ],
    )
    result = execute_native(
        q,
        "Find Methanol experiments with initial droplet diameter "
        + str(row["original"]["reported_value"])
        + " mm",
        store,
        evidence,
    )
    eid = row["original"]["evidence_refs"][0]["evidence_id"]
    examples = [
        {
            "example": "FLEX typed field access",
            "source": evidence.source_metadata(eid),
            "evidence": evidence.resolve(eid),
            "canonical_original": row["original"],
            "query_intent": q.model_dump(mode="json"),
            "subject_recovered_direct": any(
                x["id"] == subject for x in result.bundle.direct_evidence
            ),
            "ontology_mapping": {
                "predicate": "conditionType/value",
                "source_field": row["original"]["kind"],
                "role": "INITIAL_SPECIMEN_CHARACTERISTIC",
            },
            "interpretation": "Reported initial specimen characteristic, not extinction diameter or newly verified observation.",
        }
    ]
    q = QueryIntentV2(
        targets=["ExperimentalRun"],
        entity_constraints=[EntityConstraintV2(relation="hasMaterial", entity_id="SIBAL Fabric")],
        property_constraints=[
            PropertyConstraintV2(
                property_id="AirflowVelocity",
                operator="EQ",
                value=GenericValue(reported_value=30, reported_unit="cm/s"),
            )
        ],
        source_constraints=["psi-98"],
    )
    result = execute_native(
        q,
        "Find SIBAL experiments at airflow velocity 30 cm/s",
        store,
        evidence,
        hierarchical=True,
        relational=True,
    )
    examples.append(
        {
            "example": "Same material different specified airflow",
            "query_intent": q.model_dump(mode="json"),
            "direct": result.bundle.direct_evidence,
            "related": result.bundle.related_evidence,
            "sources": [
                {"source": evidence.source_metadata(p["evidence_id"]), "passage": p}
                for p in result.bundle.evidence_passages
            ],
            "limits": "Source table condition context retained; no assertion of measured airflow response.",
        }
    )
    for name, eid, interpretation in [
        (
            "SoFIE acrylic nomenclature",
            "E-751f8e0f5230aa68",
            "Documentary fuel description supports context; no acrylic family equivalence or experimental behavior transfer.",
        ),
        (
            "Saffire observation",
            "E-safety-saffire-observation",
            "Explicit observed fire behavior; active suppression implications remain separate.",
        ),
        (
            "Open question antecedent",
            "E-ae9ebc14b3783086",
            "Source context contains question wording; its status as a NASA-identified open scientific question needs review.",
        ),
    ]:
        examples.append(
            {
                "example": name,
                "source": evidence.source_metadata(eid),
                "evidence": evidence.resolve(eid),
                "physical_pdf_page_verified": False,
                "interpretation": interpretation,
            }
        )
    material = store.source_enrichment_report["additional_materials"][0]
    examples.append(
        {
            "example": "Native specimen-to-material association",
            "route": store.explore_route(material["sample_id"], [RouteStep("madeOf")], evidence),
            "limits": "Association is not hierarchy, causal support or applicability.",
        }
    )
    unknown = next(r for r in store.source_enrichment_report["specimens"] if r["identity"] is None)
    examples.append(
        {
            "example": "Unresolved specimen",
            "record": unknown,
            "publication_status": "REVIEW_REQUIRED",
        }
    )
    out.write_text(json.dumps(examples, indent=2))
    errors = []
    for line in (ROOT / "artifacts/phase3c_enrichment_live_v1.jsonl").read_text().splitlines():
        row = json.loads(line)
        for rejection in row.get("rejected", []):
            errors.append(
                {
                    "component": "extraction",
                    "evidence_id": row["evidence_id"],
                    "type": "LLM_SOURCE_SPAN_OR_MENTION_FAILURE",
                    "severity": "HIGH_IF_PUBLISHED",
                    "actual_effect": "REJECTED_NO_CANONICAL_PUBLICATION",
                    "details": rejection,
                }
            )
    errors.extend(
        [
            {
                "component": "exploratory_planning",
                "case_id": "qi19",
                "type": "SEMANTIC_SCOPE_ADDITION",
                "severity": "MODERATE",
                "actual_effect": "Initial equivalent expansion accepted; revised validator rejects; canonical intent unchanged.",
            },
            {
                "component": "graph_path_planning",
                "type": "UNSUPPORTED_ENDPOINT_RELATION",
                "severity": "MODERATE",
                "actual_effect": "Model selected hasMaterial for a specimen; no such edge exists. Native route returns zero results, no invented edge.",
            },
            {
                "component": "reranking",
                "type": "MISSING_SUPPORTING_SPAN",
                "severity": "MODERATE",
                "actual_effect": "One judgment rejected.",
            },
            {
                "component": "epistemic_contract",
                "case_id": "qi49",
                "type": "LEGACY_AMBIGUITY_LOSS",
                "severity": "HIGH_IF_ATTRIBUTED",
                "actual_effect": "Historical conversion retrieves PMMA runs for an equivalence question. Native validated intent retains ambiguity; contract review pending.",
            },
        ]
    )
    (ROOT / "artifacts/phase3c_enrichment_errors_v1.json").write_text(
        json.dumps(
            {
                "observed": errors,
                "false_family_relations_published": 0,
                "new_measured_observations_from_design": 0,
                "invalid_canonical_evidence_references": 0,
                "independent_related_relevance_errors": "UNMEASURED",
                "review_required": [
                    "CO versus CO2",
                    "burning rate units",
                    "supportedBy semantics",
                    "93 specimen identities",
                    "epistemic and expanded-candidate usefulness",
                ],
            },
            indent=2,
        )
    )
    print(json.dumps({"examples": len(examples), "errors": len(errors)}))


if __name__ == "__main__":
    main()
