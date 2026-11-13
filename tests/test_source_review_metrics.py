"""Synthetic anti-inflation checks for independently supplied source reviews."""

import copy
import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "source_review", Path(__file__).resolve().parents[1] / "scripts/score_scientific_review.py"
)
review_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(review_module)


def fixture():
    prepared = {
        "package": {
            "evidence": [
                {
                    "evidence_id": "original",
                    "text": "Original observed result. Original unresolved quantity. Original missing result.",
                }
            ],
            "scientific_extraction": {
                "records": [
                    {"id": "accepted", "status": "SOURCE_SUPPORTED"},
                    {"id": "pending", "status": "UNRESOLVED"},
                ]
            },
        }
    }
    review = {
        "basis": "Synthetic reviewer judgments, not NASA data",
        "targets": [
            {
                "id": "one",
                "kind": "statements",
                "evidence_id": "original",
                "quote": "Original observed result.",
                "outcome": "correct",
                "proposal_ids": ["accepted"],
            },
            {
                "id": "two",
                "kind": "quantities",
                "evidence_id": "original",
                "quote": "Original unresolved quantity.",
                "outcome": "unresolved",
                "proposal_ids": ["pending"],
            },
            {
                "id": "three",
                "kind": "statements",
                "evidence_id": "original",
                "quote": "Original missing result.",
                "outcome": "omitted",
            },
        ],
        "proposal_sample": [
            {
                "proposal_id": "accepted",
                "correct": True,
                "reason": "Reviewed original subject, role and expression.",
            }
        ],
    }
    return prepared, review


def test_semantic_recall_excludes_unresolved_and_precision_has_own_denominator():
    prepared, review = fixture()
    metrics = review_module.score(prepared, review)
    assert metrics["semantic_recall"] == {"numerator": 1, "denominator": 3}
    assert metrics["evidence_retention"] == {"numerator": 2, "denominator": 3}
    assert metrics["reviewed_proposal_precision"] == {"numerator": 1, "denominator": 1}


def test_unresolved_or_invented_reference_cannot_inflate_correct_recovery():
    prepared, review = fixture()
    bad = copy.deepcopy(review)
    bad["targets"][1]["outcome"] = "correct"
    with pytest.raises(ValueError, match="cannot count as correct"):
        review_module.score(prepared, bad)
    bad = copy.deepcopy(review)
    bad["targets"][2]["quote"] = "Invented reference"
    with pytest.raises(ValueError, match="not an exact original"):
        review_module.score(prepared, bad)


def test_correct_quantity_with_only_a_staged_property_is_reported_apart():
    prepared, review = fixture()
    records = prepared["package"]["scientific_extraction"]["records"]
    records.append(
        {
            "id": "staged",
            "status": "SOURCE_SUPPORTED",
            "mapping": {"kind": "staged_property_proposal", "property_id": None},
        }
    )
    review["targets"][1].update(outcome="correct", proposal_ids=["staged"])
    review["proposal_sample"].append(
        {"proposal_id": "staged", "correct": True, "reason": "Value, unit and row verified."}
    )
    metrics = review_module.score(prepared, review)
    assert metrics["semantic_recall"] == {"numerator": 2, "denominator": 3}
    assert metrics["semantic_recall_approved_properties_only"] == {
        "numerator": 1,
        "denominator": 3,
        "correct_quantity_targets_with_staged_property_only": 1,
    }


def test_a_correct_hold_is_reported_apart_and_never_counts_as_recall():
    prepared, review = fixture()
    review["targets"][1].update(
        hold_assessment="HOLD_IS_THE_CORRECT_OUTCOME",
        hold_rationale="The source prints two conflicting counts; both must stay unresolved.",
    )
    metrics = review_module.score(prepared, review)
    assert metrics["semantic_recall"] == {"numerator": 1, "denominator": 3}
    assert metrics["correctly_held_targets"] == {
        "count": 1,
        "target_ids": ["two"],
        "counts_as_recall": False,
    }
    bad = copy.deepcopy(review)
    bad["targets"][0]["hold_assessment"] = "HOLD_IS_THE_CORRECT_OUTCOME"
    with pytest.raises(ValueError, match="only to an unresolved target"):
        review_module.score(prepared, bad)
    bad = copy.deepcopy(review)
    del bad["targets"][1]["hold_rationale"]
    with pytest.raises(ValueError, match="source rationale"):
        review_module.score(prepared, bad)
