"""Check registered original cells, graph provenance, and structural shapes."""

import argparse
import json
import sys
from pathlib import Path

from pyshacl import validate
from rdflib import Graph

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.structured_provenance import round_trip
from nasa_fire_ai.query.native import NS


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Do not overwrite a validation receipt")
    snapshot = args.snapshot.resolve()
    manifest = json.loads((snapshot / "manifest.json").read_text())
    registry = EvidenceRegistry(snapshot / "evidence.sqlite", read_only=True, evidence_root=ROOT)
    graph = Graph().parse(snapshot / "graph.ttl")
    source_rows = {}
    for sid in ("psi-39", "psi-47", "psi-107"):
        ids = [
            row[0]
            for row in registry.db.execute(
                "SELECT p.evidence_id FROM passages p JOIN documents d USING(document_id) WHERE d.source_id=?",
                (sid,),
            )
        ]
        checked = sum(
            bool(round_trip(cell, ROOT))
            for eid in ids
            for cell in registry.resolve(eid).get("source_cells", [])
        )
        source_rows[sid] = {
            "original_table_rows_indexed": len(ids),
            "source_cells_round_trip_verified": checked,
            "rdf_factual_rows": 0,
        }
    refs = {str(value) for value in graph.objects(None, NS.evidenceRef)}
    missing = sorted(eid for eid in refs if registry.resolve(eid) is None)
    conforms, _, shacl_report = validate(
        graph, shacl_graph=Graph().parse(ROOT / "ontology/semantic_shapes.ttl")
    )
    result = {
        "snapshot_id": manifest["snapshot_id"],
        "holdout_sources": source_rows,
        "rdf_triples": len(graph),
        "rdf_evidence_references": len(refs),
        "missing_evidence_references": missing,
        "shacl_conforms": bool(conforms),
        "shacl_report": str(shacl_report)[:2000],
        "scope": "Structural and source-cell provenance only; scientific extraction and explanation are not validated",
    }
    registry.db.close()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "shacl_report"}, indent=2))
    if missing or not conforms:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
