"""The model may propose a term the vocabulary lacks; it is staged, never approved; synthetic."""

import pytest
from test_document_extraction import entity, submitted, validate
from test_document_extraction import service as _service

from nasa_fire_ai.ingestion.document_extraction import (
    PROPOSE_NEW_CLASS,
    PROPOSE_NEW_RELATION,
    Output,
)

service = _service

TEXT = (
    "II. Methods\nRun A1 used the Beta igniter coil. Run A1 was ignited by the Beta igniter coil.\n"
)


def run(service, proposed_class):
    p = submitted(service, TEXT)
    o = Output().model_dump()
    item = entity(p, "c", "Beta igniter coil", PROPOSE_NEW_CLASS, "the Beta igniter coil. ")
    item["proposed_class"] = proposed_class
    o["entities"] = [item]
    Output.model_validate(o)  # the request shape accepts the proposal
    return validate(service, p, o)


def test_a_proposed_class_with_an_approved_parent_is_staged_with_that_parent(service):
    result = run(service, {"term": "IgniterCoil", "parent": "Intervention"})
    (record,) = [r for r in result["records"] if r["kind"] == "entities"]
    assert record["proposal"]["class_id"] == "IgniterCoil"
    assert record["proposal_state"] == "PROPOSED_ONTOLOGY_EXTENSION"
    (proposal,) = [p for p in result["ontology_extension_proposals"] if p["kind"] == "class"]
    assert proposal["parent"] == "Intervention" and proposal["activation"] == "NONE"
    assert proposal["structural_validation"]["placement"] == "PARENT_CANDIDATE_REQUIRES_REVIEW"


def test_an_approved_term_given_through_the_sentinel_is_that_term(service):
    # Metamorphic: proposing an approved term is choosing it; nothing is staged.
    result = run(service, {"term": "Material", "parent": "Material"})
    (record,) = [r for r in result["records"] if r["kind"] == "entities"]
    assert record["proposal"]["class_id"] == "Material"
    assert not [p for p in result["ontology_extension_proposals"] if p["kind"] == "class"]


@pytest.mark.parametrize(
    "proposed,reason",
    [
        (None, "PROPOSED_TERM_NOT_NAMED"),
        ({"term": "IgniterCoil", "parent": "Gadget"}, "PROPOSED_TERM_PARENT_NOT_APPROVED"),
    ],
)
def test_a_sentinel_without_a_term_or_with_an_unapproved_parent_is_rejected(
    service, proposed, reason
):
    result = run(service, proposed)
    (record,) = [r for r in result["records"] if r["kind"] == "entities"]
    assert record["status"] == "REJECTED" and reason in record["reasons"]


def test_the_sentinels_are_never_approved_vocabulary(service):
    assert PROPOSE_NEW_CLASS not in service.semantic.class_metadata
    assert PROPOSE_NEW_RELATION not in service.semantic.relations


def test_the_request_offers_the_sentinels_with_their_instruction(service):
    from test_document_extraction import client_for
    from test_phase1_closure import _requests

    from nasa_fire_ai.config import Settings
    from nasa_fire_ai.ingestion.document_extraction import ExtractionBudget

    p = submitted(service, TEXT)
    o = Output().model_dump()
    o["entities"] = [entity(p, "a1", "A1", "ExperimentalRun", "Run A1 used")]
    client = client_for(o)
    service.prepare_scientific(
        p["id"],
        Settings(root=service.root),
        model_enabled=True,
        budget=ExtractionBudget(max_model_calls=8),
        client=client,
    )
    payloads = [payload for _prompt, payload in _requests(client)]
    identity = [x for x in payloads if x["stage"] == "identity"]
    assert identity and all(
        PROPOSE_NEW_CLASS in x["schema"]["$defs"]["Entity"]["properties"]["class_id"]["enum"]
        and PROPOSE_NEW_CLASS in x["vocabulary_extension"]
        for x in identity
    )
    for x in payloads:
        if "Relation" in x["schema"]["$defs"]:
            assert (
                PROPOSE_NEW_RELATION
                in (x["schema"]["$defs"]["Relation"]["properties"]["relation"]["enum"])
            )
