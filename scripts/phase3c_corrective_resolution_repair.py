"""Re-resolve frozen live proposals after the logged contradictory-slot bug fix."""

import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from phase3c_corrective_live import check_freeze, rows
from phase3c_live import semantic_signature, summarize

from nasa_fire_ai.evaluation.phase3c import append_result, digest, freeze_json
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.semantic import project_legacy
from nasa_fire_ai.models import ConversationContext
from nasa_fire_ai.query.native_interpreter import MinimalInterpretationV2, resolve_minimal


def main():
    check_freeze()
    latest = {
        r["case_id"]: r
        for r in rows(ROOT / "artifacts/phase3c_corrective_interpreter_live_v1.jsonl")
    }
    cases = []
    for name in ("phase3c_queryintent_v2_gold_v1.json", "phase3c_compositional_gold_v1.json"):
        cases.extend(
            c for c in json.loads((ROOT / "evals" / name).read_text())["cases"] if c["supported"]
        )
    store = project_legacy(ROOT, EvidenceRegistry(ROOT / "data/index/evidence.sqlite"))
    language = yaml.safe_load((ROOT / "domain/query_language_v2.yaml").read_text())
    output = ROOT / "artifacts/phase3c_corrective_interpreter_resolution_repair_v1.jsonl"
    completed = {r["case_id"] for r in rows(output)}
    for c in cases:
        if c["id"] in completed:
            continue
        prior = latest[c["id"]]
        row = {
            **prior,
            "version": "POST_HOLDOUT_REPAIR-v1",
            "reused_live_prediction": True,
            "architecture_digest": digest(
                ROOT / "artifacts/phase3c_corrective_native_freeze_v4.json"
            ),
        }
        context = ConversationContext.model_validate(c["context"]) if c.get("context") else None
        try:
            proposal = MinimalInterpretationV2.model_validate_json(prior["minimal_raw_output"])
            intent = resolve_minimal(proposal, store.registry, language, context, query=c["query"])
            row["resolved_intent"] = intent.model_dump(mode="json")
            row["semantic_valid"] = True
        except (ValueError, LookupError, TypeError) as error:
            row["error"] = {"type": type(error).__name__}
            row["semantic_valid"] = False
        append_result(output, row)
    repaired = rows(output)
    results = {
        "live_calls": 0,
        "reused_compatible_live_predictions": len(repaired),
        "version": "POST_HOLDOUT_REPAIR-v1",
        "gold_unchanged": True,
        "reviewed": summarize(
            [c for c in cases if c["id"].startswith("qi") and not c.get("context")], repaired
        ),
        "conversational": summarize([c for c in cases if c.get("context")], repaired),
        "compositional": summarize([c for c in cases if c["id"].startswith("comp")], repaired),
    }
    freeze_json(
        ROOT / "artifacts/phase3c_corrective_interpreter_resolution_repair_summary_v1.json", results
    )
    actual = {r["case_id"]: r for r in repaired}
    errors = []
    for c in cases:
        old = semantic_signature(latest[c["id"]].get("resolved_intent") or {})
        new = semantic_signature(actual[c["id"]].get("resolved_intent") or {})
        expected = semantic_signature(c["expected"])
        fields = [
            "operation",
            "targets",
            "entity_constraints",
            "property_constraints",
            "requested_information",
            "comparison",
            "source_constraints",
            "unresolved_mentions",
            "ambiguities",
            "clarification_required",
            "conversation_reference",
        ]
        errors.append(
            {
                "case_id": c["id"],
                "query": c["query"],
                "pre_repair_wrong_fields": [k for k in fields if old.get(k) != expected.get(k)],
                "post_repair_wrong_fields": [k for k in fields if new.get(k) != expected.get(k)],
                "expected": expected,
                "actual": new,
                "review_status": "Existing reviewed/fixture semantics; no new scientist labels",
            }
        )
    freeze_json(
        ROOT / "artifacts/phase3c_corrective_error_matrix_v1.json",
        {
            "cases": errors,
            "field_errors": {
                k: sum(k in r["post_repair_wrong_fields"] for r in errors) for k in fields
            },
        },
    )
    print(json.dumps({k: v["exact_match"] for k, v in results.items() if isinstance(v, dict)}))


if __name__ == "__main__":
    main()
