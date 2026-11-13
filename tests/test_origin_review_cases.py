"""The adversarial review's cases for SCIENCE_ORIGIN_CHECK, with the result under the broad rule.

Each row is a sentence, the value, whether the value is the cited work's (C) or this study's (U),
whether the reference list is numbered, and whether the check holds a value marked current.
Every cited value that prints a marker in its sentence is held. A cited value with no marker in
its own sentence passes: the check reads markers, not wording (the documented residual R-1: author
names without a marker, a flattened footnote digit, a marker in the sentence before). A current
value beside a marker is held unless its clause binds it to this study (the accepted false holds,
counted in the replay). Invented text only.
"""

import pytest
from test_value_origin import NUMBERED, REFERENCES, printed_check

# (id, sentence, value, truth, numbered list, held)
CASES = [
    (
        "p-prev_clause_semicolon",
        "In [2] the cord was tested; it had a smolder time of 12 s.",
        "12",
        "C",
        False,
        True,
    ),
    (
        "p-prev_clause_and",
        "The cord was tested in [2] and it had a smolder time of 12 s.",
        "12",
        "C",
        False,
        True,
    ),
    (
        "p-prev_clause_comma_and",
        "The cord was tested in [2], and it had a smolder time of 12 s.",
        "12",
        "C",
        False,
        True,
    ),
    (
        "p-distant_subject",
        "The cords of Okafor [2], after drying for a week and conditioning, had a smolder time of 12 s.",
        "12",
        "C",
        False,
        True,
    ),
    (
        "p-distant_subject2",
        (
            "The waxed cords tested by Okafor [2] in a sealed hall over two weeks of conditioning had a "
            "smolder time of 12 s."
        ),
        "12",
        "C",
        False,
        True,
    ),
    ("p-et_al_noBracket", "Okafor et al. reported a smolder time of 12 s.", "12", "C", False, True),
    ("p-two_authors", "Okafor and Varga found a smolder time of 12 s.", "12", "C", False, True),
    (
        "p-author_alone",
        "Okafor found a smolder time of 12 s for waxed cords.",
        "12",
        "C",
        False,
        True,
    ),
    # N1 rule corrected: a reference-list possessive anchors; flipped from a known residual to held.
    ("p-author_poss", "Okafor's cords smoldered for 12 s.", "12", "C", False, True),
    ("p-they_found", "They found a smolder time of 12 s for waxed cords.", "12", "C", False, False),
    (
        "p-as_reported_prev",
        "As reported previously, the waxed cords smoldered for 12 s.",
        "12",
        "C",
        False,
        False,
    ),
    (
        "p-as_reported_prev2",
        "The waxed cords smoldered for 12 s, as reported previously.",
        "12",
        "C",
        False,
        False,
    ),
    (
        "p-earlier_work",
        "In earlier work the waxed cords smoldered for 12 s.",
        "12",
        "C",
        False,
        False,
    ),
    (
        "p-prev_sentence",
        "Okafor [2] tested waxed cords. The smolder time was 12 s.",
        "12",
        "C",
        False,
        False,
    ),
    (
        "p-prev_sentence_they",
        "Okafor [2] tested waxed cords. They reported a smolder time of 12 s.",
        "12",
        "C",
        False,
        False,
    ),
    (
        "p-table_cited",
        "Table 3 lists the smolder time of waxed cords as 12 s.",
        "12",
        "C",
        False,
        False,
    ),
    (
        "p-caption_cited",
        "Fig. 4. Smolder time of waxed cords, 12 s (data from [2]).",
        "12",
        "C",
        False,
        True,
    ),
    (
        "p-caption_cited2",
        "Fig. 4. Smolder time of waxed cords (12 s), adapted from [2].",
        "12",
        "C",
        False,
        True,
    ),
    (
        "p-relative",
        "The cords, which Okafor [2] waxed by hand, smoldered for 12 s.",
        "12",
        "C",
        False,
        True,
    ),
    ("p-relative2", "Okafor [2] used cords that smoldered for 12 s.", "12", "C", False, True),
    (
        "p-relative3",
        "The cords that were studied in [2] smoldered for 12 s.",
        "12",
        "C",
        False,
        True,
    ),
    (
        "p-fronted_whereas",
        "Whereas [2] found 12 s, the present cords smoldered for 30 s.",
        "12",
        "C",
        False,
        True,
    ),
    (
        "p-fronted_whereas_v2",
        "Whereas [2] found a smolder time of 12 s for waxed cords, ours smoldered for 30 s.",
        "12",
        "C",
        False,
        True,
    ),
    (
        "p-fronted_according",
        "According to [2], waxed cords smolder for 12 s.",
        "12",
        "C",
        False,
        True,
    ),
    ("p-fronted_in", "In [2], waxed cords smoldered for 12 s.", "12", "C", False, True),
    (
        "p-fronted_following",
        "Following Okafor [2], waxed cords smoldered for 12 s.",
        "12",
        "C",
        False,
        True,
    ),
    ("p-paren_see_after", "Waxed cords smoldered for 12 s (see [2]).", "12", "C", False, True),
    (
        "p-paren_see_after_clause",
        "Waxed cords smoldered for 12 s in a sealed hall (see [2] for details).",
        "12",
        "C",
        False,
        True,
    ),
    (
        "p-sentence_end_marker",
        "Waxed cords smoldered for 12 s in a sealed hall [2].",
        "12",
        "C",
        False,
        True,
    ),
    (
        "p-footnote_flat",
        "Waxed cords smoldered for 12 s in a sealed hall2.",
        "12",
        "C",
        False,
        False,
    ),
    (
        "p-footnote_flat_word",
        "Waxed cords smoldered for 12 s according to Okafor2.",
        "12",
        "C",
        False,
        False,
    ),
    (
        "p-footnote_super",
        "Waxed cords smoldered for 12 s in a sealed hall².",
        "12",
        "C",
        False,
        True,
    ),
    ("p-footnote_super_short", "Waxed cords smoldered for 12 s².", "12", "C", False, False),
    ("p-numbered_paren", "Waxed cords smoldered for 12 s (2).", "12", "C", True, True),
    (
        "p-method_marker",
        "Using the drop rig of [2], the waxed cords smoldered for 12 s.",
        "12",
        "C",
        False,
        True,
    ),
    (
        "p-method_marker_np",
        "The drop rig [2] gave a smolder time of 12 s for waxed cords.",
        "12",
        "C",
        False,
        True,
    ),
    (
        "p-colon",
        "Okafor [2] reported the following: a smolder time of 12 s.",
        "12",
        "C",
        False,
        True,
    ),
    (
        "p-reported_by_after",
        "Waxed cords smoldered for 12 s, a value reported by Okafor [2].",
        "12",
        "C",
        False,
        True,
    ),
    (
        "p-which_was_reported",
        "Waxed cords smoldered for 12 s, which was reported in [2].",
        "12",
        "C",
        False,
        True,
    ),
    ("p-as_found_in", "Waxed cords smoldered for 12 s, as found in [2].", "12", "C", False, True),
    (
        "p-this_was_shown",
        "This was shown in [2], where waxed cords smoldered for 12 s.",
        "12",
        "C",
        False,
        True,
    ),
    (
        "p-but",
        "Okafor [2] did not condition the cords, but they smoldered for 12 s.",
        "12",
        "C",
        False,
        True,
    ),
    (
        "p-while",
        "Okafor [2] waxed the cords while they smoldered for 12 s.",
        "12",
        "C",
        False,
        True,
    ),
    (
        "p-previous_study",
        "The previous study found that waxed cords smoldered for 12 s.",
        "12",
        "C",
        False,
        False,
    ),
    ("p-author_year_np", "Okafor (1993) measured a smolder time of 12 s.", "12", "C", False, True),
    (
        "p-author_year_paren",
        "A smolder time of 12 s was measured for waxed cords (Okafor, 1993).",
        "12",
        "C",
        False,
        True,
    ),
    ("p-ref_dot", "Ref. 2 gives a smolder time of 12 s.", "12", "C", False, True),
    (
        "p-they_then",
        "Okafor [2] waxed the cords. Then they measured 12 s.",
        "12",
        "C",
        False,
        False,
    ),
    (
        "p-demonstrated_that",
        "Okafor [2] demonstrated that waxed cords smolder for 12 s.",
        "12",
        "C",
        False,
        True,
    ),
    (
        "p-showed_that_long",
        "It was shown by Okafor [2] in a sealed hall that waxed cords smolder for 12 s.",
        "12",
        "C",
        False,
        True,
    ),
    (
        "p-linewrap_cont",
        "Okafor [2] measured the waxed cords in a sealed hall and found that\nthey smoldered for 12 s.",
        "12",
        "C",
        False,
        True,
    ),
    (
        "p-cur_vs_cited",
        "Our cords smoldered for 30 s, compared with 12 s in [2].",
        "30",
        "U",
        False,
        False,
    ),
    (
        "p-cur_after_whereas",
        "Whereas [2] found 12 s, the present cords smoldered for 30 s.",
        "30",
        "U",
        False,
        True,
    ),
    (
        "p-cur_method",
        "Using the drop rig of [2], we measured a smolder time of 30 s.",
        "30",
        "U",
        False,
        False,
    ),
    ("p-cur_method_np", "The drop rig [2] was run at 30 s intervals.", "30", "U", False, True),
    (
        "p-cur_procedure_in",
        "Cords were conditioned for 30 s as described in [2].",
        "30",
        "U",
        False,
        True,
    ),
    (
        "p-cur_procedure_following",
        "Cords were conditioned for 30 s following [2].",
        "30",
        "U",
        False,
        True,
    ),
    (
        "p-cur_std",
        "Cords were conditioned for 30 s per the procedure of Okafor [2].",
        "30",
        "U",
        False,
        True,
    ),
    ("p-cur_agree", "The cords smoldered for 30 s, in agreement with [2].", "30", "U", False, True),
    (
        "p-cur_agree_noComma",
        "The cords smoldered for 30 s in agreement with [2].",
        "30",
        "U",
        False,
        True,
    ),
    (
        "p-cur_than",
        "The cords smoldered for 30 s, longer than reported in [2].",
        "30",
        "U",
        False,
        True,
    ),
    (
        "p-cur_which_longer",
        "The cords smoldered for 30 s, which is longer than the 12 s in [2].",
        "30",
        "U",
        False,
        True,
    ),
    (
        "p-cur_et_al_method",
        "The cords were waxed for 30 s by the method of Okafor et al.",
        "30",
        "U",
        False,
        True,
    ),
    ("p-cur_and_noComma", "We measured 30 s and Okafor [2] measured 12 s.", "30", "U", False, True),
    ("p-cur_but", "We measured 30 s but [2] measured 12 s.", "30", "U", False, True),
    ("p-cur_paren", "The cords smoldered for 30 s (cf. 12 s in [2]).", "30", "U", False, True),
    ("p-cur_area", "The hall was held at 30 m² of floor area.", "30", "U", False, False),
    (
        "p-cur_et_al_compare",
        "The cords smoldered for 30 s, twice the value of Okafor et al.",
        "30",
        "U",
        False,
        True,
    ),
    (
        "p-cur_like_et_al",
        "Like Okafor et al., we found that cords smoldered for 30 s.",
        "30",
        "U",
        False,
        True,
    ),
    (
        "p-cur_ref_holder",
        "The cords were mounted in the holder of Ref. 2 and smoldered for 30 s.",
        "30",
        "U",
        False,
        True,
    ),
    (
        "p-cur_ref_holder_noAnd",
        "The cords mounted in the holder of Ref. 2 smoldered for 30 s.",
        "30",
        "U",
        False,
        True,
    ),
    ("p-cur_kx_standard", "Cords were held at 30 C per KX-9 [5].", "30", "U", False, True),
    ("p-cur_super_note", "Cords smoldered for 30 s at the reduced draft³.", "30", "U", False, True),
    (
        "p-cur_agree_et_al",
        "These 30 s smolder times agree with those of Okafor et al. for waxed cords.",
        "30",
        "U",
        False,
        True,
    ),
    (
        "p-cur_rig_after",
        "The cords smoldered for 30 s in the drop rig [2].",
        "30",
        "U",
        False,
        True,
    ),
    (
        "p-cur_rig_of",
        "The cords smoldered for 30 s in the drop rig of Okafor [2].",
        "30",
        "U",
        False,
        True,
    ),
    (
        "p-cur_extends",
        "This work extends [2] with cords that smoldered for 30 s.",
        "30",
        "U",
        False,
        True,
    ),
    ("p-cur_unlike", "Unlike [2], our cords smoldered for 30 s.", "30", "U", False, False),
    (
        "p-cur_same_as",
        "Cords were cut to 30 mm, the same length as in [2].",
        "30",
        "U",
        False,
        True,
    ),
    (
        "p-cur_based_on",
        "Based on [2], the cords were conditioned for 30 s.",
        "30",
        "U",
        False,
        True,
    ),
    (
        "p-cur_et_al_subjectNP",
        "The holder of Okafor et al. was loaded with 30 cords.",
        "30",
        "U",
        False,
        True,
    ),
    (
        "e-end_marker_noun",
        "The waxed cord had a smolder time of 12 s at high draft [2].",
        "12",
        "C",
        False,
        True,
    ),
    (
        "e-end_marker_superscript",
        "The waxed cord had a smolder time of 12 s at high draft².",
        "12",
        "C",
        False,
        True,
    ),
    (
        "e-cap_participle_fronted",
        "Waxed cord had a smolder time of 12 s, as shown by Okafor [2].",
        "12",
        "C",
        False,
        True,
    ),
    (
        "e-cap_participle_appositive",
        "Waxed cord had a smolder time of 12 s, a value reported by Okafor [2].",
        "12",
        "C",
        False,
        True,
    ),
    (
        "e-but_subject_marker",
        "Our waxed cord had a smolder time of 30 s, but [2] found a smolder time of 12 s.",
        "12",
        "C",
        False,
        True,
    ),
    (
        "e-whereas_subject_marker",
        "Our waxed cord had a smolder time of 30 s whereas [2] found a smolder time of 12 s.",
        "12",
        "C",
        False,
        True,
    ),
    (
        "e-according_fronted",
        "According to [2], the waxed cord had a smolder time of 12 s.",
        "12",
        "C",
        False,
        True,
    ),
    ("e-in_fronted", "In [2], the waxed cord had a smolder time of 12 s.", "12", "C", False, True),
    (
        "e-semicolon",
        "The waxed cord was tested in [2]; it had a smolder time of 12 s.",
        "12",
        "C",
        False,
        True,
    ),
    (
        "e-two_authors_weak",
        "Okafor and Varga found a smolder time of 12 s for the waxed cord.",
        "12",
        "C",
        False,
        True,
    ),
    (
        "e-they_weak",
        "They found a smolder time of 12 s for the waxed cord.",
        "12",
        "C",
        False,
        False,
    ),
    (
        "e-relative_ed_misparse",
        "The waxed cord, which Okafor [2] dipped by hand, smoldered with a smolder time of 12 s.",
        "12",
        "C",
        False,
        True,
    ),
    (
        "e-paren_long_excised",
        "The waxed cord had a smolder time of 12 s (see [2] for details).",
        "12",
        "C",
        False,
        True,
    ),
    (
        "e-wrap_upper_split",
        (
            "The waxed cord in the sealed hall had a smolder time of 12 s, as reported by\n"
            "Okafor and Varga [2]."
        ),
        "12",
        "C",
        False,
        False,
    ),
    (
        "e-wrap_short_split",
        "In [2] the waxed cord\nhad a smolder time of 12 s.",
        "12",
        "C",
        False,
        False,
    ),
    (
        "e-cur_as_described",
        "The waxed cord was conditioned to a smolder time of 30 s as described in [2].",
        "30",
        "U",
        False,
        True,
    ),
    (
        "e-cur_method_et_al",
        "The waxed cord had a smolder time of 30 s by the method of Okafor et al.",
        "30",
        "U",
        False,
        True,
    ),
    (
        "e-cur_holder_ref",
        "The waxed cord mounted in the holder of Ref. 2 had a smolder time of 30 s.",
        "30",
        "U",
        False,
        True,
    ),
    (
        "e-cur_rig_of_author",
        "The waxed cord had a smolder time of 30 s in the drop rig of Okafor [2].",
        "30",
        "U",
        False,
        True,
    ),
    (
        "e-cur_list_wrap",
        (
            "(a) the waxed cord of Okafor [2] dipped by hand in a sealed hall\n"
            "(b) the present waxed cord with a smolder time of 30 s"
        ),
        "30",
        "U",
        False,
        True,
    ),
]


HELD = [c for c in CASES if c[5]]
PASSING_CURRENT = [c for c in CASES if not c[5] and c[3] == "U"]
RESIDUALS = [c for c in CASES if not c[5] and c[3] == "C"]


def read(case):
    return printed_check(
        case[1], case[2], NUMBERED if case[4] else REFERENCES, value_study="current"
    )


@pytest.mark.parametrize("case", [pytest.param(c, id=c[0]) for c in HELD])
def test_the_review_case_is_held_under_the_broad_rule(case):
    record = read(case)
    assert record["status"] != "SOURCE_SUPPORTED", record["origin"]
    # the same value, marked only through its subject, reads the same
    through_subject = printed_check(
        case[1], case[2], NUMBERED if case[4] else REFERENCES, value_study=None
    )
    assert through_subject["status"] == record["status"]


@pytest.mark.parametrize("case", [pytest.param(c, id=c[0]) for c in PASSING_CURRENT])
def test_the_current_case_stays_supported(case):
    assert read(case)["status"] == "SOURCE_SUPPORTED"


@pytest.mark.parametrize("case", [pytest.param(c, id="known_residual_" + c[0]) for c in RESIDUALS])
def test_known_residual(case):
    """Known residual of the cited-value origin check: a cited value without a marker in its
    sentence passes as current; covered only by condition (2) of the 3.2 freeze (manual count in
    the phase-2 run). A fix must flip this test deliberately."""
    record = read(case)
    assert record["status"] == "SOURCE_SUPPORTED", record["origin"]
    assert not any(
        a["strength"] == "strong" for o in record["origin"]["occurrences"] for a in o["anchors"]
    )


def test_no_cited_value_with_a_marker_in_its_sentence_passes_as_current():
    leaks = [
        c[0]
        for c in CASES
        if c[3] == "C"
        and not c[5]
        and any(
            a["strength"] == "strong"
            for o in read(c)["origin"]["occurrences"]
            for a in o["anchors"]
        )
    ]
    assert leaks == []
