"""The governing clause decides: synthetic sentences, metamorphic pairs."""

import pytest

from nasa_fire_ai.ingestion.clause_cues import criterion, execution, goal, plan


@pytest.mark.parametrize(
    "sentence",
    [
        "Run A1 was burned at 34 % as planned.",
        "Run A1 was burned at 34 %, the atmosphere proposed for future exploration vehicles.",
        "Run A1 was burned at 34 %; Run A2 will be burned at 30 %.",
        "Run A1 was mounted upright above the igniter, as planned.",
        "It should be noted that Run A1 was burned at 34 %.",
        "The chamber was held at 34 % to determine the extinction limit.",
    ],
)
def test_a_done_value_stays_done_whatever_another_clause_says(sentence):
    # The value printed first ("34 %" of Run A1) is governed by a past clause; a
    # sentence without a value is read from its main clause.
    offset = sentence.index("34") if "34" in sentence else None
    assert execution(sentence, offset) == "executed"


@pytest.mark.parametrize(
    "sentence",
    [
        "Panel C3 will be burned again at 34 % oxygen.",
        "Future tests will be held at a chamber pressure of 50 kPa.",
        "If ignition fails, the panels will be burned at 34 % oxygen.",
        "The pressure for Panel C3 must not exceed 50 kPa.",
        "The next series is scheduled to run at 34 % oxygen.",
        "The panels are going to be burned at 34 % oxygen.",
        "The run would be repeated at 34 % if the first failed.",
    ],
)
def test_a_value_printed_as_not_done_is_not_done(sentence):
    assert execution(sentence, sentence.index(next(c for c in sentence if c.isdigit()))) == (
        "not_done"
    )


@pytest.mark.parametrize(
    ("sentence", "reading"),
    [
        # A conditional procedure in the past was carried out where its condition held.
        ("If the coupon charred, the run was repeated at 30 % oxygen.", "executed"),
        # A standing rule in the present does not say whether anything was done.
        ("If the wall rises above 40 C, then the run is recorded as void.", "uncertain"),
        # Metamorphic: the same rule in the future is a plan.
        ("If the coupon chars, the run will be repeated at 30 % oxygen.", "not_done"),
    ],
)
def test_a_condition_is_read_from_the_clause_it_conditions(sentence, reading):
    assert execution(sentence) == reading


def test_the_other_clause_of_a_compound_sentence_is_read_on_its_own():
    sentence = "Run A1 was burned at 34 %; Run A2 will be burned at 30 %."
    assert execution(sentence, sentence.index("30")) == "not_done"


@pytest.mark.parametrize(
    "sentence",
    [
        "Each panel shall self-extinguish within 10 s.",
        "The pressure for Panel C3 must not exceed 50 kPa.",
        "Acceptance criterion: char length below 9 cm.",
        "The pass criterion was a burn length under 15 cm.",
        "The requirement is that the wall stays below 40 C.",
        "The wall temperature limit is 40 C.",
        "The maximum allowable wall temperature is 40 C.",
        "A burn length greater than 15 cm constitutes a failure.",
        "Panels that do not self-extinguish within 10 s fail the test.",
        "A panel that does not meet the acceptance criterion shall be rejected.",
        "A panel passes when its char length stays below 9 cm.",
    ],
)
def test_stated_criteria_are_criteria(sentence):
    assert criterion(sentence) == "criterion"


@pytest.mark.parametrize(
    "sentence",
    [
        "Run A1 failed the drop test.",
        "Panel C3 passed the impact test.",
        "Panel C3 was not tested against any acceptance criterion.",
        "The maximum char length in Run A1 was 7 cm.",
        "The coupon burned at least 9 cm.",
        "Panel C3 burned no more than 7 cm in the test.",
        "The wall temperature was no greater than 40 C.",
        "The flame was limited to within 3 cm of the edge.",
        "Panel C3 was tested without a pass/fail criterion.",
        "No pass-fail criterion was defined for the series.",
        "The acceptance criterion is not stated in the report.",
        "Test criteria are not defined for this material.",
        "The pass/fail criterion is unknown for these panels.",
        "It should be noted that Panel C3 failed the drop test.",
        "Panel C3 must have failed the drop test.",
        "The acceptance criteria are met by all five panels.",
        "The coating is acceptable.",
        "The drop test requires about 5 s of free fall.",
    ],
)
def test_results_negations_and_descriptions_are_not_criteria(sentence):
    assert criterion(sentence) != "criterion"


@pytest.mark.parametrize(
    ("sentence", "expected"),
    [
        ("Each panel will be dropped twice in the next series.", "plan"),
        ("Run A1 was burned as planned.", "not_plan"),
        ("No further drops are planned.", "not_plan"),
        ("The coupons were stored to be dried later.", "not_plan"),
    ],
)
def test_plans_are_read_from_the_governing_verb(sentence, expected):
    assert plan(sentence) == expected


@pytest.mark.parametrize(
    ("sentence", "expected"),
    [
        ("The goal of the project is to rank foams by charring rate.", "goal"),
        ("The work seeks to rank the foams.", "goal"),
        ("The target temperature was 40 C.", "uncertain"),
    ],
)
def test_a_goal_needs_a_goal_frame(sentence, expected):
    assert goal(sentence) == expected


@pytest.mark.parametrize(
    ("sentence", "reading"),
    [
        # A planning participle is the plan, not a past verb.
        ("Planned oxygen for each panel: 34 %.", "plan"),
        ("The proposed chamber pressure is 50 kPa.", "plan"),
        # Metamorphic: the same participle beside a past verb was done.
        ("The planned tests were run at 34 %.", "not_plan"),
    ],
)
def test_a_planning_participle_is_read_as_a_plan(sentence, reading):
    assert plan(sentence) == reading


@pytest.mark.parametrize(
    "sentence",
    [
        # A criterion defined in the present after a qualifying phrase.
        "The pass/fail criterion for a coupon, in both rigs, is set by the count of ignitions.",
        "The acceptance limit of the drum test is defined by the char length.",
    ],
)
def test_a_criterion_defined_in_the_present_is_a_criterion(sentence):
    assert criterion(sentence) == "criterion"


def test_a_past_report_about_a_criterion_noun_is_not_read_as_its_definition():
    assert criterion("The acceptance criteria were met by all panels.") == "not_criterion"


@pytest.mark.parametrize(
    ("sentence", "reading"),
    [
        # A purpose infinitive may state the study's goal; the clause does not settle it.
        ("This report covers a test series to assess the char length of foam.", "uncertain"),
        ("Run A1 charred along its edge.", "not_goal"),
    ],
)
def test_a_purpose_infinitive_leaves_a_goal_for_review(sentence, reading):
    assert goal(sentence) == reading


@pytest.mark.parametrize(
    "sentence", ["• Goal to qualify foam panels for cabin use", "Objective: to rank the coatings."]
)
def test_a_goal_noun_that_opens_its_infinitive_is_a_goal(sentence):
    assert goal(sentence) == "goal"


@pytest.mark.parametrize(
    "sentence", ["Run A1 must have burned at 34 % oxygen.", "Run A1 may have charred at 34 %."]
)
def test_an_epistemic_perfect_does_not_say_the_value_was_done(sentence):
    # An inference about the past ("must have burned") is neither a report that it
    # happened nor a prescription.
    assert execution(sentence, sentence.index("34")) == "uncertain"
