"""Build a disposable isolated holdout index and execute generic retrieval probes."""

from __future__ import annotations

import json
import tempfile
import urllib.request
from pathlib import Path

import fitz

from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.generic import profile_table
from nasa_fire_ai.ingestion.psi import PSIClient, parse_experimental_table

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/phase3b_holdout_evidence.sqlite"


def main():
    result_path = ROOT / "artifacts/phase3b_holdout_query_probes.json"
    if OUT.exists() and result_path.exists():
        print(result_path.read_text())
        return
    registry = EvidenceRegistry(OUT)
    with tempfile.TemporaryDirectory(prefix="phase3b-holdout-") as raw:
        tmp = Path(raw)
        csv_text = PSIClient(tmp / "psi").get_experimental_table("PSI-142").value
        rows = parse_experimental_table(csv_text)
        profiles = profile_table(rows)
        registry.add_source(
            {
                "source_id": "PSI-142",
                "source_type": "NASA PSI table",
                "nasa_id": "PSI-142",
                "title": "PSI-142 holdout",
                "doi": None,
                "url": "https://psi.nasa.gov/physci/repo/data/studies/PSI-142",
                "retrieved_at": "phase3b",
                "filename": "temporary",
                "sha256": "temporary",
                "mime_type": "text/csv",
                "status": "isolated",
            }
        )
        registry.add_document("PSI-142-table", "PSI-142", "PSI-142 table")
        for i, row in enumerate(rows):
            text = " | ".join(f"{k}: {v}" for k, v in row.items())
            registry.add_passage(
                {
                    "evidence_id": f"holdout-psi142-row-{i}",
                    "document_id": "PSI-142-table",
                    "page": None,
                    "section": "table row",
                    "text": text,
                    "start_offset": 0,
                    "end_offset": len(text),
                    "raw_file": "temporary",
                    "checksum": "temporary",
                }
            )
        pdf = tmp / "ntrs.pdf"
        urllib.request.urlretrieve(
            "https://ntrs.nasa.gov/api/citations/20250001364/downloads/CIR%20USNCM%20poster%20abstract%2020250203.pdf",
            pdf,
        )
        text = "\n".join(page.get_text("text") for page in fitz.open(pdf))
        registry.add_source(
            {
                "source_id": "ntrs-20250001364",
                "source_type": "NASA NTRS document",
                "nasa_id": "20250001364",
                "title": "CIR holdout",
                "doi": None,
                "url": "https://ntrs.nasa.gov/citations/20250001364",
                "retrieved_at": "phase3b",
                "filename": "temporary",
                "sha256": "temporary",
                "mime_type": "application/pdf",
                "status": "isolated",
            }
        )
        registry.add_document("ntrs-20250001364", "ntrs-20250001364", "CIR holdout")
        registry.add_passage(
            {
                "evidence_id": "holdout-ntrs-20250001364-p1",
                "document_id": "ntrs-20250001364",
                "page": 1,
                "section": "document",
                "text": text,
                "start_offset": 0,
                "end_offset": len(text),
                "raw_file": "temporary",
                "checksum": "temporary",
            }
        )
    probes = {
        "table_document_lookup": "Reference Publication",
        "numeric_identifier": "Data ID",
        "documentary_lookup": "combustion",
        "unknown_property": "invented-property-zeta",
    }
    results = {
        name: [x["evidence_id"] for x in registry.search(query)] for name, query in probes.items()
    }
    payload = {
        "index": str(OUT.relative_to(ROOT)),
        "sources": 2,
        "passages": 9,
        "table_rows": len(rows),
        "columns": len(profiles),
        "probes": probes,
        "results": results,
    }
    result_path.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
