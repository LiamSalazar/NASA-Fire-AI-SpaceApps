"""Bounded fresh clarification/correction evaluation against real-source development drafts."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from phase3c_curation_pilot import write

from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.llm.scientific_correction import generate_clarifications, interpret_correction
from nasa_fire_ai.services.curation import CurationService, ReviewPolicy


def run(directory, workspace):
    registry = EvidenceRegistry(workspace / "data/index/evidence.sqlite")
    principal = "development-scientist"
    curator = CurationService(workspace, registry, ReviewPolicy(frozenset({principal}), True))
    settings = Settings(root=workspace)
    original = next((ROOT / "data/raw/autonomous").glob("ntrs-20260003546-*.pdf"))
    saved = curator.submit(
        "Depressurization clarification evaluation",
        "Real-source advisory wording evaluation; no automatic scientific approval",
        [(original.name, original.read_bytes())],
        principal,
    )
    write(
        directory,
        "questions",
        generate_clarifications(curator, saved["package"]["id"], settings, model_enabled=True),
    )
    other = json.loads((directory.parent / "prose/prose_reviewed.json").read_text())["package"]
    tentative = next(
        s
        for s in other["statements"]
        if s["epistemic"] == "tentative_interpretation" and s.get("included")
    )
    instructions = [
        "Retain only as documentary evidence the tentative interpretation statement "
        + tentative["id"]
        + ". Exclude that scientific assertion; do not change any other statement.",
        "Replace the original source wording with 'Nomex extinguished in all four tests' and publish it as an observation.",
        "Fix the scientific scope of the conclusions; the right experimental group is unclear.",
    ]
    results = []
    for index, instruction in enumerate(instructions):
        result = interpret_correction(
            curator, other["id"], instruction, principal, settings, model_enabled=True
        )
        if index == 0 and "proposal" in result:
            changed = curator.apply_correction(result["proposal"], principal)
            result["applied_digest"] = changed["digest"]
            result["validation_after_application"] = curator.validate(changed["package"])
            result["publication"] = curator.approve_and_publish(
                other["id"], changed["digest"], principal
            )
            result["rollback"] = curator.rollback(other["id"], principal)
        results.append(result)
    write(directory, "corrections", results)
    print(
        json.dumps(
            {
                "outcomes": [r["receipt"].get("outcome", "FAILED_CALL") for r in results],
                "applied": sum("applied_digest" in r for r in results),
            }
        )
    )
    registry.db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    args = parser.parse_args()
    args.directory.mkdir(parents=True, exist_ok=True)
    run(args.directory, args.workspace)
