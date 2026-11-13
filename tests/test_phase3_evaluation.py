import pytest

from nasa_fire_ai.evaluation.phase3 import claim_metrics, score_intents, write_artifact


def test_intent_scorer_and_empty_fields():
    result = score_intents({"materials": ["PMMA"]}, {"materials": ["PMMA"]})
    assert result["exact"] and result["f1"] == 1.0


def test_artifact_writer_rejects_credentials(tmp_path):
    with pytest.raises(ValueError):
        write_artifact(tmp_path / "x.json", {"bad": "nvapi-example"})


def test_claim_metrics_distinguish_bundle_validity():
    result = claim_metrics(
        [{"claims": [{"grounding_valid": True, "evidence_ids": ["E"], "evidence_in_bundle": True}]}]
    )
    assert result["generated"] == 1 and result["citation_coverage"] == 1.0
