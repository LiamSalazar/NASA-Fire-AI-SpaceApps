"""Final offline audits and explicit failed-gate closure; no external calls."""

import ast
import json
import sys
from pathlib import Path

from pyshacl import validate

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from phase3c_corrective_live import check_freeze, rows
from phase3c_native_benchmarks import native_guard

from nasa_fire_ai.evaluation.phase3c import digest, freeze_json, proportion
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.generic import profile_table, propose_table_role
from nasa_fire_ai.ingestion.semantic import project_legacy
from nasa_fire_ai.models import GroundedAnswerDraft
from nasa_fire_ai.query.native import NS, execute_native
from nasa_fire_ai.query.v2 import QueryIntentV2
from nasa_fire_ai.services.native import validate_native_draft


def read(name):
    return json.loads((ROOT / name).read_text())


def main():
    check_freeze()
    er = EvidenceRegistry(ROOT / "data/index/evidence.sqlite")
    store = project_legacy(ROOT, er)
    baseline = read("artifacts/phase3c_corrective_baseline_v1.json")
    checks = {
        name: digest(ROOT / name) == value
        for name, value in baseline["digests"].items()
        if name != "artifacts/phase3c_progress.json"
    }
    canonical = __import__("rdflib").Graph().parse(ROOT / "data/canonical/graph.ttl")
    audited = ["src/nasa_fire_ai/query/native.py", "src/nasa_fire_ai/query/v2.py"]
    branches = []
    prohibited = {"AirflowVelocity", "OxygenConcentration", "Pressure"}
    for name in audited:
        tree = ast.parse((ROOT / name).read_text())
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.IfExp, ast.Compare)):
                constants = {
                    n.value
                    for n in ast.walk(node.test if hasattr(node, "test") else node)
                    if isinstance(n, ast.Constant) and isinstance(n.value, str)
                }
                if constants.intersection(prohibited):
                    branches.append({"file": name, "line": node.lineno})
    audit = {
        "version": "FINAL_CORRECTIVE-v1",
        "architecture_digest": digest(ROOT / "artifacts/phase3c_corrective_native_freeze_v6.json"),
        "raw_canonical_historical_digests_unchanged": all(checks.values()),
        "changed_baseline_files": [name for name, same in checks.items() if not same],
        "db_integrity": er.db.execute("PRAGMA integrity_check").fetchone()[0],
        "counts": {
            t: er.db.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
            for t in ("sources", "documents", "passages", "passages_fts", "semantic_staging")
        },
        "canonical_shacl": bool(
            validate(canonical, shacl_graph=str(ROOT / "ontology/shapes.ttl"))[0]
        ),
        "native_shacl": bool(
            validate(store.graph, shacl_graph=str(ROOT / "ontology/semantic_shapes.ttl"))[0]
        ),
        "canonical_triples": len(canonical),
        "native_triples": len(store.graph),
        "broken_native_evidence_ids": [
            str(e)
            for e in set(store.graph.objects(None, NS.evidenceRef))
            if er.resolve(str(e)) is None
        ],
        "fts_missing": er.db.execute(
            "SELECT count(*) FROM passages p LEFT JOIN passages_fts f USING(evidence_id) WHERE f.evidence_id IS NULL"
        ).fetchone()[0],
        "duplicate_passage_evidence_ids": er.db.execute(
            "SELECT count(*) FROM (SELECT evidence_id FROM passages GROUP BY evidence_id HAVING count(*)>1)"
        ).fetchone()[0],
        "projection": store.projection_report,
        "static_audit": {
            "scope": audited,
            "property_identity_branch_count": len(branches),
            "property_identity_branches": branches,
            "hardcoded_scientific_fields_in_v2": len(
                set(QueryIntentV2.model_fields).intersection(
                    {"airflow_velocity", "oxygen_concentration", "pressure"}
                )
            ),
            "limitation": "Static literal audit is bounded to named legacy identities; dynamic benchmark and runtime guards provide complementary evidence, not a formal proof of every possible branch.",
        },
    }
    audit["excluded_mutable_checkpoint"] = "artifacts/phase3c_progress.json"
    freeze_json(ROOT / "artifacts/phase3c_corrective_final_integrity_v2.json", audit)
    receipts = rows(ROOT / "artifacts/phase3c_corrective_synthesis_receipts_v2.jsonl")
    executed = {
        r["case_id"]: r for r in rows(ROOT / "artifacts/phase3c_corrective_e2e_results_v2.jsonl")
    }
    revalidation = []
    queries = {
        c["id"]: c["query"] for c in read("evals/phase3c_corrective_e2e_gold_v1.json")["cases"]
    }
    for receipt in receipts:
        row = executed[receipt["case_id"]]
        try:
            draft = GroundedAnswerDraft.model_validate_json(receipt["raw_response"])
        except ValueError:
            revalidation.append({"case_id": receipt["case_id"], "structured_valid": False})
            continue
        with native_guard():
            result = execute_native(
                QueryIntentV2.model_validate(row["interpreted_intent"]),
                queries[receipt["case_id"]],
                store,
                er,
            )
        validated = validate_native_draft(draft, result.bundle)
        revalidation.append(
            {
                "case_id": receipt["case_id"],
                "structured_valid": True,
                "valid": validated.valid,
                "errors": validated.errors,
                "claims": [c.model_dump(mode="json") for c in draft.claims],
            }
        )
    freeze_json(
        ROOT / "artifacts/phase3c_corrective_final_quote_audit_v2.json",
        {
            "version": "OFFLINE_FINAL_METADATA_REVALIDATION",
            "new_api_calls": 0,
            "cases": revalidation,
            "limitation": "Only baseline receipts; reconstruction uses persisted V2 intent and original query. This is offline quotation/metadata validation, not new live synthesis or reviewed response relevance.",
        },
    )
    jev = rows(ROOT / "artifacts/phase3c_corrective_jev_results_v1.jsonl")
    freeze_json(
        ROOT / "artifacts/phase3c_corrective_jev_usage_v1.json",
        {
            "requests": len(jev),
            "response_models": sorted({r["response"]["model"] for r in jev}),
            "input_tokens": sum(r["response"].get("usage", {}).get("input_tokens", 0) for r in jev),
            "output_tokens": sum(
                r["response"].get("usage", {}).get("output_tokens", 0) for r in jev
            ),
            "cost": "NOT_AVAILABLE",
        },
    )
    fixtures = [
        [{"title": "catalog item", "id": "a"}],
        [{"planned": "yes", "airflow velocity (m/s)": "0.2"}],
        [{"run id": "r1", "pressure (kPa)": "101"}],
        [{"unknown field": "unreviewed", "value": "3"}],
    ]
    roles = [propose_table_role(profile_table(f)) for f in fixtures]
    freeze_json(
        ROOT / "artifacts/phase3c_corrective_table_role_audit_v1.json",
        {
            "fixtures": roles,
            "automatic_canonical_roles": 0,
            "provenance_policy": "Unreviewed rows remain evidence-backed staging. Structural hints alone do not prove experimental execution.",
            "safe_unreviewed_role_handling": proportion(
                sum(not r["canonical"] for r in roles), len(roles)
            ),
            "status": "SYNTHETIC_FIXTURES_NOT_NEW_NASA_HOLDOUT",
        },
    )
    parity = read("artifacts/phase3c_corrective_native_checks_v1/phase3c_native_parity.json")
    freeze_json(
        ROOT / "artifacts/phase3c_corrective_relevance_review_packet_v1.json",
        {
            "review_status": "UNREVIEWED",
            "cases": parity["cases"],
            "review_questions": [
                "Is added documentary evidence relevant?",
                "Was relevant evidence omitted?",
                "Does source scope or authority differ?",
                "Are different evidence IDs the same underlying passage?",
            ],
            "objective_direct_disagreements": {
                "qi07": "Expanded source-backed BASS projection versus two-run V1 execution view",
                "qi08": "Expanded source-backed BASS projection versus two-run V1 execution view",
            },
            "subjective_evidence_disagreements": "REVIEW_REQUIRED; parity is not scientific truth",
        },
    )
    decisions = {
        "NATIVE_V2_EXECUTOR_DECISION": "REVISE",
        "QUERYINTERPRETER_V2_DECISION": "REVISE",
        "GENERIC_INGESTION_DECISION": "REVISE",
        "GROUNDED_SYNTHESIS_DECISION": "REVISE",
        "JEV_TRIAGE_DECISION": "KEEP_OPTIONAL",
        "GENERALIZATION_DECISION": "LIMITED",
        "V2_DEFAULT_PATH_DECISION": "KEEP_EXPERIMENTAL",
        "READY_FOR_PHASE_4": "NO",
    }
    freeze_json(
        ROOT / "artifacts/phase3c_corrective_benchmark_summary_v2.json",
        {
            "version": "FINAL_CORRECTIVE-v1",
            "closure": "EVALUATION_CLOSED_WITH_FAILED_READINESS_GATES",
            "decisions": decisions,
            "coverage": store.projection_report,
            "interpreter": read(
                "artifacts/phase3c_corrective_interpreter_resolution_repair_summary_v1.json"
            ),
            "retrieval": read("artifacts/phase3c_corrective_retrieval_summary_v1.json"),
            "parity": parity["metrics"],
            "jev": read("artifacts/phase3c_corrective_jev_summary_v1.json"),
            "end_to_end": read("artifacts/phase3c_corrective_e2e_summary_v2.json"),
            "holdout": read("artifacts/phase3c_corrective_holdout_first_pass_v2.json"),
            "unmeasured_gates": [
                "Independent paraphrase fidelity",
                "Broad independently reviewed scientific relevance",
                "New structured experimental NASA holdout",
                "New compositional patterns beyond existing three template families",
            ],
        },
    )
    print(
        json.dumps(
            {
                "integrity": audit["raw_canonical_historical_digests_unchanged"],
                "decisions": decisions,
            }
        )
    )


if __name__ == "__main__":
    main()
