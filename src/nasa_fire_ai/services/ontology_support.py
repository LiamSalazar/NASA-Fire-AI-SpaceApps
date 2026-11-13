"""Conservative ontology audit for a proposed, source-scoped proposition.

This records what the approved native graph can establish. Unmatched language and
missing triples remain open-world documentary candidates for source verification.
"""

import re
from functools import lru_cache

from rdflib import RDFS

from nasa_fire_ai.query.native import NS, canonical_record, node
from nasa_fire_ai.query.ontology_navigation import schema_closure

DASH_SPELLINGS = str.maketrans({glyph: "-" for glyph in "‐‑‒–—−"})


def identity_spelling(text):
    """Unify printed dash glyphs for identity matching; preserve source bytes."""
    return text if text.isascii() else text.translate(DASH_SPELLINGS)


def investigation_labels(store):
    """Reuse the approved lookup catalogue only for a pinned read-only snapshot."""
    mentions = store.registry.entity_mentions
    snapshot = getattr(store, "_approved_snapshot_id", None)
    key = (snapshot, len(mentions))
    cached = getattr(store, "_investigation_label_cache", None)
    if snapshot and cached is not None and cached[0] == key:
        return cached[1]
    labels = tuple(
        (entity, label)
        for entity, metadata in mentions.items()
        if metadata.get("relation") == "belongsToInvestigation"
        for label in [entity, *metadata.get("aliases", [])]
        if label
    )
    if snapshot:
        store._investigation_label_cache = (key, labels)
    return labels


@lru_cache(maxsize=32768)
def _mention_pattern(label):
    """Cache only immutable syntax; source facts and graph compatibility stay live."""
    return re.compile(r"(?<!\w)" + re.escape(identity_spelling(label)) + r"(?!\w)", re.IGNORECASE)


def scientific_mention_view(text, store):
    """A printed identifier column is metadata, not an investigation mention."""
    from nasa_fire_ai.query.record_identity import mask_deictic_references

    result = mask_deictic_references(text)
    for header in getattr(store.registry, "identifier_headers", []):
        pattern = (
            r"(?<!\w)" + re.escape(header) + r"(?=\s*(?::|#|\d|\b(?:field|column|identifier)\b))"
        )
        result = re.sub(pattern, lambda match: " " * len(match[0]), result, flags=re.IGNORECASE)
    return identity_spelling(result)


def _mentions(text, store):
    text = scientific_mention_view(text, store)
    snapshot = getattr(store, "_approved_snapshot_id", None)
    if snapshot:
        key = (snapshot, len(store.registry.entities), len(store.registry.entity_mentions))
        cached = getattr(store, "_entity_label_cache", None)
        if cached is None or cached[0] != key:
            catalogue = tuple(
                (
                    entity,
                    (entity, *store.registry.entity_mentions.get(entity, {}).get("aliases", [])),
                )
                for entity in sorted(store.registry.entities)
            )
            store._entity_label_cache = (key, catalogue)
        else:
            catalogue = cached[1]
        return {
            entity: sorted(store.classes(entity, include_ancestors=True))
            for entity in entity_mention_ids(text, catalogue)
        }
    # Most registered entities are long source-record/value identifiers. Avoid
    # thousands of regex searches for labels absent from this proposition.
    # ASCII labels retain Python's Unicode IGNORECASE equivalents (dotless i,
    # dotted I, long s and Kelvin sign); non-ASCII labels use the original regex.
    # This is only a candidate prefilter: boundaries and identity still require
    # the unchanged regex, and classes are read live from the graph below.
    folded = text.casefold().replace("\u0307", "").replace("\u0131", "i")
    matches = {}
    for entity in store.registry.entities:
        metadata = store.registry.entity_mentions.get(entity, {})
        labels = [entity, *metadata.get("aliases", [])]
        if any(
            label
            and (not label.isascii() or label.lower() in folded)
            and _mention_pattern(label).search(text)
            for label in labels
        ):
            matches[entity] = sorted(store.classes(entity, include_ancestors=True))
    return matches


@lru_cache(maxsize=4096)
def entity_mention_ids(text, catalogue):
    """Cache name syntax only; callers still read scientific classes live."""
    folded = text.casefold().replace("\u0307", "").replace("\u0131", "i")
    return tuple(
        entity
        for entity, labels in catalogue
        if any(
            label
            and (not label.isascii() or label.lower() in folded)
            and _mention_pattern(label).search(text)
            for label in labels
        )
    )


def leading_investigation(text, store):
    """Interpret an explicitly leading scientific subject, without certifying facts."""
    text = scientific_mention_view(text, store)
    # Lowercase deictic noun phrases are references, not catalogue acronyms.
    # Preserve uppercase scientific names even when their spelling is ordinary.
    reference = re.match(
        r"^(?:(?:the|this|that|these|those)\s+)?(same|previous|latter|former|aforementioned)(?![\w-])",
        text,
        re.IGNORECASE,
    )
    if reference and not reference[1].isupper():
        return None
    candidates = []
    for entity, label in investigation_labels(store):
        match = re.match(
            r"^(?:(?:For|In|According to|Each|Every|All|The(?: (?:available|original|registered))?)\s+)?"
            + re.escape(identity_spelling(label))
            + r"(?!\w)",
            text,
            re.IGNORECASE,
        )
        if match:
            candidates.append((match.end(), entity, label))
    if not candidates:
        return None
    _, entity, label = max(candidates)
    return {"id": entity, "label": label}


def investigation_mentions(text, store):
    text = scientific_mention_view(text, store)
    return set(investigation_mention_ids(text, investigation_labels(store)))


@lru_cache(maxsize=8192)
def investigation_mention_ids(text, labels):
    """Resolve repeated section introductions against the exact approved labels."""
    from nasa_fire_ai.query.record_identity import investigation_scope_groups

    mentions = [
        (entity, match.start(), match.end())
        for entity, label in labels
        for match in _mention_pattern(label).finditer(text)
    ]
    return frozenset(
        entity for group in investigation_scope_groups(text, mentions) for entity in group["ids"]
    )


def audit_relation(text, anchors, store, evidence_registry):
    """Return graph status without granting documentary truth from class compatibility.

    A relation is named only when its approved identifier or alias appears in the
    proposition. Endpoint order must be explicit and unambiguous. Source evidence
    remains mandatory even for a canonical triple.
    """
    primary = leading_investigation(text, store)
    # Alternatives in a summary are not an enumeration of physical subjects.
    # Use the approved record classes before NLI can over-entail a documentary
    # range description. This is independent of investigation/source identity.
    identity_mapping = (
        re.search(
            r"\b(?:alternatives?|ranges?|combinations?|configurations?)\b", text, re.IGNORECASE
        )
        and re.search(
            r"\b(?:distinct|identified|physical|individual|unique|separate)\b", text, re.IGNORECASE
        )
        and re.search(r"\b(?:runs?|tests?|experiments?|samples?|specimens?)\b", text, re.IGNORECASE)
        and re.search(
            r"\b(?:correspond\w*|represent\w*|enumerat\w*|identif\w*|maps?|mapping)\b",
            text,
            re.IGNORECASE,
        )
    )
    negated_identity = re.search(
        r"\b(?:not|never)\s+(?:\w+\s+){0,2}(?:correspond\w*|represent\w*|enumerat\w*|identif\w*|maps?|mapping)\b"
        r"|\b(?:not|no)\s+(?:distinct|identified|physical|individual|unique|separate)\b",
        text,
        re.IGNORECASE,
    )
    if primary and identity_mapping and not negated_identity:
        records = store.relations(primary["id"], "hasSourceRecord")
        classes = [set(store.classes(record)) for record in records]
        summary_classes = {
            "ConfigurationSummary",
            "SourceRecord",
            "ExperimentalSession",
            "PublicationFigureReference",
        }
        if (
            classes
            and any(kinds & summary_classes for kinds in classes)
            and not any(kinds & {"ExperimentalRun", "Sample"} for kinds in classes)
        ):
            return {
                "scientific_status": "ONTOLOGY_INCOMPATIBLE",
                "verification_mechanism": "source_record_identity_scope",
                "reason": "Original source record classes do not establish an enumeration of distinct physical experimental subjects",
                "resolved_entities": {primary["id"]: sorted(store.classes(primary["id"]))},
            }
    named_subjects = investigation_mentions(text, store)
    single_subject = primary and len(named_subjects) == 1
    if len(named_subjects) > 1:
        grounded = {
            subject for anchor in anchors for subject in anchor.get("scientific_subjects", [])
        }
        for anchor in anchors:
            for span in anchor.get("spans", []):
                if span.get("scope") not in {"section_heading", "source_local_name_definition"}:
                    grounded.update(investigation_mentions(span["text"], store))
        if named_subjects - grounded:
            return {
                "scientific_status": "ONTOLOGY_INCOMPATIBLE",
                "verification_mechanism": "cross_investigation_identity_scope",
                "reason": "Cross-investigation assertion requires source-scoped identity for each named investigation",
                "resolved_entities": _mentions(text, store),
            }
    if single_subject and any(
        anchor.get("scientific_subjects") and primary["id"] not in anchor["scientific_subjects"]
        for anchor in anchors
    ):
        return {
            "scientific_status": "ONTOLOGY_INCOMPATIBLE",
            "verification_mechanism": "source_scoped_record_identity",
            "reason": "Claimed investigation differs from the source passage's evidence-backed scope",
            "resolved_entities": _mentions(text, store),
        }
    if single_subject and any(
        len(anchor.get("scientific_context_groups", [])) > 1 for anchor in anchors
    ):
        return {
            "scientific_status": "ONTOLOGY_INCOMPATIBLE",
            "verification_mechanism": "mixed_investigation_context",
            "reason": "Selected passage mixes independently attributed investigations; narrow its evidence before verification",
            "resolved_entities": _mentions(text, store),
        }
    entities = _mentions(text, store)
    predicates = [
        relation
        for relation, definition in store.registry.relations.items()
        if definition.status == "CANONICAL"
        and any(
            label and _mention_pattern(label).search(text)
            for label in [relation, *definition.aliases]
        )
    ]
    receipt = {
        "resolved_entities": entities,
        "ontology_predicates": [str(node(p)) for p in predicates],
        "scientific_status": "DOCUMENTARY_CANDIDATE",
        "verification_mechanism": "original_evidence_required",
    }
    if len(entities) != 2 or len(predicates) != 1:
        return receipt
    predicate = predicates[0]
    ordered = sorted(
        entities,
        key=lambda entity: min(
            (
                m.start()
                for label in [
                    entity,
                    *store.registry.entity_mentions.get(entity, {}).get("aliases", []),
                ]
                for m in _mention_pattern(label).finditer(text)
            ),
            default=len(text),
        ),
    )
    subject, obj = ordered
    definition = store.registry.relations[predicate]
    receipt.update({"subject_entity_id": subject, "object_entity_id": obj})
    if definition.domain and not set(entities[subject]).intersection(definition.domain):
        receipt["scientific_status"] = "ONTOLOGY_INCOMPATIBLE"
        return receipt
    if definition.range and not set(entities[obj]).intersection(definition.range):
        receipt["scientific_status"] = "ONTOLOGY_INCOMPATIBLE"
        return receipt
    supplied = {span["evidence_id"] for a in anchors for span in a.get("spans", [])}
    for record in store.graph.subjects(NS.subject, node(subject)):
        if not canonical_record(store.graph, record) or store.graph.value(
            record, NS.object
        ) != node(obj):
            continue
        actual = store.graph.value(record, NS.relation)
        if actual is None or node(predicate) not in schema_closure(
            store.graph, actual, RDFS.subPropertyOf
        ):
            continue
        refs = {str(ref) for ref in store.graph.objects(record, NS.evidenceRef)}
        if (
            refs
            and refs.intersection(supplied)
            and all(evidence_registry.resolve(ref) for ref in refs)
        ):
            receipt.update(
                {
                    "scientific_status": "GRAPH_SUPPORTED_CANDIDATE",
                    "graph_assertion_id": str(record),
                    "graph_evidence_ids": sorted(refs),
                    "verification_mechanism": "approved_graph_and_original_evidence",
                }
            )
            break
    return receipt
