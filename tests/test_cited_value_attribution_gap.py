"""Cited-value attribution: a value stated by this study is not given to a cited work, and
a value of a cited work is not given to this study. With SCIENCE_ORIGIN_CHECK on (the fixture
below) every wrong-attribution case is held; the guards (a current value bound by its own
clause stays supported as current) must stay supported. Invented sentences only."""

import pytest
from test_document_extraction import entity, submitted, support, validate
from test_document_extraction import service as _service

from nasa_fire_ai.ingestion.document_extraction import Output

service = _service
REFERENCES = (
    "References\n"
    "[1] Varga, P., Cord ember study, 1985.\n"
    "[2] Okafor, N., Glow decay in waxed cords, 1993.\n"
    "[3] Wood, N., Rack char study, 1994.\n"
    "² Okafor, N., Glow decay in waxed cords, 1993.\n"
)
SUPPORTED = "SOURCE_SUPPORTED"


@pytest.fixture(autouse=True)
def origin_check_on(monkeypatch):
    """The origin check is off by default; these cases state what it must hold."""
    monkeypatch.setenv("SCIENCE_ORIGIN_CHECK", "1")


# (material, study proposed for the subject, sentence, value that must not be supported)
SYNTHETIC = (
    (
        "waxed cord",
        "cited",
        "For the waxed cord the smolder time was 9 s, compared with a smolder time of 12 s in [2].",
        "9",
    ),
    (
        "oiled twine",
        "cited",
        "For the oiled twine the smolder time was 9 s, compared with a smolder time of 12 s (Okafor, 1993).",
        "9",
    ),
    (
        "braided strand",
        "cited",
        "For the braided strand the smolder time was 9 s, compared with a smolder time of 12 s elsewhere².",
        "9",
    ),
    (
        "tarred rope",
        "current",
        "For the tarred rope the smolder time was 9 s, compared with a smolder time of 12 s in [2].",
        "12",
    ),
    (
        "dry hemp",
        "current",
        "For the dry hemp the smolder time was 9 s, compared with a smolder time of 12 s (Okafor, 1993).",
        "12",
    ),
    (
        "knotted wick",
        "current",
        "For the knotted wick the smolder time was 9 s, compared with a smolder time of 12 s elsewhere².",
        "12",
    ),
    (
        "coiled thread",
        "cited",
        "Using the method of Okafor [2], the coiled thread had a smolder time of 9 s.",
        "9",
    ),
    ("sisal line", "cited", "Here the sisal line had a smolder time of 9 s, as in [2].", "9"),
    (
        "jute string",
        "cited",
        "In these tests the jute string had a smolder time of 9 s, similar to [2].",
        "9",
    ),
    (
        "flax cord",
        "cited",
        "The flax cord (a material also studied by Okafor [2]) had a smolder time of 9 s.",
        "9",
    ),
    (
        "cotton lace",
        "cited",
        "The authors found that the cotton lace had a smolder time of 9 s, consistent with [2].",
        "9",
    ),
    ("nylon lacing", "cited", "The nylon lacing on the Wood rack had a smolder time of 9 s.", "9"),
    (
        "silk thread",
        "current",
        "The silk thread had a smolder time of 12 s, as reported in [2].",
        "12",
    ),
    ("linen band", "current", "The linen band had a smolder time of 12 s (see [2]).", "12"),
    (
        "raw wool yarn",
        "current",
        "The raw wool yarn had a smolder time of 12 s according to [2].",
        "12",
    ),
    (
        "bast rope",
        "current",
        "Okafor [2] tested the bast rope, which had a smolder time of 12 s.",
        "12",
    ),
    (
        "kapok wick",
        "current",
        "Whereas [2] reported a smolder time of 12 s, the kapok wick in this study had a smolder time of 9 s.",
        "12",
    ),
    (
        "reed cord",
        "current",
        "The reed cord, unlike the cord of [2], had a smolder time of 9 s, against a smolder time of 12 s in [2].",
        "12",
    ),
    (
        "twisted rush",
        "current",
        "Unlike [2], which reported a smolder time of 12 s, the twisted rush here had a smolder time of 9 s.",
        "12",
    ),
)
# Classes found by the second adversarial review.
REVIEW = (
    (
        "waxed cord",
        "current",
        "Okafor et al. reported a smolder time of 12 s for the waxed cord.",
        "12",
    ),
    (
        "waxed cord",
        "current",
        "The present work extends [2], where a smolder time of 12 s was found for the waxed cord.",
        "12",
    ),
    ("waxed cord", "cited", "The waxed cord had a smolder time of 12 s, refuting [2].", "12"),
)
# Guards: (material, sentence, current value that stays supported as current).
GUARDS = (
    ("waxed cord", "Here we report a smolder time of 9 s for the waxed cord, cf. [2].", "9"),
    (
        "waxed cord",
        "In this study, for the waxed cord the smolder time was 9 s, whereas [2] reported a smolder time of 12 s.",
        "9",
    ),
    ("waxed cord", "Our waxed cord, unlike the cord of [2], had a smolder time of 9 s.", "9"),
    (
        "waxed cord",
        "In this work the waxed cord, prepared as in Okafor et al., had a smolder time of 9 s.",
        "9",
    ),
    ("waxed cord", "We did measure a smolder time of 9 s for the waxed cord, cf. [2].", "9"),
)


def trimmed(sentence, expression):
    """The sentence cut just after the value and its unit: the quote of a model that stops before the marker."""
    return sentence[: sentence.index(f"{expression} s") + len(f"{expression} s")]


def records(service, material, study, sentence, expression, trim=False):
    p = submitted(service, "II. Results\n" + sentence + "\n" + REFERENCES)
    o = Output().model_dump()
    o["entities"] = [entity(p, "n", material, "Sample", sentence, study=study)]
    o["quantities"] = [
        {
            "subject": "n",
            "label": "smolder time",
            "expression": expression,
            "unit": "s",
            "epistemic": "reported_quantity",
            "support": support(p, trimmed(sentence, expression) if trim else sentence),
        }
    ]
    return validate(service, p, o)["records"]


def describe(rs):
    return [(r["kind"], r["proposal"].get("expression"), r["status"], r["reasons"]) for r in rs]


def held(rs, expression):
    found = [
        r for r in rs if r["kind"] == "quantities" and r["proposal"]["expression"] == expression
    ]
    assert found, describe(rs)
    return found


MARKS = {"absent": None, "current": "current", "cited": "cited"}
CASES = [
    pytest.param(c[0], c[2], c[3], mark, id=f"{name}{i:02d}-{c[0].replace(' ', '-')}-{mark}")
    for name, group in (("syn", SYNTHETIC), ("rev", REVIEW))
    for i, c in enumerate(group)
    # the marks that do not fit the value: unmarked, or the mark the case's subject carries
    for mark in ("absent", c[1])
]


@pytest.mark.parametrize("trim", [False, True], ids=["full-quote", "trimmed-quote"])
@pytest.mark.parametrize(("material", "sentence", "wrong", "mark"), CASES)
def test_a_value_marked_with_the_wrong_origin_is_not_supported(
    service, material, sentence, wrong, mark, trim
):
    rs = records(service, material, MARKS[mark], sentence, wrong, trim)
    assert all(r["status"] != SUPPORTED for r in held(rs, wrong)), describe(rs)


@pytest.mark.parametrize(
    ("material", "sentence", "value"),
    [pytest.param(*c, id=f"guard-{i}") for i, c in enumerate(GUARDS)],
)
def test_a_current_value_bound_by_its_own_clause_stays_supported(
    service, material, sentence, value
):
    rs = records(service, material, "current", sentence, value)
    assert all(r["status"] == SUPPORTED for r in held(rs, value)), describe(rs)
