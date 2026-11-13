"""The phrase that holds a value, and the markers printed in a sentence (invented text)."""

import pytest

from nasa_fire_ai.ingestion.clause_cues import locate_value
from nasa_fire_ai.ingestion.value_origin import binders, citation_anchors, numbered_references
from nasa_fire_ai.ingestion.value_phrase import value_phrase

NUMBERED = {
    "sections": [{"title": "References", "evidence_id": "E0", "end": 0}],
    "segments": [
        {
            "evidence_id": "E0",
            "text": "1. Varga, P., Cord study, 1985.\n2. Okafor, N., Glow, 1993.\n",
        }
    ],
}
NO_LIST = {"sections": [], "segments": []}


def phrase(sentence, value):
    found = value_phrase(sentence, locate_value(sentence, value))
    return sentence[found["start"] : found["end"]], found


@pytest.mark.parametrize(
    ("sentence", "value", "expected"),
    [
        (
            "For the waxed cord the smolder time was 9 s, compared with 12 s in [2].",
            "9",
            "For the waxed cord the smolder time was 9 s",
        ),
        (
            "For the waxed cord the smolder time was 9 s, compared with 12 s in [2].",
            "12",
            "compared with 12 s in [2]",
        ),
        (
            "Compared with 12 s in [2], the waxed cord had a smolder time of 9 s.",
            "9",
            "the waxed cord had a smolder time of 9 s",
        ),
        (
            "The waxed cord had a smolder time of 9 s versus a smolder time of 12 s in [2].",
            "9",
            "The waxed cord had a smolder time of 9 s",
        ),
        (
            "Unlike [2], which reported a smolder time of 12 s, the rush had 9 s.",
            "12",
            "Unlike [2], which reported a smolder time of 12 s",
        ),
        (
            "Okafor [2] tested the rope, which had a smolder time of 12 s.",
            "12",
            "Okafor [2] tested the rope, which had a smolder time of 12 s",
        ),
        (
            "The cord had a smolder time of 12 s, as reported in [2].",
            "12",
            "The cord had a smolder time of 12 s, as reported in [2]",
        ),
        (
            "Filled points are from this work at 9 s and open points are from Okafor².",
            "9",
            "Filled points are from this work at 9 s",
        ),
        (
            "Earlier drops used 2 s windows [3]; the present cords were dropped for 5 s.",
            "5",
            "the present cords were dropped for 5 s",
        ),
        (
            "Smolder limits of 9 s and 14 s were computed for thin cord (from Okafor et al. [2]).",
            "9",
            "Smolder limits of 9 s and 14 s were computed for thin cord (from Okafor et al. [2])",
        ),
    ],
)
def test_the_phrase_of_a_value(sentence, value, expected):
    assert phrase(sentence, value)[0] == expected


def test_a_supplement_that_closes_again_is_set_aside_and_the_host_resumes():
    text, _found = phrase(
        "Since our access is limited, using a turntable⁴, testing has been limited to 40 s.", "40"
    )
    assert text == "testing has been limited to 40 s"


def test_a_gerund_subject_is_not_a_supplement():
    text, _ = phrase("In the hall, testing has been limited to cords of 40 s.", "40")
    assert text == "testing has been limited to cords of 40 s"


def test_an_unmarked_parenthetical_with_a_source_is_excised_from_the_host():
    sentence = "The flax cord (also studied by Okafor [2]) had a smolder time of 9 s."
    _text, found = phrase(sentence, "9")
    assert [sentence[a:b] for a, b in found["excised"]] == ["(also studied by Okafor [2])"]


@pytest.mark.parametrize(
    ("text", "shape"),
    [
        ("12 s in [2]", "bracket"),
        ("12 s in [1, 2]", "bracket"),
        ("12 s in [2a]", "bracket"),
        ("12 s in [2; 1]", "bracket"),
        ("12 s in [2, p. 5]", "bracket"),
        ("12 s (Okafor, 1993)", "author_year"),
        ("12 s reported by Okafor (1993)", "author_year"),
        ("12 s reported by Okafor et al.", "et_al"),
        ("12 s in Ref. 2", "reference"),
        ("12 s elsewhere²", "superscript"),
        ("12 s (2)", "numbered"),
    ],
)
def test_marker_shapes(text, shape):
    found = [a for a in citation_anchors(text, NUMBERED) if a["strength"] == "strong"]
    assert found and found[0]["shape"] == shape, found


@pytest.mark.parametrize(
    "text",
    [
        "12 s over a face of 12 cm².",
        "12 s from Eq. (2).",
        "12 s as shown in Figure 3.",
        "12 s in figure2.",
        "Okafor was the first word.",
    ],
)
def test_these_are_not_anchors(text):
    assert not [a for a in citation_anchors(text, NUMBERED) if a["strength"] == "strong"]


def test_a_parenthesised_number_needs_a_numbered_list():
    assert not citation_anchors("12 s (2)", NO_LIST)
    assert numbered_references(NUMBERED) == {1, 2}


def _wood_document(extra=""):
    return {
        "sections": [{"title": "References", "evidence_id": "E0", "end": 0}],
        "segments": [{"evidence_id": "E0", "text": "[1] Wood, N., Rack study, 1994.\n" + extra}],
    }


def test_a_surname_of_the_list_is_a_weak_anchor_unless_it_opens_the_sentence():
    # N1 (rule corrected): mid-sentence the surname is a weak anchor; opening the sentence it
    # anchors as the subject of a finite verb, before et al. / and colleagues / a year in
    # parentheses / brackets, or as a possessive; a surname that also prints in lowercase in the
    # document (a common word) needs one of the explicit signals.
    document = _wood_document()
    mid = citation_anchors("The lacing on the Wood rack had 9 s.", document)
    assert [a["strength"] for a in mid] == ["weak"]
    # Old expectation: not an anchor. New: anchors (subject of a finite verb; "wood" never prints
    # in lowercase in this document). Direction: now holds.
    assert [a["shape"] for a in citation_anchors("Wood is a common noun here.", document)] == [
        "reference_author"
    ]
    # Same sentence in a document that also prints lowercase "wood": a common word, not held.
    # (Old expectation kept: not an anchor.)
    common = _wood_document("The wood of the rack burned.\n")
    assert not citation_anchors("Wood is a common noun here.", common)


def test_n1_twin_and_explicit_signals_with_the_surname_also_in_lowercase():
    plain = _wood_document()
    common = _wood_document("The wood of the rack burned.\n")
    assert citation_anchors("Wood found that the cord lasted 12 s.", plain)
    assert not citation_anchors("Wood found that the cord lasted 12 s.", common)
    for sentence in (
        "Wood et al. found that the cord lasted 12 s.",
        "Wood (1994) found that the cord lasted 12 s.",
        "Wood [1] found that the cord lasted 12 s.",
        "Wood and colleagues found that the cord lasted 12 s.",
    ):
        assert citation_anchors(sentence, common), sentence
        assert citation_anchors(sentence, plain), sentence


def test_n1_possessive_anchors_unless_the_registry_holds_the_term(monkeypatch):
    from nasa_fire_ai.ingestion import value_origin

    plain = _wood_document()
    sentence = "Wood's data showed 12 s for the cord."
    assert [a["shape"] for a in citation_anchors(sentence, plain)] == ["reference_author"]
    assert [a["shape"] for a in citation_anchors("The Wood's data showed 12 s.", plain)] == [
        "reference_author"
    ]
    # With the surname also in lowercase, a bare possessive is no explicit signal.
    common = _wood_document("The wood of the rack burned.\n")
    assert not citation_anchors(sentence, common)
    # A term the repo's registries already hold ("Name's noun") is a term, not an author.
    monkeypatch.setattr(value_origin, "_TERM_KEYS", {"wood s modulus"})
    assert not citation_anchors("Wood's modulus was 12 GPa.", plain)
    assert not citation_anchors("The value of Wood's modulus was 12 GPa.", plain)
    assert citation_anchors("Wood's data showed 12 s.", plain)


def test_n1_lowercase_twin_guards_only_a_capital_that_comes_from_the_sentence_start():
    plain = _wood_document()
    common = _wood_document("The wood of the rack burned.\n")
    # Sentence start: a capital proves no name, so the possessive is not held with a lowercase twin
    # (it is held without one).
    assert not citation_anchors("Wood's data showed 12 s for the cord.", common)
    assert citation_anchors("Wood's data showed 12 s for the cord.", plain)
    # Mid-sentence the capital marks a proper name: always held, possessive or bare.
    assert citation_anchors("The cord lasted 12 s, as in Wood's tests.", common)
    assert citation_anchors("The cord lasted 12 s, as in Wood's tests.", plain)
    assert citation_anchors("The cord lasted 12 s, as Wood found.", common)
    assert citation_anchors("Later, Wood found that the cord lasted 12 s.", common)


@pytest.mark.parametrize(
    ("sentence", "void"),
    [
        ("In this study the cord had 9 s.", False),
        ("Here the cord had 9 s.", False),
        ("We did measure 9 s.", False),
        ("Our earlier study found 9 s.", True),
        ("The present study [2] found 9 s.", True),
        ("The previous work found 9 s.", None),
        ("The present cords had 9 s.", None),
    ],
)
def test_binders(sentence, void):
    found = binders(sentence, citation_anchors(sentence, NUMBERED))
    if void is None:
        assert not found
    else:
        assert found and found[0]["void"] is void


def wrap(text, width):
    """Greedy line wrapping at a given measure."""
    lines, line = [], ""
    for word in text.split():
        if line and len(line) + 1 + len(word) > width:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    return "\n".join([*lines, line])


PARAGRAPH = (
    "The Varga program found that the spread of the glow could stay steady for cords roughly "
    "0.8 m in length when the draft was slow, and the same cords went out in a fast draft. "
    "A short note follows."
)


@pytest.mark.parametrize("width", [38, 56, 90])
def test_a_wrapped_sentence_is_one_sentence_at_any_measure(width):
    from nasa_fire_ai.ingestion.value_phrase import sentence_bounds

    block = wrap(PARAGRAPH, width)
    offset = block.index("0.8")
    start, end = sentence_bounds(block, offset, block)
    assert block[start:end].startswith("The Varga program")
    assert block[start:end].endswith("fast draft.")


def test_a_short_line_that_ends_a_paragraph_stays_a_boundary():
    from nasa_fire_ai.ingestion.value_phrase import sentence_bounds

    block = (
        "The panels were mounted in a row above the igniter and left to settle for a while\n"
        "before the first drop of the series was made from the top of the tower hall\n"
        "and the rest followed in order\n"
        "9 s was the longest smolder time"
    )
    offset = block.index("9 s")
    start, end = sentence_bounds(block, offset, block)
    assert block[start:end] == "9 s was the longest smolder time"


def test_the_measure_is_the_median_line_length_of_the_block():
    from nasa_fire_ai.ingestion.value_phrase import measure

    assert measure("aaaa\nbbbbbbbb\ncc\n\nddddddddd") == 6
    assert measure("") == 0


def test_a_table_row_is_its_own_sentence():
    from nasa_fire_ai.ingestion.value_phrase import sentence_bounds

    text = "Waxed cord 9 s 12 mm\nTarred rope 14 s 15 mm\nOiled twine 11 s 10 mm"
    start, end = sentence_bounds(text, text.index("14"))
    assert text[start:end] == "Tarred rope 14 s 15 mm"
