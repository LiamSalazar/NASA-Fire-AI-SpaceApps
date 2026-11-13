import json
from pathlib import Path

from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.models import EvidenceBundle, QueryIntent
from nasa_fire_ai.query.matching import classify_runs


def _ref_ids(record):
    return [ref["evidence_id"] for ref in record.get("evidence_refs", [])]


def build_bundle(
    intent: QueryIntent, query: str, root: Path, registry: EvidenceRegistry
) -> EvidenceBundle:
    records = json.loads((root / "data/canonical/records.json").read_text())
    runs = json.loads((root / "data/canonical/runs.json").read_text())
    selected_runs = [
        run
        for run in runs
        if not intent.investigations
        or run["id"].split("-")[0] + "-" + run["id"].split("-")[1] in intent.investigations
    ]
    has_structured_constraints = bool(
        intent.materials
        or intent.investigations
        or intent.gravity_conditions
        or intent.flow_velocity
        or intent.oxygen
        or intent.flow_direction
    )
    direct, related = (
        classify_runs(intent, selected_runs) if has_structured_constraints else ([], [])
    )
    safety = [record for record in records if record["type"] == "SafetyStatementRecord"]
    interventions = [record for record in records if record["type"] == "InterventionRecord"]
    observations = [record for record in records if record["type"] == "ObservationRecord"]
    relevant_safety = safety if intent.query_mode in {"safety_search", "combined_search"} else []
    if "pmma" in query.lower() or "suppression" in query.lower():
        relevant_safety = safety
    by_type = lambda value: [
        record for record in relevant_safety if record["statement_type"] == value
    ]
    eligible = [eid for match in direct for eid in match.run.get("evidence_ids", [])]
    for record in (
        relevant_safety
        + (interventions if relevant_safety else [])
        + (observations if relevant_safety else [])
    ):
        eligible.extend(_ref_ids(record))
    eligible = list(dict.fromkeys(eligible))
    passages = registry.search(query, eligible or None, limit=8)
    # A graph-eligible CSV row need not share user-facing title words (e.g.
    # "Saffire" is absent from an S1 row); retain it as constrained evidence.
    if eligible and not passages:
        passages = [
            registry.resolve(evidence_id)
            for evidence_id in eligible
            if registry.resolve(evidence_id)
        ]
    passages = list({passage["evidence_id"]: passage for passage in passages}.values())
    for passage in passages:
        passage["source_metadata"] = registry.source_metadata(passage["evidence_id"])
    direct_items = [
        {"id": m.run["id"], "matches": m.matches, "evidence_ids": m.run.get("evidence_ids", [])}
        for m in direct
    ]
    # A retrieved intervention is NASA-backed documentary evidence, but it is
    # not a structured DIRECT match merely because a safety query mentioned
    # PMMA or suppression. Keep it in ``interventions``/``evidence_passages``;
    # DIRECT remains the deterministic canonical-constraint result only.
    return EvidenceBundle(
        query_intent=intent,
        direct_evidence=direct_items,
        related_evidence=[
            {
                "id": m.run["id"],
                "matches": m.matches,
                "differs": m.differs,
                "unknown": m.unknown,
                "evidence_ids": m.run.get("evidence_ids", []),
            }
            for m in related
        ],
        interventions=interventions if relevant_safety else [],
        experimental_observations=observations if relevant_safety else [],
        nasa_conclusions=by_type("nasa_conclusion"),
        safety_implications=by_type("safety_implication"),
        requirements=by_type("requirement"),
        guidance=by_type("guidance"),
        design_test_criteria=by_type("design_criterion") + by_type("test_criterion"),
        nasa_identified_open_questions=by_type("open_question"),
        evidence_passages=passages,
        no_direct_evidence=not bool(direct_items),
    )
