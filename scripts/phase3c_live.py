"""Resumable bounded live V2 interpretation. Every API receipt is persisted immediately."""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import yaml
from openai import OpenAI, OpenAIError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from phase3c_native_benchmarks import check_freeze

from nasa_fire_ai.evaluation.phase3c import (
    append_result,
    digest,
    field_score,
    freeze_json,
    latency,
    proportion,
)
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.semantic import project_legacy
from nasa_fire_ai.models import ConversationContext
from nasa_fire_ai.query.native_interpreter import (
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    MinimalInterpretationV2,
    resolve_minimal,
)
from nasa_fire_ai.query.offline_parser import parse_query
from nasa_fire_ai.query.v2 import v1_to_v2

MODEL = "nvidia/nemotron-3.5-lightning-30b-a3b"
OUT = ROOT / "artifacts/phase3c_queryinterpreter_results.jsonl"


def semantic_signature(value):
    """Compare scientific semantics; raw source-language expressions remain in receipts."""
    value = json.loads(json.dumps(value))
    for c in value.get("property_constraints", []):
        c["value"].pop("raw_expression", None)
        if not c.get("qualifiers"):
            c.pop("qualifiers", None)
    for key in (
        "targets",
        "entity_constraints",
        "property_constraints",
        "requested_information",
        "source_constraints",
        "unresolved_mentions",
        "ambiguities",
    ):
        value[key] = sorted(value.get(key, []), key=lambda x: json.dumps(x, sort_keys=True))
    return value


def summarize(cases, receipts):
    expected = {c["id"]: c for c in cases}
    latest = {r["case_id"]: r for r in receipts}
    rows = [r for key, r in latest.items() if key in expected]
    fields = {
        k: {"tp": 0, "fp": 0, "fn": 0}
        for k in ("targets", "entity_constraints", "property_constraints", "requested_information")
    }
    exact = operation = 0
    details = []
    attribute_scores = {
        key: [0, 0]
        for key in (
            "comparison",
            "numeric_value",
            "operator",
            "unit",
            "range",
            "approximation_preservation",
            "ambiguity",
            "unknown",
            "clarification",
        )
    }
    over = under = 0
    for row in rows:
        gold = semantic_signature(expected[row["case_id"]]["expected"])
        actual = semantic_signature(row.get("resolved_intent") or {})
        row["exact_match"] = gold == actual
        exact += row["exact_match"]
        operation += gold.get("operation") == actual.get("operation")
        extras = missing = 0
        for field, counts in fields.items():
            result = field_score(gold.get(field, []), actual.get(field, []))
            for key in result:
                counts[key] += result[key]
            extras += result["fp"]
            missing += result["fn"]
        over += bool(extras)
        under += bool(missing)
        for label, key in (
            ("ambiguity", "ambiguities"),
            ("unknown", "unresolved_mentions"),
            ("clarification", "clarification_required"),
        ):
            attribute_scores[label][0] += gold.get(key) == actual.get(key)
            attribute_scores[label][1] += 1
        if gold.get("comparison") is not None:
            attribute_scores["comparison"][0] += gold.get("comparison") == actual.get("comparison")
            attribute_scores["comparison"][1] += 1
        ap = {c["property_id"]: c for c in actual.get("property_constraints", [])}
        for c in gold.get("property_constraints", []):
            a = ap.get(c["property_id"], {})
            for label, keys in (
                ("numeric_value", ["reported_value"]),
                ("unit", ["reported_unit"]),
                ("range", ["lower", "upper"]),
                ("approximation_preservation", ["approximate", "tolerance"]),
            ):
                if label == "range" and c["operator"] != "BETWEEN":
                    continue
                if label == "approximation_preservation" and c["operator"] != "APPROX":
                    continue
                attribute_scores[label][0] += all(
                    c["value"].get(key) == a.get("value", {}).get(key) for key in keys
                ) and bool(a)
                attribute_scores[label][1] += 1
            attribute_scores["operator"][0] += c["operator"] == a.get("operator")
            attribute_scores["operator"][1] += 1
        deterministic = semantic_signature(
            v1_to_v2(parse_query(expected[row["case_id"]]["query"])).model_dump(mode="json")
        )
        details.append(
            {
                "case_id": row["case_id"],
                "category": expected[row["case_id"]]["kind"],
                "nemotron_exact": row["exact_match"],
                "deterministic_exact": deterministic == gold,
                "comparison_scope": "Current V1 deterministic parser adapted as input; no native execution involved",
            }
        )
    for values in fields.values():
        tp, fp, fn = values["tp"], values["fp"], values["fn"]
        values.update(
            {
                "precision": proportion(tp, tp + fp),
                "recall": proportion(tp, tp + fn),
                "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None,
            }
        )
    return {
        "n": len(rows),
        "structured_valid": proportion(sum(r.get("schema_valid", False) for r in rows), len(rows)),
        "exact_match": proportion(exact, len(rows)),
        "operation": proportion(operation, len(rows)),
        "fields": fields,
        "attributes": {
            key: proportion(values[0], values[1]) for key, values in attribute_scores.items()
        },
        "overinterpretation": proportion(over, len(rows)),
        "underinterpretation": proportion(under, len(rows)),
        "deterministic_comparison": details,
        "fallback": proportion(sum(r.get("fallback", False) for r in rows), len(rows)),
        "latency": latency([r["latency_ms"] for r in rows]),
        "limitation": "Unsupported historical gap cases are not silently treated as reviewed field gold.",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int)
    parser.add_argument("--summarize", action="store_true")
    parser.add_argument("--second-pass", action="store_true")
    parser.add_argument("--retry-service-failures", action="store_true")
    args = parser.parse_args()
    global OUT
    if args.second_pass:
        OUT = ROOT / "artifacts/phase3c_queryinterpreter_second_pass.jsonl"
    check_freeze()
    gold_paths = [
        ROOT / "evals/phase3c_queryintent_v2_gold_v1.json",
        ROOT / "evals/phase3c_compositional_gold_v1.json",
    ]
    cases = []
    for path in gold_paths:
        cases.extend(
            [
                {**c, "gold_digest": digest(path)}
                for c in json.loads(path.read_text())["cases"]
                if c["supported"]
            ]
        )
    existing = [json.loads(line) for line in OUT.read_text().splitlines()] if OUT.exists() else []
    if args.summarize:
        freeze_json(
            ROOT
            / (
                "artifacts/phase3c_queryinterpreter_second_pass_summary.json"
                if args.second_pass
                else "artifacts/phase3c_queryinterpreter_summary.json"
            ),
            {
                "model": MODEL,
                "prompt_version": PROMPT_VERSION,
                "reviewed": summarize(
                    [c for c in cases if c["id"].startswith("qi") and not c.get("context")],
                    existing,
                ),
                "conversational": summarize([c for c in cases if c.get("context")], existing),
                "compositional": summarize(
                    [c for c in cases if c["id"].startswith("comp")], existing
                ),
            },
        )
        return
    if not os.environ.get("NVIDIA_API_KEY"):
        raise RuntimeError(
            "NVIDIA_API_KEY is required for live evaluation; no credentials are persisted"
        )
    client = OpenAI(
        api_key=os.environ["NVIDIA_API_KEY"],
        base_url=os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"),
        timeout=40,
        max_retries=0,
    )
    store = project_legacy(ROOT, EvidenceRegistry(ROOT / "data/index/evidence.sqlite"))
    language = yaml.safe_load((ROOT / "domain/query_language_v2.yaml").read_text())
    latest = {r["case_id"]: r for r in existing}
    completed = {
        key
        for key, r in latest.items()
        if not args.retry_service_failures or not r.get("service_failure")
    }
    pending = [c for c in cases if c["id"] not in completed]
    if args.limit:
        pending = pending[: args.limit]
    for case in pending:
        began = time.perf_counter()
        row = {
            "case_id": case["id"],
            "query": case["query"],
            "gold_digest": case["gold_digest"],
            "model": MODEL,
            "prompt_version": PROMPT_VERSION,
            "schema_valid": False,
            "semantic_valid": False,
            "fallback": False,
            "tokens": None,
            "errors": [],
        }
        try:
            response = client.chat.completions.create(
                model=MODEL,
                temperature=0,
                stream=False,
                max_tokens=1400,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": case["query"]},
                ],
                response_format={"type": "json_object"},
                extra_body={
                    "chat_template_kwargs": {"enable_thinking": False},
                    "reasoning_budget": 0,
                },
            )
            row["minimal_raw_output"] = response.choices[0].message.content
            row["tokens"] = response.usage.model_dump() if response.usage else None
            # Save the response before attempting resolution or model validation.
            append_result(ROOT / "artifacts/phase3c_queryinterpreter_receipts.jsonl", row)
            proposal = MinimalInterpretationV2.model_validate_json(row["minimal_raw_output"])
            row["schema_valid"] = True
            context = (
                ConversationContext.model_validate(case["context"]) if case.get("context") else None
            )
            resolved = resolve_minimal(proposal, store.registry, language, context)
            row["resolved_intent"] = resolved.model_dump(mode="json")
            store.registry.validate_intent(resolved)
            row["semantic_valid"] = True
        except (OpenAIError, ValueError, LookupError, IndexError, TypeError) as exc:
            # Do not serialize arbitrary provider errors: those can contain request credentials.
            row["errors"] = [
                {"type": type(exc).__name__, "status_code": getattr(exc, "status_code", None)}
            ]
            row["fallback"] = True
            row["service_failure"] = not isinstance(exc, (ValueError, LookupError))
        row["latency_ms"] = (time.perf_counter() - began) * 1000
        append_result(OUT, row)
        print(
            json.dumps(
                {
                    "case_id": row["case_id"],
                    "schema_valid": row["schema_valid"],
                    "errors": row["errors"],
                }
            ),
            flush=True,
        )
        if row.get("service_failure"):
            raise SystemExit(2)


if __name__ == "__main__":
    main()
