"""Actual snapshot HTTP projections preserve scientific identity and provenance."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from nasa_fire_ai.api import create_app
from nasa_fire_ai.services.conversation import ConversationService
from nasa_fire_ai.services.search import ScientificSearchService

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "data/snapshots/hackathon-20261112-scientific-rc14"


@pytest.fixture(scope="module")
def console_client():
    def factory():
        return ConversationService(ScientificSearchService(SNAPSHOT, ROOT))

    with TestClient(create_app(factory)) as client:
        yield client


def test_investigations_are_real_bounded_and_filterable(console_client):
    overview = console_client.get("/api/v1/research/overview").json()
    assert overview["investigations"] >= 2
    page = console_client.get("/api/v1/research/investigations?limit=2").json()
    assert len(page["items"]) == 2 and page["total"] == overview["investigations"]
    assert all("Investigation" in row["classes"] for row in page["items"])
    assert "raw_file" not in str(page)
    filtered = console_client.get(
        "/api/v1/research/investigations", params={"query": "Saffire"}
    ).json()
    assert {r["id"] for r in filtered["items"]} == {"psi-98", "psi-99", "psi-100"}
    assert (
        console_client.get("/api/v1/research/investigations?query=unmatched-violet-device").json()[
            "total"
        ]
        == 0
    )
    assert console_client.get("/api/v1/research/investigations?limit=101").status_code == 422
    assert (
        console_client.get("/api/v1/research/investigations/unregistered-device").status_code == 404
    )


def test_method_and_instrument_filters_use_registered_connections(console_client):
    overview = console_client.get("/api/v1/research/overview").json()
    for key, parameter in [("usesInstrument", "instrument"), ("hasDocumentedMethod", "method")]:
        feature = overview["facets"][key][0]
        rows = console_client.get(
            "/api/v1/research/investigations", params={parameter: feature["id"]}
        ).json()["items"]
        assert rows and all(
            feature["id"] in {v["id"] for v in row["features"][key]} for row in rows
        )


def test_graph_edges_have_actual_registered_evidence_and_direction(console_client):
    response = console_client.get("/api/v1/research/entities/psi-107/neighbors?limit=5").json()
    assert len(response["edges"]) == 5
    assert all("psi-107" in {e["from"], e["to"]} for e in response["edges"])
    for edge in response["edges"]:
        assert edge["classification"] == "RELATED"
        assert edge["evidence_ids"]
        for eid in edge["evidence_ids"]:
            assert console_client.get("/api/v1/evidence/" + eid).status_code == 200
    assert console_client.get("/api/v1/research/entities/unknown/neighbors").status_code == 404
    assert (
        console_client.get(
            "/api/v1/research/entities/psi-107/neighbors?relation=unapproved"
        ).status_code
        == 422
    )


def test_study_comparison_uses_actual_shared_instrument_entities(console_client):
    response = console_client.post(
        "/api/v1/research/investigation-comparison",
        json={
            "subjects": ["psi-107", "psi-106"],
            "dimensions": ["usesInstrument"],
        },
    )
    assert response.status_code == 200
    row = response.json()["rows"][0]
    assert row["status"] == "SHARED" and len(row["shared"]) == 3
    assert all("Instrument" in item["classes"] for item in row["shared"])
    assert all(v["association_evidence_ids"] for items in row["values"].values() for v in items)
    assert (
        console_client.post(
            "/api/v1/research/investigation-comparison",
            json={
                "subjects": ["psi-107", "psi-107"],
                "dimensions": [],
            },
        ).status_code
        == 422
    )
    assert (
        console_client.post(
            "/api/v1/research/investigation-comparison",
            json={
                "subjects": ["psi-107", "unknown"],
                "dimensions": [],
            },
        ).status_code
        == 404
    )


def test_source_record_projection_does_not_display_json_as_a_scientific_title(console_client):
    response = console_client.get("/api/v1/research/entities/psi-107-record-5")
    assert response.status_code == 200
    record = response.json()
    assert record["title"] == "Source row 5"
    assert record["source_fields"] and "text" not in record
    assert all(set(field) == {"label", "value"} for field in record["source_fields"])


def test_exact_lookup_preserves_identity_and_does_not_search(console_client):
    result = console_client.get("/api/v1/resolve", params={"query": "PSI-100"}).json()
    assert result["identifier"] and result["items"]
    assert {item.get("source_id", item.get("id")) for item in result["items"]} == {"psi-100"}
    source = next(item for item in result["items"] if item["kind"] == "source")
    assert source["evidence_ids"]
    evidence_id = source["evidence_ids"][0]
    evidence = console_client.get("/api/v1/resolve", params={"query": evidence_id}).json()
    assert evidence["items"][0]["evidence_id"] == evidence_id
    unknown = console_client.get("/api/v1/resolve", params={"query": "PSI-9999999"}).json()
    assert unknown["identifier"] and unknown["total"] == 0
    conceptual = console_client.get(
        "/api/v1/resolve", params={"query": "violet apparatus research"}
    ).json()
    assert not conceptual["identifier"]
    record = console_client.get("/api/v1/resolve", params={"query": "S2"}).json()
    assert record["identifier"] and any(item["id"] == "psi-100-S2" for item in record["items"])


def test_method_labels_and_combined_filters_are_source_backed(console_client):
    overview = console_client.get("/api/v1/research/overview").json()
    labels = [v["title"] for v in overview["facets"]["hasDocumentedMethod"]]
    assert labels and len(set(labels)) == len(labels)
    assert all(label.casefold() != "approach" for label in labels)
    page = console_client.get("/api/v1/research/investigations?query=Saffire&limit=100").json()
    row = next(v for v in page["items"] if v["features"].get("hasMaterial"))
    material = row["features"]["hasMaterial"][0]["id"]
    filtered = console_client.get(
        "/api/v1/research/investigations",
        params={
            "query": "Saffire",
            "material": material,
            "record_class": next(iter(row["record_classes"])),
        },
    ).json()
    assert row["id"] in {v["id"] for v in filtered["items"]}
