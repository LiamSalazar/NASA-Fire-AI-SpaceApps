"""Validate actual graph values against immutable PSI cells and source-scoped routes."""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from pyshacl import validate
from rdflib import OWL, RDF, Graph, Namespace

from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.hackathon import make_store, verify_snapshot
from nasa_fire_ai.ingestion.structured_provenance import round_trip
from nasa_fire_ai.query.native import NS, identity, node
from nasa_fire_ai.query.ontology_navigation import RouteStep, navigate
from nasa_fire_ai.services.source_definitions import registered_quotation_fragments


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = verify_snapshot(args.snapshot, ROOT)
    store = make_store(ROOT)
    store.graph = Graph().parse(args.snapshot / "graph.ttl")
    store.registry.entities.update(store.entities())
    registry = EvidenceRegistry(
        args.snapshot / "evidence.sqlite", read_only=True, evidence_root=ROOT
    )
    refs = {str(e) for e in store.graph.objects(None, NS.evidenceRef)}
    missing = [e for e in refs if not registry.resolve(e)]
    cells = registry.db.execute(
        "SELECT v.value_id,c.locator_json FROM value_cells v JOIN structured_cells c ON v.evidence_id=c.evidence_id AND v.column_ordinal=c.column_ordinal"
    ).fetchall()
    values = Counter()
    verified = []
    json_sources, json_pointers = {}, 0
    for row in registry.db.execute(
        "SELECT p.raw_file,p.text,e.location_json FROM passages p JOIN evidence_locations e USING(evidence_id)"
    ):
        location = json.loads(row["location_json"])
        pointer = location.get("json_pointer")
        if not pointer:
            continue
        path = row["raw_file"]
        if path not in json_sources:
            json_sources[path] = json.loads((ROOT / path).read_text())
        original = json_sources[path]
        for part in pointer.strip("/").split("/"):
            part = part.replace("~1", "/").replace("~0", "~")
            original = original[int(part)] if isinstance(original, list) else original[part]
        text = original if isinstance(original, str) else json.dumps(original, ensure_ascii=False)
        if text != row["text"]:
            raise ValueError("Documentary/publication pointer disagrees with original JSON")
        json_pointers += 1
    # Read each source cell once: all value alternatives preserve the same raw expression.
    for cell in cells:
        locator = json.loads(cell["locator_json"])
        round_trip(locator, ROOT)
        payload = store.payload(cell["value_id"])
        if payload["qualifiers"]["original_value"] != locator["original_value"]:
            raise ValueError("Graph/source cell disagreement")
        values[payload["property_id"]] += 1
    instrument_attributes = []
    quotation_contexts = []
    for row in registry.db.execute("SELECT DISTINCT context_id FROM curated_quotation_parts"):
        context_id = row["context_id"]
        payload = store.payload(context_id)
        fragments = registered_quotation_fragments(
            payload["text"], store.evidence(context_id), registry, context_id=context_id
        )
        if not fragments:
            raise ValueError(f"Curated quotation no longer resolves: {context_id}")
        quotation_contexts.append({"context": context_id, "original_spans": fragments})
    term_links = []
    for value in store.entities():
        for definition in store.relations(value, "hasTermDefinition"):
            if "ScientificTermDefinition" not in store.classes(definition):
                raise ValueError("Term definition has an incompatible scientific type")
            payload = store.payload(value)
            if payload.get("property_id") not in store.payload(definition)["defined_properties"]:
                raise ValueError("Term definition is attached to an incompatible field")
            term_links.append({"field": value, "definition": definition})
    for subject in store.graph.subjects(RDF.type, NS.Instrument):
        instrument = identity(subject)
        payload = store.payload(instrument)
        attributes = payload.get("instrument_attributes", {})
        if not attributes:
            continue
        fragments = registered_quotation_fragments(
            payload["text"], store.evidence(instrument), registry
        )
        if not fragments:
            raise ValueError(
                "Instrument description no longer resolves to exact original quotations"
            )
        for property_id, value in attributes.items():
            if (node(property_id), RDF.type, OWL.DatatypeProperty) not in store.graph:
                raise ValueError(
                    "Instrument predicate lacks an approved native datatype declaration"
                )
            if (
                str(store.graph.value(subject, node(property_id))) != value
                or value not in payload["text"]
            ):
                raise ValueError(
                    "Instrument facet differs from its original source-backed description"
                )
        instrument_attributes.append(
            {"instrument": instrument, "attributes": attributes, "original_spans": fragments}
        )
    shapes = Graph().parse(ROOT / "ontology/semantic_shapes.ttl")
    shapes.parse(ROOT / "ontology/psi_shapes.ttl")
    conforms, _, report = validate(store.graph, shacl_graph=shapes)
    for sid in [f"psi-{n}" for n in (107, 39, 22, 21, 20, 23, 106, 68, 47)]:
        record_relation = "hasRun" if sid == "psi-39" else "hasSourceRecord"
        family_results = 0
        for field_relation in (
            "hasCondition",
            "hasMeasurement",
            "hasRecordedField",
            "hasMaterialDescription",
        ):
            route = navigate(
                store, sid, [RouteStep(record_relation), RouteStep(field_relation)], registry
            )
            family_results += len(route["results"])
            verified.append(
                {
                    "investigation": sid,
                    "path": [record_relation, field_relation],
                    "results": len(route["results"]),
                    "truncated": route["truncated"],
                    "budget_per_step": route["budget_per_step"],
                }
            )
        if not family_results:
            raise ValueError(f"No available source-backed field reached for {sid}")
    fs = Namespace("https://example.org/nasa-fire-safety#")
    quantitative = []
    for accession, pid in [
        (107, "source:nozzle_diameter"),
        (39, "Pressure"),
        (21, "source:fuel_mfc_capacity"),
        (20, "source:ignition_count"),
        (68, "source:ambient_temperature"),
        (102, "source:weight_loss_rate"),
        (98, "source:sample_width"),
    ]:
        query = f"""SELECT DISTINCT ?record ?value ?unit WHERE {{
            {{ ?link <{NS.subject}> <{node(f"psi-{accession}")}>; <{NS.relation}> ?kind; <{NS.object}> ?record .
               VALUES ?kind {{ <{node("hasRun")}> <{node("hasSourceRecord")}> }} }}
            UNION
            {{ ?link <{NS.subject}> ?record; <{NS.relation}> <{node("belongsToInvestigation")}>; <{NS.object}> <{node(f"psi-{accession}")}> . }}
            ?quantity <{NS.subject}> ?record; <{NS.measuredProperty}> <{node(pid)}>;
                <{fs.reportedValue}> ?value; <{fs.reportedUnit}> ?unit .
        }} LIMIT 3"""
        answers = [
            {"record": str(row.record), "value": row.value.toPython(), "unit": str(row.unit)}
            for row in store.graph.query(query)
        ]
        quantitative.append({"accession": accession, "property": pid, "rows": answers})
        if not answers:
            raise ValueError("Quantitative RDF query returned no original values")
    receipt = {
        "snapshot_id": manifest["snapshot_id"],
        "rdf_triples": len(store.graph),
        "entities": len(store.entities()),
        "graph_evidence_ids": len(refs),
        "missing_graph_evidence_ids": missing,
        "roundtripped_value_cell_links": len(cells),
        "roundtripped_documentary_json_pointers": json_pointers,
        "queryable_properties": dict(values),
        "validated_paths": verified,
        "quantitative_sparql_queries": quantitative,
        "validated_instrument_attributes": instrument_attributes,
        "validated_curated_quotation_contexts": quotation_contexts,
        "validated_field_term_definitions": term_links,
        "shacl_conforms": bool(conforms),
        "shacl_report": str(report),
        "boundary": "Exact cell and graph structure checks; no automatic scientific inference or population answer-quality claim.",
    }
    args.output.write_text(json.dumps(receipt, indent=2) + "\n")
    registry.db.close()
    if missing or not conforms:
        raise SystemExit(1)
    print(
        json.dumps(
            {
                k: v
                for k, v in receipt.items()
                if k not in {"queryable_properties", "validated_paths", "shacl_report"}
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
