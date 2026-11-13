"""ORIGIN reads where a value is printed with the evidence validator's own locator.

A value the validator locates is never held "not located"; a value neither locates stays held
(the check fails closed). Invented sentences only."""

import pytest
from test_origin_final_round import check, held

from nasa_fire_ai.ingestion import value_origin

FLAG = "SCIENCE_ORIGIN_VALIDATOR_LOCATOR"


def located(record):
    occurrences = record["origin"]["occurrences"]
    return not any(o.get("basis") == "SPAN_NOT_LOCATED_IN_EVIDENCE" for o in occurrences)


def span_of(body, printed):
    start = body.index(printed)
    return [{"evidence_id": "E1", "start": start, "end": start + len(printed), "quote": printed}]


@pytest.mark.parametrize(
    "body, value, printed",
    [
        ("The waxed cord lost .54 mg of wax in the hall.", ".54", ".54 mg"),
        ("The valve ran at ~.4 slm during the hall trial.", "~.4", "~.4 slm"),
        ("Later, two cords were lit in each hall trial.", "two", "two"),
    ],
)
def test_a_span_the_validator_locates_is_never_held_as_not_located(body, value, printed):
    record = check(body, value, value_spans=span_of(body, printed))
    assert located(record), record["origin"]
    assert not held(record), record["origin"]


def test_the_validator_locator_finds_the_value_in_the_support_quote():
    body = "The waxed cord lost .54 mg of wax in the hall."
    record = check(body, ".54")
    assert located(record), record["origin"]
    assert not held(record), record["origin"]


@pytest.mark.parametrize("value", ["12", ".54"])
def test_a_value_neither_locator_finds_stays_held(value):
    body = "The waxed cord lost 7 mg of wax in the hall."
    record = check(body, value)
    assert held(record)
    assert record["origin"]["occurrences"][0]["basis"] == "SPAN_NOT_LOCATED_IN_EVIDENCE"


def test_a_span_that_points_at_other_text_is_not_a_place_for_either_locator():
    body = "The waxed cord lost 7 mg of wax and .54 mg of oil in the hall."
    record = check(body, "12", value_spans=span_of(body, "7 mg"))
    assert held(record)
    assert record["origin"]["occurrences"][0]["basis"] == "SPAN_NOT_LOCATED_IN_EVIDENCE"


def test_the_flag_off_keeps_the_earlier_reading(monkeypatch):
    monkeypatch.setenv(FLAG, "0")
    assert not value_origin.validator_locator_enabled()
    body = "The waxed cord lost .54 mg of wax in the hall."
    record = check(body, ".54", value_spans=span_of(body, ".54 mg"))
    assert held(record)
    assert record["origin"]["occurrences"][0]["basis"] == "SPAN_NOT_LOCATED_IN_EVIDENCE"


def test_the_flag_is_on_by_default(monkeypatch):
    monkeypatch.delenv(FLAG, raising=False)
    assert value_origin.validator_locator_enabled()
