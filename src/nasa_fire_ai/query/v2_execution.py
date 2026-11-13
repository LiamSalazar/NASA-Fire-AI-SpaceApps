"""Additive V2 execution over the frozen run/evidence store."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from nasa_fire_ai.context import DEFAULT_CONTEXT_POLICY
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.models import EvidenceBundle, QueryIntent
from nasa_fire_ai.query.v2 import (
    GenericMeasurement,
    GenericValue,
    PropertyDefinition,
    QueryIntentV2,
    SemanticRegistry,
    classify_candidate_v2,
    plan_v2,
    v1_to_v2,
)
from nasa_fire_ai.services.pipeline import build_bundle

# Legacy-compatibility metadata. The V2 planner/evaluator have no property branches.
LEGACY_PROPERTY_METADATA = {
    "OxygenConcentration": ("oxygen_fraction", "fraction", "fraction"),
    "Pressure": ("pressure_pa", "Pa", "pressure"),
    "AirflowVelocity": ("flow_velocity_m_s", "m/s", "velocity"),
}
LEGACY_RELATION_METADATA = {
    "hasMaterial": "material",
    "hasGravityCondition": "gravity",
    "belongsToInvestigation": "investigation_id",
}


def legacy_registry() -> SemanticRegistry:
    return SemanticRegistry(
        [
            PropertyDefinition(name, dimension, unit)
            for name, (_, unit, dimension) in LEGACY_PROPERTY_METADATA.items()
        ]
    )


def _investigation_id(run: dict) -> str:
    return "-".join(run["id"].split("-")[:2])


def _fact_index(runs: list[dict]) -> dict[str, dict[str, str]]:
    return {
        run["id"]: {
            relation: str(_investigation_id(run) if key == "investigation_id" else run.get(key, ""))
            for relation, key in LEGACY_RELATION_METADATA.items()
        }
        for run in runs
    }


def _measurements(run: dict) -> list[GenericMeasurement]:
    output = []
    for property_id, (key, unit, _) in LEGACY_PROPERTY_METADATA.items():
        if run.get(key) is not None:
            output.append(
                GenericMeasurement(
                    property_id,
                    GenericValue(
                        reported_value=run[key],
                        reported_unit=unit,
                        canonical_value=run[key],
                        canonical_unit=unit,
                    ),
                    run["id"],
                    (run.get("evidence_ids") or [""])[0],
                )
            )
    return output


@dataclass(frozen=True)
class V2ExecutionResult:
    bundle: EvidenceBundle
    planned: object


def build_bundle_v2(
    intent_v2: QueryIntentV2,
    compatibility_intent: QueryIntent,
    query: str,
    root: Path,
    registry: EvidenceRegistry,
    semantic_registry: SemanticRegistry | None = None,
) -> V2ExecutionResult:
    """Execute V2 constraints and retain the proven EvidenceBundle boundary."""
    semantic_registry = semantic_registry or legacy_registry()
    runs = json.loads((root / "data/canonical/runs.json").read_text())
    planned = plan_v2(
        intent_v2,
        semantic_registry,
        _fact_index(runs),
        {r["id"]: r.get("evidence_ids", []) for r in runs},
    )
    direct, related = [], []
    has_constraints = bool(intent_v2.entity_constraints or intent_v2.property_constraints)
    for run in runs:
        if not has_constraints:
            continue
        relation_matches, relation_differs = [], []
        facts = _fact_index([run])[run["id"]]
        for constraint in intent_v2.entity_constraints:
            (
                relation_matches
                if facts.get(constraint.relation) == constraint.entity_id
                else relation_differs
            ).append(constraint.relation)
        status, property_detail = classify_candidate_v2(
            intent_v2.property_constraints, _measurements(run), semantic_registry
        )
        if property_detail["differs"]:
            relation_differs.extend(property_detail["differs"])
        relation_matches.extend(property_detail["matches"])
        unknown = property_detail["unknown"]
        if not relation_differs:
            status = "DIRECT"
        elif relation_matches:
            status = "RELATED"
        else:
            status = "NO_DIRECT"
        detail = {"matches": relation_matches, "differs": relation_differs, "unknown": unknown}
        if status == "NO_DIRECT":
            continue
        item = {"id": run["id"], **detail, "evidence_ids": run.get("evidence_ids", [])}
        if status == "DIRECT":
            direct.append(item)
        elif status == "RELATED":
            related.append(item)
    bundle = build_bundle(compatibility_intent, query, root, registry)
    bundle.direct_evidence, bundle.related_evidence = direct, related
    bundle.no_direct_evidence = not bool(direct)
    bundle.retrieval_metadata = {
        "query_intent_v2": intent_v2.model_dump(mode="json"),
        "v2_eligible_evidence_ids": planned.eligible_evidence_ids,
        "context_policy": DEFAULT_CONTEXT_POLICY.for_query(
            c.entity_id for c in intent_v2.entity_constraints if c.relation == "hasGravityCondition"
        ),
    }
    return V2ExecutionResult(bundle, planned)


def build_bundle_from_v1_as_v2(
    intent: QueryIntent, query: str, root: Path, registry: EvidenceRegistry
) -> V2ExecutionResult:
    return build_bundle_v2(v1_to_v2(intent), intent, query, root, registry)
