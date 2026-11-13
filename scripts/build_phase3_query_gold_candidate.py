"""Build unreviewed candidate labels from deterministic repository authority only."""

import json
from pathlib import Path

from nasa_fire_ai.evaluation.phase3 import gold_digest, write_artifact
from nasa_fire_ai.query.phase3 import deterministic_proposal, validate_proposed_intent

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "evals/phase3_query_interpreter_gold.json"
TARGET = ROOT / "evals/phase3_query_interpreter_gold_candidate.json"
QUEUE = ROOT / "evals/phase3_query_gold_review_queue.json"


def candidate(case: dict) -> tuple[dict, list[dict]]:
    proposal = deterministic_proposal(case["query"])
    validated = validate_proposed_intent(proposal, case["query"])
    intent = validated.intent
    expected = {
        "query_mode": intent.query_mode,
        "materials": intent.materials,
        "investigations": intent.investigations,
        "gravity_conditions": intent.gravity_conditions,
        "phenomena": intent.phenomena,
        "safety_intents": intent.safety_intents,
        "requested_information": intent.requested_information,
        "flow_direction": intent.flow_direction,
        "numeric_constraints": {
            name: value.model_dump() if value else None
            for name, value in {
                "oxygen": intent.oxygen,
                "pressure": intent.pressure,
                "flow_velocity": intent.flow_velocity,
            }.items()
        },
        "comparison_targets": validated.comparison_targets,
        "source_constraints": [],
        "unknown_terms": validated.raw_unresolved_terms,
        "ambiguous_terms": validated.ambiguities,
        "clarification_required": validated.clarification_required,
        "no_direct_behavior": None,
    }
    needs_review = bool(validated.ambiguities or validated.raw_unresolved_terms) or case[
        "kind"
    ] in {"range", "context_followup", "phenomenon", "requested_information", "documentary"}
    status = "REVIEW_REQUIRED" if needs_review else "AUTO_HIGH_CONFIDENCE"
    queue = []
    if needs_review:
        queue.append(
            {
                "case_id": case["id"],
                "query": case["query"],
                "field": "expected",
                "candidate_values": expected,
                "reason": "ambiguity, unsupported context, or semantic scope requires domain review",
                "relevant_canonical_concepts": [],
                "current_deterministic_parser_result": intent.model_dump(),
                "review_choice": None,
            }
        )
    return {
        "id": case["id"],
        "query": case["query"],
        "kind": case["kind"],
        "expected": expected,
        "label_provenance": ["DETERMINISTIC_PARSER", "UNIT_PARSER", "SAFE_CONTROLLED_ALIAS"],
        "review_status": status,
        "review_notes": "Candidate only; not reviewed.",
        "confidence_of_rule_derivation": "HIGH" if not needs_review else "REVIEW_REQUIRED",
    }, queue


def main():
    rows, queue = [], []
    for case in json.loads(SOURCE.read_text()):
        row, pending = candidate(case)
        rows.append(row)
        queue.extend(pending)
    write_artifact(
        TARGET,
        {
            "version": "candidate-v1",
            "source_digest": gold_digest(json.loads(SOURCE.read_text())),
            "cases": rows,
        },
    )
    write_artifact(QUEUE, {"version": "candidate-v1", "items": queue})


if __name__ == "__main__":
    main()
