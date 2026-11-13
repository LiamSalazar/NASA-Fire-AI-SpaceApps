"""Versioned reproducible knowledge audit; never rewrites original data or receipts."""

import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path

import yaml
from pyshacl import validate
from rdflib import RDF, Graph

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.knowledge import enrich_native
from nasa_fire_ai.ingestion.semantic import project_legacy
from nasa_fire_ai.query.native import NS
from nasa_fire_ai.query.ontology_navigation import RouteStep, navigate, ontology_inventory

ART = ROOT / "artifacts"


def write(name, payload):
    path = ART / f"phase3c_knowledge_{name}_v1.json"
    if path.exists():
        return
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def main():
    os.environ["ONTOLOGY_GRAPH_ENRICHMENT_ENABLED"] = "false"
    evidence = EvidenceRegistry(ROOT / "data/index/evidence.sqlite")
    records = json.loads((ROOT / "data/canonical/records.json").read_text())
    store = project_legacy(ROOT, evidence)
    schema = Graph().parse(ROOT / "ontology/fire_safety.ttl")
    inventory = ontology_inventory(schema)
    native_classes = sorted(store.registry.target_classes | store.registry.information_classes)
    inventory["native_classes_before"] = native_classes
    inventory["native_relations_before"] = sorted(store.registry.relations)
    original = Graph().parse(ROOT / "data/canonical/graph.ttl")
    declared = set(inventory["object_properties"] + inventory["datatype_properties"])
    inventory["undeclared_original_graph_predicates"] = sorted(
        {
            str(p)
            for p in original.predicates()
            if str(p).startswith("https://example.org/nasa-fire-safety#") and str(p) not in declared
        }
    )
    write("ontology", inventory)
    before = {
        "triples": len(store.graph),
        "relations": len(set(store.graph.subjects(RDF.type, NS.SemanticRelation))),
        "projection": store.projection_report,
    }
    language = yaml.safe_load((ROOT / "domain/query_language_v2.yaml").read_text())
    aliases = {
        key: value.get("aliases", [key])
        for key, value in language["entity_mentions"].items()
        if value.get("relation") == "hasMaterial"
    }
    enrichment = enrich_native(store, records, evidence, ROOT / "ontology/fire_safety.ttl", aliases)
    write("enrichment", enrichment)
    graph_file = ART / "phase3c_knowledge_enriched_graph_v1.ttl"
    if not graph_file.exists():
        store.graph.serialize(graph_file, format="turtle")
    source_rows = []
    for source in evidence.db.execute("SELECT * FROM sources ORDER BY source_id"):
        row = dict(source)
        docs = [
            r[0]
            for r in evidence.db.execute(
                "SELECT document_id FROM documents WHERE source_id=?", (row["source_id"],)
            )
        ]
        passages = [
            dict(r)
            for r in evidence.db.execute(
                "SELECT p.* FROM passages p JOIN documents d USING(document_id) WHERE d.source_id=?",
                (row["source_id"],),
            )
        ]
        canonical = [
            r
            for r in records
            if any(e["source_id"] == row["source_id"] for e in r.get("evidence_refs", []))
        ]
        refs = {p["evidence_id"] for p in passages}
        approved_relations = {
            str(s)
            for s in store.graph.subjects(RDF.type, NS.SemanticRelation)
            if refs.intersection(str(e) for e in store.graph.objects(s, NS.evidenceRef))
        }
        source_rows.append(
            {
                "source_id": row["source_id"],
                "nasa_id": row["nasa_id"],
                "title": row["title"],
                "url": row["url"],
                "status": row["status"],
                "documents": docs,
                "passages": len(passages),
                "canonical_records": len(canonical),
                "record_types": dict(Counter(r["type"] for r in canonical)),
                "projected_relations": len(approved_relations),
                "scientifically_structured": bool(canonical),
                "documentary_retrievable": bool(passages),
                "coverage_state": "STRUCTURED"
                if canonical
                else "PARSED"
                if passages
                else "ACQUIRED",
                "scientific_extraction_completeness": "UNMEASURED",
                "sha256": row["sha256"],
            }
        )
    write("source_inventory", source_rows)
    examples = []
    for start, route in [
        ("psi-98", ["hasRun", "usesSample", "madeOf"]),
        ("psi-98", ["hasRun", "hasCondition"]),
        ("saffire-iv-flow-off-observation", ["reportedBy"]),
    ]:
        result = navigate(store, start, [RouteStep(p) for p in route], evidence, budget=10000)
        examples.append({"start": start, "route": route, **result})
    write("paths", examples)
    shapes = Graph().parse(ROOT / "ontology/semantic_shapes.ttl")
    native_ok, _, native_report = validate(store.graph, shacl_graph=shapes)
    canonical_ok, _, canonical_report = validate(
        original, shacl_graph=Graph().parse(ROOT / "ontology/shapes.ttl")
    )
    integrity = {
        "sqlite": evidence.db.execute("PRAGMA integrity_check").fetchone()[0],
        "foreign_keys": [list(r) for r in evidence.db.execute("PRAGMA foreign_key_check")],
        "native_shacl": bool(native_ok),
        "canonical_shacl": bool(canonical_ok),
        "native_report": str(native_report),
        "canonical_report": str(canonical_report),
        "missing_fts": evidence.db.execute(
            "SELECT count(*) FROM passages WHERE evidence_id NOT IN (SELECT evidence_id FROM passages_fts)"
        ).fetchone()[0],
        "orphan_passages": evidence.db.execute(
            "SELECT count(*) FROM passages WHERE document_id NOT IN (SELECT document_id FROM documents)"
        ).fetchone()[0],
    }
    baseline = json.loads((ART / "phase3c_knowledge_baseline_v1.json").read_text())["digests"]
    immutable = {
        p: h
        for p, h in baseline.items()
        if p.startswith(("data/raw/", "data/canonical/", "evals/", "artifacts/"))
    }
    changed = [
        p
        for p, h in immutable.items()
        if not (ROOT / p).exists() or hashlib.sha256((ROOT / p).read_bytes()).hexdigest() != h
    ]
    integrity["immutable_files_checked"] = len(immutable)
    integrity["changed_immutable_files"] = changed
    write("integrity", integrity)
    write(
        "summary",
        {
            "sources": len(source_rows),
            "documents": evidence.db.execute("SELECT count(*) FROM documents").fetchone()[0],
            "passages": evidence.db.execute("SELECT count(*) FROM passages").fetchone()[0],
            "record_types": dict(Counter(r["type"] for r in records)),
            "sources_with_canonical_records": sum(
                r["scientifically_structured"] for r in source_rows
            ),
            "before": before,
            "after": {
                "triples": len(store.graph),
                "relations": len(set(store.graph.subjects(RDF.type, NS.SemanticRelation))),
            },
            "approved_new_domain_taxonomy": 0,
            "observed_measurements_added": 0,
        },
    )
    print(
        json.dumps(
            {"summary": str(ART / "phase3c_knowledge_summary_v1.json"), "integrity": integrity}
        )
    )


if __name__ == "__main__":
    main()
