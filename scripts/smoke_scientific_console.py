"""Real TCP integration checks using registered records, graph edges and sources."""

import argparse
import json
from pathlib import Path

import httpx


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Do not overwrite a smoke receipt")
    checks = {}
    with httpx.Client(base_url=args.url + "/api/v1", timeout=240) as client:

        def get(path, **kwargs):
            response = client.get(path, **kwargs)
            response.raise_for_status()
            return response.json()

        checks["health"] = get("/health")["status"] == "ok"
        overview = get("/research/overview")
        checks["investigations"] = overview["investigations"]
        studies = get("/research/investigations", params={"query": "Saffire"})
        assert {s["id"] for s in studies["items"]} == {"psi-98", "psi-99", "psi-100"}
        checks["investigation_filter"] = True
        records = get("/records", params={"investigation": "psi-25", "identifier": "B12"})
        record = records["items"][0]
        cells = [c for e in record["evidence"] for c in e.get("source_cells", [])]
        verified = 0
        for field in record["fields"]:
            q = field["qualifiers"]
            assert any(
                c["original_header"].strip() == q["source_header"]
                and c["original_value"] == q["original_value"]
                for c in cells
            )
            verified += 1
        checks["original_cell_fields_verified"] = verified
        response = client.post(
            "/comparisons",
            json={
                "subjects": ["psi-100-S1", "psi-100-S2"],
                "dimensions": ["AirflowVelocity", "FlowDirection"],
            },
        )
        response.raise_for_status()
        matrix = response.json()["matrix"]
        assert {r["dimension"]: r["status"] for r in matrix} == {
            "AirflowVelocity": "MATCH",
            "FlowDirection": "DIFFER",
        }
        assert all(
            v["value"]["reported_unit"] == "cm/s"
            for row in matrix
            if row["dimension"] == "AirflowVelocity"
            for values in row["values"].values()
            for v in values
        )
        checks["native_comparison_and_units"] = True
        response = client.post(
            "/research/investigation-comparison",
            json={"subjects": ["psi-107", "psi-106"], "dimensions": ["usesInstrument"]},
        )
        response.raise_for_status()
        row = response.json()["rows"][0]
        assert row["status"] == "SHARED" and len(row["shared"]) == 3
        checks["shared_registered_instruments"] = 3
        graph = get("/research/entities/psi-107/neighbors", params={"limit": 8})
        assert graph["edges"] and all("psi-107" in {e["from"], e["to"]} for e in graph["edges"])
        resolved = 0
        for edge in graph["edges"]:
            for eid in edge["evidence_ids"]:
                original = get("/evidence/" + eid)
                assert original["text"] and "raw_file" not in original
                resolved += 1
        checks["graph_edge_evidence_resolved"] = resolved
        record_view = get("/research/entities/psi-107-record-5")
        assert record_view["title"] == "Source row 5" and record_view["source_fields"]
        checks["readable_record_projection"] = True
        response = client.post("/search", json={"query": "PMMA oxygen 22.2 %", "limit": 10})
        response.raise_for_status()
        assert response.json()["direct"] and response.json()["related"]
        checks["search_direct_and_related"] = True
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps({"status": "passed", "checks": checks}, indent=2) + "\n")
        schema = client.get(args.url + "/openapi.json")
        if schema.status_code == 200:
            args.output.with_name("openapi.json").write_text(
                json.dumps(schema.json(), indent=2) + "\n"
            )
    print(json.dumps(checks))


if __name__ == "__main__":
    main()
