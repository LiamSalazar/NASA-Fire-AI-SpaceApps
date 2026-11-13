"""Opt-in additive publication of validated PSI row identities; no inferred science."""

import json

import yaml


def project_validated_psi(store, evidence, root):
    path = root / "data/canonical/phase3c_targeted_psi_records_v1.json"
    if not path.exists():
        return
    records = json.loads(path.read_text())
    samples = root / "data/canonical/phase3c_targeted_psi_samples_v1.json"
    if samples.exists():
        records.extend(json.loads(samples.read_text()))
    language = yaml.safe_load((root / "domain/query_language_v2.yaml").read_text())
    approved_materials = {
        key: meta["aliases"]
        for key, meta in language["entity_mentions"].items()
        if meta["relation"] == "hasMaterial"
    }
    publication = json.loads(
        (root / "artifacts/phase3c_targeted_psi_publication_v2.json").read_text()
    )
    names = {row["source_id"]: row["investigation"] for row in publication}
    for row in records:
        refs = [e["evidence_id"] for e in row["evidence_refs"]]
        if any(evidence.resolve(e) is None for e in refs):
            raise ValueError("unresolvable PSI publication evidence")
        cls = {
            "InvestigationRecord": "Investigation",
            "SampleRecord": "Sample",
            "ExperimentalRunRecord": "ExperimentalRun",
        }[row["type"]]
        if cls not in store.registry.target_classes:
            # Existing ontology class only, never invent a row-role class.
            from rdflib import OWL, RDF, Graph, URIRef

            schema = Graph().parse(root / "ontology/fire_safety.ttl")
            if (
                URIRef("https://example.org/nasa-fire-safety#" + cls),
                RDF.type,
                OWL.Class,
            ) not in schema:
                raise LookupError(cls)
            store.registry.register_target_class(cls)
        if row["id"] in store.entities() and store.payload(row["id"]) != row:
            raise ValueError("conflicting PSI identity")
        store.add_entity(row["id"], cls, refs, [row["source_id"]], row)
        if cls == "ExperimentalRun":
            store.add_relation(row["id"], "belongsToInvestigation", row["investigation_id"], refs)
        elif cls == "Sample":
            sid = row["source_id"]
            title = evidence.source_metadata(refs[0])["title"]
            if sid not in store.entities():
                store.add_entity(sid, "Investigation", refs, [sid], {"id": sid, "title": title})
            mentions = getattr(store.registry, "entity_mentions", {})
            mentions[sid] = {"relation": "belongsToInvestigation", "aliases": [title, names[sid]]}
            store.registry.entity_mentions = mentions
            store.add_relation(row["id"], "belongsToInvestigation", sid, refs)
            raw = row["reported_material_description"].strip().casefold()
            matches = [
                material
                for material, aliases in approved_materials.items()
                if raw in {material.casefold(), *(alias.casefold() for alias in aliases)}
            ]
            if len(matches) == 1:
                # Exact approved source labels only; mixtures, blank cells and
                # cross-row inheritance cannot establish material identity.
                store.add_relation(row["id"], "hasMaterial", matches[0], refs)
