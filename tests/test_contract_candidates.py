"""Contract readings C2-C4 (flags SCIENCE_CONTRACT_C2..C4; C2 on by default since Diego's decision,
C3 off again on his later decision, C4 off): each reads one more general linguistic form;
with its flag off the earlier reading holds. Synthetic text."""

import pytest
from test_document_extraction import entity, submitted, support, validate
from test_document_extraction import service as _service

from nasa_fire_ai.ingestion.document_extraction import Output, role_errors

service = _service


def configuration_reasons(service, text):
    p = submitted(service, f"II. Methods\nRun A1 was set up.\n{text}\n")
    o = Output().model_dump()
    o["entities"] = [entity(p, "a1", "A1", "ExperimentalRun", "Run A1 was set up")]
    o["statements"] = [
        {
            "subjects": ["a1"],
            "text": text,
            "class_id": "ExperimentalCondition",
            "epistemic": "experimental_configuration",
            "study": "current",
            "support": support(p, text),
        }
    ]
    (record,) = [r for r in validate(service, p, o)["records"] if r["kind"] == "statements"]
    return record["reasons"]


def test_a_derived_value_is_not_an_observation():
    item = {
        "text": "The mould drift proved to be below the projected value (for any assumed cure).",
        "epistemic": "measured_observation",
    }
    assert "DERIVED_IS_NOT_OBSERVATION" in role_errors(item)


# --- with SCIENCE_PURPOSE_READER on, the readings above change by design -------------------
def test_the_purpose_reader_reads_the_set_up_class_not_the_phrase_c2(service, monkeypatch):
    reason = "CONFIGURATION_ROLE_NOT_ESTABLISHED_IN_ORIGINAL_PASSAGE"
    monkeypatch.setenv("SCIENCE_CONTRACT_C2", "1")
    monkeypatch.setenv("SCIENCE_PURPOSE_READER", "1")
    # "adjusted" belongs to the class; "tested in" alone is execution, not set-up.
    assert reason not in configuration_reasons(service, "The heater of Run A1 was adjusted twice.")
    assert reason in configuration_reasons(service, "Four slabs were tested in Run A1.")


# --- the reader is on by default; with it off, the two set-up phrases no longer trigger ----


def test_the_purpose_reader_is_on_by_default(service, monkeypatch):
    monkeypatch.delenv("SCIENCE_PURPOSE_READER", raising=False)
    monkeypatch.setenv("SCIENCE_CONTRACT_C2", "1")
    reason = "CONFIGURATION_ROLE_NOT_ESTABLISHED_IN_ORIGINAL_PASSAGE"
    # The set-up class reads "adjusted"; with the reader off this sentence would be refused.
    assert reason not in configuration_reasons(service, "The valve of Run A1 was adjusted twice.")
    monkeypatch.setenv("SCIENCE_PURPOSE_READER", "0")
    assert reason in configuration_reasons(service, "The valve of Run A1 was adjusted twice.")


@pytest.mark.parametrize(
    "text",
    ["Six coupons were tested in Run A1.", "The valve of Run A1 was adjusted twice."],
)
def test_with_the_reader_off_the_two_phrases_no_longer_trigger(service, monkeypatch, text):
    monkeypatch.setenv("SCIENCE_PURPOSE_READER", "0")
    monkeypatch.setenv("SCIENCE_CONTRACT_C2", "1")
    reason = "CONFIGURATION_ROLE_NOT_ESTABLISHED_IN_ORIGINAL_PASSAGE"
    assert reason in configuration_reasons(service, text)
