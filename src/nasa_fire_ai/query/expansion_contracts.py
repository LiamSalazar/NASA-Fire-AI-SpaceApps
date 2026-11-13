"""Typed numeric equivalence and non-authoritative discovery hypotheses."""

import math
import re
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict

from nasa_fire_ai.normalization.units import normalize

NUMBER = r"[-+]?\d+(?:\.\d+)?"
UNIT = r"(?:(?:cm/s|mm/s|m/s|mmHg|kPa|Pa|fraction|cm|mm|m|W|K|s)\b|%)"
PATTERN = re.compile(
    rf"(?P<prefix>between\s+|from\s+|at\s+least\s+|at\s+most\s+|greater\s+than\s+|less\s+than\s+|approximately\s+|about\s+|>=\s*|<=\s*|>\s*|<\s*|=\s*|≈\s*)?"
    rf"(?P<value>{NUMBER})\s*(?P<unit1>{UNIT})?"
    rf"(?:(?P<join>\s*(?:\+/-|±|to|and)\s*)(?P<second>{NUMBER})\s*)?"
    rf"(?P<unit2>{UNIT})?",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class NumericExpression:
    operator: str
    value: float
    unit: str | None
    upper_or_tolerance: float | None = None
    lower_inclusive: bool | None = None
    upper_inclusive: bool | None = None


def numeric_expressions(text):
    expressions = []
    for match in PATTERN.finditer(text):
        # Numbers embedded in experiment identifiers are identity, not quantities.
        if match.start() and text[match.start() - 1].isalnum():
            continue
        prefix = (match["prefix"] or "").strip().lower()
        operator = {
            ">=": "GTE",
            "<=": "LTE",
            ">": "GT",
            "<": "LT",
            "=": "EQ",
            "at least": "GTE",
            "at most": "LTE",
            "greater than": "GT",
            "less than": "LT",
            "approximately": "APPROX",
            "about": "APPROX",
            "≈": "APPROX",
        }.get(prefix, "EQ")
        join = (match["join"] or "").strip()
        second = float(match["second"]) if match["second"] else None
        if join:
            operator = "APPROX" if join in {"±", "+/-"} else "BETWEEN"
        unit = match["unit2"] or match["unit1"]
        value = float(match["value"])
        if unit is None:
            # Unsupported unit tokens remain unresolved lexical quantities.
            # Equal bare numbers do not prove equality across unknown dimensions.
            suffix = re.match(r"\s*([A-Za-z°μ][A-Za-z0-9°μ/^\-]*)", text[match.end() :])
            if suffix:
                unit = "UNRESOLVED:" + suffix[1].casefold()
        if unit and not unit.startswith("UNRESOLVED:"):
            value, canonical = normalize(value, match["unit1"] or unit)
            if second is not None:
                second, second_unit = normalize(second, unit)
                if second_unit != canonical:
                    raise ValueError("incompatible numeric dimensions")
            unit = canonical
        inclusion = (
            True
            if re.search(r"\binclusive\b", text, re.IGNORECASE)
            else (False if re.search(r"\bexclusive\b", text, re.IGNORECASE) else None)
        )
        expressions.append(
            NumericExpression(
                operator,
                value,
                unit,
                second,
                inclusion if operator == "BETWEEN" else None,
                inclusion if operator == "BETWEEN" else None,
            )
        )
    return expressions


def numeric_equivalence(original, expanded):
    try:
        left, right = numeric_expressions(original), numeric_expressions(expanded)
    except ValueError:
        return False, "unsupported_or_incompatible_numeric_unit"
    if len(left) != len(right):
        return False, "numeric_constraint_changed_or_dropped"
    for a, b in zip(left, right, strict=True):
        if a.operator != b.operator:
            return False, "numeric_operator_changed"
        if (a.lower_inclusive, a.upper_inclusive) != (b.lower_inclusive, b.upper_inclusive):
            return False, "numeric_range_inclusivity_changed"
        if a.unit != b.unit:
            return False, "numeric_unit_dimension_changed"
        if not math.isclose(a.value, b.value, rel_tol=1e-12, abs_tol=1e-12):
            return False, "numeric_constraint_changed_or_dropped"
        if (a.upper_or_tolerance is None) != (b.upper_or_tolerance is None) or (
            a.upper_or_tolerance is not None
            and not math.isclose(
                a.upper_or_tolerance, b.upper_or_tolerance, rel_tol=1e-12, abs_tol=1e-12
            )
        ):
            return False, "numeric_range_or_tolerance_changed"
    return True, "typed_numeric_constraints_preserved"


class DiscoveryHypothesis(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str
    relationship: Literal[
        "BROADER_DISCOVERY",
        "NARROWER_DISCOVERY",
        "SIBLING_DISCOVERY",
        "RELATED_PHENOMENON",
        "DOCUMENTARY_SYNONYM",
        "UNVERIFIED_HYPOTHESIS",
    ]
    requested_concept: str | None = None
    proposed_concept: str | None = None


def validate_discovery(hypothesis, intent, store, evidence_registry):
    """Discovery can change search scope, never original intent or eligibility."""
    if not hypothesis.query.strip() or len(hypothesis.query) > 500:
        return False, "empty_or_overlong"
    expected = {
        "BROADER_DISCOVERY": "ANCESTOR",
        "NARROWER_DISCOVERY": "DESCENDANT",
        "SIBLING_DISCOVERY": "SIBLING",
    }
    if hypothesis.relationship in expected:
        from nasa_fire_ai.query.hierarchy import traverse

        verified = False
        for constraint in intent.entity_constraints:
            if constraint.entity_id != hypothesis.requested_concept:
                continue
            paths = traverse(store, constraint.entity_id, constraint.relation, evidence_registry)[
                "paths"
            ]
            row = paths.get(hypothesis.proposed_concept)
            verified |= bool(row and row["relationship_type"] == expected[hypothesis.relationship])
        if not verified:
            return False, "declared_relationship_not_graph_validated"
    return True, "exploratory_only_original_intent_unchanged"
