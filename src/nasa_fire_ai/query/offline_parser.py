"""Small conservative parser for the indexed Day-3 vocabulary only."""

import re

from nasa_fire_ai.models import NumericFilter, QueryIntent
from nasa_fire_ai.query.lexicon import resolve


def parse_query(text: str) -> QueryIntent:
    lower = text.lower()
    concepts = [r.canonical_ids[0] for r in resolve(text) if r.status == "resolved"]
    materials = [
        {"material:pmma": "PMMA", "material:sibal_fabric": "SIBAL Fabric"}[c]
        for c in concepts
        if c in {"material:pmma", "material:sibal_fabric"}
    ]
    investigations = [
        {"investigation:saffire_i": "psi-98", "investigation:bass_ii": "psi-25"}[c]
        for c in concepts
        if c in {"investigation:saffire_i", "investigation:bass_ii"}
    ]
    gravity = ["microgravity"] if "gravity:microgravity" in concepts else []
    safety_words = {
        "requirement": "requirement",
        "guidance": "guidance",
        "suppression": "safety_implication",
        "open question": "open_question",
    }
    safety = [value for word, value in safety_words.items() if word in lower]
    if "suppress" in lower and "safety_implication" not in safety:
        safety.append("safety_implication")
    requested = []
    if any(
        word in lower
        for word in (
            "run",
            "experiment",
            "compare",
            "saffire",
            "bass",
            "tested",
            "intervention",
            "observed",
        )
    ):
        requested.append("experiments")
    if safety or any(word in lower for word in ("observed", "conclusion", "safety")):
        requested.append("safety")
    flow = None
    match = re.search(
        r"(?:air\s*flow|airflow|flow)\s*(<=|>=|<|>|=|at most)?\s*(\d+(?:\.\d+)?)\s*(cm/s|m/s)",
        lower,
    )
    if match:
        operator = {"below": "<", "under": "<", "at most": "<=", "no more than": "<="}.get(
            match.group(1) or "=", match.group(1) or "="
        )
        flow = NumericFilter(operator=operator, value=float(match.group(2)), unit=match.group(3))
    mode = (
        "compare"
        if "compare" in lower
        else "combined_search"
        if requested == ["experiments", "safety"]
        else "safety_search"
        if safety
        else "experiment_search"
        if requested
        else "general_search"
    )
    return QueryIntent(
        query_mode=mode,
        materials=materials,
        investigations=investigations,
        gravity_conditions=gravity,
        flow_velocity=flow,
        safety_intents=safety,
        requested_information=requested,
    )
