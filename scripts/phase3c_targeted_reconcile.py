"""Complete frozen parity reconciliation plus current native-resolution probes."""

import json
import os
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.semantic import project_legacy
from nasa_fire_ai.query.native import execute_native
from nasa_fire_ai.query.native_interpreter import MinimalInterpretationV2, resolve_minimal
from nasa_fire_ai.query.v2 import QueryIntentV2


def main():
    existing = EvidenceRegistry(ROOT / "data/index/phase3c_targeted_existing_snapshot_v2.sqlite")
    current = EvidenceRegistry(ROOT / "data/index/evidence.sqlite")
    os.environ["ONTOLOGY_GRAPH_ENRICHMENT_ENABLED"] = "true"
    os.environ["FLEX_SOURCE_CORRECTIONS_ENABLED"] = "false"
    os.environ["PSI_STRUCTURED_PUBLICATION_ENABLED"] = "false"
    os.environ["SOURCE_KNOWLEDGE_ENRICHMENT_ENABLED"] = "false"
    before = project_legacy(ROOT, existing)
    os.environ["SOURCE_KNOWLEDGE_ENRICHMENT_ENABLED"] = "true"
    after = project_legacy(ROOT, existing)
    os.environ["PSI_STRUCTURED_PUBLICATION_ENABLED"] = "true"
    os.environ["FLEX_SOURCE_CORRECTIONS_ENABLED"] = "true"
    published = project_legacy(ROOT, current)
    language = yaml.safe_load((ROOT / "domain/query_language_v2.yaml").read_text())
    history = json.loads(
        (ROOT / "artifacts/phase3c_enrichment_parity_reconciliation_v1.json").read_text()
    )["cases"]
    gold = json.loads((ROOT / "evals/phase3_query_interpreter_gold_reviewed_v1.json").read_text())[
        "cases"
    ]
    results = []
    review = []
    for old in history:
        query = old["query"]
        frozen = QueryIntentV2.model_validate(old["intent"])
        native = resolve_minimal(
            MinimalInterpretationV2(), published.registry, language, query=query
        )
        row = {
            "case_id": old["case_id"],
            "original_query": query,
            "historical_gold": next(g for g in gold if g["id"] == old["case_id"]),
            "frozen_intent": old["intent"],
            "historical_before_direct": old["baseline_v2_direct"],
            "historical_before_related": old["baseline_v2_related"],
            "historical_enriched_direct": old["v2_direct"],
            "historical_enriched_related": old["v2_related"],
            "native_resolution_probe": native.model_dump(mode="json"),
            "native_probe_contract": "raw alias/information discovery with empty linguistic proposal; numeric extraction not exercised",
            "variants": {},
            "independent_scientific_disposition": "UNRESOLVED_PENDING_REVIEW",
        }
        for label, store, registry, intent in [
            ("A", before, existing, frozen),
            ("B", after, existing, frozen),
            ("C", published, current, frozen),
            ("native_C", published, current, native),
        ]:
            result = execute_native(
                intent, query, store, registry, hierarchical=True, relational=True
            )
            row["variants"][label] = {
                "direct": result.bundle.direct_evidence,
                "related": result.bundle.related_evidence,
                "evidence_ids": [p["evidence_id"] for p in result.bundle.evidence_passages],
                "related_groups": result.bundle.retrieval_metadata["related_presentation"],
                "information_selection": result.bundle.retrieval_metadata["selection_trace"],
                "latency_ms": result.latency_ms,
            }
        old_direct = set(old["v2_direct"])
        new_direct = {r["id"] for r in row["variants"]["B"]["direct"]}
        old_related = set(old["v2_related"])
        new_related = {r["id"] for r in row["variants"]["B"]["related"]}
        row["delta_from_historical_enriched"] = {
            "added_direct": sorted(new_direct - old_direct),
            "removed_direct": sorted(old_direct - new_direct),
            "added_related": sorted(new_related - old_related),
            "removed_related": sorted(old_related - new_related),
        }
        for candidate in row["variants"]["B"]["related"]:
            review.append(
                {
                    "case_id": old["case_id"],
                    "query": query,
                    "candidate": candidate,
                    "independent_label": None,
                    "proposal_authority": "TECHNICAL_REVIEW_ONLY",
                    "scientific_relationship_status": "GRAPH_CONSTRAINTS_RECORDED; useful answering value unreviewed",
                    "required_review_dimensions": [
                        "requested_and_actual_material",
                        "phenomenon",
                        "gravity",
                        "numeric_conditions",
                        "measurement_context",
                        "epistemic_type",
                        "provenance",
                        "citation_quality",
                        "claim_applicability",
                        "reason_for_inclusion",
                    ],
                }
            )
        if query.startswith("Does ") and " mean " in query:
            row["technical_disposition"] = (
                "DEMONSTRABLE_CONCEPTUAL_OPERATION_CORRECTION; experimental hits cannot answer terminology"
            )
        elif query == "BASS tests":
            row["technical_disposition"] = (
                "DEMONSTRABLE_ALIAS_IDENTITY_CORRECTION; frozen PSI-25 filter retained only for parity; native PSI-26 separately"
            )
        else:
            row["technical_disposition"] = (
                "PARITY_AND_SOURCE_RELATION_CHECKS; scientific usefulness unadjudicated"
            )
        results.append(row)
    out = ROOT / "artifacts/phase3c_targeted_parity_reconciliation_v4.json"
    assert not out.exists()
    out.write_text(
        json.dumps(
            {
                "cases": results,
                "scientific_relevance_precision": "NOT_MEASURABLE",
                "gold_modified": False,
                "scope": "A/B same preserved original source universe; C adds validated PSI identities and original-PDF FLEX crosswalks",
            },
            indent=2,
        )
    )
    out = ROOT / "artifacts/phase3c_targeted_related_review_complete_v4.json"
    assert not out.exists()
    out.write_text(
        json.dumps(
            {"candidates": review, "expert_labels": 0, "precision_at_k": "NOT_MEASURABLE"}, indent=2
        )
    )
    print({"cases": len(results), "related_review_candidates": len(review)})


if __name__ == "__main__":
    main()
