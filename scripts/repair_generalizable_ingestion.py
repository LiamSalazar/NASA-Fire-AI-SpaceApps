"""Offline Phase-1 corrective receipts over archived sources; never contacts a model.

Reads historical registry snapshots in read-only mode. All preparation, exports,
SHACL and checkpoints are written to a new isolated destination.
"""

import argparse
import json
import shutil
import sqlite3
import sys
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from pyshacl import validate
from rdflib import Graph, Literal

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.document_extraction import (
    ExtractionBudget,
    extraction_semantic,
    validate_output,
)
from nasa_fire_ai.ingestion.document_structure import structure
from nasa_fire_ai.query.native import NS, SemanticGraph
from nasa_fire_ai.services.curation import CurationService, project_package

HISTORY = ROOT / "artifacts/phase1_generalizable_ingestion/v1"


def write(path, value):
    with path.open("x") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False)


def historical_failures(service, package):
    path = HISTORY / "holdout_first_pass/workspace/data/index/evidence.sqlite"
    receipt = []
    with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as db:
        for key, raw in db.execute(
            "SELECT cache_key,payload_json FROM phase3_cache WHERE cache_kind='scientific_document_failure' ORDER BY cache_key"
        ):
            payload = json.loads(raw)
            checked = validate_output(
                payload.get(
                    "output",
                    {
                        k: []
                        for k in ("entities", "statements", "relations", "quantities", "concepts")
                    },
                ),
                package,
                structure(package, service.root),
                extraction_semantic(service, package),
            )
            receipt.append(
                {
                    "cache_key": key,
                    "historical_payload": payload,
                    "raw_provider_response_available": "raw_response" in payload,
                    "independent_validation": checked["records"],
                    "counts": dict(
                        Counter(r["kind"] + ":" + r["status"] for r in checked["records"])
                    ),
                }
            )
    return receipt


def protocol_adapter():
    """Empty controlled responses measure actual requests and cache behavior only."""
    client = Mock()

    def respond(**kwargs):
        request = json.loads(kwargs["messages"][1]["content"])
        response = {k: [] for k in request["schema"]["properties"]}
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=json.dumps(response)), finish_reason="stop"
                )
            ],
            usage=None,
        )

    client.client.with_options.return_value.chat.completions.create.side_effect = respond
    return client


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args()
    out = args.directory.resolve()
    out.mkdir(parents=True, exist_ok=False)
    workspace = out / "workspace"
    for name in ("domain", "ontology", "data/canonical"):
        shutil.copytree(ROOT / name, workspace / name)
    registry = EvidenceRegistry(workspace / "data/index/evidence.sqlite")
    service = CurationService(workspace, registry)
    settings = Settings(root=workspace, nvidia_api_key=None)
    reports = []
    for source, run in [
        ("PSI-98", "development_run1"),
        ("20150008961", "development_run1"),
        ("20260003546", "development_run1"),
        ("20250010653", "holdout_first_pass"),
    ]:
        baseline = json.loads((HISTORY / run / (source + "_baseline.json")).read_text())
        p = baseline["package"]
        for original in p["inputs"]:
            destination = workspace / original["stored_input"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(HISTORY / run / "workspace" / original["stored_input"], destination)
        service.save(p, p["creator"])
        prepared = service.prepare_scientific(p["id"], settings)
        replay = service.prepare_scientific(p["id"], settings)
        write(out / (source + "_prepared.json"), prepared)
        package = prepared["package"]
        store = SemanticGraph(service.property_registry(package))
        project_package(store, package)
        for node in list(store.graph.subjects(NS.canonical, None)):
            store.graph.set((node, NS.canonical, Literal(False)))
        for node in list(store.graph.subjects(NS.evidenceRef, None)):
            store.graph.set((node, NS.reviewState, Literal("STAGED_CANDIDATE")))
        conforms, _, shacl = validate(
            store.graph, shacl_graph=Graph().parse(workspace / "ontology/semantic_shapes.ttl")
        )
        store.graph.serialize(out / (source + ".ttl"), format="turtle")
        (out / (source + "_shacl.txt")).write_text(str(shacl))
        (out / (source + "_package.zip")).write_bytes(service.export_package(p["id"]))
        evidence = {e["evidence_id"]: e for e in package["evidence"]}
        extraction = package["scientific_extraction"]
        spans = [s for r in extraction["records"] for s in r["support_spans"]]
        reports.append(
            {
                "source": source,
                "split": "DEVELOPMENT_REGRESSION",
                "package_id": p["id"],
                "original_integrity_errors": service.validate_originals(package),
                "idempotent": prepared["digest"] == replay["digest"],
                "native_shacl": bool(conforms),
                "new_live_model_calls": 0,
                "source_locations": {
                    "denominator": len(spans),
                    "correct": sum(
                        evidence[s["evidence_id"]]["text"][s["start"] : s["end"]] == s["quote"]
                        and evidence[s["evidence_id"]]["checksum"] == s["checksum"]
                        for s in spans
                    ),
                },
                "table_row_roles": extraction["table_row_role_proposals"],
                "table_quantities": len(extraction["table_quantity_proposals"]),
                "run_candidate_labels": [
                    e["label"] for e in package["entities"] if e["class_id"] == "ExperimentalRun"
                ],
                "scientific_proposals": dict(
                    Counter(r["kind"] + ":" + r["status"] for r in extraction["records"])
                ),
                "scientific_validation": service.validate(package),
                "coverage": extraction["document"]["coverage"],
            }
        )
        if source == "20250010653":
            write(out / "historical_failure_replay.json", historical_failures(service, package))
            client = protocol_adapter()
            # Bounded offline preparations exercise complete staged cache/resume.
            for _ in range(4):
                controlled = service.prepare_scientific(
                    p["id"],
                    settings,
                    model_enabled=True,
                    budget=ExtractionBudget(
                        max_model_calls=16, max_total_tokens=200000, timeout_seconds=900
                    ),
                    client=client,
                )
                if controlled["processing"]["status"] == "COMPLETE":
                    break
            replay = service.prepare_scientific(
                p["id"],
                settings,
                model_enabled=True,
                budget=ExtractionBudget(
                    max_model_calls=0, max_total_tokens=200000, timeout_seconds=900
                ),
                client=client,
            )
            calls = client.client.with_options.return_value.chat.completions.create.call_args_list
            requests = [json.loads(c.kwargs["messages"][1]["content"]) for c in calls]
            write(
                out / "controlled_protocol.json",
                {
                    "label": "EMPTY CONTROLLED ADAPTER: protocol, budgeting and cache checks; no recovered model science",
                    "live_calls": 0,
                    "controlled_calls": len(calls),
                    "final_processing": controlled["processing"],
                    "zero_call_replay": replay["processing"],
                    "idempotent": controlled["digest"] == replay["digest"],
                    "requests": requests,
                    "max_request_bytes": max(
                        len(c.kwargs["messages"][1]["content"].encode()) for c in calls
                    ),
                },
            )
    write(
        out / "validation.json",
        {
            "reports": reports,
            "PHASE1_COMPLETE": False,
            "live_scientific_acceptance": "NOT_RUN_IN_THIS_OFFLINE_EXECUTION",
            "published_packages": registry.db.execute(
                "SELECT count(*) FROM research_active"
            ).fetchone()[0],
            "approval_receipts": registry.db.execute(
                "SELECT count(*) FROM research_approvals"
            ).fetchone()[0],
            "sqlite_integrity": registry.db.execute("PRAGMA integrity_check").fetchone()[0],
            "foreign_keys": [list(r) for r in registry.db.execute("PRAGMA foreign_key_check")],
            "labels": "Developer mechanical source checks; not independent scientific gold or live model acceptance",
        },
    )
    registry.db.close()
    passed = all(
        not r["original_integrity_errors"]
        and r["idempotent"]
        and r["native_shacl"]
        and r["source_locations"]["correct"] == r["source_locations"]["denominator"]
        for r in reports
    )
    print(
        json.dumps(
            {
                "directory": str(out),
                "sources": len(reports),
                "offline_checks_passed": passed,
                "live_calls": 0,
            }
        )
    )
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
