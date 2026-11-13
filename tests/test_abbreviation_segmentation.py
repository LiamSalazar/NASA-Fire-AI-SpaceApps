"""List 5: scholarly abbreviations do not end sentences (SCIENCE_ABBREVIATION_SEGMENTATION,
and SCIENCE_ABBREVIATION_SEGMENTATION_INPUT for the readings that change model input).

How the helper decides whether a period ends a sentence (``abbreviation_period``): it finds
the member of the class whose period it is, then reads what follows.

- e.g., i.e., cf., viz., vs., ca., op. cit.: never an end.
- etc., et al., ibid.: an end at the end of the text, at a line break, or before whitespace
  and an uppercase letter (also "(" except for "et al."); "et al. (2010)", "et al. 8" and
  "etc. and" are not ends.
- Fig./Figs., Eq./Eqs., Ref./Refs., sec., ch., vol., no., p./pp., n./nn., ed./eds.: not an end
  only before a numeral, "(" and a numeral, or a one-letter or roman label; before a word
  ("The answer was no. The next run") the period stays an end.

Every sentence here is invented (B8): a quellin probe, a zorvex rig, a vorn cell.
"""

import pytest

from nasa_fire_ai.ingestion import (
    clause_cues,
    composition,
    extraction_resources,
    narrative_candidates,
    scientific_scope,
    statement_integrity,
    subject_recognition,
)
from nasa_fire_ai.ingestion import document_extraction as de
from nasa_fire_ai.ingestion.abbreviations import (
    MASK,
    abbreviation_period,
    mask_abbreviation_periods,
    segmentation_input_view,
    segmentation_view,
)

FLAG = "SCIENCE_ABBREVIATION_SEGMENTATION"
INPUT_FLAG = "SCIENCE_ABBREVIATION_SEGMENTATION_INPUT"


@pytest.fixture
def on(monkeypatch):
    monkeypatch.setenv(FLAG, "1")
    monkeypatch.delenv(INPUT_FLAG, raising=False)


@pytest.fixture
def off(monkeypatch):
    monkeypatch.setenv(FLAG, "0")
    monkeypatch.delenv(INPUT_FLAG, raising=False)


@pytest.fixture
def input_on(monkeypatch):
    monkeypatch.setenv(INPUT_FLAG, "1")
    monkeypatch.setenv(FLAG, "0")


def periods(text):
    return [i for i, ch in enumerate(text) if ch == "." and abbreviation_period(text, i)]


# Each sentence has a member of the class in its middle, followed by "(" or a capital, where a
# plain "." + space + capital/paren rule cuts.
MID_SENTENCE = [
    ("The quellin probe (e.g. Zorvex limits) held.", "e.g."),
    ("The quellin probe (i.e. Zorvex limits) held.", "i.e."),
    ("The quellin probe (cf. Zorvex limits) held.", "cf."),
    ("The quellin probe (viz. Zorvex limits) held.", "viz."),
    ("The quellin probe was hot vs. Zorvex rigs in the cell.", "vs."),
    ("The quellin probe was hot, ca. (2) times the zorvex rig.", "ca."),
    ("The quellin probe, op. cit. 4, held.", "op. cit."),
    ("The quellin probe held, see Fig. (3) and the vorn cell.", "Fig."),
    ("The quellin probes held, see Figs. (3) and the vorn cell.", "Figs."),
    ("The quellin probe held, see Eq. (2) and the vorn cell.", "Eq."),
    ("The quellin probes held, see Eqs. (2) and the vorn cell.", "Eqs."),
    ("The quellin probe held, see Ref. (5) and the vorn cell.", "Ref."),
    ("The quellin probes held, see Refs. (5) and the vorn cell.", "Refs."),
    ("The quellin probe held, see Vol. (4) and the vorn cell.", "Vol."),
    ("The quellin probe held, see No. (4) and the vorn cell.", "No."),
    ("The quellin probe held, see pp. (4) and the vorn cell.", "pp."),
    ("Zorvex et al. (2010) reported a quellin probe.", "et al."),
    ("The quellin probe (Zorvex et al. 8) held.", "et al."),
    ("Zorvex et al. 2010 reported a quellin probe.", "et al."),
    ("The quellin probe held, etc. and the vorn cell.", "etc."),
]


def span_start(text, offset):
    return clause_cues._sentence_span(text, offset)[0]


@pytest.mark.parametrize(("text", "member"), MID_SENTENCE)
def test_member_mid_sentence_does_not_split_with_the_flag_on(on, text, member):
    del member
    assert span_start(text, len(text) - 2) == 0
    assert len(clause_cues.clauses(text)) <= 2  # at most the "and" / comma clause breaks
    assert MASK in segmentation_view(text)


@pytest.mark.parametrize(
    "text",
    [
        "The quellin probe (e.g. Zorvex limits) held.",
        "The quellin probe held, see Fig. (3) and the vorn cell.",
        "The quellin probe held, see Eq. (2) and the vorn cell.",
    ],
)
def test_the_same_sentences_split_with_the_flag_off(off, text):
    assert span_start(text, len(text) - 2) > 0
    assert segmentation_view(text) is text


def test_a_true_end_after_a_normal_word_still_splits(on):
    text = "The quellin probe held. The zorvex rig failed."
    assert span_start(text, len(text) - 2) == len("The quellin probe held. ")
    assert periods(text) == []


def test_a_label_word_before_a_word_is_still_an_end(on):
    text = "The answer for the zorvex rig was no. The next run began."
    assert span_start(text, len(text) - 2) == len("The answer for the zorvex rig was no. ")
    assert not abbreviation_period(text, text.index("no.") + 2)


def test_a_can_end_member_before_a_capital_is_an_end(on):
    for member in ("etc.", "ibid.", "et al."):
        text = f"The quellin probes held, {member} The next run began."
        assert span_start(text, len(text) - 2) == len(f"The quellin probes held, {member} ")
        assert periods(text) == []


def test_a_can_end_member_at_the_end_of_the_text_or_a_line_is_an_end(on):
    assert periods("The vorn cell held, etc.") == []
    assert periods("The vorn cell held, etc.\nthe next line") == []


def test_cut_falls_before_a_label_not_after_it(on):
    text = "Run 4 ended. Fig. 5 shows the vorn cell."
    assert span_start(text, len(text) - 2) == len("Run 4 ended. ")
    assert periods(text) == [text.index("Fig.") + 3]


def test_the_period_decision_per_group():
    text = "A cf. B, etc. C, Fig. 3, no. D, no. the"
    assert abbreviation_period(text, text.index("cf.") + 2)  # never an end
    assert not abbreviation_period(text, text.index("etc.") + 3)  # can end, capital follows
    assert abbreviation_period(text, text.index("Fig.") + 3)  # label, numeral follows
    assert not abbreviation_period(text, text.index("no. D") + 2)  # no: numeral only
    assert abbreviation_period("see Fig. A and Vol. IV", 7)  # one-letter label follows
    assert not abbreviation_period(text, text.index("no. the") + 2)  # a word follows
    assert not abbreviation_period(text, 0)  # not a period
    assert not abbreviation_period(text, len(text) + 4)


def test_inner_periods_and_internal_spaces():
    assert mask_abbreviation_periods("a (e. g. b) c") == f"a (e{MASK} g{MASK} b) c"
    assert mask_abbreviation_periods("a (I.e. b) c") == f"a (I{MASK}e{MASK} b) c"
    assert mask_abbreviation_periods("a, op. cit. 4,") == f"a, op{MASK} cit{MASK} 4,"


@pytest.mark.parametrize(("text", "member"), MID_SENTENCE)
def test_mask_keeps_length_and_offsets(text, member):
    del member
    masked = mask_abbreviation_periods(text)
    assert len(masked) == len(text)
    assert masked.replace(MASK, ".") == text
    assert all(a == b for a, b in zip(masked, text, strict=True) if a != MASK)


def test_quotes_are_never_altered_by_the_mask():
    text = 'The "quellin probe" (Fig. 3) held, “zorvex” too.'
    masked = mask_abbreviation_periods(text)
    assert [c for c in masked if c in "\"“”'"] == [c for c in text if c in "\"“”'"]


# Metamorphic: a member for another member of its group, or a change of case or spacing.
@pytest.mark.parametrize(
    "group",
    [
        ("e.g.", "i.e.", "cf.", "viz.", "vs.", "ca."),
        ("Fig.", "Figs.", "Eq.", "Eqs.", "Ref.", "Refs.", "Vol.", "No.", "pp.", "Sec.", "Ch."),
    ],
)
def test_swapping_members_of_a_group_gives_the_same_segmentation(on, group):
    results = set()
    for member in group:
        arg = "(3)" if member[0].isupper() or member in {"pp."} else "Zorvex"
        text = f"The quellin probe held {member} {arg} and the vorn cell. Then it ended."
        results.add(text[span_start(text, text.index("Then")) :])
    assert len(results) == 1


@pytest.mark.parametrize("variant", ["e.g.", "E.g.", "e. g.", "E. G.", "e.g. "])
def test_case_and_spacing_do_not_change_the_segmentation(on, variant):
    text = f"The quellin probe ({variant} Zorvex limits) held. The next run began."
    assert span_start(text, len(text) - 2) == text.index("The next")


@pytest.mark.parametrize("variant", ["I.e.", "i.e.", "I. E.", "i. e."])
def test_case_and_spacing_do_not_change_the_class(variant):
    text = f"the chamber turned ({variant} onset)"
    assert mask_abbreviation_periods(text).count(MASK) == 2


# Splitters, one case per reading: the flag off cuts at the abbreviation, the flag on does not.
def test_s2_clauses(on, monkeypatch):
    text = "The quellin probe held (Fig. (3)) and cooled. The vorn cell ended."
    assert clause_cues.clauses(text)[0][2].startswith("The quellin probe held (Fig. (3))")
    monkeypatch.setenv(FLAG, "0")
    assert clause_cues.clauses(text)[0][2] == "The quellin probe held (Fig."


def test_s3_passive_clauses_keep_one_clause(on, monkeypatch):
    text = "The quellin probe cf. Zorvex was heated by the rig."
    assert len(clause_cues.passive_clauses(text)) == 1
    monkeypatch.setenv(FLAG, "0")
    assert len(clause_cues.passive_clauses(text)) == 2


def test_s4_purpose_clause_runs_through_the_abbreviation(on, monkeypatch):
    text = "The rig was set in order to compare e.g. Zorvex limits, then it ran."
    ((start, end),) = clause_cues.purpose_spans(text, forms=("marked",))
    assert "Zorvex limits" in text[start:end]
    monkeypatch.setenv(FLAG, "0")
    ((start, end),) = clause_cues.purpose_spans(text, forms=("marked",))
    assert "Zorvex" not in text[start:end]


def test_s23_windows_in_criterion_and_goal(on, monkeypatch):
    text = "The test limit for the vorn cell, cf. Zorvex, shall be 3 W."
    assert clause_cues.criterion(text) == "criterion"
    goal = "The goal of the zorvex campaign, see Eq. (2), is to compare cells."
    assert clause_cues.goal(goal) == "goal"
    monkeypatch.setenv(FLAG, "0")
    assert clause_cues.goal(goal) == "uncertain"


def test_s5_binding_clauses(on, monkeypatch):
    quote = "The quellin probe reached 5 W (Fig. 3) and the vorn cell reached 7 W."
    assert len(de.binding_clauses(quote)) == 1
    monkeypatch.setenv(FLAG, "0")
    assert len(de.binding_clauses(quote)) == 2


def test_s6_printed_subject_sentence(on, monkeypatch):
    window = "The vorn cell was heated (Fig. (3)) to 40 W. The rig was cooled."
    quote = "to 40 W."
    sentence = subject_recognition._sentence(window, quote, False)
    assert sentence.startswith("The vorn cell was heated (Fig.")
    monkeypatch.setenv(FLAG, "0")
    assert subject_recognition._sentence(window, quote, False).startswith("(3))")


def test_s9_s10_s11_sentence_readers(on, monkeypatch):
    evidence = {"e": {"text": "The vorn cell ran (Eq. (2)) hot. It was then 40 W."}}
    assert de.value_sentences([{"evidence_id": "e", "start": 2, "end": 6}], evidence) == [
        "The vorn cell ran (Eq. (2)) hot."
    ]
    monkeypatch.setenv(FLAG, "0")
    assert de.value_sentences([{"evidence_id": "e", "start": 2, "end": 6}], evidence) == [
        "The vorn cell ran (Eq."
    ]


def test_s18_composition_sentences(on, monkeypatch):
    text = "The zorvex mix (Fig. 3) has 5% quellin. The rest is vorn."
    assert len(list(composition._sentences(text))) == 2
    monkeypatch.setenv(FLAG, "0")
    assert len(list(composition._sentences(text))) == 3


def test_s20_sentence_with(on, monkeypatch):
    text = "See Ref. (5) for the quellin probe. The vorn cell ran."
    assert scientific_scope.sentence_with(text, "quellin") == "See Ref. (5) for the quellin probe."
    monkeypatch.setenv(FLAG, "0")
    assert scientific_scope.sentence_with(text, "quellin") == "(5) for the quellin probe."


def test_s23_statement_integrity_windows_keep_the_printed_text(on, monkeypatch):
    text = "The symbols, cf. Zorvex, are the vorn cell data."
    assert statement_integrity.documentary_pointer(text)
    assert statement_integrity.POINTER.search(text).group() == text.rstrip(".")
    monkeypatch.setenv(FLAG, "0")
    assert not statement_integrity.documentary_pointer(text)


# Track B: the readings that change model input, behind their own flag.
def test_q5_complexity_counts_sentences(input_on, monkeypatch):
    text = "The quellin probe (Fig. 3) held. The vorn cell failed."
    assert extraction_resources.complexity(text)["sentences"] == 2
    monkeypatch.delenv(INPUT_FLAG)
    assert extraction_resources.complexity(text)["sentences"] == 3


def test_q3_literal_candidates_quote_the_whole_sentence(input_on, monkeypatch):
    from types import SimpleNamespace

    semantic = SimpleNamespace(
        entity_mentions={}, properties={}, resolve_property=lambda label: (None, None)
    )
    segment = {
        "text": "Run A1 was tested as shown in Fig. 3 for the quellin probe. Then it stopped.",
        "evidence_id": "e",
        "source_id": "s",
        "start": 0,
        "section": "Results",
    }

    def quotes():
        found = narrative_candidates.literal_candidates(segment, semantic)
        return [s["quote"] for e in found["entities"] for s in e["support"]]

    assert quotes() == ["Run A1 was tested as shown in Fig. 3 for the quellin probe."]
    monkeypatch.delenv(INPUT_FLAG)
    assert quotes() == ["Run A1 was tested as shown in Fig."]


def test_q2_source_anchor_pattern_uses_the_class(input_on):
    # The class replaces the "al/Fig/Figs/Eq/Eqs" lookbehinds; Dr and Prof stay.
    assert segmentation_input_view("by Dr. Zorvex and Fig. 3") == f"by Dr. Zorvex and Fig{MASK} 3"


def test_the_two_flags_are_independent(monkeypatch):
    text = "The quellin probe (Fig. 3) held. The vorn cell failed."
    monkeypatch.setenv(FLAG, "1")
    monkeypatch.delenv(INPUT_FLAG, raising=False)
    assert segmentation_view(text) != text
    assert segmentation_input_view(text) is text
    assert extraction_resources.complexity(text)["sentences"] == 3
    monkeypatch.setenv(FLAG, "0")
    monkeypatch.setenv(INPUT_FLAG, "1")
    assert segmentation_view(text) is text
    assert segmentation_input_view(text) != text
    assert span_start("A cf. (Zorvex) held.", 12) > 0


def test_segmentation_is_on_by_default_and_input_is_off(monkeypatch):
    monkeypatch.delenv(FLAG, raising=False)
    monkeypatch.delenv(INPUT_FLAG, raising=False)
    text, _member = MID_SENTENCE[0]
    assert segmentation_view(text) is not text
    assert segmentation_input_view(text) is text


@pytest.mark.parametrize("value", ["0", ""])
def test_flags_off_leave_every_reading_unchanged(monkeypatch, value):
    for name in (FLAG, INPUT_FLAG):
        monkeypatch.setenv(name, value)
    for text, _member in MID_SENTENCE:
        assert segmentation_view(text) is text
        assert segmentation_input_view(text) is text
        cuts = [c.end() for c in clause_cues.SENTENCE_BREAK.finditer(text)]
        assert span_start(text, len(text) - 2) == (cuts[-1] if cuts else 0)


# Adversarial cases: a plain sentence end that looks like a member must still split.
@pytest.mark.parametrize(
    ("first", "second"),
    [
        ("The vorn rig ran near Paradise, CA.", "The zorvex sample reached 40 mm."),
        ("Vorn data were taken from Okafor, op. cit.", "The present zorvex run reached 12 mm."),
        ("The answer was no.", "A second test ran."),
        ("The dominant product was NO.", "A zorvex flame then reached 40 mm."),
        ("The vorn trace was no.", "MCMC sampling of the cell followed."),
        ("The vorn trace was no.\n", "A second test ran."),
        ("The vorn trace was no.\n\n", "A second test ran."),
        ("The sample burned after 60 sec.", "A flame of 2 cm formed."),
        ("The vorn trace is in ref.", "A second test ran."),
        ("The vorn trace was dated p.", "A second test ran."),
        ("Flame spread was studied by Okafor et al.", "12 zorvex samples then reached 40 mm."),
        ("The vorn cell was hot.", "Did the zorvex rig mix?"),
    ],
)
def test_real_sentence_ends_that_look_like_members_still_split(on, first, second):
    text = first + (" " if not first.endswith("\n") else "") + second
    if second[0].isupper():
        assert span_start(text, len(text) - 2) == len(text) - len(second)
    assert not abbreviation_period(text, len(first.rstrip()) - 1)


@pytest.mark.parametrize(
    "text",
    [
        "see Fig. A and the vorn cell",
        "see Vol. IV and the vorn cell",
        "see Eq. (2) and the vorn cell",
        "see ch. iv and the vorn cell",
        "see Sec. 3 and the vorn cell",
        "see Ref. 5 and the vorn cell",
        "Okafor et al. 12, then the vorn cell",
        "Okafor et al. 2010 then the vorn cell",
        "Okafor, Ca. 40 mm, and the vorn cell",
    ],
)
def test_real_members_are_still_masked(text):
    assert MASK in mask_abbreviation_periods(text)


def test_lowercase_roman_does_not_match_ordinary_words(on):
    for word in ("did", "mild", "mix", "civil"):
        text = f"The vorn cell ran in fig. {word} the rig."
        assert not abbreviation_period(text, text.index("fig.") + 3)


def test_the_view_pattern_matches_the_printed_text(on, monkeypatch):
    pattern = statement_integrity.POINTER
    match = pattern.search("the symbols, cf. Zorvex, are the vorn cell data")
    assert match.string == "the symbols, cf. Zorvex, are the vorn cell data"
    assert match.group() == match[0]
    import re

    from nasa_fire_ai.ingestion.abbreviations import ViewPattern

    rx = ViewPattern(re.compile(r"(?P<w>vorn)[^.]*?(cell)"))
    text = "vorn rig, cf. zorvex cell"
    assert rx.sub(r"<\g<w>>", text) == "<vorn>"
    monkeypatch.setenv(FLAG, "0")
    assert rx.sub(r"<\g<w>>", text) == text  # the window stops at "cf." with the flag off
    assert rx.sub(r"<\g<w>>", "vorn rig cell") == "<vorn>"
    assert rx.sub(r"<\2>", "vorn x cell") == "<cell>"
