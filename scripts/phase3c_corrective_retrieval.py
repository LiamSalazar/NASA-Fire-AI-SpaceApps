"""Independent source/record-backed retrieval probes, separate from V1 parity."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from phase3c_corrective_live import check_freeze
from phase3c_native_benchmarks import native_guard

from nasa_fire_ai.evaluation.phase3c import append_result, digest, freeze_json, latency, proportion
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.semantic import project_legacy
from nasa_fire_ai.query.native import execute_native
from nasa_fire_ai.query.v2 import (
    EntityConstraintV2,
    GenericValue,
    PropertyConstraintV2,
    QueryIntentV2,
)


def prepare():
    epistemic = json.loads((ROOT / "evals/phase1_5_epistemic_gold.json").read_text())["cases"]
    mapping = {
        "ReportedExperimentalObservation": "ReportedObservation",
        "NASAIdentifiedOpenQuestion": "OpenQuestion",
    }
    cases = []
    for c in epistemic:
        if c["gold_label"] == "NONE":
            continue
        cls = mapping.get(c["gold_label"], c["gold_label"])
        intent = QueryIntentV2(requested_information=[cls], source_constraints=[c["source_id"]])
        cases.append(
            {
                "id": c["gold_case_id"],
                "query": f"Find {cls}: {c['passage']}",
                "intent": intent.model_dump(mode="json"),
                "expected_evidence_ids": [c["evidence_id"]],
                "basis": "Existing reviewed epistemic record; exact-text/source-constrained retrieval, NOT paraphrase relevance gold",
            }
        )
    q = QueryIntentV2(
        targets=["ExperimentalRun"],
        entity_constraints=[
            EntityConstraintV2(relation="hasMaterial", entity_id="SIBAL Fabric"),
            EntityConstraintV2(relation="hasGravityCondition", entity_id="microgravity"),
        ],
        property_constraints=[
            PropertyConstraintV2(
                property_id="AirflowVelocity",
                operator="GTE",
                value=GenericValue(reported_value=20, reported_unit="cm/s"),
            )
        ],
    )
    cases.append(
        {
            "id": "canonical-table-conditions",
            "query": "SIBAL Fabric microgravity airflow at least 20 cm/s",
            "intent": q.model_dump(mode="json"),
            "expected_evidence_ids": ["E-psi-98-table-S1", "E-psi-98-table-S2"],
            "expected_direct": ["psi-98-S1", "psi-98-S2"],
            "basis": "Immutable source-backed canonical condition/sample records, not executor prediction",
        }
    )
    q.property_constraints[0].operator = "LT"
    q.property_constraints[0].value.reported_value = 10
    cases.append(
        {
            "id": "canonical-table-related",
            "query": "SIBAL Fabric microgravity airflow below 10 cm/s",
            "intent": q.model_dump(mode="json"),
            "expected_evidence_ids": ["E-psi-98-table-S1", "E-psi-98-table-S2"],
            "expected_direct": [],
            "expected_related": ["psi-98-S1", "psi-98-S2"],
            "basis": "Known 20 cm/s conditions differ, material/gravity match",
        }
    )
    cases.append(
        {
            "id": "unavailable-source",
            "query": "NASA evidence from unavailable source",
            "intent": QueryIntentV2(
                targets=["Document"], source_constraints=["unavailable-source"]
            ).model_dump(mode="json"),
            "expected_evidence_ids": [],
            "basis": "Source ID absent from registry; objective no-answer",
        }
    )
    freeze_json(
        ROOT / "evals/phase3c_corrective_retrieval_gold_v1.json",
        {
            "version": "corrective-record-gold-v1",
            "cases": cases,
            "limitations": [
                "Twelve objective probes, not independently reviewed topical paraphrase relevance",
                "No invented scientist review",
                "Review packet required for subjective relevance and paraphrase retrieval",
            ],
        },
    )


def main():
    check_freeze()
    prepare()
    evidence = EvidenceRegistry(ROOT / "data/index/evidence.sqlite")
    store = project_legacy(ROOT, evidence)
    gold_path = ROOT / "evals/phase3c_corrective_retrieval_gold_v1.json"
    cases = json.loads(gold_path.read_text())["cases"]
    output = ROOT / "artifacts/phase3c_corrective_retrieval_v1.jsonl"
    completed = (
        {json.loads(l)["case_id"] for l in output.read_text().splitlines()}
        if output.exists()
        else set()
    )
    for case in cases:
        if case["id"] in completed:
            continue
        with native_guard():
            result = execute_native(
                QueryIntentV2.model_validate(case["intent"]),
                case["query"],
                store,
                evidence,
                limit=10,
            )
        ids = [p["evidence_id"] for p in result.bundle.evidence_passages]
        expected = set(case["expected_evidence_ids"])
        rank = next((i for i, eid in enumerate(ids, 1) if eid in expected), None)
        fields = [
            r
            for key in (
                "experimental_observations",
                "interventions",
                "nasa_conclusions",
                "safety_implications",
                "requirements",
                "guidance",
                "design_test_criteria",
                "nasa_identified_open_questions",
            )
            for r in getattr(result.bundle, key)
        ]
        scientific_ids = {ref["evidence_id"] for r in fields for ref in r.get("evidence_refs", [])}
        row = {
            "case_id": case["id"],
            "gold_digest": digest(gold_path),
            "retrieved_ids": ids,
            "expected_ids": sorted(expected),
            "rank": rank,
            "all_expected_found": expected.issubset(ids),
            "scientific_record_found": expected.issubset(scientific_ids)
            if case["id"].startswith("reviewed")
            else None,
            "no_answer_correct": not ids if not expected else None,
            "direct": [r["id"] for r in result.bundle.direct_evidence],
            "related": [r["id"] for r in result.bundle.related_evidence],
            "direct_correct": sorted(r["id"] for r in result.bundle.direct_evidence)
            == case.get("expected_direct")
            if "expected_direct" in case
            else None,
            "related_correct": sorted(r["id"] for r in result.bundle.related_evidence)
            == case.get("expected_related")
            if "expected_related" in case
            else None,
            "evidence_valid": all(evidence.resolve(e) for e in ids),
            "latency": result.latency_ms,
            "sources": [p.get("source_metadata") for p in result.bundle.evidence_passages],
            "omitted_expected": sorted(expected - set(ids)),
            "extra_ids": sorted(set(ids) - expected),
            "extra_relevance": "UNREVIEWED: exact gold is a required subset, not an exhaustive relevance set",
        }
        append_result(output, row)
        print(
            json.dumps({"case": case["id"], "all_expected_found": row["all_expected_found"]}),
            flush=True,
        )
    rows = [json.loads(l) for l in output.read_text().splitlines()]
    positive = [r for r in rows if r["expected_ids"]]
    n = len(positive)
    metrics = {
        f"Recall@{k}": proportion(
            sum(r["rank"] is not None and r["rank"] <= k for r in positive), n
        )
        for k in (1, 3, 5, 10)
    }
    metrics.update(
        {
            "all_required_evidence": proportion(sum(r["all_expected_found"] for r in positive), n),
            "scientific_class_recovery": proportion(
                sum(r["scientific_record_found"] is True for r in rows),
                sum(r["scientific_record_found"] is not None for r in rows),
            ),
            "MRR": {
                "numerator": sum(1 / r["rank"] for r in positive if r["rank"]),
                "denominator": n,
                "estimate": sum(1 / r["rank"] for r in positive if r["rank"]) / n,
            },
        }
    )
    freeze_json(
        ROOT / "artifacts/phase3c_corrective_retrieval_summary_v1.json",
        {
            "cases": len(rows),
            "metrics": metrics,
            "latency": {
                key: latency([r["latency"][key] for r in rows]) for key in rows[0]["latency"]
            },
            "precision_at_k": "NOT_MEASURED: exhaustive independent relevance gold unavailable",
            "authority": "Reviewed epistemic identities and immutable canonical records; no V1 predictions as gold",
        },
    )


if __name__ == "__main__":
    main()
