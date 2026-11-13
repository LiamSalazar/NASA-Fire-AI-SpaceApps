from pathlib import Path

import pytest
from pyshacl import validate
from rdflib import RDFS, Graph

from nasa_fire_ai.ingestion.enrichment import source_rows, specimen_dimensions
from nasa_fire_ai.ingestion.knowledge import normalize_mention
from nasa_fire_ai.ingestion.source_spans import recover_span
from nasa_fire_ai.normalization.units import normalize


def test_reversible_whitespace_unicode_offsets():
    source = "Pressure:\n  20\u00a0kPa; cafe\u0301 flames."
    located = recover_span(source, "Pressure: 20 kPa; café flames.")
    assert source[located["start"] : located["end"]] == located["span"]
    assert located["method"] == "WHITESPACE_NFC"
    with pytest.raises(ValueError):
        recover_span(source, "Pressure: 25 kPa; café flames.")
    with pytest.raises(ValueError):
        recover_span("fire fire", "fire")
    assert recover_span("fire fire", "fire", 5)["start"] == 5


def test_generic_dimensions_and_identity_rejection():
    result = specimen_dimensions("1 cm wide 200 micron thick MaterialQ")
    assert [r["attribute"] for r in result] == ["width", "thickness"]
    assert result[1]["canonical_value"] == pytest.approx(0.0002)
    assert result[1]["reported_unit"] == "micron"
    assert specimen_dimensions("2 cm MaterialQ") == []
    assert normalize_mention("MaterialQ-compatible foam", {"Q": ["MaterialQ"]})["identity"] is None
    assert normalize_mention("not MaterialQ", {"Q": ["MaterialQ"]})["identity"] is None


def test_table_column_integrity(tmp_path):
    p = tmp_path / "source.csv"
    p.write_text("Fuel,Initial diameter; mm,Extinction diameter; mm\nMaterialQ,2,1\n")
    headers, row = source_rows({"raw_file": str(p), "text": "MaterialQ,2,1"}, tmp_path)
    assert dict(zip(headers, row, strict=True))["Initial diameter; mm"] == "2"
    assert source_rows({"raw_file": str(p), "text": "MaterialQ,2"}, tmp_path) == (None, None)


def test_units_do_not_change_dimensions():
    assert normalize(200, "um") == (pytest.approx(0.0002), "m")
    assert normalize(20, "ppm") == (pytest.approx(0.00002), "fraction")
    # Source-backed FLEX Table IX now documents this area/time unit. It must
    # remain dimensionally distinct from both a length and a linear velocity.
    assert normalize(1, "mm2/s") == (pytest.approx(1e-6), "m2/s")
    assert normalize(1, "mm")[1] == "m"


def test_declarations_do_not_entail_domains_and_ranges():
    root = Path(__file__).resolve().parents[1]
    schema = Graph().parse(root / "ontology/fire_safety.ttl")
    assert not list(schema.triples((None, RDFS.domain, None)))
    assert not list(schema.triples((None, RDFS.range, None)))
    original = Graph().parse(root / "data/canonical/graph.ttl")
    assert validate(original, shacl_graph=str(root / "ontology/enrichment_shapes.ttl"))[0]


@pytest.fixture(scope="module")
def enriched_store():
    import os

    from nasa_fire_ai.evidence import EvidenceRegistry
    from nasa_fire_ai.ingestion.semantic import project_legacy

    root = Path(__file__).resolve().parents[1]
    flags = ["ONTOLOGY_GRAPH_ENRICHMENT_ENABLED", "SOURCE_KNOWLEDGE_ENRICHMENT_ENABLED"]
    old = {key: os.environ.get(key) for key in flags}
    try:
        for key in flags:
            os.environ[key] = "true"
        yield project_legacy(root, EvidenceRegistry(root / "data/index/evidence.sqlite"))
    finally:
        for key, value in old.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def test_source_field_roles_and_ambiguities(enriched_store):
    report = enriched_store.source_enrichment_report
    assert len(report["mapped"]) == 1777
    assert {"burning_rate", "initial_carbon_dioxide"}.isdisjoint(
        x["original"]["kind"] for x in report["mapped"]
    )
    for row in report["mapped"]:
        assert row["qualifiers"]["observed_status"] == "NOT_ASSERTED"
        assert (
            enriched_store.payload(row["record_id"])["value"]["reported_unit"]
            == row["original"]["reported_unit"]
        )
    assert all(x["specimen_identity_preserved"] for x in report["specimens"])
    assert sum(x["identity"] is not None for x in report["specimens"]) == 312


def test_new_fields_are_executable_not_measurements(enriched_store):
    from nasa_fire_ai.query.native import classify_native
    from nasa_fire_ai.query.v2 import GenericValue, PropertyConstraintV2, QueryIntentV2

    row = next(
        x
        for x in enriched_store.source_enrichment_report["mapped"]
        if x["original"]["kind"] == "initial_droplet_diameter"
    )
    subject = enriched_store.payload(row["record_id"])["subject"]
    q = QueryIntentV2(
        property_constraints=[
            PropertyConstraintV2(
                property_id=row["property_id"],
                operator="EQ",
                value=GenericValue(
                    reported_value=row["original"]["reported_value"],
                    reported_unit=row["original"]["reported_unit"],
                ),
            )
        ]
    )
    assert classify_native(subject, q, enriched_store)[0] == "DIRECT"
    assert "Measurement" not in enriched_store.classes(row["record_id"])
    q.property_constraints[0].value.reported_value *= 2
    assert classify_native(subject, q, enriched_store)[0] != "DIRECT"


def test_duplicate_csv_rows_are_not_resolved(tmp_path):
    path = tmp_path / "duplicate.csv"
    path.write_text("Fuel,Value\nMaterialQ,1\nMaterialQ,1\n")
    assert source_rows({"raw_file": str(path), "text": "MaterialQ,1"}, tmp_path) == (None, None)
    with pytest.raises(ValueError):
        recover_span("some text", "   ")


def test_native_intent_does_not_force_safety(enriched_store):
    import yaml

    from nasa_fire_ai.query.native_interpreter import MinimalInterpretationV2, resolve_minimal

    root = Path(__file__).resolve().parents[1]
    language = yaml.safe_load((root / "domain/query_language_v2.yaml").read_text())
    intent = resolve_minimal(
        MinimalInterpretationV2(requested_information=["observations"]),
        enriched_store.registry,
        language,
        query="What did NASA observe about suppression?",
    )
    assert "SafetyImplication" not in intent.requested_information
    intent = resolve_minimal(
        MinimalInterpretationV2(entities=["Methanol"]),
        enriched_store.registry,
        language,
        query="Find Methanol experiments",
    )
    assert any(c.entity_id == "Methanol" for c in intent.entity_constraints)


def test_broad_query_does_not_gain_safety_scope():
    from nasa_fire_ai.query.controlled_reasoning import validate_expansion
    from nasa_fire_ai.query.v2 import QueryIntentV2, SemanticRegistry

    assert not validate_expansion(
        "What about acrylic fires?",
        "acrylic combustion NASA safety",
        QueryIntentV2(),
        SemanticRegistry(),
    )[0]


def test_pdf_table_retains_columns(tmp_path):
    import pymupdf

    from nasa_fire_ai.ingestion.pdf import extract_pdf_tables

    path = tmp_path / "table.pdf"
    with pymupdf.open() as doc:
        page = doc.new_page()
        for x in [40, 180, 320]:
            page.draw_line((x, 40), (x, 140))
        for y in [40, 90, 140]:
            page.draw_line((40, y), (320, y))
        for x, y, text in [
            (50, 65, "Initial mm"),
            (190, 65, "Final mm"),
            (50, 115, "2"),
            (190, 115, "1"),
        ]:
            page.insert_text((x, y), text)
        doc.save(path)
    table = extract_pdf_tables(path)[0]
    assert table["cells"] == [["Initial mm", "Final mm"], ["2", "1"]]
    assert table["physical_pdf_page"] == 1
    assert table["publication_status"] == "REVIEW_REQUIRED"


def test_enrichment_projection_is_idempotent(enriched_store):
    import json

    import yaml

    from nasa_fire_ai.evidence import EvidenceRegistry
    from nasa_fire_ai.ingestion.enrichment import enrich_source_fields

    root = Path(__file__).resolve().parents[1]
    records = json.loads((root / "data/canonical/records.json").read_text())
    language = yaml.safe_load((root / "domain/query_language_v2.yaml").read_text())
    aliases = {
        k: v["aliases"]
        for k, v in language["entity_mentions"].items()
        if v["relation"] == "hasMaterial"
    }
    triples, count = len(enriched_store.graph), enriched_store.projection_report["conditions"]
    enrich_source_fields(
        enriched_store,
        records,
        EvidenceRegistry(root / "data/index/evidence.sqlite"),
        root,
        aliases,
    )
    assert len(enriched_store.graph) == triples
    assert enriched_store.projection_report["conditions"] == count
    assert len(enriched_store.projection_staging) == 537


def test_source_labels_can_be_requested_with_spaces(enriched_store):
    import yaml

    from nasa_fire_ai.query.native_interpreter import (
        MinimalInterpretationV2,
        PropertyMention,
        resolve_minimal,
    )

    root = Path(__file__).resolve().parents[1]
    language = yaml.safe_load((root / "domain/query_language_v2.yaml").read_text())
    query = "Find experiments with initial droplet diameter >= 2 mm"
    intent = resolve_minimal(
        MinimalInterpretationV2(
            properties=[PropertyMention(label="initial droplet diameter", expression=">= 2 mm")]
        ),
        enriched_store.registry,
        language,
        query=query,
    )
    assert intent.property_constraints[0].property_id == "source:initial_droplet_diameter"
    assert intent.property_constraints[0].operator == "GTE"
