"""Gold reconciliation and resumable controlled-reasoning ablation runner."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from statistics import median

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.semantic import project_legacy
from nasa_fire_ai.llm.interfaces import NvidiaStructuredClient
from nasa_fire_ai.llm.jev import JevSettings, classify_epistemic, decision_value, list_models
from nasa_fire_ai.query.controlled_reasoning import (
    ControlledReasoningFlags,
    NemotronControlledReasoner,
    run_ablation,
    validate_expansion,
)
from nasa_fire_ai.query.v2 import QueryIntentV2

INTERPRETER = ROOT / "artifacts/phase3c_final_repair_interpreter_cases_v6.jsonl"
PROPOSAL = ROOT / "docs/documents3cPropose/NASA_PHASE3C_RECONCILIACION_GOLD_PROPUESTAS_v1.json"
OBJECTIVE = ROOT / "artifacts/phase3c_final_repair_objective_retrieval_v2.jsonl"
GOLD_OUT = ROOT / "artifacts/phase3c_controlled_gold_reconciliation_proposed_v1.json"
ABLATION_GOLD = ROOT / "evals/phase3c_controlled_ablation_regression_gold_v1.json"
CALLS_OUT = ROOT / "artifacts/phase3c_controlled_reasoning_api_calls_v1.jsonl"
CASES_OUT = ROOT / "artifacts/phase3c_controlled_ablation_cases_v1.jsonl"
SUMMARY_OUT = ROOT / "artifacts/phase3c_controlled_ablation_summary_v1.json"
JEV_CALLS_OUT = ROOT / "artifacts/phase3c_controlled_reasoning_jev_calls_v1.jsonl"
CASES_V2_OUT = ROOT / "artifacts/phase3c_controlled_ablation_cases_v2.jsonl"
CALLS_V2_OUT = ROOT / "artifacts/phase3c_controlled_reasoning_api_calls_v2.jsonl"
SUMMARY_V2_OUT = ROOT / "artifacts/phase3c_controlled_ablation_summary_v2.json"
CASES_V3_OUT = ROOT / "artifacts/phase3c_controlled_ablation_cases_v3.jsonl"
CALLS_V3_OUT = ROOT / "artifacts/phase3c_controlled_reasoning_api_calls_v3.jsonl"
SUMMARY_V3_OUT = ROOT / "artifacts/phase3c_controlled_ablation_summary_v3.json"


def digest(value) -> str:
    if isinstance(value, Path):
        raw = value.read_bytes()
    elif isinstance(value, bytes):
        raw = value
    else:
        raw = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode()
    return hashlib.sha256(raw).hexdigest()


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def reconcile_gold() -> dict:
    cases = load_jsonl(INTERPRETER)
    suggestions = json.loads(PROPOSAL.read_text())
    suggested = {row["case_id"]: row for row in suggestions["adjudication_proposals"]}
    mismatches = []
    for row in cases:
        gold = row["expected_intent"]
        predicted = row["repaired_resolved_intent"]
        expected_info = gold.get("requested_information", [])
        predicted_info = predicted.get("requested_information", [])
        if expected_info == predicted_info:
            continue
        case_id = row["case_id"]
        proposal = suggested.get(case_id, {})
        target_duplication = "ExperimentalRun" in expected_info and "ExperimentalRun" in gold.get(
            "targets", []
        )
        proposed_info = proposal.get("proposed_requested_information")
        if target_duplication:
            status = "STRUCTURAL_CONTRACT_CORRECTION_PROPOSED"
            rationale = (
                "ExperimentalRun is already represented as the requested target in this case; "
                "whether it is duplicated as epistemic requested_information is a contract question. "
                "This is a diagnostic proposal only, not approved gold."
            )
            structural = True
        elif case_id == "qi27" or proposed_info is None:
            status = "UNRESOLVED"
            rationale = proposal.get(
                "justification", "Broad 'reported' information class needs contract adjudication."
            )
            structural = False
        else:
            status = "SEMANTIC_REVIEW_REQUIRED"
            rationale = proposal.get(
                "justification", "The requested epistemic scope is a semantic gold judgment."
            )
            structural = False
        mismatches.append(
            {
                "case_id": case_id,
                "question": row["query"],
                "original_gold": {
                    "targets": gold.get("targets", []),
                    "requested_information": expected_info,
                },
                "current_model_intent": {
                    "targets": predicted.get("targets", []),
                    "requested_information": predicted_info,
                },
                "proposed_revised_intent": {
                    "targets": gold.get("targets", []),
                    "requested_information": proposed_info,
                },
                "reason": rationale,
                "structural_or_scientific_judgment": "STRUCTURAL" if structural else "SEMANTIC",
                "adjudication_status": status,
                "expert_reviewed": False,
                "historical_gold_modified": False,
            }
        )
    output = {
        "version": "phase3c-controlled-gold-reconciliation-proposed-v1",
        "status": "PROPOSAL_ONLY_NOT_FROZEN_GOLD",
        "reviewer": "technical reconciliation; no independent scientist review",
        "human_expert_validated": False,
        "historical_gold_modified": False,
        "source_digests": {
            str(INTERPRETER.relative_to(ROOT)): digest(INTERPRETER),
            str(PROPOSAL.relative_to(ROOT)): digest(PROPOSAL),
        },
        "recomputed_discrepancy_count": len(mismatches),
        "discrepancies": mismatches,
        "sensitivity_metrics": {
            "denominator": len(cases),
            "gold_requested_information_mismatch_n": len(mismatches),
            "status_counts": {
                status: sum(x["adjudication_status"] == status for x in mismatches)
                for status in sorted({x["adjudication_status"] for x in mismatches})
            },
            "interpretation": "Diagnostic only; no corrected exact-match score is reported because none of the proposals has approval.",
        },
    }
    GOLD_OUT.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n")
    return output


def freeze_ablation_gold() -> dict:
    rows = load_jsonl(OBJECTIVE)
    gold = {
        "version": "phase3c-controlled-ablation-regression-gold-v1",
        "status": "EXPOSED_REGRESSION_NOT_INDEPENDENT_RELEVANCE_GOLD",
        "source": str(OBJECTIVE.relative_to(ROOT)),
        "source_digest": digest(OBJECTIVE),
        "cases": [
            {
                "case_id": row["case_id"],
                "query": row["query"],
                "expected_intent": row["intent"],
                "required_evidence_ids": row["expected_evidence_ids"],
                "gold_basis": "Frozen source-backed evidence identity or justified no-answer state; not complete scientific relevance gold.",
                "expected_no_direct": row["no_direct"],
                "review_status": "OBJECTIVE_IDENTITY_REGRESSION",
                "not_independent_relevance": True,
            }
            for row in rows
        ],
    }
    if ABLATION_GOLD.exists() and json.loads(ABLATION_GOLD.read_text()) != gold:
        raise RuntimeError("Frozen controlled ablation regression gold already exists and differs")
    ABLATION_GOLD.write_text(json.dumps(gold, indent=2, ensure_ascii=False) + "\n")
    return gold


def _dump_case(result: dict, case: dict, benchmark_digest: str, run_profile: str) -> dict:
    configurations = {}
    for key, value in result["configurations"].items():
        configurations[key] = {
            "candidate_ids": value.get("candidate_ids", []),
            "contextual_candidate_ids": [
                x.get("evidence_id") for x in value.get("contextual_candidates", [])
            ],
            "expansion": value.get("expansion"),
            "search_traces": value.get("search_traces"),
            "reranking": value.get("reranking"),
            "jev": value.get("jev"),
            "calls": value.get("calls", 0),
        }
    return {
        "case_id": case["case_id"],
        "query": case["query"],
        "benchmark_digest": benchmark_digest,
        "run_profile": run_profile,
        "intent_digest": result["intent_digest"],
        "model": result["model"],
        "prompt_versions": result["prompt_versions"],
        "features": result["features"],
        "required_evidence_ids": case["required_evidence_ids"],
        "native_direct_ids": result["native_direct_ids"],
        "native_related_ids": result["native_related_ids"],
        "latency_ms": result["latency_ms"],
        "configurations": configurations,
        "errors": result["errors"],
        "gold_status": case["review_status"],
    }


def run_benchmark(live: bool, jev_enabled: bool = False) -> dict:
    if not ABLATION_GOLD.exists():
        gold = freeze_ablation_gold()
    else:
        gold = json.loads(ABLATION_GOLD.read_text())
    benchmark_digest = digest(gold)
    run_profile = f"nvidia:{int(live)};jev:{int(jev_enabled)}"
    completed = {}
    if CASES_OUT.exists():
        for row in load_jsonl(CASES_OUT):
            if (
                row.get("benchmark_digest") == benchmark_digest
                and row.get("run_profile") == run_profile
            ):
                completed[row["case_id"]] = row
    settings = Settings()
    evidence = EvidenceRegistry(settings.registry_path)
    store = project_legacy(ROOT, evidence)
    language = yaml.safe_load((ROOT / "domain/query_language_v2.yaml").read_text())
    reasoner = None
    jev_cache = {}
    if live:
        provider = NvidiaStructuredClient(
            settings.nvidia_api_key, settings.nvidia_base_url, settings.nvidia_phase3_model
        )

        def persist_call(event: dict) -> None:
            event["benchmark_digest"] = benchmark_digest
            event["created_by"] = "phase3c-controlled-ablation-v1"
            with CALLS_OUT.open("a") as stream:
                stream.write(json.dumps(event, ensure_ascii=False) + "\n")
                stream.flush()

        call_cache = {}
        if CALLS_OUT.exists():
            for event in load_jsonl(CALLS_OUT):
                if event.get("benchmark_digest") == benchmark_digest and event.get("cache_key"):
                    call_cache[event["cache_key"]] = event
        reasoner = NemotronControlledReasoner(
            provider.client,
            settings.nvidia_phase3_model,
            store.registry,
            language,
            event_sink=persist_call,
            cache=call_cache,
        )
    jev_settings = JevSettings()
    jev_metadata = {
        "requested": jev_enabled,
        "configured_alias": jev_settings.model,
        "status": "NOT_REQUESTED",
    }
    jev_advisor = None
    if jev_enabled:
        try:
            models = list_models(jev_settings)
            model_rows = models.get("data", models.get("models", []))
            model_ids = [
                str(row.get("id")) for row in model_rows if isinstance(row, dict) and row.get("id")
            ]
            jev_metadata.update({"available_models": model_ids, "status": "DISCOVERED"})
            if model_ids and jev_settings.model not in model_ids:
                jev_metadata.update({"status": "MODEL_ALIAS_NOT_LISTED", "calls_enabled": False})
            else:
                jev_metadata["calls_enabled"] = True
                if JEV_CALLS_OUT.exists():
                    for event in load_jsonl(JEV_CALLS_OUT):
                        if event.get("benchmark_digest") == benchmark_digest:
                            jev_cache[event["input_digest"]] = event

                def jev_advisor(candidate):
                    input_digest = digest(
                        [
                            candidate["evidence_id"],
                            candidate.get("text", ""),
                            candidate.get("source_metadata"),
                        ]
                    )
                    if input_digest in jev_cache:
                        return jev_cache[input_digest]["proposal"]
                    raw = classify_epistemic(
                        {
                            "passage": candidate.get("text", "")[:1800],
                            "source": candidate.get("source_metadata"),
                        },
                        jev_settings,
                    )
                    label, confidence = decision_value(raw, "epistemic_type")
                    event = {
                        "benchmark_digest": benchmark_digest,
                        "input_digest": input_digest,
                        "evidence_id": candidate["evidence_id"],
                        "model_alias": jev_settings.model,
                        "response_model": raw.get("model") if isinstance(raw, dict) else None,
                        "proposal": {"label": label, "confidence": confidence},
                        "raw_response": raw,
                    }
                    with JEV_CALLS_OUT.open("a") as stream:
                        stream.write(json.dumps(event, ensure_ascii=False) + "\n")
                        stream.flush()
                    jev_cache[input_digest] = event
                    return event["proposal"]

        except Exception as error:  # noqa: BLE001 - Jev is optional and cannot block retrieval
            jev_metadata.update({"status": "API_UNAVAILABLE", "error_type": type(error).__name__})
            jev_advisor = None
    flags = ControlledReasoningFlags(
        query_expansion=live,
        contextual_reranking=live,
        jev_advisory_triage=jev_enabled and bool(jev_advisor),
    )
    for case in gold["cases"]:
        prior = completed.get(case["case_id"])
        if prior:
            continue
        intent = QueryIntentV2.model_validate(case["expected_intent"])
        result = run_ablation(
            case["query"],
            intent,
            store,
            evidence,
            reasoner=reasoner,
            flags=flags,
            jev_advisor=jev_advisor,
        )
        output = _dump_case(result, case, benchmark_digest, run_profile)
        with CASES_OUT.open("a") as stream:
            stream.write(json.dumps(output, ensure_ascii=False) + "\n")
            stream.flush()
        completed[case["case_id"]] = output
        print(json.dumps({"completed": case["case_id"], "cases": len(completed)}), flush=True)
    summary = summarize(gold, list(completed.values()), benchmark_digest, live)
    summary["jev_model_discovery"] = jev_metadata
    summary["run_profile"] = run_profile
    SUMMARY_OUT.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    return summary


def run_second_pass(live: bool, iteration: int = 2) -> dict:
    """Revalidate frozen expansion proposals and rerun only changed candidate pools."""
    gold = json.loads(ABLATION_GOLD.read_text())
    benchmark_digest = digest(gold)
    case_output = CASES_V2_OUT if iteration == 2 else CASES_V3_OUT
    call_output = CALLS_V2_OUT if iteration == 2 else CALLS_V3_OUT
    summary_output = SUMMARY_V2_OUT if iteration == 2 else SUMMARY_V3_OUT
    budget = 12 if iteration >= 3 else 40
    run_profile = f"strict-expansion-v{iteration};rerank-budget-{budget};nvidia-rerank:{int(live)}"
    original_rows = [
        row
        for row in load_jsonl(CASES_OUT)
        if row.get("benchmark_digest") == benchmark_digest
        and row.get("run_profile") == "nvidia:1;jev:1"
    ]
    by_query = {row["query"]: row for row in original_rows}
    completed = {}
    if case_output.exists():
        for row in load_jsonl(case_output):
            if (
                row.get("benchmark_digest") == benchmark_digest
                and row.get("run_profile") == run_profile
            ):
                completed[row["case_id"]] = row
    settings = Settings()
    evidence = EvidenceRegistry(settings.registry_path)
    store = project_legacy(ROOT, evidence)
    language = yaml.safe_load((ROOT / "domain/query_language_v2.yaml").read_text())
    provider = None
    actual_reasoner = None
    cache = {}
    if CALLS_OUT.exists():
        for event in load_jsonl(CALLS_OUT):
            if event.get("benchmark_digest") == benchmark_digest and event.get("cache_key"):
                cache[event["cache_key"]] = event
    for cache_path in (CALLS_V2_OUT, CALLS_V3_OUT):
        if cache_path.exists():
            for event in load_jsonl(cache_path):
                if event.get("benchmark_digest") == benchmark_digest and event.get("cache_key"):
                    cache[event["cache_key"]] = event
    if live:
        provider = NvidiaStructuredClient(
            settings.nvidia_api_key, settings.nvidia_base_url, settings.nvidia_phase3_model
        )

        def persist_call(event: dict) -> None:
            event["benchmark_digest"] = benchmark_digest
            event["created_by"] = f"phase3c-controlled-ablation-iteration-{iteration}"
            with call_output.open("a") as stream:
                stream.write(json.dumps(event, ensure_ascii=False) + "\n")
                stream.flush()

        actual_reasoner = NemotronControlledReasoner(
            provider.client,
            settings.nvidia_phase3_model,
            store.registry,
            language,
            event_sink=persist_call,
            cache=cache,
        )

    class ReplayedExpansion:
        model_identity = settings.nvidia_phase3_model if live else None

        def expand(self, query, intent):
            prior = by_query[query]["configurations"]["B"]["expansion"]
            output = {
                "version": prior.get("version"),
                "source": f"replayed_model_proposal_revalidated_under_policy_v{iteration}",
                "model": prior.get("model"),
                "query_digest": digest(query),
                "intent_digest": digest(intent.model_dump(mode="json")),
                "accepted": [],
                "rejected": [],
                "error": prior.get("error"),
                "usage": prior.get("usage", {}),
            }
            proposals = prior.get("accepted", []) + prior.get("rejected", [])
            for item in proposals:
                candidate = item["query"]
                valid, reason = validate_expansion(
                    query, candidate, intent, store.registry, language
                )
                output["accepted" if valid else "rejected"].append(
                    {"query": candidate, "accepted": valid, "reason": reason}
                )
            return output

        def rerank(self, query, intent, candidates):
            if actual_reasoner:
                return actual_reasoner.rerank(query, intent, candidates)
            prior = by_query[query]["configurations"]["C"].get("reranking")
            if prior and prior.get("candidate_input_ids") == sorted(
                c["evidence_id"] for c in candidates
            ):
                return prior
            return {
                "judgments": [],
                "invalid": [],
                "error": "rerank_not_reexecuted_without_live_model",
                "usage": {},
            }

    replay_reasoner = ReplayedExpansion()
    prior_jev = {}
    if JEV_CALLS_OUT.exists():
        for event in load_jsonl(JEV_CALLS_OUT):
            if event.get("benchmark_digest") == benchmark_digest:
                prior_jev[event["input_digest"]] = event["proposal"]

    def jev_replay(candidate):
        key = digest(
            [candidate["evidence_id"], candidate.get("text", ""), candidate.get("source_metadata")]
        )
        return prior_jev.get(key, {"label": None, "confidence": None, "cached": False})

    flags = ControlledReasoningFlags(
        query_expansion=True,
        contextual_reranking=True,
        jev_advisory_triage=bool(prior_jev),
    )
    for case in gold["cases"]:
        if case["case_id"] in completed:
            continue
        intent = QueryIntentV2.model_validate(case["expected_intent"])
        result = run_ablation(
            case["query"],
            intent,
            store,
            evidence,
            reasoner=replay_reasoner,
            flags=flags,
            jev_advisor=jev_replay if prior_jev else None,
        )
        output = _dump_case(result, case, benchmark_digest, run_profile)
        output["version"] = f"post_strict_expansion_filter_iteration_{iteration}"
        with case_output.open("a") as stream:
            stream.write(json.dumps(output, ensure_ascii=False) + "\n")
            stream.flush()
        completed[case["case_id"]] = output
        print(
            json.dumps({"second_pass_completed": case["case_id"], "cases": len(completed)}),
            flush=True,
        )
    summary = summarize(gold, list(completed.values()), benchmark_digest, live)
    summary.update(
        {
            "run_profile": run_profile,
            "version": f"phase3c-controlled-ablation-results-v{iteration}",
            "status": "SECOND_PASS_AFTER_GENERIC_CONCEPT_EXPANSION_FILTER_FIX",
            "first_pass": str(CASES_OUT.relative_to(ROOT)),
            "second_pass_changes": "Model expansion proposals replayed from immutable first pass; added registered concepts now rejected unless present in query or validated intent. Changed pools reranked live when requested; iteration 3 caps reranker input at 12 passages.",
        }
    )
    summary_output.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    return summary


def summarize(gold: dict, rows: list[dict], benchmark_digest: str, live: bool) -> dict:
    cases = {row["case_id"]: row for row in rows}
    counts = {}
    latencies = {name: [] for name in ("native_total", "expansion", "reranking")}
    false_direct = 0
    for config in "ABCD":
        values = {
            k: 0
            for k in (
                "identity_recall_at_1",
                "identity_recall_at_5",
                "identity_recall_at_10",
                "identity_recovered_anywhere",
            )
        }
        denominator = 0
        for case in gold["cases"]:
            row = cases.get(case["case_id"])
            if not row:
                continue
            expected = set(case["required_evidence_ids"])
            candidate_ids = row["configurations"][config]["candidate_ids"]
            if expected:
                denominator += 1
                values["identity_recovered_anywhere"] += bool(expected & set(candidate_ids))
                for k in (1, 5, 10):
                    values[f"identity_recall_at_{k}"] += bool(expected & set(candidate_ids[:k]))
            false_direct += bool(row["native_direct_ids"] and not expected) if config == "A" else 0
        counts[config] = {
            metric: {
                "numerator": int(value),
                "denominator": denominator,
                "estimate": value / denominator if denominator else None,
            }
            for metric, value in values.items()
        }
    for row in rows:
        for key, values in latencies.items():
            latency_key = {"expansion": "query_expansion"}.get(key, key)
            if row["latency_ms"].get(latency_key) is not None:
                values.append(row["latency_ms"][latency_key])
        for key in ("expansion", "reranking"):
            config = row["configurations"].get("B" if key == "expansion" else "C", {})
            details = config.get(key)
            if details and details.get("error"):
                pass
    summary = {
        "version": "phase3c-controlled-ablation-results-v1",
        "status": "MEASURED_EXPOSED_REGRESSION_NOT_INDEPENDENT_RELEVANCE_EVALUATION",
        "gold_digest": benchmark_digest,
        "model": rows[0]["model"] if rows else None,
        "live_nemotron": live,
        "N": len(rows),
        "gold_status": gold["status"],
        "configuration_metrics": counts,
        "metrics_warning": "The frozen gold contains expected evidence identities, not complete relevance judgments. These are identity-recovery diagnostics only; precision and scientific relevance are not scoreable.",
        "false_direct_promotions": {
            "numerator": 0,
            "denominator": len(rows),
            "estimate": 0.0,
            "basis": "controlled candidates never modify native DIRECT/RELATED fields",
        },
        "native_direct_ids_on_no_answer_cases": {
            "numerator": sum(
                bool(cases.get(case["case_id"], {}).get("native_direct_ids"))
                for case in gold["cases"]
                if not case["required_evidence_ids"] and case["case_id"] in cases
            ),
            "denominator": sum(
                not case["required_evidence_ids"] and case["case_id"] in cases
                for case in gold["cases"]
            ),
            "interpretation": "No-answer correctness requires independent evidence relevance labels; this count only checks whether baseline canonical DIRECT remained empty.",
        },
        "latency_ms": {
            key: {
                "N": len(vals),
                "median": median(vals) if vals else None,
                "max": max(vals) if vals else None,
            }
            for key, vals in latencies.items()
        },
        "api_cost": "not provided by response API",
        "unreviewed_e2e_cases": "Preserved in existing review packet; not silently relabeled.",
        "jev": "Not invoked by this runner unless explicitly configured through a separate adapter; prior Jev triage is not query-specific relevance truth.",
    }
    SUMMARY_OUT.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=(
            "reconcile",
            "freeze-gold",
            "benchmark",
            "benchmark-live",
            "benchmark-live-jev",
            "benchmark-second-pass",
            "benchmark-second-pass-live",
            "benchmark-third-pass",
            "benchmark-third-pass-live",
        ),
    )
    args = parser.parse_args()
    if args.command == "reconcile":
        print(json.dumps(reconcile_gold(), ensure_ascii=False))
    elif args.command == "freeze-gold":
        print(json.dumps(freeze_ablation_gold(), ensure_ascii=False))
    elif args.command.startswith("benchmark-second-pass"):
        print(
            json.dumps(
                run_second_pass(live=args.command == "benchmark-second-pass-live"),
                ensure_ascii=False,
            )
        )
    elif args.command.startswith("benchmark-third-pass"):
        print(
            json.dumps(
                run_second_pass(live=args.command == "benchmark-third-pass-live", iteration=3),
                ensure_ascii=False,
            )
        )
    else:
        print(
            json.dumps(
                run_benchmark(
                    live=args.command in {"benchmark-live", "benchmark-live-jev"},
                    jev_enabled=args.command == "benchmark-live-jev",
                ),
                ensure_ascii=False,
            )
        )


if __name__ == "__main__":
    main()
