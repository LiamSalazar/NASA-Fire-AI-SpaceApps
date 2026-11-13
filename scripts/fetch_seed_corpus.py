#!/usr/bin/env python3
"""Fetch only official NASA endpoints; failures are manifest records, never substitutions."""

import hashlib
import json
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw"
RAW.mkdir(parents=True, exist_ok=True)
sources = [
    (
        "ntrs-20205007829",
        "NTRS",
        "20205007829",
        "Spacecraft Fire Safety Needs for Exploration",
        None,
        "https://ntrs.nasa.gov/api/citations/20205007829/downloads/Exploration%20Needs%20in%20Fire%20Safety_9-25-2020.pdf",
    ),
    (
        "ntrs-20150020937",
        "NTRS",
        "20150020937",
        "Flammability Configuration Analysis for Spacecraft Applications",
        None,
        "https://ntrs.nasa.gov/api/citations/20150020937/downloads/20150020937.pdf",
    ),
    (
        "psi-25",
        "PSI",
        "PSI-25",
        "BASS-II",
        "10.60555/4qc4-de67",
        "https://lsda.jsc.nasa.gov/Experiment/PSI-25",
    ),
    (
        "psi-98",
        "PSI",
        "PSI-98",
        "Saffire-I",
        "10.60555/0t15-1z43",
        "https://lsda.jsc.nasa.gov/Experiment/PSI-98",
    ),
    (
        "nasa-std-6001",
        "NASA Standard",
        "NASA-STD-6001",
        "NASA-STD-6001",
        None,
        "https://standards.nasa.gov/standard/nasa/nasa-std-6001",
    ),
]
manifest = []
for sid, typ, nid, title, doi, url in sources:
    row = {
        "source_id": sid,
        "source_type": typ,
        "nasa_identifier": nid,
        "title": title,
        "doi": doi,
        "canonical_url": url,
        "retrieval_timestamp": datetime.now(UTC).isoformat(),
        "filename": None,
        "sha256": None,
        "mime_type": None,
        "status": "failed",
    }
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "nasa-fire-ai-mvp/0.1"})
        data = urllib.request.urlopen(req, timeout=45).read()
        suffix = ".pdf" if data.startswith(b"%PDF") else ".html"
        fn = f"{sid}{suffix}"
        path = RAW / fn
        if not path.exists():
            path.write_bytes(data)
        row.update(
            filename=fn,
            sha256=hashlib.sha256(data).hexdigest(),
            mime_type="application/pdf" if suffix == ".pdf" else "text/html",
            status="fetched",
        )
    except OSError as e:
        row["status"] = "failed: " + str(e)[:180]
    manifest.append(row)
(RAW / "manifest.json").write_text(json.dumps(manifest, indent=2))
print(json.dumps(manifest, indent=2))
