"""Reconcile team inventory, original PSI tables, and a scientific snapshot."""

import argparse
import csv
import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FAMILIES = ("solids", "droplets", "gas_flames", "aerosols", "sessions")


def records(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def report(root, snapshot):
    clean = root / "data/raw/hackathon-team/data/clean"
    campaigns = records(clean / "campaigns.csv")
    publications = records(clean / "publications.csv")
    processed = defaultdict(list)
    for family in FAMILIES:
        for row in records(clean / f"{family}.csv"):
            processed[row["accession"]].append((family, row))
    manifest = json.loads((snapshot / "manifest.json").read_text())
    sources = {row["source_id"]: row for row in manifest["sources"]}
    db = sqlite3.connect(snapshot / "evidence.sqlite")
    evidence_counts = dict(
        db.execute(
            "SELECT d.source_id,count(*) FROM passages p JOIN documents d USING(document_id) GROUP BY d.source_id"
        )
    )
    db.close()
    for family in FAMILIES:
        expected = len(records(clean / f"{family}.csv"))
        actual = evidence_counts.get(f"team-processed-{family}", 0)
        if actual != expected:
            raise ValueError(f"Processed row index mismatch for {family}: {actual}/{expected}")
    table_receipts = [
        root / "artifacts/hackathon/official_tables.json",
        root / "artifacts/hackathon/official_tables_expansion_20261109.json",
    ]
    official = {
        row["source_id"]: row
        for path in table_receipts
        if path.exists()
        for row in json.loads(path.read_text())
    }
    matrix = []
    for campaign in campaigns:
        accession = campaign["accession"]
        sid = accession.lower()
        values = processed[accession]
        qc = Counter()
        for _, row in values:
            if row.get("qc_flags"):
                qc.update(x.strip() for x in row["qc_flags"].split(";") if x.strip())
        excluded = sum(
            (row.get("excluded") or "").lower() in {"1", "true", "yes"}
            for _, row in values
        )
        source = official.get(accession)
        original = sources.get(sid, {})
        indexed = sum(
            1 for family, _ in values if evidence_counts.get(f"team-processed-{family}", 0)
        )
        depth = original.get("depth", "C")
        disposition = (
            "source_explicit_structured_and_documentary"
            if depth == "A"
            else "original_table_documentary_pending_mapping"
            if depth == "B"
            else "team_processed_discovery_only_pending_original"
            if values
            else "catalogue_only_no_eligible_table_rows"
        )
        matrix.append(
            {
                "accession": accession,
                "investigation": campaign["title"],
                "campaign": campaign["campaign"],
                "family": campaign["family"],
                "team_table_kind": campaign["table_kind"],
                "available": True,
                "catalogue_metadata": True,
                "original_nasa_table": source,
                "original_table_evidence_rows": evidence_counts.get(sid, 0),
                "processed_family_tables": sorted({family for family, _ in values}),
                "processed_rows": len(values),
                "eligible_processed_rows": len(values) - excluded,
                "excluded_processed_rows": excluded,
                "provisional_indexed_rows": indexed,
                "available_measurement_columns": sorted(
                    {key for _, row in values for key, value in row.items() if value and key not in {
                        "uid", "accession", "campaign", "family", "test_id", "date",
                        "n_flags", "qc_flags", "excluded", "exclude_reason", "source_file", "source_line",
                    }}
                ),
                "publications_metadata_records": sum(r["accession"] == accession for r in publications),
                "full_text_publications_verified": 0,
                "qc_flags": dict(qc.most_common()),
                "provenance": "original PSI bytes and cell locators" if source else "team processed CSV with claimed source_file/source_line only",
                "ingestion_status": disposition,
                "rdf_depth": depth,
                "text_index_evidence_rows": evidence_counts.get(sid, 0) + indexed + evidence_counts.get("catalog-" + sid, 0),
                "vector_index_rows": 0,
                "api_queryability": "original structured/documentary and provisional discovery"
                if source else "provisional discovery and catalogue only",
                "remaining_gap": "Original row interpretation and QC review required"
                if source else "Original NASA table or publication text unavailable in this snapshot",
            }
        )
    eligible = sum(row["eligible_processed_rows"] for row in matrix)
    disposed = sum(
        row["eligible_processed_rows"]
        for row in matrix
        if row["provisional_indexed_rows"] == row["processed_rows"]
    )
    return {
        "snapshot_id": manifest["snapshot_id"],
        "campaigns": matrix,
        "summary": {
            "campaigns_classified": len(matrix),
            "team_campaigns": len(campaigns),
            "processed_family_rows": sum(row["processed_rows"] for row in matrix),
            "eligible_processed_rows": eligible,
            "eligible_rows_represented_or_explicitly_disposed": disposed,
            "science_verified_rows": None,
            "original_psi_tables": len(official),
            "original_psi_table_evidence_rows": sum(row["original_table_evidence_rows"] for row in matrix),
            "publications_metadata_records": len(publications),
            "full_text_publications_verified": 0,
            "vector_index_provisioned": False,
        },
        "interpretation": "Processed row disposition is discovery access, not scientific validation; original rows and clean rows have different granularity and are not equated.",
    }


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Preserve prior receipts: output must not exist")
    result = report(ROOT, args.snapshot)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result["summary"], indent=2))


if __name__ == "__main__":
    main()
