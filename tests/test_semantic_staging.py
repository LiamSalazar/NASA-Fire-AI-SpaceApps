from pathlib import Path

import pytest

from nasa_fire_ai.evidence.registry import EvidenceRegistry


def test_staging_persists_provenance_and_rejects_canonical_state(tmp_path: Path):
    registry = EvidenceRegistry(tmp_path / "evidence.sqlite")
    registry.stage_semantic_candidate(
        {
            "candidate_id": "candidate-1",
            "candidate_type": "PropertyCandidate",
            "raw_label": "Novel temperature",
            "source_id": "holdout-a",
            "evidence_id": "e-1",
            "resolution_status": "CANDIDATE_NEW_CONCEPT",
            "review_status": "PENDING",
            "observed_unit": "K",
        }
    )
    assert registry.staged_semantic_candidates()[0]["evidence_id"] == "e-1"
    with pytest.raises(ValueError, match="cannot be canonical"):
        registry.stage_semantic_candidate(
            {
                "candidate_id": "bad",
                "candidate_type": "PropertyCandidate",
                "raw_label": "bad",
                "resolution_status": "CANONICAL",
            }
        )
