"""Review of c099faa, group 2: every facet check reads the governing clause through
``clause_cues``; a reading the clause does not settle is held, never decided by a
phrase elsewhere in the sentence. Synthetic text; each test failed before the change.
"""

import pytest
from test_document_extraction import entity, submitted, validate
from test_document_extraction import service as _service
from test_facet_review_fixes import statement_record
from test_scientific_facets import only, quantity

from nasa_fire_ai.ingestion.document_extraction import Output
from nasa_fire_ai.ingestion.scientific_facets import facet_review

service = _service
STUDY = "Synthetic study"


@pytest.mark.parametrize(
    "text",
    [
        # Done, with a planning aside: not a plan.
        "Run A1 was burned at 34 % oxygen as planned.",
        # A purpose that mentions the future is not a plan of its own.
        "The chamber was purged so that future runs would start clean.",
    ],
)
def test_a_done_step_is_never_read_as_a_plan(service, text):
    record = statement_record(service, text, "planned_activity", "PlannedActivity")
    assert record["status"] == "REJECTED"
    assert any("PLAN_NOT_EXPLICIT_IN_SOURCE" in r for r in record["reasons"])


def test_a_plan_the_clause_cannot_settle_is_held_for_review():
    errors, holds = facet_review(
        "statements",
        {"text": "Oxygen for the next panels: 34 %.", "epistemic": "planned_activity"},
    )
    assert errors == [] and holds == ["PLAN_READING_UNCERTAIN_REQUIRES_REVIEW"]


@pytest.mark.parametrize(
    "text",
    [
        # A measured extreme, not a limit.
        "Panel C3 burned no more than 7 cm in the test.",
        "The wall temperature was no greater than 40 C.",
        # A result reported about a criterion.
        "The acceptance criteria are met by all panels.",
    ],
)
def test_a_measured_extreme_or_a_result_is_not_a_criterion(service, text):
    record = statement_record(service, text, "test_criterion", "TestCriterion")
    assert record["status"] == "REJECTED"
    assert any("CRITERION_NOT_EXPLICIT_IN_SOURCE" in r for r in record["reasons"])


@pytest.mark.parametrize(
    "text",
    [
        # Nominal criterion frames without a modal verb.
        "Acceptance criterion: char length below 9 cm.",
        "The pass criterion was a burn length under 15 cm.",
        # A discourse frame does not hide the norm.
        "It should be noted that each panel must pass the self-extinguishment test.",
    ],
)
def test_a_criterion_frame_is_a_criterion(service, text):
    record = statement_record(service, text, "test_criterion", "TestCriterion")
    assert not any("CRITERION_NOT_EXPLICIT_IN_SOURCE" in r for r in record["reasons"])


def test_a_goal_word_without_a_goal_frame_is_held():
    errors, holds = facet_review(
        "statements", {"text": "The aim of the run was met.", "epistemic": "stated_goal"}
    )
    assert errors == [] and holds == ["GOAL_READING_UNCERTAIN_REQUIRES_REVIEW"]


def test_a_stated_goal_frame_is_a_goal():
    errors, holds = facet_review(
        "statements",
        {"text": "The goal was to measure the flame length.", "epistemic": "stated_goal"},
    )
    assert errors == [] and holds == []


def test_a_proposed_value_needs_a_clause_that_plans_it(service):
    # "as planned" is a frame, not this value's modality: the value was done.
    sentence = "Run A1 was burned at 34 % oxygen as planned."
    p = submitted(service, f"{STUDY}\nII. Methods\n{sentence}\n")
    o = Output().model_dump()
    o["entities"] = [entity(p, "inv", STUDY, "Investigation", STUDY)]
    o["quantities"] = [
        quantity(p, sentence, "inv", "oxygen", "34", "%", "experimental_configuration", "proposed")
    ]
    record = only(validate(service, p, o)["records"], "quantities")
    assert record["status"] == "REJECTED"
    assert any("MODALITY_NOT_SUPPORTED_BY_SOURCE" in r for r in record["reasons"])


def test_a_proposed_value_printed_as_planned_is_accepted():
    errors, holds = facet_review(
        "quantities",
        {"epistemic": "experimental_configuration", "modality": "proposed"},
        sentence="The next series will hold oxygen at 34 %.",
    )
    assert errors == [] and holds == []


CONFIG = {"epistemic": "experimental_configuration"}


def test_a_purpose_infinitive_does_not_make_a_done_value_intended():
    errors, _ = facet_review(
        "quantities",
        {**CONFIG, "modality": "intended"},
        sentence="The chamber was held at 34 % to determine the extinction limit.",
    )
    assert errors == ["MODALITY_NOT_SUPPORTED_BY_SOURCE"]


def test_an_intended_value_the_clause_states_is_accepted():
    errors, holds = facet_review(
        "quantities",
        {**CONFIG, "modality": "intended"},
        sentence="The goal is to hold oxygen at 34 % in every panel.",
    )
    assert errors == [] and holds == []


@pytest.mark.parametrize(
    "item",
    [
        {**CONFIG, "modality": "proposed"},
        {"epistemic": "criterion_value"},
    ],
)
def test_a_value_that_cannot_be_located_cannot_claim_a_non_default_reading(item):
    # The value's own printed position was not found: no clause can support the
    # claimed modality or role, and none is borrowed from another sentence.
    errors, _ = facet_review("quantities", item, sentence="")
    assert "VALUE_NOT_LOCATED_FOR_FACET_READING" in errors


def test_a_default_value_that_cannot_be_located_keeps_its_other_checks():
    assert facet_review("quantities", CONFIG, sentence="") == ([], [])
