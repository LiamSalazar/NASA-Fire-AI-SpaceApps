#!/usr/bin/env python3
"""Import verified upstream NASA acquisition artifacts and profile CSV tables."""

import csv
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
UP = Path(sys.argv[1]).resolve()
OUT = ROOT / "data/raw/upstream_nasa_space_apps"
EDA = ROOT / "data/eda"
EDA.mkdir(parents=True, exist_ok=True)
selected = {
    "PSI-26_BASS",
    "PSI-68_FLEX-2",
    "PSI-69_FLEX",
    "PSI-99_SAFFIRE-II",
    "PSI-100_SAFFIRE-III",
    "PSI-101_SAME-R",
    "PSI-102_SAME",
    "PSI-107_SPICE",
}
imports = []
profiles = []
for table in sorted((UP / "data/psi").glob("*/Experimental table/*.csv")):
    family = table.parents[1].name
    with table.open(encoding="utf-8-sig", errors="replace", newline="") as f:
        rows = list(csv.DictReader(f))
        columns = list(rows[0]) if rows else []
    missing = {c: sum(not (r.get(c) or "").strip() for r in rows) for c in columns}
    profiles.append(
        {
            "investigation_folder": family,
            "table": str(table.relative_to(UP)),
            "rows": len(rows),
            "columns": columns,
            "missingness": missing,
            "units": [c for c in columns if "(" in c or ";" in c],
            "unique_counts": {c: len({r.get(c, "") for r in rows}) for c in columns},
        }
    )
    if family in selected:
        target = OUT / table.relative_to(UP / "data")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(table, target)
        imports.append(
            {
                "upstream_path": str(table.relative_to(UP)),
                "our_path": str(target.relative_to(ROOT)),
                "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                "classification": "SAFE_RAW_SOURCE",
                "verification": "PSI accession/folder retained; upstream manifest available",
            }
        )
        manifest = table.parents[1] / "files_manifest.csv"
        if manifest.exists():
            mt = OUT / manifest.relative_to(UP / "data")
            mt.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(manifest, mt)
for rel, kind in [
    ("ntrs/catalog.csv", "SAFE_METADATA"),
    ("taskbook/taskbook_combustion.csv", "SAFE_METADATA"),
    ("psi/psi_index.csv", "SAFE_MANIFEST"),
]:
    src = UP / "data" / rel
    dst = OUT / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    imports.append(
        {
            "upstream_path": "data/" + rel,
            "our_path": str(dst.relative_to(ROOT)),
            "sha256": hashlib.sha256(dst.read_bytes()).hexdigest(),
            "classification": kind,
            "verification": "upstream catalog/metadata; not canonical scientific evidence",
        }
    )
(EDA / "experimental_tables.json").write_text(json.dumps(profiles, indent=2) + "\n")
(EDA / "upstream_imports.json").write_text(json.dumps(imports, indent=2) + "\n")
print(
    json.dumps(
        {
            "tables_profiled": len(profiles),
            "artifacts_imported": len(imports),
            "selected_tables": len(selected),
        },
        indent=2,
    )
)
