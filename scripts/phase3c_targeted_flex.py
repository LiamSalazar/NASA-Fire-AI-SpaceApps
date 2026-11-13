"""Corroborate degraded CSV headings against original NASA Table IX and dictionary."""

import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.structured_provenance import table_cells


def same_number(left, right):
    try:
        return float(left) == float(right)
    except ValueError:
        return left.strip() == right.strip() or (
            left.strip() in {"", "-", "–"} and right.strip() in {"", "-", "–"}
        )


def main():
    registry = EvidenceRegistry(ROOT / "data/index/evidence.sqlite")
    pdf = ROOT / "data/raw/ntrs-20150023456.pdf"
    checksum = hashlib.sha256(pdf.read_bytes()).hexdigest()
    dictionary = registry.resolve("E-461f3b21bbb33b68")
    assert "diameter squared versus time" in dictionary["text"]
    assert "CO2—ambient carbon dioxide" in dictionary["text"]
    csv_path = (
        ROOT
        / registry.db.execute(
            "SELECT raw_file FROM passages p JOIN documents d USING(document_id) WHERE d.source_id='psi-69' LIMIT 1"
        ).fetchone()[0]
    )
    headers, rows, csv_metadata = table_cells(csv_path, ROOT)
    extracted = {}
    document = "ntrs-20150023456-targeted-flex-table-v1"
    registry.add_document(document, "ntrs-20150023456", "FLEX Table IX exact row/cells")
    with pymupdf.open(pdf) as doc:
        for index in range(25, 34):
            page = doc[index]
            table = page.find_tables().tables[0]
            raw = table.extract()
            assert raw[1][8] == "CO2" and "mm2/s" in raw[0][12]
            columns = [cell.splitlines() for cell in raw[2]]
            count = len(columns[0])
            assert all(len(c) == count for c in columns)
            for i in range(count):
                row = [c[i] for c in columns]
                assert re.fullmatch(r"FLEX–\d+", row[0])
                # Verify every reconstructed cell aligns with the test anchor
                # in actual page coordinates, rather than zipping line counts alone.
                anchors = [w for w in page.get_text("words") if w[4] == row[0]]
                assert len(anchors) == 1
                anchor = anchors[0]
                boxes = []
                for col in range(15):
                    cell = table.rows[2].cells[col]
                    words = [
                        w
                        for w in page.get_text("words")
                        if cell[0] <= (w[0] + w[2]) / 2 <= cell[2] and abs(w[1] - anchor[1]) < 1.5
                    ]
                    if len(words) != 1 or words[0][4] != row[col]:
                        raise ValueError("row geometry does not corroborate cell reconstruction")
                    boxes.append(list(words[0][:4]))
                eid = f"E-targeted-flex-pdf-{row[0]}"
                text = json.dumps(
                    {
                        "NASA FLEX test": row[0],
                        "FLEX engineering identifier": row[1],
                        "CO2 mole fraction": row[8],
                        "Burning rate (mm2/s)": row[12],
                    }
                )
                registry.add_passage(
                    {
                        "evidence_id": eid,
                        "document_id": document,
                        "page": index + 1,
                        "section": "Table IX; original NASA test " + row[0],
                        "text": text,
                        "start_offset": 0,
                        "end_offset": len(text),
                        "raw_file": str(pdf.relative_to(ROOT)),
                        "checksum": checksum,
                    }
                )
                extracted.setdefault(row[1], []).append(
                    {
                        "values": row,
                        "physical_pdf_page": index + 1,
                        "cell_boxes": boxes,
                        "evidence_id": eid,
                        "pdf_checksum": checksum,
                        "table_boundary": list(table.bbox),
                    }
                )
    records = json.loads((ROOT / "data/canonical/records.json").read_text())
    targets = [
        r
        for r in records
        if r["type"] == "ConditionRecord"
        and r["kind"] in {"initial_carbon_dioxide", "burning_rate"}
    ]
    corrections, staged, comparisons = [], [], []
    for record in targets:
        eid = record["evidence_refs"][0]["evidence_id"]
        locator = registry.db.execute(
            "SELECT locator_json FROM structured_cells WHERE evidence_id=? AND column_ordinal=2",
            (eid,),
        ).fetchone()
        if not locator:
            staged.append({"record_id": record["id"], "reason": "missing exact CSV row locator"})
            continue
        identifier = json.loads(locator[0])["original_value"]
        csv_locator = json.loads(locator[0])
        csv_row = rows[csv_locator["row_ordinal"] - 2]
        options = extracted.get(identifier, [])
        numeric = [5, 6, 7, 8, 9, 10, 11, 12, 13]
        options = [
            option
            for option in options
            if csv_row[4] == option["values"][4]
            and all(same_number(csv_row[col], option["values"][col]) for col in numeric)
        ]
        official = options[0] if len(options) == 1 else None
        if not official or not csv_row:
            staged.append(
                {
                    "record_id": record["id"],
                    "reason": "engineering identifier absent in original PDF",
                }
            )
            continue
        numeric = [5, 6, 7, 8, 9, 10, 11, 12, 13]
        matches = {
            headers[col]: same_number(csv_row[col], official["values"][col]) for col in numeric
        }
        if csv_row[4] != official["values"][4] or not all(matches.values()):
            staged.append(
                {
                    "record_id": record["id"],
                    "reason": "source numeric/fuel conflict",
                    "checks": matches,
                }
            )
            continue
        column = 8 if record["kind"] == "initial_carbon_dioxide" else 12
        if float(official["values"][column]) != record["reported_value"]:
            staged.append(
                {
                    "record_id": record["id"],
                    "reason": "canonical value differs from corroborated PDF cell",
                }
            )
            continue
        correction = {
            "record_id": record["id"],
            "kind": record["kind"],
            "original_record": record,
            "original_csv_header": headers[column],
            "original_csv_unit": record.get("reported_unit"),
            "corrected_source_unit": "fraction" if column == 8 else "mm2/s",
            "scientific_role": "INITIAL_SOURCE_REPORTED_CO2_MOLE_FRACTION"
            if column == 8
            else "SOURCE_DERIVED_BURNING_RATE_CONSTANT",
            "method": "NASA dictionary linear fit of diameter squared versus time"
            if column == 12
            else "NASA dictionary/Table IX CO2 heading",
            "value": record["reported_value"],
            "csv_checksum": csv_metadata["checksum"],
            "engineering_identifier": identifier,
            "original_nasa_test": official["values"][0],
            "csv_test_label": csv_row[0],
            "dictionary_evidence_id": dictionary["evidence_id"],
            "pdf": official,
            "column_ordinal": column + 1,
            "validation": "EXACT_ENGINEERING_IDENTIFIER_FUEL_AND_ALL_NINE_NUMERIC_COLUMNS",
            "independent_scientist_review": False,
        }
        corrections.append(correction)
        comparisons.append({"record_id": record["id"], "matched_numeric_columns": matches})
    out = ROOT / "artifacts/phase3c_targeted_flex_corrections_v3.json"
    assert not out.exists()
    out.write_text(
        json.dumps(
            {
                "source_url": "https://ntrs.nasa.gov/citations/20150023456",
                "dictionary_physical_page": 25,
                "pdf_checksum": checksum,
                "original_csv_checksum": csv_metadata["checksum"],
                "corrections": corrections,
                "staged": staged,
                "corrected_counts": dict(Counter(c["kind"] for c in corrections)),
                "original_values_units_preserved": True,
                "csv_test_numbers_may_be_reindexed": True,
            },
            indent=2,
        )
    )
    print({"corrected": len(corrections), "remaining": len(staged)})


if __name__ == "__main__":
    main()
