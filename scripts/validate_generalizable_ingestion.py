"""Rebuild isolated Phase-1 packages and source-grounded developer acceptance checks."""

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

from pyshacl import validate
from rdflib import Graph, Literal

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.query.native import NS, SemanticGraph
from nasa_fire_ai.services.curation import CurationService, project_package


def file_hash(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def write(path, value):
    with path.open("x") as f:
        json.dump(value, f, indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    registry = EvidenceRegistry(args.run / "workspace/data/index/evidence.sqlite")
    service = CurationService(args.run / "workspace", registry)
    reports = []
    for baseline in sorted(args.run.glob("*_baseline.json")):
        initial = json.loads(baseline.read_text())
        package_id = initial["package"]["id"]
        current = service.prepare_scientific(package_id, Settings(root=service.root))
        # This validator rebuilds deterministic candidates. Live receipts stay immutable.
        package = current["package"]
        extraction = package["scientific_extraction"]
        replay = service.prepare_scientific(package_id, Settings(root=service.root))
        write(args.output / (baseline.stem.replace("_baseline", "") + "_final.json"), current)
        (args.output / (baseline.stem + ".zip")).write_bytes(service.export_package(package_id))
        store = SemanticGraph(service.property_registry(package))
        project_package(store, package)
        for node in list(store.graph.subjects(NS.canonical, None)):
            store.graph.set((node, NS.canonical, Literal(False)))
        for node in list(store.graph.subjects(NS.evidenceRef, None)):
            store.graph.set((node, NS.reviewState, Literal("STAGED_CANDIDATE")))
        conforms, _, result = validate(
            store.graph, shacl_graph=Graph().parse(service.root / "ontology/semantic_shapes.ttl")
        )
        store.graph.serialize(args.output / (baseline.stem + ".ttl"), format="turtle")
        (args.output / (baseline.stem + "_shacl.txt")).write_text(str(result))
        attributes = extraction["table_quantity_proposals"]
        source_spans = [s for r in extraction["records"] for s in r["support_spans"]]
        evidence = {e["evidence_id"]: e for e in package["evidence"]}
        locations = sum(
            evidence[s["evidence_id"]]["text"][s["start"] : s["end"]] == s["quote"]
            and evidence[s["evidence_id"]]["checksum"] == s["checksum"]
            for s in source_spans
        )
        reports.append(
            {
                "source": baseline.stem.replace("_baseline", ""),
                "package_id": package_id,
                "baseline_entities": len(initial["package"]["entities"]),
                "final_entities": len(package["entities"]),
                "baseline_values": len(initial["package"]["values"]),
                "final_native_values": len(package["values"]),
                "typed_table_attributes": len(attributes),
                "source_locations": {"correct": locations, "denominator": len(source_spans)},
                "original_integrity_errors": service.validate_originals(package),
                "idempotent": current["digest"] == replay["digest"],
                "native_shacl": bool(conforms),
                "coverage": extraction["document"]["coverage"],
                "proposals": dict(
                    Counter(r["kind"] + ":" + r["status"] for r in extraction["records"])
                ),
                "review_requirements": len(extraction["review_requirements"]),
                "detected_table_records": len(extraction["structured_table_records"]),
                "processing": current["processing"],
                "ready_for_scientific_approval": service.validate(package)["ready"],
            }
        )
    write(
        args.output / "validation.json",
        {
            "reports": reports,
            "published_packages": registry.db.execute(
                "SELECT count(*) FROM research_active"
            ).fetchone()[0],
            "approval_receipts": registry.db.execute(
                "SELECT count(*) FROM research_approvals"
            ).fetchone()[0],
            "sqlite_integrity": registry.db.execute("PRAGMA integrity_check").fetchone()[0],
            "foreign_keys": [list(r) for r in registry.db.execute("PRAGMA foreign_key_check")],
            "labels": "Developer source checks, not independent scientific gold",
        },
    )
    registry.db.close()
    print(
        json.dumps(
            {
                "sources": len(reports),
                "source_integrity": all(not r["original_integrity_errors"] for r in reports),
                "shacl": all(r["native_shacl"] for r in reports),
                "idempotence": all(r["idempotent"] for r in reports),
            }
        )
    )


if __name__ == "__main__":
    main()
