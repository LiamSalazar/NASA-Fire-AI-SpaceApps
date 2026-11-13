"""A concept the model proposes reaches the same staging as an unlisted term.

Synthetic text and a controlled stand-in for the model; no live call, no NASA data.
"""

import json

from test_document_extraction import client_for, entity, submitted, support
from test_document_extraction import service as _service

from nasa_fire_ai.config import Settings
from nasa_fire_ai.ingestion.document_extraction import ExtractionBudget, Output
from nasa_fire_ai.ingestion.proposal_states import identifier, structural_validation

service = _service
TEXT = "II. Methods\nRun A1 used a porous radiative shield above the sample.\n"
SENTENCE = "Run A1 used a porous radiative shield above the sample."


def concept(package, kind, term, parent=None):
    return {
        "kind": kind,
        "term": term,
        "definition": "A shield the source describes above the sample.",
        "parent_or_existing": parent,
        "why_existing_insufficient": "No approved term names this shield.",
        "support": support(package, SENTENCE),
    }


def prepare(service, concepts, text=TEXT):
    package = submitted(service, text)
    output = Output().model_dump()
    output["entities"] = [entity(package, "a1", "A1", "ExperimentalRun", SENTENCE)]
    output["concepts"] = [concept(package, *c) for c in concepts]
    result = service.prepare_scientific(
        package["id"],
        Settings(root=service.root),
        model_enabled=True,
        budget=ExtractionBudget(max_model_calls=3, max_total_tokens=100000),
        client=client_for(output),
    )
    return result


def staged_rows(service):
    return [
        json.loads(row[0])
        for row in service.registry.db.execute(
            "SELECT payload_json FROM semantic_staging WHERE candidate_type='ontology_extension'"
        )
    ]


def test_a_printed_new_concept_is_staged_with_its_printed_name_and_never_activated(service):
    result = prepare(service, [("class", "porous radiative shield")])
    extraction = result["package"]["scientific_extraction"]
    (proposal,) = [p for p in extraction["ontology_extension_proposals"] if p["kind"] == "class"]
    assert proposal["term"] == "PorousRadiativeShield"
    assert proposal["printed_labels"] == ["porous radiative shield"]
    # The model's wording of the meaning is kept apart from a source definition.
    assert proposal["definition"] == "NOT_ESTABLISHED_BY_SOURCE"
    assert proposal["proposed_definition"]
    assert proposal["structural_validation"]["placement"] == (
        "PARENT_NOT_ESTABLISHED_REQUIRES_REVIEW"
    )
    assert [s["raw_label"] for s in staged_rows(service)] == ["PorousRadiativeShield"]
    assert (
        "PorousRadiativeShield" not in service.property_registry(result["package"]).class_metadata
    )


def test_a_concept_restating_an_approved_term_is_reused_not_staged(service):
    # Metamorphic: the same flow with an approved term printed in the source.
    result = prepare(service, [("class", "sample")])
    extraction = result["package"]["scientific_extraction"]
    assert not [p for p in extraction["ontology_extension_proposals"] if p["kind"] == "class"]
    record = next(r for r in extraction["records"] if r["kind"] == "concepts")
    assert "EXISTING_CONCEPT_REUSE_REQUIRED" in record["reasons"]


def test_a_concept_the_source_does_not_print_is_rejected(service):
    result = prepare(service, [("class", "thermal blanket")])
    record = next(
        r for r in result["package"]["scientific_extraction"]["records"] if r["kind"] == "concepts"
    )
    assert record["status"] == "REJECTED" and "CONCEPT_TERM_ABSENT" in record["reasons"]


def test_an_unplaced_relation_and_an_unapproved_parent_are_staged_but_not_well_formed():
    approved = {"class": {"Material", "Sample"}, "relation": {"madeOf"}, "property": set()}
    relation = {
        "kind": "relation",
        "term": "shieldsSample",
        "evidence": [{"evidence_id": "E", "quote": "q"}],
        "activation": "NONE",
    }
    assert "RELATION_DOMAIN_OR_RANGE_UNKNOWN" in structural_validation(relation, approved)["errors"]
    unplaced = {
        "kind": "class",
        "term": "PorousShield",
        "parent": "Shield",
        "evidence": [{"evidence_id": "E", "quote": "q"}],
        "activation": "NONE",
    }
    assert "PARENT_NOT_APPROVED" in structural_validation(unplaced, approved)["errors"]


def test_an_alias_must_name_an_approved_term():
    approved = {"class": {"Material"}, "relation": set(), "property": set()}
    alias = {
        "kind": "alias",
        "term": "fuelMaterial",
        "alias_of": "Material",
        "evidence": [{"evidence_id": "E", "quote": "q"}],
        "activation": "NONE",
    }
    assert "ALIAS_TARGET_NOT_APPROVED" not in structural_validation(alias, approved)["errors"]
    alias["alias_of"] = "Shield"
    assert "ALIAS_TARGET_NOT_APPROVED" in structural_validation(alias, approved)["errors"]


def test_identifiers_keep_their_kind_convention():
    assert identifier("porous radiative shield", "class") == "PorousRadiativeShield"
    assert identifier("shields the sample", "relation") == "shieldsTheSample"
    assert identifier("IgniterCoil", "class") == "IgniterCoil"


def test_production_relation_reuse_reads_the_enforced_endpoint_contract(service):
    # A staged relation between a run and a material is compared with the approved
    # relations that link those classes, not with every approved relation.
    from nasa_fire_ai.ingestion.document_extraction import RELATION_ENDPOINTS, extraction_semantic
    from nasa_fire_ai.ingestion.ontology_context import relation_signatures

    semantic = extraction_semantic(service, submitted(service, TEXT))
    approved = {
        "relation": set(semantic.relations),
        "relation_endpoints": relation_signatures(semantic, RELATION_ENDPOINTS),
    }
    proposal = {
        "kind": "relation",
        "term": "shieldedWith",
        "domain": ["ExperimentalRun"],
        "range": ["Material"],
        "evidence": [{"evidence_id": "E", "quote": "q"}],
        "activation": "NONE",
    }
    found = structural_validation(proposal, approved)["reuse_analysis"]
    assert "hasMaterial" in found["approved_relations_with_compatible_endpoints"]
    assert "hasPhenomenon" not in found["approved_relations_with_compatible_endpoints"]
