"""Exact CSV cell locators, stored only in the operational evidence registry."""

import csv
import hashlib
from pathlib import Path


def table_cells(path, root):
    path = Path(path)
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    # Decode bytes directly: read_text would translate CRLF inside quoted cells,
    # while round_trip reads with newline="" and keeps the original characters.
    try:
        text = data.decode("utf-8-sig")
        encoding = "utf-8-sig"
    except UnicodeDecodeError:
        text = data.decode("cp1252")
        encoding = "cp1252"
    import io

    rows = list(csv.reader(io.StringIO(text, newline="")))
    headers = rows[0]
    return (
        headers,
        rows[1:],
        {
            "raw_file": str(path.relative_to(root)),
            "checksum": digest,
            "encoding": encoding,
            "table": "CSV",
            "source_version": digest,
            "offset_contract": "one-based logical CSV record ordinal including header",
        },
    )


def round_trip(locator, root):
    path = root / locator["raw_file"]
    if hashlib.sha256(path.read_bytes()).hexdigest() != locator["checksum"]:
        raise ValueError("source checksum mismatch")
    with path.open(encoding=locator["encoding"], newline="") as handle:
        rows = list(csv.reader(handle))
    row, col = locator["row_ordinal"], locator["column_ordinal"]
    if rows[0][col - 1] != locator["original_header"]:
        raise ValueError("header mismatch")
    if rows[row - 1][col - 1] != locator["original_value"]:
        raise ValueError("source cell mismatch")
    return True


def register_cells(registry, evidence_id, metadata, row_ordinal, headers, row):
    registry.db.execute(
        "CREATE TABLE IF NOT EXISTS structured_cells (evidence_id TEXT, column_ordinal INTEGER, locator_json TEXT, PRIMARY KEY(evidence_id,column_ordinal))"
    )
    import json

    for i, (header, value) in enumerate(zip(headers, row, strict=True), 1):
        locator = {
            **metadata,
            "evidence_id": evidence_id,
            "row_ordinal": row_ordinal,
            "column_ordinal": i,
            "original_header": header,
            "original_value": value,
            "unit_source": "original_header_or_cell; no inferred unit",
            "data_dictionary": None,
        }
        existing = registry.db.execute(
            "SELECT locator_json FROM structured_cells WHERE evidence_id=? AND column_ordinal=?",
            (evidence_id, i),
        ).fetchone()
        encoded = json.dumps(locator, sort_keys=True)
        if existing and existing[0] != encoded:
            raise ValueError("cell provenance identity conflict")
        registry.db.execute(
            "INSERT OR IGNORE INTO structured_cells VALUES (?,?,?)", (evidence_id, i, encoded)
        )
    registry.db.commit()
