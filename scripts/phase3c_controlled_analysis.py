"""Produce reproducible A/B/C/D diagnostics and a blank human review packet."""

from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from phase3c_controlled_reasoning import digest, load_jsonl

from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry

GOLD = ROOT / "evals/phase3c_controlled_e2e_regression_gold_v1.json"
FIRST_PASS = ROOT / "artifacts/phase3c_controlled_e2e_ablation_cases_v1.jsonl"
LATEST_PASS = ROOT / "artifacts/phase3c_controlled_e2e_ablation_cases_v4.jsonl"
API_FIRST = ROOT / "artifacts/phase3c_controlled_e2e_api_calls_v1.jsonl"
API_LATEST = ROOT / "artifacts/phase3c_controlled_e2e_api_calls_v4.jsonl"
JEV_CALLS = ROOT / "artifacts/phase3c_controlled_e2e_jev_calls_v1.jsonl"
ANALYSIS_OUT = ROOT / "artifacts/phase3c_controlled_ablation_analysis_v1.json"
REVIEW_OUT = ROOT / "artifacts/phase3c_controlled_scientific_relevance_review_packet_v2.json"
DIAGNOSTICS_OUT = ROOT / "artifacts/phase3c_controlled_case_diagnostics_v1.json"
PROVENANCE_OUT = ROOT / "artifacts/phase3c_controlled_provenance_audit_v1.json"


def p95(values: list[float]) -> float | None:
    if not values:
        return None
    values = sorted(values)
    return values[max(0, math.ceil(0.95 * len(values)) - 1)]


def wilson(successes: int, total: int, z: float = 1.96) -> dict | None:
    if not total:
        return None
    rate = successes / total
    denom = 1 + z * z / total
    center = (rate + z * z / (2 * total)) / denom
    margin = z * math.sqrt(rate * (1 - rate) / total + z * z / (4 * total * total)) / denom
    return {"lower": max(0.0, center - margin), "upper": min(1.0, center + margin)}


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def evidence_metadata(registry: EvidenceRegistry, evidence_id: str) -> dict:
    passage = registry.resolve(evidence_id)
    if not passage:
        return {"evidence_id": evidence_id, "registry_resolved": False}
    source = registry.source_metadata(evidence_id) or {}
    return {
        "evidence_id": evidence_id,
        "registry_resolved": True,
        "source_id": source.get("source_id"),
        "nasa_id": source.get("nasa_id"),
        "source_type": source.get("source_type"),
        "title": source.get("title"),
        "official_url": source.get("url"),
        "page_as_stored": passage.get("page"),
        "page_semantics": "registry integer; physical PDF page not verified by this benchmark",
        "section_as_stored": passage.get("section"),
        "passage_text": passage.get("text"),
        "start_offset": passage.get("start_offset"),
        "end_offset": passage.get("end_offset"),
        "raw_file": passage.get("raw_file"),
        "checksum": passage.get("checksum"),
    }


def verify_local_pdf_location(passage: dict, source: dict) -> dict:
    raw_file = passage.get("raw_file")
    candidates = [Path(raw_file)] if raw_file else []
    nasa_id = source.get("nasa_id")
    if nasa_id:
        candidates.append(ROOT / "data/raw" / f"ntrs-{nasa_id}.pdf")
    path = next((p for p in candidates if p.is_file() and p.suffix.lower() == ".pdf"), None)
    if path is None:
        return {"verified": False, "reason": "no local source PDF with an auditable page map"}
    try:
        import fitz

        document = fitz.open(path)
        excerpt = re.sub(r"[^a-z0-9]+", " ", passage.get("text", "").lower()).strip()
        excerpt = " ".join(excerpt.split())
        if len(excerpt) < 45:
            return {"verified": False, "reason": "passage excerpt too short for page matching"}
        for index, page in enumerate(document, 1):
            page_text = re.sub(r"[^a-z0-9]+", " ", page.get_text().lower()).strip()
            page_text = " ".join(page_text.split())
            if excerpt in page_text:
                return {
                    "verified": True,
                    "physical_pdf_page": index,
                    "pdf_path": str(path.relative_to(ROOT)),
                    "method": "normalized exact excerpt match",
                }
        return {
            "verified": False,
            "pdf_path": str(path.relative_to(ROOT)),
            "reason": "passage excerpt not found contiguously on one physical PDF page",
        }
    except Exception as exc:  # noqa: BLE001 - audit is non-authoritative if parser fails
        return {"verified": False, "reason": type(exc).__name__}


def main() -> None:
    gold = json.loads(GOLD.read_text())
    first = {
        x["case_id"]: x for x in load_jsonl(FIRST_PASS) if x.get("benchmark_digest") == digest(gold)
    }
    latest = {
        x["case_id"]: x
        for x in load_jsonl(LATEST_PASS)
        if x.get("benchmark_digest") == digest(gold)
    }
    if set(first) != set(latest) or set(first) != {x["case_id"] for x in gold["cases"]}:
        raise RuntimeError("A/B/C/D artifacts do not have complete, aligned case coverage")

    registry = EvidenceRegistry(Settings().registry_path)
    expected = {x["case_id"]: x for x in gold["cases"]}
    case_metrics = []
    configs: dict[str, dict[str, list[str]]] = {
        name: {} for name in ("A", "A_budget_matched", "B", "C", "D")
    }
    for case_id, original in first.items():
        updated = latest[case_id]
        configs["A"][case_id] = original["configurations"]["A"]["candidate_ids"]
        base = list(configs["A"][case_id])
        traces = original["configurations"]["B"].get("search_traces") or []
        lexical = traces[0].get("hits", []) if traces else []
        configs["A_budget_matched"][case_id] = dedupe(base + lexical)
        configs["B"][case_id] = original["configurations"]["B"]["candidate_ids"]
        configs["C"][case_id] = updated["configurations"]["C"]["candidate_ids"]
        configs["D"][case_id] = updated["configurations"]["D"]["candidate_ids"]
        gold_case = expected[case_id]
        required = set(gold_case["required_evidence_ids"])
        hit_ranks = {}
        for name in configs:
            hit_ranks[name] = next(
                (i + 1 for i, eid in enumerate(configs[name][case_id]) if eid in required), None
            )
        case_metrics.append(
            {
                "case_id": case_id,
                "review_status": gold_case["relevance_status"],
                "required_evidence_ids": sorted(required),
                "rank_of_first_expected_id": hit_ranks,
                "candidate_counts": {name: len(configs[name][case_id]) for name in configs},
                "new_expansion_candidates_beyond_budget_matched_lexical": len(
                    set(configs["B"][case_id]) - set(configs["A_budget_matched"][case_id])
                ),
                "direct_ids_identical_across_modes": len(
                    {
                        tuple(original["native_direct_ids"]),
                        tuple(updated["native_direct_ids"]),
                    }
                )
                == 1,
                "related_ids_identical_across_modes": len(
                    {
                        tuple(original["native_related_ids"]),
                        tuple(updated["native_related_ids"]),
                    }
                )
                == 1,
            }
        )

    scoreable = [x for x in gold["cases"] if x["scoreable_identity_case"]]
    metrics = {}
    for name, per_case in configs.items():
        hits = {}
        reciprocal_rank = 0.0
        for k in (1, 3, 5, 10):
            found = 0
            for case in scoreable:
                rank = next(
                    (
                        i + 1
                        for i, eid in enumerate(per_case[case["case_id"]][:k])
                        if eid in set(case["required_evidence_ids"])
                    ),
                    None,
                )
                found += rank is not None
                if k == 10 and rank:
                    reciprocal_rank += 1 / rank
            hits[f"identity_recall@{k}"] = {
                "numerator": int(found),
                "denominator": len(scoreable),
                "estimate": found / len(scoreable) if scoreable else None,
                "wilson_95": wilson(int(found), len(scoreable)),
                "sample_size_warning": "SMALL_N" if len(scoreable) < 10 else None,
                "status": "EXPOSED_OBJECTIVE_IDENTITY_REGRESSION; not relevance precision",
            }
        metrics[name] = {
            **hits,
            "identity_MRR_at_10": {
                "numerator_equivalent": reciprocal_rank,
                "denominator": len(scoreable),
                "estimate": reciprocal_rank / len(scoreable) if scoreable else None,
            },
            "mean_candidate_count": sum(len(per_case[c["case_id"]]) for c in gold["cases"])
            / len(gold["cases"]),
        }

    expansions = [first[cid]["configurations"]["B"].get("expansion") or {} for cid in first]
    accepted = [x for result in expansions for x in result.get("accepted", [])]
    rejected = [x for result in expansions for x in result.get("rejected", [])]
    rejection_reasons = Counter(x["reason"].split(":", 1)[0] for x in rejected)
    api_by_pass = {
        "initial_e2e_ablation": load_jsonl(API_FIRST),
        "compact_span_rerank_pass": load_jsonl(API_LATEST),
    }
    usage_by_pass = {}
    for pass_name, api_events in api_by_pass.items():
        latency_by_type: dict[str, list[float]] = {}
        error_counts = Counter()
        token_counts = Counter()
        for event in api_events:
            event_type = event.get("event_type", "unknown")
            usage = event.get("usage") or {}
            if isinstance(usage.get("latency_ms"), (int, float)):
                latency_by_type.setdefault(event_type, []).append(usage["latency_ms"])
                token_counts[event_type + "_input"] += usage.get("input_tokens") or 0
                token_counts[event_type + "_output"] += usage.get("output_tokens") or 0
            if event.get("error"):
                error_counts[f"{event_type}:{event['error']}"] += 1
        usage_by_pass[pass_name] = {
            "api_requests": len(api_events),
            "latency_ms": {
                kind: {
                    "n": len(values),
                    "median": median(values) if values else None,
                    "p95": p95(values),
                    "max": max(values) if values else None,
                }
                for kind, values in latency_by_type.items()
            },
            "tokens_when_returned": dict(token_counts),
            "error_counts": dict(error_counts),
        }
    latest_rows = list(latest.values())
    rerank_errors = Counter(
        str(x["configurations"]["C"].get("reranking", {}).get("error")) for x in latest_rows
    )
    rerank_invalid = Counter(
        invalid["reason"]
        for row in latest_rows
        for invalid in row["configurations"]["C"].get("reranking", {}).get("invalid", [])
    )
    rerank_judgments = [
        judgment
        for row in latest_rows
        for judgment in row["configurations"]["C"].get("reranking", {}).get("judgments", [])
    ]
    jev = load_jsonl(JEV_CALLS)
    jev_labels = Counter(x.get("proposal", {}).get("label") for x in jev)

    analysis = {
        "version": "phase3c-controlled-ablation-analysis-v1",
        "status": "EXPOSED_REGRESSION_ONLY; HUMAN_RELEVANCE_REVIEW_PENDING",
        "gold_digest": digest(gold),
        "first_pass_digest": digest(FIRST_PASS),
        "compact_rerank_pass_digest": digest(LATEST_PASS),
        "model": "nvidia/nemotron-3.5-lightning-30b-a3b",
        "code_digests": {
            str(path.relative_to(ROOT)): file_digest(path)
            for path in (
                ROOT / "src/nasa_fire_ai/query/controlled_reasoning.py",
                ROOT / "src/nasa_fire_ai/query/native_interpreter.py",
                ROOT / "src/nasa_fire_ai/services/native.py",
                ROOT / "scripts/phase3c_controlled_e2e.py",
            )
        },
        "prompt_versions": {
            "expansion": "phase3c-controlled-discovery-v1",
            "first_rerank": "phase3c-contextual-rerank-v1",
            "compact_rerank": "phase3c-contextual-rerank-v4",
        },
        "N": len(gold["cases"]),
        "human_reviewed_cases": 0,
        "review_required_cases": [c["case_id"] for c in gold["cases"] if c["review_required"]],
        "objective_identity_cases": len(scoreable),
        "configurations": metrics,
        "expansion": {
            "proposals_accepted": len(accepted),
            "proposals_rejected": len(rejected),
            "accepted_per_query_count": sum(bool(x.get("accepted")) for x in expansions),
            "rejection_reason_prefix_counts": dict(rejection_reasons),
            "unique_new_candidates_beyond_budget_matched_lexical": sum(
                x["new_expansion_candidates_beyond_budget_matched_lexical"] for x in case_metrics
            ),
            "decision": "No identity-recall improvement over budget-matched original-query FTS on exposed gold; candidate-pool expansion alone is not a relevance gain.",
        },
        "reranking": {
            "successful_api_calls_with_usage": sum(
                isinstance(
                    r["configurations"]["C"]
                    .get("reranking", {})
                    .get("usage", {})
                    .get("latency_ms"),
                    (int, float),
                )
                for r in latest_rows
            ),
            "case_error_counts": dict(rerank_errors),
            "accepted_judgments": len(rerank_judgments),
            "accepted_relevance_labels": dict(
                Counter(x["candidate_relevance"] for x in rerank_judgments)
            ),
            "accepted_judgments_with_verified_verbatim_span": sum(
                bool(x.get("supporting_span")) for x in rerank_judgments
            ),
            "rejected_output_counts": dict(rerank_invalid),
            "direct_related_effect": "NONE; controlled proposals never enter native DIRECT/RELATED or evidence_passages.",
        },
        "jev": {
            "configured_alias": "jev-latest",
            "observed_response_models": sorted(
                {str(x.get("response_model")) for x in jev if x.get("response_model")}
            ),
            "calls": len(jev),
            "provisional_label_counts": dict(jev_labels),
            "independent_relevance_labels": 0,
            "D_incremental_value": "Not established; advisory proposals only; no scientific relevance gold.",
        },
        "api_usage_by_pass": usage_by_pass,
        "cost": "Provider cost not returned in responses; no monetary estimate is asserted.",
        "case_metrics": case_metrics,
        "api_error_counts": dict(error_counts),
    }
    ANALYSIS_OUT.write_text(json.dumps(analysis, indent=2, ensure_ascii=False) + "\n")

    include_ids = {c["case_id"] for c in gold["cases"] if c["review_required"]} | {
        "qi03",
        "qi11",
        "qi12",
    }
    packet_cases = []
    for case in gold["cases"]:
        if case["case_id"] not in include_ids:
            continue
        old, new = first[case["case_id"]], latest[case["case_id"]]
        candidate_ids = dedupe(
            [
                eid
                for config in "ABCD"
                for eid in (
                    old["configurations"][config]["candidate_ids"]
                    if config in {"A", "B"}
                    else new["configurations"][config]["candidate_ids"]
                )
            ]
        )
        c_judgments = {
            x["evidence_id"]: x
            for x in new["configurations"]["C"].get("reranking", {}).get("judgments", [])
        }
        d_jev = {
            x["evidence_id"]: x.get("proposal")
            for x in old["configurations"]["D"].get("jev", {}).get("judgments", [])
        }
        candidates = []
        for evidence_id in candidate_ids:
            metadata = evidence_metadata(registry, evidence_id)
            if not metadata.get("registry_resolved"):
                candidates.append(metadata)
                continue
            metadata.update(
                {
                    "retrieved_by": [
                        name
                        for name in "ABCD"
                        if evidence_id
                        in (
                            old["configurations"][name]["candidate_ids"]
                            if name in {"A", "B"}
                            else new["configurations"][name]["candidate_ids"]
                        )
                    ],
                    "nemotron_contextual_proposal": c_judgments.get(evidence_id),
                    "jev_rhetorical_proposal": d_jev.get(evidence_id),
                    "native_bundle_passage": evidence_id
                    in old["configurations"]["A"]["candidate_ids"],
                    "canonical_match_effect_of_model": "NONE",
                }
            )
            candidates.append(metadata)
        packet_cases.append(
            {
                "case_id": case["case_id"],
                "query": case["query"],
                "requested_information": case["expected_intent"].get("requested_information", []),
                "canonical_constraints": {
                    "targets": case["expected_intent"].get("targets", []),
                    "entities": case["expected_intent"].get("entity_constraints", []),
                    "properties": case["expected_intent"].get("property_constraints", []),
                    "comparison": case["expected_intent"].get("comparison"),
                    "sources": case["expected_intent"].get("source_constraints", []),
                },
                "review_status": case["relevance_status"],
                "frozen_expected_identity_ids": case["required_evidence_ids"],
                "native_direct_entity_ids": old["native_direct_ids"],
                "native_related_entity_ids": old["native_related_ids"],
                "rankings": {name: configs[name][case["case_id"]] for name in configs},
                "candidates": candidates,
                "reviewer_assessment": {
                    "relevance": None,
                    "direct_or_related": None,
                    "source_authority": None,
                    "topic_scope": None,
                    "no_answer_appropriateness": None,
                    "notes": None,
                    "reviewer_id": None,
                },
            }
        )
    review_packet = {
        "version": "phase3c-controlled-scientific-relevance-review-packet-v2",
        "human_review_performed": False,
        "gold_status": "BLANK_REVIEW_FIELDS; not model-derived relevance truth",
        "gold_digest": digest(gold),
        "A_B_C_D_results_digest": digest(LATEST_PASS),
        "included_case_ids": [x["case_id"] for x in packet_cases],
        "cases": packet_cases,
    }
    REVIEW_OUT.write_text(json.dumps(review_packet, indent=2, ensure_ascii=False) + "\n")

    selected_diagnostics = []
    interpreter = {
        x["case_id"]: x
        for x in load_jsonl(ROOT / "artifacts/phase3c_final_repair_interpreter_cases_v6.jsonl")
    }
    for case_id in ("qi24", "qi27", "comp01", "comp11", "qi12", "qi42", "qi18"):
        case = expected[case_id]
        old, new = first[case_id], latest[case_id]
        selected_diagnostics.append(
            {
                "case_id": case_id,
                "query": case["query"],
                "review_status": case["relevance_status"],
                "gold_expected_intent": case["expected_intent"],
                "frozen_expected_evidence_ids": case["required_evidence_ids"],
                "interpreter_receipt": {
                    "raw_minimal_extraction": interpreter.get(case_id, {}).get(
                        "raw_minimal_extraction"
                    ),
                    "resolved_intent": interpreter.get(case_id, {}).get("repaired_resolved_intent"),
                    "root_cause": interpreter.get(case_id, {}).get("root_cause"),
                },
                "top_evidence_by_configuration": {
                    name: [evidence_metadata(registry, eid) for eid in ids[:5]]
                    for name, ids in {
                        "A": old["configurations"]["A"]["candidate_ids"],
                        "B": old["configurations"]["B"]["candidate_ids"],
                        "C": new["configurations"]["C"]["candidate_ids"],
                        "D": new["configurations"]["D"]["candidate_ids"],
                    }.items()
                },
                "expansion": old["configurations"]["B"].get("expansion"),
                "reranker": new["configurations"]["C"].get("reranking"),
                "human_relevance_judgment": None,
            }
        )
    DIAGNOSTICS_OUT.write_text(
        json.dumps(
            {
                "version": "phase3c-controlled-case-diagnostics-v1",
                "human_relevance_review_performed": False,
                "cases": selected_diagnostics,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    )
    provenance_records = []
    for evidence_id in ("E-382165f1a4516fa8", "E-safety-saffire-suppression-open-question"):
        passage = registry.resolve(evidence_id)
        source = registry.source_metadata(evidence_id) or {}
        if passage:
            provenance_records.append(
                {
                    "evidence_id": evidence_id,
                    "source_id": source.get("source_id"),
                    "nasa_id": source.get("nasa_id"),
                    "title": source.get("title"),
                    "official_url": source.get("url"),
                    "page_as_stored": passage.get("page"),
                    "section_as_stored": passage.get("section"),
                    "physical_page_audit": verify_local_pdf_location(passage, source),
                    "citation_policy": "Do not relabel the stored page as a physical PDF page unless the audit verifies it.",
                }
            )
    PROVENANCE_OUT.write_text(
        json.dumps(
            {
                "version": "phase3c-controlled-provenance-audit-v1",
                "records": provenance_records,
                "interpretation": "Citation-location metadata is preserved; no page values were rewritten. Physical PDF pagination is reported only when a local official PDF passage match verifies it.",
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    )
    print(
        json.dumps(
            {
                "analysis": str(ANALYSIS_OUT.relative_to(ROOT)),
                "review_packet": str(REVIEW_OUT.relative_to(ROOT)),
                "diagnostics": str(DIAGNOSTICS_OUT.relative_to(ROOT)),
                "provenance_audit": str(PROVENANCE_OUT.relative_to(ROOT)),
                "objective_cases": len(scoreable),
                "review_required": sum(c["review_required"] for c in gold["cases"]),
                "human_review_performed": False,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
