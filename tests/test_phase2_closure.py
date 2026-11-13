import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_phase2_graph_gold_is_source_backed_and_records_managed_passages():
    gold = json.loads((ROOT / "evals/phase2_graph_constrained_gold.json").read_text())
    assert gold["cases"]
    for case in gold["cases"]:
        assert case["review_status"] == "SOURCE_BACKED"
        assert case["expected_evidence_ids"]


def test_discovery_gold_preserves_non_authoritative_rationale_and_provenance():
    gold = json.loads((ROOT / "evals/phase2_discovery_gold.json").read_text())
    assert len(gold["cases"]) == 15
    for case in gold["cases"]:
        assert case["relevant_evidence_ids"]
        assert case["relevant_source_ids"]
        assert "does not" not in case["why_potentially_relevant"].lower()
        assert case["why_not_direct"] and case["why_not_related"]


def test_closure_evaluation_separates_semantic_coverage_from_ranking():
    evaluation = json.loads((ROOT / "data/eda/phase2_closure_evaluation.json").read_text())
    semantic = evaluation["semantic_resolution"]
    assert semantic["coverage"] < 1
    assert semantic["coverage_conditioned"]["top1"] >= semantic["end_to_end"]["top1"]
    assert evaluation["discovery"]["provenance_coverage"] == 1.0
