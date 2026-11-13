"""Reproducible Phase-1 application-service demonstrations; no scientific approval.

Evaluation sources are frozen in the campaign manifest. This driver has no
source-specific extraction rules and does not modify frozen historical evals.
"""

import argparse
import hashlib
import json
import shutil
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.document_extraction import ExtractionBudget
from nasa_fire_ai.services.curation import CurationService


def write(path, value):
    with path.open("x") as f:
        json.dump(value, f, indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("split", choices=["development", "holdout"])
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--model", action="store_true")
    args = parser.parse_args()
    out = args.directory.resolve()
    out.mkdir(parents=True, exist_ok=False)
    workspace = out / "workspace"
    for name in ("domain", "ontology", "data/canonical"):
        shutil.copytree(ROOT / name, workspace / name)
    registry = EvidenceRegistry(workspace / "data/index/evidence.sqlite")
    service = CurationService(workspace, registry)
    frozen = json.loads(
        (ROOT / "artifacts/phase1_generalizable_ingestion/v1/evaluation_freeze.json").read_text()
    )
    identifiers = (
        frozen["development"][1:] if args.split == "development" else [frozen["holdout"]["nasa_id"]]
    )
    settings = Settings(root=workspace)
    results = []
    if args.split == "development":
        raw = ROOT / "data/raw/psi/PSI-98_experimental_table.csv"
        baseline = service.submit(
            "PSI-98 Saffire experimental table",
            "Official NASA PSI structured combustion data",
            [(raw.name, raw.read_bytes())],
            "developer-evaluation",
        )
        package = baseline["package"]
        package["source_provenance"] = {
            "source_url": "https://psi.nasa.gov/geode-py/ws/studies/PSI-98/download",
            "publisher_origin": "NASA PSI",
            "sha256": hashlib.sha256(raw.read_bytes()).hexdigest(),
            "metadata": json.loads((ROOT / "data/raw/psi/PSI-98_metadata.json").read_text()),
            "eligibility": "PRESERVED_OFFICIAL_PSI_SOURCE",
            "scientific_review": "NONE",
        }
        baseline = service.save(package, "developer-evaluation")
        write(out / "PSI-98_baseline.json", baseline)
        prepared = service.prepare_scientific(package["id"], settings)
        write(out / "PSI-98_prepared.json", prepared)
        results.append(
            {"source": "PSI-98", "package_id": package["id"], "processing": prepared["processing"]}
        )
    for identifier in identifiers:
        baseline = service.submit_ntrs(identifier, "developer-evaluation")
        write(out / (identifier + "_baseline.json"), baseline)
        prepared = service.prepare_scientific(
            baseline["package"]["id"],
            settings,
            model_enabled=args.model,
            budget=ExtractionBudget(
                max_model_calls=4 if args.split == "development" else 6,
                max_total_tokens=100000,
                timeout_seconds=300,
            ),
        )
        write(out / (identifier + "_prepared.json"), prepared)
        replay = service.prepare_scientific(
            baseline["package"]["id"],
            settings,
            model_enabled=args.model,
            budget=ExtractionBudget(
                max_model_calls=0, max_total_tokens=100000, timeout_seconds=300
            ),
        )
        write(
            out / (identifier + "_replay.json"),
            {
                "digest": replay["digest"],
                "duplicate": replay.get("duplicate", False),
                "processing": replay["processing"],
            },
        )
        package = prepared["package"]
        write(out / (identifier + "_validation.json"), service.validate(package))
        (out / (identifier + "_package.zip")).write_bytes(service.export_package(package["id"]))
        extraction = package["scientific_extraction"]
        results.append(
            {
                "source": identifier,
                "package_id": package["id"],
                "digest": prepared["digest"],
                "source_integrity": service.validate_originals(package),
                "source_url": package["source_provenance"]["source_url"],
                "proposals": dict(
                    Counter((r["kind"] + ":" + r["status"]) for r in extraction["records"])
                ),
                "processing": prepared["processing"],
                "coverage": extraction["document"]["coverage"],
                "unchanged_replay_digest": prepared["digest"] == replay["digest"],
            }
        )
    write(
        out / "summary.json",
        {
            "split": args.split,
            "labels": "Developer verified source evidence; no independent scientific gold",
            "results": results,
            "approved_packages": registry.db.execute(
                "SELECT count(*) FROM research_active"
            ).fetchone()[0],
            "approval_receipts": registry.db.execute(
                "SELECT count(*) FROM research_approvals"
            ).fetchone()[0],
            "integrity": registry.db.execute("PRAGMA integrity_check").fetchone()[0],
        },
    )
    registry.db.close()
    print(
        json.dumps(
            {
                "directory": str(out),
                "sources": len(results),
                "new_model_calls": sum(r["processing"]["new_model_calls"] for r in results),
            }
        )
    )


if __name__ == "__main__":
    main()
