"""Verify original auxiliary science records and scoped graph paths over TCP."""

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from verify_scientific_restore_http import exercise

from nasa_fire_ai.services.conversation import ConversationService
from nasa_fire_ai.services.search import ScientificSearchService


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--snapshot-name", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Do not overwrite an acceptance receipt")

    def factory():
        return ConversationService(
            ScientificSearchService(args.root / "data/snapshots" / args.snapshot_name, args.root),
            provider=None,
            entailment=None,
        )

    def inspect(client):
        checked = []
        for accession, ordinals in ((98, (4, 5)), (99, (11, 12, 13, 14, 15, 16)), (26, (67,))):
            original = list(
                csv.reader(
                    (
                        args.root
                        / "data/raw/hackathon-psi"
                        / f"PSI-{accession}_experimental_table.csv"
                    ).open(encoding="utf-8-sig")
                )
            )
            response = client.get(
                "/api/v1/records",
                params={
                    "investigation": f"psi-{accession}",
                    "limit": 100,
                },
            )
            response.raise_for_status()
            records = {r["id"]: r for r in response.json()["items"]}
            for ordinal in ordinals:
                record = records[f"psi-{accession}-annotation-{ordinal}"]
                assert "ExperimentalRun" not in record["classes"]
                row = {
                    h.strip(): v for h, v in zip(original[0], original[ordinal - 1], strict=True)
                }
                fields = []
                for field in record["fields"]:
                    qualifier = field["qualifiers"]
                    assert qualifier["original_value"] == row[qualifier["source_header"]]
                    for eid in field["evidence_ids"]:
                        evidence = client.get("/api/v1/evidence/" + eid)
                        evidence.raise_for_status()
                        assert evidence.json()["structured_location"]["row_ordinal"] == ordinal
                    fields.append(field["property_id"])
                    if field["property_id"] == "source:regression_rate":
                        assert field["value"]["canonical_unit"] == "m/s"
                        assert abs(field["value"]["lower"] - 0.00001) < 1e-12
                        assert abs(field["value"]["upper"] - 0.00004) < 1e-12
                checked.append(
                    {
                        "record": record["id"],
                        "original_row": ordinal,
                        "classes": record["classes"],
                        "queryable_fields": fields,
                    }
                )
        paths = []
        for label, expected in (
            ("2-7", {"psi-99-annotation-14"}),
            ("2-8", {"psi-99-annotation-15", "psi-99-annotation-16"}),
            ("2-9", {"psi-99-annotation-16"}),
            ("2-6", set()),
        ):
            result = client.post(
                "/api/v1/ontology/navigate",
                json={
                    "start": "psi-99-" + label,
                    "steps": [{"relation": "hasSourceAnnotation"}],
                },
            )
            result.raise_for_status()
            assert {r["entity"] for r in result.json()["results"]} == expected
            paths.append({"source_record": label, **result.json()})
        result = client.post(
            "/api/v1/ontology/navigate",
            json={
                "start": "psi-99-2-8",
                "steps": [{"relation": "hasSourceAnnotation"}, {"relation": "hasRecordedField"}],
            },
        )
        result.raise_for_status()
        assert any(
            r["entity_details"].get("value", {}).get("canonical_unit") == "m/s"
            for r in result.json()["results"]
        )
        for row in result.json()["results"]:
            for edge in row["path"]:
                for eid in edge["evidence_ids"]:
                    client.get("/api/v1/evidence/" + eid).raise_for_status()
        return {
            "original_auxiliary_records": checked,
            "source_scoped_paths": paths,
            "two_hop_measurement_path": result.json(),
            "boundary": "Source/graph/HTTP verification; no model generation or usefulness score.",
        }

    result = exercise(factory, 8774, inspect)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                "original_auxiliary_records_checked": len(result["original_auxiliary_records"]),
                "scoped_routes_checked": len(result["source_scoped_paths"]),
                "two_hop_original_quantity": True,
            }
        )
    )


if __name__ == "__main__":
    main()
