"""An unknown study does not make another entity of a current one; synthetic, never NASA data."""

from test_document_extraction import entity, submitted, validate
from test_document_extraction import service as _service

from nasa_fire_ai.ingestion.document_extraction import (
    Output,
)

service = _service


def test_an_unknown_study_does_not_make_another_entity_of_a_current_one(service):
    text = "II. Methods\nThe drop gave microgravity. Microgravity flames were short."
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [
        entity(p, "a", "microgravity", "GravityCondition", "The drop gave microgravity."),
        entity(p, "b", "microgravity", "GravityCondition", "Microgravity flames were short."),
    ]
    o["entities"][1]["study"] = "unknown"
    records = [r for r in validate(service, p, o)["records"] if r["kind"] == "entities"]
    active = [r for r in records if r["status"] != "REJECTED" and not r.get("duplicate_of")]
    assert len(active) == 1
    assert active[0]["proposal"]["study"] == "current"
    # Negative: a cited proposal of the same name stays its own entity.
    o["entities"][1]["study"] = "cited"
    records = [r for r in validate(service, p, o)["records"] if r["kind"] == "entities"]
    assert sum(r["status"] != "REJECTED" and not r.get("duplicate_of") for r in records) == 2
