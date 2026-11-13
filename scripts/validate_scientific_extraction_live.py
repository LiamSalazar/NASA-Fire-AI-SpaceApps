"""Frozen, bounded Nemotron validation. Dry-run by default; requires renewed authorization.

LUCI is development/regression. The other investigation is a frozen final lineage.
No result can approve/publish science or tune the frozen production contract.
"""

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.document_extraction import ExtractionBudget
from nasa_fire_ai.services.curation import CurationService

RECEIPTS = ROOT / "artifacts/phase1_generalizable_ingestion/v2"
PLANS = {
    "smoke": {"max_calls": 1, "output_tokens": 1200, "total_tokens": 30000, "elapsed_seconds": 60},
    "luci": {
        "max_calls": 21,
        "output_tokens": 1800,
        "total_tokens": 400000,
        "elapsed_seconds": 900,
    },
    "holdout": {
        "max_calls": 15,
        "output_tokens": 1800,
        "total_tokens": 200000,
        "elapsed_seconds": 900,
    },
}


def write(path, value):
    with path.open("x") as f:
        json.dump(value, f, indent=2, ensure_ascii=False)


def verify_freeze():
    frozen = json.loads((RECEIPTS / "contract_freeze.json").read_text())
    for name, expected in frozen["files"].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
            raise ValueError("Frozen extraction contract changed: " + name)
    return frozen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=PLANS)
    parser.add_argument("--directory", type=Path)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument(
        "--authorization-ref", help="Reference to renewed explicit user authorization"
    )
    args = parser.parse_args()
    plan = PLANS[args.stage]
    verify_freeze()
    if not args.execute:
        print(
            json.dumps(
                {
                    "stage": args.stage,
                    "dry_run": True,
                    "live_calls": 0,
                    "limits": plan,
                    "call_timeout_seconds": 55,
                    "retries": 0,
                    "cost_usd": "UNKNOWN: account pricing and failed-call billing unavailable",
                },
                indent=2,
            )
        )
        return
    if not args.authorization_ref or not args.directory:
        parser.error(
            "--execute requires --authorization-ref and a new --directory; original budget exhausted"
        )
    settings = Settings()
    if not settings.nvidia_api_key:
        parser.error("Nemotron key unavailable; offline system remains usable")
    out = args.directory.resolve()
    out.mkdir(parents=True, exist_ok=False)
    workspace = out / "workspace"
    for name in ("domain", "ontology", "data/canonical"):
        shutil.copytree(ROOT / name, workspace / name)
    registry = EvidenceRegistry(workspace / "data/index/evidence.sqlite")
    service = CurationService(workspace, registry)
    if args.stage == "holdout":
        freeze = json.loads((RECEIPTS / "evaluation_freeze.json").read_text())
        submitted = service.submit_ntrs(freeze["nasa_id"], "authorized-live-validation")
    else:
        history = ROOT / "artifacts/phase1_generalizable_ingestion/v1/holdout_first_pass"
        package = json.loads((history / "20250010653_baseline.json").read_text())["package"]
        for source in package["inputs"]:
            target = workspace / source["stored_input"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(history / "workspace" / source["stored_input"], target)
        submitted = service.save(package, package["creator"])
    write(out / "submission.json", submitted)
    write(
        out / "authorization.json",
        {"reference": args.authorization_ref, "stage": args.stage, "limits": plan},
    )
    calls, tokens, elapsed, attempts = 0, 0, 0.0, []
    # Resume in the same registry, with a shared call/token/elapsed ceiling.
    for index in range(3):
        remaining_tokens = min(200000, plan["total_tokens"] - tokens)
        remaining_time = plan["elapsed_seconds"] - elapsed
        if calls >= plan["max_calls"] or remaining_tokens < 1000 or remaining_time <= 0:
            break
        result = service.prepare_scientific(
            submitted["package"]["id"],
            Settings(root=workspace),
            model_enabled=True,
            budget=ExtractionBudget(
                max_model_calls=min(16, plan["max_calls"] - calls),
                max_output_tokens=plan["output_tokens"],
                max_total_tokens=remaining_tokens,
                timeout_seconds=min(900, remaining_time),
                call_timeout_seconds=55,
                segment_chars=2500,
                retries=0,
            ),
        )
        write(out / f"preparation_{index + 1}.json", result)
        processing = result["processing"]
        calls += processing["new_model_calls"]
        tokens += processing["tokens_consumed_or_reserved"]
        elapsed += processing["duration_seconds"]
        attempts.append(processing)
        if processing["status"] == "COMPLETE" or processing["new_model_calls"] == 0:
            break
    write(
        out / "result.json",
        {
            "stage": args.stage,
            "new_live_calls": calls,
            "tokens_consumed_or_reserved": tokens,
            "elapsed_seconds": elapsed,
            "attempts": attempts,
            "source_integrity": service.validate_originals(
                service.get(submitted["package"]["id"])["package"]
            ),
            "PHASE1_COMPLETE": False,
            "scientific_acceptance": "SOURCE_ADJUDICATION_REQUIRED; protocol completion is insufficient",
            "holdout_policy": "Retain failures; never tune on final holdout responses",
            "published_packages": registry.db.execute(
                "SELECT count(*) FROM research_active"
            ).fetchone()[0],
        },
    )
    registry.db.close()
    print(
        json.dumps(
            {
                "directory": str(out),
                "new_live_calls": calls,
                "scientific_acceptance": "NOT_AUTOMATIC",
            }
        )
    )


if __name__ == "__main__":
    main()
