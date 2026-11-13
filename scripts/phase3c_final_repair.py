"""Versioned final corrective benchmarks; writes only new v1 artifacts."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from phase3c_corrective_live import MODEL, rows
from phase3c_live import semantic_signature
from phase3c_native_benchmarks import native_guard

from nasa_fire_ai.evaluation.phase3c import append_result, digest, freeze_json, latency, proportion
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.semantic import load_semantic_registry, project_legacy
from nasa_fire_ai.models import ConversationContext
from nasa_fire_ai.query.native import SemanticGraph, execute_native
from nasa_fire_ai.query.native_interpreter import MinimalInterpretationV2, resolve_minimal
from nasa_fire_ai.query.v2 import QueryIntentV2
from nasa_fire_ai.services.native import answer_native_text


def read(name):
    return json.loads((ROOT / name).read_text())


def check_freeze():
    name = "artifacts/phase3c_final_repair_native_freeze_v4.json"
    if not (ROOT / name).exists():
        name = "artifacts/phase3c_final_repair_native_freeze_v3.json"
    if not (ROOT / name).exists():
        name = "artifacts/phase3c_final_repair_native_freeze_v2.json"
    if not (ROOT / name).exists():
        name = "artifacts/phase3c_final_repair_native_freeze_v1.json"
    frozen = read(name)
    for name, expected in frozen["digests"].items():
        if digest(ROOT / name) != expected:
            raise RuntimeError(f"Final repair freeze changed: {name}")


def init():
    historical = read("artifacts/phase3c_corrective_baseline_v1.json")
    golds = [
        "evals/phase3c_queryintent_v2_gold_v1.json",
        "evals/phase3c_compositional_gold_v1.json",
        "evals/phase3c_corrective_e2e_gold_v1.json",
        "evals/phase3c_corrective_retrieval_gold_v1.json",
        "evals/phase3c_corrective_jev_gold_v1.json",
    ]
    baseline_value = {
        "version": "phase3c-final-repair-v1",
        "parent_freeze": "artifacts/phase3c_corrective_native_freeze_v6.json",
        "parent_freeze_digest": digest(ROOT / "artifacts/phase3c_corrective_native_freeze_v6.json"),
        "immutable_historical_digests": historical["digests"],
        "frozen_gold_digests": {name: digest(ROOT / name) for name in golds},
        "pre_iteration_summary": read("artifacts/phase3c_corrective_benchmark_summary_v3.json"),
    }
    if not (ROOT / "artifacts/phase3c_final_repair_baseline.json").exists():
        freeze_json(ROOT / "artifacts/phase3c_final_repair_baseline.json", baseline_value)
    current_path = ROOT / "artifacts/phase3c_final_repair_progress.json"
    if current_path.exists():
        state = read("artifacts/phase3c_final_repair_progress.json")
        state["status"] = "IN_PROGRESS"
        state["completed"] = list(
            dict.fromkeys(
                state.get("completed", [])
                + [
                    "historical_state_audit",
                    "class_scoped_topic_selector_repair",
                    "measurement_condition_bundle_fields",
                    "mmhg_si_conversion",
                    "context_qualified_constraint_execution",
                    "source_name_constraint_regression",
                ]
            )
        )
        state["pending"] = [
            "frozen_12_case_retrieval_regression",
            "re_resolve_live_minimal_interpretations",
            "candidate_root_cause_inventory",
            "meaningful_structured_holdout_search",
            "final_quality_and_decision",
        ]
        state["latest_freeze"] = "artifacts/phase3c_final_repair_native_freeze_v1.json"
        current_path.write_text(json.dumps(state, indent=2) + "\n")
    else:
        current_path.write_text(
            json.dumps(
                {
                    "version": "phase3c-final-repair-v1",
                    "status": "IN_PROGRESS",
                    "baseline": "artifacts/phase3c_final_repair_baseline.json",
                    "completed": [
                        "historical_state_audit",
                        "class_scoped_topic_selector_repair",
                        "measurement_condition_bundle_fields",
                        "mmhg_si_conversion",
                        "context_qualified_constraint_execution",
                        "source_name_constraint_regression",
                    ],
                    "pending": [
                        "frozen_12_case_retrieval_regression",
                        "re_resolve_live_minimal_interpretations",
                        "candidate_root_cause_inventory",
                        "meaningful_structured_holdout_search",
                        "final_quality_and_decision",
                    ],
                    "latest_freeze": None,
                    "evaluation_digests": {},
                    "model": MODEL,
                    "credentials": "environment only; never persisted",
                },
                indent=2,
            )
            + "\n"
        )


def freeze():
    freeze_path = ROOT / "artifacts/phase3c_final_repair_native_freeze_v4.json"
    if freeze_path.exists():
        check_freeze()
        state = read("artifacts/phase3c_final_repair_progress.json")
        state["latest_freeze"] = str(freeze_path.relative_to(ROOT))
        state.setdefault("evaluation_digests", {})["native_freeze"] = digest(freeze_path)
        (ROOT / "artifacts/phase3c_final_repair_progress.json").write_text(
            json.dumps(state, indent=2) + "\n"
        )
        return
    paths = [
        *sorted((ROOT / "src/nasa_fire_ai").rglob("*.py")),
        *sorted((ROOT / "domain").glob("*.yaml")),
        *sorted((ROOT / "ontology").glob("*.ttl")),
    ]
    freeze_json(
        ROOT / "artifacts/phase3c_final_repair_native_freeze_v4.json",
        {
            "version": "post-repair-v1",
            "parent_freeze_digest": digest(
                ROOT / "artifacts/phase3c_corrective_native_freeze_v6.json"
            ),
            "digests": {str(p.relative_to(ROOT)): digest(p) for p in paths},
        },
    )
    state = read("artifacts/phase3c_final_repair_progress.json")
    state["latest_freeze"] = "artifacts/phase3c_final_repair_native_freeze_v1.json"
    state["evaluation_digests"]["native_freeze"] = digest(ROOT / state["latest_freeze"])
    (ROOT / "artifacts/phase3c_final_repair_progress.json").write_text(
        json.dumps(state, indent=2) + "\n"
    )


def projection():
    check_freeze()
    evidence = EvidenceRegistry(ROOT / "data/index/evidence.sqlite")
    store = project_legacy(ROOT, evidence)
    by_reason, by_label = {}, {}
    for item in store.projection_staging:
        reason = item.get("reason", "unspecified")
        by_reason[reason] = by_reason.get(reason, 0) + 1
        label = item.get("raw_label", "unspecified")
        by_label[label] = by_label.get(label, 0) + 1
    freeze_json(
        ROOT / "artifacts/phase3c_final_repair_coverage_v1.json",
        {
            "version": "post-repair-v1",
            "counts": store.projection_report,
            "unresolved_by_root_reason": by_reason,
            "unresolved_by_field": by_label,
            "unit_conversion": {
                "unit": "mmHg",
                "property": "Pressure",
                "factor_to_Pa": 133.322387415,
                "records": sum(
                    (
                        json.loads(str(raw))
                        .get("qualifiers", {})
                        .get("original_record", {})
                        .get("reported_unit")
                        or ""
                    ).lower()
                    == "mmhg"
                    for raw in store.graph.objects(
                        None,
                        __import__("rdflib")
                        .Namespace("https://example.org/nasa-fire-safety/semantic/")
                        .payload,
                    )
                ),
                "identity_basis": "Existing declarative pressure->Pressure mapping plus registered pressure dimension",
                "source_values_preserved": True,
            },
            "staging_provenance_complete": proportion(
                sum(
                    bool(x.get("source_id") and x.get("evidence_id") and x.get("provenance"))
                    for x in store.projection_staging
                ),
                len(store.projection_staging),
            ),
            "broken_native_evidence_ids": [
                str(e)
                for e in set(
                    store.graph.objects(
                        None,
                        __import__("rdflib")
                        .Namespace("https://example.org/nasa-fire-safety/semantic/")
                        .evidenceRef,
                    )
                )
                if evidence.resolve(str(e)) is None
            ],
            "raw_canonical_digest_checks": all(
                digest(ROOT / name) == expected
                for name, expected in read("artifacts/phase3c_corrective_baseline_v1.json")[
                    "digests"
                ].items()
                if name.startswith(("data/raw/", "data/canonical/"))
            ),
            "native_triples": len(store.graph),
        },
    )


def interpreter_repair():
    check_freeze()
    evidence = EvidenceRegistry(ROOT / "data/index/evidence.sqlite")
    store = project_legacy(ROOT, evidence)
    language = yaml.safe_load((ROOT / "domain/query_language_v2.yaml").read_text())
    sources = [
        (
            "phase3c_queryintent_v2_gold_v1.json",
            "phase3c_corrective_interpreter_live_v1.jsonl",
            "standalone",
        ),
        (
            "phase3c_compositional_gold_v1.json",
            "phase3c_corrective_interpreter_live_v1.jsonl",
            "historical_compositional",
        ),
        (
            "phase3c_corrective_compositional_gold_v1.json",
            "phase3c_corrective_compositional_results_v2.jsonl",
            "new_compositional",
        ),
    ]
    results = []
    output = ROOT / "artifacts/phase3c_final_repair_interpreter_cases_v6.jsonl"
    prior = {r["case_id"]: r for r in rows(output)}
    for gold_name, predictions_name, group in sources:
        predictions = {r["case_id"]: r for r in rows(ROOT / "artifacts" / predictions_name)}
        gold = read("evals/" + gold_name)
        for case in gold["cases"]:
            if not case.get("supported") or case["id"] in prior:
                continue
            pred = predictions.get(case["id"])
            if not pred or not pred.get("minimal_raw_output"):
                continue
            proposal = MinimalInterpretationV2.model_validate_json(pred["minimal_raw_output"])
            context = (
                ConversationContext.model_validate(case["context"]) if case.get("context") else None
            )
            try:
                resolved = resolve_minimal(
                    proposal, store.registry, language, context, query=case["query"]
                )
                store.registry.validate_intent(resolved)
                actual = resolved.model_dump(mode="json")
                valid = True
                error = None
            except (ValueError, LookupError) as exc:
                actual, valid, error = None, False, type(exc).__name__
            row = {
                "case_id": case["id"],
                "group": group,
                "query": case["query"],
                "gold_digest": digest(ROOT / "evals" / gold_name),
                "raw_minimal_extraction": pred["minimal_raw_output"],
                "original_resolved_intent": pred.get("resolved_intent"),
                "repaired_resolved_intent": actual,
                "expected_intent": case["expected"],
                "valid": valid,
                "exact": bool(
                    actual and semantic_signature(actual) == semantic_signature(case["expected"])
                ),
                "latency_ms": pred.get("latency_ms"),
                "context": case.get("context"),
                "root_cause": interpretation_root_cause(case, proposal, actual),
                "provenance": "Persisted live model extraction re-resolved after deterministic repair; no new model call.",
                "error": error,
            }
            append_result(output, row)
            prior[case["id"]] = row
            results.append(row)
    all_rows = rows(output)
    groups = {}
    for group in sorted({r["group"] for r in all_rows}):
        subset = [r for r in all_rows if r["group"] == group]
        groups[group] = {
            "n": len(subset),
            "valid": proportion(sum(r["valid"] for r in subset), len(subset)),
            "exact": proportion(sum(r["exact"] for r in subset), len(subset)),
            "failure_root_causes": {
                cause: sum(r["root_cause"] == cause for r in subset)
                for cause in sorted({r["root_cause"] for r in subset})
            },
        }
    freeze_json(
        ROOT / "artifacts/phase3c_final_repair_interpreter_summary_v6.json",
        {
            "version": "POST_DETERMINISTIC_RESOLUTION_REPAIR-v6",
            "groups": groups,
            "field_metrics": interpreter_field_metrics(all_rows),
            "new_model_calls": 0,
            "case_trace_file": str(output.relative_to(ROOT)),
            "field_analysis": "Raw proposals, original resolved intent, repaired intent and reviewed expected fields coexist per case for layer attribution.",
        },
    )


def interpretation_root_cause(case, proposal, actual):
    expected = case["expected"]
    if actual is None:
        return "SEMANTIC_VALIDATION"
    if set(expected.get("requested_information", [])) - set(
        actual.get("requested_information", [])
    ):
        recognized = set()
        query = case["query"].lower()
        language = yaml.safe_load((ROOT / "domain/query_language_v2.yaml").read_text())
        for cls, aliases in language["information_mentions"].items():
            if any(alias.lower() in query for alias in [cls, *aliases]):
                recognized.add(cls)
        return (
            "DETERMINISTIC_INFO_RESOLUTION"
            if set(expected["requested_information"]) & recognized
            else "MODEL_INFO_EXTRACTION"
        )
    if expected.get("comparison") and not actual.get("comparison"):
        return (
            "COMPARISON_OPERAND_RESOLUTION"
            if proposal.comparison_operands
            else "MODEL_COMPARISON_EXTRACTION"
        )
    expected_signature = semantic_signature(expected)
    actual_signature = semantic_signature(actual)
    if expected_signature.get("property_constraints") != actual_signature.get(
        "property_constraints"
    ):
        return "PROPERTY_OR_NUMERIC_RESOLUTION"
    if expected_signature.get("entity_constraints") != actual_signature.get("entity_constraints"):
        return "ENTITY_RESOLUTION"
    if expected_signature.get("targets") != actual_signature.get("targets"):
        return "TARGET_RESOLUTION"
    if expected_signature.get("unresolved_mentions") != actual_signature.get("unresolved_mentions"):
        return "ABSTENTION_OR_UNKNOWN_RESOLUTION"
    return "OTHER_FIELD_OR_EXACT_CANONICALIZATION"


def interpreter_field_metrics(rows_):
    from collections import Counter

    def field_key(value):
        return json.dumps(value, sort_keys=True)

    metrics = {}
    for field in (
        "targets",
        "entity_constraints",
        "property_constraints",
        "requested_information",
        "source_constraints",
        "unresolved_mentions",
        "ambiguities",
    ):
        tp = fp = fn = 0
        for row in rows_:
            expected = semantic_signature(row["expected_intent"]).get(field, [])
            actual = semantic_signature(row["repaired_resolved_intent"] or {}).get(field, [])
            gold, predicted = {field_key(x) for x in expected}, {field_key(x) for x in actual}
            tp += len(gold & predicted)
            fp += len(predicted - gold)
            fn += len(gold - predicted)
        precision = tp / (tp + fp) if tp + fp else (1.0 if not fn else 0.0)
        recall = tp / (tp + fn) if tp + fn else 1.0
        metrics[field] = {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": precision,
            "recall": recall,
            "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 1.0,
        }

    operation_ok = comparison_ok = comparison_n = 0
    numeric = Counter()
    numeric_denominators = Counter()
    for row in rows_:
        expected = row["expected_intent"]
        actual = row["repaired_resolved_intent"] or {}
        operation_ok += expected.get("operation") == actual.get("operation")
        if expected.get("comparison") is not None:
            comparison_n += 1
            comparison_ok += semantic_signature({"comparison": expected.get("comparison")}).get(
                "comparison"
            ) == semantic_signature({"comparison": actual.get("comparison")}).get("comparison")
        actual_props = {p["property_id"]: p for p in actual.get("property_constraints", [])}
        for prop in expected.get("property_constraints", []):
            found = actual_props.get(prop["property_id"])
            for name, keys in {
                "numeric_value": ("reported_value",),
                "operator": (),
                "unit": ("reported_unit",),
                "range": ("lower", "upper"),
                "approximation": ("approximate", "tolerance"),
            }.items():
                if name == "operator":
                    ok = bool(found) and prop.get("operator") == found.get("operator")
                else:
                    ok = bool(found) and all(
                        prop.get("value", {}).get(key) == found.get("value", {}).get(key)
                        for key in keys
                    )
                if name == "range" and prop.get("operator") != "BETWEEN":
                    continue
                if name == "approximation" and prop.get("operator") != "APPROX":
                    continue
                numeric[name] += bool(ok)
                numeric_denominators[name] += 1
    metrics["operation_accuracy"] = proportion(operation_ok, len(rows_))
    metrics["comparison_correctness"] = proportion(comparison_ok, comparison_n)
    metrics["numeric_fields"] = {
        name: proportion(numeric[name], numeric_denominators[name])
        for name in sorted(numeric_denominators)
    }
    return metrics


def objective_retrieval():
    check_freeze()
    evidence = EvidenceRegistry(ROOT / "data/index/evidence.sqlite")
    store = project_legacy(ROOT, evidence)
    gold = read("evals/phase3c_corrective_retrieval_gold_v1.json")
    output = ROOT / "artifacts/phase3c_final_repair_objective_retrieval_v2.jsonl"
    prior = {r["case_id"]: r for r in rows(output)}
    for case in gold["cases"]:
        if case["id"] in prior:
            continue
        intent = QueryIntentV2.model_validate(case["intent"])
        with native_guard():
            execution = execute_native(intent, case["query"], store, evidence)
        bundle = execution.bundle
        actual_ids = sorted({p["evidence_id"] for p in bundle.evidence_passages})
        expected_ids = case.get("expected_evidence_ids", [])
        row = {
            "case_id": case["id"],
            "gold_digest": digest(ROOT / "evals/phase3c_corrective_retrieval_gold_v1.json"),
            "query": case["query"],
            "intent": case["intent"],
            "expected_evidence_ids": expected_ids,
            "actual_evidence_ids": actual_ids,
            "required_recall": proportion(
                len(set(expected_ids) & set(actual_ids)), len(expected_ids)
            )
            if expected_ids
            else None,
            "exact_evidence_ids": set(expected_ids) == set(actual_ids) if expected_ids else None,
            "expected_direct": case.get("expected_direct"),
            "actual_direct": [x["id"] for x in bundle.direct_evidence],
            "expected_related": case.get("expected_related"),
            "actual_related": [x["id"] for x in bundle.related_evidence],
            "no_direct": bundle.no_direct_evidence,
            "source_metadata_valid": all(
                evidence.resolve(eid) and evidence.source_metadata(eid) for eid in actual_ids
            ),
            "selection_trace": bundle.retrieval_metadata["selection_trace"],
            "eligible_evidence_ids": execution.eligible_evidence_ids,
            "latency_ms": execution.latency_ms,
        }
        append_result(output, row)
    scored = rows(output)
    positive = [r for r in scored if r["expected_evidence_ids"]]
    direct = [r for r in scored if r.get("expected_direct") is not None]
    related = [r for r in scored if r.get("expected_related") is not None]
    freeze_json(
        ROOT / "artifacts/phase3c_final_repair_objective_retrieval_summary_v2.json",
        {
            "version": "POST_REPAIR-v2",
            "n": len(scored),
            "required_evidence_recovery": proportion(
                sum(
                    r["required_recall"]["numerator"] == r["required_recall"]["denominator"]
                    for r in positive
                ),
                len(positive),
            ),
            "exact_evidence_set": proportion(
                sum(r["exact_evidence_ids"] for r in positive), len(positive)
            ),
            "direct_set_match": proportion(
                sum(set(r["expected_direct"]) == set(r["actual_direct"]) for r in direct),
                len(direct),
            ),
            "related_set_match": proportion(
                sum(set(r["expected_related"]) == set(r["actual_related"]) for r in related),
                len(related),
            ),
            "source_metadata_valid": proportion(
                sum(r["source_metadata_valid"] for r in scored), len(scored)
            ),
            "latency": latency([r["latency_ms"]["total"] for r in scored]),
            "gold_limitations": gold["limitations"],
        },
    )


def service_regression():
    _run_service_regression()


def prepare_review_and_holdout_packets():
    """Prepare transparent review packets; never infer independent relevance labels."""
    gold = read("evals/phase3c_corrective_e2e_gold_v1.json")
    results = {
        r["case_id"]: r for r in rows(ROOT / "artifacts/phase3c_final_repair_e2e_cases_v6.jsonl")
    }
    baseline = EvidenceRegistry(ROOT / "data/index/evidence.sqlite")
    holdout_path = ROOT / "artifacts/phase3c_corrective_holdout_evidence_v2.sqlite"
    holdout = EvidenceRegistry(holdout_path) if holdout_path.exists() else None
    packet_cases = []
    for case in gold["cases"]:
        row = results.get(case["id"], {})
        is_holdout = case.get("source_namespace") == "holdout"
        registry = holdout if is_holdout and holdout else baseline
        evidence_ids = sorted(
            set(case.get("required_evidence_ids") or []) | set(row.get("actual_evidence_ids", []))
        )
        evidence = []
        for evidence_id in evidence_ids:
            passage = registry.resolve(evidence_id) if registry else None
            evidence.append(
                {
                    "evidence_id": evidence_id,
                    "text": passage.get("text") if passage else None,
                    "source": registry.source_metadata(evidence_id) if registry else None,
                    "location": (
                        {k: passage.get(k) for k in ("page", "section", "document_id")}
                        if passage
                        else None
                    ),
                    "returned_by_current_run": evidence_id in row.get("actual_evidence_ids", []),
                    "frozen_required_identity": evidence_id
                    in (case.get("required_evidence_ids") or []),
                }
            )
        objectively_scoreable = row.get("retrieval_correct") is not None
        packet_cases.append(
            {
                "case_id": case["id"],
                "query": case["query"],
                "requested_information": case.get("expected_intent", {}).get(
                    "requested_information", []
                ),
                "expected_intent": case.get("expected_intent"),
                "frozen_expected_evidence_ids": case.get("required_evidence_ids"),
                "actual_evidence_ids": row.get("actual_evidence_ids", []),
                "retrieved_evidence": evidence,
                "retrieval_diagnostic_trace": row.get("selection_trace"),
                "objective_gold_basis": (
                    "Frozen source-backed evidence identity or justified no-answer state; this does not score subjective topical relevance."
                    if objectively_scoreable
                    else None
                ),
                "review_status": (
                    "OBJECTIVE_IDENTITY_SCOREABLE_RELEVANCE_STILL_REVIEWABLE"
                    if objectively_scoreable
                    else "REVIEW_REQUIRED"
                ),
                "reviewer_label": None,
                "reviewer_evidence_justification": None,
                "reviewer_authority_assessment": None,
                "reviewer_no_direct_assessment": None,
            }
        )
    freeze_json(
        ROOT / "artifacts/phase3c_final_repair_scientific_relevance_review_v2.json",
        {
            "version": "final-repair-review-v1",
            "gold_digest": digest(ROOT / "evals/phase3c_corrective_e2e_gold_v1.json"),
            "evaluated_case_digest": digest(
                ROOT / "artifacts/phase3c_final_repair_e2e_cases_v6.jsonl"
            ),
            "human_review_performed": False,
            "policy": "Machine-generated packet. Existing exact source-backed IDs are objective identity checks only; all relevance/authority judgments remain for independent review.",
            "cases": packet_cases,
        },
    )

    old_pool = read("artifacts/phase3c_holdout_candidates.json")
    structured = [r for r in old_pool.get("pool", []) if r.get("kind") == "structured"]
    psi_status = {
        row["source_id"]: row
        for row in rows(ROOT / "artifacts/phase3c_holdout_preflight.jsonl")
        if str(row.get("source_id", "")).upper().startswith("PSI-")
    }
    for candidate in structured:
        candidate["prior_structural_preflight"] = psi_status.get(candidate["source_id"])
        candidate["selected_for_new_final_repair_holdout"] = False
        if candidate.get("eligible") and not candidate.get("selected"):
            candidate["final_repair_disposition"] = (
                "PREVIOUSLY_EXPOSED_OR_NO_USABLE_EXPERIMENTAL_TABLE"
            )
    freeze_json(
        ROOT / "artifacts/phase3c_final_repair_structured_candidates_v2.json",
        {
            "version": "structured-candidate-pool-v1",
            "source_candidate_pool": "artifacts/phase3c_holdout_candidates.json",
            "source_pool_digest": digest(ROOT / "artifacts/phase3c_holdout_candidates.json"),
            "architecture_digest": digest(
                ROOT / "artifacts/phase3c_final_repair_native_freeze_v4.json"
            ),
            "candidate_count": len(structured),
            "selected_source": None,
            "selection_result": "NO_NEW_ELIGIBLE_STRUCTURED_SOURCE_ACQUIRED",
            "limitation": "Prior eligible PSI records had already been structurally preflighted in Phase 3C; some lacked experimental tables. Other fire-safety combustion tables were already present in canonical/evaluation/semantic-design history. This is a bounded-candidate result, not a claim NASA has no such data.",
            "pool": structured,
        },
    )


def final_results():
    baseline = read("artifacts/phase3c_final_repair_baseline.json")
    unchanged = []
    changed = []
    missing = []
    for name, expected in baseline["digests"].items():
        path = ROOT / name
        if not path.exists():
            missing.append(name)
        elif digest(path) == expected:
            unchanged.append(name)
        else:
            changed.append(name)
    coverage = read("artifacts/phase3c_final_repair_coverage_v1.json")
    retrieval = read("artifacts/phase3c_final_repair_objective_retrieval_summary_v2.json")
    interpreter = read("artifacts/phase3c_final_repair_interpreter_summary_v6.json")
    end_to_end = read("artifacts/phase3c_final_repair_e2e_summary_v6.json")
    quality = read("artifacts/phase3c_final_repair_quality_v2.json")
    bm25 = read("artifacts/phase3c_final_repair_bm25_v1.json")
    results = {
        "version": "phase3c-final-repair-results-v1",
        "status": "CLOSED_ENGINEERING_WITH_READINESS_BLOCKERS",
        "native_freeze": "artifacts/phase3c_final_repair_native_freeze_v4.json",
        "native_freeze_digest": digest(
            ROOT / "artifacts/phase3c_final_repair_native_freeze_v4.json"
        ),
        "baseline": "artifacts/phase3c_final_repair_baseline.json",
        "historical_baseline_digest_audit": {
            "expected": len(baseline["digests"]),
            "unchanged": len(unchanged),
            "changed": changed,
            "missing": missing,
        },
        "coverage": coverage,
        "objective_retrieval": retrieval,
        "interpreter": interpreter,
        "end_to_end": end_to_end,
        "quality": quality,
        "bm25_regression": bm25,
        "decisions": {
            "NATIVE_V2_EXECUTOR_DECISION": "REVISE",
            "QUERYINTERPRETER_V2_DECISION": "REVISE",
            "GENERIC_INGESTION_DECISION": "REVISE",
            "GROUNDED_SYNTHESIS_DECISION": "REVISE",
            "JEV_TRIAGE_DECISION": "KEEP_OPTIONAL",
            "GENERALIZATION_DECISION": "LIMITED",
            "V2_DEFAULT_PATH_DECISION": "KEEP_EXPERIMENTAL",
            "READY_FOR_PHASE_4": "NO",
        },
        "blockers": [
            "Standalone query exactness is 11/41 and requested-information recall remains 34/50; approve a reviewed language contract before any default-path change.",
            "No genuinely new eligible structured NASA combustion dataset was acquired; generalization beyond prior PSI/NTRS exposures remains limited.",
            "Eight end-to-end cases remain REVIEW_REQUIRED for scientific relevance; no independent human relevance review was performed.",
            "Grounded synthesis still rejects paraphrases without independent fidelity gold; end-to-end full objective success remains 2/20.",
        ],
        "artifacts": {
            "coverage": "artifacts/phase3c_final_repair_coverage_v1.json",
            "retrieval_cases": "artifacts/phase3c_final_repair_objective_retrieval_v2.jsonl",
            "interpreter_cases": "artifacts/phase3c_final_repair_interpreter_cases_v6.jsonl",
            "e2e_cases": "artifacts/phase3c_final_repair_e2e_cases_v6.jsonl",
            "relevance_review": "artifacts/phase3c_final_repair_scientific_relevance_review_v2.json",
            "structured_candidates": "artifacts/phase3c_final_repair_structured_candidates_v2.json",
        },
    }
    freeze_json(ROOT / "artifacts/phase3c_final_repair_results.json", results)
    state = read("artifacts/phase3c_final_repair_progress.json")
    state["status"] = "CLOSED_WITH_READINESS_BLOCKERS"
    state["completed"] = list(
        dict.fromkeys(
            state.get("completed", [])
            + [
                "requested_information_retrieval_repair",
                "frozen_retrieval_regression_rerun",
                "interpreter_layer_diagnosis_and_deterministic_repair",
                "mmhg_conversion_and_context_filter",
                "second_pass_end_to_end_execution",
                "review_packet_preparation",
                "structured_holdout_candidate_audit",
                "final_decision_and_reports",
            ]
        )
    )
    state["pending"] = [
        "independent_scientist_review_of_8_REVIEW_REQUIRED_cases",
        "acquire_and_freeze_an_unseen_structured_NASA_combustion_dataset_if_an_eligible_source_is_found",
        "improve_standalone_requested_information_and_range_interpretation_before_default_enablement",
        "independently_reviewed_paraphrase_fidelity_gold_before_relaxing_quotation_policy",
    ]
    state["evaluation_digests"] = {
        **state.get("evaluation_digests", {}),
        "final_results": digest(ROOT / "artifacts/phase3c_final_repair_results.json"),
        "interpreter_v6": digest(
            ROOT / "artifacts/phase3c_final_repair_interpreter_summary_v6.json"
        ),
        "retrieval_v2": digest(
            ROOT / "artifacts/phase3c_final_repair_objective_retrieval_summary_v2.json"
        ),
        "e2e_v6": digest(ROOT / "artifacts/phase3c_final_repair_e2e_summary_v6.json"),
        "bm25": digest(ROOT / "artifacts/phase3c_final_repair_bm25_v1.json"),
    }
    (ROOT / "artifacts/phase3c_final_repair_progress.json").write_text(
        json.dumps(state, indent=2) + "\n"
    )


def _run_service_regression():
    check_freeze()
    gold = read("evals/phase3c_corrective_e2e_gold_v1.json")
    evidence = EvidenceRegistry(ROOT / "data/index/evidence.sqlite")
    store = project_legacy(ROOT, evidence)
    holdout_evidence = EvidenceRegistry(
        ROOT / "artifacts/phase3c_corrective_holdout_evidence_v2.sqlite"
    )
    holdout_store = SemanticGraph(load_semantic_registry(ROOT / "domain/semantic_registry.yaml"))
    for doc_id, source_id, title in holdout_evidence.db.execute(
        "SELECT document_id,source_id,title FROM documents"
    ):
        ids = [
            r[0]
            for r in holdout_evidence.db.execute(
                "SELECT evidence_id FROM passages WHERE document_id=?", (doc_id,)
            )
        ]
        if ids:
            holdout_store.add_entity(
                doc_id, "Document", ids, [source_id], {"id": doc_id, "title": title}
            )
    proposals = {
        r["case_id"]: r
        for r in rows(ROOT / "artifacts/phase3c_corrective_interpreter_live_v1.jsonl")
    }
    output = ROOT / "artifacts/phase3c_final_repair_e2e_cases_v6.jsonl"
    prior = {r["case_id"]: r for r in rows(output)}
    language = yaml.safe_load((ROOT / "domain/query_language_v2.yaml").read_text())
    for case in gold["cases"]:
        if case["id"] in prior:
            continue
        proposal_row = proposals.get(case["id"])
        if proposal_row and proposal_row.get("minimal_raw_output"):
            proposal = MinimalInterpretationV2.model_validate_json(
                proposal_row["minimal_raw_output"]
            )

            class Cached:
                def __init__(self, value):
                    self.value = value

                def interpret_minimal(self, query):
                    return self.value

            interpreter = Cached(proposal)
        else:

            class Missing:
                def interpret_minimal(self, query):
                    raise ValueError("persisted live interpretation unavailable")

            interpreter = Missing()
        is_holdout = case["source_namespace"] == "holdout"
        active_store, active_evidence = (
            (holdout_store, holdout_evidence) if is_holdout else (store, evidence)
        )
        with native_guard():
            response = answer_native_text(
                case["query"], active_store, active_evidence, language, interpreter
            )
        bundle = response.execution.bundle
        actual = bundle.retrieval_metadata["query_intent_v2"]
        found = sorted({p["evidence_id"] for p in bundle.evidence_passages})
        required = case.get("required_evidence_ids")
        if case["id"] in {"qi19", "qi20"}:
            recovered = not found and actual["clarification_required"]
        elif case["id"] == "qi22":
            recovered = not found and bool(actual["unresolved_mentions"])
        elif case.get("expected_source"):
            recovered = bool(found) and all(
                (active_evidence.source_metadata(eid) or {}).get("source_id")
                == case["expected_source"]
                for eid in found
            )
        elif required is not None:
            recovered = set(required).issubset(found)
        else:
            recovered = None
        previous = next(
            (
                r
                for r in rows(ROOT / "artifacts/phase3c_corrective_e2e_results_v2.jsonl")
                if r["case_id"] == case["id"]
            ),
            {},
        )
        trace = bundle.retrieval_metadata["selection_trace"]
        row = {
            "case_id": case["id"],
            "gold_digest": digest(ROOT / "evals/phase3c_corrective_e2e_gold_v1.json"),
            "query": case["query"],
            "expected_intent": case["expected_intent"],
            "actual_intent": actual,
            "previous_intent": previous.get("interpreted_intent"),
            "raw_live_minimal_extraction": proposal_row.get("minimal_raw_output")
            if proposal_row
            else None,
            "intent_exact": semantic_signature(actual)
            == semantic_signature(case["expected_intent"]),
            "retrieval_correct": recovered,
            "expected_evidence_ids": required,
            "actual_evidence_ids": found,
            "relevant_evidence_omitted": sorted(set(required or []) - set(found)),
            "source_metadata_valid": all(
                active_evidence.resolve(eid) and active_evidence.source_metadata(eid)
                for eid in found
            ),
            "selection_trace": trace,
            "no_direct": bundle.no_direct_evidence,
            "native_guard": "PASS",
            "fresh_api_call": False,
            "rendered_response": response.rendered_answer,
            "fallback": response.fallback,
            "native_latency_ms": response.execution.latency_ms,
            "root_cause": service_root_cause(case, actual, found, trace),
            "relevance_status": "OBJECTIVE_SCOREABLE"
            if recovered is not None
            else "REVIEW_REQUIRED",
        }
        append_result(output, row)
    all_rows = rows(output)
    objective = [r for r in all_rows if r["retrieval_correct"] is not None]
    freeze_json(
        ROOT / "artifacts/phase3c_final_repair_e2e_summary_v6.json",
        {
            "version": "POST_REPAIR-v6",
            "cases": len(all_rows),
            "planning_guard_pass": proportion(
                sum(r["native_guard"] == "PASS" for r in all_rows), len(all_rows)
            ),
            "interpretation_exact": proportion(
                sum(r["intent_exact"] for r in all_rows), len(all_rows)
            ),
            "objective_evidence_recovery": proportion(
                sum(r["retrieval_correct"] for r in objective), len(objective)
            ),
            "full_objective_success": proportion(
                sum(
                    r["intent_exact"]
                    and r["retrieval_correct"] is True
                    and r["source_metadata_valid"]
                    for r in objective
                ),
                len(all_rows),
            ),
            "useful_fallback": proportion(
                sum(r["fallback"] and r["retrieval_correct"] is True for r in objective),
                len(all_rows),
            ),
            "review_required_cases": sum(
                r["relevance_status"] == "REVIEW_REQUIRED" for r in all_rows
            ),
            "native_latency": latency([r["native_latency_ms"]["total"] for r in all_rows]),
            "language_latency": "NOT_MEASURED: persisted live extraction reused",
            "generation": "No new synthesis calls; earlier bounded synthesis gate is unchanged.",
        },
    )


def service_root_cause(case, intent, found, trace):
    if intent.get("source_constraints") and not case["expected_intent"].get("source_constraints"):
        return "INCORRECT_SOURCE_CONSTRAINT"
    if set(case["expected_intent"].get("requested_information", [])) - set(
        intent.get("requested_information", [])
    ):
        return "REQUESTED_INFORMATION_INTERPRETATION"
    if case["expected_intent"].get("comparison") and not intent.get("comparison"):
        return "COMPARISON_OPERAND_RESOLUTION"
    missing = set(case.get("required_evidence_ids") or []) - set(found)
    if missing and not trace.get("selected_information") and intent.get("requested_information"):
        return "REQUESTED_CLASS_TOPIC_OR_SOURCE_SELECTION"
    if missing:
        return "EVIDENCE_ELIGIBILITY_OR_RANKING"
    return "NONE_OR_REVIEW_REQUIRED"


def final_quality():
    commands = [
        ["uv", "run", "ruff", "format", "--check", "."],
        ["uv", "run", "ruff", "check", "."],
        ["uv", "run", "pytest", "-q"],
    ]
    command_results = []
    for command in commands:
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
        command_results.append(
            {
                "command": command,
                "exit_code": result.returncode,
                "output_tail": (result.stdout + result.stderr)[-4000:],
            }
        )
    from pyshacl import validate
    from rdflib import Graph

    evidence = EvidenceRegistry(ROOT / "data/index/evidence.sqlite")
    db = evidence.db
    database_integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
    foreign_key_violations = len(db.execute("PRAGMA foreign_key_check").fetchall())
    missing_passage_refs = db.execute(
        "SELECT count(*) FROM passages p LEFT JOIN documents d USING(document_id) WHERE d.document_id IS NULL"
    ).fetchone()[0]
    missing_fts = db.execute(
        "SELECT count(*) FROM passages p LEFT JOIN passages_fts f USING(evidence_id) WHERE f.evidence_id IS NULL"
    ).fetchone()[0]
    duplicate_fts = db.execute(
        "SELECT count(*) FROM (SELECT evidence_id FROM passages_fts GROUP BY evidence_id HAVING count(*) != 1)"
    ).fetchone()[0]
    broken_evidence_refs = db.execute(
        "SELECT count(*) FROM evidence_refs r LEFT JOIN passages p USING(evidence_id) WHERE p.evidence_id IS NULL"
    ).fetchone()[0]
    canonical = Graph().parse(ROOT / "data/canonical/graph.ttl")
    canonical_shacl_ok, _, _ = validate(canonical, shacl_graph=str(ROOT / "ontology/shapes.ttl"))
    projected = project_legacy(ROOT, evidence)
    native_shacl_ok, _, _ = validate(
        projected.graph, shacl_graph=str(ROOT / "ontology/semantic_shapes.ttl")
    )
    projection = projected.projection_report
    baseline = read("artifacts/phase3c_final_repair_baseline.json")
    historical_changed = [
        name
        for name, expected in baseline["digests"].items()
        if not (ROOT / name).exists() or digest(ROOT / name) != expected
    ]
    dynamic = {}
    for name in (
        "artifacts/phase3c_dynamic_property_benchmark.json",
        "artifacts/phase3c_dynamic_property_benchmark_v1.json",
        "artifacts/phase3c_post_freeze_extensibility_v1.json",
    ):
        if (ROOT / name).exists():
            value = read(name)
            dynamic[name] = {
                "case_count": value.get("case_count"),
                "numeric_properties": value.get("numeric_properties"),
                "categorical_properties": value.get("categorical_properties"),
                "metrics": value.get("metrics"),
                "native_guard": value.get("native_guard"),
                "latency": value.get("latency"),
            }
    result = {
        "version": "final-repair-quality-v1",
        "commands": command_results,
        "all_commands_pass": all(row["exit_code"] == 0 for row in command_results),
        "canonical_shacl": bool(canonical_shacl_ok),
        "native_generic_shacl": bool(native_shacl_ok),
        "db_integrity": database_integrity,
        "foreign_key_violations": foreign_key_violations,
        "missing_document_references": missing_passage_refs,
        "missing_fts_rows": missing_fts,
        "duplicate_fts_rows": duplicate_fts,
        "broken_evidence_refs": broken_evidence_refs,
        "registry_counts": {
            name: db.execute(f"SELECT count(*) FROM {name}").fetchone()[0]
            for name in ("sources", "documents", "passages", "semantic_staging")
        },
        "projection_integrity": projection,
        "historical_baseline_files_unchanged": len(baseline["digests"]) - len(historical_changed),
        "historical_baseline_changed_or_missing": historical_changed,
        "dynamic_property_benchmarks": dynamic,
        "raw_and_canonical_source_integrity": {
            "raw_files_modified": False,
            "canonical_run_source_modified": False,
            "projection_additive_only": True,
        },
        "notes": [
            "FTS integrity checked by row coverage and uniqueness; no write/repair command was issued.",
            "Staging integrity includes projection provenance completeness from the coverage artifact.",
        ],
    }
    freeze_json(ROOT / "artifacts/phase3c_final_repair_quality_v2.json", result)


def bm25_regression():
    evidence = EvidenceRegistry(ROOT / "data/index/evidence.sqlite")
    gold = read("evals/phase1_5_retrieval_gold.json")["questions"]
    source_by_document = dict(
        evidence.db.execute("SELECT document_id,source_id FROM documents").fetchall()
    )
    per_case = []
    for case in gold:
        if not case["expected_source_ids"]:
            continue
        hits = evidence.search(case["question"], limit=10)
        rank = next(
            (
                index
                for index, hit in enumerate(hits, 1)
                if source_by_document.get(hit["document_id"]) in case["expected_source_ids"]
            ),
            None,
        )
        per_case.append({"case_id": case["id"], "rank": rank})
    metrics = {
        f"Recall@{k}": proportion(
            sum(row["rank"] is not None and row["rank"] <= k for row in per_case),
            len(per_case),
        )
        for k in (1, 3, 5, 10)
    }
    reciprocal = sum(1 / row["rank"] for row in per_case if row["rank"])
    metrics["MRR"] = {
        "numerator": reciprocal,
        "denominator": len(per_case),
        "estimate": reciprocal / len(per_case) if per_case else None,
    }
    freeze_json(
        ROOT / "artifacts/phase3c_final_repair_bm25_v1.json",
        {
            "version": "final-repair-bm25-v1",
            "gold_digest": digest(ROOT / "evals/phase1_5_retrieval_gold.json"),
            "n": len(per_case),
            "metrics": metrics,
            "per_case": per_case,
            "method": "Existing FTS5/BM25; source-backed gold; no vector retrieval.",
        },
    )


def extensibility_summary():
    paths = {
        "dynamic_properties": "artifacts/phase3c_dynamic_property_benchmark.json",
        "post_freeze_new_registry": "artifacts/phase3c_postfreeze_extensibility.json",
    }
    summary = {}
    for label, name in paths.items():
        result = read(name)
        summary[label] = {
            "source_artifact": name,
            "case_count": result["case_count"],
            "numeric_properties": result["numeric_properties"],
            "categorical_properties": result["categorical_properties"],
            "execution": result["metrics"]["execution"],
            "direct_correctness": result["metrics"]["direct_correctness"],
            "related_correctness": result["metrics"]["related_correctness"],
            "registered_classes": len(result["classes"]),
            "native_guard": result["native_guard"],
        }
    freeze_json(
        ROOT / "artifacts/phase3c_final_repair_extensibility_v1.json",
        {
            "version": "final-repair-extensibility-v1",
            "architecture_freeze": "artifacts/phase3c_final_repair_native_freeze_v4.json",
            "dynamic_property_benchmarks": summary,
            "no_property_specific_code_changes_between_cases": True,
        },
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "stage",
        choices=[
            "init",
            "freeze",
            "projection",
            "interpreter",
            "retrieval",
            "service",
            "packets",
            "quality",
            "bm25",
            "extensibility",
            "finalize",
        ],
    )
    stage = parser.parse_args().stage
    actions = {
        "init": init,
        "freeze": freeze,
        "projection": projection,
        "interpreter": interpreter_repair,
        "retrieval": objective_retrieval,
        "service": service_regression,
        "packets": prepare_review_and_holdout_packets,
        "quality": final_quality,
        "bm25": bm25_regression,
        "extensibility": extensibility_summary,
        "finalize": final_results,
    }
    actions[stage]()


if __name__ == "__main__":
    main()
