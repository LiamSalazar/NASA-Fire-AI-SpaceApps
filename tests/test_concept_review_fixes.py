"""Fixes from the review of concept staging and candidate linking; synthetic terms only."""

import pytest

from nasa_fire_ai.ingestion.proposal_states import (
    identifier,
    structural_validation,
    vocabulary_extension_proposals,
)
from nasa_fire_ai.ingestion.semantic_candidates import link_proposals, repeated_terms

EVIDENCE = [{"evidence_id": "E-1", "quote": "a printed term"}]
APPROVED = {
    "class": {"FlameSpread", "Ignition", "Material", "ExperimentalRun"},
    "information_class": set(),
    "relation": {"hasMaterial"},
    "property": {"OxygenConcentration"},
    "aliases": {"flamespread": "FlameSpread", "o2": "OxygenConcentration"},
    "relation_endpoints": {},
}


def proposal(kind, term, **extra):
    return {"kind": kind, "term": term, "evidence": EVIDENCE, "activation": "NONE", **extra}


# 5. A term of another kind or an alias of another term is not a new term.
@pytest.mark.parametrize(
    ("kind", "term", "error"),
    [
        ("property", "flameSpread", "TERM_EQUIVALENT_TO_AN_APPROVED_TERM_OF_ANOTHER_KIND"),
        ("class", "OxygenConcentration", "TERM_EQUIVALENT_TO_AN_APPROVED_TERM_OF_ANOTHER_KIND"),
    ],
)
def test_a_term_approved_under_another_kind_is_not_new(kind, term, error):
    result = structural_validation(proposal(kind, term), APPROVED)
    assert error in result["errors"] and not result["well_formed"]


def test_an_alias_whose_words_name_another_approved_term_is_refused():
    result = structural_validation(
        proposal("alias", "flame spread", alias_of=["Ignition"]), APPROVED
    )
    assert "ALIAS_NAMES_ANOTHER_APPROVED_TERM" in result["errors"]
    # Metamorphic: the same words as a variant of the term they already name are fine.
    same = structural_validation(
        proposal("alias", "flame spread", alias_of=["FlameSpread"]), APPROVED
    )
    assert "ALIAS_NAMES_ANOTHER_APPROVED_TERM" not in same["errors"]


def concept_record(rid, kind, term, parent=None):
    return {
        "id": rid,
        "kind": "concepts",
        "status": "UNRESOLVED",
        "proposal_state": "PROPOSED_ONTOLOGY_EXTENSION",
        "reasons": ["ONTOLOGY_EXTENSION_REVIEW"],
        "support_spans": [{"evidence_id": "E-1", "start": 0, "end": 5, "quote": "q"}],
        "proposal": {"kind": kind, "term": term, "parent_or_existing": parent},
    }


# 6. An approved term in its printed words links to that term and stages nothing.
def test_an_approved_term_in_printed_words_is_linked_not_staged():
    record = concept_record("r", "class", "experimental runs")
    assert vocabulary_extension_proposals([record], {}, APPROVED) == []
    assert record["reuses_approved_term"] == "ExperimentalRun"


# 7. One normalization; siblings that differ only in case or plural are one proposal.
@pytest.mark.parametrize(
    ("term", "kind", "expected"),
    [
        ("shroud", "class", "Shroud"),
        ("Shrouds", "class", "Shroud"),
        ("Ignites", "relation", "ignites"),
        ("ignites sample", "relation", "ignitesSample"),
        ("α-phase layer", "class", "AlphaPhaseLayer"),
        ("β-phase layer", "class", "BetaPhaseLayer"),
        ("burning rates", "property", "burningRate"),
    ],
)
def test_identifiers_follow_one_normalization(term, kind, expected):
    assert identifier(term, kind) == expected


def test_case_and_plural_siblings_are_one_proposal():
    records = [concept_record("a", "class", "Shroud"), concept_record("b", "class", "shrouds")]
    staged = vocabulary_extension_proposals(records, {}, APPROVED)
    assert [p["term"] for p in staged] == ["Shroud"]
    assert sorted(staged[0]["supporting_records"]) == ["a", "b"]


# 8. An unapproved parent places nothing; aliases and properties are not subclasses.
def test_placement_needs_an_approved_parent_and_a_class():
    unplaced = structural_validation(proposal("class", "PorousShield", parent="Shield"), APPROVED)
    assert "PARENT_NOT_APPROVED" in unplaced["errors"]
    assert unplaced["placement"] == "PARENT_NOT_ESTABLISHED_REQUIRES_REVIEW"
    alias = structural_validation(
        proposal("alias", "spread", alias_of=["FlameSpread"], parent="X"), APPROVED
    )
    assert alias["placement"] == "ALIAS_OF_APPROVED_TERM" and "parent_candidate" not in alias
    prop = structural_validation(proposal("property", "charDepth", parent="Material"), APPROVED)
    assert prop["placement"] == "PROPERTY" and "parent_candidate" not in prop
    # Without the approved vocabulary nothing is placed (fails closed).
    blind = structural_validation(proposal("class", "PorousShield", parent="Material"), {})
    assert "PARENT_NOT_APPROVED" in blind["errors"] and "parent_candidate" not in blind


# 9. Two printed uses naming different targets are a conflict, in any order.
def test_conflicting_alias_targets_are_kept_and_refused():
    for order in ((0, 1), (1, 0)):
        records = [
            concept_record("a", "alias", "spread rate", "FlameSpread"),
            concept_record("b", "alias", "spread rate", "Ignition"),
        ]
        (staged,) = vocabulary_extension_proposals([records[i] for i in order], {}, APPROVED)
        assert staged["alias_of"] == ["FlameSpread", "Ignition"]
        assert "ALIAS_TARGET_CONFLICT" in staged["structural_validation"]["errors"]


# 10. A candidate the approved vocabulary covers is a duplicate, not a link.
def test_a_covered_candidate_is_a_duplicate_of_approved_vocabulary():
    staged = {"id": "p", "term": "FlameSpread", "printed_labels": ["flame spread"]}
    inventory = [
        {
            "id": "candidate-flame-spread",
            "label": "flame spread",
            "coverage": "COVERED",
            "approved_term": "FlameSpread",
        }
    ]
    (trace,) = link_proposals([staged], inventory)
    assert trace["decision"] == "DUPLICATE_OF_APPROVED" and "source_candidate" not in staged


# 11. Generic printed terms survive mining whatever their word endings.
@pytest.mark.parametrize(
    "term",
    [
        "burning rate",
        "melting point",
        "heating rate",
        "flame speed",
        "oxygen supply",
        "valve assembly",
        "coating thickness",
        "limiting oxygen index",
    ],
)
def test_generic_terms_are_mined_whatever_their_endings(term):
    text = f"The {term} was recorded. The {term} was reported again."
    assert term in {t.lower() for t in repeated_terms(text)}
