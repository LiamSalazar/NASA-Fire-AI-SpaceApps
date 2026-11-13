"""Offline provider controls; these fixtures do not measure Nemotron quality."""

from pathlib import Path

import pytest

from nasa_fire_ai.ingestion.hackathon import build_snapshot
from nasa_fire_ai.llm.interfaces import ProviderFailure
from nasa_fire_ai.query.native_interpreter import MinimalInterpretationV2
from nasa_fire_ai.services.search import ScientificSearchService

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def engine(tmp_path_factory):
    path = tmp_path_factory.mktemp("assistant") / "snapshot"
    build_snapshot(ROOT, path)
    service = ScientificSearchService(path, ROOT)
    yield service
    service.close()


class Interpreter:
    def __init__(self):
        self.last_receipt = {"usage": {"total_tokens": 42}, "retries": 0}

    def interpret_minimal(self, query):
        return MinimalInterpretationV2()


class Failure(Interpreter):
    def interpret_minimal(self, query):
        raise ProviderFailure("timeout")


class Hallucination(Interpreter):
    def interpret_minimal(self, query):
        return MinimalInterpretationV2(entities=["microgravity"])


def test_provider_unavailable_keeps_offline_claim_gate(engine):
    result = engine.search("Saffire I airflow 20 cm/s", assist=True)
    assert result.provider["status"] == "UNAVAILABLE"
    assert result.direct
    assert result.metrics["llm_calls"] == 0
    assert result.claims
    for claim in result.claims:
        assert claim["validation"]["status"].startswith("SUPPORTED")
        assert all(engine.registry.resolve(eid) for eid in claim["evidence_ids"])


@pytest.mark.parametrize("provider", [Failure(), Hallucination()])
def test_invalid_or_failed_interpretation_cannot_change_eligibility(engine, monkeypatch, provider):
    monkeypatch.setattr(engine, "model_interpreter", provider)
    result = engine.search("PMMA in a lunar habitat oxygen 22.2 %", assist=True)
    assert result.provider["status"] == "DEGRADED"
    assert not result.direct
    assert result.intent.unresolved_mentions


def test_valid_interpretation_preserves_original_numeric_filter(engine, monkeypatch):
    monkeypatch.setattr(engine, "model_interpreter", Interpreter())
    result = engine.search("Saffire I airflow 30 cm/s", assist=True)
    assert result.provider["status"] == "AVAILABLE"
    assert not result.direct
    assert result.related
    assert result.intent.property_constraints[0].value.reported_value == 30


def test_directed_research_has_finite_budget_and_no_promotion(engine):
    result = engine.search("FLEX simulated pressure 100 kPa", assist=True, research=True)
    assert not result.direct
    assert result.investigation["action_attempts"] <= 2
    assert result.investigation["model_calls"] == []
    assert result.investigation["stop_reason"]


def test_pagination_is_reproducible(engine):
    a = engine.search("PMMA oxygen 22.2 %", limit=2)
    b = engine.search("PMMA oxygen 22.2 %", limit=1, offset=1)
    assert b.direct[0]["id"] == a.direct[1]["id"]


def test_real_measurement_query_uses_own_run_scope(engine):
    result = engine.search("Saffire I measurements", assist=True)
    assert {r["id"] for r in result.direct} == {"psi-98-S1-value-9", "psi-98-S2-value-9"}
    assert all("Measurement" in r["classes"] for r in result.direct)
    assert not engine.search("Saffire I observations").direct
    assert all(r["payload"]["subject"].startswith("psi-98-") for r in result.direct)
    assert result.claims
    for claim in result.claims:
        assert claim["modality"] == "reported_measurement"
        assert all(
            record["id"] not in engine.store.relations(claim["subject"], "hasMeasurement")
            for record in claim["conditions"]
        )
