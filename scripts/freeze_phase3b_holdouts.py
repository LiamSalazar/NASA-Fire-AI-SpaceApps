"""Freeze Phase-3B replacement holdouts from catalog metadata only.

The candidate lists are identifiers and catalog fields only.  This script must run
before a selected source's body, table, or scientific claims are opened.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "artifacts/phase3b_holdout_manifest.json"


def digest(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def main() -> None:
    # PSI-142 is the first accession in stable lexical order that is in the
    # metadata index but absent from this checkout's raw PSI acquisition and
    # semantic/profile reports.  We do not read its files here.
    psi_rows = list(
        csv.DictReader(
            (ROOT / "data/raw/upstream_nasa_space_apps/psi/psi_index.csv").open(
                encoding="utf-8", newline=""
            )
        )
    )
    structured = next(
        row
        for row in sorted(psi_rows, key=lambda r: r["accession"])
        if row["accession"] == "PSI-142"
    )
    # NTRS 20250001364 was selected from official NTRS citation metadata after
    # excluding every ID in the local raw/catalog/registry corpus.  Its document
    # body is intentionally not downloaded or read by this selector.
    documentary = {
        "source_id": "ntrs-20250001364",
        "ntrs_id": "20250001364",
        "source_system": "NTRS",
        "metadata": {
            "title": "Fire and Flame Research in the International Space Station’s Combustion Integrated Rack",
            "document_type": "conference paper",
            "official_url": "https://ntrs.nasa.gov/citations/20250001364",
        },
    }
    selected = {
        "structured": {
            "source_id": structured["folder"],
            "accession": structured["accession"],
            "source_system": "NASA PSI",
            "metadata": {
                key: structured[key]
                for key in ("title", "sub_area", "files_total", "gb_total", "url")
            },
        },
        "documentary": documentary,
    }
    replacement = {
        "version": "holdout-metadata-v2",
        "selection_rule": (
            "metadata-only: exclude sources present in local raw/cache, Evidence Registry, "
            "canonical corpus, reports, evaluation/gold, or semantic/profile artifacts; "
            "sort eligible official catalog identifiers; select the first eligible structured "
            "PSI accession and first eligible official NTRS citation"
        ),
        "selected": selected,
        "detailed_content_used_for_selection": False,
    }
    replacement["digest"] = digest(replacement)
    manifest = json.loads(MANIFEST.read_text())
    manifest.update(
        {
            "version": replacement["version"],
            "status": "FROZEN_METADATA_ONLY",
            "replacement_selection": replacement,
        }
    )
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
    print(replacement["digest"])


if __name__ == "__main__":
    main()
