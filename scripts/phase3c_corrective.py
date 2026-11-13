"""Resumable corrective evaluation; original Phase 3C artifacts remain immutable."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nasa_fire_ai.evaluation.phase3c import digest, freeze_json


def coverage():
    from pyshacl import validate

    from nasa_fire_ai.evidence import EvidenceRegistry
    from nasa_fire_ai.ingestion.semantic import project_legacy

    evidence = EvidenceRegistry(ROOT / "data/index/evidence.sqlite")
    store = project_legacy(ROOT, evidence)
    freeze_json(
        ROOT / "artifacts/phase3c_corrective_coverage_v2.json",
        {
            "version": "POST_CORRECTION-v1",
            "counts": store.projection_report,
            "staging_candidates": store.projection_staging,
            "native_shacl": bool(
                validate(store.graph, shacl_graph=str(ROOT / "ontology/semantic_shapes.ttl"))[0]
            ),
            "native_triples": len(store.graph),
            "limitations": [
                "Unmapped properties remain candidates; no new property identities invented",
                "Reported conditions are not promoted to observed measurements",
                "Unsupported mmHg conversion is staged rather than approximated",
            ],
        },
    )
    print(json.dumps(store.projection_report))


def baseline():
    if (ROOT / "artifacts/phase3c_corrective_baseline_v1.json").exists():
        print("Existing corrective baseline retained")
        return
    paths = [
        *sorted((ROOT / "data/raw").rglob("*")),
        *sorted((ROOT / "data/canonical").glob("*")),
        *sorted((ROOT / "artifacts").glob("phase3c_*.json*")),
        *sorted((ROOT / "evals").glob("phase3c_*.json")),
        ROOT / "domain/lexicon.yaml",
    ]
    freeze_json(
        ROOT / "artifacts/phase3c_corrective_baseline_v1.json",
        {
            "version": "phase3c-corrective-v1",
            "label": "PRE_CORRECTION",
            "digests": {str(p.relative_to(ROOT)): digest(p) for p in paths if p.is_file()},
        },
    )
    print("Baseline frozen; no corpus writes")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "stage",
        choices=[
            "baseline",
            "coverage",
            "freeze",
            "freeze-repair",
            "freeze-service",
            "freeze-resolution",
            "freeze-authority",
            "freeze-final",
            "freeze-final-repair",
        ],
    )
    args = parser.parse_args()
    if args.stage == "baseline":
        baseline()
    elif args.stage == "coverage":
        coverage()
    elif args.stage in {
        "freeze",
        "freeze-repair",
        "freeze-service",
        "freeze-resolution",
        "freeze-authority",
        "freeze-final",
        "freeze-final-repair",
    }:
        paths = [
            *sorted((ROOT / "src/nasa_fire_ai").rglob("*.py")),
            *sorted((ROOT / "domain").glob("*.yaml")),
            *sorted((ROOT / "ontology").glob("*.ttl")),
        ]
        freeze_json(
            ROOT
            / (
                "artifacts/phase3c_final_repair_native_freeze_v1.json"
                if args.stage == "freeze-final-repair"
                else "artifacts/phase3c_corrective_native_freeze_v6.json"
                if args.stage == "freeze-final"
                else "artifacts/phase3c_corrective_native_freeze_v5.json"
                if args.stage == "freeze-authority"
                else "artifacts/phase3c_corrective_native_freeze_v4.json"
                if args.stage == "freeze-resolution"
                else "artifacts/phase3c_corrective_native_freeze_v3.json"
                if args.stage == "freeze-service"
                else "artifacts/phase3c_corrective_native_freeze_v2.json"
                if args.stage == "freeze-repair"
                else "artifacts/phase3c_corrective_native_freeze_v1.json"
            ),
            {
                "version": "POST_CORRECTION-v1",
                "digests": {str(p.relative_to(ROOT)): digest(p) for p in paths},
            },
        )
        print("Corrected native architecture frozen")


if __name__ == "__main__":
    main()
