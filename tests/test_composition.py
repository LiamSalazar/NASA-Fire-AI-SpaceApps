"""Material composition read from the document's own wording, staged for review."""

from test_document_extraction import client_for, entity, submitted
from test_document_extraction import service as _service

from nasa_fire_ai.config import Settings
from nasa_fire_ai.ingestion.composition import (
    composition_assertions,
    explain,
    ontology_extension_proposals,
)
from nasa_fire_ai.ingestion.document_extraction import Output

service = _service

TEXT = (
    "Alpha-filled Beta was tested here. "
    "A similar metal filled Beta compound named Omega uses Gamma filler in Beta instead of Alpha. "
    "The composition of Omega is 40% Gamma and 60% Beta. "
    "The Gamma component of Omega is made up of 90% Delta, 8% Epsilon, and 2% Zeta. "
    "Although the percentage of Alpha in the Alpha-filled Beta is not known, it is small. "
    "The composition of Sigma is 30% Gamma and 70% Beta by weight."
)
ENTITIES = [
    {"id": "e:afb", "label": "Alpha-filled Beta", "class_id": "Material"},
    {"id": "e:omega", "label": "Omega", "class_id": "Material"},
    {"id": "e:sigma", "label": "Sigma", "class_id": "Material"},
]


def assertions():
    evidence = [{"evidence_id": "E-1", "page": 3, "text": TEXT}]
    return {
        (a["subject"]["label"], a["component"]["label"], a["context"]): a
        for a in composition_assertions(evidence, ENTITIES)
    }


def test_components_roles_and_proportions_come_from_the_wording_only():
    found = assertions()
    gamma = found[("Omega", "Gamma", None)]
    assert gamma["relation_candidate"] == "hasComponent"
    assert gamma["subject"]["entity_id"] == "e:omega"
    assert gamma["component"]["entity_status"] == "STAGED_ENTITY_PROPOSAL"
    assert gamma["role"] == "filler" and gamma["role_host"]["label"] == "Beta"
    assert gamma["proportion"] == {
        "value": 40.0,
        "unit": "%",
        "basis": "UNSPECIFIED_IN_SOURCE",
        "status": "REPORTED",
        "listed_components_sum": 100.0,
    }
    assert gamma["source_descriptor"] == "metal filled Beta compound"
    # The other listed component has no documented role.
    assert found[("Omega", "Beta", None)]["role"] is None
    assert found[("Omega", "Beta", None)]["proportion"]["value"] == 60.0
    # A stated basis is kept; an unstated one is never assumed.
    assert found[("Sigma", "Gamma", None)]["proportion"]["basis"] == "MASS"
    for record in found.values():
        assert record["lifecycle"] == "SOURCE_SUPPORTED_PENDING_REVIEW"
        assert record["activation"] == "NONE"
        assert record["evidence"] and all(e["quote"] for e in record["evidence"])


def test_a_nested_component_keeps_the_material_it_is_described_in():
    found = assertions()
    delta = found[("Gamma", "Delta", "Omega")]
    assert delta["proportion"]["value"] == 90.0
    assert ("Gamma", "Delta", None) not in found  # not the substance in general


def test_a_filled_name_and_a_documented_unknown_share():
    found = assertions()
    alpha = found[("Alpha-filled Beta", "Alpha", None)]
    assert alpha["role"] == "filler"
    assert alpha["proportion"]["status"] == "NOT_KNOWN_PER_SOURCE"
    assert alpha["proportion"]["value"] is None


def test_only_validated_materials_are_composition_subjects():
    evidence = [
        {
            "evidence_id": "E-1",
            "page": 1,
            "text": "The composition of the cabin air was 21% O2 and 79% N2.",
        }
    ]
    assert composition_assertions(evidence, ENTITIES) == []


def test_explanations_are_rendered_from_the_structured_assertion():
    found = assertions()
    text = " ".join(explain(found[("Omega", "Gamma", None)]))
    assert "Omega contains Gamma as a component." in text
    assert "Gamma acts as the filler of Omega, in Beta." in text
    assert "40% on a basis the source does not state" in text
    assert "SOURCE_SUPPORTED_PENDING_REVIEW" in text
    sigma = " ".join(explain(found[("Sigma", "Gamma", None)]))
    assert "30% by mass" in sigma
    unknown = " ".join(explain(found[("Alpha-filled Beta", "Alpha", None)]))
    assert "is not known" in unknown and "%" not in unknown


def test_the_relation_is_proposed_as_vocabulary_only_when_the_ontology_lacks_it():
    found = list(assertions().values())
    [proposal] = ontology_extension_proposals(found, {"madeOf", "hasMaterial"})
    assert proposal["term"] == "hasComponent"
    assert (proposal["domain"], proposal["range"]) == ("Material", "Material")
    assert proposal["activation"] == "NONE"
    assert proposal["status"] == "STAGED_FOR_ONTOLOGY_REVIEW"
    assert "madeOf" in proposal["why_existing_relations_do_not_fit"]
    assert ontology_extension_proposals(found, {"hasComponent"}) == []


def test_preparation_stages_composition_without_touching_the_graph(service):
    text = "The composition of Omega is 40% Gamma and 60% Beta. Omega seals were tested."
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [entity(p, "omega", "Omega", "Material", "Omega seals were tested.")]
    prepared = service.prepare_scientific(
        p["id"], Settings(root=service.root), model_enabled=True, client=client_for(o)
    )
    extraction = prepared["package"]["scientific_extraction"]
    components = {a["component"]["label"] for a in extraction["composition_proposals"]}
    assert components == {"Gamma", "Beta"}
    assert extraction["ontology_extension_proposals"][0]["term"] == "hasComponent"
    staged = service.registry.db.execute(
        "SELECT candidate_type, review_status FROM semantic_staging WHERE candidate_type IN "
        "('composition','ontology_extension')"
    ).fetchall()
    assert sorted(tuple(row) for row in staged) == [
        ("composition", "PENDING"),
        ("composition", "PENDING"),
        ("ontology_extension", "PENDING"),
    ]
