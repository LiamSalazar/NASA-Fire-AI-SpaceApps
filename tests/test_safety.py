import json
from pathlib import Path

from nasa_fire_ai.models import Claim, QueryIntent
from nasa_fire_ai.query import classify_runs

ROOT = Path(__file__).resolve().parents[1]


def test_every_curated_safety_record_has_evidence_and_distinct_types():
    records = json.loads((ROOT / "data/canonical/safety_records.json").read_text())
    statements = [record for record in records if record["type"] == "SafetyStatementRecord"]
    assert all(record["evidence_refs"] for record in statements)
    types = {record["statement_type"] for record in statements}
    assert {
        "requirement",
        "guidance",
        "design_criterion",
        "test_criterion",
        "nasa_conclusion",
        "safety_implication",
        "open_question",
    } <= types


def test_observation_conclusion_and_implication_are_separate_entities():
    records = json.loads((ROOT / "data/canonical/safety_records.json").read_text())
    identifiers = {record.get("id", record.get("statement_id")) for record in records}
    assert {
        "saffire-iv-flow-off-observation",
        "saffire-suppression-conclusion",
        "suppression-system-implication",
    } <= identifiers


def test_experimental_failure_does_not_become_guidance():
    records = json.loads((ROOT / "data/canonical/safety_records.json").read_text())
    observation = next(
        record for record in records if record.get("id") == "saffire-iv-flow-off-observation"
    )
    assert "guidance" not in observation["type"].lower()


def test_direct_evidence_and_open_question_can_coexist():
    records = json.loads((ROOT / "data/canonical/safety_records.json").read_text())
    assert any(
        record.get("statement_id") == "saffire-suppression-open-question" for record in records
    )
    assert any(record.get("id") == "saffire-iv-flow-off-observation" for record in records)


def test_no_direct_evidence_creates_no_open_question():
    direct, related = classify_runs(
        QueryIntent(materials=["unindexed material"]), [{"id": "run", "material": "PMMA"}]
    )
    assert not direct and not related
    notice = Claim(
        claim_id="n",
        claim_type="no_direct_evidence_notice",
        text="No direct matching evidence was found.",
    )
    assert notice.claim_type == "no_direct_evidence_notice"
