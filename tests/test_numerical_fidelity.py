"""Real native entry-point regressions; synthetic sources are explicitly non-NASA."""

import json
from pathlib import Path

import pytest
import yaml

from nasa_fire_ai.evaluation.reconstruction import reconstruct_passage
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.semantic import load_semantic_registry
from nasa_fire_ai.ingestion.structured_provenance import register_cells, table_cells
from nasa_fire_ai.query.native import SemanticGraph
from nasa_fire_ai.query.native_interpreter import MinimalInterpretationV2, PropertyMention
from nasa_fire_ai.query.v2 import GenericValue, PropertyDefinition
from nasa_fire_ai.services.native import answer_native_text

ROOT = Path(__file__).resolve().parents[1]
GOLD = json.loads((ROOT / "evals/phase3c_numeric_gold_proposal_v1.json").read_text())["cases"]


def add_passage(registry, row):
    registry.add_passage(
        {
            "page": None,
            "section": None,
            "start_offset": 0,
            "end_offset": len(row["text"]),
            "raw_file": None,
            "checksum": None,
            **row,
        }
    )


@pytest.fixture
def native(tmp_path, monkeypatch):
    monkeypatch.setenv("HIERARCHICAL_SEMANTIC_RETRIEVAL_ENABLED", "true")
    monkeypatch.setenv("RELATIONAL_RELATED_RETRIEVAL_ENABLED", "true")
    registry = load_semantic_registry(ROOT / "domain/semantic_registry.yaml")
    store = SemanticGraph(registry)
    evidence = EvidenceRegistry(tmp_path / "registry.sqlite")
    evidence.add_source({"source_id": "synthetic", "title": "Synthetic regression fixture"})
    evidence.add_document("doc", "synthetic", "Synthetic regression fixture")
    for identity, velocity in [("below", 0.1), ("boundary", 0.2), ("above", 0.3)]:
        eid = "E-" + identity
        add_passage(evidence, {"evidence_id": eid, "document_id": "doc", "text": identity})
        store.add_entity(identity, "ExperimentalRun", [eid], ["synthetic"])
        store.add_relation(identity, "hasMaterial", "PMMA", [eid])
        store.add_value(
            "v-" + identity,
            identity,
            "AirflowVelocity",
            GenericValue(reported_value=velocity, reported_unit="m/s"),
            [eid],
        )
        store.add_value(
            "o-" + identity,
            identity,
            "OxygenConcentration",
            GenericValue(reported_value=0.2, reported_unit="fraction"),
            [eid],
        )
    return store, evidence, yaml.safe_load((ROOT / "domain/query_language_v2.yaml").read_text())


@pytest.mark.parametrize("case", GOLD, ids=[c["case_id"] for c in GOLD])
def test_literal_question_reaches_plan_and_bundle(native, case):
    store, evidence, language = native
    # Campaign comparison case needs actual investigation operands, so this
    # fixture checks its constraint using the literal search clause.
    query = case["query"].split(" at ", 1)[-1] if case["case_id"] == "qi50" else case["query"]
    response = answer_native_text(query, store, evidence, language)
    constraint = response.execution.plan.intent.property_constraints[0]
    expected = case["expected"]
    assert constraint.property_id == expected["property_id"]
    assert constraint.operator == expected["operator"]
    normalized = store.registry.validate(constraint)
    assert normalized.canonical_value == pytest.approx(expected["canonical_value"])
    assert normalized.canonical_unit == expected["canonical_unit"]
    assert constraint.value.reported_unit == expected["reported_unit"]
    assert constraint.value.approximate == expected["approximate"]
    assert constraint.value.tolerance is None
    assert response.execution.bundle.retrieval_metadata["query_intent_v2"]["property_constraints"]


@pytest.mark.parametrize(
    "operator,expected",
    [
        (">", {"above"}),
        (">=", {"boundary", "above"}),
        ("<", {"below"}),
        ("<=", {"below", "boundary"}),
        ("=", {"boundary"}),
    ],
)
def test_boundary_classification(native, operator, expected):
    store, evidence, language = native
    response = answer_native_text(f"PMMA airflow {operator} 20 cm/s", store, evidence, language)
    assert {c["id"] for c in response.execution.bundle.direct_evidence} == expected
    assert {c["id"] for c in response.execution.bundle.related_evidence} == {
        "above",
        "below",
        "boundary",
    } - expected
    if operator == "<":
        assert (
            "Requested airflow: below 20.0 cm/s. Reported airflow: 0.2 m/s."
            in response.rendered_answer
        )


def test_model_cannot_drop_or_change_literal_constraint(native):
    store, evidence, language = native

    class Lossy:
        def interpret_minimal(self, _):
            return MinimalInterpretationV2(
                properties=[PropertyMention(label="airflow", expression=">= 99 cm/s")]
            )

    response = answer_native_text("PMMA airflow < 20 cm/s", store, evidence, language, Lossy())
    assert {c["id"] for c in response.execution.bundle.direct_evidence} == {"below"}
    assert response.execution.plan.intent.property_constraints[0].operator == "LT"


def test_model_cannot_supply_an_unasked_property_or_missing_unit(native):
    store, evidence, language = native

    class Invented:
        def interpret_minimal(self, _):
            return MinimalInterpretationV2(
                properties=[
                    PropertyMention(label="airflow", expression="10 cm/s"),
                    PropertyMention(label="oxygen", expression="20%"),
                ]
            )

    unitless = answer_native_text("PMMA airflow 10", store, evidence, language, Invented())
    assert not unitless.execution.bundle.direct_evidence
    assert unitless.execution.plan.intent.unresolved_mentions
    constrained = answer_native_text(
        "PMMA airflow >= 20 cm/s", store, evidence, language, Invented()
    )
    assert {c.property_id for c in constrained.execution.plan.intent.property_constraints} == {
        "AirflowVelocity"
    }


def test_approximation_is_not_exact_equality(native):
    store, evidence, language = native
    response = answer_native_text("PMMA about 20% oxygen", store, evidence, language)
    assert not response.execution.bundle.direct_evidence
    assert all(
        "OxygenConcentration" in c["unknown"] for c in response.execution.bundle.related_evidence
    )


def test_conjunctive_properties_and_explicit_tolerance(native):
    store, evidence, language = native
    response = answer_native_text(
        "PMMA airflow >= 20 cm/s and oxygen 20% +/- 1%", store, evidence, language
    )
    intent = response.execution.plan.intent
    assert len(intent.property_constraints) == 2
    assert {c["id"] for c in response.execution.bundle.direct_evidence} == {"boundary", "above"}
    oxygen = next(c for c in intent.property_constraints if c.property_id == "OxygenConcentration")
    assert oxygen.operator == "APPROX"
    assert oxygen.value.tolerance == 1
    assert store.registry.validate(oxygen).tolerance == 0.01


def test_range_inclusive_and_exclusive_boundaries(native):
    store, evidence, language = native
    inclusive = answer_native_text(
        "PMMA airflow between 10 and 20 cm/s inclusive", store, evidence, language
    )
    exclusive = answer_native_text(
        "PMMA airflow between 10 and 20 cm/s exclusive", store, evidence, language
    )
    assert {c["id"] for c in inclusive.execution.bundle.direct_evidence} == {"below", "boundary"}
    assert not exclusive.execution.bundle.direct_evidence


@pytest.mark.parametrize(
    "query",
    [
        "airflow 20 knots",
        "airflow 10 cm/s or airflow 20 cm/s",
        "airflow between 0.1 m/s and 20 cm/s",
    ],
)
def test_unsupported_or_disjunctive_quantity_cannot_be_direct(native, query):
    store, evidence, language = native
    response = answer_native_text(query, store, evidence, language)
    assert not response.execution.bundle.direct_evidence
    intent = response.execution.plan.intent
    assert intent.unresolved_mentions or intent.clarification_required


def test_new_registered_property_without_special_parser_branch(native):
    store, evidence, language = native
    store.registry.register(
        PropertyDefinition("UnseenSpeed", "velocity", "m/s", aliases=["unseen transport speed"])
    )
    response = answer_native_text(
        "unseen transport speed at least 150 mm/s", store, evidence, language
    )
    assert response.execution.plan.intent.property_constraints[0].property_id == "UnseenSpeed"
    assert (
        store.registry.validate(
            response.execution.plan.intent.property_constraints[0]
        ).canonical_value
        == 0.15
    )


def test_reconstructed_csv_preserves_multiline_and_logical_locator(tmp_path):
    path = tmp_path / "table.csv"
    path.write_text('Run,Note\na,"line one\nline two"\n', newline="\n")
    headers, rows, metadata = table_cells(path, tmp_path)
    registry = EvidenceRegistry(tmp_path / "e.sqlite")
    registry.add_source({"source_id": "synthetic"})
    registry.add_document("doc", "synthetic", "Synthetic")
    add_passage(
        registry,
        {
            "evidence_id": "E",
            "document_id": "doc",
            "text": ",".join(rows[0]),
            "raw_file": "table.csv",
            "checksum": metadata["checksum"],
        },
    )
    register_cells(registry, "E", metadata, 2, headers, rows[0])
    reconstructed = reconstruct_passage("E", registry, tmp_path)
    assert reconstructed["status"] == "VERIFIED"
    assert reconstructed["structured_row"] == ["a", "line one\nline two"]
    assert reconstructed["verified_location"]["physical_pdf_page"] is None
    assert reconstructed["verified_location"]["record_ordinal_including_header"] == 2


def test_missing_source_and_evidence_are_explicit(tmp_path):
    registry = EvidenceRegistry(tmp_path / "e.sqlite")
    assert reconstruct_passage("missing", registry, tmp_path)["status"] == "MISSING_EVIDENCE"
    registry.add_source({"source_id": "synthetic"})
    registry.add_document("doc", "synthetic", "Synthetic")
    add_passage(
        registry,
        {"evidence_id": "E", "document_id": "doc", "text": "preserved", "raw_file": "absent.csv"},
    )
    assert reconstruct_passage("E", registry, tmp_path)["status"] == "MISSING_SOURCE"


def test_table_gravity_without_source_column_is_staged(tmp_path, monkeypatch):
    import sqlite3

    from nasa_fire_ai.ingestion.semantic import project_legacy

    path = tmp_path / "registry.sqlite"
    with (
        sqlite3.connect(f"file:{ROOT}/data/index/evidence.sqlite?mode=ro", uri=True) as original,
        sqlite3.connect(path) as backup,
    ):
        original.backup(backup)
    monkeypatch.setenv("NATIVE_SOURCE_CONTEXT_VALIDATION_ENABLED", "true")
    evidence = EvidenceRegistry(path)
    store = project_legacy(ROOT, evidence)
    for run in ["psi-98-S1", "psi-98-S2"]:
        assert not store.relations(run, "hasGravityCondition")
        assert any(
            r["subject"] == run and "gravity declaration lacks" in r.get("reason", "")
            for r in store.projection_staging
        )


def test_verified_context_reaches_model_and_invalidates_cache(native, monkeypatch):
    from nasa_fire_ai.query.controlled_reasoning import NemotronControlledReasoner
    from nasa_fire_ai.query.v2 import QueryIntentV2

    store, _, _ = native
    reasoner = NemotronControlledReasoner(None, "synthetic-model", store.registry)
    captured = []

    def call(_system, user, _tokens):
        captured.append(json.loads(user))
        return {"judgments": []}, {"input_tokens": 0, "output_tokens": 0}

    monkeypatch.setattr(reasoner, "_json_call", call)
    candidate = {
        "evidence_id": "synthetic",
        "text": "synthetic fragment",
        "structured_location": {
            "physical_pdf_page": 1,
            "checksum": "synthetic-digest",
            "context_before": "Synthetic antecedent",
            "context_after": "",
        },
    }
    intent = QueryIntentV2(targets=["ExperimentalRun"])
    first = reasoner.rerank("synthetic query", intent, [candidate])
    replay = reasoner.rerank("synthetic query", intent, [candidate])
    assert captured[0]["candidates"][0]["registered_source_context"]["text"].startswith(
        "Synthetic antecedent"
    )
    assert replay["new_calls"] == 0
    candidate["structured_location"]["context_before"] = "Changed synthetic antecedent"
    changed = reasoner.rerank("synthetic query", intent, [candidate])
    assert changed["cache_key"] != first["cache_key"]
    assert len(captured) == 2
