"""Bounded, resumable corrective API evaluation with separate immutable receipts."""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import httpx
import yaml
from openai import OpenAI, OpenAIError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from benchmark_jev import binary_metrics, rule_label
from phase3c_live import summarize

from nasa_fire_ai.evaluation.phase3c import append_result, digest, freeze_json, latency, proportion
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.semantic import project_legacy
from nasa_fire_ai.llm.jev import JevSettings, list_models, triage_claim
from nasa_fire_ai.models import ConversationContext
from nasa_fire_ai.query.native_interpreter import (
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    MinimalInterpretationV2,
    resolve_minimal,
)

MODEL = "nvidia/nemotron-3.5-lightning-30b-a3b"


def check_freeze():
    path = ROOT / "artifacts/phase3c_final_repair_native_freeze_v4.json"
    if not path.exists():
        path = ROOT / "artifacts/phase3c_final_repair_native_freeze_v3.json"
    if not path.exists():
        path = ROOT / "artifacts/phase3c_final_repair_native_freeze_v2.json"
    if not path.exists():
        path = ROOT / "artifacts/phase3c_final_repair_native_freeze_v1.json"
    if not path.exists():
        path = ROOT / "artifacts/phase3c_corrective_native_freeze_v6.json"
    if not path.exists():
        path = ROOT / "artifacts/phase3c_corrective_native_freeze_v5.json"
    if not path.exists():
        path = ROOT / "artifacts/phase3c_corrective_native_freeze_v4.json"
    if not path.exists():
        path = ROOT / "artifacts/phase3c_corrective_native_freeze_v3.json"
    if not path.exists():
        path = ROOT / "artifacts/phase3c_corrective_native_freeze_v2.json"
    if not path.exists():
        path = ROOT / "artifacts/phase3c_corrective_native_freeze_v1.json"
    frozen = json.loads(path.read_text())
    for name, expected in frozen["digests"].items():
        if digest(ROOT / name) != expected:
            raise RuntimeError(
                f"Corrective architecture changed: {name}; freeze a separate repair pass"
            )


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def interpret(limit=None, replay=False):
    check_freeze()
    gold = []
    for name in ("phase3c_queryintent_v2_gold_v1.json", "phase3c_compositional_gold_v1.json"):
        path = ROOT / "evals" / name
        gold.extend(
            [
                {**c, "gold_digest": digest(path)}
                for c in json.loads(path.read_text())["cases"]
                if c["supported"]
            ]
        )
    output = (
        ROOT / f"artifacts/phase3c_corrective_interpreter_{'replay' if replay else 'live'}_v1.jsonl"
    )
    prior = {r["case_id"]: r for r in rows(output)}
    old = {
        r["case_id"]: r for r in rows(ROOT / "artifacts/phase3c_queryinterpreter_second_pass.jsonl")
    }
    store = project_legacy(ROOT, EvidenceRegistry(ROOT / "data/index/evidence.sqlite"))
    language = yaml.safe_load((ROOT / "domain/query_language_v2.yaml").read_text())
    client = (
        None
        if replay
        else OpenAI(
            api_key=os.environ["NVIDIA_API_KEY"],
            base_url=os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"),
            timeout=40,
            max_retries=0,
        )
    )
    calls = 0
    attempt_counts = {cid: sum(r["case_id"] == cid for r in rows(output)) for cid in prior}
    for case in gold:
        if case["id"] in prior and not prior[case["id"]].get("service_failure"):
            continue
        if limit is not None and calls >= limit:
            break
        if attempt_counts.get(case["id"], 0) >= 2:
            continue
        calls += 1
        row = {
            "case_id": case["id"],
            "query": case["query"],
            "gold_digest": case["gold_digest"],
            "model": MODEL,
            "prompt_version": PROMPT_VERSION,
            "schema_valid": False,
            "semantic_valid": False,
            "fallback": False,
            "service_failure": False,
        }
        started = time.perf_counter()
        try:
            if replay:
                row["minimal_raw_output"] = old.get(case["id"], {}).get("minimal_raw_output")
            else:
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
                row["latency_ms"] = (time.perf_counter() - started) * 1000
                append_result(
                    ROOT / "artifacts/phase3c_corrective_interpreter_receipts_v1.jsonl", row
                )
            proposal = MinimalInterpretationV2.model_validate_json(row["minimal_raw_output"])
            row["schema_valid"] = True
            context = (
                ConversationContext.model_validate(case["context"]) if case.get("context") else None
            )
            intent = resolve_minimal(
                proposal, store.registry, language, context, query=case["query"]
            )
            store.registry.validate_intent(intent)
            row["semantic_valid"] = True
            row["resolved_intent"] = intent.model_dump(mode="json")
        except (OpenAIError, ValueError, TypeError, LookupError) as error:
            row["error"] = {
                "type": type(error).__name__,
                "status": getattr(error, "status_code", None),
            }
            row["fallback"] = True
            row["service_failure"] = type(error).__name__ in {
                "APIConnectionError",
                "APITimeoutError",
                "APIStatusError",
                "InternalServerError",
                "RateLimitError",
            }
        row.setdefault("latency_ms", (time.perf_counter() - started) * 1000)
        append_result(output, row)
        print(
            json.dumps(
                {
                    "case": case["id"],
                    "valid": row["semantic_valid"],
                    "service_failure": row["service_failure"],
                }
            ),
            flush=True,
        )
    latest = rows(output)
    summary = {
        "version": "POST_CORRECTION-v1",
        "live": not replay,
        "reviewed": summarize(
            [c for c in gold if c["id"].startswith("qi") and not c.get("context")], latest
        ),
        "conversational": summarize([c for c in gold if c.get("context")], latest),
        "compositional": summarize([c for c in gold if c["id"].startswith("comp")], latest),
    }
    # Progress summary is deliberately replaceable; call receipts are append-only.
    output.with_suffix(".summary.json").write_text(json.dumps(summary, indent=2) + "\n")


def jev(limit=None):
    check_freeze()
    settings = JevSettings(api_key=os.environ["TYPESAFE_API_KEY"])
    discovery_path = ROOT / "artifacts/phase3c_corrective_jev_models_v1.json"
    if not discovery_path.exists():
        try:
            response = list_models(settings)
            freeze_json(discovery_path, {"models": response, "requested_model": settings.model})
        except (httpx.HTTPError, ValueError, LookupError) as error:
            append_result(
                ROOT / "artifacts/phase3c_corrective_jev_service_errors_v1.jsonl",
                {
                    "stage": "model_discovery",
                    "type": type(error).__name__,
                    "status": getattr(getattr(error, "response", None), "status_code", None),
                },
            )
            print("Jev discovery failed; sanitized error persisted")
            return
    discovery = json.loads(discovery_path.read_text())
    if settings.model not in {m["name"] for m in discovery["models"]["models"]}:
        raise RuntimeError("Configured Jev model not account-visible")
    gold_path = ROOT / "evals/phase1_5_epistemic_gold.json"
    gold = json.loads(gold_path.read_text())["cases"]
    freeze_json(
        ROOT / "evals/phase3c_corrective_jev_gold_v1.json",
        {
            "source_digest": digest(gold_path),
            "cases": gold,
            "policy": "Existing reviewed labels; N=30, positives=9. No new human review claimed.",
        },
    )
    path = ROOT / "artifacts/phase3c_corrective_jev_results_v1.jsonl"
    existing = {r["case_id"]: r for r in rows(path)}
    calls = 0
    attempt_counts = {cid: sum(r["case_id"] == cid for r in rows(path)) for cid in existing}
    for case in gold:
        if case["gold_case_id"] in existing and existing[case["gold_case_id"]].get("response"):
            continue
        if limit is not None and calls >= limit:
            break
        if attempt_counts.get(case["gold_case_id"], 0) >= 2:
            continue
        calls += 1
        started = time.perf_counter()
        row = {
            "case_id": case["gold_case_id"],
            "model": settings.model,
            "gold_digest": digest(gold_path),
        }
        try:
            row["response"] = triage_claim(
                {
                    k: case[k]
                    for k in ("document_id", "page", "section", "local_heading", "passage")
                },
                settings,
            )
            row["score"] = row["response"]["answers"]["contains_candidate_claim"]["noul"]
        except (httpx.HTTPError, ValueError, TypeError, LookupError) as error:
            row["error"] = {
                "type": type(error).__name__,
                "status": getattr(getattr(error, "response", None), "status_code", None),
            }
        row["latency_ms"] = (time.perf_counter() - started) * 1000
        append_result(path, row)
        print(json.dumps({"case": row["case_id"], "success": "score" in row}), flush=True)
    latest = {r["case_id"]: r for r in rows(path)}
    cases = [c for c in gold if latest.get(c["gold_case_id"], {}).get("score") is not None]
    truth = [c["gold_label"] != "NONE" for c in cases]
    rule = [rule_label(c) != "NONE" for c in cases]
    scores = [latest[c["gold_case_id"]]["score"] for c in cases]
    configs = {
        "A_rules": [float(x) for x in rule],
        "B_jev": scores,
        "C_rules_plus_advisory": [int(r) + s for r, s in zip(rule, scores)],
    }
    budgets = {
        name: {
            str(k): proportion(
                sum(
                    truth[i]
                    for i in sorted(
                        range(len(cases)), key=lambda i: (-score[i], cases[i]["gold_case_id"])
                    )[:k]
                ),
                min(k, len(cases)),
            )
            for k in (5, 10, 20)
        }
        for name, score in configs.items()
    }
    result = {
        "version": "POST_CORRECTION-v1",
        "model": settings.model,
        "completed": len(cases),
        "planned": len(gold),
        "A": binary_metrics(truth, rule) if cases else None,
        "B": binary_metrics(truth, [s >= 0.5 for s in scores]) if cases else None,
        "review_budget_positive_yield": budgets,
        "latency": latency([latest[c["gold_case_id"]]["latency_ms"] for c in cases]),
        "support": {
            label: sum(c["gold_label"] == label for c in cases)
            for label in sorted({c["gold_label"] for c in cases})
        },
        "D_nemotron": "NOT_EVALUATED: no equivalent independently reviewed candidate-extraction outputs",
        "relevant_evidence_omitted": 0,
        "hard_filter": False,
        "cost": "NOT_AVAILABLE",
        "decision": "INCONCLUSIVE",
        "limitation": "Small imbalanced reviewed set. Review priority is simulated, not a human workload study.",
    }
    (ROOT / "artifacts/phase3c_corrective_jev_summary_v1.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["interpreter", "replay", "jev"])
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    if args.stage == "jev":
        jev(args.limit)
    else:
        interpret(args.limit, replay=args.stage == "replay")
