"""Data provenance (SCIENCE_STRUCTURED_PROVENANCE): a statement that says where the study's data
come from is its own complete record with the Publication class, read only by the existing
data-provenance reader. Off by default: the role is not in the contract. Synthetic text."""

from test_document_extraction import entity, submitted, support, validate
from test_document_extraction import service as _service

from nasa_fire_ai.evaluation.phase1_protocol import outcome
from nasa_fire_ai.ingestion.document_extraction import Output, parse_model_output, stage_schema

service = _service
FLAG = "SCIENCE_STRUCTURED_PROVENANCE"
OWN = "Synthetic study"
SOURCES = "The reference burn values were obtained from two vendor reports and a public database."
POINTER = "Table 4 lists the reference burn values."
CITED = "Lee [4] reported a lower burn rate for the same foam."


def record(service, text, role="data_provenance"):
    p = submitted(service, f"{OWN}\nII. Methods\n{text}\n")
    o = Output().model_dump()
    o["entities"] = [entity(p, "inv", OWN, "Investigation", OWN)]
    o["statements"] = [
        {
            "subjects": ["inv"],
            "text": text,
            "class_id": "Publication",
            "epistemic": role,
            "study": "current",
            "support": support(p, text),
        }
    ]
    (r,) = [x for x in validate(service, p, o)["records"] if x["kind"] == "statements"]
    return r


def test_off_by_default_the_role_is_not_in_the_contract(monkeypatch):
    monkeypatch.delenv(FLAG, raising=False)
    roles = stage_schema("propositions")["$defs"]["Statement"]["properties"]["epistemic"]["enum"]
    assert "data_provenance" not in roles
    result, errors = parse_model_output(
        '{"statements": [{"text": "x", "class_id": "Publication", "epistemic": "data_provenance",'
        ' "support": [{"evidence_id": "E1", "quote": "x", "start": 0}]}]}'
    )
    assert not result["statements"] and errors


def test_the_same_sentence_as_documentary_context_stays_retained(service, monkeypatch):
    # Metamorphic: only the role changes; documentary context is still retention.
    monkeypatch.setenv(FLAG, "1")
    assert outcome([record(service, SOURCES + " ", role="documentary_context")]) == (
        "EVIDENCE_RETAINED"
    )


def test_a_pointer_or_a_citation_is_never_provenance(service, monkeypatch):
    # Negative: neither says where the data come from in the provenance reader's sense.
    monkeypatch.setenv(FLAG, "1")
    for text in (POINTER, CITED):
        r = record(service, text)
        assert r["status"] == "REJECTED"
        assert "DATA_PROVENANCE_NOT_EXPLICIT_IN_SOURCE" in " ".join(r["reasons"])
