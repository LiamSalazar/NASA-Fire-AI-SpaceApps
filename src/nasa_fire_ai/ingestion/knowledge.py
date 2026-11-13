"""Additive source-backed ontology alignment; no canonical input mutation."""

import re
from dataclasses import replace

from rdflib import OWL, RDF, RDFS, Graph, Namespace

from nasa_fire_ai.query.native import node
from nasa_fire_ai.query.v2 import RelationDefinition

FS = Namespace("https://example.org/nasa-fire-safety#")


def normalize_mention(text, approved_mentions):
    matches = {
        canonical
        for canonical, aliases in approved_mentions.items()
        if any(
            re.search(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", text, re.IGNORECASE)
            for alias in aliases
        )
    }
    if matches and re.search(
        r"\b(?:not|without|compatible|like|mixture|blend|coated)\b", text, re.IGNORECASE
    ):
        return {"original": text, "identity": None, "status": "AMBIGUOUS"}
    return {
        "original": text,
        "identity": next(iter(matches)) if len(matches) == 1 else None,
        "status": "MATCH" if len(matches) == 1 else "AMBIGUOUS" if matches else "UNKNOWN",
    }


def enrich_native(store, records, evidence_registry, ontology_path, approved_mentions):
    """Project explicit canonical foreign keys using existing ontology relations.

    Scalar condition records stay conditions. No measurement observations are inferred.
    """
    schema = Graph().parse(ontology_path)
    for triple in schema:
        store.graph.add(triple)
    declared = {str(p).removeprefix(str(FS)) for p in schema.subjects(RDF.type, OWL.ObjectProperty)}
    classes = {str(c).removeprefix(str(FS)) for c in schema.subjects(RDF.type, OWL.Class)}
    for cls in classes:
        store.registry.register_target_class(cls)
        store.graph.add((node(cls), RDF.type, OWL.Class))
        store.graph.add((node(cls), OWL.equivalentClass, FS[cls]))
    for child, parent in schema.subject_objects(RDFS.subClassOf):
        if str(child).startswith(str(FS)) and str(parent).startswith(str(FS)):
            store.graph.add(
                (
                    node(str(child).removeprefix(str(FS))),
                    RDFS.subClassOf,
                    node(str(parent).removeprefix(str(FS))),
                )
            )
    for prop in schema.subjects(RDF.type, OWL.DatatypeProperty):
        if not str(prop).startswith(str(FS)):
            continue
        native = node(str(prop).removeprefix(str(FS)))
        store.graph.add((native, RDF.type, OWL.DatatypeProperty))
        store.graph.add((native, OWL.equivalentProperty, prop))
        for predicate in (RDFS.domain, RDFS.range, RDFS.label, RDFS.comment):
            for value in schema.objects(prop, predicate):
                target = (
                    node(str(value).removeprefix(str(FS)))
                    if str(value).startswith(str(FS))
                    else value
                )
                store.graph.add((native, predicate, target))
    for rel in declared:
        existing = store.registry.relations.get(rel, RelationDefinition(rel))
        domain = [
            str(value).removeprefix(str(FS))
            for value in schema.objects(FS[rel], RDFS.domain)
            if str(value).startswith(str(FS))
        ]
        ranges = [
            str(value).removeprefix(str(FS))
            for value in schema.objects(FS[rel], RDFS.range)
            if str(value).startswith(str(FS))
        ]
        labels = [str(label) for label in schema.objects(FS[rel], RDFS.label)]
        store.registry.register_relation(
            replace(
                existing,
                domain=existing.domain or domain,
                range=existing.range or ranges,
                aliases=list(dict.fromkeys([*existing.aliases, *labels])),
            )
        )
    indexed = {r.get("id", r.get("statement_id")): r for r in records}
    report = {"entities": 0, "relations": 0, "normalization": [], "rejected": []}
    for rid, record in indexed.items():
        cls = {"SampleRecord": "Sample", "ConditionRecord": "ExperimentalCondition"}.get(
            record["type"]
        )
        refs = [e["evidence_id"] for e in record.get("evidence_refs", [])]
        if cls and refs and all(evidence_registry.resolve(e) for e in refs):
            store.add_entity(
                rid, cls, refs, [e["source_id"] for e in record["evidence_refs"]], record
            )
            report["entities"] += 1
        if record["type"] == "SampleRecord":
            normalized = normalize_mention(record["material"], approved_mentions)
            normalized["sample_id"] = rid
            normalized["evidence_ids"] = refs
            report["normalization"].append(normalized)
            if normalized["identity"] and refs and all(evidence_registry.resolve(e) for e in refs):
                # Unresolved source descriptions remain specimen payloads, not approved material identities.
                material = normalized["identity"]
                store.add_entity(
                    material,
                    "Material",
                    refs,
                    [e["source_id"] for e in record["evidence_refs"]],
                    payload={"id": material},
                )
                if rid in store.registry.entities:
                    store.add_relation(rid, "madeOf", material, refs)
                    report["relations"] += 1
    for rid, record in indexed.items():
        refs = [e["evidence_id"] for e in record.get("evidence_refs", [])]
        if not refs or any(evidence_registry.resolve(e) is None for e in refs):
            continue
        links = []
        if record["type"] == "ExperimentalRunRecord":
            links = [
                (record.get("investigation_id"), "hasRun", rid),
                (rid, "usesSample", record.get("sample_id")),
            ]
            links += [(rid, "hasCondition", cid) for cid in record.get("condition_ids", [])]
        if record["type"] == "ExperimentalRunRecord":
            sample = indexed.get(record.get("sample_id"), {})
            normalized = normalize_mention(sample.get("material", ""), approved_mentions)
            sample_refs = [e["evidence_id"] for e in sample.get("evidence_refs", [])]
            if (
                normalized["identity"]
                and sample_refs
                and all(evidence_registry.resolve(e) for e in sample_refs)
            ):
                store.add_relation(rid, "hasMaterial", normalized["identity"], sample_refs)
                report["relations"] += 1
        if record.get("source_document"):
            links.append((rid, "reportedBy", record["source_document"]))
        for subject, relation, obj in links:
            if subject in store.registry.entities and obj in store.registry.entities:
                store.add_relation(subject, relation, obj, refs)
                report["relations"] += 1
            else:
                report["rejected"].append(
                    {
                        "subject": subject,
                        "relation": relation,
                        "object": obj,
                        "reason": "unresolved endpoint",
                        "evidence_ids": refs,
                    }
                )
    store.knowledge_enrichment_report = report
    return report


def validate_relation_proposal(proposal, evidence_registry):
    """Model proposals require literal spans; validation does not approve semantics."""
    required = {
        "source_id",
        "evidence_id",
        "subject_mention",
        "predicate_candidate",
        "object_mention",
        "supporting_span",
    }
    if required - proposal.keys():
        raise ValueError("incomplete relation proposal")
    evidence = evidence_registry.resolve(proposal["evidence_id"])
    metadata = evidence_registry.source_metadata(proposal["evidence_id"])
    if not evidence or not metadata or metadata["source_id"] != proposal["source_id"]:
        raise ValueError("source identity mismatch")
    from nasa_fire_ai.ingestion.source_spans import normalized_with_offsets, recover_span

    located = recover_span(
        evidence["text"], proposal["supporting_span"], proposal.get("span_start")
    )
    span = located["span"]
    if any(
        not proposal[key]
        or normalized_with_offsets(proposal[key])[0] not in normalized_with_offsets(span)[0]
        for key in ("subject_mention", "object_mention")
    ):
        raise ValueError("mention absent from supporting span")
    return {
        **proposal,
        "model_supporting_span": proposal["supporting_span"],
        "supporting_span": span,
        "span_start": located["start"],
        "span_end": located["end"],
        "span_validation_method": located["method"],
        "mapping_status": "PENDING_VALIDATION",
        "review_status": "PENDING",
        "epistemic_status": "PROPOSED_EXPLICIT_SOURCE_STATEMENT",
        "page_status": "UNVERIFIED",
        "source_location": {
            "document_id": evidence["document_id"],
            "page": evidence.get("page"),
            "page_status": "UNVERIFIED",
        },
        "staging_contract_version": "knowledge-relations-v2",
    }


def stage_relation_proposal(proposal, evidence_registry):
    """Content-addressed staging, preserving conflicts and pending scientific review."""
    import hashlib
    import json

    validated = validate_relation_proposal(proposal, evidence_registry)
    digest = hashlib.sha256(json.dumps(validated, sort_keys=True).encode()).hexdigest()
    row = {
        **validated,
        "candidate_id": "scientific-relation:" + digest,
        "candidate_type": "RELATION",
        "raw_label": validated["predicate_candidate"],
        "resolution_status": "CANDIDATE_RELATION",
        "reason": "Exact source span validated; ontology mapping and scientific interpretation require review",
    }
    evidence_registry.stage_semantic_candidate(row)
    return row
