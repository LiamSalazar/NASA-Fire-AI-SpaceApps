"""Real source checks for the bounded hackathon adapter, no scientific gold changes."""

from pathlib import Path

import pytest
from rdflib import RDF, Graph

from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.hackathon import build_snapshot, make_store, verify_snapshot
from nasa_fire_ai.query.native import NS
from nasa_fire_ai.query.ontology_navigation import RouteStep, navigate

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def snapshot(tmp_path_factory):
    output = tmp_path_factory.mktemp("corpus") / "snapshot"
    manifest = build_snapshot(ROOT, output)
    store = make_store(ROOT)
    store.graph = Graph().parse(output / "graph.ttl")
    store.registry.entities.update(store.entities())
    evidence = EvidenceRegistry(output / "evidence.sqlite", read_only=True)
    yield output, manifest, store, evidence
    evidence.db.close()


def test_original_integrity_and_idempotence(snapshot):
    output, manifest, _, _ = snapshot
    assert verify_snapshot(output, ROOT) == manifest
    assert build_snapshot(ROOT, output) == manifest
    replay = build_snapshot(ROOT, output.parent / "replay")
    assert replay["artifacts"] == manifest["artifacts"]
    assert manifest["depth_counts"]["A"] >= 2
    assert manifest["depth_counts"]["B"] >= 1
    assert manifest["depth_counts"]["C"] >= 1


def test_every_graph_reference_has_original(snapshot):
    _, _, store, registry = snapshot
    for eid in {str(e) for e in store.graph.objects(None, NS.evidenceRef)}:
        row = registry.resolve(eid)
        assert row and Path(row["raw_file"]).is_file()
        assert row["structured_location"]
        assert row["checksum"]


def test_saffire_scopes_and_values(snapshot):
    _, _, store, registry = snapshot
    assert store.values("psi-98-S1", "AirflowVelocity")[0].canonical_value == 0.2
    assert store.values("psi-98-S1", "OxygenConcentration")[0].lower == 0.215
    assert store.values("psi-98-S2", "OxygenConcentration")[0].approximate
    assert not store.relations("psi-98-S1", "hasGravityCondition")
    row = registry.resolve(store.evidence("psi-98-S1")[0])
    assert row["structured_location"]["row_ordinal"] == 2
    assert any(c["original_value"] == "20" for c in row["source_cells"])


def test_no_campaign_or_adjacent_row_condition_transfer(snapshot):
    _, _, store, _ = snapshot
    assert len(store.relations("psi-68", "hasSourceRecord")) == 8
    assert not store.relations("psi-68", "hasRun")
    assert not store.values("psi-102-5", "AirflowVelocity")
    assert store.values("psi-102-1", "AirflowVelocity")[0].canonical_value == 0.05
    assert not store.relations("psi-99-2-6", "hasMaterial")
    assert not store.relations("psi-99-2-7", "hasMaterial")
    assert not store.relations("psi-25-B3", "hasMaterial")


def test_approved_path_and_no_operational_locations_in_rdf(snapshot):
    _, _, store, registry = snapshot
    route = navigate(store, "psi-98", [RouteStep("hasRun"), RouteStep("usesSample")], registry)
    assert route["results"]
    serialized = store.graph.serialize(format="turtle")
    assert "/home/" not in serialized
    assert "sha256" not in serialized
    assert "original_header" not in serialized


def test_source_supported_measurement_roles(snapshot):
    _, _, store, _ = snapshot
    # v2 corrects the v1 condition-only contract using the original column header.
    assert "Measurement" in store.classes("psi-98-S1-value-9")
    assert "psi-98-S1-value-9" in store.relations("psi-98-S1", "hasMeasurement")
    assert "psi-98-S1-value-9" not in store.relations("psi-98-S1", "hasCondition")
    assert store.payload("psi-98-S1-value-9")["qualifiers"]["original_value"] == "420"
    assert "ExperimentalCondition" in store.classes("psi-98-S1-value-5", include_ancestors=True)
    assert not list(store.graph.subjects(RDF.type, NS.ReportedObservation))


def test_camera_rows_and_column_notes_are_not_runs(snapshot):
    _, _, store, _ = snapshot
    runs = [
        s
        for s in store.entities()
        if s.startswith("psi-99-") and "ExperimentalRun" in store.classes(s)
    ]
    assert len(runs) == 9
    assert all(not s.startswith("psi-99-Note") for s in runs)
    oxygen = store.value_records("psi-99-2-1", "OxygenConcentration")
    assert oxygen[0]["qualifiers"]["modality"] == "derived"
    assert oxygen[0]["qualifiers"]["source_note"] == "Note 1"
