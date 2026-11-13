"""SCIENCE_ORIGIN_CHECK, final round, fix 7 for shape N1: a reference-list surname as an anchor.

A surname from the document's own reference list is an anchor when it is (i) the subject of a
finite verb (any verb: read from the closed classes and the form of the clause, no verb list),
(ii) followed by "et al.", (iii) followed by "and colleagues" / "and co-workers", or (iv) followed
by a year in parentheses, or (v) a possessive ("Name's data showed ..."). A surname that is also an
ordinary sentence-initial word ("Long exposure", "White deposits", "Hill-type fits") is not an
author there; "Name's noun" is no author where the repo's registries already hold it as a term.

The residual shapes N2-N16 of the third verification are ``known_residual_<shape>`` tests: the
cited value prints no marker and no author where the structure reads (condition (2) of the 3.2
freeze), so only the manual count of the phase-2 run sees it. Invented text only.
"""

import pytest
from test_origin_final_round import check, held, pages_check

RESIDUAL_REASON = (
    "Freeze 3.2 condition (2): the cited value prints no marker and no author where the structure "
    "reads; only the manual count of the phase-2 run sees it."
)

COMMON = (
    "References\n"
    "[1] Young, T., Cord stiffness, 1987.\n"
    "[2] Long, R., Smolder of waxed cords, 1991.\n"
    "[3] White, K., Char depth of cords, 1999.\n"
    "[4] Hill, A., Creep of hemp, 2003.\n"
)
FALSE_HOLDS = [
    "Long exposure raised the smolder time to 30 s.",
    "White deposits covered the cord after 30 s.",
    "Hill-type fits gave 30 s.",
]


@pytest.mark.parametrize("sentence", FALSE_HOLDS)
def test_a_surname_that_is_an_ordinary_word_is_not_held(sentence):
    record = check(sentence, "30", refs=COMMON)
    assert not held(record), record["origin"]


def test_an_eponymous_term_of_the_registry_is_not_held(monkeypatch):
    from nasa_fire_ai.ingestion import value_origin

    sentence = "Young's modulus of the cord was 3 GPa."
    # No registry term of this shape exists in the repo: the possessive anchors (old expectation:
    # not held; direction: now holds).
    assert held(check(sentence, "3", refs=COMMON))
    monkeypatch.setattr(value_origin, "_TERM_KEYS", {"young s modulus"})
    assert not held(check(sentence, "3", refs=COMMON))


NAMES = (
    "References\n"
    "[1] Haldorsen, T., Ember creep in jute ropes, 1988.\n"
    "[2] Quintero, L., Wick char rates under draft, 2004.\n"
    "[3] Abernethy, J. and Pellegrini, S., Glow fronts in sisal, 1999.\n"
)
POSITIVE = [
    # (i) the subject of a finite verb, any verb
    "Haldorsen measured a creep time of 14 s for jute.",
    "Haldorsen gives a creep time of 14 s for jute.",
    "Haldorsen obtained 14 s for jute.",
    "Haldorsen previously recorded a creep time of 14 s.",
    "Haldorsen was able to show 14 s for jute.",
    "Abernethy and Pellegrini derived a creep time of 14 s.",
    "Quintero, Haldorsen and Abernethy observed a creep time of 14 s.",
    # (ii) et al.
    "Haldorsen et al. creep time for jute: 14 s.",
    "Quintero et al. 14 s was the creep time for jute.",
    # (iii) and colleagues / co-workers
    "Haldorsen and colleagues, creep time of jute: 14 s.",
    "Quintero and co-workers measured a creep time of 14 s.",
    # (iv) a year in parentheses
    "Haldorsen (1988) creep time of jute: 14 s.",
    "Quintero (2004) measured a creep time of 14 s.",
]


@pytest.mark.parametrize("sentence", POSITIVE)
def test_a_reference_list_author_in_an_author_position_holds_a_current_value(sentence):
    record = check(sentence, "14", refs=NAMES)
    assert held(record), record["origin"]
    assert any(
        a["shape"] in {"reference_author", "author_year", "et_al"}
        for o in record["origin"]["occurrences"]
        for a in o["anchors"]
    )


def test_the_surname_alone_without_an_author_position_is_not_an_anchor():
    assert not held(check("Haldorsen cords of jute crept for 14 s.", "14", refs=NAMES))


def test_a_possessive_is_an_author_position():
    # N1 rule corrected: "Haldorsen's cords crept for 14 s." is a cited value (old: not held).
    assert held(check("Haldorsen's cords crept for 14 s.", "14", refs=NAMES))


# ---- known residuals N2-N16 of the third verification --------------------------------------------
LIST = (
    "References\n"
    "[1] Haldorsen, T., Ember creep in jute ropes, 1988.\n"
    "[2] Quintero, L., Wick char rates under draft, 2004.\n"
    "[3] Abernethy, J. and Pellegrini, S., Glow fronts in sisal, 1999.\n"
    "[4] Ødegård, K., Smoulder of tarred hemp, 2011.\n"
)
NUMLESS = "References\nNone listed.\n"
RESIDUAL = {
    "N1_year_without_parentheses": ("Haldorsen 1988 measured a creep time of 14 s for jute.", LIST),
    "N4_nonascii_surname_year": ("Ødegård (2011) measured a creep time of 14 s.", LIST),
    "N4_nonascii_surname_bare": (
        "As Ødegård measured, the creep time of tarred hemp is 14 s.",
        LIST,
    ),
    "N5_author_not_in_list": ("Fennimore measured a creep time of 14 s for jute.", LIST),
    "N5_possessive_not_in_list": ("Fennimore's creep time for jute was 14 s.", LIST),
    "N6_refs_without_period": ("The creep time of jute is 14 s (refs 1-2).", LIST),
    "N6_reference_word": ("The creep time of jute is 14 s (reference 2).", LIST),
    "N6_doi": ("The creep time of jute is 14 s (doi:10.9999/jute.14).", LIST),
    "N6_url": ("The creep time of jute is 14 s (see www.jutelab.example/report).", LIST),
    "N7_number_without_numbered_list": ("The creep time of jute is 14 s (2).", NUMLESS),
    "N8_keyed_marker_not_in_list": ("The creep time of jute is 14 s [Q04].", LIST),
    "N9_superscript_after_space": ("The creep time of jute is 14 s ².", LIST),
    "N10_named_campaign": ("The KESTREL-2 campaign measured a creep time of 14 s for jute.", LIST),
    "N10_named_facility": ("At the Brandvik drop tower the creep time of jute was 14 s.", LIST),
    "N10_named_standard": ("The creep time of jute specified by ASTM D9999 is 14 s.", LIST),
    "N11_year_and_place": ("In the 1988 campaign at Tromsø the creep time of jute was 14 s.", LIST),
    "N12_marker_in_next_sentence": (
        "The creep time of jute was 14 s. This value is taken from [1].",
        LIST,
    ),
    "N13_marker_in_heading": (
        "2.1 Data of Haldorsen [1]\n\nThe creep time of jute was 14 s.",
        LIST,
    ),
    "N14_hyphenated_name_wrapped": (
        "The creep time of jute was 14 s as reported by Hal-\ndorsen [1].",
        LIST,
    ),
}


@pytest.mark.parametrize(
    "shape", [pytest.param(k, id="known_residual_" + k) for k in sorted(RESIDUAL)]
)
def test_known_residual(shape):
    """Known residual: RESIDUAL_REASON. A fix must flip this test deliberately."""
    assert RESIDUAL_REASON
    body, refs = RESIDUAL[shape]
    record = check(body, "14", refs=refs, unit="s")
    assert not held(record), record["origin"]


def test_known_residual_N15_run_on_page_opens_upper_case():
    record = pages_check(
        [
            "The jute ropes tested by Haldorsen [1] in the draft hall,",
            "With dry fibre, a creep time of 14 s.",
        ],
        "14",
        1,
        refs=LIST,
    )
    assert RESIDUAL_REASON and not held(record), record["origin"]


def test_known_residual_N16_run_on_page_interrupted_by_a_float():
    record = pages_check(
        [
            "The jute ropes tested by Haldorsen [1] in the draft hall",
            "Table 2. Creep times\n\nhad a creep time of 14 s.",
        ],
        "14",
        1,
        refs=LIST,
    )
    assert RESIDUAL_REASON and not held(record), record["origin"]
