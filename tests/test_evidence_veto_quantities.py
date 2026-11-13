"""SCIENCE_EVIDENCE_VETO_QUANTITIES (on by default; "0" turns it off): the quantity vetoes read the printed line(s) around the
located span, never the model's quote alone. Invented text only.

Each case trims the quote of one value inside its printed line and checks that, with the flag on,
the trimmed record is held or rejected for the reason the whole line gives; with the flag off the
trimmed quote still evades (the control that the flag changes something and nothing else).
"""

import pytest
from test_document_extraction import entity, submitted, support, validate
from test_document_extraction import service as _service
from test_scientific_facets import only, quantity

from nasa_fire_ai.ingestion.clause_cues import printed_line_bounds
from nasa_fire_ai.ingestion.document_extraction import Output
from nasa_fire_ai.ingestion.quantity_validation import printed_span
from nasa_fire_ai.ingestion.subject_recognition import heading_rule_accepts

service = _service
FLAG = "SCIENCE_EVIDENCE_VETO_QUANTITIES"
SUPPORTED = "SOURCE_SUPPORTED"


def read(service, monkeypatch, on, text, quote, subject, others, item):
    """The one quantity record of ``text`` with its support cut to ``quote``."""
    monkeypatch.setenv(FLAG, "1" if on else "0")
    p = submitted(service, "II. Results\n" + text + "\n")
    o = Output().model_dump()
    o["entities"] = [entity(p, "n", *subject, text)] + [
        entity(p, f"o{i}", *other, text) for i, other in enumerate(others)
    ]
    o["quantities"] = [quantity(p, quote, "n", *item)]
    o["quantities"][0]["support"] = support(p, quote)
    return only(validate(service, p, o)["records"], "quantities")


RUN = ("Alpha run", "ExperimentalRun")
SHEET = ("Alpha sheet", "Sample")

# (id, printed text, trimmed quote, subject, other entities, quantity item,
#  statuses off/on, a reason the flag-on record carries)
CASES = (
    (
        "planned-value-on-a-run",
        "In the Alpha run the chamber pressure was set to 2.4 atm for the next series.",
        "the chamber pressure was set to 2.4 atm",
        RUN,
        (),
        ("chamber pressure", "2.4", "atm", "experimental_configuration"),
        ("UNRESOLVED", "REJECTED"),
        "PLANNED_VALUE_ATTRIBUTED_TO_EXECUTED_RUN",
    ),
    (
        "value-printed-as-not-done",
        "Panel C3 was held at 34 % oxygen for the next series.",
        "Panel C3 was held at 34 % oxygen",
        ("Panel C3", "Sample"),
        (),
        ("oxygen", "34", "%", "experimental_configuration", "actual"),
        (SUPPORTED, "UNRESOLVED"),
        "VALUE_PRINTED_AS_NOT_DONE_REQUIRES_REVIEW",
    ),
    (
        "derivation-word-dropped",
        "In the Alpha run the calculated burn rate was 2.1 mm/s.",
        "burn rate was 2.1 mm/s.",
        RUN,
        (),
        ("burn rate", "2.1", "mm/s", "reported_quantity"),
        ("UNRESOLVED", "REJECTED"),
        "EXPLICIT_DERIVATION_IS_NOT_REPORTED_MEASUREMENT",
    ),
    (
        "caption-head-dropped",
        "Figure 6 – Alpha sheet flame length 4.2 cm at 21% O2",
        "Alpha sheet flame length 4.2 cm at",
        SHEET,
        (),
        ("flame length", "4.2", "cm", "reported_quantity"),
        ("UNRESOLVED", "UNRESOLVED"),
        "REPORTED_VALUE_PRINTED_IN_A_CAPTION_REQUIRES_REVIEW",
    ),
    (
        "rival-subject-dropped",
        "The Beta sheet, cut from the Alpha sheet, had an ignition temperature of 410 C.",
        "Alpha sheet, had an ignition temperature of 410 C.",
        SHEET,
        (("Beta sheet", "Sample"),),
        ("ignition temperature", "410", "C", "reported_quantity"),
        (SUPPORTED, "UNRESOLVED"),
        "QUANTITY_LOCAL_SUBJECT_BINDING_UNRESOLVED",
    ),
)


@pytest.mark.parametrize("case", CASES, ids=[c[0] for c in CASES])
def test_a_trimmed_quote_is_read_in_its_printed_line(service, monkeypatch, case):
    _id, text, quote, subject, others, item, (off, on), reason = case
    assert quote in text and quote != text
    trimmed_off = read(service, monkeypatch, False, text, quote, subject, others, item)
    trimmed_on = read(service, monkeypatch, True, text, quote, subject, others, item)
    whole_on = read(service, monkeypatch, True, text, text, subject, others, item)
    assert trimmed_off["status"] == off, trimmed_off["reasons"]
    assert trimmed_on["status"] == on, trimmed_on["reasons"]
    assert reason in trimmed_on["reasons"], trimmed_on["reasons"]
    # Never more accepted than the whole line.
    order = {"REJECTED": 0, "UNRESOLVED": 1, SUPPORTED: 2}
    assert order[trimmed_on["status"]] <= order[whole_on["status"]]


def test_the_flag_is_on_by_default(monkeypatch):
    monkeypatch.delenv(FLAG, raising=False)
    from nasa_fire_ai.ingestion.quantity_validation import evidence_veto_quantities

    assert evidence_veto_quantities() is True
    monkeypatch.setenv(FLAG, "0")
    assert evidence_veto_quantities() is False


def test_a_quote_over_two_lines_reads_the_union_of_its_lines():
    text = "Alpha was dry.\nBeta was wet, planned for 3 s.\nGamma was cold.\n"
    start, end = text.index("dry"), text.index("planned")
    lo, hi = printed_line_bounds(text, start, end)
    assert text[lo:hi] == "Alpha was dry.\nBeta was wet, planned for 3 s."
    # One line, and a sentence end inside a line is a cut.
    one = printed_line_bounds(text, text.index("Beta"), text.index("wet"))
    assert text[one[0] : one[1]] == "Beta was wet, planned for 3 s."
    both = "It was dry. It was wet at 4 s.\n"
    cut = printed_line_bounds(both, both.index("wet"), both.index("wet") + 3)
    assert both[cut[0] : cut[1]] == "It was wet at 4 s."


def test_a_span_that_cannot_be_placed_has_no_printed_line():
    evidence = {"E1": {"text": "Alpha was dry at 3 s.\n"}}
    span = {"evidence_id": "E1", "start": 0, "end": 5, "quote": "Alpha"}
    assert printed_span(span, evidence)["quote"] == "Alpha was dry at 3 s."
    assert printed_span({**span, "quote": "Gamma"}, evidence) is None
    assert printed_span({**span, "evidence_id": "E2"}, evidence) is None
    assert printed_span({**span, "end": 99}, evidence) is None


def test_an_unplaced_span_is_held(service, monkeypatch):
    from nasa_fire_ai.ingestion import quantity_validation

    monkeypatch.setattr(quantity_validation, "printed_span", lambda span, evidence: None)
    text = "The Alpha sheet had an ignition temperature of 410 C."
    record = read(
        service,
        monkeypatch,
        True,
        text,
        text,
        SHEET,
        (),
        ("ignition temperature", "410", "C", "reported_quantity"),
    )
    assert record["status"] != SUPPORTED
    assert "QUANTITY_PRINTED_LINE_NOT_LOCATED" in record["reasons"]


def test_a_rival_in_the_printed_line_blocks_the_heading_rule(monkeypatch):
    from nasa_fire_ai.ingestion import subject_recognition

    monkeypatch.setattr(subject_recognition, "section_for_span", lambda span, document: "Alpha")
    entities = {
        "a": {"label": "Alpha", "class_id": "Sample", "validation_status": SUPPORTED},
        "b": {"label": "Beta", "class_id": "Sample", "validation_status": SUPPORTED},
    }
    spans = [{"quote": "had a density of 3 g"}]
    line = [{"quote": "Beta, with Alpha, had a density of 3 g"}]
    assert heading_rule_accepts("a", spans, entities, {})
    assert heading_rule_accepts("a", spans, entities, {}, line) is None


def test_a_name_cut_out_of_the_quote_is_looked_for_in_the_printed_line(service, monkeypatch):
    text = "In the Alpha run the mean hold time was 5 s."
    item = ("mean hold time", "5", "s", "reported_quantity")
    off = read(service, monkeypatch, False, text, "was 5 s", RUN, (), item)
    on = read(service, monkeypatch, True, text, "was 5 s", RUN, (), item)
    whole = read(service, monkeypatch, True, text, text, RUN, (), item)
    assert "QUANTITY_NAME_NOT_IN_SOURCE_SUPPORT" in off["reasons"]
    assert (on["status"], on["reasons"]) == (whole["status"], whole["reasons"])


def records_of(service, monkeypatch, on, text, items):
    """The quantity records of ``text`` for several proposals (item, quote) on one run."""
    monkeypatch.setenv(FLAG, "1" if on else "0")
    p = submitted(service, "II. Results\n" + text + "\n")
    o = Output().model_dump()
    o["entities"] = [entity(p, "n", *SHEET, text)]
    o["quantities"] = []
    for item, quote in items:
        q = quantity(p, quote, "n", *item)
        q["support"] = support(p, quote)
        o["quantities"].append(q)
    return [r for r in validate(service, p, o)["records"] if r["kind"] == "quantities"]


CONFLICT = "CONFLICTING_ROLE_PROPOSALS_FOR_SAME_SOURCE_SPAN"


def test_two_trims_of_one_value_in_two_roles_still_collide(service, monkeypatch):
    text = "The Alpha sheet had an ignition temperature of 410 C in the burn."
    config = ("ignition temperature", "410", "C", "experimental_configuration")
    result = ("ignition temperature", "410", "C", "reported_quantity")
    for on in (False, True):
        rows = records_of(
            service,
            monkeypatch,
            on,
            text,
            [(config, text), (result, "Alpha sheet had an ignition temperature of 410 C in")],
        )
        assert all(CONFLICT in r["reasons"] for r in rows), [r["reasons"] for r in rows]


def test_two_different_values_of_one_sentence_do_not_collide(service, monkeypatch):
    text = "The Alpha sheet had an ignition temperature of 410 C and a burn time of 9 s."
    pressure = ("ignition temperature", "410", "C", "experimental_configuration")
    held = ("burn time", "9", "s", "reported_quantity")
    for on in (False, True):
        rows = records_of(service, monkeypatch, on, text, [(pressure, text), (held, text)])
        assert not any(CONFLICT in r["reasons"] for r in rows), [r["reasons"] for r in rows]


def test_a_partner_trimmed_to_lose_its_unit_still_collides(service, monkeypatch):
    text = "The Alpha sheet had an ignition temperature of 410 C in the burn."
    config = ("ignition temperature", "410", "C", "experimental_configuration")
    result = ("ignition temperature", "410", "C", "reported_quantity")
    cut = "The Alpha sheet had an ignition temperature of 410"
    off = records_of(service, monkeypatch, False, text, [(config, text), (result, cut)])
    on = records_of(service, monkeypatch, True, text, [(config, text), (result, cut)])
    assert not any(CONFLICT in r["reasons"] for r in off)
    assert [r["status"] for r in off][1] == "REJECTED"
    assert all(CONFLICT in r["reasons"] for r in on), [(r["status"], r["reasons"]) for r in on]

