"""SCIENCE_ORIGIN_CHECK, final bounded round: the second review's cases and the six structural fixes.

Fixes under test (FINAL_ROUND_ACCEPTANCE.md; fix 3, line breaks through the de-wrap layer, comes
after step 0 and is pending):

1. a strong marker inside the value's phrase, or in a fronted adjunct that opens with in / from /
   according, cancels the self-mention exemption of the broad rule;
2. a superscript after . , ; : ) is a marker;
4. every printed occurrence of the value (number and unit) in the paragraph is judged;
5. a sentence that opens a page is read with the head printed on the page before;
6. a located value span counts only where the value is printed;
7. surnames from the document's own reference list are anchors.

Every row of PROBE is one of the review's probes (the labels of the review group them: B = the
self-mention binders, S = sentence segmentation, T = tables and captions, O = occurrence choice,
F = fail closed, V = the reverse mark) with its result under this round. A cited value that still
passes is a ``known_residual_<shape>`` whose reason is condition (2) of the 3.2 freeze: no marker
and no author is printed where the structure reads, so only the manual count of the phase-2 run
can see it. Invented text only.
"""

import copy
import random
import re

import pytest
from test_value_origin import NUMBERED, REFERENCES

from nasa_fire_ai.ingestion.value_origin import citation_anchors, origin_check

RESIDUAL_REASON = (
    "Freeze 3.2 condition (2): the cited value prints no marker and no author where the structure "
    "reads (sentence, phrase, paragraph, page head); only the manual count of the phase-2 run "
    "sees it."
)


def check(
    body,
    value,
    quote=None,
    study="current",
    subj="current",
    refs=REFERENCES,
    value_spans=None,
    occurrence=0,
    sep="\n\n",
    unit=None,
):
    """origin_check on a supported record whose page is ``body`` + reference list."""
    page = body + sep + refs
    document = {
        "sections": [
            {"title": "References", "evidence_id": "E1", "end": page.index("References") + 10}
        ],
        "segments": [{"evidence_id": "E1", "text": page}],
    }
    quote = body if quote is None else quote
    item = {"subject": "n", "expression": value}
    if unit:
        item["unit"] = unit
    if study:
        item["study"] = study
    record = {"status": "SOURCE_SUPPORTED", "reasons": []}
    if value_spans == "auto":
        qs = page.find(quote)
        found = list(re.finditer(r"(?<![\d.])" + re.escape(value) + r"(?!\d)", quote))
        m = found[occurrence]
        record["quantity_value_spans"] = [
            {"evidence_id": "E1", "start": qs + m.start(), "end": qs + m.end(), "quote": value}
        ]
    elif value_spans is not None:
        record["quantity_value_spans"] = value_spans
    entities = {"n": {"study": subj, "label": "cords", "class_id": "Sample"}}
    span = {"evidence_id": "E1", "start": page.find(quote), "quote": quote}
    origin_check(item, record, [span], entities, document, {"E1": {"text": page}})
    return record


def pages_check(pages, value, offset_in, study="current", unit="s", refs=REFERENCES):
    """origin_check over several printed pages of one source; the value is on page ``offset_in``."""
    texts = list(pages)
    texts[-1] = texts[-1] + "\n\n" + refs
    evidence = {
        f"E{k + 1}": {"evidence_id": f"E{k + 1}", "text": t, "page": k + 1, "source_id": "S"}
        for k, t in enumerate(texts)
    }
    last = f"E{len(texts)}"
    document = {
        "sections": [
            {"title": "References", "evidence_id": last, "end": texts[-1].index("Ref") + 10}
        ],
        "segments": [{"evidence_id": k, "text": e["text"]} for k, e in evidence.items()],
    }
    eid = f"E{offset_in + 1}"
    text = evidence[eid]["text"]
    start = text.index(value)
    item = {"subject": "n", "expression": value, "unit": unit, "study": study}
    record = {
        "status": "SOURCE_SUPPORTED",
        "reasons": [],
        "quantity_value_spans": [
            {"evidence_id": eid, "start": start, "end": start + len(value), "quote": value}
        ],
    }
    entities = {"n": {"study": "current", "label": "cords", "class_id": "Sample"}}
    span = {"evidence_id": eid, "start": 0, "quote": text[: start + len(value) + 3]}
    origin_check(item, record, [span], entities, document, evidence)
    return record


def held(record):
    return record["status"] != "SOURCE_SUPPORTED"


# (id, body, value, quote, kwargs, truth): C = cited work's value, U = this study's value.
# The result under this round is in HELD_NOW / RESIDUAL below.
PROBE = [
    (
        "B-in_ref_we_reported",
        "In [2], we reported a smolder time of 12 s for waxed cords.",
        "12",
        None,
        {},
        "C",
    ),
    (
        "B-in_our_paper_we",
        "In our 1993 paper [2], we measured a smolder time of 12 s.",
        "12",
        None,
        {},
        "C",
    ),
    (
        "B-in_our_earlier_we",
        "In our earlier work [2], we found a smolder time of 12 s.",
        "12",
        None,
        {},
        "C",
    ),
    (
        "B-as_in_our_earlier",
        "As in our earlier work [2], we found a smolder time of 12 s.",
        "12",
        None,
        {},
        "C?",
    ),
    ("B-we_note_that", "We note that [2] measured a smolder time of 12 s.", "12", None, {}, "C"),
    (
        "B-we_previously_reported",
        "We previously reported [2] a smolder time of 12 s for waxed cords.",
        "12",
        None,
        {},
        "C",
    ),
    (
        "B-we_have_shown",
        "We have shown [2] that waxed cords smolder for 12 s.",
        "12",
        None,
        {},
        "C",
    ),
    (
        "B-we_showed_before",
        "We showed before [2] that waxed cords smolder for 12 s.",
        "12",
        None,
        {},
        "C",
    ),
    ("B-our_group_found", "Our group found [2] a smolder time of 12 s.", "12", None, {}, "C"),
    ("B-here_following", "Here, following [2], the smolder time is 12 s.", "12", None, {}, "C?"),
    (
        "B-here_we_recall",
        "Here we recall that Okafor [2] measured a smolder time of 12 s.",
        "12",
        None,
        {},
        "C",
    ),
    (
        "B-we_recall_the",
        "We recall the smolder time of 12 s measured by Okafor [2].",
        "12",
        None,
        {},
        "C",
    ),
    ("B-in_ref_2_we", "In Ref. 2 we measured a smolder time of 12 s.", "12", None, {}, "C"),
    (
        "B-our_prior_paper_2019",
        "Our 2019 study [2] found a smolder time of 12 s.",
        "12",
        None,
        {},
        "C",
    ),
    (
        "B-this_study_cites",
        "This study uses the smolder time of 12 s from [2].",
        "12",
        None,
        {},
        "C",
    ),
    ("B-we_adopt_value", "We adopt a smolder time of 12 s, after Okafor [2].", "12", None, {}, "C"),
    ("B-we_take", "We take the smolder time as 12 s [2].", "12", None, {}, "C"),
    ("B-here_value_from", "Here the smolder time is 12 s, taken from [2].", "12", None, {}, "C"),
    ("B-we_use_previous", "We use 12 s, the smolder time found in [2].", "12", None, {}, "C"),
    (
        "S-paren_after_period",
        "The waxed cords smoldered for 12 s. (Okafor, 1993)",
        "12",
        None,
        {},
        "C",
    ),
    (
        "S-numbered_after_period",
        "The waxed cords smoldered for 12 s. (2)",
        "12",
        None,
        {"refs": NUMBERED},
        "C",
    ),
    ("S-bracket_after_period", "The waxed cords smoldered for 12 s. [2]", "12", None, {}, "C"),
    (
        "S-super_after_period",
        "The waxed cords smoldered for 12 s.² Next we dried them.",
        "12",
        None,
        {},
        "C",
    ),
    (
        "S-wrap_by_upper",
        "The waxed cord in the sealed hall had a smolder time of 12 s as reported by\nOkafor [2].",
        "12",
        None,
        {},
        "C",
    ),
    (
        "S-wrap_bracket_split",
        "The waxed cord in the sealed hall had a smolder time of 12 s [1,\n2].",
        "12",
        None,
        {},
        "C",
    ),
    ("S-wrap_et_al_short", "Okafor et\nal. measured a smolder time of 12 s.", "12", None, {}, "C"),
    (
        "S-wrap_in_short",
        "In Okafor [2] the cords\nhad a smolder time of 12 s.",
        "12",
        None,
        {},
        "C",
    ),
    (
        "S-wrap_upper_mid",
        "The cords tested by Okafor [2] in the hall of the\nNational Fire Lab had a smolder time of 12 s.",
        "12",
        None,
        {},
        "C",
    ),
    (
        "S-abbrev_fig",
        "As in Fig. 2 of Okafor [2], the cords smoldered for 12 s.",
        "12",
        None,
        {},
        "C",
    ),
    ("S-eg", "Waxed cords (e.g. Okafor [2]) smoldered for 12 s.", "12", None, {}, "C"),
    (
        "S-question",
        "Did the cords of Okafor [2] smolder? They did! The time was 12 s.",
        "12",
        None,
        {},
        "C",
    ),
    (
        "T-caption_marker",
        "Table 2. Smolder times of waxed cords from the literature [2].\nWaxed cord   12 s\nDry cord   30 s",
        "12",
        "Waxed cord   12 s",
        {},
        "C",
    ),
    (
        "T-caption_et_al",
        "Table 2. Values of Okafor et al.\nWaxed cord   12 s",
        "12",
        "Waxed cord   12 s",
        {},
        "C",
    ),
    (
        "T-row_ref_col",
        "Table 2. Literature values.\nWaxed cord   12 s   [2]",
        "12",
        "Waxed cord   12 s   [2]",
        {},
        "C",
    ),
    (
        "O-two_occ_quote_second",
        "Okafor [2] measured a smolder time of 12 s. That 12 s smolder time is the reference.",
        "12",
        "That 12 s smolder time is the reference.",
        {"unit": "s"},
        "C",
    ),
    (
        "O-two_occ_vs_first",
        "Okafor [2] measured a smolder time of 12 s. That 12 s smolder time is the reference.",
        "12",
        "That 12 s smolder time is the reference.",
        {"value_spans": "auto", "unit": "s"},
        "C",
    ),
    (
        "O-quote_both_valuespan_second",
        "Okafor [2] measured 12 s; the waxed cords smoldered for 12 s.",
        "12",
        None,
        {"value_spans": "auto", "occurrence": 1},
        "C",
    ),
    (
        "O-same_sentence_two",
        "The waxed cords smoldered for 12 s, and Okafor [2] measured 12 s.",
        "12",
        None,
        {"value_spans": "auto", "occurrence": 0},
        "U?",
    ),
    (
        "O-abstract_repeat",
        "Abstract: the waxed cords smoldered for 12 s.\n\nOkafor [2] measured a smolder time of 12 s.",
        "12",
        "Abstract: the waxed cords smoldered for 12 s.",
        {},
        "C?",
    ),
    (
        "F-valuespan_out_of_range",
        "Okafor [2] measured a smolder time of 12 s.",
        "12",
        None,
        {"value_spans": [{"evidence_id": "E1", "start": 99999, "end": 100001}]},
        "C",
    ),
    (
        "F-valuespan_wrong_eid",
        "Okafor [2] measured a smolder time of 12 s.",
        "12",
        None,
        {"value_spans": [{"evidence_id": "E9", "start": 3, "end": 5}]},
        "C",
    ),
    (
        "F-valuespan_points_elsewhere",
        "The cords were dried. Okafor [2] measured a smolder time of 12 s.",
        "12",
        None,
        {"value_spans": [{"evidence_id": "E1", "start": 4, "end": 6}]},
        "C",
    ),
    (
        "F-expression_no_digits",
        "Okafor [2] measured a smolder time of twelve seconds.",
        "twelve",
        None,
        {},
        "C",
    ),
    (
        "F-expression_range",
        "Okafor [2] measured a smolder time of 12-14 s.",
        "12-14",
        None,
        {},
        "C",
    ),
    ("F-expression_sci", "Okafor [2] measured a rate of 1.2 × 10^3 s.", "1.2e3", None, {}, "C"),
    ("F-comma_decimal", "Okafor [2] measured a smolder time of 12,5 s.", "12.5", None, {}, "C"),
    ("F-thin_space", "Okafor [2] measured a count of 12 000 cords.", "12000", None, {}, "C"),
    (
        "V-cited_mark_named_inv",
        "The waxed cords smoldered for 30 s [2] in the present tests.",
        "30",
        None,
        {"study": "cited"},
        "U?",
    ),
]

# Cited values (truth C) that stay supported although a marker or an author is printed: the shapes
# the structure of this round does not read. Each is a known residual, not a pass.
RESIDUAL = {
    "B-as_in_our_earlier": "a comparison head ('as in') opens the sentence: the adjunct compares, it does not locate",
    "B-here_following": "the adjunct opens with an adverb, the marker follows a participle",
    "B-we_adopt_value": "the marker follows the value's phrase in a subordinate adjunct ('after Okafor [2]')",
    "B-here_value_from": "the marker is in a participial supplement after the value's phrase",
    "S-paren_after_period": "the marker opens the next sentence (printed after the full stop)",
    "S-numbered_after_period": "the numbered marker opens the next sentence",
    "S-wrap_by_upper": "line break inside the sentence: fix 3, through the step-0 de-wrap layer, is pending",
    "S-wrap_et_al_short": "line break inside the author phrase: fix 3 pending",
    "S-wrap_upper_mid": "line break after an upper-case run: fix 3 pending",
    "S-question": "the marker is in the question before the value's sentence",
    "T-caption_marker": "the marker is in the table caption, a separate line",
    "T-caption_et_al": "the author is in the table caption, a separate line",
    "O-abstract_repeat": "the other occurrence stands in another paragraph of the page",
}
PASSES_AS_OWN = {"V-cited_mark_named_inv"}  # truth U?: a cited mark on an own value, no harm
FALSE_HOLD = {"O-same_sentence_two"}  # truth U?: the broad rule (accepted false hold)

HELD_NOW = [c for c in PROBE if c[0] not in RESIDUAL and c[0] not in PASSES_AS_OWN]


def run_probe(c):
    _cid, body, value, quote, kw, _ = c
    return check(body, value, quote, **kw)


@pytest.mark.parametrize("case", [pytest.param(c, id=c[0]) for c in HELD_NOW])
def test_the_review_probe_is_held(case):
    record = run_probe(case)
    assert held(record), record["origin"]
    assert record["status"] == "UNRESOLVED"


@pytest.mark.parametrize(
    "case", [pytest.param(c, id="known_residual_" + c[0]) for c in PROBE if c[0] in RESIDUAL]
)
def test_known_residual(case):
    """Known residual: reason in RESIDUAL; condition (2) of the 3.2 freeze. A fix must flip this
    test deliberately."""
    assert case[0] in RESIDUAL and RESIDUAL_REASON
    record = run_probe(case)
    assert not held(record), record["origin"]


@pytest.mark.parametrize("cid", sorted(PASSES_AS_OWN))
def test_the_reverse_mark_stays_supported(cid):
    case = next(c for c in PROBE if c[0] == cid)
    assert not held(run_probe(case))


def test_every_probe_is_accounted_for():
    ids = {c[0] for c in PROBE}
    assert len(ids) == len(PROBE) == 48
    assert set(RESIDUAL) | PASSES_AS_OWN <= ids


# ---- fix 1: a marker in the value's phrase, or in a locating adjunct, cancels the exemption ----
FIX1_HELD = [
    "In [2], we reported a smolder time of 12 s.",
    "In our paper [2] we reported a smolder time of 12 s.",
    "From [2], we take a smolder time of 12 s.",
    "According to [2], we obtained a smolder time of 12 s.",
    "In the study of Okafor [2], we found a smolder time of 12 s.",
    "We previously reported [2] a smolder time of 12 s.",
    "We measured a smolder time of 12 s (see [2]).",
]
FIX1_KEPT = [
    # a comparison head is not a locating adjunct
    "In contrast to [2], we measured a smolder time of 12 s.",
    "In comparison with [2], we measured a smolder time of 12 s.",
    "Unlike [2], we measured a smolder time of 12 s.",
    "Similar to [2], we measured a smolder time of 12 s.",
    # a marker after the clause, outside the value's phrase
    "We measured a smolder time of 12 s; this agrees with [2].",
    "We measured a smolder time of 12 s, compared with 15 s in [2].",
    # a bare marker in a parenthesis after the value is the value's own citation
]


@pytest.mark.parametrize("sentence", FIX1_HELD)
def test_fix1_the_marker_in_the_phrase_or_locating_adjunct_holds(sentence):
    assert held(check(sentence, "12"))


@pytest.mark.parametrize("sentence", FIX1_KEPT)
def test_fix1_a_binder_still_keeps_a_marker_outside_the_phrase(sentence):
    record = check(sentence, "12")
    assert not held(record), record["origin"]


# ---- fix 2: a superscript after . , ; : ) is a marker -------------------------------------------
FIX2_HELD = [
    "The waxed cords smoldered for 12 s.² Next we dried them.",
    "The waxed cords smoldered for 12 s,² and the dry ones for 9 s.",
    "The waxed cords smoldered for 12 s;² the dry ones did not.",
    "The waxed cords (see below) smoldered for 12 s (Okafor and Varga)² in the hall.",
    "The waxed cords smoldered for 12 s.¹² Next we dried them.",
]
FIX2_KEPT = [
    "The waxed cords smoldered for 12 s at 4 W/(m K)² in the hall.",
    "The waxed cords had an area of 12 m² in the hall.",
    "The waxed cords had a rate of 12 (m/s)² in the hall.",
    "The waxed cords had an energy of 12 (J/m)².",
]


@pytest.mark.parametrize("sentence", FIX2_HELD)
def test_fix2_a_superscript_after_punctuation_is_a_marker(sentence):
    record = check(sentence, "12")
    assert held(record), record["origin"]
    anchors = citation_anchors(sentence, {})
    assert any(a["shape"] == "superscript" for a in anchors)


@pytest.mark.parametrize("sentence", FIX2_KEPT)
def test_fix2_an_exponent_is_not_a_marker(sentence):
    record = check(sentence, "12")
    assert not held(record), record["origin"]


# ---- fix 4: every printed occurrence of the value in the paragraph is judged --------------------
def test_fix4_the_cited_occurrence_holds_the_quoted_own_one():
    body = "Okafor [2] measured a smolder time of 12 s. Our cords smoldered for 12 s in the hall."
    record = check(body, "12", "Our cords smoldered for 12 s in the hall.", unit="s")
    assert held(record)
    assert record["origin"]["held_by_other_occurrence"] is True
    assert [o["extra"] for o in record["origin"]["occurrences"]] == [False, True]


def test_fix4_the_quoted_occurrence_alone_holds_without_the_other_flag():
    body = "Okafor [2] measured a smolder time of 12 s. Our cords smoldered for 12 s in the hall."
    record = check(body, "12", "Okafor [2] measured a smolder time of 12 s.", unit="s")
    assert held(record)
    assert record["origin"]["held_by_other_occurrence"] is False


def test_fix4_the_unit_must_match():
    body = "Okafor [2] measured a length of 12 mm. Our cords smoldered for 12 s in the hall."
    record = check(body, "12", "Our cords smoldered for 12 s in the hall.", unit="s")
    assert not held(record), record["origin"]


def test_fix4_a_number_inside_a_marker_is_not_a_value():
    body = "Okafor [12] measured a count. Our cords smoldered for 12 s in the hall."
    record = check(body, "12", "Our cords smoldered for 12 s in the hall.", unit="s")
    assert not held(record), record["origin"]


def test_fix4_another_paragraph_is_not_read():
    body = (
        "Okafor [2] measured a smolder time of 12 s.\n\nOur cords smoldered for 12 s in the hall."
    )
    record = check(body, "12", "Our cords smoldered for 12 s in the hall.", unit="s")
    assert not held(record), record["origin"]


def test_fix4_a_value_without_a_unit_is_read_where_the_same_word_follows():
    body = "Okafor [2] counted 12 cords. We dried 12 cords in the hall. We tested 12 racks."
    record = check(body, "12", "We dried 12 cords in the hall.")
    assert held(record)
    assert record["origin"]["held_by_other_occurrence"] is True
    body = "Okafor [2] counted 12 racks. We dried 12 cords in the hall."
    assert not held(check(body, "12", "We dried 12 cords in the hall."))


def test_fix4_a_cited_mark_is_held_by_an_own_occurrence_too():
    body = "Okafor [2] measured a smolder time of 12 s. We measured a smolder time of 12 s."
    record = check(
        body, "12", "Okafor [2] measured a smolder time of 12 s.", study="cited", unit="s"
    )
    assert held(record)
    assert record["origin"]["held_by_other_occurrence"] is True


def test_fix4_the_other_occurrence_never_lets_a_held_record_pass():
    body = "Okafor [2] measured a smolder time of 12 s. Our cords smoldered for 12 s in the hall."
    only_cited = check(body, "12", "Okafor [2] measured a smolder time of 12 s.", unit="s")
    assert held(only_cited)


# ---- fix 5: a sentence that opens a page carries the head printed on the page before ------------
HEAD = "II. Results\nThe waxed cords tested by Okafor [2] in the sealed hall over two weeks"
TAIL = "had a smolder time of 12 s. The present cords were dried."


def test_fix5_the_page_head_is_read():
    record = pages_check([HEAD, TAIL], "12", 1)
    assert held(record), record["origin"]
    first = record["origin"]["occurrences"][0]
    assert first["continued_from"]["evidence_id"] == "E1"


def test_fix5_a_page_that_starts_a_sentence_has_no_head():
    record = pages_check([HEAD + ".", "The waxed cords had a smolder time of 12 s."], "12", 1)
    assert not held(record), record["origin"]
    record = pages_check([HEAD, "The waxed cords had a smolder time of 12 s."], "12", 1)
    assert not held(record), record["origin"]


def test_fix5_a_head_without_a_marker_does_not_hold():
    head = "II. Results\nThe waxed cords dried in the sealed hall over two weeks"
    record = pages_check([head, TAIL], "12", 1)
    assert not held(record), record["origin"]


def test_fix5_pages_of_another_source_are_not_joined():
    texts = [HEAD, TAIL + "\n\nReferences\n[2] Okafor, N., Glow decay, 1993.\n"]
    evidence = {
        "E1": {"evidence_id": "E1", "text": texts[0], "page": 1, "source_id": "S1"},
        "E2": {"evidence_id": "E2", "text": texts[1], "page": 2, "source_id": "S2"},
    }
    document = {
        "sections": [],
        "segments": [{"evidence_id": k, "text": e["text"]} for k, e in evidence.items()],
    }
    start = texts[1].index("12")
    item = {"subject": "n", "expression": "12", "unit": "s", "study": "current"}
    record = {
        "status": "SOURCE_SUPPORTED",
        "reasons": [],
        "quantity_value_spans": [
            {"evidence_id": "E2", "start": start, "end": start + 2, "quote": "12"}
        ],
    }
    entities = {"n": {"study": "current", "label": "cords", "class_id": "Sample"}}
    origin_check(
        item,
        record,
        [{"evidence_id": "E2", "start": 0, "quote": TAIL}],
        entities,
        document,
        evidence,
    )
    assert not held(record), record["origin"]


# ---- fix 6: the value must be printed at the located value span ---------------------------------
def test_fix6_a_span_that_points_elsewhere_is_not_a_place_of_the_value():
    body = "The cords were dried. Okafor [2] measured a smolder time of 12 s."
    record = check(body, "12", value_spans=[{"evidence_id": "E1", "start": 4, "end": 6}])
    assert held(record)
    assert record["origin"]["occurrences"][0]["basis"] == "CITATION_IN_VALUE_PHRASE"


def test_fix6_a_span_that_prints_another_number_is_not_a_place_of_the_value():
    body = "The cords smoldered for 13 s. Okafor [2] measured a smolder time of 12 s."
    start = body.index("13")
    record = check(
        body, "12", value_spans=[{"evidence_id": "E1", "start": start, "end": start + 2}]
    )
    assert held(record)
    assert record["origin"]["occurrences"][0]["sentence"]["start"] > 0


def test_fix6_a_span_in_the_middle_of_a_number_is_not_the_value():
    body = "Okafor [2] measured a smolder time of 112 s."
    start = body.index("112") + 1
    record = check(
        body, "12", value_spans=[{"evidence_id": "E1", "start": start, "end": start + 2}]
    )
    assert held(record)  # no place -> read in the quote -> not located -> held (fail closed)


def test_fix6_a_span_that_prints_the_value_is_a_place():
    body = "The waxed cords smoldered for 12 s in the hall."
    start = body.index("12")
    record = check(
        body, "12", value_spans=[{"evidence_id": "E1", "start": start, "end": start + 2}]
    )
    assert not held(record), record["origin"]


def test_fix6_a_value_that_is_nowhere_printed_is_held():
    record = check("The waxed cords smoldered for 15 s in the hall.", "12")
    assert held(record)
    assert record["origin"]["occurrences"][0]["basis"] == "SPAN_NOT_LOCATED_IN_EVIDENCE"


# ---- fix 7: surnames from the document's own reference list are anchors -------------------------
FIX7_HELD = [
    "Okafor found a smolder time of 12 s for waxed cords.",
    "Okafor and Varga found a smolder time of 12 s.",
    "The waxed cords of Okafor smoldered for 12 s.",
    "Varga reported a smolder time of 12 s.",
]


@pytest.mark.parametrize("sentence", FIX7_HELD)
def test_fix7_a_reference_list_surname_holds_a_current_value(sentence):
    record = check(sentence, "12")
    assert held(record), record["origin"]
    assert any(
        a["shape"] == "reference_author"
        for o in record["origin"]["occurrences"]
        for a in o["anchors"]
    )


def test_fix7_a_name_that_is_not_in_the_list_is_not_an_anchor():
    assert not held(check("Zhang found a smolder time of 12 s for waxed cords.", "12"))


def test_fix7_a_common_word_that_opens_the_sentence_is_not_an_author():
    refs = "References\n[1] Frame, P., Cord ember study, 1985.\n"
    assert not held(check("Frame tests of the waxed cords gave 12 s.", "12", refs=refs))
    assert held(check("Frame reported a smolder time of 12 s.", "12", refs=refs))
    assert held(check("The waxed cords of Frame smoldered for 12 s.", "12", refs=refs))


def test_fix7_a_binder_keeps_a_name_outside_the_phrase():
    record = check("We measured a smolder time of 12 s, as did Okafor.", "12")
    assert not held(record), record["origin"]


def test_fix7_the_name_changes_nothing_for_a_cited_mark():
    """A cited mark is read as before (row 7: no marker in the phrase); the surname is not a pass."""
    record = check("Okafor found a smolder time of 12 s for waxed cords.", "12", study="cited")
    assert record["origin"]["basis"] == "NO_CITATION_IN_VALUE_PHRASE"


# ---- never accepts more (the fuzz of the acceptance (a), in miniature) --------------------------
TOK = [
    "Waxed",
    "cords",
    "the",
    "of",
    "[2]",
    "(2)",
    "(",
    ")",
    ",",
    ";",
    ":",
    ".",
    "and",
    "but",
    "which",
    "12",
    "12 s",
    "s",
    "Okafor",
    "Varga",
    "et",
    "al.",
    "we",
    "our",
    "this",
    "study",
    "compared",
    "with",
    "\n",
    "\n\n",
    "²",
    "s.²",
    ")²",
    "as",
    "reported",
    "in",
    "Ref.",
    "(Okafor, 1993)",
    "than",
    "unlike",
    "smoldered",
    "for",
    "e.g.",
    "[",
    "]",
    "Fig.",
    "from",
    "according",
    "to",
    "here",
    "present",
    "earlier",
    "previously",
    "found",
    "12.5",
    "112",
    "1.12",
]


@pytest.mark.parametrize("seed", [3, 11])
def test_the_check_never_accepts_more_and_never_raises(seed):
    rng = random.Random(seed)
    for _ in range(400):
        pages = []
        for _page in range(rng.choice([1, 2])):
            words = [rng.choice(TOK) for _ in range(rng.randint(1, 30))]
            if "12" not in words and "12 s" not in words:
                words.insert(rng.randint(0, len(words)), rng.choice(["12", "12 s"]))
            pages.append(" ".join(words))
        if len(pages) == 2 and rng.random() < 0.6:
            pages[1] = pages[1][:1].lower() + pages[1][1:]
        pages[-1] += "\n\n" + REFERENCES
        evidence = {
            f"E{k + 1}": {"evidence_id": f"E{k + 1}", "text": t, "page": k + 1, "source_id": "S"}
            for k, t in enumerate(pages)
        }
        document = {
            "sections": [
                {
                    "title": "References",
                    "evidence_id": f"E{len(pages)}",
                    "end": pages[-1].index("References") + 10,
                }
            ],
            "segments": [{"evidence_id": k, "text": e["text"]} for k, e in evidence.items()],
        }
        eid = rng.choice(list(evidence))
        text = evidence[eid]["text"]
        expression = rng.choice(["12", "12", "12.5", "1.12"])
        item = {"subject": "n", "expression": expression}
        if rng.random() < 0.7:
            item["unit"] = rng.choice(["s", "", "mm"])
        mark = rng.choice(["current", "cited", None])
        if mark:
            item["study"] = mark
        entities = {
            "n": {
                "study": rng.choice(["current", "cited", None]),
                "label": "cords",
                "class_id": "Sample",
            }
        }
        record = {
            "status": rng.choice(["SOURCE_SUPPORTED"] * 5 + ["UNRESOLVED", "REJECTED"]),
            "reasons": [],
        }
        found = [m for m in range(len(text)) if text.startswith(expression, m)]
        if rng.random() < 0.5 and found:
            a = rng.choice(found)
            record["quantity_value_spans"] = [
                {"evidence_id": eid, "start": a, "end": a + len(expression), "quote": expression}
            ]
        a = rng.choice(found) if found else 0
        spans = [{"evidence_id": eid, "start": a, "quote": text[a : a + rng.randint(1, 60)]}]
        before = copy.deepcopy(record)
        after = copy.deepcopy(record)
        origin_check(item, after, spans, entities, document, evidence)
        again = copy.deepcopy(record)
        origin_check(item, again, spans, entities, document, evidence)
        assert after == again
        origin = after.pop("origin")
        if before["status"] != "SOURCE_SUPPORTED":
            assert after == before and origin["decision"] == "NOT_RUN"
        elif after["status"] == "SOURCE_SUPPORTED":
            assert after == before and origin["decision"] == "PASS"
        else:
            assert after["status"] == "UNRESOLVED" and origin["decision"] == "HOLD"
            assert set(before["reasons"]) <= set(after["reasons"])
