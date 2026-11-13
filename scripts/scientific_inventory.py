"""Inventory source depth and every original table column without inferring science."""

import argparse
import json
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nasa_fire_ai.ingestion.hackathon import verify_snapshot
from nasa_fire_ai.ingestion.structured_provenance import table_cells


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = verify_snapshot(args.snapshot, ROOT)
    db = sqlite3.connect(args.snapshot / "evidence.sqlite")
    db.row_factory = sqlite3.Row
    fields = defaultdict(Counter)
    locations = defaultdict(set)
    for row in db.execute(
        "SELECT c.*,v.value_id FROM structured_cells c LEFT JOIN value_cells v ON v.evidence_id=c.evidence_id AND v.column_ordinal=c.column_ordinal"
    ):
        locator = json.loads(row["locator_json"])
        path = locator["raw_file"]
        key = (path, locator["original_header"])
        if str(locator["original_value"]).strip():
            locations[key].add((row["evidence_id"], row["column_ordinal"]))
            if row["value_id"]:
                fields[key]["value_links"] += 1
    tables = []
    for source in manifest["sources"]:
        if source["depth"] != "A":
            continue
        accession = source["source_id"].upper()
        path = f"data/raw/hackathon-psi/{accession}_experimental_table.csv"
        headers, raw_rows, _ = table_cells(ROOT / path, ROOT)
        rows = [dict(zip(headers, row, strict=False)) for row in raw_rows if any(row)]
        columns = []
        for header in rows[0]:
            # Locators preserve the original header, including whitespace.
            keys = [key for key in fields if key[0] == path and key[1].strip() == header.strip()]
            mapped = sum(fields[key]["value_links"] for key in keys)
            columns.append(
                {
                    "original_header": header,
                    "nonempty_source_rows": sum(bool(row[header].strip()) for row in rows),
                    "queryable_value_links": mapped,
                    "representation": "typed_field_with_cell_lineage"
                    if mapped
                    else "original_identifier_or_material_payload_or_documentary_source_cell",
                }
            )
        tables.append(
            {
                "source_id": source["source_id"],
                "source_rows": len(rows),
                "columns": columns,
                "adapter_receipt": source,
            }
        )
    sources = []
    for source in db.execute("SELECT source_id,title,source_type FROM sources ORDER BY source_id"):
        counts = db.execute(
            "SELECT COUNT(*) FROM passages p JOIN documents d USING(document_id) WHERE d.source_id=?",
            (source["source_id"],),
        ).fetchone()[0]
        sources.append({**dict(source), "searchable_passages": counts})
    result = {
        "snapshot_id": manifest["snapshot_id"],
        "depth_counts": manifest["depth_counts"],
        "sources": sources,
        "original_tables": tables,
        "boundary": "Header coverage is not proof of physical-run identity or measured status. Read each field's curated role and raw cell. Catalogue/publication metadata is not full-text findings.",
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    db.close()


if __name__ == "__main__":
    main()
