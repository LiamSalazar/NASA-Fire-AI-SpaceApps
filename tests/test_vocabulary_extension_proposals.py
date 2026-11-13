"""Unknown vocabulary becomes a staged extension proposal, never a silent loss; synthetic text."""

from test_document_extraction import entity, submitted, support, validate
from test_document_extraction import service as _service

from nasa_fire_ai.ingestion.document_extraction import Output

service = _service

TEXT = (
    "II. Methods\nRun A1 used the Beta igniter coil. Run A1 was ignited by the Beta igniter coil.\n"
)


def run(service, entities, relations=()):
    p = submitted(service, TEXT)
    o = Output().model_dump()
    o["entities"] = [entity(p, *e) for e in entities]
    o["relations"] = [
        {"subject": s, "relation": rel, "object": ob, "support": support(p, quote)}
        for s, rel, ob, quote in relations
    ]
    return validate(service, p, o)


def test_a_registered_class_is_reused_and_proposes_nothing(service):
    result = run(service, [("a1", "A1", "ExperimentalRun", "Run A1 used")])
    (record,) = [r for r in result["records"] if r["kind"] == "entities"]
    assert record["proposal_state"] in {"SOURCE_SUPPORTED", "STRUCTURALLY_WELL_FORMED"}
    assert not [p for p in result.get("ontology_extension_proposals", []) if p["kind"] == "class"]


def test_an_unknown_class_with_valid_evidence_is_a_staged_class_proposal(service):
    result = run(service, [("c", "Beta igniter coil", "IgniterCoil", "the Beta igniter coil. ")])
    (record,) = [r for r in result["records"] if r["kind"] == "entities"]
    assert record["reasons"] == ["UNREGISTERED_CLASS_NEEDS_SEMANTIC_REVIEW"]
    assert record["proposal_state"] == "PROPOSED_ONTOLOGY_EXTENSION"
    (proposal,) = [p for p in result["ontology_extension_proposals"] if p["kind"] == "class"]
    assert proposal["term"] == "IgniterCoil" and proposal["instances"] == ["Beta igniter coil"]
    assert (
        proposal["activation"] == "NONE" and proposal["definition"] == "NOT_ESTABLISHED_BY_SOURCE"
    )
    assert proposal["evidence"] and proposal["supporting_records"] == [record["id"]]
    assert proposal["structural_validation"]["well_formed"]


def relation_result(service, relation):
    text = (
        "Run A1 was tested in microgravity at airflow velocity 20 cm/s.\nA1 flame extinguished.\n"
    )
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [
        entity(p, "a1", "A1", "ExperimentalRun", text),
        entity(p, "mg", "microgravity", "ExperimentalCondition", text),
    ]
    o["relations"] = [
        {"subject": "a1", "object": "mg", "relation": relation, "support": support(p, text)}
    ]
    return validate(service, p, o)


def test_an_unknown_relation_between_known_entities_records_its_domain_and_range(service):
    # Metamorphic: the same edge with an approved relation needs no proposal.
    approved = relation_result(service, "hasGravityCondition")
    (edge,) = [r for r in approved["records"] if r["kind"] == "relations"]
    assert edge["status"] == "SOURCE_SUPPORTED"
    assert not [p for p in approved["ontology_extension_proposals"] if p["kind"] == "relation"]
    result = relation_result(service, "testedUnderCondition")
    (record,) = [r for r in result["records"] if r["kind"] == "relations"]
    assert "UNREGISTERED_RELATION" in record["reasons"]
    assert record["proposal_state"] == "PROPOSED_ONTOLOGY_EXTENSION"
    (proposal,) = [p for p in result["ontology_extension_proposals"] if p["kind"] == "relation"]
    assert proposal["term"] == "testedUnderCondition"
    assert proposal["domain"] == ["ExperimentalRun"] and proposal["range"] == [
        "ExperimentalCondition"
    ]


def test_an_unknown_class_with_another_open_problem_is_not_called_an_extension(service):
    # Negative: the class is unknown and the label is not printed in its support.
    result = run(service, [("c", "Gamma heater", "IgniterCoil", "the Beta igniter coil. ")])
    (record,) = [r for r in result["records"] if r["kind"] == "entities"]
    assert record["proposal_state"] != "PROPOSED_ONTOLOGY_EXTENSION"
    assert not [p for p in result.get("ontology_extension_proposals", []) if p["kind"] == "class"]
