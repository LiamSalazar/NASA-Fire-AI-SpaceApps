"""Controlled A/B/C/D discovery ablation on the full exposed 20-case receipt."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from statistics import median

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from phase3c_controlled_reasoning import digest, load_jsonl

from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.semantic import project_legacy
from nasa_fire_ai.llm.interfaces import NvidiaStructuredClient
from nasa_fire_ai.llm.jev import JevSettings, classify_epistemic, decision_value, list_models
from nasa_fire_ai.query.controlled_reasoning import (
    ControlledReasoningFlags,
    NemotronControlledReasoner,
    run_ablation,
)
from nasa_fire_ai.query.v2 import QueryIntentV2

SOURCE = ROOT / "artifacts/phase3c_final_repair_e2e_cases_v6.jsonl"
GOLD = ROOT / "evals/phase3c_controlled_e2e_regression_gold_v1.json"
CASES = ROOT / "artifacts/phase3c_controlled_e2e_ablation_cases_v1.jsonl"
CALLS = ROOT / "artifacts/phase3c_controlled_e2e_api_calls_v1.jsonl"
JEV_CALLS = ROOT / "artifacts/phase3c_controlled_e2e_jev_calls_v1.jsonl"
SUMMARY = ROOT / "artifacts/phase3c_controlled_e2e_ablation_summary_v1.json"
REVIEW = ROOT / "artifacts/phase3c_controlled_scientific_relevance_review_packet_v1.json"
CASES_V2 = ROOT / "artifacts/phase3c_controlled_e2e_ablation_cases_v2.jsonl"
CALLS_V2 = ROOT / "artifacts/phase3c_controlled_e2e_api_calls_v2.jsonl"
SUMMARY_V2 = ROOT / "artifacts/phase3c_controlled_e2e_ablation_summary_v2.json"
CASES_V3 = ROOT / "artifacts/phase3c_controlled_e2e_ablation_cases_v3.jsonl"
CALLS_V3 = ROOT / "artifacts/phase3c_controlled_e2e_api_calls_v3.jsonl"
SUMMARY_V3 = ROOT / "artifacts/phase3c_controlled_e2e_ablation_summary_v3.json"
CASES_V4 = ROOT / "artifacts/phase3c_controlled_e2e_ablation_cases_v4.jsonl"
CALLS_V4 = ROOT / "artifacts/phase3c_controlled_e2e_api_calls_v4.jsonl"
SUMMARY_V4 = ROOT / "artifacts/phase3c_controlled_e2e_ablation_summary_v4.json"
JEV_CALLS_V1 = JEV_CALLS


def freeze_gold() -> dict:
    source_rows = load_jsonl(SOURCE)
    gold_cases = []
    source_is_absent = True
    db = Settings().registry_path
    import sqlite3

    conn = sqlite3.connect(db)
    source_is_absent = not conn.execute(
        "SELECT 1 FROM sources WHERE source_id=? OR nasa_id=? LIMIT 1",
        ("20140011119", "20140011119"),
    ).fetchone()
    conn.close()
    for row in source_rows:
        ids = row.get("expected_evidence_ids") or []
        status = row.get("relevance_status")
        no_answer = False
        basis = None
        if status == "OBJECTIVE_SCOREABLE" and not ids:
            intent = row["expected_intent"]
            if intent.get("clarification_required") or intent.get("unresolved_mentions"):
                no_answer = True
                basis = "Frozen gold intent requires clarification or retains an unresolved term; no canonical direct evidence is eligible."
            elif row["case_id"] == "corrective-unseen-document" and source_is_absent:
                no_answer = True
                basis = "Exact source ID absent from frozen local source registry at gold-freeze time; this is corpus-scoped, not a claim NASA has no such source."
        gold_cases.append(
            {
                "case_id": row["case_id"],
                "query": row["query"],
                "expected_intent": row["expected_intent"],
                "required_evidence_ids": ids,
                "expected_no_direct": no_answer,
                "no_direct_basis": basis,
                "relevance_status": status,
                "scoreable_identity_case": bool(ids) and status == "OBJECTIVE_SCOREABLE",
                "review_required": status == "REVIEW_REQUIRED",
                "gold_digest": row.get("gold_digest"),
            }
        )
    gold = {
        "version": "phase3c-controlled-e2e-regression-gold-v1",
        "status": "EXPOSED_REGRESSION_WITH_REVIEW_REQUIRED_CASES",
        "source": str(SOURCE.relative_to(ROOT)),
        "source_digest": digest(SOURCE),
        "source_registry_absent_20140011119": bool(source_is_absent),
        "human_relevance_review_performed": False,
        "cases": gold_cases,
    }
    if GOLD.exists() and json.loads(GOLD.read_text()) != gold:
        raise RuntimeError("Frozen 20-case controlled E2E gold differs; refusing mutation")
    GOLD.write_text(json.dumps(gold, indent=2, ensure_ascii=False) + "\n")
    return gold


def _serialize_case(case: dict, result: dict, benchmark_digest: str, profile: str) -> dict:
    configs = {}
    for name, item in result["configurations"].items():
        configs[name] = {
            "candidate_ids": item.get("candidate_ids", []),
            "contextual_candidate_ids": [
                x.get("evidence_id") for x in item.get("contextual_candidates", [])
            ],
            "expansion": item.get("expansion"),
            "search_traces": item.get("search_traces"),
            "reranking": item.get("reranking"),
            "jev": item.get("jev"),
        }
    return {
        "case_id": case["case_id"],
        "query": case["query"],
        "benchmark_digest": benchmark_digest,
        "run_profile": profile,
        "intent_digest": result["intent_digest"],
        "model": result["model"],
        "prompt_versions": result["prompt_versions"],
        "features": result["features"],
        "gold_status": case["relevance_status"],
        "required_evidence_ids": case["required_evidence_ids"],
        "expected_no_direct": case["expected_no_direct"],
        "native_direct_ids": result["native_direct_ids"],
        "native_related_ids": result["native_related_ids"],
        "latency_ms": result["latency_ms"],
        "configurations": configs,
    }


def run_rerank_second_pass() -> dict:
    """Re-use frozen expansion/Jev proposals and retry reranking with a bounded contract."""
    gold = json.loads(GOLD.read_text())
    gold_digest = digest(gold)
    first_pass = {
        row["case_id"]: row
        for row in load_jsonl(CASES)
        if row.get("benchmark_digest") == gold_digest
        and row.get("run_profile") == "nvidia-live;jev:1;rerank-budget-12"
    }
    if len(first_pass) != len(gold["cases"]):
        raise RuntimeError("Second pass requires complete immutable first-pass case coverage")
    profile = "rerank-v4;compact-span-contract;candidate-budget-5;jev-replayed"
    completed = (
        {
            row["case_id"]: row
            for row in load_jsonl(CASES_V4)
            if row.get("benchmark_digest") == gold_digest and row.get("run_profile") == profile
        }
        if CASES_V4.exists()
        else {}
    )

    settings = Settings()
    evidence = EvidenceRegistry(settings.registry_path)
    store = project_legacy(ROOT, evidence)
    language = yaml.safe_load((ROOT / "domain/query_language_v2.yaml").read_text())
    provider = NvidiaStructuredClient(
        settings.nvidia_api_key, settings.nvidia_base_url, settings.nvidia_phase3_model
    )

    def persist_call(event):
        event["benchmark_digest"] = gold_digest
        event["run_profile"] = profile
        with CALLS_V4.open("a") as stream:
            stream.write(json.dumps(event, ensure_ascii=False) + "\n")
            stream.flush()

    reasoner = NemotronControlledReasoner(
        provider.client,
        settings.nvidia_phase3_model,
        store.registry,
        language,
        event_sink=persist_call,
    )

    prior_jev = {}
    if JEV_CALLS_V1.exists():
        for event in load_jsonl(JEV_CALLS_V1):
            if event.get("benchmark_digest") == gold_digest:
                prior_jev[event["input_digest"]] = event["proposal"]

    def jev_replay(candidate):
        key = digest(
            [candidate["evidence_id"], candidate.get("text", ""), candidate.get("source_metadata")]
        )
        return prior_jev.get(key, {"label": None, "confidence": None, "cached": False})

    class FrozenExpansionReasoner:
        model_identity = settings.nvidia_phase3_model

        def expand(self, query, _intent):
            frozen = next(row for row in first_pass.values() if row["query"] == query)
            return frozen["configurations"]["B"]["expansion"]

        def rerank(self, query, intent, candidates):
            return reasoner.rerank(query, intent, candidates)

    replay = FrozenExpansionReasoner()
    flags = ControlledReasoningFlags(
        query_expansion=True,
        contextual_reranking=True,
        jev_advisory_triage=bool(prior_jev),
    )
    for case in gold["cases"]:
        if case["case_id"] in completed:
            continue
        source_row = first_pass[case["case_id"]]
        intent = QueryIntentV2.model_validate(case["expected_intent"])
        result = run_ablation(
            case["query"],
            intent,
            store,
            evidence,
            reasoner=replay,
            flags=flags,
            jev_advisor=jev_replay if prior_jev else None,
            per_query_limit=20,
        )
        row = _serialize_case(case, result, gold_digest, profile)
        row["expansion_replayed_from_first_pass"] = source_row["configurations"]["B"]["expansion"]
        with CASES_V4.open("a") as stream:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
            stream.flush()
        completed[case["case_id"]] = row
        print(
            json.dumps({"second_pass_completed": case["case_id"], "n": len(completed)}), flush=True
        )

    summary = summarize(gold, list(completed.values()), gold_digest, profile)
    summary["version"] = "phase3c-controlled-e2e-ablation-summary-v4"
    summary["status"] = "FOURTH_PASS_COMPACT_VERBATIM_SPAN_CONTRACT; EARLIER_PASSES_PRESERVED"
    summary["first_pass_artifact"] = str(CASES.relative_to(ROOT))
    summary["fourth_pass_changes"] = {
        "classification": "GENERIC_BUG_FIX / PROMPT_AND_BUDGET_REDUCTION",
        "candidate_budget": 5,
        "max_passage_characters": 700,
        "max_output_tokens": 900,
        "required_verbatim_support_span_for_high_medium": True,
        "expansions": "replayed from immutable first pass; no repeat expansion calls",
        "jev": "replayed from first-pass advisory receipts; no new Jev calls",
        "native_direct_related": "recomputed by unchanged native executor",
    }
    SUMMARY_V4.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    return summary


def run_live(jev_enabled: bool = True) -> dict:
    gold = json.loads(GOLD.read_text()) if GOLD.exists() else freeze_gold()
    gold_digest = digest(gold)
    profile = f"nvidia-live;jev:{int(jev_enabled)};rerank-budget-12"
    completed = {}
    if CASES.exists():
        for row in load_jsonl(CASES):
            if row.get("benchmark_digest") == gold_digest and row.get("run_profile") == profile:
                completed[row["case_id"]] = row
    settings = Settings()
    evidence = EvidenceRegistry(settings.registry_path)
    store = project_legacy(ROOT, evidence)
    language = yaml.safe_load((ROOT / "domain/query_language_v2.yaml").read_text())
    call_cache = {}
    if CALLS.exists():
        for event in load_jsonl(CALLS):
            if event.get("benchmark_digest") == gold_digest and event.get("cache_key"):
                call_cache[event["cache_key"]] = event
    provider = NvidiaStructuredClient(
        settings.nvidia_api_key, settings.nvidia_base_url, settings.nvidia_phase3_model
    )

    def persist_call(event):
        event["benchmark_digest"] = gold_digest
        event["run_profile"] = profile
        with CALLS.open("a") as stream:
            stream.write(json.dumps(event, ensure_ascii=False) + "\n")
            stream.flush()

    reasoner = NemotronControlledReasoner(
        provider.client,
        settings.nvidia_phase3_model,
        store.registry,
        language,
        event_sink=persist_call,
        cache=call_cache,
    )

    jev_settings = JevSettings()
    jev_metadata = {"configured_alias": jev_settings.model, "status": "NOT_REQUESTED"}
    jev_cache = {}
    jev_advisor = None
    if jev_enabled:
        try:
            listed = list_models(jev_settings)
            ids = [
                str(item.get("id"))
                for item in listed.get("data", listed.get("models", []))
                if isinstance(item, dict) and item.get("id")
            ]
            jev_metadata.update({"available_model_ids": ids, "status": "DISCOVERED"})
            if JEV_CALLS.exists():
                for event in load_jsonl(JEV_CALLS):
                    if event.get("benchmark_digest") == gold_digest:
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
                response = classify_epistemic(
                    {
                        "passage": candidate.get("text", "")[:1800],
                        "source": candidate.get("source_metadata"),
                    },
                    jev_settings,
                )
                label, confidence = decision_value(response, "epistemic_type")
                event = {
                    "benchmark_digest": gold_digest,
                    "input_digest": input_digest,
                    "evidence_id": candidate["evidence_id"],
                    "configured_model_alias": jev_settings.model,
                    "response_model": response.get("model"),
                    "proposal": {"label": label, "confidence": confidence},
                    "raw_response": response,
                }
                with JEV_CALLS.open("a") as stream:
                    stream.write(json.dumps(event, ensure_ascii=False) + "\n")
                    stream.flush()
                jev_cache[input_digest] = event
                return event["proposal"]

        except Exception as exc:  # noqa: BLE001 - Jev is advisory and cannot block core ablation
            jev_metadata.update({"status": "API_UNAVAILABLE", "error_type": type(exc).__name__})
            jev_advisor = None

    flags = ControlledReasoningFlags(
        query_expansion=True,
        contextual_reranking=True,
        jev_advisory_triage=bool(jev_advisor),
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
            reasoner,
            flags,
            jev_advisor=jev_advisor,
            per_query_limit=20,
        )
        row = _serialize_case(case, result, gold_digest, profile)
        with CASES.open("a") as stream:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
            stream.flush()
        completed[case["case_id"]] = row
        print(json.dumps({"completed": case["case_id"], "n": len(completed)}), flush=True)

    summary = summarize(gold, list(completed.values()), gold_digest, profile)
    summary["jev"] = jev_metadata
    SUMMARY.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    return summary


def summarize(gold: dict, rows: list[dict], gold_digest: str, profile: str) -> dict:
    by_id = {r["case_id"]: r for r in rows}
    metrics = {}
    for config in "ABCD":
        positive = [
            c for c in gold["cases"] if c["scoreable_identity_case"] and c["case_id"] in by_id
        ]
        metrics[config] = {}
        for k in (1, 3, 5, 10):
            found = 0
            for c in positive:
                ids = set(c["required_evidence_ids"])
                ranked = by_id[c["case_id"]]["configurations"][config]["candidate_ids"][:k]
                found += bool(ids & set(ranked))
            metrics[config][f"expected_identity_recall@{k}"] = {
                "numerator": int(found),
                "denominator": len(positive),
                "estimate": found / len(positive) if positive else None,
                "status": "EXPOSED_OBJECTIVE_REGRESSION_NOT_COMPLETE_RELEVANCE_GOLD",
            }
        metrics[config]["mean_candidate_count"] = {
            "n": len(rows),
            "mean": sum(
                len(by_id[r["case_id"]]["configurations"][config]["candidate_ids"]) for r in rows
            )
            / len(rows)
            if rows
            else 0,
        }
    direct_false = sum(
        bool(r["native_direct_ids"])
        for r in rows
        if next(c for c in gold["cases"] if c["case_id"] == r["case_id"])["expected_no_direct"]
    )
    review = [r for r in rows if r["gold_status"] == "REVIEW_REQUIRED"]
    latency = [
        r["latency_ms"].get("native_total")
        for r in rows
        if r["latency_ms"].get("native_total") is not None
    ]
    return {
        "version": "phase3c-controlled-e2e-ablation-summary-v1",
        "status": "EXPOSED_REGRESSION; REVIEW_REQUIRED_CASES_NOT_SCORED_FOR_RELEVANCE",
        "gold_digest": gold_digest,
        "run_profile": profile,
        "N": len(rows),
        "objective_identity_cases": sum(c["scoreable_identity_case"] for c in gold["cases"]),
        "review_required_cases": len(review),
        "objective_no_direct_cases": sum(c["expected_no_direct"] for c in gold["cases"]),
        "configurations": metrics,
        "false_direct_on_objective_no_direct": {
            "numerator": int(direct_false),
            "denominator": sum(c["expected_no_direct"] for c in gold["cases"]),
            "estimate": direct_false / max(1, sum(c["expected_no_direct"] for c in gold["cases"])),
        },
        "unscored_review_case_ids": [c["case_id"] for c in gold["cases"] if c["review_required"]],
        "precision_and_relevance": "NOT SCOREABLE: no complete independent evidence-relevance labels; human review fields remain blank in the review packet.",
        "native_retrieval_latency_ms": {
            "n": len(latency),
            "median": median(latency) if latency else None,
            "max": max(latency) if latency else None,
        },
        "jev_role": "Rhetorical advisory only; no filtering or canonical evidence promotion.",
    }


def make_review_packet() -> dict:
    gold = json.loads(GOLD.read_text())
    rows = [r for r in load_jsonl(CASES) if r.get("benchmark_digest") == digest(gold)]
    by_id = {r["case_id"]: r for r in rows}
    evidence = EvidenceRegistry(Settings().registry_path)
    include_ids = {c["case_id"] for c in gold["cases"] if c["review_required"]} | {
        "qi03",
        "qi11",
        "qi12",
    }
    packet_cases = []
    for case in gold["cases"]:
        if case["case_id"] not in include_ids or case["case_id"] not in by_id:
            continue
        row = by_id[case["case_id"]]
        candidate_ids = list(
            dict.fromkeys(
                eid for config in "ABCD" for eid in row["configurations"][config]["candidate_ids"]
            )
        )
        by_judgment = {
            j["evidence_id"]: j
            for j in row["configurations"]["C"].get("reranking", {}).get("judgments", [])
        }
        candidates = []
        for eid in candidate_ids:
            passage = evidence.resolve(eid)
            if not passage:
                continue
            candidates.append(
                {
                    "evidence_id": eid,
                    "text": passage["text"],
                    "source": evidence.source_metadata(eid),
                    "page": passage.get("page"),
                    "section": passage.get("section"),
                    "retrieved_by": [
                        config
                        for config in "ABCD"
                        if eid in row["configurations"][config]["candidate_ids"]
                    ],
                    "nemotron_proposal": by_judgment.get(eid),
                    "jev_proposal": next(
                        (
                            j["proposal"]
                            for j in row["configurations"]["D"].get("jev", {}).get("judgments", [])
                            if j["evidence_id"] == eid
                        ),
                        None,
                    ),
                    "deterministic_validation": {
                        "native_direct_entity_ids": row["native_direct_ids"],
                        "native_related_entity_ids": row["native_related_ids"],
                        "native_bundle_passage": eid in row["configurations"]["A"]["candidate_ids"],
                        "controlled_status": "CONTEXTUAL_CANDIDATE_ONLY"
                        if eid in row["configurations"]["C"]["contextual_candidate_ids"]
                        else "BASELINE_BUNDLE_PASSAGE",
                    },
                    "candidate_relevance_details": {
                        "why_retrieved": row["configurations"]["C"].get("search_traces"),
                        "constraint_support_proposal": by_judgment.get(eid, {}).get(
                            "constraint_assessments", []
                        ),
                        "known_differences_or_unknowns": [
                            x
                            for x in by_judgment.get(eid, {}).get("constraint_assessments", [])
                            if x.get("status") in {"DIFFERS", "UNKNOWN"}
                        ],
                        "native_eligibility": "SEE_NATIVE_BUNDLE_PASSAGE_FLAG; contextual candidates are never canonical evidence",
                    },
                    "reviewer_label": None,
                    "reviewer_authority_assessment": None,
                    "reviewer_scope_note": None,
                    "reviewer_id": None,
                }
            )
        packet_cases.append(
            {
                "case_id": case["case_id"],
                "query": case["query"],
                "requested_information": case["expected_intent"]["requested_information"],
                "canonical_constraints": {
                    "entities": case["expected_intent"]["entity_constraints"],
                    "properties": case["expected_intent"]["property_constraints"],
                    "comparison": case["expected_intent"]["comparison"],
                    "sources": case["expected_intent"]["source_constraints"],
                },
                "historical_gold_status": case["relevance_status"],
                "objective_expected_evidence_ids": case["required_evidence_ids"],
                "A_B_C_D_candidate_ids": {
                    key: row["configurations"][key]["candidate_ids"] for key in "ABCD"
                },
                "candidates": candidates,
                "reviewer_assessment": {
                    "relevance": None,
                    "source_authority": None,
                    "no_answer_appropriateness": None,
                    "notes": None,
                },
            }
        )
    packet = {
        "version": "phase3c-controlled-scientific-relevance-review-v1",
        "human_review_performed": False,
        "gold_digest": digest(gold),
        "result_digest": digest(CASES),
        "cases": packet_cases,
    }
    REVIEW.write_text(json.dumps(packet, indent=2, ensure_ascii=False) + "\n")
    return packet


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=(
            "freeze-gold",
            "benchmark-live",
            "rerank-second-pass",
            "rerank-third-pass",
            "rerank-fourth-pass",
            "review-packet",
        ),
    )
    args = parser.parse_args()
    if args.command == "freeze-gold":
        output = freeze_gold()
    elif args.command == "review-packet":
        output = make_review_packet()
    elif args.command in {"rerank-second-pass", "rerank-third-pass", "rerank-fourth-pass"}:
        output = run_rerank_second_pass()
    else:
        output = run_live()
    print(json.dumps({k: v for k, v in output.items() if k != "cases"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
