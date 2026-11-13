"""Offline replay of saved Phase 1 packages through the current numeric handling.

Inputs are exposed development/regression receipts only: saved original source
text, saved document structure and saved raw Nemotron proposals. The replay makes
no model calls, needs no API key, writes only to a new output directory and never
modifies any existing receipt. It measures numeric syntax handling, not
scientific correctness: a retained proposal still requires scientific review.

Run once on the code being compared and once on the candidate code, then diff:

    uv run python scripts/phase1_numeric_replay.py --output artifacts/.../before
    uv run python scripts/phase1_numeric_replay.py --output artifacts/.../after
"""

import argparse
import copy
import gzip
import json
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

RECEIPTS = "artifacts/phase1_generalizable_ingestion/v4"
# Saved prepared packages, relative to RECEIPTS. Application receipts carry the
# final document structure; the numbered ones carry raw quantity proposals.
PACKAGES = [
    "luci_application_final/prepared.json.gz",
    "independent_ptfe_application/prepared.json.gz",
    "independent_ptfe/prepared_1.json.gz",
    "independent_regulator_application/prepared.json.gz",
    "independent_regulator/prepared_1.json.gz",
    "independent_textiles_application/prepared.json.gz",
    "independent_textiles/prepared_1.json.gz",
    "independent_ignition_application/prepared.json.gz",
    "independent_ignition/prepared_1.json.gz",
    "independent_ignition/prepared_2.json.gz",
]


def load(path):
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def inventory(coverage):
    return [
        {"expression": q["expression"], "unit": q["unit"], "page": unit["page"]}
        for unit in coverage["source_units"]
        for q in unit["quantity_inventory"]
    ]


def replay(name, service):
    from nasa_fire_ai.ingestion.document_extraction import (
        extraction_semantic,
        validate_output,
    )
    from nasa_fire_ai.ingestion.pdf_quantities import pdf_table_quantities
    from nasa_fire_ai.ingestion.scientific_coverage import coverage

    # A name is relative to the v4 receipts unless it is a repository path.
    prepared = load(ROOT / name if (ROOT / name).exists() else ROOT / RECEIPTS / name)
    package = prepared["package"]
    extraction = package["scientific_extraction"]
    document = extraction["document"]
    raw = extraction["raw_proposals"]
    # Quantities depend on validated entity endpoints only; other kinds are
    # replayed empty so the comparison isolates quantity handling.
    output = {
        "entities": copy.deepcopy(raw["entities"]),
        "quantities": copy.deepcopy(raw["quantities"]),
        "statements": [],
        "relations": [],
        "concepts": [],
    }
    records = validate_output(output, package, document, extraction_semantic(service, package))[
        "records"
    ]
    quantities = [r for r in records if r["kind"] == "quantities"]
    cells = pdf_table_quantities(package, document)
    found = inventory(coverage(package, document, {"records": []}, [], []))
    return {
        "package": name,
        "source_sha256": [i["sha256"] for i in package["inputs"]],
        "evidence_pages": len(package["evidence"]),
        "raw_quantity_proposals": len(raw["quantities"]),
        "quantity_status": dict(Counter(r["status"] for r in quantities)),
        "quantity_reasons": dict(Counter(x for r in quantities for x in r["reasons"])),
        "quantity_records": [
            {
                "expression": r["proposal"]["expression"],
                "unit": r["proposal"]["unit"],
                "label": r["proposal"]["label"],
                "status": r["status"],
                "reasons": r["reasons"],
                "numeric_form": (r.get("numeric_expression") or {}).get("form"),
                "expression_normalization": r.get("expression_normalization"),
            }
            for r in quantities
        ],
        "pdf_table_cells": [
            {
                "expression": c["proposal"]["expression"],
                "unit": c["proposal"]["unit"],
                "page": c["support_spans"][0]["page"],
            }
            for c in cells
        ],
        "source_quantity_inventory": found,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--packages", nargs="*", default=PACKAGES)
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.mkdir(parents=True, exist_ok=False)  # exclusive: never overwrite receipts

    from nasa_fire_ai.evidence import EvidenceRegistry
    from nasa_fire_ai.services.curation import CurationService

    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=False
    ).stdout.strip()
    dirty = subprocess.run(
        ["git", "status", "--porcelain", "--", "src"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for name in ("domain", "ontology", "data/canonical"):
            shutil.copytree(ROOT / name, tmp / name)
        registry = EvidenceRegistry(tmp / "data/index/evidence.sqlite")
        try:
            service = CurationService(tmp, registry)
            results = [replay(name, service) for name in args.packages]
        finally:
            registry.db.close()
    receipt = {
        "kind": "PHASE1_NUMERIC_OFFLINE_REPLAY",
        "git_head": head,
        "uncommitted_src_changes": bool(dirty),
        "model_calls": 0,
        "inputs": "Exposed development/regression receipts; not an independent evaluation",
        "scientific_acceptance": "NOT_ESTABLISHED_BY_SYNTAX_REPLAY",
        "packages": results,
    }
    (output / "replay.json").write_text(
        json.dumps(receipt, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    for result in results:
        print(
            result["package"],
            "quantities",
            result["quantity_status"],
            "pdf_cells",
            len(result["pdf_table_cells"]),
            "inventory",
            len(result["source_quantity_inventory"]),
        )


if __name__ == "__main__":
    main()
