"""Reproducible same-corpus audit, literal predicate reconciliation and enrichment."""

import json
import os
import sys
from collections import Counter
from pathlib import Path

from pyshacl import validate
from rdflib import RDF, RDFS, Graph

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.semantic import project_legacy
from nasa_fire_ai.query.native import NS

ART = ROOT / "artifacts"


def write(name, data):
    p = ART / f"phase3c_enrichment_{name}_v1.json"
    if p.exists():
        raise FileExistsError(p)
    p.write_text(json.dumps(data, indent=2))


def main():
    evidence = EvidenceRegistry(ROOT / "data/index/evidence.sqlite")
    records = json.loads((ROOT / "data/canonical/records.json").read_text())
    os.environ["ONTOLOGY_GRAPH_ENRICHMENT_ENABLED"] = "true"
    os.environ["SOURCE_KNOWLEDGE_ENRICHMENT_ENABLED"] = "false"
    before = project_legacy(ROOT, evidence)
    os.environ["SOURCE_KNOWLEDGE_ENRICHMENT_ENABLED"] = "true"
    after = project_legacy(ROOT, evidence)
    enrichment = after.source_enrichment_report
    write("specimens", enrichment["specimens"])
    write("source_fields", enrichment["mapped"])
    original_staging = before.projection_staging
    mapped = {row["record_id"] for row in enrichment["mapped"]}
    inventory = []
    for row in original_staging:
        record = row["provenance"]
        kind = record["kind"]
        inventory.append(
            {
                "record_id": record["id"],
                "kind": kind,
                "original_record": record,
                "disposition": "EXECUTABLE_SOURCE_FIELD"
                if record["id"] in mapped
                else "REVIEW_REQUIRED",
                "role": next(
                    (
                        x["qualifiers"]["role"]
                        for x in enrichment["mapped"]
                        if x["record_id"] == record["id"]
                    ),
                    "AMBIGUOUS_RATE_UNIT"
                    if kind == "burning_rate"
                    else "AMBIGUOUS_CHEMICAL_IDENTITY"
                    if kind == "initial_carbon_dioxide"
                    else "UNRESOLVED",
                ),
                "observed_measurement_published": False,
            }
        )
    write("field_inventory", inventory)
    used = Graph().parse(ROOT / "data/canonical/graph.ttl")
    old = json.loads((ART / "phase3c_knowledge_ontology_v1.json").read_text())[
        "undeclared_original_graph_predicates"
    ]
    predicates = []
    for uri in old:
        rows = list(used.triples((None, __import__("rdflib").URIRef(uri), None)))
        predicates.append(
            {
                "predicate": uri,
                "usages": len(rows),
                "subject_types": sorted(
                    {str(t) for s, _, _ in rows for t in used.objects(s, RDF.type)}
                ),
                "object_kinds": dict(Counter(type(o).__name__ for _, _, o in rows)),
                "disposition": "REVIEW_REQUIRED_NO_DECLARATION"
                if uri.endswith("supportedBy")
                else "DECLARED_EXISTING_LITERAL_SEMANTICS",
                "domain_range": "NONE; no new entailment or authority",
                "constraint": "quarantine historical evidential association"
                if uri.endswith("supportedBy")
                else "literal datatype checks in enrichment_shapes.ttl",
                "authority_change": False,
            }
        )
    write("predicate_audit", predicates)
    source_inventory = []
    for row in evidence.db.execute("SELECT source_id,title,nasa_id,url FROM sources"):
        sid = row["source_id"]
        canonical = [
            r for r in records if any(e["source_id"] == sid for e in r.get("evidence_refs", []))
        ]
        source_inventory.append(
            {
                **dict(row),
                "passages": evidence.db.execute(
                    "SELECT count(*) FROM passages p JOIN documents d USING(document_id) WHERE d.source_id=?",
                    (sid,),
                ).fetchone()[0],
                "canonical_record_types": dict(Counter(r["type"] for r in canonical)),
                "new_executable_fields": sum(
                    any(e["source_id"] == sid for e in x["original"]["evidence_refs"])
                    for x in enrichment["mapped"]
                ),
                "new_material_identities": sum(
                    sid in after.sources(x["identity"]) for x in enrichment["additional_materials"]
                ),
                "scientific_extraction_completeness": "UNMEASURED",
            }
        )
    write("source_inventory", source_inventory)
    write(
        "summary",
        {
            "sources": len(source_inventory),
            "documents": evidence.db.execute("SELECT count(*) FROM documents").fetchone()[0],
            "passages": evidence.db.execute("SELECT count(*) FROM passages").fetchone()[0],
            "canonical_record_types": dict(Counter(r["type"] for r in records)),
            "before": {
                "entities": len(before.entities()),
                "relations": len(set(before.graph.subjects(RDF.type, NS.SemanticRelation))),
                "executable_conditions": before.projection_report["conditions"],
                "unmapped_fields": len(original_staging),
                "material_samples": 70,
            },
            "after": {
                "entities": len(after.entities()),
                "relations": len(set(after.graph.subjects(RDF.type, NS.SemanticRelation))),
                "executable_conditions": before.projection_report["conditions"]
                + len(enrichment["mapped"]),
                "unmapped_fields": len(original_staging) - len(mapped),
                "material_samples": sum(x["identity"] is not None for x in enrichment["specimens"]),
                "specimen_dispositions": dict(
                    Counter(x["disposition"] for x in enrichment["specimens"])
                ),
                "observed_measurements_added": 0,
                "additional_canonical_materials": sorted(
                    {x["identity"] for x in enrichment["additional_materials"]}
                ),
            },
            "mapped_by_kind": dict(Counter(x["original"]["kind"] for x in enrichment["mapped"])),
            "native_shacl": bool(
                validate(after.graph, shacl_graph=str(ROOT / "ontology/semantic_shapes.ttl"))[0]
            ),
            "literal_shacl": bool(
                validate(used, shacl_graph=str(ROOT / "ontology/enrichment_shapes.ttl"))[0]
            ),
            "new_domain_range_entailments": len(
                list(
                    Graph()
                    .parse(ROOT / "ontology/fire_safety.ttl")
                    .triples((None, RDFS.domain, None))
                )
            ),
        },
    )
    after.graph.serialize(ART / "phase3c_enrichment_graph_v1.ttl", format="turtle")
    print(
        json.dumps(
            {
                "mapped_fields": len(mapped),
                "additional_normalized_samples": len(enrichment["additional_materials"]),
            }
        )
    )


if __name__ == "__main__":
    main()
