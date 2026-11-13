"""Ontology snippets are built from the real ontology and registry, per class in play.

Synthetic package; the semantics are the repository's approved ontology.
"""

import pytest
from test_document_extraction import service as _service
from test_document_extraction import submitted

from nasa_fire_ai.ingestion.document_extraction import RELATION_ENDPOINTS, extraction_semantic
from nasa_fire_ai.ingestion.ontology_context import ontology_context, snippet

service = _service


@pytest.fixture
def semantic(service):
    return extraction_semantic(service, submitted(service, "Run A1 burned.\n"))


def test_a_criterion_sees_its_place_among_the_normative_statements(semantic):
    found = snippet("TestCriterion", semantic, RELATION_ENDPOINTS)
    assert found["status"] == "APPROVED"
    assert found["ancestors"][:2] == ["NormativeStatement", "SafetyKnowledge"]
    siblings = snippet("NormativeStatement", semantic, RELATION_ENDPOINTS)["children"]
    assert {"DesignCriterion", "TestCriterion", "Requirement", "Guidance"} <= set(siblings)


def test_a_subclass_inherits_the_relations_of_its_ancestors(semantic):
    # PressureCondition is never named by a relation contract; ExperimentalCondition is.
    inherited = snippet("PressureCondition", semantic, RELATION_ENDPOINTS)
    assert "ExperimentalCondition" in inherited["ancestors"]
    assert "hasCondition" in {r["relation"] for r in inherited["relations_as_object"]}
    # Metamorphic: an unrelated class does not inherit it.
    phenomenon = snippet("Ignition", semantic, RELATION_ENDPOINTS)
    assert "hasCondition" not in {r["relation"] for r in phenomenon["relations_as_object"]}


def test_a_class_outside_the_ontology_is_reported_as_such(semantic):
    assert snippet("IgniterCoil", semantic)["status"] == "NOT_IN_APPROVED_ONTOLOGY"


def test_staged_terms_are_context_never_approved(semantic):
    staged = [
        {
            "kind": "class",
            "term": "IgniterCoil",
            "parent": "Intervention",
            "status": "STAGED_FOR_ONTOLOGY_REVIEW",
        }
    ]
    context = ontology_context(["Material"], semantic, RELATION_ENDPOINTS, staged)
    assert context["staged"] == [
        {
            "term": "IgniterCoil",
            "kind": "class",
            "status": "STAGED_FOR_ONTOLOGY_REVIEW",
            "parent": "Intervention",
        }
    ]
    assert all(s["class"] != "IgniterCoil" for s in context["approved"])


def test_the_context_is_stable_whatever_the_order_of_the_classes(semantic):
    one = ontology_context(["Sample", "Material", "Sample"], semantic, RELATION_ENDPOINTS)
    other = ontology_context(["Material", "Sample"], semantic, RELATION_ENDPOINTS)
    assert one == other


def propositions_requests(service, monkeypatch, enabled):
    from test_document_extraction import client_for, entity
    from test_phase1_closure import _requests

    from nasa_fire_ai.config import Settings
    from nasa_fire_ai.ingestion.document_extraction import ExtractionBudget, Output

    monkeypatch.setenv("SCIENCE_ONTOLOGY_CONTEXT", "1" if enabled else "0")
    text = "II. Methods\nRun A1 used a coil. Run A1 burned for a short time.\n"
    p = submitted(service, text)
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
    return [x for _prompt, x in _requests(client) if x["stage"] == "propositions"]


def test_the_ontology_context_is_off_by_default(service, monkeypatch):
    payloads = propositions_requests(service, monkeypatch, enabled=False)
    assert payloads and not any("ontology_context" in x for x in payloads)


def test_the_request_carries_snippets_for_the_classes_in_play(service, monkeypatch):
    payloads = propositions_requests(service, monkeypatch, enabled=True)
    for payload in payloads:
        classes = {s["class"] for s in payload["ontology_context"]["approved"]}
        # The known entities' classes and the approved statement classes, never a
        # global dump of the ontology.
        assert {e["class_id"] for e in payload["known_entities"]} <= classes
        assert {"TestCriterion", "ReportedObservation"} <= classes
        assert "Ignition" not in classes


def test_preparing_an_unchanged_package_again_sends_nothing_new(service, monkeypatch):
    from test_document_extraction import client_for, entity

    from nasa_fire_ai.config import Settings
    from nasa_fire_ai.ingestion.document_extraction import ExtractionBudget, Output

    monkeypatch.setenv("SCIENCE_ONTOLOGY_CONTEXT", "1")
    text = "II. Methods\nRun A1 used a porous radiative shield. Run A1 burned briefly.\n"
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [entity(p, "a1", "A1", "ExperimentalRun", "Run A1 used")]
    o["concepts"] = [
        {
            "kind": "class",
            "term": "porous radiative shield",
            "definition": "A shield the source describes.",
            "parent_or_existing": None,
            "why_existing_insufficient": "No approved term names it.",
            "support": [{"evidence_id": p["evidence"][0]["evidence_id"], "quote": text.strip()}],
        }
    ]
    client = client_for(o)
    create = client.client.with_options.return_value.chat.completions.create
    run = {
        "settings": Settings(root=service.root),
        "model_enabled": True,
        "budget": ExtractionBudget(max_model_calls=8),
        "client": client,
    }
    service.prepare_scientific(p["id"], **run)
    calls = create.call_count
    # The first preparation staged a term; it must not change the next requests.
    service.prepare_scientific(p["id"], **run)
    assert create.call_count == calls


def test_rejected_superseded_and_approved_terms_are_not_offered_as_staged(semantic):
    staged = [
        {"kind": "class", "term": "PorousShield", "review_status": "PENDING"},
        {"kind": "class", "term": "OldShield", "review_status": "REJECTED"},
        {"kind": "class", "term": "PriorShield", "review_status": "SUPERSEDED"},
        {"kind": "class", "term": "Material", "review_status": "PENDING"},
    ]
    context = ontology_context([], semantic, RELATION_ENDPOINTS, staged)
    assert [s["term"] for s in context["staged"]] == ["PorousShield"]


def test_the_identity_stage_sees_the_classes_it_chooses_among(service, monkeypatch):
    from test_document_extraction import client_for, entity
    from test_phase1_closure import _requests

    from nasa_fire_ai.config import Settings
    from nasa_fire_ai.ingestion.document_extraction import (
        ExtractionBudget,
        Output,
        identity_classes,
    )

    monkeypatch.setenv("SCIENCE_ONTOLOGY_CONTEXT", "1")
    text = "II. Methods\nRun A1 burned briefly.\n"
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [entity(p, "a1", "A1", "ExperimentalRun", "Run A1 burned")]
    client = client_for(o)
    service.prepare_scientific(
        p["id"],
        Settings(root=service.root),
        model_enabled=True,
        budget=ExtractionBudget(max_model_calls=8),
        client=client,
    )
    identity = [x for _prompt, x in _requests(client) if x["stage"] == "identity"]
    semantic = extraction_semantic(service, p)
    for payload in identity:
        offered = {s["class"] for s in payload["ontology_context"]["approved"]}
        assert set(identity_classes(semantic)) <= offered


def test_extraction_and_curation_read_one_ontology(service):
    from nasa_fire_ai.ingestion.semantic import approved_ontology

    p = submitted(service, "Run A1 burned.\n")
    p["scientific_extraction"] = {"records": []}
    extraction = extraction_semantic(service, p)
    curation = service.property_registry(p)
    ontology = approved_ontology(service.root)
    assert approved_ontology(service.root) is ontology  # parsed once
    for cls, meta in ontology["classes"].items():
        assert extraction.class_metadata[cls]["approved_ontology_parents"] == meta["parents"]
        assert curation.class_metadata[cls]["approved_ontology_parents"] == meta["parents"]


def all_stage_requests(service, monkeypatch, flags):
    from test_document_extraction import client_for, entity
    from test_phase1_closure import _requests

    from nasa_fire_ai.config import Settings
    from nasa_fire_ai.ingestion.document_extraction import ExtractionBudget, Output

    for flag in ("SCIENCE_ONTOLOGY_CONTEXT", "SCIENCE_CANDIDATE_CONTRACT"):
        monkeypatch.setenv(flag, "1" if flag in flags else "0")
    text = (
        "II. Methods\nRun A1 used a porous radiative shield. Run A1 burned briefly.\n"
        "The porous radiative shield was replaced after each run.\n"
    )
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [entity(p, "a1", "A1", "ExperimentalRun", "Run A1 used")]
    client = client_for(o)
    service.prepare_scientific(
        p["id"],
        Settings(root=service.root),
        model_enabled=True,
        budget=ExtractionBudget(max_model_calls=12),
        client=client,
    )
    return [x for _prompt, x in _requests(client)]


@pytest.mark.parametrize(
    "flags",
    [
        {"SCIENCE_ONTOLOGY_CONTEXT"},
        {"SCIENCE_ONTOLOGY_CONTEXT", "SCIENCE_CANDIDATE_CONTRACT"},
        {"SCIENCE_CANDIDATE_CONTRACT"},
    ],
)
def test_each_request_part_travels_with_its_own_instruction(service, monkeypatch, flags):
    payloads = all_stage_requests(service, monkeypatch, flags)
    assert {x["stage"] for x in payloads} >= {"identity", "propositions", "relationships"}
    for x in payloads:
        assert ("ontology_context" in x) == ("ontology_context_use" in x), x["stage"]
        assert ("ontology_context" in x) == ("SCIENCE_ONTOLOGY_CONTEXT" in flags)
        assert ("source_term_candidates" in x) == ("source_term_contract" in x), x["stage"]
    if "SCIENCE_CANDIDATE_CONTRACT" in flags:
        assert any("source_term_candidates" in x for x in payloads)
