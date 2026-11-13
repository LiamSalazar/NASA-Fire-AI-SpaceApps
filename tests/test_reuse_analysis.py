"""Directive cases A-C and the §6 distinctions, decided from the terms; synthetic vocabulary."""

import pytest

from nasa_fire_ai.ingestion.proposal_states import structural_validation

EVIDENCE = [{"evidence_id": "E-1", "start": 0, "end": 9, "quote": "Beta coil"}]
APPROVED = {
    "class": {"ExperimentalRun", "Material", "Sample"},
    "relation": {"hasMaterial", "usesSample"},
    "relation_endpoints": {
        "hasMaterial": (["ExperimentalRun", "Sample"], ["Material"]),
        "usesSample": (["ExperimentalRun"], ["Sample"]),
    },
}


def check(kind="class", term="IgniterCoil", **extra):
    proposal = {
        "kind": kind,
        "term": term,
        "definition": "NOT_ESTABLISHED_BY_SOURCE",
        "evidence": EVIDENCE,
        "activation": "NONE",
        **extra,
    }
    return structural_validation(proposal, APPROVED)


def test_case_a_an_approved_term_written_differently_is_reused_not_extended():
    for term in ("Experimental_Run", "ExperimentalRuns"):
        result = check(term=term)
        assert result["reuse_analysis"]["case"] == "A_REUSE_APPROVED_TERM"
        assert "TERM_EQUIVALENT_TO_AN_APPROVED_TERM" in result["errors"]


def test_case_b_a_qualified_approved_class_is_a_subclass_or_attribute_for_review():
    result = check(term="MicrogravityExperimentalRun", instances=["drop tower runs"])
    assert result["well_formed"]
    assert result["reuse_analysis"]["case"] == "B_PARTIAL_EXTENSION_REVIEW"
    assert result["parent_candidate"] == "ExperimentalRun"
    assert result["placement"] == "PARENT_CANDIDATE_REQUIRES_REVIEW"


def test_case_c_genuinely_new_vocabulary():
    result = check(term="IgniterCoil", instances=["Beta coil", "Gamma coil"])
    assert result["well_formed"] and result["reuse_analysis"]["case"] == "C_NEW_VOCABULARY"
    assert result["placement"] == "PARENT_NOT_ESTABLISHED_REQUIRES_REVIEW"


@pytest.mark.parametrize(
    "term,instances",
    [("Coil3", ["Coil 3"]), ("BetaIgniterCoil", ["Beta igniter coil"])],
)
def test_a_class_named_after_its_only_instance_is_an_instance(term, instances):
    result = check(term=term, instances=instances)
    assert "TERM_NAMES_AN_INSTANCE" in result["errors"]


def test_digits_in_a_grade_or_alloy_class_ask_for_review_not_an_error():
    # Negative: a class whose name carries a grade number is legitimate vocabulary.
    result = check(term="Steel316", instances=["316 steel plate", "316 steel tube"])
    assert result["well_formed"] and "TERM_NAMES_AN_INSTANCE" not in result["errors"]
    assert result["reuse_analysis"]["warnings"] == ["TERM_MAY_NAME_AN_INSTANCE_REQUIRES_REVIEW"]


def test_a_class_with_several_instances_is_not_an_instance():
    # Negative: the same name over several documented instances is a class.
    result = check(term="IgniterCoil", instances=["Beta igniter coil", "igniter coil"])
    assert "TERM_NAMES_AN_INSTANCE" not in result["errors"]


def test_a_new_relation_between_endpoints_an_approved_relation_links_is_reviewed_as_qualified():
    result = check(kind="relation", term="burnedMaterial", domain=["Sample"], range=["Material"])
    assert result["reuse_analysis"]["approved_relations_with_compatible_endpoints"] == [
        "hasMaterial"
    ]
    assert result["reuse_analysis"]["case"] == "B_PARTIAL_EXTENSION_REVIEW"


def test_a_relation_between_endpoints_no_approved_relation_links_is_new():
    result = check(kind="relation", term="ignitedBy", domain=["Sample"], range=["IgniterCoil"])
    assert result["reuse_analysis"]["approved_relations_with_compatible_endpoints"] == []
    assert result["reuse_analysis"]["case"] == "C_NEW_VOCABULARY"


def test_a_relation_with_unknown_endpoints_is_no_evidence_of_reuse():
    # Metamorphic: the same proposal against relations whose endpoints are unknown
    # finds no compatible relation (an unknown domain is not "any class").
    unknown = {**APPROVED, "relation_endpoints": {"hasMaterial": ([], []), "usesSample": ([], [])}}
    proposal = {
        "kind": "relation",
        "term": "burnedMaterial",
        "domain": ["Sample"],
        "range": ["Material"],
        "evidence": EVIDENCE,
        "activation": "NONE",
    }
    result = structural_validation(proposal, unknown)
    assert result["reuse_analysis"]["approved_relations_with_compatible_endpoints"] == []
