"""SCIENCE_RECORDING_RULE: one recording-rule frame, read by the three
checks that each kept their own copy (the clause criterion frame, the test-criterion
kind cue, the normative-requirement cue).

A recording rule is a decision rule (ISO/IEC 17025:2017, 3.7 and 7.8.6: how a result is
stated against a condition): a conditional subordinate clause ("if", "unless"), then, in
the main clause, a present passive of any past participle followed by "as" and a category (no verb list; a numeric complement such as "taken as 0.9"
is an assumed value; see test_recording_and_fragments.py).

Synthetic text only (B8): an invented domain (welds, cells, gauges, seals).
"""

import pytest

from nasa_fire_ai.ingestion import clause_cues
from nasa_fire_ai.ingestion.document_extraction import role_errors
from nasa_fire_ai.ingestion.scientific_facets import facet_review

FLAG = "SCIENCE_RECORDING_RULE"
NORMATIVE = "NORMATIVE_ROLE_NOT_EXPLICIT_IN_SOURCE"
NOT_CRITERION = "CRITERION_NOT_EXPLICIT_IN_SOURCE"
VERBS = ("recorded", "reported", "scored", "counted", "rated", "classified")  # a sample


@pytest.fixture
def on(monkeypatch):
    monkeypatch.setenv(FLAG, "1")
    return monkeypatch


def three_readings(text):
    """(clause criterion, test-criterion facet, normative-requirement role) for ``text``."""
    return (
        clause_cues.criterion(text) == "criterion",
        facet_review("statements", {"text": text, "epistemic": "test_criterion"}) == ([], []),
        NORMATIVE not in role_errors({"text": text, "epistemic": "normative_requirement"}),
    )


# --- positive -------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "If the weld shows porosity, the joint is classified as a reject.",
        "If a cell vents, the cycle is scored as void.",
        "If a cell vents, then the cycle is scored as void.",
        "If the gauge drifts past the band, the reading is classified as void.",
        "Unless the bead cracks, the joint is recorded as a pass.",
    ],
)
def test_a_recording_rule_is_read_alike_by_all_three_checks(on, text):
    assert clause_cues.recording_rule(text)
    assert three_readings(text) == (True, True, True)


def test_there_is_no_verb_list_left():
    assert not hasattr(clause_cues, "RECORDING_VERBS")


# --- negative -------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        # A past event, not a rule.
        "The reading was classified as void after the gauge drifted.",
        # An assumed value, not a recorded result.
        "If no value is printed, the emissivity is taken as 0.9.",
        # A reporting convention without a condition.
        "Values are reported as mean and range.",
        # The recording verb sits in the condition, not in the main clause.
        "If values are reported as means, the bars show the range.",
    ],
)
def test_what_is_not_a_recording_rule_is_read_as_none_by_all_three(on, text):
    assert not clause_cues.recording_rule(text)
    criterion, facet, normative = three_readings(text)
    assert not normative
    assert not facet
    assert not criterion


def test_a_recorded_past_event_is_still_not_a_criterion(on):
    assert clause_cues.criterion("The result was recorded as a pass after the weld cooled.") == (
        "not_criterion"
    )


# --- metamorphic ----------------------------------------------------------------------


@pytest.mark.parametrize("verb", VERBS)
def test_every_verb_of_the_list_reads_alike_in_every_check(on, verb):
    text = f"If the bead cracks, the joint is {verb} as a reject."
    assert three_readings(text) == (True, True, True)


@pytest.mark.parametrize("verb", VERBS)
def test_then_or_a_comma_after_the_condition_reads_alike(on, verb):
    comma = f"If a cell vents, the cycle is {verb} as void."
    then = f"If a cell vents, then the cycle is {verb} as void."
    assert three_readings(comma) == three_readings(then)


@pytest.mark.parametrize(("noun", "other"), [("cell", "module"), ("cycle", "charge")])
def test_renaming_the_object_keeps_the_reading(on, noun, other):
    text = "If a cell vents, the cycle is scored as void."
    assert three_readings(text) == three_readings(text.replace(noun, other))


def test_present_and_past_differ_only_by_tense(on):
    rule = "If the bead cracks, the joint is classified as a reject."
    event = "The bead cracked, and the joint was classified as a reject."
    assert clause_cues.recording_rule(rule)
    assert not clause_cues.recording_rule(event)
    assert clause_cues.criterion(event) != "criterion"


def test_flag_is_on_by_default(monkeypatch):
    monkeypatch.delenv(FLAG, raising=False)
    # A numeric complement is an assumed value, not a classification.
    taken = "If no value is printed, the emissivity is taken as 0.9."
    assert NORMATIVE in role_errors({"text": taken, "epistemic": "normative_requirement"})


def test_flag_off_keeps_each_copy(monkeypatch):
    # Off, the three copies keep their own lists: "considered as" passes the normative
    # cue and "taken as" the clause frame, exactly as before.
    monkeypatch.setenv(FLAG, "0")
    considered = "If the seal holds, then the joint is considered as sound."
    taken = "If no value is printed, the emissivity is taken as 0.9."
    assert NORMATIVE not in role_errors({"text": considered, "epistemic": "normative_requirement"})
    assert clause_cues.criterion(taken) == "criterion"
