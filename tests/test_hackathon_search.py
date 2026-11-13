"""Real NASA integration plus explicitly synthetic constraint adversaries."""

from pathlib import Path

import pytest
from rdflib import Literal

from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.hackathon import build_snapshot, make_store
from nasa_fire_ai.query.native import NS, node
from nasa_fire_ai.query.v2 import (
    GenericValue,
    PropertyConstraintV2,
    QueryIntentV2,
)
from nasa_fire_ai.services.search import ScientificSearchService

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def engine(tmp_path_factory):
    path = tmp_path_factory.mktemp("search") / "snapshot"
    build_snapshot(ROOT, path)
    service = ScientificSearchService(path, ROOT)
    yield service
    service.close()


@pytest.mark.parametrize(
    "question",
    [
        "Saffire I airflow 20 cm/s",
        "Find SAFFIRE-I with air flow 0.2 m/s",
        "SAFFIRE-I airflow at least 19 cm/s",
    ],
)
def test_real_saffire_paraphrases(engine, question):
    result = engine.search(question)
    assert result.sufficiency == "DIRECT_EVIDENCE"
    assert {r["id"] for r in result.direct} == {"psi-98-S1", "psi-98-S2"}
    for row in result.direct:
        assert all(c["status"] == "MATCH" for c in row["constraints"])
        assert row["ontology_paths"]
        assert all(e["source"]["source_id"] == "psi-98" for e in row["evidence"])


def test_one_changed_constraint_real(engine):
    result = engine.search("SAFFIRE-I airflow 30 cm/s")
    assert not result.direct
    assert {r["id"] for r in result.related} == {"psi-98-S1", "psi-98-S2"}
    assert all("AirflowVelocity" in r["different_dimensions"] for r in result.related)


def test_saffire_comparison_real(engine):
    result = engine.search("Compare Saffire I S1 and S2")
    assert result.intent.operation == "COMPARE"
    assert result.comparison["run_ids"] == ["psi-98-S1", "psi-98-S2"]
    assert "FlowDirection" in result.comparison["different_conditions"]
    assert "AirflowVelocity" in result.comparison["shared_conditions"]
    assert "Pressure" in result.comparison["unknown_or_unavailable_conditions"]


@pytest.mark.parametrize(
    "question",
    [
        "PMMA in microgravity",
        "Studies of flame propagation in solid materials in microgravity",
        "PMMA in a hypothetical lunar habitat with oxygen 22.2 %",
        "PMMA oxygen partial pressure 22.2 %",
        "PMMA unknown-property 83 kPa",
        "FLEX simulated pressure 100 kPa",
        "PMMA oxygen 22.2 % and oxygen 21 %",
    ],
)
def test_unsupported_conditions_never_direct(engine, question):
    result = engine.search(question)
    assert not result.direct
    assert result.sufficiency == "NO_DIRECT_EVIDENCE"
    assert (
        result.intent.unresolved_mentions
        or result.related
        or result.documentary
        or result.discovery
    )


@pytest.mark.parametrize(
    "question", ["FLEX extinction", "SAME smoke detection", "SAME-R smoke detection"]
)
def test_relevant_sources_survive_unresolved_phenomena(engine, question):
    result = engine.search(question)
    assert not result.direct
    assert result.related or result.discovery or result.documentary
    assert result.intent.unresolved_mentions


def test_normative_document_is_not_observation(engine):
    result = engine.search("NASA-STD-6001 requirements")
    assert not result.direct
    assert result.documentary
    assert any(r["source"]["source_id"] == "nasa-std-6001b-change3" for r in result.documentary)
    assert result.intent.requested_information == ["Requirement"]


def test_source_constraints_before_ranking(engine):
    intent = QueryIntentV2(targets=["Document"], source_constraints=["nasa-std-6001b-change3"])
    result = engine.search("flammability requirements", intent=intent)
    assert result.documentary
    assert all(r["source"]["source_id"] == "nasa-std-6001b-change3" for r in result.documentary)
    assert not result.direct


def test_fts_and_every_returned_evidence_resolve(engine):
    result = engine.search("PMMA oxygen 22.2 %", limit=5)
    assert result.direct
    assert result.metrics["llm_calls"] == 0
    for row in result.direct + result.related:
        assert row["evidence"]
        for evidence in row["evidence"]:
            assert engine.registry.resolve(evidence["evidence_id"])
            assert Path(evidence["raw_file"]).is_file()
    assert result.metrics["total_ms"] > 0
    assert result.snapshot_id


@pytest.fixture
def synthetic(engine, tmp_path, monkeypatch):
    """Invented logical fixture, never published to a NASA snapshot."""
    store = make_store(ROOT)
    registry = EvidenceRegistry(tmp_path / "synthetic.sqlite")
    registry.add_document("SYNTHETIC", "SYNTHETIC", "Invented logical fixture")
    registry.add_passage(
        {
            "evidence_id": "SYNTHETIC",
            "document_id": "SYNTHETIC",
            "page": None,
            "section": None,
            "text": "Invented apparatus record",
            "start_offset": 0,
            "end_offset": 25,
            "raw_file": "SYNTHETIC",
            "checksum": "SYNTHETIC",
        }
    )
    store.add_entity("synthetic-run", "ExperimentalRun", ["SYNTHETIC"], ["SYNTHETIC"])
    monkeypatch.setattr(engine, "store", store)
    monkeypatch.setattr(engine, "registry", registry)
    yield store
    registry.db.close()


def pressure_intent(unit="Pa", value=123):
    return QueryIntentV2(
        targets=["ExperimentalRun"],
        property_constraints=[
            PropertyConstraintV2(
                property_id="Pressure",
                operator="EQ",
                value=GenericValue(reported_value=value, reported_unit=unit),
            )
        ],
    )


def test_synthetic_conflict_never_direct(engine, synthetic):
    for rid, value in [("synthetic-a", 123), ("synthetic-b", 456)]:
        synthetic.add_value(
            rid,
            "synthetic-run",
            "Pressure",
            GenericValue(reported_value=value, reported_unit="Pa"),
            ["SYNTHETIC"],
        )
    result = engine.search("invented", intent=pressure_intent())
    assert not result.direct
    matrix = engine._matrix("synthetic-run", pressure_intent())
    assert matrix[0]["status"] == "CONFLICT"


def test_synthetic_simulation_never_becomes_measurement(engine, synthetic):
    synthetic.add_value(
        "synthetic-prediction",
        "synthetic-run",
        "Pressure",
        GenericValue(reported_value=123, reported_unit="Pa"),
        ["SYNTHETIC"],
        {"modality": "simulated"},
    )
    result = engine.search("invented", intent=pressure_intent())
    assert not result.direct
    assert engine._matrix("synthetic-run", pressure_intent())[0]["status"] == "NOT_COMPARABLE"


def test_synthetic_incompatible_unit_is_not_numeric_match(engine, synthetic):
    synthetic.add_value(
        "synthetic-pressure",
        "synthetic-run",
        "Pressure",
        GenericValue(reported_value=123, reported_unit="Pa"),
        ["SYNTHETIC"],
    )
    record = node("synthetic-pressure")
    synthetic.graph.remove((record, NS.value, None))
    synthetic.graph.add(
        (
            record,
            NS.value,
            Literal(GenericValue(reported_value=123, reported_unit="cm/s").model_dump_json()),
        )
    )
    assert engine._matrix("synthetic-run", pressure_intent())[0]["status"] == "NOT_COMPARABLE"


def test_synthetic_unseen_subject_value(engine, synthetic):
    synthetic.add_value(
        "synthetic-pressure",
        "synthetic-run",
        "Pressure",
        GenericValue(reported_value=987, reported_unit="Pa"),
        ["SYNTHETIC"],
    )
    result = engine.search("invented", intent=pressure_intent(value=987))
    assert [r["id"] for r in result.direct] == ["synthetic-run"]


def test_real_approved_subclass_is_found_through_parent(engine):
    intent = QueryIntentV2(
        targets=["ExperimentalCondition"],
        source_constraints=["psi-69"],
        property_constraints=[
            PropertyConstraintV2(
                property_id="Pressure",
                operator="GT",
                value=GenericValue(reported_value=700, reported_unit="mmHg"),
            )
        ],
    )
    result = engine.search("pressure conditions", intent=intent, limit=4)
    assert result.direct
    assert all("PressureCondition" in r["classes"] for r in result.direct)
    assert all("ExperimentalCondition" in r["approved_class_ancestors"] for r in result.direct)
    assert all(r["evidence"][0]["source"]["source_id"] == "psi-69" for r in result.direct)
