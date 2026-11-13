"""Through the normal service: a new concept is staged for review and the baseline is untouched.

Synthetic text and a controlled stand-in for the model; no live call, no NASA data.
"""

import json

from test_document_extraction import client_for, entity, submitted
from test_document_extraction import service as _service

from nasa_fire_ai.config import Settings
from nasa_fire_ai.ingestion.document_extraction import ExtractionBudget, Output

service = _service
TEXT = "II. Methods\nRun A1 used the Beta igniter coil to ignite the sample.\n"


def test_a_new_concept_reaches_review_staging_without_touching_the_baseline(service):
    package = submitted(service, TEXT)
    output = Output().model_dump()
    sentence = "Run A1 used the Beta igniter coil to ignite the sample."
    output["entities"] = [entity(package, "c", "Beta igniter coil", "IgniterCoil", sentence)]
    result = service.prepare_scientific(
        package["id"],
        Settings(root=service.root),
        model_enabled=True,
        budget=ExtractionBudget(max_model_calls=3, max_total_tokens=100000),
        client=client_for(output),
    )
    extraction = result["package"]["scientific_extraction"]
    (proposal,) = [p for p in extraction["ontology_extension_proposals"] if p["kind"] == "class"]
    assert proposal["term"] == "IgniterCoil" and proposal["structural_validation"]["well_formed"]
    staged = [
        json.loads(row[0])
        for row in service.registry.db.execute(
            "SELECT payload_json FROM semantic_staging WHERE candidate_type='ontology_extension'"
        )
    ]
    assert [s["raw_label"] for s in staged] == ["IgniterCoil"]
    assert staged[0]["resolution_status"] == "CANDIDATE_NEW_CONCEPT"
    assert staged[0]["review_status"] == "PENDING"
    item = next(
        i for i in result["package"]["proposed_extension_items"] if i["term"] == "IgniterCoil"
    )
    assert item["included"] is False
    # The approved vocabulary is unchanged: staging never activates a term.
    assert "IgniterCoil" not in service.property_registry(result["package"]).class_metadata
