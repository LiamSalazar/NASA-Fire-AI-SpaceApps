"""Report current source, graph, passage and measurement depth without scientific grading."""

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rdflib import OWL, Graph

from nasa_fire_ai.query.native import NS, identity, node
from nasa_fire_ai.services.search import ScientificSearchService


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--vectors", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    search = ScientificSearchService(args.snapshot, root)
    try:
        sources = {}
        for source in search.registry.db.execute("SELECT * FROM sources ORDER BY source_id"):
            item = dict(source)
            item["registered_passages"] = search.registry.db.execute(
                "SELECT COUNT(*) FROM passages p JOIN documents d USING(document_id) WHERE d.source_id=?",
                (source["source_id"],),
            ).fetchone()[0]
            item["depth"] = search.depths.get(source["source_id"])
            sources[source["source_id"]] = item
        meta = json.loads((args.vectors / "documentary.metadata.json").read_text())
        assert meta["snapshot_id"] == search.manifest["snapshot_id"]
        investigations = []
        campaign_file = root / "data/raw/hackathon-team/data/clean/campaigns.csv"
        for campaign in csv.DictReader(campaign_file.open()):
            sid = campaign["accession"].lower()
            records = search._investigation_records(sid)
            classes = Counter(c for record in records for c in search.store.classes(record))
            subjects = {sid, *records}
            for relation in search.store.registry.relations:
                subjects.update(search.store.relations(sid, relation))
            measures = set()
            relation_count = 0
            for subject in subjects:
                for edge in search.store.graph.subjects(NS.subject, node(subject)):
                    if search.store.graph.value(edge, NS.measuredProperty):
                        measures.add(edge)
                    elif search.store.graph.value(edge, NS.relation):
                        relation_count += 1
            reported_roles = Counter(
                search.store.payload(identity(measure))
                .get("qualifiers", {})
                .get("scientific_role", "unspecified")
                for measure in measures
            )
            graph_sources = {
                source for subject in subjects for source in search.store.sources(subject)
            }
            topical = {
                source for source, scopes in search.source_scopes.items() if sid in scopes
            } - graph_sources
            investigations.append(
                {
                    "investigation": sid,
                    "title": campaign["title"],
                    "catalogue": "catalog-" + sid in sources,
                    "record_classes": dict(sorted(classes.items())),
                    "queryable_value_records": len(measures),
                    "quantity_roles": dict(sorted(reported_roles.items())),
                    "outgoing_assertion_records": relation_count,
                    "source_backed_association_sources": sorted(graph_sources),
                    "additional_title_routing_sources": sorted(topical),
                    "registered_passages_in_associated_sources": sum(
                        sources[s]["registered_passages"] for s in graph_sources if s in sources
                    ),
                    "documentary_sources": sorted(
                        s
                        for s in graph_sources
                        if s in sources
                        and sources[s]["mime_type"] in {"application/pdf", "application/json"}
                    ),
                    "original_citations": [
                        {k: sources[s][k] for k in ("source_id", "title", "doi", "url", "sha256")}
                        for s in sorted(graph_sources)
                        if s in sources
                    ],
                }
            )
        receipt = {
            "snapshot_id": search.manifest["snapshot_id"],
            "ontology_version": str(
                next(
                    Graph().parse(root / "ontology/psi_science.ttl").objects(None, OWL.versionInfo)
                )
            ),
            "vector_metadata": meta,
            "sources": list(sources.values()),
            "investigations": investigations,
            "depth_counts": dict(Counter(source["depth"] for source in sources.values())),
            "entities_by_class": dict(
                Counter(
                    class_id
                    for subject in search.store.entities()
                    for class_id in search.store.classes(subject)
                )
            ),
            "relationships_by_predicate": dict(
                Counter(
                    identity(predicate)
                    for predicate in search.store.graph.objects(None, NS.relation)
                )
            ),
            "registered_value_records": len(
                set(search.store.graph.subjects(NS.measuredProperty, None))
            ),
            "boundary": "Source and graph inventory, not answer-quality grading. Title routing is topical only. Publication metadata is not full scientific content; configuration/session/acquisition records are not reconciled physical runs.",
        }
        args.output.write_text(json.dumps(receipt, indent=2) + "\n")
    finally:
        search.close()


if __name__ == "__main__":
    main()
