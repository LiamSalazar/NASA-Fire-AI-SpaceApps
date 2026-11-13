"""Offline-only Phase-3 evaluation helpers. They never call an LLM."""

import hashlib
import json
from pathlib import Path
from typing import Any


def gold_digest(cases: list[dict[str, Any]]) -> str:
    return hashlib.sha256(json.dumps(cases, sort_keys=True).encode()).hexdigest()


def _flat(value: object) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, list):
        return {json.dumps(x, sort_keys=True) for x in value}
    return {json.dumps(value, sort_keys=True)}


def score_intents(expected: dict[str, Any], actual: dict[str, Any]) -> dict[str, float | bool]:
    fields = [
        "query_mode",
        "materials",
        "investigations",
        "gravity_conditions",
        "phenomena",
        "safety_intents",
        "requested_information",
        "flow_direction",
        "numeric_constraints",
        "comparison_targets",
        "unknown_terms",
        "ambiguous_terms",
        "clarification_required",
    ]
    tp = fp = fn = 0
    exact = True
    for field in fields:
        e, a = _flat(expected.get(field)), _flat(actual.get(field))
        tp += len(e & a)
        fp += len(a - e)
        fn += len(e - a)
        exact &= e == a
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    return {
        "exact": exact,
        "precision": precision,
        "recall": recall,
        "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
    }


def write_artifact(path: Path, payload: dict[str, Any]) -> None:
    """Persist only sanitized benchmark data; reject credential-shaped content."""
    rendered = json.dumps(payload, indent=2, sort_keys=True)
    lowered = rendered.lower()
    if "nvapi-" in lowered or "sk-ant-" in lowered or "authorization" in lowered:
        raise ValueError("benchmark artifacts may not contain credentials or authorization headers")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rendered + "\n")


def claim_metrics(cases: list[dict[str, Any]]) -> dict[str, int | float]:
    claims = [claim for case in cases for claim in case.get("claims", [])]
    accepted = [claim for claim in claims if claim.get("grounding_valid")]
    cited = [claim for claim in accepted if claim.get("evidence_ids")]
    valid = [claim for claim in cited if claim.get("evidence_in_bundle")]
    return {
        "generated": len(claims),
        "accepted": len(accepted),
        "citation_coverage": len(cited) / len(accepted) if accepted else 0.0,
        "evidence_validity": len(valid) / len(cited) if cited else 0.0,
    }
