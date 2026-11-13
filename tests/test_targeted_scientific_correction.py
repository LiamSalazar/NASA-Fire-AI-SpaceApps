"""Generic regressions independent of exposed case IDs."""

import json
from pathlib import Path

import pytest
import yaml

from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.structured_provenance import register_cells, round_trip, table_cells
from nasa_fire_ai.query.conceptual import is_conceptual_question
from nasa_fire_ai.query.native import SemanticGraph, execute_native
from nasa_fire_ai.query.native_interpreter import MinimalInterpretationV2, resolve_minimal
from nasa_fire_ai.query.related_presentation import group_related
from nasa_fire_ai.query.v2 import (
    QueryIntentV2,
    RelationDefinition,
    SemanticRegistry,
)

ROOT = Path(__file__).resolve().parents[1]


def language():
    return yaml.safe_load((ROOT / "domain/query_language_v2.yaml").read_text())


@pytest.mark.parametrize(
    "query,expected",
    [
        ("BASS tests", {"psi-26"}),
        ("BASS-II tests", {"psi-25"}),
        ("BASS and BASS-II tests", {"psi-25", "psi-26"}),
        ("Burning and Suppression of Solids-II tests", {"psi-25"}),
    ],
)
def test_exact_investigation_aliases(query, expected):
    registry = SemanticRegistry()
    registry.entities.update({"psi-25", "psi-26"})
    intent = resolve_minimal(MinimalInterpretationV2(), registry, language(), query=query)
    assert {c.entity_id for c in intent.entity_constraints} == expected


def test_unseen_overlapping_names():
    registry = SemanticRegistry()
    registry.entities.update({"study-a", "study-b"})
    doc = language()
    doc["entity_mentions"] = {
        "study-a": {"relation": "belongsToInvestigation", "aliases": ["DEMO"]},
        "study-b": {"relation": "belongsToInvestigation", "aliases": ["DEMO-X"]},
    }
    intent = resolve_minimal(MinimalInterpretationV2(), registry, doc, query="DEMO-X tests")
    assert [c.entity_id for c in intent.entity_constraints] == ["study-b"]
    broad = resolve_minimal(MinimalInterpretationV2(), registry, doc, query="DEMO series tests")
    assert broad.clarification_required
    assert "investigation_group_scope_unestablished" in broad.ambiguities


@pytest.mark.parametrize(
    "query",
    [
        "Does acrylic mean PMMA?",
        "Is helium equivalent to nitrogen?",
        "Is specimen a type of apparatus?",
        "What is the definition of extinction?",
        "Is helium a gas?",
        "Define extinction",
    ],
)
def test_conceptual_queries_preserve_operation(query, tmp_path):
    assert is_conceptual_question(query)
    registry = SemanticRegistry()
    intent = resolve_minimal(
        MinimalInterpretationV2(entities=["PMMA"]), registry, language(), query=query
    )
    assert intent.operation == "EXPLAIN"
    assert intent.targets == ["Publication"]
    assert intent.entity_constraints == []
    evidence = EvidenceRegistry(tmp_path / "evidence.sqlite")
    store = SemanticGraph(registry)
    store.add_entity("some-run", "ExperimentalRun", ["E-run"])
    historical = QueryIntentV2(targets=["ExperimentalRun"])
    result = execute_native(historical, query, store, evidence)
    assert not result.bundle.direct_evidence
    assert not result.bundle.related_evidence
    assert result.bundle.retrieval_metadata["conceptual_query"]["equivalence_asserted"] is False


def test_experiment_question_not_conceptual():
    assert not is_conceptual_question("PMMA experiments in microgravity")


def test_documentary_routing_preserves_explicit_investigation_scope():
    registry = SemanticRegistry()
    registry.entities.add("study-z")
    registry.entity_mentions = {
        "study-z": {"relation": "belongsToInvestigation", "aliases": ["ORION"]}
    }
    intent = resolve_minimal(
        MinimalInterpretationV2(entities=["ORION"]),
        registry,
        language(),
        query="In the ORION report and its data-organization document, what particle formation was modeled?",
    )
    assert intent.targets == ["Publication"]
    assert [c.entity_id for c in intent.entity_constraints] == ["study-z"]


def test_csv_round_trip_duplicates_and_multiline(tmp_path):
    source = tmp_path / "table.csv"
    source.write_text(
        'Test,Length (mm),Note\na,2,"line one\nline two"\na,2,"line one\nline two"\n',
        newline="\n",
    )
    headers, rows, metadata = table_cells(source, tmp_path)
    registry = EvidenceRegistry(tmp_path / "evidence.sqlite")
    for ordinal, row in enumerate(rows, 2):
        register_cells(registry, f"E-{ordinal}", metadata, ordinal, headers, row)
        register_cells(registry, f"E-{ordinal}", metadata, ordinal, headers, row)
    locators = [
        json.loads(r[0]) for r in registry.db.execute("SELECT locator_json FROM structured_cells")
    ]
    assert len(locators) == 6
    assert all(round_trip(locator, tmp_path) for locator in locators)
    locators[0]["original_value"] = "fabricated"
    with pytest.raises(ValueError, match="cell mismatch"):
        round_trip(locators[0], tmp_path)


def test_csv_round_trip_preserves_crlf_inside_quoted_cell(tmp_path):
    source = tmp_path / "table.csv"
    source.write_bytes(b'Test,Note\r\na,"line one\r\nline two"\r\n')
    headers, rows, metadata = table_cells(source, tmp_path)
    assert rows == [["a", "line one\r\nline two"]]
    registry = EvidenceRegistry(tmp_path / "evidence.sqlite")
    register_cells(registry, "E-2", metadata, 2, headers, rows[0])
    locators = [
        json.loads(r[0]) for r in registry.db.execute("SELECT locator_json FROM structured_cells")
    ]
    assert all(round_trip(locator, tmp_path) for locator in locators)


def test_related_groups_keep_all_ids_and_deduplicate_citations():
    registry = SemanticRegistry(
        relations=[RelationDefinition("belongsToInvestigation"), RelationDefinition("hasMaterial")]
    )
    store = SemanticGraph(registry)
    registry.entities.update({"study", "material"})
    items = []
    for run in ["a", "b"]:
        store.add_entity(run, "ExperimentalRun", ["E-shared"])
        store.add_relation(run, "belongsToInvestigation", "study", ["E-shared"])
        store.add_relation(run, "hasMaterial", "material", ["E-shared"])
        items.append(
            {
                "id": run,
                "evidence_ids": ["E-shared"],
                "relationship_explanation": {
                    "dimensions": [{"dimension": "gravity", "status": "UNKNOWN", "actual": []}]
                },
            }
        )
    result = group_related(items, store)
    assert result["complete_candidate_count"] == 2
    assert result["groups"][0]["candidate_ids"] == ["a", "b"]
    assert result["groups"][0]["evidence_ids"] == ["E-shared"]
    items[1]["relationship_explanation"]["dimensions"][0]["status"] = "DIFFER"
    assert len(group_related(items, store)["groups"]) == 2


def test_operational_fields_remain_unmapped():
    config = yaml.safe_load((ROOT / "domain/source_field_accessors.yaml").read_text())
    for kind in [
        "initial_carbon_dioxide",
        "burning_rate",
        "gmt",
        "flow_restrictor",
        "fan_display",
        "air_display",
        "total_frames_shot",
    ]:
        assert kind not in config["fields"]


def test_explicit_investigation_groups_are_distinct(tmp_path):
    registry = SemanticRegistry(
        relations=[RelationDefinition("belongsToInvestigation", selection_scope=True)]
    )
    registry.entities.update({"study-1", "study-2"})
    store = SemanticGraph(registry)
    evidence = EvidenceRegistry(tmp_path / "evidence.sqlite")
    for i in [1, 2]:
        sid, eid = f"study-{i}", f"E-{i}"
        evidence.add_source({"source_id": sid, "title": sid})
        evidence.add_document(sid, sid, sid)
        evidence.add_passage(
            {
                "evidence_id": eid,
                "document_id": sid,
                "page": None,
                "section": "table",
                "text": sid,
                "start_offset": 2,
                "end_offset": 2,
                "raw_file": "synthetic",
                "checksum": "synthetic",
            }
        )
        store.add_entity(f"run-{i}", "ExperimentalRun", [eid], [sid])
        store.add_relation(f"run-{i}", "belongsToInvestigation", sid, [eid])
    from nasa_fire_ai.query.v2 import EntityConstraintV2

    intent = QueryIntentV2(
        targets=["ExperimentalRun"],
        entity_constraints=[
            EntityConstraintV2(relation="belongsToInvestigation", entity_id=f"study-{i}")
            for i in [1, 2]
        ],
        ambiguities=["multiple_values_for_relation:belongsToInvestigation"],
        clarification_required=True,
    )
    result = execute_native(intent, "study-1 and study-2 tests", store, evidence)
    assert {(r["id"], r["requested_group"]) for r in result.bundle.direct_evidence} == {
        ("run-1", "study-1"),
        ("run-2", "study-2"),
    }
    assert len(result.bundle.retrieval_metadata["grouped_search"]) == 2
    assert {r["id"] for r in result.bundle.semantic_records} == {"run-1", "run-2"}
    single = execute_native(intent, "same experiment in study-1 and study-2", store, evidence)
    assert not single.bundle.direct_evidence
    assert "grouped_search" not in single.bundle.retrieval_metadata


def test_broad_report_does_not_force_safety_implication():
    registry = SemanticRegistry()
    registry.information_classes.add("Intervention")
    intent = resolve_minimal(
        MinimalInterpretationV2(),
        registry,
        language(),
        query="What has NASA reported about suppressing polymer fires?",
    )
    assert set(intent.requested_information) == {
        "ReportedObservation",
        "NASAConclusion",
        "Intervention",
    }
    assert "SafetyImplication" not in intent.requested_information


def test_context_topic_cannot_make_statement_direct(tmp_path):
    from nasa_fire_ai.query.evidence_selection import select_information

    registry = SemanticRegistry()
    registry.class_metadata = {"ReportedObservation": {"information": True}}
    registry.selection_policy = {
        "stop_words": ["what", "observed"],
        "topical_wordforms": {"suppression": ["suppression", "suppressing"]},
    }
    store = SemanticGraph(registry)
    evidence = EvidenceRegistry(tmp_path / "evidence.sqlite")
    evidence.add_source({"source_id": "source"})
    evidence.add_document("document", "source", "Synthetic experiment")
    for eid, text in [
        ("E-own", "Polymer specimen measured"),
        ("E-neighbor", "Suppression tests elsewhere"),
    ]:
        evidence.add_passage(
            {
                "evidence_id": eid,
                "document_id": "document",
                "page": 1,
                "section": None,
                "text": text,
                "start_offset": 0,
                "end_offset": len(text),
                "raw_file": "synthetic",
                "checksum": "synthetic",
            }
        )
    store.add_entity(
        "statement",
        "ReportedObservation",
        ["E-own"],
        ["source"],
        {"text": "Polymer specimen measured"},
    )
    selected, trace = select_information(
        QueryIntentV2(requested_information=["ReportedObservation"]),
        "what observed suppressing polymer",
        store,
        evidence,
    )
    assert not selected
    assert "requested_topic_absent_from_statement_scope:suppression" in trace[0]["excluded"]


def test_source_corrections_keep_units_and_derived_roles(monkeypatch):
    from nasa_fire_ai.ingestion.semantic import project_legacy
    from nasa_fire_ai.ingestion.source_corrections import project_source_corrections
    from nasa_fire_ai.normalization.units import normalize
    from nasa_fire_ai.query.native import classify_native
    from nasa_fire_ai.query.native_interpreter import PropertyMention
    from nasa_fire_ai.query.v2 import GenericValue, PropertyConstraintV2

    monkeypatch.setenv("ONTOLOGY_GRAPH_ENRICHMENT_ENABLED", "true")
    monkeypatch.setenv("SOURCE_KNOWLEDGE_ENRICHMENT_ENABLED", "true")
    monkeypatch.setenv("FLEX_SOURCE_CORRECTIONS_ENABLED", "true")
    monkeypatch.setenv("PSI_STRUCTURED_PUBLICATION_ENABLED", "true")
    evidence = EvidenceRegistry(ROOT / "data/index/evidence.sqlite")
    store = project_legacy(ROOT, evidence)
    report = json.loads((ROOT / "artifacts/phase3c_targeted_flex_corrections_v3.json").read_text())
    records = json.loads((ROOT / "data/canonical/records.json").read_text())
    for correction in report["corrections"]:
        original = correction["original_record"]
        payload = store.payload("source-correction:" + original["id"])
        assert payload["qualifiers"]["original_record"] == original
        assert payload["qualifiers"]["observed_status"] == "NOT_ASSERTED"
        assert payload["value"]["reported_unit"] == correction["corrected_source_unit"]
        query = QueryIntentV2(
            property_constraints=[
                PropertyConstraintV2(
                    property_id=payload["property_id"],
                    operator="EQ",
                    value=GenericValue(
                        reported_value=original["reported_value"],
                        reported_unit=correction["corrected_source_unit"],
                    ),
                )
            ]
        )
        assert classify_native(payload["subject"], query, store)[0] == "DIRECT"
        if correction["kind"] == "burning_rate":
            assert original["reported_unit"] == "mm"
            assert payload["qualifiers"]["role"] == "SOURCE_DERIVED_BURNING_RATE_CONSTANT"
            assert payload["value"]["canonical_unit"] == "m2/s"
    count = len(store.graph)
    project_source_corrections(store, evidence, ROOT, records)
    assert len(store.graph) == count
    assert normalize(1, "mm2/s") == (1e-6, "m2/s")
    assert normalize(1, "mm") == (0.001, "m")
    intent = resolve_minimal(
        MinimalInterpretationV2(
            properties=[PropertyMention(label="burning rate", expression="above 0.5 mm²/s")]
        ),
        store.registry,
        language(),
        query="burning rate above 0.5 mm²/s",
    )
    assert intent.property_constraints[0].value.reported_unit == "mm²/s"
    assert not intent.unresolved_mentions
    initial_intent = resolve_minimal(
        MinimalInterpretationV2(
            properties=[
                PropertyMention(label="initial carbon dioxide", expression="above 0 fraction")
            ]
        ),
        store.registry,
        language(),
        query="initial carbon dioxide above 0 fraction",
    )
    assert initial_intent.property_constraints[0].qualifiers["context"] == "initial"
    assert any(
        classify_native(value["subject"], initial_intent, store)[0] == "DIRECT"
        for value in (
            store.payload("source-correction:" + c["record_id"]) for c in report["corrections"]
        )
        if value["property_id"] == "source:initial_carbon_dioxide"
    )
    samples = resolve_minimal(
        MinimalInterpretationV2(targets=["samples"]),
        store.registry,
        language(),
        query="NASA samples",
    )
    assert samples.targets == ["Sample"]
    assert not samples.requested_information
    sample_intent = resolve_minimal(
        MinimalInterpretationV2(), store.registry, language(), query="PMMA SAFFIRE-II samples"
    )
    sample_result = execute_native(sample_intent, "PMMA SAFFIRE-II samples", store, evidence)
    assert len(sample_result.bundle.direct_evidence) == 1
    assert sample_result.bundle.direct_evidence[0]["id"] == "psi-99-reported-sample-2-8"


def test_pdf_location_is_explicit_and_conflicts_rejected(tmp_path):
    evidence = EvidenceRegistry(tmp_path / "registry.sqlite")
    evidence.add_source({"source_id": "s"})
    evidence.add_document("d", "s", "synthetic")
    evidence.add_passage(
        {
            "evidence_id": "E",
            "document_id": "d",
            "page": 5,
            "section": "table",
            "text": "x",
            "start_offset": 0,
            "end_offset": 1,
            "raw_file": "synthetic",
            "checksum": "synthetic",
        }
    )
    assert "page_location_verified" not in evidence.resolve("E")
    evidence.add_evidence_location(
        "E", {"physical_pdf_page": 5, "verification": "synthetic fixture"}
    )
    assert evidence.resolve("E")["page_location_verified"] is True
    with pytest.raises(ValueError, match="conflicting"):
        evidence.add_evidence_location("E", {"physical_pdf_page": 6})


def test_unseen_conceptual_identity_uses_approved_source_relation(tmp_path):
    from rdflib import OWL

    from nasa_fire_ai.query.hierarchy import TaxonomyEdge, add_taxonomy_edge

    registry = SemanticRegistry()
    registry.entities.update({"TermAlpha", "TermBeta"})
    store = SemanticGraph(registry)
    evidence = EvidenceRegistry(tmp_path / "registry.sqlite")
    evidence.add_source(
        {"source_id": "SyntheticAuthority", "title": "Synthetic terminology fixture"}
    )
    evidence.add_document("fixture", "SyntheticAuthority", "Synthetic terminology fixture")
    evidence.add_passage(
        {
            "evidence_id": "E-identity",
            "document_id": "fixture",
            "page": None,
            "section": "terminology",
            "text": "TermAlpha and TermBeta identify the same individual in this synthetic fixture.",
            "start_offset": 0,
            "end_offset": 83,
            "raw_file": None,
            "checksum": None,
        }
    )
    add_taxonomy_edge(
        store,
        TaxonomyEdge(
            "TermAlpha",
            str(OWL.sameAs),
            "TermBeta",
            "Synthetic reviewer",
            "APPROVED",
            "Synthetic fixture",
            "hasMaterial",
            "v1",
            ("E-identity",),
            "individual",
            "individual",
        ),
    )
    result = execute_native(
        QueryIntentV2(targets=["ExperimentalRun"]), "Does TermAlpha mean TermBeta?", store, evidence
    )
    assert not result.bundle.direct_evidence
    support = result.bundle.retrieval_metadata["conceptual_query"]["approved_relations"]
    assert len(support) == 1 and support[0]["predicate"] == str(OWL.sameAs)
    assert [p["evidence_id"] for p in result.bundle.evidence_passages] == ["E-identity"]
