"""Scientific facets: independent dimensions of what an extracted record asserts.

A legacy epistemic role ("measured_observation", "experimental_configuration", ...)
bundles several independent scientific dimensions into one label. Here each role is
a *profile* over those dimensions, so records and receipts written with the old
roles keep their meaning, while new kinds of statement (a plan, a goal, a design or
test criterion, a proposed condition) are expressed by combining dimensions rather
than by inventing an unrelated label for each case.

Dimensions:

- ``statement_type``: what kind of scientific statement it is.
- ``epistemic_role``: how the source stands toward it (observed, derived, concluded,
  interpreted, hypothesized, questioned, prescribed, intended, retained).
- ``modality``: actual, proposed, intended, conditional, hypothetical or
  prescriptive. Only ``actual`` describes something that happened.
- ``execution_status``: executed, planned, not_applicable or unknown; ongoing for an
  activity the source reports as under way (the statement's ``execution``).
- ``temporal_scope``: the current study, historical (cited or background) work,
  the future, or unknown; background for the state of the art or prior knowledge of
  the field (the statement's ``scope``).
- ``attribution``: the current study, a cited study, or unknown.

Subject, applicability, source evidence and verification stay where they already
live on the record (``subjects``/``subject``, the scope checks, ``support_spans``,
``status``/``proposal_state``); ``facets_of`` reports them beside the dimensions so
that one call answers every question about a record.

The source must support the facets. ``facet_review`` reads the printed sentence
through ``clause_cues`` (its governing clause, frames and purpose removed) for the
modality, plan, goal or criterion a record claims; it never upgrades a record, and
a reading the clause does not settle is held for review.
"""

import os
import re
from dataclasses import dataclass

from nasa_fire_ai.ingestion import clause_cues

MODALITIES = (
    "actual",
    "proposed",
    "intended",
    "conditional",
    "hypothetical",
    "prescriptive",
)


@dataclass(frozen=True)
class Role:
    """One role of a statement or a value: the single place every role table is read from.

    ``statement_profile`` and ``quantity_profile`` are the role's default value on each
    facet axis for a statement and for a quantity (None when the role is not offered for
    that kind). Every other table that names roles is a view of ``ROLES``.
    """

    name: str
    kinds: tuple
    statement_profile: dict | None
    quantity_profile: dict | None
    family: str | None
    statement_class: str | None
    class_options: tuple
    value_definition: str | None
    option_rank: int | None
    quantity_rank: int | None
    value_rank: int | None
    definition: str | None
    prompt_rank: int | None
    checks: tuple
    allowed: dict
    asserts: bool
    temporal_scope: str
    evidence_basis: str
    decisions: tuple
    flag: str | None
    holds: tuple = ()
    definition_v2: str | None = None


# Statement roles in the order of the wire schema, then the value-only roles.
ROLES = {
    r.name: r
    for r in (
        Role(
            name="measured_observation",
            kinds=("statements",),
            statement_profile={
                "statement_type": "observation",
                "epistemic_role": "observed",
                "modality": "actual",
                "execution_status": "executed",
            },
            quantity_profile=None,
            family="OBSERVATION",
            statement_class="ReportedObservation",
            class_options=(),
            value_definition=None,
            option_rank=0,
            quantity_rank=None,
            value_rank=None,
            definition='what this study saw or measured in its own tests\n  ("The third coupon charred along its upper edge.").',
            prompt_rank=0,
            allowed={},
            asserts=True,
            temporal_scope="current",
            evidence_basis="measured",
            decisions=("R1", "R6", "V3"),
            definition_v2='what this study saw or measured in its own tests, with the outcome stated\n  ("The third coupon charred along its upper edge."); how a run was watched or recorded is\n  experimental_configuration, and the result of a model or a simulation is a conclusion or an\n  interpretation with basis simulated, never an observation.',
            holds=("instrument_setup", "directive_not_executed", "qualifiers_preserved"),
            checks=(
                "observation_must_be",
                "observed_or_concluded_claims",
                "observation_inferred",
                "multiple_bullets",
                "observation_layout",
                "observation_derived",
            ),
            flag=None,
        ),
        Role(
            name="author_reported_conclusion",
            kinds=("statements",),
            statement_profile={
                "statement_type": "conclusion",
                "epistemic_role": "concluded",
                "modality": "actual",
                "execution_status": "executed",
            },
            quantity_profile=None,
            family="INTERPRETATION",
            statement_class="NASAConclusion",
            class_options=(),
            value_definition=None,
            option_rank=12,
            quantity_rank=None,
            value_rank=None,
            definition='what the authors conclude from their own work, stated\n  as established ("The coated foam therefore resists ignition better than bare foam.").',
            prompt_rank=1,
            allowed={
                "scope": frozenset({"background"}),
                "execution": frozenset({"ongoing"}),
                "evidence_basis": frozenset({"predicted", "simulated"}),
            },
            asserts=True,
            temporal_scope="current",
            evidence_basis="stated",
            decisions=("R1", "R6", "V2"),
            definition_v2='what the authors conclude from their own work, stated\n  as established ("The coated foam therefore resists ignition better than bare foam."); an\n  activity the source reports as under way is not a conclusion.',
            holds=("directive_not_executed", "qualifiers_preserved"),
            checks=("observed_or_concluded_claims", "multiple_bullets"),
            flag=None,
        ),
        Role(
            name="tentative_interpretation",
            kinds=("statements",),
            statement_profile={
                "statement_type": "interpretation",
                "epistemic_role": "interpreted",
                "modality": "actual",
                "execution_status": "executed",
            },
            quantity_profile=None,
            family="INTERPRETATION",
            statement_class="NASAConclusion",
            class_options=(),
            value_definition=None,
            option_rank=13,
            quantity_rank=None,
            value_rank=None,
            definition='a hedged reading of results, including one that offers\n  an answer while asking for more work to settle it ("Airflow may govern the\n  charring, but more drops would have to confirm it.").',
            prompt_rank=2,
            allowed={
                "scope": frozenset({"background"}),
                "evidence_basis": frozenset({"predicted", "simulated"}),
            },
            asserts=True,
            temporal_scope="current",
            evidence_basis="stated",
            decisions=("R1", "R6"),
            definition_v2='a hedged reading of results, including one that offers\n  an answer while asking for more work to settle it, and one considered but not established\n  ("Airflow may govern the charring, but more drops would have to confirm it."); what the\n  source says is not known stays open_question.',
            holds=("directive_not_executed",),
            checks=("multiple_bullets",),
            flag=None,
        ),
        Role(
            name="hypothesis",
            kinds=("statements",),
            statement_profile={
                "statement_type": "hypothesis",
                "epistemic_role": "hypothesized",
                "modality": "hypothetical",
                "execution_status": "not_applicable",
            },
            quantity_profile=None,
            family="INTERPRETATION",
            statement_class="NASAConclusion",
            class_options=(),
            value_definition=None,
            option_rank=14,
            quantity_rank=None,
            value_rank=None,
            definition='a proposition put forward to be tested, not yet a result\n  ("Thinner panels are expected to burn faster.").',
            prompt_rank=3,
            allowed={
                "modality": frozenset({"conditional"}),
                "evidence_basis": frozenset({"predicted", "simulated"}),
            },
            asserts=True,
            temporal_scope="unknown",
            evidence_basis="stated",
            decisions=("R1", "R6"),
            checks=("multiple_bullets",),
            flag=None,
        ),
        Role(
            name="open_question",
            kinds=("statements",),
            statement_profile={
                "statement_type": "question",
                "epistemic_role": "questioned",
                "modality": "hypothetical",
                "execution_status": "not_applicable",
            },
            quantity_profile=None,
            family="QUESTION",
            statement_class="OpenQuestion",
            class_options=(),
            value_definition=None,
            option_rank=15,
            quantity_rank=None,
            value_rank=None,
            definition='what the source says is not known ("The gas speed beside the panel\n  during the drop is not known.").',
            prompt_rank=4,
            allowed={"modality": frozenset({"conditional"})},
            asserts=True,
            temporal_scope="unknown",
            evidence_basis="stated",
            decisions=("R1",),
            checks=("open_question_explicit", "multiple_bullets"),
            flag=None,
        ),
        Role(
            name="normative_requirement",
            kinds=("statements",),
            statement_profile={
                "statement_type": "requirement",
                "epistemic_role": "prescribed",
                "modality": "prescriptive",
                "execution_status": "not_applicable",
            },
            quantity_profile=None,
            family="NORM",
            statement_class="Requirement",
            class_options=(),
            value_definition=None,
            option_rank=4,
            quantity_rank=None,
            value_rank=None,
            definition='a requirement the source states\n  ("Each panel shall self-extinguish within ten seconds.").',
            prompt_rank=5,
            allowed={"modality": frozenset({"conditional"})},
            asserts=True,
            temporal_scope="unknown",
            evidence_basis="stated",
            decisions=("R1",),
            checks=("normative_explicit", "multiple_bullets"),
            flag=None,
        ),
        Role(
            name="guidance",
            kinds=("statements",),
            statement_profile={
                "statement_type": "guidance",
                "epistemic_role": "prescribed",
                "modality": "prescriptive",
                "execution_status": "not_applicable",
            },
            quantity_profile=None,
            family="NORM",
            statement_class="Guidance",
            class_options=(),
            value_definition=None,
            option_rank=5,
            quantity_rank=None,
            value_rank=None,
            definition='a recommendation the source itself gives ("Inspect each seal before use.").',
            prompt_rank=8,
            allowed={"modality": frozenset({"conditional"})},
            asserts=True,
            temporal_scope="unknown",
            evidence_basis="stated",
            decisions=("R1",),
            checks=("guidance_explicit", "multiple_bullets"),
            flag=None,
        ),
        Role(
            name="experimental_configuration",
            kinds=("statements", "quantities"),
            statement_profile={
                "statement_type": "configuration",
                "epistemic_role": "reported",
                "modality": "actual",
                "execution_status": "executed",
            },
            quantity_profile={
                "statement_type": "setpoint",
                "epistemic_role": "reported",
                "modality": "actual",
                "execution_status": "executed",
            },
            family="CONFIGURATION",
            statement_class="ExperimentalCondition",
            class_options=("ExperimentalCondition", "Intervention"),
            value_definition="a setting: a value the study set for its tests ('held at 40 % humidity'); planned or proposed settings keep this role with modality proposed or intended",
            option_rank=1,
            quantity_rank=2,
            value_rank=1,
            definition='how this study\'s tests were set up or run, including\n  executed procedure steps ("The panels were mounted upright above the igniter.").',
            prompt_rank=9,
            allowed={
                "execution_v2": frozenset({"ongoing"}),
                "modality": frozenset({"conditional", "hypothetical", "intended", "proposed"}),
            },
            asserts=True,
            temporal_scope="current",
            evidence_basis="stated",
            decisions=("R1", "V2", "V3"),
            definition_v2='how this study\'s tests were set up or run, including\n  executed procedure steps and how the run was watched or recorded with cameras or sensors\n  ("The panels were mounted upright above the igniter."); work only requested of someone is\n  planned_activity, not an executed step.',
            holds=("directive_not_executed", "qualifiers_preserved"),
            checks=("multiple_bullets", "configuration_objective"),
            flag=None,
        ),
        Role(
            name="derived_quantity",
            kinds=("statements", "quantities"),
            statement_profile={
                "statement_type": "derivation",
                "epistemic_role": "derived",
                "modality": "actual",
                "execution_status": "not_applicable",
            },
            quantity_profile={
                "statement_type": "derivation",
                "epistemic_role": "derived",
                "modality": "actual",
                "execution_status": "not_applicable",
            },
            family="DERIVATION",
            statement_class="Measurement",
            class_options=("Measurement",),
            value_definition="a value computed from data: a fit, difference, margin or ratio",
            option_rank=8,
            quantity_rank=1,
            value_rank=3,
            definition='a result computed from data, such as a fit, difference or margin\n  ("The fitted slope leaves a margin of two percent.").',
            prompt_rank=10,
            allowed={
                "modality": frozenset({"conditional", "hypothetical"}),
                "evidence_basis": frozenset({"predicted", "simulated"}),
            },
            asserts=True,
            temporal_scope="current",
            evidence_basis="computed",
            decisions=("R1", "R6"),
            checks=("multiple_bullets",),
            flag=None,
        ),
        Role(
            name="documentary_context",
            kinds=("statements",),
            statement_profile={
                "statement_type": "documentary",
                "epistemic_role": "retained",
                "modality": "unknown",
                "execution_status": "unknown",
            },
            quantity_profile=None,
            family="DOCUMENTARY",
            statement_class="Publication",
            class_options=("Publication", "Document"),
            value_definition=None,
            option_rank=11,
            quantity_rank=None,
            value_rank=None,
            definition='what the document is or points to, such as its scope, a\n  figure or table pointer, or where its data come from ("Table 2 lists the panel\n  thicknesses.").',
            prompt_rank=11,
            allowed={},
            asserts=False,
            temporal_scope="unknown",
            evidence_basis="retained",
            decisions=("R1", "P6"),
            holds=("documentary_activity",),
            checks=(),
            flag=None,
        ),
        Role(
            name="planned_activity",
            kinds=("statements",),
            statement_profile={
                "statement_type": "plan",
                "epistemic_role": "intended",
                "modality": "proposed",
                "execution_status": "planned",
            },
            quantity_profile=None,
            family="INTENTION",
            statement_class="PlannedActivity",
            class_options=(),
            value_definition=None,
            option_rank=6,
            quantity_rank=None,
            value_rank=None,
            definition='work the source says will be or is planned to be done, not yet\n  done ("Each panel will be dropped twice in the next series.").',
            prompt_rank=12,
            allowed={
                "execution_v2": frozenset({"ongoing"}),
                "modality": frozenset({"conditional", "intended", "proposed"}),
                "statement_facets": frozenset({"plan_goal"}),
            },
            asserts=True,
            temporal_scope="future",
            evidence_basis="stated",
            decisions=("R1", "V2", "V3"),
            definition_v2='work the source says will be or is planned to be done, not yet\n  done, including work only requested of, asked of or assigned to someone ("Each panel will be\n  dropped twice in the next series.").',
            checks=("multiple_bullets",),
            flag=None,
        ),
        Role(
            name="stated_goal",
            kinds=("statements",),
            statement_profile={
                "statement_type": "goal",
                "epistemic_role": "intended",
                "modality": "intended",
                "execution_status": "not_applicable",
            },
            quantity_profile=None,
            family="INTENTION",
            statement_class="ResearchGoal",
            class_options=(),
            value_definition=None,
            option_rank=7,
            quantity_rank=None,
            value_rank=None,
            definition='an aim or objective the source states ("The work seeks to rank the\n  foams by charring rate.").',
            prompt_rank=13,
            allowed={
                "modality": frozenset({"conditional", "intended", "proposed"}),
                "statement_facets": frozenset({"plan_goal"}),
            },
            asserts=True,
            temporal_scope="future",
            evidence_basis="stated",
            decisions=("R1", "V3"),
            checks=("multiple_bullets",),
            flag=None,
        ),
        Role(
            name="design_criterion",
            kinds=("statements",),
            statement_profile={
                "statement_type": "design_criterion",
                "epistemic_role": "prescribed",
                "modality": "prescriptive",
                "execution_status": "not_applicable",
            },
            quantity_profile=None,
            family="NORM",
            statement_class="DesignCriterion",
            class_options=(),
            value_definition=None,
            option_rank=3,
            quantity_rank=None,
            value_rank=None,
            definition='a target or limit a design must meet, when the source states it\n  as such ("The enclosure is sized to hold its wall below 40 C.").',
            prompt_rank=7,
            allowed={"modality": frozenset({"conditional"})},
            asserts=True,
            temporal_scope="unknown",
            evidence_basis="stated",
            decisions=("R1",),
            checks=("multiple_bullets",),
            flag=None,
        ),
        Role(
            name="test_criterion",
            kinds=("statements",),
            statement_profile={
                "statement_type": "test_criterion",
                "epistemic_role": "prescribed",
                "modality": "prescriptive",
                "execution_status": "not_applicable",
            },
            quantity_profile=None,
            family="NORM",
            statement_class="TestCriterion",
            class_options=(),
            value_definition=None,
            option_rank=2,
            quantity_rank=None,
            value_rank=None,
            definition='the condition a test result must meet to pass or fail, when the\n  source states it as such ("A panel passes when its char stays shorter than 9 cm.").',
            prompt_rank=6,
            allowed={"modality": frozenset({"conditional"})},
            asserts=True,
            temporal_scope="unknown",
            evidence_basis="stated",
            decisions=("R1",),
            checks=("multiple_bullets",),
            flag=None,
        ),
        Role(
            name="data_provenance",
            kinds=("statements",),
            statement_profile={
                "statement_type": "provenance",
                "epistemic_role": "reported",
                "modality": "actual",
                "execution_status": "not_applicable",
            },
            quantity_profile=None,
            family=None,
            statement_class="Publication",
            class_options=("Publication", "Document"),
            value_definition=None,
            option_rank=None,
            quantity_rank=None,
            value_rank=None,
            definition=None,
            prompt_rank=None,
            allowed={
                "modality": frozenset({"conditional", "hypothetical", "intended", "proposed"})
            },
            asserts=True,
            temporal_scope="unknown",
            evidence_basis="stated",
            decisions=("R1",),
            checks=("multiple_bullets",),
            flag="SCIENCE_STRUCTURED_PROVENANCE",
        ),
        Role(
            name="reported_quantity",
            kinds=("quantities",),
            statement_profile=None,
            quantity_profile={
                "statement_type": "measurement",
                "epistemic_role": "observed",
                "modality": "actual",
                "execution_status": "executed",
            },
            family="OBSERVATION",
            statement_class=None,
            class_options=(),
            value_definition="a measurement datum: what this study measured ('the panel bent 4 mm')",
            option_rank=9,
            quantity_rank=0,
            value_rank=0,
            definition=None,
            prompt_rank=None,
            allowed={},
            asserts=True,
            temporal_scope="current",
            evidence_basis="measured",
            decisions=("R1", "R6"),
            holds=("directive_not_executed", "qualifiers_preserved"),
            checks=(),
            flag=None,
        ),
        Role(
            name="criterion_value",
            kinds=("quantities",),
            statement_profile=None,
            quantity_profile={
                "statement_type": "criterion_value",
                "epistemic_role": "prescribed",
                "modality": "prescriptive",
                "execution_status": "not_applicable",
            },
            family="NORM",
            statement_class=None,
            class_options=(),
            value_definition="a specification: a limit a requirement or criterion prescribes ('shall deflect less than 9 mm', 'at least 55 % humidity')",
            option_rank=10,
            quantity_rank=3,
            value_rank=2,
            definition=None,
            prompt_rank=None,
            allowed={"modality": frozenset({"conditional"})},
            asserts=True,
            temporal_scope="unknown",
            evidence_basis="stated",
            decisions=("R1",),
            checks=(),
            flag=None,
        ),
    )
}


def statement_roles():
    return tuple(name for name, r in ROLES.items() if "statements" in r.kinds)


def quantity_roles():
    ranked = sorted(
        (r for r in ROLES.values() if r.quantity_rank is not None), key=lambda r: r.quantity_rank
    )
    return tuple(r.name for r in ranked)


def statement_profiles():
    return {n: dict(r.statement_profile) for n, r in ROLES.items() if r.statement_profile}


def quantity_profiles():
    ranked = sorted(
        (r for r in ROLES.values() if r.quantity_profile), key=lambda r: r.quantity_rank
    )
    return {r.name: dict(r.quantity_profile) for r in ranked}


def statement_classes():
    return {n: r.statement_class for n, r in ROLES.items() if r.statement_class}


def class_flexible_roles():
    return {n: r.class_options for n, r in ROLES.items() if r.class_options}


def role_families():
    return {n: r.family for n, r in ROLES.items() if r.family}


def role_options():
    ranked = sorted(
        (r for r in ROLES.values() if r.option_rank is not None), key=lambda r: r.option_rank
    )
    return [r.name for r in ranked]


def allowed_modalities():
    """The modalities a role may state, keyed by the epistemic role of its profile."""
    table = {}
    for r in ROLES.values():
        profile = r.statement_profile or r.quantity_profile
        found = r.allowed.get("modality")
        if found:
            table.setdefault(profile["epistemic_role"], found)
    return table


def roles_allowing(axis, value, kind=set):
    """The roles whose ``allowed`` table admits ``value`` on ``axis``."""
    return kind(n for n, r in ROLES.items() if value in r.allowed.get(axis, ()))


def value_role_definitions():
    ranked = sorted((r for r in ROLES.values() if r.value_definition), key=lambda r: r.value_rank)
    return {r.name: r.value_definition for r in ranked}


# Legacy and current statement roles, each a profile over the dimensions, read from
# ``ROLES``. The ontology class each one maps to is in ``STATEMENT_CLASSES``.
STATEMENT_PROFILES = statement_profiles()
QUANTITY_PROFILES = quantity_profiles()

# A modality other than the profile's own changes what happened, so it changes the
# execution status: a proposed setpoint was planned, not executed; a prescribed,
# conditional or hypothetical value describes nothing that was done.
EXECUTION_FOR_MODALITY = {
    "proposed": "planned",
    "intended": "planned",
    "prescriptive": "not_applicable",
    "conditional": "not_applicable",
    "hypothetical": "not_applicable",
}

# The one table of modalities a role may state besides its own, read from ``Role.allowed``
# by the validator and checked against the request (``tests/test_scientific_facets.py``).
# "actual" is never stated: it means no modality. What was observed, concluded,
# interpreted or merely retained has no other modality.
ALLOWED_MODALITIES = allowed_modalities()

# The remaining axes of the facet dictionary (``Role.temporal_scope`` and
# ``Role.evidence_basis`` give each role's default). They are not yet on the wire.
TEMPORAL_SCOPES = ("current", "historical", "background", "future", "unknown")
EVIDENCE_BASES = ("measured", "computed", "simulated", "predicted", "stated", "retained")

# The studies a value or an entity may be marked with (``unknown`` is no mark).
ORIGIN_MARKS = ("current", "cited")
STUDY_SCOPE = {"current": "current", "cited": "historical", "unknown": "unknown"}
STUDY_ATTRIBUTION = {"current": "current_study", "cited": "cited_study", "unknown": "unknown"}


def profile(kind, role):
    profiles = QUANTITY_PROFILES if kind == "quantities" else STATEMENT_PROFILES
    return profiles.get(role)


def stated_modality(item):
    """The modality a proposal states; "actual" and an absent key both mean none."""
    modality = item.get("modality")
    return None if modality in {None, "actual"} else modality


PLAN_GOAL_ROLES = roles_allowing("statement_facets", "plan_goal", frozenset)


def plan_goal_facets_enabled():
    """R4 flag: plans and goals carry explicit facets and a canonical modality."""
    return os.getenv("SCIENCE_PLAN_GOAL_FACETS", "0") == "1"


def canonical_modality(kind, item):
    """The stated modality, none when it only repeats the role profile's own."""
    base = profile(kind, item.get("epistemic"))
    modality = stated_modality(item)
    return None if base and modality == base["modality"] else modality


def record_facets(record):
    """A record's facets without the verification state (a plan is never verified as run)."""
    found = facets_of(record)
    return None if found is None else {k: v for k, v in found.items() if k != "verification"}


def facets(kind, item):
    """The dimensions a statement or quantity proposal asserts.

    ``item`` is the proposal as the model or a deterministic path wrote it. A
    record without an explicit ``modality`` (every record written before facets
    existed) gets its profile's own, so old records read as they always did.
    """
    base = profile(kind, item.get("epistemic"))
    if base is None:
        return None
    result = dict(base)
    modality = stated_modality(item)
    if modality and modality != base["modality"]:
        result["modality"] = modality
        result["execution_status"] = EXECUTION_FOR_MODALITY.get(modality, base["execution_status"])
    if result["modality"] in {"proposed", "intended"}:
        result["temporal_scope"] = "future"
    else:
        result["temporal_scope"] = STUDY_SCOPE.get(item.get("study", "current"), "unknown")
    result["attribution"] = STUDY_ATTRIBUTION.get(item.get("study", "current"), "unknown")
    # Present only on records written with the background facets.
    if item.get("scope") == "background":
        result["temporal_scope"] = "background"
    if item.get("execution") == "ongoing":
        result["execution_status"] = "ongoing"
    if item.get("basis"):
        result["evidence_basis"] = item["basis"]
    return result


def facets_of(record):
    """A validated record's dimensions, with its subject and verification beside them."""
    item = record.get("proposal") or {}
    result = facets(record.get("kind"), item)
    if result is None:
        return None
    subjects = item.get("subjects")
    if subjects is None and item.get("subject"):
        subjects = [item["subject"]]
    return {
        **result,
        "subjects": list(subjects or []),
        "verification": record.get("proposal_state") or record.get("status"),
    }


def describes_execution(kind, item):
    """True only when the record asserts that something actually happened."""
    result = facets(kind, item)
    return bool(result) and result["execution_status"] == "executed"


def not_done_value(item):
    """A value with a known role that reports nothing done (a criterion value, or a
    proposed, prescribed, conditional or hypothetical one). A value whose role has
    no profile (a table attribute path) is left to its own contract."""
    result = facets("quantities", item)
    return bool(result) and result["modality"] != "actual"


def not_done_configuration(item):
    """A configuration statement that states something not done (proposed,
    intended, prescribed, conditional or hypothetical): kept for review, never
    published as an executed condition."""
    result = facets("statements", item)
    return (
        bool(result)
        and result["statement_type"] == "configuration"
        and (result["modality"] != "actual")
    )


# Printed cues for the modalities the clause reading does not decide. Deliberately
# general language, never source phrases: an intention is announced with goal or
# purpose words, a condition with a conditional clause, a hypothesis with hedging.
MODALITY_CUES = {
    "intended": r"\b(?:goals?|objectives?|aims?|purpose|intend\w*|seek(?:s|ing)?\s+to|in\s+order\s+to|"
    r"targets?|to\s+(?:demonstrate|develop|determine|evaluate|investigate|mature|obtain|"
    r"establish|assess|characterize|quantify|identify|understand|improve|enable))\b",
    "conditional": r"\b(?:if|unless|provided\s+that|in\s+case|when(?:ever)?|"
    r"should\s+\w+\s+(?:occur|fail)|contingency|otherwise)\b",
    "hypothetical": r"\b(?:hypothes\w*|may|might|could|would|possibl\w*|speculat\w*|"
    r"presum\w*|expected\s+to|predict\w*)\b",
}
# What kind of norm a criterion is, beside the clause that states it.
CRITERION_KIND_CUES = {
    "test_criterion": r"\b(?:pass\w*|fail\w*|accept\w*|reject\w*|criteri(?:on|a)|tests?)\b|"
    # A rule for how a test result is recorded.
    r"\b(?:is|are)\s+(?:recorded|reported|scored|counted|rated)\s+as\b",
    "design_criterion": r"\b(?:design\w*|requir\w*|criteri(?:on|a)|targets?|limits?|sized|"
    r"rated|margin|minimum|maximum|at\s+(?:least|most)|exceed|below|above|within|under|over|"
    r"(?:less|more|greater|lower|higher)\s+than)\b|[<>≤≥]",
}
UNCERTAIN = "MODALITY_READING_UNCERTAIN_REQUIRES_REVIEW"


def _reading(value, accepted, rejected, error, hold):
    """(errors, holds) for one clause reading."""
    if value == accepted:
        return [], []
    if value == rejected:
        return [error], []
    return [], [hold]


def _inside_purpose(text, value):
    """Whether the printed value follows a purpose cue in its sentence: what a done
    step sought ("the panel was sprayed, aiming for a 2 mm layer"), not the step itself."""
    at = text.find(value) if value else -1
    if os.getenv("SCIENCE_PURPOSE_READER", "1") == "1":
        # Inside the purpose clause itself, or after a goal noun.
        return at > 0 and (
            clause_cues.in_purpose(text, at) or bool(clause_cues.GOAL_WORD.search(text[:at]))
        )
    return at > 0 and bool(re.search(MODALITY_CUES["intended"], text[:at], re.IGNORECASE))


def modality_review(text, modality, value=None):
    """(errors, holds): the printed clause must carry the claimed modality; none
    needs no cue. A plan or a prescription is read from the governing clause; a
    clause that does not settle it is held. ``value`` is the printed value, when the
    claim is about one."""
    if not modality or modality in {"actual", "unknown"}:
        return [], []
    if modality == "proposed":
        return _reading(
            clause_cues.plan(text),
            "plan",
            "not_plan",
            "MODALITY_NOT_SUPPORTED_BY_SOURCE",
            UNCERTAIN,
        )
    if modality == "prescriptive":
        clause = clause_cues.governing_clause(text)
        if clause_cues.NORMATIVE.search(clause) or clause_cues.criterion(text) == "criterion":
            return [], []
        if clause_cues.execution(text) == "executed":
            return ["MODALITY_NOT_SUPPORTED_BY_SOURCE"], []
        return [], [UNCERTAIN]
    if modality not in MODALITY_CUES:
        return ["MODALITY_NOT_RECOGNIZED"], []
    if (
        modality == "intended"
        and clause_cues.execution(text) == "executed"
        and not _inside_purpose(text, value)
    ):
        # A purpose of a step that was done ("held at X to determine Y") is not an
        # intention for the value.
        return ["MODALITY_NOT_SUPPORTED_BY_SOURCE"], []
    if modality == "intended" and clause_cues.plan(text) == "plan":
        # "will" states a fact or an intent about the future (ISO/IEC/IEEE 29148; NASA
        # Systems Engineering Handbook): a planned clause supports an intention.
        return [], []
    printed = text if modality == "intended" else clause_cues.strip_frames(text)
    if modality == "hypothetical" and os.getenv("SCIENCE_MODAL_29148", "1") == "1":
        # "may" governing a use or an application is a permission, not a hedge.
        printed = clause_cues.PERMISSION.sub(" ", printed)
    if modality == "intended" and os.getenv("SCIENCE_PURPOSE_READER", "1") == "1":
        cued = clause_cues.GOAL_WORD.search(printed) or clause_cues.purpose_spans(printed)
    else:
        cued = re.search(MODALITY_CUES[modality], printed, re.IGNORECASE)
    if not cued:
        return ["MODALITY_NOT_SUPPORTED_BY_SOURCE"], []
    return [], []


def modality_errors(text, modality):
    return modality_review(text, modality)[0]


def facet_review(kind, item, sentence=None):
    """(errors, holds): the facets a statement or quantity claims must be what its
    source prints.

    ``sentence`` is the printed sentence (or clause) that carries the value or
    statement; cues are read there only, never from a neighbouring sentence of the
    support. A role's own modality needs no extra cue (its existing checks apply).
    Another modality must be one the role allows and must be printed. A plan, a
    goal and a criterion are each read from the governing clause by
    ``clause_cues``: a reading that contradicts the claim is an error, one the
    clause does not settle is a hold.
    """
    text = sentence if sentence is not None else item.get("text") or ""
    role = item.get("epistemic")
    base = profile(kind, role)
    if base is None:
        return [], []
    errors, holds = [], []
    modality = stated_modality(item)
    if modality and modality != base["modality"]:
        if modality not in ALLOWED_MODALITIES.get(base["epistemic_role"], ()):
            errors.append("MODALITY_CONTRADICTS_ROLE")
        elif text:
            found = modality_review(text, modality, item.get("expression"))
            errors += found[0]
            holds += found[1]
    if not text:
        if sentence == "" and (
            (modality and modality != base["modality"])
            or base["statement_type"] in {"plan", "goal", "criterion_value"}
        ):
            # The value's own printed position was not found: no clause supports
            # a reading other than the role's default, and none is borrowed.
            errors.append("VALUE_NOT_LOCATED_FOR_FACET_READING")
        return errors, holds
    found = ([], [])
    if base["statement_type"] == "plan":
        found = _reading(
            clause_cues.plan(text),
            "plan",
            "not_plan",
            "PLAN_NOT_EXPLICIT_IN_SOURCE",
            "PLAN_READING_UNCERTAIN_REQUIRES_REVIEW",
        )
    elif base["statement_type"] == "goal":
        found = _reading(
            clause_cues.goal(text),
            "goal",
            "not_goal",
            "GOAL_NOT_EXPLICIT_IN_SOURCE",
            "GOAL_READING_UNCERTAIN_REQUIRES_REVIEW",
        )
    elif base["statement_type"] in {"test_criterion", "design_criterion", "criterion_value"}:
        found = _reading(
            clause_cues.criterion(text),
            "criterion",
            "not_criterion",
            "CRITERION_NOT_EXPLICIT_IN_SOURCE",
            "CRITERION_READING_UNCERTAIN_REQUIRES_REVIEW",
        )
        kind_cue = CRITERION_KIND_CUES.get(base["statement_type"])
        if (
            kind_cue
            and base["statement_type"] == "test_criterion"
            and os.getenv("SCIENCE_RECORDING_RULE", "1") == "1"
        ):
            # The recording alternative is the one shared frame (clause_cues).
            kind_cue = (
                None
                if clause_cues.recording_rule(text)
                else r"\b(?:pass\w*|fail\w*|accept\w*|reject\w*|criteri(?:on|a)|tests?)\b"
            )
        if not found[0] and kind_cue and not re.search(kind_cue, text, re.IGNORECASE):
            found = (["CRITERION_NOT_EXPLICIT_IN_SOURCE"], [])
    errors += found[0]
    holds += found[1]
    return errors, holds


def facet_errors(kind, item, sentence=None):
    """The errors of ``facet_review`` (what the source contradicts)."""
    return facet_review(kind, item, sentence)[0]


BACKGROUND_FACET_FIELDS = ("scope", "execution")
# Roles a background statement or an ongoing activity may take: the authors report
# them; neither is this study's observation, configuration or plan.
BACKGROUND_ROLES = roles_allowing("scope", "background", set)
ONGOING_ROLES = roles_allowing("execution", "ongoing", set)


def ongoing_activity_roles_enabled():
    """V2 (Track B): an ongoing activity is stated by an activity role, not a conclusion."""
    return os.getenv("SCIENCE_ONGOING_ACTIVITY_ROLES", "0") == "1"


def ongoing_roles():
    """The roles that may state ``execution: ongoing``: the activity roles under V2, else the
    legacy set."""
    if ongoing_activity_roles_enabled():
        return roles_allowing("execution_v2", "ongoing", set)
    return ONGOING_ROLES


def value_origin_mark_enabled():
    """A2a flag: the model marks the study that produced each quantity (``Quantity.study``)."""
    return os.getenv("SCIENCE_VALUE_ORIGIN_MARK", "0") == "1"


def background_facets_enabled():
    return os.getenv("SCIENCE_BACKGROUND_FACETS", "0") == "1"


# Data provenance (SCIENCE_STRUCTURED_PROVENANCE, off by default until measured): a statement
# that names where the study's data come from is its own complete record, not retained
# documentary context. Without the flag the role is not part of the contract.
PROVENANCE_ROLE = "data_provenance"

# The role that records what the document is or points to (one name for the consumers outside this module).
DOCUMENTARY_ROLE = "documentary_context"


def structured_provenance_enabled():
    return os.getenv("SCIENCE_STRUCTURED_PROVENANCE", "0") == "1"


STATEMENT_CLASSES = statement_classes()
# Roles whose class the model chooses within an explicit set (and its approved
# subclasses); every other role must use (a subclass of) its own class.
CLASS_FLEXIBLE_ROLES = class_flexible_roles()


# Why a proposal was held for its role, in plain words (the role check).
ROLE_CHECK_WORDS = (
    # Most specific first: each reason takes the first cue it contains.
    ("CHANGING_OBSERVATION", "a change it reports reads as observed, not as a set-up"),
    ("CONFIGURATION_ROLE", "the printed clause does not state how the tests were set up"),
    (
        "MODALITY",
        (
            "the printed clause does not support its modality (actual, proposed, intended, "
            "conditional, hypothetical, prescriptive)"
        ),
    ),
    ("CRITERION", "the printed clause does not state it as a criterion"),
    ("PLAN", "the printed clause does not state it as a plan"),
    ("GUIDANCE", "the printed clause does not state it as guidance or a permission"),
    ("NORMATIVE", "the printed clause does not state it as a requirement"),
    ("OPEN_QUESTION", "the printed clause does not say it is not known"),
    ("DERIVED", "it is derived, not observed or measured"),
    ("INFERRED", "it is an inference, not a direct observation"),
    ("MEASUREMENT", "it is not a measurement"),
    ("OBSERVATION", "it is not a direct observation"),
    ("ROLE", "its role is not established by the printed clause"),
)

# Roles of a value or statement, defined from open ontologies and from the modal-verb
# conventions of requirements writing, never from a source: the Information Artifact
# Ontology (IAO) and OBI for the kinds of data, ISO/IEC/IEEE 29148 and the NASA
# Systems Engineering Handbook for "shall", "should", "may" and "will". Examples are
# invented.
ROLE_VOCABULARY = {
    "sources": [
        (
            "IAO / OBI: measurement datum, setting datum, specification, plan "
            "specification, objective specification"
        ),
        (
            "ISO/IEC/IEEE 29148 and the NASA Systems Engineering Handbook: 'shall' states a "
            "requirement, 'should' a goal or recommendation, 'may' a permission, 'will' a "
            "statement of fact or of intent, never a requirement"
        ),
    ],
    "value_roles": value_role_definitions(),
    "modal_verbs": {
        "shall / must": "a requirement: normative_requirement, or a criterion if it states "
        "a pass or fail condition",
        "should": "a goal or recommendation: guidance",
        "may / can be used / is permitted": "a permission: guidance, never an executed step",
        "will / is planned": "a fact or an intent about the future: planned_activity or a "
        "value with modality proposed; never a requirement, never done",
    },
    "scope": "a value printed for an earlier program, a cited study or a historical "
    "environment is cited, not this study's (study 'cited').",
}


def request_role_vocabulary():
    """The role vocabulary the request sends; with SCIENCE_MODAL_29148 its modal verbs
    come from the one dictionary the validator reads (clause_cues.NORMATIVE_MODALS)."""
    if os.getenv("SCIENCE_MODAL_29148", "1") != "1":
        return ROLE_VOCABULARY
    from nasa_fire_ai.ingestion.clause_cues import NORMATIVE_MODALS

    return {**ROLE_VOCABULARY, "modal_verbs": dict(NORMATIVE_MODALS)}


# Value roles for environments of earlier work and for assessment targets
# (SCIENCE_ENVIRONMENT_SUBJECTS); read with ROLE_VOCABULARY.
ENVIRONMENT_VALUE_ROLES = [
    (
        "A value printed for an earlier program, mission or cited work keeps the role "
        "experimental_configuration with study cited and the cited environment as its "
        "subject; it is never this study's measurement."
    ),
    (
        "A target condition that an assessment or test must reach is "
        "experimental_configuration with modality intended and the target environment "
        "as its subject; criterion_value is a limit a result must meet to pass."
    ),
    (
        "A bound printed before a value ('at least 25', 'up to 30') stays in its "
        "expression as printed, never dropped; the quantity name is the printed "
        "variable, never the unit."
    ),
]
# SCIENCE_ENVIRONMENT_SUBJECTS_V2: the same roles without any instruction to give the
# value an environment as subject; validation alone binds a value to an environment.
ENVIRONMENT_VALUE_ROLES_V2 = [
    (
        "A value printed for an earlier program, mission or cited work has the role "
        "experimental_configuration with study cited; it is never this study's "
        "measurement."
    ),
    (
        "A target condition that an assessment or test must reach has the role "
        "experimental_configuration with modality intended; criterion_value is a limit "
        "a result must meet to pass."
    ),
    (
        "A value belongs to an environment identity only when the value is printed "
        "inside that environment's own label; otherwise its subject is what its clause "
        "names."
    ),
    ENVIRONMENT_VALUE_ROLES[2],
]
ROLE_OPTIONS = role_options()
ROLE_MODALITIES = list(MODALITIES)
ROLE_STUDIES = list(ORIGIN_MARKS)


def role_bullets(kind):
    """The prompt bullets that define the roles of ``kind``, in prompt order."""
    ranked = sorted(
        (r for r in ROLES.values() if kind in r.kinds and r.prompt_rank is not None),
        key=lambda r: r.prompt_rank,
    )
    v2 = role_definitions_v2_enabled()
    return "".join(f"- {r.name}: {(v2 and r.definition_v2) or r.definition}\n" for r in ranked)


def role_enabled(role):
    """A role offered only with a flag is part of the contract only while the flag is on."""
    flag = ROLES[role].flag
    return flag is None or os.getenv(flag, "0") == "1"


def role_definitions_v2_enabled():
    """A10 (Track B): revised role definitions and the ``basis`` wire field."""
    return os.getenv("SCIENCE_ROLE_DEFINITIONS_V2", "0") == "1"


def allowed_bases(role):
    """The evidence bases a record of ``role`` may state: its own and those its table admits."""
    found = ROLES[role]
    return {found.evidence_basis} | set(found.allowed.get("evidence_basis", ()))

# Shared consultation profile; existing role, not a new semantic classification.
REPORTED_QUANTITY_ROLE = "reported_quantity"
