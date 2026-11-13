"""Phase-3 proposal validation.  No model output reaches retrieval unvalidated."""

import hashlib
import json
import re
from pathlib import Path

from nasa_fire_ai.models import (
    ConversationContext,
    NumericFilter,
    ProposedEntityMention,
    ProposedNumericConstraint,
    ProposedQueryIntent,
    QueryIntent,
    ValidatedQueryIntent,
)
from nasa_fire_ai.normalization.units import normalize
from nasa_fire_ai.query.lexicon import load_lexicon, resolve

ROOT = Path(__file__).resolve().parents[3]
_MODES = {"general_search", "experiment_search", "safety_search", "combined_search", "compare"}
_REQUESTED = {
    "experiments",
    "observations",
    "measurements",
    "conclusions",
    "publications",
    "safety",
}
_SAFETY = {"requirement", "guidance", "design_criterion", "safety_implication", "open_question"}
_CANONICAL = {
    "material:pmma": ("materials", "PMMA"),
    "material:sibal_fabric": ("materials", "SIBAL Fabric"),
    "investigation:saffire_i": ("investigations", "psi-98"),
    "investigation:bass_ii": ("investigations", "psi-25"),
    "gravity:microgravity": ("gravity_conditions", "microgravity"),
}


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def lexicon_digest() -> str:
    return _digest(ROOT / "domain/lexicon.yaml")


def ontology_digest() -> str:
    return _digest(ROOT / "data/canonical/graph.ttl")


def deterministic_proposal(text: str) -> ProposedQueryIntent:
    """Conservative non-LLM proposal; preserves lexicon ambiguity and unknown terms."""
    lower = text.lower()
    mentions: dict[str, list[ProposedEntityMention]] = {
        "materials": [],
        "investigations": [],
        "gravity_conditions": [],
    }
    ambiguities: list[str] = []
    unknown: list[str] = []
    for item in resolve(text):
        if item.status == "ambiguous":
            ambiguities.append(
                f"{item.matched_alias} is ambiguous: {', '.join(item.canonical_ids)}"
            )
            unknown.append(item.matched_alias or "")
            continue
        if item.status == "resolved" and item.canonical_ids[0] in _CANONICAL:
            field, label = _CANONICAL[item.canonical_ids[0]]
            mentions[field].append(
                ProposedEntityMention(
                    raw_span=item.matched_alias or label,
                    entity_type_candidate=field[:-1],
                    canonical_candidate=item.canonical_ids[0],
                )
            )
    if "velocity" in lower and not re.search(r"(?:air\s*flow|airflow|flow velocity)", lower):
        ambiguities.append("velocity is ambiguous: airflow velocity or flame-spread velocity")
        unknown.append("velocity")
    if "xenon" in lower:
        unknown.append("xenon")
    numeric: list[ProposedNumericConstraint] = []
    match = re.search(
        r"(?:air\s*flow|airflow|flow velocity)\s*(?:is\s*)?(<=|>=|<|>|=|below|under|at most|no more than)?\s*(?:about|roughly)?\s*(\d+(?:\.\d+)?)\s*(cm/s|m/s)",
        lower,
    )
    if match:
        op = {"below": "<", "under": "<", "at most": "<=", "no more than": "<="}.get(
            match.group(1) or "=", match.group(1) or "="
        )
        numeric.append(
            ProposedNumericConstraint(
                field_candidate="flow_velocity",
                operator_candidate=op,
                raw_numeric_span=match.group(0),
                value=float(match.group(2)),
                reported_unit=match.group(3),
                is_approximate=bool(re.search(r"about|roughly", match.group(0))),
            )
        )
    requested = []
    if any(x in lower for x in ("observe", "observed")):
        requested.append("observations")
    if "conclusion" in lower:
        requested.append("conclusions")
    if any(x in lower for x in ("safety", "suppress", "requirement", "guidance", "open question")):
        requested.append("safety")
    if any(x in lower for x in ("compare", "run", "experiment", "saffire", "bass")):
        requested.append("experiments")
    safety = []
    for word, value in (
        ("requirement", "requirement"),
        ("guidance", "guidance"),
        ("open question", "open_question"),
        ("suppress", "safety_implication"),
    ):
        if word in lower:
            safety.append(value)
    targets = re.findall(r"\bS\d+\b", text, flags=re.IGNORECASE)
    mode = (
        "compare"
        if "compare" in lower
        else "safety_search"
        if safety
        else "experiment_search"
        if requested
        else "general_search"
    )
    return ProposedQueryIntent(
        query_mode=mode,
        materials=mentions["materials"],
        investigations=mentions["investigations"],
        gravity_conditions=mentions["gravity_conditions"],
        safety_intents=safety,
        requested_information=list(dict.fromkeys(requested)),
        numeric_constraints=numeric,
        comparison_targets=targets,
        raw_unresolved_terms=[x for x in unknown if x],
        ambiguities=ambiguities,
        clarification_required=bool(ambiguities),
    )


def _canonical_for_mention(mention: ProposedEntityMention) -> tuple[str, str] | None:
    """Use exact canonical/safe lexicon resolution before an LLM candidate."""
    raw = mention.raw_span.strip().lower()
    lexicon = load_lexicon()
    for item in lexicon:
        if raw == item["canonical_label"].lower():
            return _CANONICAL.get(item["canonical_id"])
    resolutions = resolve(mention.raw_span)
    if any(r.status == "ambiguous" for r in resolutions):
        return None
    for resolution in resolutions:
        if resolution.status == "resolved" and resolution.canonical_ids[0] in _CANONICAL:
            return _CANONICAL[resolution.canonical_ids[0]]
    if mention.canonical_candidate in _CANONICAL:
        return _CANONICAL[mention.canonical_candidate]
    return None


def _resolve_comparison(
    targets: list[str], context: ConversationContext | None
) -> tuple[list[str], list[str]]:
    runs = json.loads((ROOT / "data/canonical/runs.json").read_text())
    ids: list[str] = []
    ambiguous: list[str] = []
    for target in targets:
        hits = [r["id"] for r in runs if r["id"].lower().endswith("-" + target.lower())]
        if context and target.lower() in {
            x.split("-")[-1].lower() for x in context.current_run_ids
        }:
            hits = [x for x in context.current_run_ids if x.lower().endswith("-" + target.lower())]
        if len(hits) == 1:
            ids.extend(hits)
        elif len(hits) > 1:
            ambiguous.append(f"{target} matches multiple validated runs")
    return list(dict.fromkeys(ids)), ambiguous


def validate_proposed_intent(
    proposal: ProposedQueryIntent, raw_query: str, context: ConversationContext | None = None
) -> ValidatedQueryIntent:
    # The live adapter emits raw linguistic mentions.  Deterministic code,
    # not the model, expands them into the legacy fielded proposal contract.
    if proposal.mentions:
        for encoded in proposal.mentions:
            text, _, type_candidate = encoded.partition("|")
            target = {
                "material": proposal.materials,
                "investigation": proposal.investigations,
                "gravity": proposal.gravity_conditions,
                "phenomenon": proposal.phenomena,
            }.get(type_candidate)
            if target is not None:
                target.append(
                    ProposedEntityMention(raw_span=text, entity_type_candidate=type_candidate)
                )
        proposal.query_mode = (
            proposal.query_mode_candidate
            if proposal.query_mode_candidate in _MODES
            else deterministic_proposal(raw_query).query_mode
        )
        proposal.raw_unresolved_terms = list(
            dict.fromkeys(proposal.raw_unresolved_terms + proposal.unresolved_terms)
        )
        proposal.ambiguities = list(
            dict.fromkeys(proposal.ambiguities + proposal.ambiguity_candidates)
        )
    actions: list[str] = []
    ambiguities = list(proposal.ambiguities)
    unresolved = list(proposal.raw_unresolved_terms)
    values: dict[str, object] = {"materials": [], "investigations": [], "gravity_conditions": []}
    for field, mentions in (
        ("materials", proposal.materials),
        ("investigations", proposal.investigations),
        ("gravity_conditions", proposal.gravity_conditions),
    ):
        for mention in mentions:
            resolved = _canonical_for_mention(mention)
            if resolved is None:
                ambiguities.append(f"Unresolved or ambiguous {mention.raw_span}")
                unresolved.append(mention.raw_span)
            else:
                target_field, label = resolved
                if target_field != field:
                    ambiguities.append(f"{mention.raw_span} does not validate as {field}")
                    unresolved.append(mention.raw_span)
                else:
                    values[field].append(label)  # type: ignore[index]
                    actions.append(f"resolved {mention.raw_span} to {label}")
    filters: dict[str, NumericFilter] = {}
    for number in proposal.numeric_constraints:
        if number.value is None or not number.reported_unit:
            raise ValueError("numeric proposal requires a value and supported unit")
        canonical_value, canonical_unit = normalize(number.value, number.reported_unit)
        expected_unit = {"oxygen": "fraction", "pressure": "Pa", "flow_velocity": "m/s"}[
            number.field_candidate
        ]
        if canonical_unit != expected_unit:
            raise ValueError(
                f"unsupported unit for {number.field_candidate}: {number.reported_unit}"
            )
        # Preserve user-reported value/unit in QueryIntent; deterministic matcher converts it.
        filters[number.field_candidate] = NumericFilter(
            operator=number.operator_candidate, value=number.value, unit=number.reported_unit
        )
        actions.append(f"validated {number.raw_numeric_span} as {canonical_value} {canonical_unit}")
    if proposal.query_mode not in _MODES:
        raise ValueError(f"unsupported query mode: {proposal.query_mode}")
    comparison_ids, comparison_ambiguity = _resolve_comparison(proposal.comparison_targets, context)
    ambiguities.extend(comparison_ambiguity)
    if comparison_ids and not values["investigations"]:
        values["investigations"].extend(
            "-".join(run_id.split("-")[:2]) for run_id in comparison_ids
        )  # type: ignore[union-attr]
        actions.append("derived investigation constraint from validated comparison runs")
    intent = QueryIntent(
        query_mode=proposal.query_mode,
        materials=list(dict.fromkeys(values["materials"])),  # type: ignore[arg-type]
        investigations=list(dict.fromkeys(values["investigations"])),  # type: ignore[arg-type]
        gravity_conditions=list(dict.fromkeys(values["gravity_conditions"])),  # type: ignore[arg-type]
        oxygen=filters.get("oxygen"),
        pressure=filters.get("pressure"),
        flow_velocity=filters.get("flow_velocity"),
        flow_direction=proposal.flow_direction,
        phenomena=[x.raw_span for x in proposal.phenomena],
        safety_intents=[x for x in proposal.safety_intents if x in _SAFETY],
        requested_information=[x for x in proposal.requested_information if x in _REQUESTED],
    )
    clarification = None
    if ambiguities:
        if any("flow" in item.lower() for item in ambiguities):
            clarification = (
                "By velocity or flow, do you mean airflow velocity or flame-spread velocity?"
            )
        elif any("acrylic" in item.lower() for item in ambiguities):
            clarification = "Does acrylic refer to a specific material documented in this corpus?"
        else:
            clarification = (
                "Please clarify the ambiguous term before relying on a constrained result."
            )
    return ValidatedQueryIntent(
        intent=intent,
        raw_query=raw_query,
        raw_unresolved_terms=list(dict.fromkeys(unresolved)),
        ambiguities=list(dict.fromkeys(ambiguities)),
        clarification_required=bool(ambiguities),
        clarification=clarification,
        comparison_targets=comparison_ids,
        validation_actions=actions,
        ontology_digest=ontology_digest(),
        lexicon_digest=lexicon_digest(),
    )
