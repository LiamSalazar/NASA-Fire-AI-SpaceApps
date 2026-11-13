"""List 4 of the F4 lists: the recording rule reads its predicate by structure (any past
participle followed by "as", ISO/IEC 17025:2017 decision-rule frame), and the reference
fragment end is initials, years and the bibliographic class of
``nasa_fire_ai.ingestion.abbreviations`` (The Chicago Manual of Style, 17th ed., ch. 10).

Synthetic text only (B8): an invented domain (welds, kilns, quessel and zorvex parts).
"""

import re

import pytest
from test_recording_rule import three_readings

from nasa_fire_ai.ingestion import abbreviations, clause_cues
from nasa_fire_ai.ingestion.document_structure import FRAGMENT_END, printed_table_regions

# --- recording rule ---------------------------------------------------------------------

REGULAR = ("logged", "tallied", "graded", "marked", "tagged", "recorded")
IRREGULAR = ("taken", "set", "held", "built")


@pytest.fixture
def on(monkeypatch):
    monkeypatch.setenv("SCIENCE_RECORDING_RULE", "1")
    return monkeypatch


def rule(participle, noun="joint"):
    return f"If the zorvex bead cracks, the {noun} is {participle} as a reject."


def test_a_participle_outside_the_old_list_is_a_recording_rule(on):
    text = "If the quessel coupon does not crack, the result is logged as a pass."
    assert clause_cues.recording_rule(text)
    assert three_readings(text) == (True, True, True)


def test_no_verb_list_remains():
    assert not hasattr(clause_cues, "RECORDING_VERBS")
    assert not hasattr(clause_cues, "RECORDING_RULE")


@pytest.mark.parametrize(
    "text",
    [
        # No "as": a use, not a recording.
        "If the quessel coupon cracks, the sample is used.",
        # No condition.
        "The result is logged as a pass.",
        # An assumed or default value, not a category.
        "If no zorvex value is printed, the emissivity is taken as 0.9.",
        "If no zorvex value is printed, the gap is set as 5 mm.",
        "If no zorvex value is printed, the load is taken as T = 300.",
        # Not a participle before "as".
        "If the zorvex seal holds, then the joint is sound as built.",
        # Past tense: an event.
        "The zorvex bead cracked, and the joint was logged as a reject.",
        # The participle sits in the condition.
        "If values are logged as means, the bars show the range.",
        # A sentence break between condition and predicate.
        "If the zorvex bead cracks. The joint is logged as a reject.",
    ],
)
def test_what_is_not_a_recording_rule_does_not_match(on, text):
    assert not clause_cues.recording_rule(text)


@pytest.mark.parametrize("participle", REGULAR + IRREGULAR)
def test_every_participle_reads_alike(on, participle):
    assert clause_cues.recording_rule(rule(participle))
    assert clause_cues.recording_rule(rule(participle, "cycle"))


@pytest.mark.parametrize("participle", REGULAR)
def test_then_or_a_comma_and_negation_read_alike(on, participle):
    comma = f"If a quessel cell vents, the cycle is {participle} as void."
    then = f"If a quessel cell vents, then the cycle is {participle} as void."
    negated = f"If a quessel cell vents, the cycle is not {participle} as void."
    assert clause_cues.recording_rule(comma)
    assert clause_cues.recording_rule(then)
    assert clause_cues.recording_rule(negated)


@pytest.mark.parametrize("participle", ["considered", "taken", "set", "logged"])
@pytest.mark.parametrize(
    ("category", "number"),
    [("sound", "0.9"), ("a pass", "5 mm"), ("void", "T = 300"), ("a reject", "-40")],
)
def test_same_frame_category_complement_matches_numeric_does_not(on, participle, category, number):
    frame = "If the quessel seal holds, then the joint is {} as {}."
    assert clause_cues.recording_rule(frame.format(participle, category))
    assert not clause_cues.recording_rule(frame.format(participle, number))


def test_a_classification_is_a_recording_rule(on):
    # A category is assigned on a condition ("considered as sound"): a decision rule.
    text = "If the seal holds, then the joint is considered as sound."
    assert three_readings(text) == (True, True, True)


@pytest.mark.parametrize("bound", [">425 C", "<= 3 mm", "above 40 kPa", "≥ 12 s"])
def test_an_interval_complement_names_a_class_and_is_a_recording_rule(on, bound):
    text = f"If the zorvex probe heats past the band, then the value is recorded as {bound}."
    assert clause_cues.recording_rule(text)


def test_a_later_number_does_not_make_the_complement_numeric(on):
    assert clause_cues.recording_rule("If a cell vents, the cycle is logged as void after 3 runs.")


def test_a_non_participle_in_the_same_slot_never_matches(on):
    for word in ("sound", "fast", "bad", "open", "broken"):
        assert not clause_cues.recording_rule(rule(word))


# --- reference fragment end -------------------------------------------------------------

TABLE = "Table 4: Quessel widths\nPlate A 0.4\nPlate B 0.7\n"


def regions(previous):
    return printed_table_regions(previous + "\n" + TABLE)


@pytest.mark.parametrize(
    "ending", ["Kiln ledger of Arden, Vol.", "Notes of Arden, pp.", "Arden, no."]
)
def test_a_line_ending_in_a_bibliographic_abbreviation_is_a_fragment(ending):
    assert FRAGMENT_END.search(ending)
    assert regions(ending) == []


@pytest.mark.parametrize(
    "ending", ["Handled by Zorvex Inc.", "Crated by Quessel Co.", "Mr. Quessel Jr."]
)
def test_a_dropped_abbreviation_no_longer_blocks_a_caption(ending):
    assert not FRAGMENT_END.search(ending)
    assert len(regions(ending)) == 1


@pytest.mark.parametrize(
    "ending",
    ["Arden, J.", "Arden, 1999.", "Arden, 1999b.", "Arden et al.", "Arden VOL.", "See Fig."],
)
def test_initials_years_and_case_variants_still_end_a_fragment(ending):
    assert FRAGMENT_END.search(ending)


def test_proc_lett_phys_and_eq_are_no_longer_members():
    for word in ("proc", "lett", "phys", "eq", "jr", "st", "co", "inc"):
        assert not FRAGMENT_END.search(f"Zorvex {word}.")
        assert word not in abbreviations.BIBLIOGRAPHIC_ABBREVIATIONS


def test_a_word_that_merely_ends_like_a_member_is_not_a_fragment():
    assert not FRAGMENT_END.search("The quessel seal was reconfigured to a hold.")
    assert not FRAGMENT_END.search("The zorvex rig is online.")


# --- the shared class -------------------------------------------------------------------


def test_the_class_is_referenced_and_shared():
    assert "Chicago Manual of Style" in abbreviations.__doc__
    assert "chapter 10" in abbreviations.__doc__
    assert set(abbreviations.BIBLIOGRAPHIC_ABBREVIATIONS) <= set(
        abbreviations.SCHOLARLY_ABBREVIATIONS
    )
    assert set(abbreviations.POINTER_ABBREVIATIONS) <= set(abbreviations.SCHOLARLY_ABBREVIATIONS)


@pytest.mark.parametrize("member", abbreviations.POINTER_ABBREVIATIONS)
def test_pointer_abbreviations_still_mark_an_endophoric_pointer(member):
    assert clause_cues.ENDOPHORIC_MARKER.match(f"{member}. 3")
    assert clause_cues.ENDOPHORIC_MARKER.match(f"{member} 3")


def test_pointer_abbreviations_keep_their_members():
    assert abbreviations.POINTER_ABBREVIATIONS == ("fig", "figs", "sec", "ch", "p", "pp")
    assert not clause_cues.ENDOPHORIC_MARKER.match("p-type layer")
    assert not clause_cues.ENDOPHORIC_MARKER.match("ch4 level")


def test_alternation_puts_the_longer_member_first():
    pattern = re.compile(abbreviations.alternation(["p", "pp", "eds", "ed"]))
    assert pattern.match("pp").group() == "pp"
    assert pattern.match("eds").group() == "eds"
