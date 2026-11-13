import json
from pathlib import Path

import yaml

from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.semantic import (
    ingest_generic_table,
    load_semantic_registry,
    project_canonical_conditions,
    project_legacy,
)
from nasa_fire_ai.query.native import NS, SemanticGraph, classify_native
from nasa_fire_ai.query.native_interpreter import (
    MinimalInterpretationV2,
    PropertyMention,
    parse_expression,
    resolve_minimal,
)
from nasa_fire_ai.query.v2 import (
    GenericValue,
    PropertyConstraintV2,
    PropertyDefinition,
    QueryIntentV2,
    SemanticRegistry,
)

ROOT = Path(__file__).resolve().parents[1]


def test_full_projection_is_idempotent_and_keeps_source_context():
    evidence = EvidenceRegistry(ROOT / "data/index/evidence.sqlite")
    store = project_legacy(ROOT, evidence)
    assert store.projection_report["total_runs"] == 405
    assert store.projection_report["projected_runs"] == 405
    assert store.projection_report["conditions"] > 400
    assert store.projection_report["measurements"] == 0
    assert store.projection_staging
    assert all(c["provenance"] and c["evidence_id"] for c in store.projection_staging)
    before = set(store.graph)
    project_canonical_conditions(
        store,
        json.loads((ROOT / "data/canonical/records.json").read_text()),
        yaml.safe_load((ROOT / "domain/legacy_semantic_projection.yaml").read_text()),
        evidence,
    )
    assert set(store.graph) == before
    assert store.values("psi-98-S1", "AirflowVelocity")[0].reported_unit == "cm/s"


def test_missing_conflicting_and_invalid_values_are_not_differences():
    registry = SemanticRegistry([PropertyDefinition("TestFutureProperty", "velocity", "m/s")])
    store = SemanticGraph(registry)
    store.add_entity("r", "ExperimentalRun", ["E-r"])
    q = QueryIntentV2(
        property_constraints=[
            PropertyConstraintV2(
                property_id="TestFutureProperty",
                operator="LT",
                value=GenericValue(reported_value=0.1, reported_unit="m/s"),
            )
        ]
    )
    assert classify_native("r", q, store)[1]["unknown"] == ["TestFutureProperty"]
    store.add_value(
        "a",
        "r",
        "TestFutureProperty",
        GenericValue(reported_value=0.08, reported_unit="m/s"),
        ["E-r"],
    )
    assert classify_native("r", q, store)[0] == "DIRECT"
    store.add_value(
        "b",
        "r",
        "TestFutureProperty",
        GenericValue(reported_value=0.2, reported_unit="m/s"),
        ["E-r"],
    )
    assert classify_native("r", q, store)[1]["unknown"] == ["TestFutureProperty"]
    assert len(list(store.graph.objects(None, NS.value))) == 2


def test_eligible_fts_filter_precedes_limit(tmp_path):
    evidence = EvidenceRegistry(tmp_path / "e.sqlite")
    evidence.add_source({"source_id": "source", "title": "NASA source"})
    evidence.add_document("doc", "source", "NASA source")
    for i in range(50):
        evidence.add_passage(
            {
                "evidence_id": f"E-{i}",
                "document_id": "doc",
                "page": i,
                "section": None,
                "text": "suppression",
                "start_offset": None,
                "end_offset": None,
                "raw_file": None,
                "checksum": None,
            }
        )
    assert (
        evidence.search("suppression", eligible_ids=["E-49"], limit=1)[0]["evidence_id"] == "E-49"
    )
    evidence.db.execute("DELETE FROM evidence_refs WHERE evidence_id='E-49'")
    assert evidence.source_metadata("E-49")["title"] == "NASA source"


def test_no_table_row_is_automatically_an_executed_run(tmp_path):
    evidence = EvidenceRegistry(tmp_path / "e.sqlite")
    store = SemanticGraph(load_semantic_registry(ROOT / "domain/semantic_registry.yaml"))
    result = ingest_generic_table(
        [{"run id": "planned-1", "airflow (m/s)": "0.2"}], "fixture", ["E-1"], store, evidence
    )
    assert result["canonical_records"] == 0
    assert not store.entities()
    assert evidence.staged_semantic_candidates()[0]["provenance"]


def test_numeric_surface_and_ambiguity_protection():
    language = yaml.safe_load((ROOT / "domain/query_language_v2.yaml").read_text())
    registry = load_semantic_registry(ROOT / "domain/semantic_registry.yaml")
    assert parse_expression("no greater than 0.1 m/s", "numeric", language["operators"])[0] == "LTE"
    assert (
        parse_expression("between 21.5 and 21.7 percent", "numeric", language["operators"])[
            1
        ].reported_unit
        == "%"
    )
    assert parse_expression("0.10-0.20 m/s", "numeric", language["operators"])[1].upper == 0.2
    assert (
        parse_expression("roughly 0.2 m/s", "numeric", language["operators"])[1].tolerance is None
    )
    proposal = MinimalInterpretationV2(
        entities=["PMMA", "SAFFIRE-I"],
        properties=[PropertyMention(label="airflow", expression="0.2 m/s")],
    )
    q = resolve_minimal(proposal, registry, language, query="acrylic Saffire velocity 0.2 m/s")
    assert q.clarification_required
    assert not q.entity_constraints and not q.property_constraints
    q = resolve_minimal(
        MinimalInterpretationV2(entities=["SIBAL Fabric microgravity"]), registry, language
    )
    assert len(q.entity_constraints) == 2 and q.targets == ["ExperimentalRun"]


def test_native_language_service_without_credentials_is_safe(tmp_path):
    from nasa_fire_ai.services.native import answer_native_text

    evidence = EvidenceRegistry(tmp_path / "e.sqlite")
    store = SemanticGraph(load_semantic_registry(ROOT / "domain/semantic_registry.yaml"))
    response = answer_native_text("velocity effects", store, evidence, {})
    assert response.fallback
    assert "clarify" in response.rendered_answer
    assert not response.execution.bundle.direct_evidence


def test_unreviewed_legacy_claim_types_do_not_become_nasa_conclusions():
    store = project_legacy(ROOT, EvidenceRegistry(ROOT / "data/index/evidence.sqlite"))
    assert len(store.legacy_statement_staging) == 3
    assert "open_question-ntrs-20205007829" not in store.entities()


def test_known_slots_do_not_remain_unresolved_but_new_concepts_do():
    language = yaml.safe_load((ROOT / "domain/query_language_v2.yaml").read_text())
    registry = load_semantic_registry(ROOT / "domain/semantic_registry.yaml")
    registry.source_ids.add("official-source")
    q = resolve_minimal(
        MinimalInterpretationV2(
            requested_information=["guidance"],
            unknown=["guidance", "new NASA property", "official-source"],
        ),
        registry,
        language,
        query="Find guidance from source official-source",
    )
    assert q.requested_information == ["Guidance"]
    assert q.unresolved_mentions == ["new NASA property"]
    assert q.source_constraints == ["official-source"]


def test_requested_information_is_class_scoped_topic_ranked_and_traced(tmp_path):
    from nasa_fire_ai.query.native import execute_native

    evidence = EvidenceRegistry(tmp_path / "e.sqlite")
    evidence.add_source({"source_id": "SRC", "title": "NASA fire safety report"})
    evidence.add_document("doc", "SRC", "NASA fire safety report")
    registry = load_semantic_registry(ROOT / "domain/semantic_registry.yaml")
    store = SemanticGraph(registry)
    fixtures = [
        ("obs", "ReportedObservation", "E-obs", "Observed flame persistence during suppression."),
        (
            "conclusion",
            "NASAConclusion",
            "E-conclusion",
            "NASA concluded suppressant concentration was too brief for surface cooling.",
        ),
        (
            "requirement",
            "Requirement",
            "E-requirement",
            "Materials shall meet this standard for spacecraft use.",
        ),
        ("guidance", "Guidance", "E-guidance", "Guidance for flammability assessments."),
        (
            "question",
            "OpenQuestion",
            "E-question",
            "NASA identified an open question about repeat testing.",
        ),
        ("measurement", "Measurement", "E-measurement", "Reported airflow measurement: 0.08 m/s."),
    ]
    for i, (entity, cls, eid, text) in enumerate(fixtures):
        evidence.add_passage(
            {
                "evidence_id": eid,
                "document_id": "doc",
                "page": i + 1,
                "section": cls,
                "text": text,
                "start_offset": None,
                "end_offset": None,
                "raw_file": None,
                "checksum": None,
            }
        )
        store.add_entity(
            entity,
            cls,
            [eid],
            ["SRC"],
            {"id": entity, "normalized_text": text, "statement_type": cls},
        )

    for requested, query, expected in (
        ("ReportedObservation", "What was observed about flame suppression?", "E-obs"),
        ("NASAConclusion", "What did NASA conclude about suppressant?", "E-conclusion"),
        (
            "Requirement",
            "What does the standard require for spacecraft materials?",
            "E-requirement",
        ),
        ("Guidance", "Find guidance for flammability assessment", "E-guidance"),
        (
            "OpenQuestion",
            "What open question did NASA identify about repeat testing?",
            "E-question",
        ),
        ("Measurement", "Find airflow measurements", "E-measurement"),
    ):
        result = execute_native(
            QueryIntentV2(targets=["ExperimentalRun"], requested_information=[requested]),
            query,
            store,
            evidence,
        )
        ids = {p["evidence_id"] for p in result.bundle.evidence_passages}
        assert ids == {expected}
        assert result.bundle.retrieval_metadata["selection_trace"]["information_candidates"]
        assert result.bundle.retrieval_metadata["selection_trace"]["ranked_passage_candidates"]
        assert result.bundle.direct_evidence
        assert not result.bundle.guidance or requested == "Guidance"
        assert not result.bundle.requirements or requested == "Requirement"
        assert not result.bundle.nasa_conclusions or requested == "NASAConclusion"
        if requested == "Measurement":
            assert result.bundle.measurements[0]["id"] == "measurement"
            assert not result.bundle.experimental_observations

    result = execute_native(
        QueryIntentV2(targets=["ExperimentalRun"], requested_information=["NASAConclusion"]),
        "NASA conclusion about lunar geology",
        store,
        evidence,
    )
    assert not result.bundle.evidence_passages
    assert result.bundle.no_direct_evidence
    assert (
        result.bundle.retrieval_metadata["selection_trace"]["no_direct_reason"]
        == "no_class_topic_source_eligible_evidence"
    )


def test_named_agency_is_not_treated_as_a_source_constraint():
    language = yaml.safe_load((ROOT / "domain/query_language_v2.yaml").read_text())
    registry = load_semantic_registry(ROOT / "domain/semantic_registry.yaml")
    intent = resolve_minimal(
        MinimalInterpretationV2(requested_information=["guidance"], sources=["NASA"]),
        registry,
        language,
        query="Find NASA guidance",
    )
    assert intent.requested_information == ["Guidance"]
    assert intent.source_constraints == []


def test_scientific_topic_does_not_imply_requested_safety_information():
    language = yaml.safe_load((ROOT / "domain/query_language_v2.yaml").read_text())
    registry = load_semantic_registry(ROOT / "domain/semantic_registry.yaml")
    intent = resolve_minimal(
        MinimalInterpretationV2(entities=["PMMA"]),
        registry,
        language,
        query="PMMA fire suppression experiment",
    )
    assert "SafetyImplication" not in intent.requested_information
    explicit = resolve_minimal(
        MinimalInterpretationV2(),
        registry,
        language,
        query="What safety implications did NASA identify?",
    )
    assert "SafetyImplication" in explicit.requested_information


def test_experimental_run_is_a_target_not_a_requested_information_class():
    language = yaml.safe_load((ROOT / "domain/query_language_v2.yaml").read_text())
    registry = load_semantic_registry(ROOT / "domain/semantic_registry.yaml")
    intent = resolve_minimal(
        MinimalInterpretationV2(targets=["experiments"], requested_information=["experiments"]),
        registry,
        language,
        query="Find PMMA experiments",
    )
    assert intent.targets == ["ExperimentalRun"]
    assert "ExperimentalRun" not in intent.requested_information


def test_resolver_clears_resolved_aliases_and_keeps_unknowns_unresolved():
    language = yaml.safe_load((ROOT / "domain/query_language_v2.yaml").read_text())
    registry = load_semantic_registry(ROOT / "domain/semantic_registry.yaml")
    proposal = MinimalInterpretationV2(
        operation="search",
        targets=["measurements"],
        entities=["SIBAL Fabric", "quasarcoat"],
        properties=[PropertyMention(label="airflow velocity", expression="roughly 0.2 m/s")],
        requested_information=["measurements"],
        ambiguous=["SIBAL Fabric", "quasarcoat", "airflow velocity"],
    )
    intent = resolve_minimal(
        proposal,
        registry,
        language,
        query="Find measurements for SIBAL Fabric and quasarcoat at roughly 0.2 m/s airflow velocity",
    )
    assert intent.targets == ["ExperimentalRun"]
    assert intent.requested_information == ["Measurement"]
    assert intent.entity_constraints[0].entity_id == "SIBAL Fabric"
    assert intent.property_constraints[0].property_id == "AirflowVelocity"
    assert intent.property_constraints[0].value.approximate
    assert "quasarcoat" in intent.unresolved_mentions
    assert "quasarcoat" not in intent.ambiguities
    assert "airflow velocity" not in intent.ambiguities


def test_context_qualifier_and_mmhg_conversion_are_explicit_and_dimension_safe():
    from nasa_fire_ai.normalization.units import normalize

    assert normalize(760, "mmHg") == (101325.01443540001, "Pa")
    assert normalize(10, "mmHg")[1] == "Pa"
    language = yaml.safe_load((ROOT / "domain/query_language_v2.yaml").read_text())
    registry = load_semantic_registry(ROOT / "domain/semantic_registry.yaml")
    operator, value = parse_expression("about 0.2 ± 0.01 m/s", "numeric", language["operators"])
    assert operator == "APPROX" and value.approximate and value.tolerance == 0.01

    store = SemanticGraph(registry)
    store.add_entity("run", "ExperimentalRun", ["E-run"])
    store.add_value(
        "initial",
        "run",
        "OxygenConcentration",
        GenericValue(reported_value=0.2, reported_unit="fraction"),
        ["E-initial"],
        {"context": "initial"},
        class_id="ExperimentalCondition",
    )
    store.add_value(
        "final",
        "run",
        "OxygenConcentration",
        GenericValue(reported_value=0.18, reported_unit="fraction"),
        ["E-final"],
        {"context": "final"},
        class_id="ExperimentalCondition",
    )
    q = QueryIntentV2(
        property_constraints=[
            PropertyConstraintV2(
                property_id="OxygenConcentration",
                operator="EQ",
                value=GenericValue(reported_value=0.2, reported_unit="fraction"),
                qualifiers={"context": "final"},
            )
        ]
    )
    assert classify_native("run", q, store)[0] == "NO_DIRECT"
    assert classify_native("run", q, store)[1]["differs"] == ["OxygenConcentration"]
    missing_context = QueryIntentV2(
        property_constraints=[
            PropertyConstraintV2(
                property_id="OxygenConcentration",
                operator="EQ",
                value=GenericValue(reported_value=0.2, reported_unit="fraction"),
                qualifiers={"context": "observed_measurement"},
            )
        ]
    )
    assert classify_native("run", missing_context, store)[1]["unknown"] == ["OxygenConcentration"]
