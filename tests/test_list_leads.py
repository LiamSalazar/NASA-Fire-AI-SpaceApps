"""A line that opens a list is the lead of its items, not a statement; synthetic text."""

import pytest
from test_document_extraction import entity, submitted, support, validate
from test_document_extraction import service as _service

from nasa_fire_ai.ingestion.document_extraction import Output

service = _service
TEXT = (
    "II. Methods\nRun A1 used three coupon types.\n"
    "• Coupon types tested:\n• Layered felt\n• Woven mesh\n"
    "Run A1 burned the woven mesh to 9 cm.\n"
)


def statement(p, text, role="documentary_context"):
    return {
        "subjects": ["a1"],
        "text": text,
        "epistemic": role,
        "study": "current",
        "support": support(p, text),
    }


@pytest.mark.parametrize("lead", ["• Coupon types tested:", "Coupon types tested:"])
def test_a_list_lead_is_not_a_statement(service, lead):
    p = submitted(service, TEXT)
    o = Output().model_dump()
    o["entities"] = [entity(p, "a1", "A1", "ExperimentalRun", "Run A1 used")]
    o["statements"] = [statement(p, lead)]
    (record,) = [r for r in validate(service, p, o)["records"] if r["kind"] == "statements"]
    assert record["status"] == "REJECTED" and "STATEMENT_IS_A_LIST_LEAD" in record["reasons"]


def test_a_sentence_with_a_colon_inside_is_still_a_statement(service):
    # Metamorphic: a colon inside a sentence does not make it a list lead.
    p = submitted(service, TEXT)
    o = Output().model_dump()
    o["entities"] = [entity(p, "a1", "A1", "ExperimentalRun", "Run A1 used")]
    o["statements"] = [
        statement(p, "Run A1 burned the woven mesh to 9 cm.", "measured_observation")
    ]
    (record,) = [r for r in validate(service, p, o)["records"] if r["kind"] == "statements"]
    assert "STATEMENT_IS_A_LIST_LEAD" not in record["reasons"]
