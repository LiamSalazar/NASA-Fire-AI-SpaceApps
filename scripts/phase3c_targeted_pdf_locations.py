"""Attach verified physical PDF geometry to existing opaque evidence identities."""

import json
import sys
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nasa_fire_ai.evidence import EvidenceRegistry


def main():
    report = json.loads((ROOT / "artifacts/phase3c_targeted_flex_corrections_v3.json").read_text())
    registry = EvidenceRegistry(ROOT / "data/index/evidence.sqlite")
    verified = []
    with pymupdf.open(ROOT / "data/raw/ntrs-20150023456.pdf") as pdf:
        for correction in report["corrections"]:
            source = correction["pdf"]
            column = correction["column_ordinal"] - 1
            page = pdf[source["physical_pdf_page"] - 1]
            box = source["cell_boxes"][column]
            words = [
                w[4]
                for w in page.get_text("words")
                if w[0] >= box[0] - 0.01
                and w[1] >= box[1] - 0.01
                and w[2] <= box[2] + 0.01
                and w[3] <= box[3] + 0.01
            ]
            assert words == [source["values"][column]]
            location = {
                "physical_pdf_page": source["physical_pdf_page"],
                "table": "IX",
                "table_boundary": source["table_boundary"],
                "row_identifier": source["values"][0],
                "engineering_identifier": source["values"][1],
                "original_headers": {
                    "9": "CO2; initial ambient composition, mole fraction",
                    "13": "Burning rate, mm2/s",
                },
                "cell_boxes": source["cell_boxes"],
                "original_cell_text": source["values"],
                "checksum": source["pdf_checksum"],
                "raw_file": "data/raw/ntrs-20150023456.pdf",
                "verification": "original page words and table columns aligned with row identifier",
            }
            registry.add_evidence_location(source["evidence_id"], location)
            verified.append(
                {
                    "record_id": correction["record_id"],
                    "evidence_id": source["evidence_id"],
                    "column_ordinal": column + 1,
                    "physical_pdf_page": source["physical_pdf_page"],
                    "round_trip": True,
                }
            )
    out = ROOT / "artifacts/phase3c_targeted_pdf_provenance_v2.json"
    assert not out.exists()
    out.write_text(
        json.dumps(
            {"checks": verified, "numerator": len(verified), "denominator": len(verified)}, indent=2
        )
    )
    print({"verified_pdf_cells": len(verified)})


if __name__ == "__main__":
    main()
