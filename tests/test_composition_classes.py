"""Composition cue classes (SCIENCE_SCORABLE_COMPOSITION): CONTRAST_CUES and BOUND_CUE are
classes with general references, not enumerations. Invented materials only; no model call."""

import pytest

from nasa_fire_ai.ingestion.clause_cues import _APPROXIMATOR
from nasa_fire_ai.ingestion.composition import (
    BOUND_CUE,
    _contrasted,
    _list_shares,
)

SUBJECT, PART, OTHER = "Zorvium blend", "Quellite", "Arnite"


def shares(prefix, part=PART):
    sentence = f"The composition of {SUBJECT} is {prefix} 40% {part} and 60% {OTHER}."
    return _list_shares(sentence, SUBJECT, part)


def bounded(prefix, part=PART):
    found = shares(prefix, part)
    assert found and len(found) == 1
    return found[0][1]


def test_an_exact_share_is_exact():
    assert shares("")[0][:2] == (40.0, False)
    assert shares("")[0][2] == "40% Quellite"


@pytest.mark.parametrize(
    "prefix",
    [
        "approximately",
        "about",
        "roughly",
        "nearly",
        "almost",
        "around",
        "less than",
        "more than",
        "fewer than",
        "greater than",
        "higher than",
        "smaller than",
        "at least",
        "at most",
        "up to",
        "as much as",
        "as little as",
        "<",
        ">",
        "≤",
        "≥",
        "≈",
        "±",
    ],
)
def test_a_bound_cue_makes_the_share_a_bound(prefix):
    assert bounded(prefix) is True


def test_the_added_sign_keeps_the_printed_qualifier():
    assert shares("≈")[0][2].startswith("≈")


@pytest.mark.parametrize("word", ["approximately", "about", "roughly", "nearly", "around"])
def test_every_approximator_member_is_a_bound(word):
    # Metamorphic: the class is clause_cues' own, any member gives the same reading.
    assert bounded(word) is True and bounded(word.upper()) is True


def test_the_approximator_is_the_clause_cues_class():
    assert _APPROXIMATOR in BOUND_CUE.pattern


@pytest.mark.parametrize("than", ["less", "fewer", "greater", "lower", "larger"])
def test_any_comparative_before_than_is_a_bound(than):
    assert bounded(f"{than} than") is True


def test_a_comparative_without_than_is_still_held_by_the_fallback():
    assert bounded("higher") is True


# Words that are in no bound class: the structural fallback still holds the share as a bound
# (qualified), never as an exact value. Some of these left the explicit list on purpose.
@pytest.mark.parametrize(
    "prefix",
    [
        "under",
        "over",
        "below",
        "above",
        "between",
        "maximum",
        "minimum",
        "max",
        "min",
        "circa",
        "ca.",
        "~",
        "zorvex",
        "nominal",
    ],
)
def test_any_other_preceding_word_or_sign_holds_the_share_as_a_bound(prefix):
    assert bounded(prefix) is True
    assert shares(prefix)[0][2].startswith(prefix)


@pytest.mark.parametrize("prefix", ["", "the", "a", "this", "its"])
def test_a_bare_or_determiner_led_share_stays_exact(prefix):
    assert bounded(prefix) is False


def test_a_bare_second_item_stays_exact_and_a_qualified_one_is_a_bound():
    plain = f"The composition of {SUBJECT} is 40% {PART} and the 60% {OTHER}."
    assert _list_shares(plain, SUBJECT, OTHER)[0][:2] == (60.0, False)
    held = f"The composition of {SUBJECT} is 40% {PART} and circa 60% {OTHER}."
    assert _list_shares(held, SUBJECT, OTHER)[0][1] is True
    assert _list_shares(held, SUBJECT, PART)[0][1] is False


def test_the_qualifier_applies_to_its_own_item_only():
    sentence = f"The composition of {SUBJECT} is under 40% {PART} and 60% {OTHER}."
    assert _list_shares(sentence, SUBJECT, PART)[0][1] is True
    assert _list_shares(sentence, SUBJECT, OTHER)[0][1] is False


def test_a_range_is_still_a_bound_through_the_range_rule():
    sentence = f"The composition of {SUBJECT} is 30-40% {PART} and 60% {OTHER}."
    assert _list_shares(sentence, SUBJECT, PART)[0][1] is True


@pytest.mark.parametrize(
    "text",
    [
        "Zorvium uses Arnite instead of Quellite.",
        "Zorvium contains no Quellite.",
        "Zorvium is no longer made with Quellite.",
        "Zorvium has none of the Quellite.",
        "Zorvium holds nothing of Quellite.",
        "Zorvium is made without Quellite.",
        "Zorvium has Arnite in place of Quellite.",
        "Zorvium has Arnite rather than Quellite.",
        "Zorvium has all but Arnite, except Quellite.",
        "Zorvium is Arnite excluding Quellite.",
        "Zorvium is never Quellite.",
        "Zorvium has neither Arnite nor Quellite.",
        "Nobody added Quellite.",
        "Nowhere is Quellite used.",
        "Zorvium is not Quellite.",
    ],
)
def test_a_contrast_cue_before_the_constituent_contrasts_it(text):
    assert _contrasted(text, PART) is True


def test_no_cue_means_not_contrasted():
    assert _contrasted("Quellite and Arnite are listed.", PART) is False
    assert _contrasted("Zorvium contains Quellite.", PART) is False


def test_a_cue_after_the_constituent_does_not_contrast_it():
    assert _contrasted("Zorvium contains Quellite, not Arnite.", PART) is False


def test_a_word_that_merely_contains_a_negator_is_not_a_cue():
    assert _contrasted("Zorvium contains notable Quellite and nothingness.", PART) is False
    assert _contrasted("Zorvium is knotted with Quellite.", PART) is False


@pytest.mark.parametrize("word", ["not", "no", "never", "none", "nothing", "without"])
def test_any_negator_member_gives_the_same_reading(word):
    assert _contrasted(f"Zorvium has {word} Quellite.", PART) is True


def test_unlike_stays_a_contrast_cue():
    # Kept as a safety member: dropping it would let the constituent after it read as a
    # component of the formulation.
    assert _contrasted("Zorvium is unlike Quellite.", PART) is True
