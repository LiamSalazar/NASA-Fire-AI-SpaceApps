"""Condition (c): a binding self-mention keeps a current-study value beside a marker; the broad rule
holds the others.

With SCIENCE_ORIGIN_CHECK on and the value marked current (explicitly, and again through its
subject only), each case stays SOURCE_SUPPORTED and gets no ORIGIN_ reason, while the same marker
moved into the value's own phrase (the negative twins) is held. The shapes keep the syntax of
sentences that print a marker beside a current value in real articles, rewritten as invented text.
"""

import os

import pytest
from test_cited_value_attribution_gap import GUARDS
from test_document_extraction import entity, submitted, support, validate
from test_document_extraction import service as _service
from test_value_origin import printed_check

from nasa_fire_ai.ingestion.document_extraction import Output

service = _service
SUPPORTED = "SOURCE_SUPPORTED"
REFERENCES = (
    "References\n"
    "[1] Varga, P., Cord ember study, 1985.\n"
    "[2] Okafor, N., Glow decay in waxed cords, 1993.\n"
)
NUMBERED = "References\n1. Varga, P., Cord ember study, 1985.\n2. Okafor, N., Glow decay, 1993.\n"


@pytest.fixture(autouse=True)
def origin_check_on(monkeypatch):
    monkeypatch.setenv("SCIENCE_ORIGIN_CHECK", "1")


def check(sentence, value, refs, value_study):
    """The origin check on a supported quantity record, reading the printed page."""
    return printed_check(sentence, value, refs, value_study)


def status(service, sentence, value, label, qlabel, unit, references, value_study, flag):
    p = submitted(service, "II. Results\n" + sentence + "\n" + references)
    o = Output().model_dump()
    o["entities"] = [entity(p, "n", label, "Sample", sentence, study="current")]
    q = {
        "subject": "n",
        "label": qlabel,
        "expression": value,
        "unit": unit,
        "epistemic": "reported_quantity",
        "support": support(p, sentence),
    }
    if value_study:
        q["study"] = value_study
    o["quantities"] = [q]
    os.environ["SCIENCE_ORIGIN_CHECK"] = flag
    try:
        rs = validate(service, p, o)["records"]
    finally:
        os.environ["SCIENCE_ORIGIN_CHECK"] = "1"
    return next(r for r in rs if r["kind"] == "quantities")


# (sentence, value, subject label, quantity label, unit, reference list)
DISTANT = [
    (
        (
            "Since our only steady access to slow drafts is the 3 m stilling hall, using a "
            "turntable⁴, testing has been limited to cords that smolder within 40 s."
        ),
        "40",
        "cords",
        "smolder",
        "s",
        REFERENCES,
    ),
    (
        (
            "Then, using a bench clamp with the prescribed hand torque¹, the cords were struck "
            "12 times at the free end."
        ),
        "12",
        "cords",
        "times",
        None,
        REFERENCES,
    ),
    (
        (
            "Hence, a cord ember analysis (7) (8) was performed using a 40-node mesh of the "
            "imported holder geometry."
        ),
        "40",
        "cord ember analysis",
        "node",
        None,
        "References\n7. Varga, P., Mesh study, 1985.\n8. Okafor, N., Holder study, 1993.\n",
    ),
    (
        "This seeks to show that the cords stay below 60 C per KX-9 (5).",
        "60",
        "cords",
        "below",
        "C",
        "References\n5. Varga, P., Cord standard, 1985.\n",
    ),
    (
        "This report will discuss cord charring in steps of 9 s as depicted in figure2.",
        "9",
        "cord charring",
        "steps",
        "s",
        REFERENCES,
    ),
    (
        "Filled points are from this work at 9 s and open points are from Okafor².",
        "9",
        "Filled points",
        "points",
        "s",
        REFERENCES,
    ),
    (
        (
            "Smolder limits of 9 s and 14 s were computed with equations 3 and 4 for thin cord "
            "(from Okafor et al. [2])."
        ),
        "9",
        "Smolder limits",
        "limits",
        "s",
        REFERENCES,
    ),
    (
        "The cords were dried in a tube oven³ at 80 C for 12 h.",
        "80",
        "cords",
        "dried",
        "C",
        REFERENCES,
    ),
    (
        "Following the soaking procedure of [4], each cord was soaked for 12 h.",
        "12",
        "cord",
        "soaked",
        "h",
        "References\n[4] Varga, P., Soaking study, 1985.\n",
    ),
    (
        "Earlier drops used 2 s windows [3]; the present cords were dropped for 5 s.",
        "5",
        "present cords",
        "dropped",
        "s",
        REFERENCES + "[3] Wood, N., Rack char study, 1994.\n",
    ),
]
TWINS = [
    (
        (
            "Since our only steady access to slow drafts is the 3 m stilling hall, testing has "
            "been limited to cords that smolder within 40 s elsewhere⁴."
        ),
        "40",
        "cords",
        "smolder",
        "s",
        REFERENCES,
    ),
    (
        (
            "Hence, a cord ember analysis was performed using a 40-node mesh [7] of the imported "
            "holder geometry."
        ),
        "40",
        "cord ember analysis",
        "node",
        None,
        "References\n[7] Varga, P., Mesh study, 1985.\n",
    ),
    (
        "The cords were dried in a tube oven at 80 C [3] for 12 h.",
        "80",
        "cords",
        "dried",
        "C",
        REFERENCES + "[3] Wood, N., Rack char study, 1994.\n",
    ),
]


# Under the broad rule (a marker anywhere in the sentence holds a current value unless the value's
# clause binds it to this study) these shapes are held although their value is the study's own:
# the accepted false holds, counted in the replay. The others stay supported: a self-mention
# binds the value, or the sentence prints no marker at all (a flattened "figure2" is none).
BROAD_HELD = {1, 2, 3, 6, 7, 8, 9}
DISTANT_CASES = [pytest.param(i, *case, id=f"shape-{i}") for i, case in enumerate(DISTANT)]


@pytest.mark.parametrize("via", ["value", "subject"])
@pytest.mark.parametrize(
    ("index", "sentence", "value", "label", "qlabel", "unit", "refs"), DISTANT_CASES
)
def test_a_distant_marker_holds_a_current_value_only_by_the_broad_rule(
    index, sentence, value, label, qlabel, unit, refs, via
):
    record = check(sentence, value, refs, "current" if via == "value" else None)
    assert record["origin"]["mark"] == "current"
    if index in BROAD_HELD:
        assert record["status"] != SUPPORTED, record["origin"]
        assert record["origin"]["basis"] in {
            "CITATION_IN_VALUE_SENTENCE",
            "CITATION_IN_VALUE_PHRASE",
        }
    else:
        assert record["status"] == SUPPORTED, record["origin"]
        assert not any(x.startswith("ORIGIN_") for x in record["reasons"])


@pytest.mark.parametrize(("sentence", "value", "label", "qlabel", "unit", "refs"), TWINS)
def test_the_same_marker_in_the_value_phrase_holds(sentence, value, label, qlabel, unit, refs):
    record = check(sentence, value, refs, "current")
    assert record["status"] != SUPPORTED
    assert "ORIGIN_MARK_CONTRADICTED" in record["reasons"]


@pytest.mark.parametrize(
    ("material", "sentence", "value"),
    [pytest.param(*c, id=f"guard-{i}") for i, c in enumerate(GUARDS)],
)
@pytest.mark.parametrize("via", ["value", "subject"])
def test_the_five_guards_stay_supported(service, material, sentence, value, via):
    mark = "current" if via == "value" else None
    on = status(service, sentence, value, material, "smolder time", "s", REFERENCES, mark, "1")
    assert on["status"] == SUPPORTED, on["reasons"]
