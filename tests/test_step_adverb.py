"""SCIENCE_STEP_ADVERB: a manner adverb in a step, and an apparatus noun, are not an outcome (invented text)."""

import pytest

from nasa_fire_ai.ingestion.statement_integrity import (
    outcome_cue,
    procedure_without_outcome,
    step_adverb_enabled,
)


@pytest.fixture
def on(monkeypatch):
    monkeypatch.setenv("SCIENCE_STEP_ADVERB", "1")


@pytest.mark.parametrize(
    "text",
    [
        "The coupon was evenly heated by the igniter.",
        "The coupon was gently tested with a burner.",
        "The panel was slowly mounted on the holder and tested at the base.",
        "The tube was quickly purged through the reactor line.",
    ],
)
def test_a_step_with_a_manner_adverb_or_an_apparatus_noun_is_a_procedure(on, text):
    assert procedure_without_outcome(text)


@pytest.mark.parametrize(
    "text",
    [
        "The coupon was evenly heated and ignited.",
        "The coupon was tested with a burner and it burned.",
        "The coupon was slowly heated until it failed.",
        "The coupon was tested and showed no reaction.",
    ],
)
def test_a_reported_outcome_keeps_the_observation(on, text):
    assert not procedure_without_outcome(text)


def test_the_flag_is_on_by_default_and_off_reads_as_before(monkeypatch):
    monkeypatch.delenv("SCIENCE_STEP_ADVERB", raising=False)
    assert step_adverb_enabled()
    monkeypatch.setenv("SCIENCE_STEP_ADVERB", "0")
    assert not step_adverb_enabled()
    assert not procedure_without_outcome("The coupon was evenly heated by the igniter.")
    assert procedure_without_outcome("The coupon was heated by a spark.")


def test_an_apparatus_noun_is_no_outcome_only_with_the_flag():
    assert outcome_cue("the igniter") is not None
    assert outcome_cue("the igniter", instruments=True) is None
    assert outcome_cue("the sample ignited", instruments=True) is not None
