"""SCIENCE_EVIDENCE_VETO_ENTITIES: the entity and relation vetoes that read the quote (often the
bare label) read the printed line(s) around the located span. Invented text only.

Each case cuts the quote of one proposal inside its printed line and checks that, with the flag
on, the cut record is never more accepted than the whole line and carries the reason the whole
line gives; with the flag off the cut quote still evades (the control).
"""

import pytest
from test_document_extraction import entity, submitted, support, validate
from test_document_extraction import service as _service
from test_phase1_closure import relation

from nasa_fire_ai.ingestion.document_extraction import Output

service = _service
FLAG = "SCIENCE_EVIDENCE_VETO_ENTITIES"
SUPPORTED = "SOURCE_SUPPORTED"
ORDER = {"REJECTED": 0, "UNRESOLVED": 1, SUPPORTED: 2}


def records(service, monkeypatch, on, text, build):
    monkeypatch.setenv(FLAG, "1" if on else "0")
    p = submitted(service, "II. Results\n" + text + "\n")
    o = Output().model_dump()
    build(p, o)
    return validate(service, p, o)["records"]


def entity_record(service, monkeypatch, on, text, quote, label, cls, study="current"):
    def build(p, o):
        o["entities"] = [entity(p, "n", label, cls, quote, study=study)]

    return records(service, monkeypatch, on, text, build)[0]


# (id, printed text, cut quote, label, class, study, statuses off/on, reason with the flag on)
ENTITY_CASES = (
    (
        "planned-run",
        "Test 7 was performed as a dry run and later cancelled.",
        "Test 7 was performed",
        "7",
        "ExperimentalRun",
        "current",
        (SUPPORTED, "REJECTED"),
        "DOCUMENTARY_OR_PLANNED_IS_NOT_EXECUTED_RUN",
    ),
    (
        "strategic-phase",
        "Phase 2 will extend the programme if funding allows.",
        "Phase 2",
        "Phase 2",
        "ExperimentFamily",
        "current",
        (SUPPORTED, "UNRESOLVED"),
        "STRATEGIC_PHASE_IS_NOT_ESTABLISHED_EXPERIMENT_GROUP",
    ),
    (
        "future-research",
        "The Alpha Experiment which will fly next year studies ignition.",
        "The Alpha Experiment",
        "Alpha Experiment",
        "Investigation",
        "current",
        (SUPPORTED, "UNRESOLVED"),
        "FUTURE_RESEARCH_IS_NOT_CURRENT_INVESTIGATION",
    ),
    (
        "cited-research",
        "Previous studies Alpha Tests reported smoldering in this blend.",
        "Alpha Tests",
        "Alpha Tests",
        "ExperimentFamily",
        "current",
        (SUPPORTED, "REJECTED"),
        "CITED_RESEARCH_IS_NOT_CURRENT_EXPERIMENT",
    ),
    (
        "test-medium",
        "The chamber was pressurized with Zeta gas before each burn.",
        "Zeta gas",
        "Zeta gas",
        "Material",
        "current",
        (SUPPORTED, "UNRESOLVED"),
        "TEST_MEDIUM_IS_NOT_A_TESTED_MATERIAL",
    ),
)


@pytest.mark.parametrize("case", ENTITY_CASES, ids=[c[0] for c in ENTITY_CASES])
def test_a_cut_entity_quote_is_read_in_its_printed_line(service, monkeypatch, case):
    _id, text, quote, label, cls, study, (off, on), reason = case
    assert quote in text and quote != text
    cut_off = entity_record(service, monkeypatch, False, text, quote, label, cls, study)
    cut_on = entity_record(service, monkeypatch, True, text, quote, label, cls, study)
    whole_on = entity_record(service, monkeypatch, True, text, text, label, cls, study)
    assert cut_off["status"] == off, cut_off["reasons"]
    assert cut_on["status"] == on, cut_on["reasons"]
    assert reason in cut_on["reasons"], cut_on["reasons"]
    assert ORDER[cut_on["status"]] <= ORDER[whole_on["status"]]


def relation_record(service, monkeypatch, on, text, quote):
    def build(p, o):
        o["entities"] = [
            entity(p, "s", "Alpha", "Sample", text),
            entity(p, "o", "21% O2", "ExperimentalCondition", text),
        ]
        o["relations"] = [relation(p, "s", "hasCondition", "o", quote)]
        o["relations"][0]["support"] = support(p, quote)

    return next(
        r for r in records(service, monkeypatch, on, text, build) if r["kind"] == "relations"
    )


RELATION_TEXT = "Alpha was burned at 21% O2 except in Run 4."
RELATION_CUT = "Alpha was burned at 21% O2"


def test_a_relation_cut_before_its_exception_is_read_in_its_printed_line(service, monkeypatch):
    off = relation_record(service, monkeypatch, False, RELATION_TEXT, RELATION_CUT)
    on = relation_record(service, monkeypatch, True, RELATION_TEXT, RELATION_CUT)
    whole = relation_record(service, monkeypatch, True, RELATION_TEXT, RELATION_TEXT)
    assert "NEGATION_OR_LOCAL_EXCEPTION_REQUIRES_REVIEW" not in off["reasons"]
    assert "NEGATION_OR_LOCAL_EXCEPTION_REQUIRES_REVIEW" in on["reasons"], on["reasons"]
    assert ORDER[on["status"]] <= ORDER[whole["status"]]


def test_the_flag_is_on_by_default_and_zero_turns_it_off(monkeypatch):
    from nasa_fire_ai.ingestion.entity_validation import evidence_veto_entities

    monkeypatch.delenv(FLAG, raising=False)
    assert evidence_veto_entities() is True
    monkeypatch.setenv(FLAG, "0")
    assert evidence_veto_entities() is False


def test_an_unplaced_span_is_held(service, monkeypatch):
    from nasa_fire_ai.ingestion import quantity_validation

    monkeypatch.setattr(quantity_validation, "printed_span", lambda span, evidence: None)
    text = "The Alpha sheet burned."
    record = entity_record(service, monkeypatch, True, text, text, "Alpha sheet", "Sample")
    assert record["status"] != SUPPORTED
    assert "ENTITY_PRINTED_LINE_NOT_LOCATED" in record["reasons"]


# ---- the two relation vetoes the first cut left out -------------------------------------------

PROVENANCE_FULL = (
    "Okafor et al. [4] report that the reference char depth values were obtained from the "
    "Marlow panel survey."
)
PROVENANCE_CUT = (
    "[4] report that the reference char depth values were obtained from the Marlow panel survey."
)


def provenance_relation(service, monkeypatch, on, quote):
    from test_structured_provenance import OWN, SOURCE, TERM
    from test_structured_provenance import build as provenance_build

    monkeypatch.setenv("SCIENCE_STRUCTURED_PROVENANCE", "1")
    monkeypatch.setenv(FLAG, "1" if on else "0")
    result = provenance_build(service, text=PROVENANCE_FULL, relation_text=quote)
    assert OWN and SOURCE and TERM
    (record,) = [r for r in result["records"] if r["kind"] == "relations"]
    return record


def test_a_cut_provenance_relation_is_read_in_its_printed_line(service, monkeypatch):
    # Flag off, the cut loses "Okafor et al.": the cited work's provenance is
    # bound as this study's. Flag on, the printed line shows the attribution and nothing binds.
    whole = provenance_relation(service, monkeypatch, True, PROVENANCE_FULL)
    off = provenance_relation(service, monkeypatch, False, PROVENANCE_CUT)
    on = provenance_relation(service, monkeypatch, True, PROVENANCE_CUT)
    assert (off.get("context_resolution") or {}).get("basis") == "STUDY_DATA_SOURCE_PRINTED", off
    assert (on.get("context_resolution") or {}).get("basis") != "STUDY_DATA_SOURCE_PRINTED", on
    assert ORDER[on["status"]] <= ORDER[whole["status"]]
    assert ORDER[on["status"]] < ORDER[off["status"]]


def test_a_provenance_relation_stays_bound_when_the_line_is_this_studys(service, monkeypatch):
    from test_structured_provenance import TEXT
    from test_structured_provenance import build as provenance_build

    monkeypatch.setenv("SCIENCE_STRUCTURED_PROVENANCE", "1")
    monkeypatch.setenv(FLAG, "1")
    result = provenance_build(service, text=TEXT)
    (record,) = [r for r in result["records"] if r["kind"] == "relations"]
    assert (record.get("context_resolution") or {}).get("basis") == "STUDY_DATA_SOURCE_PRINTED"


RIVAL_TEXT = "Beta and Alpha were burned at 21% O2 in the second series."
RIVAL_CUT = "Alpha were burned at 21% O2 in the second series."


def rival_relation(service, monkeypatch, on, quote):
    def build(p, o):
        o["entities"] = [
            entity(p, "s", "Alpha", "Sample", RIVAL_TEXT),
            entity(p, "r", "Beta", "Sample", RIVAL_TEXT),
            entity(p, "o", "21% O2", "ExperimentalCondition", RIVAL_TEXT),
        ]
        o["relations"] = [relation(p, "s", "hasCondition", "o", quote)]
        o["relations"][0]["support"] = support(p, quote)

    return next(
        r for r in records(service, monkeypatch, on, RIVAL_TEXT, build) if r["kind"] == "relations"
    )


def test_a_rival_subject_dropped_by_a_cut_is_found_in_the_printed_line(service, monkeypatch):
    whole = rival_relation(service, monkeypatch, True, RIVAL_TEXT)
    off = rival_relation(service, monkeypatch, False, RIVAL_CUT)
    on = rival_relation(service, monkeypatch, True, RIVAL_CUT)
    assert "LOCAL_SUBJECT_BINDING_UNRESOLVED" in whole["reasons"], whole
    assert "LOCAL_SUBJECT_BINDING_UNRESOLVED" not in off["reasons"], off
    assert "LOCAL_SUBJECT_BINDING_UNRESOLVED" in on["reasons"], on
    assert ORDER[on["status"]] <= ORDER[whole["status"]]
