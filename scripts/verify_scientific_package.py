"""Verify ordinary isolated application outputs, original retrieval and native SHACL."""

import argparse
import hashlib
import io
import json
import sys
from pathlib import Path
from zipfile import ZipFile

from pyshacl import validate
from rdflib import Graph, Literal

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.document_extraction import ExtractionBudget
from nasa_fire_ai.query.native import NS, SemanticGraph
from nasa_fire_ai.services.curation import CurationService, project_package


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--package-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--replay", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    registry = EvidenceRegistry(args.workspace / "data/index/evidence.sqlite")
    service = CurationService(args.workspace, registry)
    current = service.get(args.package_id)
    replays = []
    if args.replay:
        for _ in range(2):
            current = service.prepare_scientific(
                args.package_id,
                Settings(root=service.root),
                model_enabled=True,
                budget=ExtractionBudget(max_model_calls=0, recovery_only=True),
            )
            replays.append(
                {"digest": current["digest"], "calls": current["processing"]["new_model_calls"]}
            )
    package = current["package"]
    evidence = {e["evidence_id"]: e for e in package["evidence"]}
    extraction = package["scientific_extraction"]
    spans = [
        s
        for r in [*extraction["records"], *extraction.get("pdf_table_quantity_proposals", [])]
        for s in r["support_spans"]
    ]
    correct = sum(
        evidence[s["evidence_id"]]["text"][s["start"] : s["end"]] == s["quote"]
        and evidence[s["evidence_id"]]["checksum"] == s["checksum"]
        and evidence[s["evidence_id"]]["source_id"] == s["source_id"]
        for s in spans
    )
    data = service.export_package(args.package_id)
    (args.output / "package.zip").write_bytes(data)
    with ZipFile(io.BytesIO(data)) as archive:
        originals = [
            {
                "sha256": m["sha256"],
                "export_matches": hashlib.sha256(
                    archive.read(m["sha256"] + Path(m["name"]).suffix)
                ).hexdigest()
                == m["sha256"],
            }
            for m in package["inputs"]
        ]
    store = SemanticGraph(service.property_registry(package))
    project_package(store, package)
    for node in list(store.graph.subjects(NS.canonical, None)):
        store.graph.set((node, NS.canonical, Literal(False)))
    for node in list(store.graph.subjects(NS.evidenceRef, None)):
        store.graph.set((node, NS.reviewState, Literal("STAGED_CANDIDATE")))
    conforms, _, report = validate(
        store.graph, shacl_graph=Graph().parse(service.root / "ontology/semantic_shapes.ttl")
    )
    store.graph.serialize(args.output / "isolated.ttl", format="turtle")
    (args.output / "shacl.txt").write_text(str(report))
    (args.output / "prepared.json").write_text(json.dumps(current, ensure_ascii=False, indent=2))
    result = {
        "package_id": args.package_id,
        "digest": current["digest"],
        "source_spans": {"correct": correct, "denominator": len(spans)},
        "originals": originals,
        "integrity_errors": service.validate_originals(package),
        "replays": replays,
        "idempotent": replays[0]["digest"] == replays[1]["digest"] if replays else None,
        "native_id_duplicates": {
            kind: len(package[kind])
            - len({r.get("id") or json.dumps(r, sort_keys=True) for r in package[kind]})
            for kind in ("entities", "relations", "values", "statements")
        },
        "shacl_conforms": bool(conforms),
        "isolated_triples": len(store.graph),
        "scientific_validation": service.validate(package),
        "sqlite_integrity": registry.db.execute("PRAGMA integrity_check").fetchone()[0],
        "foreign_keys": [list(r) for r in registry.db.execute("PRAGMA foreign_key_check")],
        "approvals": registry.db.execute("SELECT count(*) FROM research_approvals").fetchone()[0],
        "publications": registry.db.execute("SELECT count(*) FROM research_active").fetchone()[0],
    }
    (args.output / "verification.json").write_text(json.dumps(result, indent=2, ensure_ascii=False))
    registry.db.close()
    print(json.dumps({k: v for k, v in result.items() if k != "scientific_validation"}))
    if (
        correct != len(spans)
        or not conforms
        or result["integrity_errors"]
        or not all(o["export_matches"] for o in originals)
        or (replays and not result["idempotent"])
        or any(result["native_id_duplicates"].values())
        or result["approvals"]
        or result["publications"]
    ):
        raise SystemExit("Application verification failed")


if __name__ == "__main__":
    main()
