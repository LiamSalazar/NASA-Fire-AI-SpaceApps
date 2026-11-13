"""Fresh source-location, secret-exclusion and complete handoff manifest checks."""

import csv
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry

PREFIX = "phase3c_consolidation"
VERSION = "v3" if "--version-v3" in sys.argv else "v2" if "--version-v2" in sys.argv else "v1"


def save(name, value):
    with (ROOT / "artifacts" / f"{PREFIX}_{name}.json").open("x") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


def main():
    import pymupdf

    registry = EvidenceRegistry(Settings().registry_path, read_only=True)
    units = json.loads((ROOT / "artifacts/phase3c_real_context_source_units_v8.json").read_text())[
        "units"
    ]
    checked = []
    for unit in units.values():
        row = registry.resolve(unit["evidence_id"])
        raw = Path(row["raw_file"])
        if not raw.is_absolute():
            raw = ROOT / "data/raw" / raw
        checksum_valid = hashlib.sha256(raw.read_bytes()).hexdigest() == row["checksum"]
        if row.get("source_cells"):
            records = list(csv.reader(raw.read_text(encoding="utf-8-sig").splitlines()))
            support = all(
                records[cell["row_ordinal"] - 1][cell["column_ordinal"] - 1]
                == cell["original_value"]
                and records[0][cell["column_ordinal"] - 1] == cell["original_header"]
                for cell in row["source_cells"]
            )
            location_kind = row["offset_contract"]
        else:
            if raw.suffix.lower() == ".pdf":
                with pymupdf.open(raw) as document:
                    text = document[row["page"] - 1].get_text()
            else:
                text = raw.read_text()
            support = text[row["start_offset"] : row["end_offset"]] == unit["text"]
            location_kind = row["structured_location"].get("locator_status")
        checked.append(
            {
                "evidence_id": unit["evidence_id"],
                "checksum_valid": checksum_valid,
                "exact_raw_span": support,
                "location_kind": location_kind,
            }
        )
    acquisition = json.loads((ROOT / "artifacts" / f"{PREFIX}_acquisition_v2.json").read_text())
    pdf_checks = []
    with pymupdf.open(ROOT / acquisition["raw_file"]) as document:
        for eid in acquisition["evidence_ids"]:
            row = registry.resolve(eid)
            pdf_checks.append(
                {
                    "evidence_id": eid,
                    "physical_pdf_page": row["page"],
                    "locator_verified": row["page_location_verified"],
                    "exact_page_text": document[row["page"] - 1].get_text() == row["text"],
                }
            )
    # This schema does not declare foreign keys: anti-join checks are not optional.
    missing_refs = registry.db.execute(
        "SELECT count(*) FROM evidence_refs e LEFT JOIN sources s USING(source_id) WHERE s.source_id IS NULL"
    ).fetchone()[0]
    extra_fts = registry.db.execute(
        "SELECT count(*) FROM passages_fts f LEFT JOIN passages p USING(evidence_id) WHERE p.evidence_id IS NULL"
    ).fetchone()[0]
    gates = []
    for command in (
        ["uv", "run", "ruff", "format", "--check", "."],
        ["uv", "run", "ruff", "check", "."],
    ):
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
        gates.append(
            {
                "command": command,
                "exit_code": result.returncode,
                "output": result.stdout + result.stderr,
                "execution": "FRESH_LOCAL_EXECUTION",
            }
        )
    save(
        f"source_integrity_{VERSION}",
        {
            "source_units": checked,
            "new_pdf_pages": pdf_checks,
            "missing_evidence_sources": missing_refs,
            "extra_fts_rows": extra_fts,
            "final_ruff": gates,
            "all_source_spans_valid": all(
                x["checksum_valid"] and x["exact_raw_span"] for x in checked
            ),
            "all_new_pages_valid": all(
                x["locator_verified"] and x["exact_page_text"] for x in pdf_checks
            ),
            "independent_review": None,
        },
    )
    if not all(x["checksum_valid"] and x["exact_raw_span"] for x in checked):
        raise RuntimeError("Source span validation failed")
    if not all(x["locator_verified"] and x["exact_page_text"] for x in pdf_checks):
        raise RuntimeError("Physical page validation failed")
    if any(gate["exit_code"] for gate in gates) or missing_refs or extra_fts:
        raise RuntimeError("Integrity gate failed")
    paths = set()
    for parent, pattern in (
        ("artifacts", f"{PREFIX}*"),
        ("docs", "PHASE3C_CONSOLIDATION*"),
        ("scripts", "phase3c_consolidation*"),
    ):
        for path in (ROOT / parent).glob(pattern):
            paths.update([path] if path.is_file() else (p for p in path.rglob("*") if p.is_file()))
    changed = subprocess.check_output(
        ["git", "diff", "--name-only"], cwd=ROOT, text=True
    ).splitlines()
    paths.update(ROOT / path for path in changed)
    for relative in (
        "src/nasa_fire_ai/ingestion/autonomous.py",
        "src/nasa_fire_ai/services/scientific_synthesis.py",
        "src/nasa_fire_ai/llm/scientific_selection.py",
        "scripts/maintain_knowledge.py",
        "tests/test_scientific_synthesis.py",
        "tests/test_autonomous_maintenance.py",
        acquisition["raw_file"],
    ):
        paths.add(ROOT / relative)
    paths.update(p for p in (ROOT / "ops").rglob("*") if p.is_file())
    keys = [key for key in (Settings().nvidia_api_key, os.getenv("TYPESAFE_API_KEY")) if key]
    index = []
    for path in sorted(paths):
        raw = path.read_bytes()
        if any(key.encode() in raw for key in keys):
            raise RuntimeError("Secret exclusion failed")
        value = json.loads(raw) if path.suffix == ".json" else None
        index.append(
            {
                "path": str(path.relative_to(ROOT)),
                "bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "top_level_count": len(value) if isinstance(value, (dict, list)) else None,
            }
        )
    save(
        f"artifact_index_v{int(VERSION[1:]) + 1}",
        {
            "files": index,
            "files_count": len(index),
            "api_secret_exclusion": "PASS",
            "env_included": False,
            "generated_vector_files": "excluded; local rebuildable indexes",
            "index_self_hash": "excluded",
        },
    )
    print(
        f"Verified {len(checked)} exact raw source spans and {len(pdf_checks)} PDF pages; indexed {len(index)} files"
    )


if __name__ == "__main__":
    main()
