"""SCIENCE_DIRECTIVE_EXECUTION and SCIENCE_QUALIFIER_CHECK (invented text).

A request is not an execution; a clause qualifier the record dropped is held. The directive frame
constrains the axes only and never picks a role; the qualifier check reads the printed clause."""

import pytest

from nasa_fire_ai.ingestion.statement_integrity import (
    HOLD_CHECKS,
    directive_execution_enabled,
    directive_not_executed,
    qualifier_check_enabled,
    qualifiers_dropped,
)


def context(clause="", **item):
    return {"item": item, "clause": lambda: clause}


@pytest.mark.parametrize(
    "text",
    [
        "The vendor was asked to test the cord at two draft speeds.",
        "The team was requested to measure the char depth.",
        "Two panels were tasked to hold their shape for ten minutes.",
        "The lab was instructed to repeat the drop.",
        "Each coupon is required to be dried first.",
        "The agency requested the lab to run the series.",
    ],
)
def test_a_directive_without_completion_is_not_an_execution(text):
    assert directive_not_executed(text, None, context(epistemic="experimental_configuration"))


@pytest.mark.parametrize(
    "text",
    [
        "The vendor was asked to test the cord and the tests were completed in May.",
        "The cord was tested at two draft speeds.",
        "The team asked about the char depth.",
    ],
)
def test_a_completed_or_plain_clause_is_not_held(text):
    assert not directive_not_executed(text, None, context(epistemic="experimental_configuration"))


def test_a_record_that_states_a_modality_is_not_held():
    ctx = context(epistemic="experimental_configuration", modality="intended")
    assert not directive_not_executed("The vendor was asked to test the cord.", None, ctx)


@pytest.mark.parametrize(
    ("clause", "text"),
    [
        ("No smoke was seen at the lower draft.", "Smoke was seen at the lower draft."),
        ("The cord may have charred along its edge.", "The cord charred along its edge."),
        ("If the cord ignites, the tray is closed.", "The tray is closed."),
        ("The tray was not closed before the drop.", "The tray was closed before the drop."),
    ],
)
def test_a_dropped_negation_hedge_or_condition_is_held(clause, text):
    assert qualifiers_dropped(text, None, context(clause, epistemic="measured_observation"))


@pytest.mark.parametrize(
    ("clause", "text", "item"),
    [
        ("No smoke was seen.", "No smoke was seen.", {}),
        ("The cord may have charred.", "The cord may have charred.", {}),
        (
            "If the cord ignites, the tray is closed.",
            "If the cord ignites, the tray is closed.",
            {},
        ),
        ("The cord may have charred.", "The cord charred.", {"modality": "hypothetical"}),
        ("The cord charred.", "The cord charred.", {}),
        ("", "No smoke was seen.", {}),
    ],
)
def test_a_kept_or_stated_qualifier_is_not_held(clause, text, item):
    assert not qualifiers_dropped(
        text, None, context(clause, epistemic="measured_observation", **item)
    )


def test_flags_are_off_by_default_and_bound(monkeypatch):
    from nasa_fire_ai.ingestion.scientific_facets import ROLES

    monkeypatch.delenv("SCIENCE_DIRECTIVE_EXECUTION", raising=False)
    monkeypatch.delenv("SCIENCE_QUALIFIER_CHECK", raising=False)
    assert not directive_execution_enabled() and not qualifier_check_enabled()
    assert {"directive_not_executed", "qualifiers_preserved"} <= set(HOLD_CHECKS)
    for name in ("measured_observation", "experimental_configuration"):
        assert {"directive_not_executed", "qualifiers_preserved"} <= set(ROLES[name].holds)
    assert "qualifiers_preserved" not in ROLES["tentative_interpretation"].holds


# ---- end to end: the printed clause is read, not the quote the model chose
from test_document_extraction import entity, submitted, support, validate
from test_document_extraction import service as _service

from nasa_fire_ai.ingestion.document_extraction import Output

service = _service
PAGE = "Synthetic Drop Study\nI. Results\nNo smoke was seen at the lower draft.\nThe vendor was asked to test the cord.\n"


def statement_records(service, quote, epistemic="measured_observation"):
    p = submitted(service, PAGE)
    o = Output().model_dump()
    o["entities"] = [
        entity(p, "inv", "Synthetic Drop Study", "Investigation", "Synthetic Drop Study")
    ]
    o["statements"] = [
        {
            "subjects": ["inv"],
            "text": quote,
            "class_id": "ReportedObservation",
            "epistemic": epistemic,
            "study": "current",
            "support": support(p, quote),
        }
    ]
    return [r for r in validate(service, p, o)["records"] if r["kind"] == "statements"]


def test_a_quote_that_stops_after_the_negation_is_held_with_the_flag(service, monkeypatch):
    monkeypatch.delenv("SCIENCE_QUALIFIER_CHECK", raising=False)
    off = statement_records(service, "smoke was seen at the lower draft.")
    monkeypatch.setenv("SCIENCE_QUALIFIER_CHECK", "1")
    on = statement_records(service, "smoke was seen at the lower draft.")
    assert (
        "QUALIFIER_DROPPED_FROM_CLAUSE" in on[0]["reasons"]
        and on[0]["status"] != "SOURCE_SUPPORTED"
    )
    assert "QUALIFIER_DROPPED_FROM_CLAUSE" not in off[0]["reasons"]


def test_the_whole_negated_sentence_is_not_held(service, monkeypatch):
    monkeypatch.setenv("SCIENCE_QUALIFIER_CHECK", "1")
    on = statement_records(service, "No smoke was seen at the lower draft.")
    assert "QUALIFIER_DROPPED_FROM_CLAUSE" not in on[0]["reasons"]


def quantity_record(service, sentence, value, epistemic="reported_quantity"):
    p = submitted(service, "Synthetic Drop Study\nI. Results\n" + sentence + "\n")
    o = Output().model_dump()
    o["entities"] = [
        entity(p, "n", "cord", "Sample", sentence),
    ]
    o["quantities"] = [
        {
            "subject": "n",
            "label": "smolder time",
            "expression": value,
            "unit": "s",
            "epistemic": epistemic,
            "support": support(p, sentence),
        }
    ]
    return next(r for r in validate(service, p, o)["records"] if r["kind"] == "quantities")


def test_a_hedged_value_clause_is_held_with_the_qualifier_flag(service, monkeypatch):
    sentence = "The cord may have a smolder time of 9 s."
    monkeypatch.delenv("SCIENCE_QUALIFIER_CHECK", raising=False)
    off = quantity_record(service, sentence, "9")
    monkeypatch.setenv("SCIENCE_QUALIFIER_CHECK", "1")
    on = quantity_record(service, sentence, "9")
    assert "QUALIFIER_DROPPED_FROM_CLAUSE" not in off["reasons"]
    if off["status"] == "SOURCE_SUPPORTED":
        assert on["status"] != "SOURCE_SUPPORTED"
    assert (
        on["status"] in {"UNRESOLVED", "REJECTED"}
        or "QUALIFIER_DROPPED_FROM_CLAUSE" in on["reasons"]
    )
