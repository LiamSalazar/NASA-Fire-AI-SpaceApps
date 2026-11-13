#!/usr/bin/env python3
"""Generic header-alias ETL demonstration for verified upstream FLEX table."""

import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.phase1 import stable_id

p = (
    ROOT
    / "data/raw/upstream_nasa_space_apps/psi/PSI-69_FLEX/Experimental table/PSI-69_Experimental table_FLEX.csv"
)
digest = hashlib.sha256(p.read_bytes()).hexdigest()
reg = EvidenceRegistry(Settings().registry_path)
reg.add_source(
    {
        "source_id": "psi-69",
        "source_type": "PSI experimental table",
        "nasa_id": "PSI-69",
        "title": "Flame Extinguishment Experiment (FLEX)",
        "doi": "10.60555/mbq8-0451",
        "url": "https://psi.nasa.gov/physci/repo/data/studies/PSI-69",
        "retrieved_at": "phase1.5 upstream import",
        "filename": str(p.relative_to(ROOT)),
        "sha256": digest,
        "mime_type": "text/csv",
        "status": "fetched",
    }
)
reg.add_document("psi-69-experimental-table", "psi-69", "PSI-69 FLEX Experimental table")
aliases = {
    "Ambient pressure; mmHg": ("pressure", "mmHg"),
    "O initial ambient composition; mole fraction": ("initial_oxygen", "fraction"),
    "N initial ambient composition; mole fraction": ("initial_nitrogen", "fraction"),
    "CO initial ambient composition; mole fraction": ("initial_carbon_dioxide", "fraction"),
    "He initial ambient composition; mole fraction": ("initial_helium", "fraction"),
    "Droplet initial diameter; mm": ("initial_droplet_diameter", "mm"),
    "Visible flame extinction diameter; mm": ("visible_flame_extinction_diameter", "mm"),
    "Burning rate; mm": ("burning_rate", "mm"),
    "Burn time; s": ("burn_time", "s"),
}
records = []
with p.open(encoding="utf-8-sig", errors="replace", newline="") as f:
    for n, row in enumerate(csv.DictReader(f), 2):
        key = (row.get("FLEX Test #") or "").strip()
        fuel = (row.get("Fuel") or "").strip()
        if not key or not fuel:
            continue
        eid = stable_id("E", "psi-69", digest, "row", str(n))
        text = ",".join(row.values())
        reg.add_passage(
            {
                "evidence_id": eid,
                "document_id": "psi-69-experimental-table",
                "page": None,
                "section": "Experimental table",
                "text": text,
                "start_offset": n,
                "end_offset": n,
                "raw_file": str(p.relative_to(ROOT)),
                "checksum": digest,
            }
        )
        ev = [{"evidence_id": eid, "source_id": "psi-69", "section": "Experimental table"}]
        rid = f"psi-69-{key}"
        sample = rid + "-sample"
        records.append(
            {"type": "SampleRecord", "id": sample, "material": fuel, "evidence_refs": ev}
        )
        cids = []
        for header, (kind, unit) in aliases.items():
            value = (row.get(header) or "").strip()
            if not value:
                continue
            try:
                value = float(value)
            except ValueError:
                continue
            cid = f"{rid}-{kind}"
            cids.append(cid)
            records.append(
                {
                    "type": "ConditionRecord",
                    "id": cid,
                    "kind": kind,
                    "reported_value": value,
                    "reported_unit": unit,
                    "canonical_value": value if unit == "fraction" else None,
                    "canonical_unit": "fraction" if unit == "fraction" else None,
                    "evidence_refs": ev,
                }
            )
        records.append(
            {
                "type": "ExperimentalRunRecord",
                "id": rid,
                "investigation_id": "psi-69",
                "sample_id": sample,
                "condition_ids": cids,
                "evidence_refs": ev,
            }
        )
out = ROOT / "data/canonical/phase15_structured.json"
out.write_text(json.dumps(records, indent=2) + "\n")
print({"runs": sum(x["type"] == "ExperimentalRunRecord" for x in records), "records": len(records)})
