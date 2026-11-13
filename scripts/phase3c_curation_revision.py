"""Meaningful real-source revision via scientific review APIs, without editing source data."""

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from phase3c_curation_pilot import write

from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.services.curation import CurationService, ReviewPolicy
from nasa_fire_ai.services.phase3 import Phase3AssistantService


def revise(workspace, directory):
    principal = "development-scientist"
    registry = EvidenceRegistry(workspace / "data/index/evidence.sqlite")
    service = CurationService(workspace, registry, ReviewPolicy(frozenset({principal}), True))
    pid = next(
        p["package_id"]
        for p in service.list_packages()
        if service.get(p["package_id"])["package"]["title"]
        == "Saffire-I isolated incorporation pilot"
    )
    previous = registry.db.execute(
        "SELECT digest FROM research_active WHERE package_id=?", (pid,)
    ).fetchone()[0]
    table = service.get(pid)["package"]["tables"][0]
    extension = {
        "property": {
            "property_id": "BurnDuration",
            "dimension": "time",
            "canonical_unit": "s",
            "aliases": ["burn duration", "burn time"],
            "context": "reported_quantity",
        },
        "definition": "Source-reported duration of the burn in seconds; no inference about flame spread or suppression effectiveness.",
        "why_existing_insufficient": "The current quantity registry lacks an approved duration property.",
        "domain": "ExperimentalRun",
        "range": "numeric",
        "evidence_ids": [table["evidence_ids"][0]],
        "impact": "Compatible addition; historical conditions and original documentary burn-time values preserved.",
        "validation_contract": "SemanticRegistry.validate",
    }
    service.propose_extension(pid, extension, principal)
    service.approve_extension(pid, "BurnDuration", principal)
    key = "column:" + table["id"] + ":Burn Time (s)"
    service.reopen_decision(
        pid,
        key,
        "Represent the explicitly reported burn duration through its newly reviewed quantity contract.",
        principal,
    )
    changed = service.clarification(
        pid,
        key,
        "BurnDuration",
        "The original PSI table reports 420 s for S1 and 70 s for S2.",
        principal,
    )
    receipt = service.approve_and_publish(pid, changed["digest"], principal)
    write(
        directory,
        "meaningful_revision",
        {"previous_active_digest": previous, "prepared": changed, "receipt": receipt},
    )
    os.environ["NATIVE_V2_QUERY_ENABLED"] = "true"
    os.environ["NEMOTRON_SCIENTIFIC_SELECTION_ENABLED"] = "false"
    assistant = Phase3AssistantService(
        root=workspace, settings=Settings(root=workspace, nvidia_api_key=None)
    )
    response = assistant.answer_query(
        "Which measurements were reported in Saffire-I isolated incorporation pilot?"
    )
    write(directory, "measurement_query_final", response.model_dump(mode="json"))
    (directory / "research_package.zip").write_bytes(service.export_package(pid))
    rollback = service.rollback(pid, principal)
    write(directory, "meaningful_rollback", rollback)
    write(
        directory,
        "measurements_after_rollback",
        assistant.answer_query(
            "Which measurements were reported in Saffire-I isolated incorporation pilot?"
        ).model_dump(mode="json"),
    )
    write(directory, "meaningful_reactivation", service.publish(pid, changed["digest"], principal))
    print(
        {
            "measurements": len(response.evidence_bundle.measurements),
            "digest": changed["digest"],
            "history_preserved": rollback["restored_digest"] == previous,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args()
    args.directory.mkdir(parents=True, exist_ok=True)
    revise(args.workspace, args.directory)
