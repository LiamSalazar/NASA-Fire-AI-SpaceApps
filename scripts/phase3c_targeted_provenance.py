"""Validate historical CSV row contracts and attach exact cell locators additively."""

import csv
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.structured_provenance import register_cells, round_trip, table_cells


def main():
    registry = EvidenceRegistry(ROOT / "data/index/evidence.sqlite")
    results = []
    cache = {}
    legacy_decoding = {}
    for passage in registry.db.execute(
        "SELECT * FROM passages WHERE raw_file LIKE '%.csv' AND evidence_id NOT LIKE 'E-targeted-%'"
    ).fetchall():
        path = ROOT / passage["raw_file"]
        if not path.exists():
            path = ROOT / "data/raw" / passage["raw_file"]
        row = {
            "evidence_id": passage["evidence_id"],
            "historical_offsets": [passage["start_offset"], passage["end_offset"]],
        }
        if not path.exists():
            row["status"] = "MISSING_SOURCE"
            results.append(row)
            continue
        if path not in cache:
            cache[path] = table_cells(path, ROOT)
            legacy_decoding[path] = list(
                csv.reader(io.StringIO(path.read_bytes().decode("utf-8-sig", errors="replace")))
            )[1:]
        headers, values, metadata = cache[path]
        if passage["checksum"] != metadata["checksum"]:
            row["status"] = "CHECKSUM_MISMATCH"
            results.append(row)
            continue
        matches = []
        for ordinal, cells in enumerate(values, 2):
            buffer = io.StringIO()
            csv.writer(buffer, lineterminator="").writerow(cells)
            legacy_row = legacy_decoding[path][ordinal - 2]
            if passage["text"] in {",".join(cells), buffer.getvalue(), ",".join(legacy_row)}:
                matches.append((ordinal, cells))
        ordinal_matches = [
            m for m in matches if m[0] == passage["start_offset"] == passage["end_offset"]
        ]
        resolved = ordinal_matches if len(ordinal_matches) == 1 else matches
        if len(resolved) == 1 and len(resolved[0][1]) == len(headers):
            ordinal, cells = resolved[0]
            register_cells(registry, passage["evidence_id"], metadata, ordinal, headers, cells)
            row.update(
                status="EXACT_ROW_VERIFIED",
                row_ordinal=ordinal,
                columns=len(headers),
                offset_contract="corroborated CSV logical row ordinal; not character offsets",
            )
        else:
            row.update(status="UNRESOLVED", matching_rows=len(matches))
        results.append(row)
    checks = [
        round_trip(json.loads(r[0]), ROOT)
        for r in registry.db.execute("SELECT locator_json FROM structured_cells")
    ]
    path = ROOT / "artifacts/phase3c_targeted_legacy_provenance_v2.json"
    assert not path.exists()
    path.write_text(
        json.dumps(
            {
                "rows": results,
                "round_trip_numerator": sum(checks),
                "round_trip_denominator": len(checks),
            },
            indent=2,
        )
    )
    print(
        {
            "verified_rows": sum(r["status"] == "EXACT_ROW_VERIFIED" for r in results),
            "cells": len(checks),
        }
    )


if __name__ == "__main__":
    main()
