"""The role dictionary: every table that names roles is a view of ``scientific_facets.ROLES``.

The frozen copies below are the values of the separate tables before they became views;
a view must stay equal to its copy, in the same order where order reaches a request.
"""

from nasa_fire_ai.ingestion import scientific_facets as sf

FROZEN_STATEMENT_PROFILES = {
    "measured_observation": {
        "statement_type": "observation",
        "epistemic_role": "observed",
        "modality": "actual",
        "execution_status": "executed",
    },
    "author_reported_conclusion": {
        "statement_type": "conclusion",
        "epistemic_role": "concluded",
        "modality": "actual",
        "execution_status": "executed",
    },
    "tentative_interpretation": {
        "statement_type": "interpretation",
        "epistemic_role": "interpreted",
        "modality": "actual",
        "execution_status": "executed",
    },
    "hypothesis": {
        "statement_type": "hypothesis",
        "epistemic_role": "hypothesized",
        "modality": "hypothetical",
        "execution_status": "not_applicable",
    },
    "open_question": {
        "statement_type": "question",
        "epistemic_role": "questioned",
        "modality": "hypothetical",
        "execution_status": "not_applicable",
    },
    "normative_requirement": {
        "statement_type": "requirement",
        "epistemic_role": "prescribed",
        "modality": "prescriptive",
        "execution_status": "not_applicable",
    },
    "guidance": {
        "statement_type": "guidance",
        "epistemic_role": "prescribed",
        "modality": "prescriptive",
        "execution_status": "not_applicable",
    },
    "experimental_configuration": {
        "statement_type": "configuration",
        "epistemic_role": "reported",
        "modality": "actual",
        "execution_status": "executed",
    },
    "derived_quantity": {
        "statement_type": "derivation",
        "epistemic_role": "derived",
        "modality": "actual",
        "execution_status": "not_applicable",
    },
    "data_provenance": {
        "statement_type": "provenance",
        "epistemic_role": "reported",
        "modality": "actual",
        "execution_status": "not_applicable",
    },
    "documentary_context": {
        "statement_type": "documentary",
        "epistemic_role": "retained",
        "modality": "unknown",
        "execution_status": "unknown",
    },
    "planned_activity": {
        "statement_type": "plan",
        "epistemic_role": "intended",
        "modality": "proposed",
        "execution_status": "planned",
    },
    "stated_goal": {
        "statement_type": "goal",
        "epistemic_role": "intended",
        "modality": "intended",
        "execution_status": "not_applicable",
    },
    "design_criterion": {
        "statement_type": "design_criterion",
        "epistemic_role": "prescribed",
        "modality": "prescriptive",
        "execution_status": "not_applicable",
    },
    "test_criterion": {
        "statement_type": "test_criterion",
        "epistemic_role": "prescribed",
        "modality": "prescriptive",
        "execution_status": "not_applicable",
    },
}

FROZEN_QUANTITY_PROFILES = {
    "reported_quantity": {
        "statement_type": "measurement",
        "epistemic_role": "observed",
        "modality": "actual",
        "execution_status": "executed",
    },
    "derived_quantity": {
        "statement_type": "derivation",
        "epistemic_role": "derived",
        "modality": "actual",
        "execution_status": "not_applicable",
    },
    "experimental_configuration": {
        "statement_type": "setpoint",
        "epistemic_role": "reported",
        "modality": "actual",
        "execution_status": "executed",
    },
    "criterion_value": {
        "statement_type": "criterion_value",
        "epistemic_role": "prescribed",
        "modality": "prescriptive",
        "execution_status": "not_applicable",
    },
}

FROZEN_STATEMENT_CLASSES = {
    "measured_observation": "ReportedObservation",
    "author_reported_conclusion": "NASAConclusion",
    "tentative_interpretation": "NASAConclusion",
    "hypothesis": "NASAConclusion",
    "open_question": "OpenQuestion",
    "normative_requirement": "Requirement",
    "guidance": "Guidance",
    "experimental_configuration": "ExperimentalCondition",
    "derived_quantity": "Measurement",
    "documentary_context": "Publication",
    "design_criterion": "DesignCriterion",
    "test_criterion": "TestCriterion",
    "planned_activity": "PlannedActivity",
    "stated_goal": "ResearchGoal",
    "data_provenance": "Publication",
}

FROZEN_CLASS_FLEXIBLE_ROLES = {
    "experimental_configuration": ("ExperimentalCondition", "Intervention"),
    "derived_quantity": ("Measurement",),
    "documentary_context": ("Publication", "Document"),
    "data_provenance": ("Publication", "Document"),
}

FROZEN_ROLE_FAMILY = {
    "measured_observation": "OBSERVATION",
    "derived_quantity": "DERIVATION",
    "experimental_configuration": "CONFIGURATION",
    "author_reported_conclusion": "INTERPRETATION",
    "tentative_interpretation": "INTERPRETATION",
    "hypothesis": "INTERPRETATION",
    "normative_requirement": "NORM",
    "guidance": "NORM",
    "open_question": "QUESTION",
    "documentary_context": "DOCUMENTARY",
    "reported_quantity": "OBSERVATION",
    "design_criterion": "NORM",
    "test_criterion": "NORM",
    "criterion_value": "NORM",
    "planned_activity": "INTENTION",
    "stated_goal": "INTENTION",
}

FROZEN_ROLE_OPTIONS = [
    "measured_observation",
    "experimental_configuration",
    "test_criterion",
    "design_criterion",
    "normative_requirement",
    "guidance",
    "planned_activity",
    "stated_goal",
    "derived_quantity",
    "reported_quantity",
    "criterion_value",
    "documentary_context",
    "author_reported_conclusion",
    "tentative_interpretation",
    "hypothesis",
    "open_question",
]

FROZEN_VALUE_ROLES = {
    "reported_quantity": "a measurement datum: what this study measured ('the panel bent 4 mm')",
    "experimental_configuration": "a setting: a value the study set for its tests ('held at 40 % "
    "humidity'); planned or proposed settings keep this role with "
    "modality proposed or intended",
    "criterion_value": "a specification: a limit a requirement or criterion prescribes ('shall "
    "deflect less than 9 mm', 'at least 55 % humidity')",
    "derived_quantity": "a value computed from data: a fit, difference, margin or ratio",
}


def test_profiles_are_views_of_the_roles():
    assert sf.statement_profiles() == FROZEN_STATEMENT_PROFILES
    assert sf.quantity_profiles() == FROZEN_QUANTITY_PROFILES
    assert list(sf.quantity_profiles()) == list(FROZEN_QUANTITY_PROFILES)


def test_classes_and_families_are_views_of_the_roles():
    assert sf.statement_classes() == FROZEN_STATEMENT_CLASSES
    assert sf.class_flexible_roles() == FROZEN_CLASS_FLEXIBLE_ROLES
    assert sf.role_families() == FROZEN_ROLE_FAMILY


def test_options_and_value_definitions_are_views_of_the_roles():
    assert sf.role_options() == FROZEN_ROLE_OPTIONS
    assert list(sf.value_role_definitions().items()) == list(FROZEN_VALUE_ROLES.items())


def test_every_role_has_a_profile_for_each_of_its_kinds():
    for role in sf.ROLES.values():
        assert ("statements" in role.kinds) == (role.statement_profile is not None)
        assert ("quantities" in role.kinds) == (role.quantity_profile is not None)


def test_the_wire_order_of_the_roles_is_kept():
    assert sf.statement_roles()[-1] == "data_provenance"
    assert sf.quantity_roles() == tuple(FROZEN_QUANTITY_PROFILES)


def test_the_derived_constants_equal_the_frozen_tables():
    assert sf.STATEMENT_CLASSES == FROZEN_STATEMENT_CLASSES
    assert sf.CLASS_FLEXIBLE_ROLES == FROZEN_CLASS_FLEXIBLE_ROLES
    assert sf.ROLE_OPTIONS == FROZEN_ROLE_OPTIONS
    assert list(sf.ROLE_VOCABULARY["value_roles"].items()) == list(FROZEN_VALUE_ROLES.items())
    assert sf.ROLE_MODALITIES == list(sf.MODALITIES)
    assert sf.ROLE_STUDIES == ["current", "cited"]


def test_the_schema_enums_are_the_roles_in_wire_order():
    from nasa_fire_ai.ingestion.extraction_schema import Output

    defs = Output.model_json_schema()["$defs"]
    assert defs["Statement"]["properties"]["epistemic"]["enum"] == list(sf.statement_roles())
    assert defs["Quantity"]["properties"]["epistemic"]["enum"] == list(FROZEN_QUANTITY_PROFILES)
    assert list(sf.statement_roles()[:3]) == [
        "measured_observation",
        "author_reported_conclusion",
        "tentative_interpretation",
    ]


def test_every_offered_statement_role_is_defined_in_the_prompt(monkeypatch):
    from nasa_fire_ai.ingestion.extraction_request import STAGE_INSTRUCTIONS, stage_schema

    prompt = STAGE_INSTRUCTIONS["propositions"]
    assert "<<role_bullets>>" not in prompt
    offered = stage_schema("propositions")["$defs"]["Statement"]["properties"]["epistemic"]["enum"]
    for role in offered:
        assert f"- {role}: " in prompt
    assert "data_provenance" not in offered
    monkeypatch.setenv("SCIENCE_STRUCTURED_PROVENANCE", "1")
    on = stage_schema("propositions")["$defs"]["Statement"]["properties"]["epistemic"]["enum"]
    assert on == list(sf.statement_roles())


# Quoted role names outside scientific_facets, per file, at the time the dictionary became
# the one table. The numbers may only shrink: a new role table must be a view of ROLES.
ROLE_LITERAL_ALLOWANCE = {
    "src/nasa_fire_ai/ingestion/document_extraction.py": 12,
    "src/nasa_fire_ai/ingestion/extraction_request.py": 3,
    "src/nasa_fire_ai/ingestion/extraction_validation.py": 26,
    "src/nasa_fire_ai/ingestion/narrative_candidates.py": 3,
    "src/nasa_fire_ai/ingestion/proposal_states.py": 1,
    "src/nasa_fire_ai/ingestion/quantity_naming.py": 2,
    "src/nasa_fire_ai/ingestion/quantity_validation.py": 23,
    "src/nasa_fire_ai/ingestion/scientific_scope.py": 1,
    "src/nasa_fire_ai/ingestion/statement_validation.py": 39,
    "src/nasa_fire_ai/ingestion/structural_candidates.py": 7,
    "src/nasa_fire_ai/ingestion/subject_recognition.py": 6,
    "src/nasa_fire_ai/models/__init__.py": 21,
    "src/nasa_fire_ai/query/native.py": 1,
    "src/nasa_fire_ai/query/offline_parser.py": 3,
    "src/nasa_fire_ai/query/phase3.py": 7,
    "src/nasa_fire_ai/services/curation.py": 22,
    "src/nasa_fire_ai/services/grounding.py": 7,
    "src/nasa_fire_ai/services/investigation.py": 1,
    "src/nasa_fire_ai/services/native.py": 4,
    "src/nasa_fire_ai/services/pipeline.py": 4,
    "src/nasa_fire_ai/services/scientific_synthesis.py": 13,
}


def test_no_module_adds_a_role_literal():
    import re
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    pattern = re.compile("[\"'](" + "|".join(sf.ROLES) + ")[\"']")
    for path in sorted((root / "src").rglob("*.py")):
        if path.name == "scientific_facets.py":
            continue
        found = len(pattern.findall(path.read_text(encoding="utf-8")))
        allowed = ROLE_LITERAL_ALLOWANCE.get(path.relative_to(root).as_posix(), 0)
        assert found <= allowed, f"{path.name}: {found} role literals, {allowed} allowed"


def test_every_check_a_role_names_exists():
    from nasa_fire_ai.ingestion.statement_integrity import ROLE_CHECKS

    named = {c for r in sf.ROLES.values() for c in r.checks}
    assert named == set(ROLE_CHECKS)
    assert "multiple_bullets" not in sf.ROLES["documentary_context"].checks
    assert "multiple_bullets" in sf.ROLES["measured_observation"].checks


def test_the_allowed_tables_are_views_of_the_roles():
    assert sf.ALLOWED_MODALITIES == {
        "reported": frozenset({"proposed", "intended", "conditional", "hypothetical"}),
        "derived": frozenset({"conditional", "hypothetical"}),
        "intended": frozenset({"proposed", "intended", "conditional"}),
        "prescribed": frozenset({"conditional"}),
        "hypothesized": frozenset({"conditional"}),
        "questioned": frozenset({"conditional"}),
    }
    assert sf.BACKGROUND_ROLES == {"author_reported_conclusion", "tentative_interpretation"}
    assert sf.ONGOING_ROLES == {"author_reported_conclusion"}
    assert sf.PLAN_GOAL_ROLES == frozenset({"planned_activity", "stated_goal"})


def test_simulated_and_predicted_are_never_stated_by_a_measured_role():
    for role in ("measured_observation", "reported_quantity", "experimental_configuration"):
        assert not sf.ROLES[role].allowed.get("evidence_basis")
    for role in ("derived_quantity", "author_reported_conclusion", "tentative_interpretation"):
        assert sf.ROLES[role].allowed["evidence_basis"] == {"simulated", "predicted"}
    assert sf.ROLES["measured_observation"].evidence_basis == "measured"
    assert sf.ROLES["derived_quantity"].evidence_basis == "computed"
    assert sf.ROLES["documentary_context"].evidence_basis == "retained"
    assert not sf.ROLES["documentary_context"].asserts
    assert all(r.asserts for n, r in sf.ROLES.items() if n != "documentary_context")


def test_every_role_axis_value_is_in_its_axis():
    for role in sf.ROLES.values():
        assert role.temporal_scope in sf.TEMPORAL_SCOPES
        assert role.evidence_basis in sf.EVIDENCE_BASES
        assert role.decisions and role.decisions[0] == "R1"
        for value in role.allowed.get("modality", ()):
            assert value in sf.MODALITIES
        for value in role.allowed.get("evidence_basis", ()):
            assert value in sf.EVIDENCE_BASES


def test_the_dictionary_end_to_end_for_every_role(monkeypatch):
    """H7: each role is offered, accepted, profiled, checked and classed consistently."""
    from pathlib import Path

    from nasa_fire_ai.ingestion.extraction_request import stage_schema
    from nasa_fire_ai.ingestion.extraction_schema import Quantity, Statement
    from nasa_fire_ai.ingestion.semantic import load_semantic_registry
    from nasa_fire_ai.ingestion.statement_integrity import ROLE_CHECKS

    root = Path(__file__).resolve().parent.parent
    registry = load_semantic_registry(root / "domain" / "semantic_registry.yaml")
    unregistered = {"PlannedActivity", "ResearchGoal"}
    families = {
        "OBSERVATION",
        "DERIVATION",
        "CONFIGURATION",
        "INTERPRETATION",
        "NORM",
        "QUESTION",
        "DOCUMENTARY",
        "INTENTION",
    }
    monkeypatch.setenv("SCIENCE_STRUCTURED_PROVENANCE", "1")
    offered = stage_schema("propositions")["$defs"]["Statement"]["properties"]["epistemic"]["enum"]
    span = [{"evidence_id": "E1", "quote": "x"}]
    for name, role in sf.ROLES.items():
        if "statements" in role.kinds:
            assert name in offered
            Statement.model_validate(
                {"text": "t", "class_id": "C", "epistemic": name, "support": span}
            )
            found = sf.facets("statements", {"epistemic": name})
            assert role.statement_profile.items() <= found.items()
        if "quantities" in role.kinds:
            Quantity.model_validate(
                {
                    "subject": "K",
                    "label": "l",
                    "expression": "1",
                    "epistemic": name,
                    "support": span,
                }
            )
            found = sf.facets("quantities", {"epistemic": name})
            assert role.quantity_profile.items() <= found.items()
        assert set(role.checks) <= set(ROLE_CHECKS)
        if role.statement_class:
            known = registry.information_classes | registry.target_classes
            assert role.statement_class in known | unregistered, name
        if name != sf.PROVENANCE_ROLE:
            assert role.family in families, name
    monkeypatch.delenv("SCIENCE_STRUCTURED_PROVENANCE")
    assert (
        sf.PROVENANCE_ROLE
        not in stage_schema("propositions")["$defs"]["Statement"]["properties"]["epistemic"]["enum"]
    )
    cues = {cue for cue, _ in sf.ROLE_CHECK_WORDS}
    assert {"OPEN_QUESTION", "GUIDANCE", "NORMATIVE", "ROLE"} <= cues


def test_every_hold_a_role_names_exists():
    from nasa_fire_ai.ingestion.statement_integrity import HOLD_CHECKS

    assert {h for r in sf.ROLES.values() for h in r.holds} <= set(HOLD_CHECKS)
