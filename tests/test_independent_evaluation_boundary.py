"""Synthetic prospective boundary checks; no NASA facts or inference calls."""

import importlib.util
import json
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "independent_driver",
    Path(__file__).resolve().parents[1] / "scripts/run_phase1_scientific_validation.py",
)
driver = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(driver)


def reference(tmp_path):
    package = {
        "inputs": [{"sha256": "source-sha"}],
        "evidence": [{"evidence_id": "e", "source_id": "s", "text": "Synthetic original."}],
    }
    freeze = {
        "evaluation": {"membership": "RESERVED_SYNTHETIC", "ntrs_id": "123"},
        "source_review_plan": {"minimum_targets": 1, "minimum_statements": 1},
    }
    ref = {
        "membership": "RESERVED_SYNTHETIC",
        "source_ntrs_id": "123",
        "source_sha256": "source-sha",
        "targets": [
            {
                "id": "t",
                "kind": "statements",
                "evidence_id": "e",
                "source_id": "s",
                "start": 0,
                "end": 19,
                "quote": "Synthetic original.",
            }
        ],
    }
    (tmp_path / "source_reference.json").write_text(json.dumps(ref))
    return package, freeze, ref


def test_missing_reference_blocks_reserved_inference(tmp_path):
    package, freeze, _ = reference(tmp_path)
    (tmp_path / "source_reference.json").unlink()
    with pytest.raises(FileNotFoundError):
        driver.commit_source_reference(tmp_path, freeze, package, 0)
    assert not (tmp_path / "source_reference_commitment.json").exists()


def test_started_inference_cannot_be_retroactively_registered(tmp_path):
    package, freeze, _ = reference(tmp_path)
    with pytest.raises(ValueError, match="before source reference"):
        driver.commit_source_reference(tmp_path, freeze, package, 1)


def test_reference_freeze_is_idempotent_and_rejects_post_inference_edits(tmp_path):
    package, freeze, ref = reference(tmp_path)
    driver.commit_source_reference(tmp_path, freeze, package, 0)
    driver.commit_source_reference(tmp_path, freeze, package, 2)
    ref["review_note"] = "Later edit"
    (tmp_path / "source_reference.json").write_text(json.dumps(ref))
    with pytest.raises(ValueError, match="reference changed"):
        driver.commit_source_reference(tmp_path, freeze, package, 2)


def test_invented_original_span_cannot_be_committed(tmp_path):
    package, freeze, ref = reference(tmp_path)
    ref["targets"][0]["quote"] = "Invented synthetic claim"
    (tmp_path / "source_reference.json").write_text(json.dumps(ref))
    with pytest.raises(ValueError, match="exact original"):
        driver.commit_source_reference(tmp_path, freeze, package, 0)
