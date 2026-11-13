"""SCIENCE_ORIGIN_CHECK: a value's origin mark is read against the phrase that prints it.

The check only holds (it never accepts a record the flag-off validator did not accept, never moves
a subject, never writes a study). Invented sentences only. The effective mark is the quantity's own
``study``, else its subject's study when current or cited, else none."""

import pytest
from test_document_extraction import entity, submitted, support, validate
from test_document_extraction import service as _service

from nasa_fire_ai.ingestion.document_extraction import Output

service = _service
FLAG = "SCIENCE_ORIGIN_CHECK"
SUPPORTED = "SOURCE_SUPPORTED"
REFERENCES = (
    "References\n"
    "[1] Varga, P., Cord ember study, 1985.\n"
    "[2] Okafor, N., Glow decay in waxed cords, 1993.\n"
)
NUMBERED = "References\n1. Varga, P., Cord ember study, 1985.\n2. Okafor, N., Glow decay, 1993.\n"
NO_LIST = "Acknowledgements\nThanks to the bench crew.\n"


def run(
    service,
    monkeypatch,
    sentence,
    value,
    subject_study="current",
    value_study=None,
    cls="Sample",
    label="waxed cord",
    qlabel="smolder time",
    references=REFERENCES,
    flag="1",
):
    monkeypatch.setenv(FLAG, flag)
    p = submitted(service, "II. Results\n" + sentence + "\n" + references)
    o = Output().model_dump()
    o["entities"] = [entity(p, "n", label, cls, sentence, study=subject_study)]
    q = {
        "subject": "n",
        "label": qlabel,
        "expression": value,
        "unit": "s",
        "epistemic": "reported_quantity",
        "support": support(p, sentence),
    }
    if value_study is not None:
        q["study"] = value_study
    o["quantities"] = [q]
    rs = validate(service, p, o)["records"]
    return next(r for r in rs if r["kind"] == "quantities")


MARKERS = [
    "in [2]",
    "in [1, 2]",
    "in [2a]",
    "in [2; 1]",
    "in [2, p. 5]",
    "(Okafor, 1993)",
    "reported by Okafor (1993)",
    "reported by Okafor et al.",
    "elsewhere²",
    "in Ref. 2",
]
ORDERS = [
    "For the waxed cord the smolder time was 9 s, compared with a smolder time of 12 s {m}.",
    "Compared with a smolder time of 12 s {m}, the waxed cord had a smolder time of 9 s.",
    "The waxed cord had a smolder time of 9 s, whereas a smolder time of 12 s was found {m}.",
    "The waxed cord had a smolder time of 9 s versus a smolder time of 12 s {m}.",
]


@pytest.mark.parametrize("order", ORDERS)
@pytest.mark.parametrize("marker", MARKERS)
def test_a_cited_value_marked_current_is_held_in_every_shape(service, monkeypatch, order, marker):
    sentence = order.format(m=marker)
    off = run(service, monkeypatch, sentence, "12", value_study="current", flag="0")
    r = run(service, monkeypatch, sentence, "12", value_study="current")
    assert r["status"] != SUPPORTED, r["reasons"]
    if off["status"] == SUPPORTED:  # the flag-off validator did not hold it: the check does
        assert "ORIGIN_MARK_CONTRADICTED" in r["reasons"]


@pytest.mark.parametrize("order", ORDERS)
@pytest.mark.parametrize("marker", MARKERS[:3])
def test_the_broad_rule_holds_the_current_value_beside_a_cited_complement(
    service, monkeypatch, order, marker
):
    # A marker anywhere in the value's sentence holds a value marked current (SPEC 7.4): the
    # current value beside the cited one is a false hold the replay counts, not a leak.
    r = run(service, monkeypatch, order.format(m=marker), "9", value_study="current")
    assert r["status"] != SUPPORTED
    assert r["origin"]["basis"] in {"CITATION_IN_VALUE_SENTENCE", "CITATION_IN_VALUE_PHRASE"}


def test_a_self_mention_in_the_value_clause_binds_the_current_value(service, monkeypatch):
    s = "In this study the waxed cord had a smolder time of 9 s, compared with 12 s in [2]."
    r = run(service, monkeypatch, s, "9", value_study="current")
    assert r["status"] == SUPPORTED, r["reasons"]


@pytest.mark.parametrize(
    "sentence",
    [
        "The waxed cord had a smolder time of 9 s.",
        "The waxed cord had a smolder time of 9 s, as shown in Figure 3.",
        "The waxed cord had a smolder time of 9 s over a face of 12 cm².",
        "The waxed cord had a smolder time of 9 s (Table 2).",
    ],
)
def test_a_current_value_without_a_marker_stays_supported(service, monkeypatch, sentence):
    r = run(service, monkeypatch, sentence, "9", value_study="current")
    assert r["status"] == SUPPORTED, r["reasons"]


def test_a_correctly_cited_value_with_its_marker_stays_supported(service, monkeypatch):
    s = "The waxed cord had a smolder time of 12 s in [2]."
    r = run(service, monkeypatch, s, "12", "cited", value_study="cited")
    assert r["status"] == SUPPORTED, r["reasons"]


def test_a_cited_investigation_named_as_subject_needs_no_marker(service, monkeypatch):
    s = "The Varga program found a smolder time of 12 s for thin cords."
    r = run(service, monkeypatch, s, "12", "cited", cls="Investigation", label="Varga program")
    assert not any(x.startswith("ORIGIN_") for x in r["reasons"]), r["reasons"]
    assert r["origin"]["mark"] == "cited"


@pytest.mark.parametrize(
    ("references", "cited"), [(NUMBERED, True), (REFERENCES, True), (NO_LIST, False)]
)
def test_a_parenthesised_number_is_a_citation_only_when_the_list_numbers_it(
    service, monkeypatch, references, cited
):
    s = "The waxed cord had a smolder time of 12 s (2)."
    r = run(service, monkeypatch, s, "12", "cited", value_study="cited", references=references)
    assert (r["status"] == SUPPORTED) is cited, r["reasons"]


def test_an_equation_number_is_never_a_citation(service, monkeypatch):
    s = "The waxed cord had a smolder time of 12 s from Eq. (2)."
    r = run(service, monkeypatch, s, "12", "cited", value_study="cited", references=NUMBERED)
    assert r["status"] != SUPPORTED


def test_a_current_value_mark_on_a_cited_subject_is_held(service, monkeypatch):
    r = run(
        service,
        monkeypatch,
        "The waxed cord had a smolder time of 9 s.",
        "9",
        "cited",
        value_study="current",
    )
    assert "ORIGIN_MARK_CONFLICTS_WITH_SUBJECT" in r["reasons"]


def test_a_value_takes_its_subjects_study_when_it_has_no_mark(service, monkeypatch):
    s = "The waxed cord had a smolder time of 12 s, as reported in [2]."
    r = run(service, monkeypatch, s, "12", "current")
    assert r["origin"]["mark"] == "current" and r["origin"]["mark_source"] == "subject"
    assert r["status"] != SUPPORTED


def test_the_check_never_moves_a_subject_or_writes_a_study(service, monkeypatch):
    s = "The waxed cord had a smolder time of 12 s, as reported in [2]."
    r = run(service, monkeypatch, s, "12", value_study="current")
    assert r["proposal"].get("study") == "current"
    assert r["proposal"]["subject"] == "n"


def test_the_check_is_on_by_default_and_zero_turns_it_off(monkeypatch):
    from nasa_fire_ai.ingestion.value_origin import origin_check_enabled

    monkeypatch.delenv(FLAG, raising=False)
    assert origin_check_enabled()
    monkeypatch.setenv(FLAG, "0")
    assert not origin_check_enabled()
    monkeypatch.setenv(FLAG, "1")
    assert origin_check_enabled()


def test_flag_off_is_todays_behaviour(service, monkeypatch):
    s = "For the waxed cord the smolder time was 9 s, compared with a smolder time of 12 s in [2]."
    r = run(service, monkeypatch, s, "12", flag="0")
    assert "origin" not in r and r["status"] == SUPPORTED


def test_the_receipt_names_the_phrase_and_the_anchor(service, monkeypatch):
    s = "For the waxed cord the smolder time was 9 s, compared with a smolder time of 12 s in [2]."
    r = run(service, monkeypatch, s, "12", value_study="current")
    occurrence = r["origin"]["occurrences"][0]
    assert occurrence["row"] == 3 and occurrence["basis"] == "CITATION_IN_VALUE_PHRASE"
    assert [a["text"] for a in occurrence["anchors"]] == ["[2]"]


CASES = [o.format(m=m) for o in ORDERS for m in MARKERS[:4]] + [
    "The waxed cord had a smolder time of 9 s.",
    "Here we report a smolder time of 9 s for the waxed cord, cf. [2].",
    "The waxed cord had a smolder time of 9 s, as in [2].",
    "The waxed cord had a smolder time of 12 s in [2].",
]


@pytest.mark.parametrize("sentence", CASES)
@pytest.mark.parametrize("mark", [None, "current", "cited"])
@pytest.mark.parametrize("subject_study", ["current", "cited", "unknown"])
@pytest.mark.parametrize("value", ["9", "12"])
def test_the_flag_never_accepts_more(service, monkeypatch, sentence, mark, subject_study, value):
    if f"{value} s" not in sentence:
        pytest.skip("value not printed")
    kwargs = {"value_study": mark, "subject_study": subject_study}
    off = run(service, monkeypatch, sentence, value, flag="0", **kwargs)["status"]
    on = run(service, monkeypatch, sentence, value, flag="1", **kwargs)["status"]
    assert on in {off, "UNRESOLVED"}
    assert not (on == SUPPORTED and off != SUPPORTED)


def printed_check(
    sentence,
    value,
    refs=REFERENCES,
    value_study="current",
    subject_study="current",
    quote=None,
    label="cords",
):
    """The origin check on a supported quantity record, reading a printed page that holds the
    sentence and the reference list. ``quote`` is what the model chose to support the value."""
    from nasa_fire_ai.ingestion.value_origin import origin_check

    page = sentence + "\n" + refs
    heading_end = page.index("References") + len("References")
    document = {
        "sections": [{"title": "References", "evidence_id": "E1", "end": heading_end}],
        "segments": [{"evidence_id": "E1", "text": page}],
    }
    quote = sentence if quote is None else quote
    item = {"subject": "n", "expression": value}
    if value_study:
        item["study"] = value_study
    record = {"status": "SOURCE_SUPPORTED", "reasons": []}
    entities = {"n": {"study": subject_study, "label": label, "class_id": "Sample"}}
    span = {"evidence_id": "E1", "start": page.find(quote), "quote": quote}
    origin_check(item, record, [span], entities, document, {"E1": {"text": page}})
    return record


# ---- the check reads the printed page, not the model's quote
PRINTED = "The waxed cord had a smolder time of 12 s according to [2]."


def quantity(p, quote, study="current"):
    return {
        "subject": "n",
        "label": "smolder time",
        "expression": "12",
        "unit": "s",
        "epistemic": "reported_quantity",
        "support": support(p, quote),
        "study": study,
    }


def run_quotes(service, monkeypatch, quotes, flag="1"):
    monkeypatch.setenv(FLAG, flag)
    p = submitted(service, "II. Results\n" + PRINTED + "\n" + REFERENCES)
    o = Output().model_dump()
    o["entities"] = [entity(p, "n", "waxed cord", "Sample", PRINTED, study="current")]
    o["quantities"] = [quantity(p, q) for q in quotes]
    rs = validate(service, p, o)["records"]
    return [r for r in rs if r["kind"] == "quantities"]


@pytest.mark.parametrize(
    "quote",
    [
        PRINTED,
        "The waxed cord had a smolder time of 12 s",
        "waxed cord had a smolder time of 12 s",
        "smolder time of 12 s according",
    ],
)
def test_a_quote_that_stops_before_the_marker_does_not_hide_it(service, monkeypatch, quote):
    (record,) = run_quotes(service, monkeypatch, [quote])
    assert record["status"] != SUPPORTED, record["reasons"]


def test_a_trimmed_duplicate_cannot_become_the_active_supported_proposal(service, monkeypatch):
    records = run_quotes(
        service, monkeypatch, [PRINTED, "The waxed cord had a smolder time of 12 s"]
    )
    assert records and all(r["status"] != SUPPORTED for r in records), [
        (r["status"], r["reasons"]) for r in records
    ]


def test_a_value_that_cannot_be_located_in_the_evidence_is_held():
    record = printed_check(
        "The waxed cord had a smolder time of 12 s.",
        "12",
        quote="a quote that the page does not print, 12 s",
    )
    assert record["status"] == "UNRESOLVED"
    assert "ORIGIN_SPAN_NOT_LOCATED" in record["reasons"]
    assert record["origin"]["basis"] == "SPAN_NOT_LOCATED_IN_EVIDENCE"
