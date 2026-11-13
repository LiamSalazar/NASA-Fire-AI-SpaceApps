"""A sentence that sets a current-study value beside a cited value never gives the current
value to the cited work: a proposal attributing it to the cited study is not source
supported. Synthetic invented sentences. The digit cases are the real attribution checks
(their quantities are well formed); they are held with SCIENCE_ORIGIN_CHECK on (the fixture)."""

import pytest
from test_document_extraction import entity, submitted, support, validate
from test_document_extraction import service as _service

from nasa_fire_ai.ingestion.document_extraction import Output

service = _service
REFERENCES = (
    "References\n"
    "[1] Varga, P., Cord ember study, 1985.\n"
    "[2] Okafor, N., Glow decay in waxed cords, 1993.\n"
)
SENTENCES = {
    "reported_by_name": (
        (
            "The cords in this test smoldered for nine seconds, compared with twelve seconds "
            "reported by Okafor [2]."
        ),
        "cords",
    ),
    "present_tests": (
        "The present tests gave nine seconds, against twelve seconds in [2].",
        "present tests",
    ),
    "waxed_cord": (
        "The waxed cord smoldered for nine seconds, compared with twelve seconds in [2].",
        "waxed cord",
    ),
    "digits_reported_by_name": (
        "For the cords in this test the smolder time was 9 s, compared with a smolder time of 12 s reported by Okafor [2].",
        "cords",
    ),
    "digits_present_tests": (
        "In the present tests the smolder time was 9 s, against a smolder time of 12 s in [2].",
        "present tests",
    ),
    "digits_waxed_cord": (
        "For the waxed cord the smolder time was 9 s, compared with a smolder time of 12 s in [2].",
        "waxed cord",
    ),
}
SUPPORTED = "SOURCE_SUPPORTED"


@pytest.fixture(autouse=True)
def origin_check_on(monkeypatch):
    """The origin check is off by default; these cases state what it must hold."""
    monkeypatch.setenv("SCIENCE_ORIGIN_CHECK", "1")


WORDS = [k for k in SENTENCES if not k.startswith("digits")]
DIGITS = [k for k in SENTENCES if k.startswith("digits")]
KEYS = WORDS + DIGITS
NINE = ("nine", "9")
TWELVE = ("twelve", "12")


def build(service, key, study, trim=False):
    """The model proposes the subject, both values and the sentence with one study."""
    sentence, label = SENTENCES[key]
    p = submitted(service, "II. Results\n" + sentence + "\n" + REFERENCES)
    o = Output().model_dump()
    o["entities"] = [entity(p, "n", label, "Sample", sentence, study=study)]

    def quantity(expression):
        digits = key.startswith("digits")
        return {
            "subject": "n",
            "label": "smolder time"
            if digits
            else ("smoldered" if "smoldered" in sentence else "gave"),
            "expression": expression,
            "unit": "s" if key.startswith("digits") else "seconds",
            "epistemic": "reported_quantity",
            "support": support(
                p,
                sentence[: sentence.index(f"{expression} s") + len(f"{expression} s")]
                if trim and digits
                else sentence,
            ),
        }

    digits = key.startswith("digits")
    o["quantities"] = [quantity("9" if digits else "nine"), quantity("12" if digits else "twelve")]
    o["statements"] = [
        {
            "text": sentence,
            "class_id": "ReportedObservation",
            "epistemic": "measured_observation",
            "subjects": ["n"],
            "study": study,
            "support": support(p, sentence),
        }
    ]
    return p, o


def records(service, key, study, trim=False):
    p, o = build(service, key, study, trim)
    return validate(service, p, o)["records"]


def describe(rs):
    return [(r["kind"], r["proposal"].get("expression"), r["status"], r["reasons"]) for r in rs]


def value(rs, expression):
    found = [
        r for r in rs if r["kind"] == "quantities" and r["proposal"]["expression"] in expression
    ]
    assert found, describe(rs)
    return found


@pytest.mark.parametrize("trim", [False, True], ids=["full-quote", "trimmed-quote"])
@pytest.mark.parametrize("key", KEYS)
def test_the_current_value_is_not_supported_as_cited_work(service, key, trim):
    rs = records(service, key, "cited", trim)
    held = value(rs, NINE) + [r for r in rs if r["kind"] == "statements"]
    assert all(r["status"] != SUPPORTED for r in held), describe(rs)


@pytest.mark.parametrize("trim", [False, True], ids=["full-quote", "trimmed-quote"])
@pytest.mark.parametrize("key", list(SENTENCES))
def test_a_current_proposal_is_never_turned_into_a_cited_record(service, key, trim):
    rs = records(service, key, "current", trim)
    for r in value(rs, NINE) + [r for r in rs if r["kind"] == "statements"]:
        assert r["proposal"].get("study") in (None, "current"), describe(rs)
    for r in rs:
        assert r["status"] != SUPPORTED or r["proposal"].get("study") != "cited", describe(rs)


@pytest.mark.parametrize("trim", [False, True], ids=["full-quote", "trimmed-quote"])
@pytest.mark.parametrize("key", KEYS)
def test_the_cited_value_is_not_supported_as_a_current_result(service, key, trim):
    rs = records(service, key, "current", trim)
    assert all(r["status"] != SUPPORTED for r in value(rs, TWELVE)), describe(rs)


@pytest.mark.parametrize("trim", [False, True], ids=["full-quote", "trimmed-quote"])
@pytest.mark.parametrize(
    ("key", "study"),
    [(k, st) for k in WORDS for st in ("cited", "current")]
    + [(k, "cited") for k in DIGITS]
    + [(k, "current") for k in DIGITS],
)
def test_no_supported_nine_value_has_a_cited_subject(service, key, study, trim):
    rs = records(service, key, study, trim)
    studies = {r["proposal"]["key"]: r["proposal"]["study"] for r in rs if r["kind"] == "entities"}
    for r in value(rs, NINE):
        assert r["status"] != SUPPORTED or studies[r["proposal"]["subject"]] != "cited", describe(
            rs
        )
