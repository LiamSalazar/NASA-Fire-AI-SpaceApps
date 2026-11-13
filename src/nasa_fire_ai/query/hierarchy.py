"""Reviewed RDF taxonomy traversal, separate from experimental relations.

No taxonomy is inferred from labels, model proposals, or experimental co-occurrence.
SKOS hierarchy supports discovery; only class subsumption, reviewed membership,
or individual identity can satisfy a category/identity constraint.
"""

import hashlib
import json
import re
from collections import deque
from dataclasses import asdict, dataclass

from rdflib import OWL, RDF, RDFS, SKOS, Literal, URIRef

HIERARCHY = {str(RDFS.subClassOf), str(SKOS.broader), str(RDF.type)}
IDENTITY = {str(OWL.sameAs)}
RELATED = {str(SKOS.related), str(SKOS.exactMatch)}


@dataclass(frozen=True)
class TaxonomyEdge:
    subject: str
    predicate: str
    object: str
    authority: str
    review_state: str
    provenance: str
    scope: str
    version: str
    evidence_ids: tuple[str, ...]
    subject_kind: str = "concept"
    object_kind: str = "concept"

    def validate(self, registry):
        if self.predicate not in HIERARCHY | IDENTITY | RELATED:
            raise ValueError("unsupported taxonomy predicate")
        if not all((self.authority, self.provenance, self.scope, self.version, self.evidence_ids)):
            raise ValueError("taxonomy provenance required")
        if self.subject not in registry.entities or self.object not in registry.entities:
            raise LookupError("taxonomy endpoints must be registered")
        if self.review_state not in {"APPROVED", "PENDING", "REJECTED"}:
            raise ValueError("invalid review state")
        kinds = (self.subject_kind, self.object_kind)
        expected = {
            str(RDFS.subClassOf): ("class", "class"),
            str(RDF.type): ("individual", "class"),
            str(OWL.sameAs): ("individual", "individual"),
            str(SKOS.broader): ("concept", "concept"),
            str(SKOS.related): ("concept", "concept"),
            str(SKOS.exactMatch): ("concept", "concept"),
        }
        if kinds != expected[self.predicate]:
            raise ValueError("predicate incompatible with endpoint modeling")


def add_taxonomy_edge(store, edge):
    from nasa_fire_ai.query.native import NS, node

    edge.validate(store.registry)
    payload = asdict(edge)
    key = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    record = node("taxonomy:" + key)
    # Standard RDF reification, not a new scientific relation vocabulary.
    for predicate, value in (
        (RDF.type, RDF.Statement),
        (RDF.subject, node(edge.subject)),
        (RDF.predicate, URIRef(edge.predicate)),
        (RDF.object, node(edge.object)),
        (NS.payload, Literal(json.dumps(payload, sort_keys=True))),
    ):
        store.graph.add((record, predicate, value))
    for eid in edge.evidence_ids:
        store.graph.add((record, NS.evidenceRef, Literal(eid)))
    # Reviewed edges are still consulted through their provenance-bearing records.
    # They never create experiment-to-material relations.
    return str(record)


def taxonomy_edges(store, evidence_registry=None):
    from nasa_fire_ai.query.native import NS, node

    approved, staged = [], []
    for record in store.graph.subjects(RDF.type, RDF.Statement):
        raw = store.graph.value(record, NS.payload)
        if raw is None:
            continue
        payload = json.loads(str(raw))
        payload["evidence_ids"] = tuple(payload["evidence_ids"])
        edge = TaxonomyEdge(**payload)
        edge.validate(store.registry)
        if any(
            store.graph.value(record, predicate) != value
            for predicate, value in (
                (RDF.subject, node(edge.subject)),
                (RDF.predicate, URIRef(edge.predicate)),
                (RDF.object, node(edge.object)),
            )
        ):
            raise ValueError("taxonomy reification conflicts with provenance payload")
        if {str(e) for e in store.graph.objects(record, NS.evidenceRef)} != set(edge.evidence_ids):
            raise ValueError("taxonomy evidence references conflict with payload")
        if edge.review_state == "APPROVED" and (
            evidence_registry is None
            or all(evidence_registry.resolve(eid) for eid in edge.evidence_ids)
        ):
            approved.append(edge)
        else:
            staged.append(edge)
    return sorted(approved, key=lambda e: (e.subject, e.predicate, e.object)), staged


def traverse(store, requested, scope, evidence_registry=None, max_depth=4, max_visits=128):
    """Bounded simple paths: down, up, or up-then-down, never down-then-up.

    A shared distant root is not sufficient: the scope must be explicitly reviewed
    for the requested experimental dimension. Budgets bound paths, including cycles.
    """
    if not 1 <= max_depth <= 8 or not 1 <= max_visits <= 1024:
        raise ValueError("invalid traversal budget")
    edges, _ = taxonomy_edges(store, evidence_registry)
    adjacency = {}
    for edge in edges:
        if edge.scope != scope:
            continue
        for start, end, direction in (
            (edge.subject, edge.object, "ANCESTOR"),
            (edge.object, edge.subject, "DESCENDANT"),
        ):
            if edge.predicate in IDENTITY:
                direction = "IDENTITY"
            elif edge.predicate in RELATED:
                direction = "RELATED"
            adjacency.setdefault(start, []).append((end, direction, edge))
    queue = deque([(requested, [], (requested,), "")])
    results, visited, exhausted = {}, 0, False
    while queue and visited < max_visits:
        current, path, nodes, phase = queue.popleft()
        visited += 1
        if len(path) >= max_depth:
            continue
        for actual, direction, edge in adjacency.get(current, []):
            if len(results) >= max_visits or visited + len(queue) >= max_visits:
                exhausted = True
                break
            if actual in nodes:
                continue
            if phase in {"DESCENDANT", "SIBLING"} and direction == "ANCESTOR":
                continue
            if direction == "RELATED" and path:
                continue
            new_phase = (
                "SIBLING"
                if phase in {"ANCESTOR", "SIBLING"} and direction == "DESCENDANT"
                else phase
                if direction == "IDENTITY" and phase
                else direction
            )
            step = {
                **asdict(edge),
                "direction": direction,
                "from_concept": current,
                "to_concept": actual,
            }
            new_path = [*path, step]
            category_match = new_phase in {"DESCENDANT", "IDENTITY"} and all(
                p["predicate"] in {str(RDFS.subClassOf), str(RDF.type), str(OWL.sameAs)}
                for p in new_path
            )
            row = {
                "requested_concept": requested,
                "actual_concept": actual,
                "relationship_type": new_phase,
                "depth": len(new_path),
                "path": new_path,
                "category_match": category_match,
                "taxonomy_evidence_ids": sorted(
                    {eid for p in new_path for eid in p["evidence_ids"]}
                ),
            }
            prior = results.get(actual)
            if prior is None or (not category_match, len(new_path)) < (
                not prior["category_match"],
                prior["depth"],
            ):
                results[actual] = row
            if direction != "RELATED":
                queue.append((actual, new_path, (*nodes, actual), new_phase))
    return {"paths": results, "visits": visited, "budget_exhausted": exhausted or bool(queue)}


def constraint_explanation(subject, intent, store, paths, detail, query=None):
    from nasa_fire_ai.query.contextual import enabled

    dimensions = []
    for constraint in intent.entity_constraints:
        actual = sorted(store.relations(subject, constraint.relation))
        context_resolution = None
        if not actual and enabled() and (layer := getattr(store, "context_layer", None)):
            values, context_resolution = layer.relations(subject, constraint.relation)
            actual = sorted(values)
        relations = [
            paths.get((constraint.relation, constraint.entity_id), {}).get(a) for a in actual
        ]
        relations = [r for r in relations if r]
        status = (
            "MATCH"
            if constraint.entity_id in actual or any(r["category_match"] for r in relations)
            else "DIFFER"
            if actual
            else "UNKNOWN"
        )
        dimensions.append(
            {
                "dimension": constraint.relation,
                "status": status,
                "requested": constraint.entity_id,
                "actual": actual,
                "relationships": relations,
                "evidence_ids": store.evidence(subject),
                "context_resolution": context_resolution.model_dump(mode="json")
                if context_resolution
                else None,
            }
        )
    for constraint in intent.property_constraints:
        records = store.value_records(subject, constraint.property_id)
        if not records and enabled() and (layer := getattr(store, "context_layer", None)):
            records = layer.values(subject, constraint.property_id, constraint.qualifiers)
        outcome = next(
            (
                key
                for key in ("matches", "differs", "unknown", "invalid")
                if constraint.property_id in detail[key]
            ),
            "unknown",
        )
        dimensions.append(
            {
                "dimension": constraint.property_id,
                "status": {"matches": "MATCH", "differs": "DIFFER"}.get(outcome, "UNKNOWN"),
                "invalid": outcome == "invalid",
                "requested": constraint.model_dump(mode="json"),
                "actual": [
                    {**row, "value": row["value"].model_dump(mode="json")} for row in records
                ],
            }
        )
    policy = store.registry.selection_policy.get("related", {})
    dimension_weights = policy.get("dimension_weights", {})
    status_weights = {
        "MATCH": policy.get("match_weight", 3),
        "DIFFER": policy.get("difference_weight", -2),
        "UNKNOWN": policy.get("unknown_weight", -1),
    }
    for dimension in dimensions:
        dimension["ranking_contribution"] = (
            dimension_weights.get(dimension["dimension"], 1) * status_weights[dimension["status"]]
        )
    counts = {s: sum(d["status"] == s for d in dimensions) for s in ("MATCH", "DIFFER", "UNKNOWN")}
    topic_terms = sorted(
        {
            term
            for forms in store.registry.selection_policy.get("topical_wordforms", {}).values()
            for term in forms
            if query and re.search(rf"\b{re.escape(term)}\b", query, re.IGNORECASE)
        }
    )
    return {
        "scientific_context": {
            "requested_phenomenon_topic_terms": topic_terms,
            "topic_term_authority": "LINGUISTIC_TOPIC_ONLY; not a canonical phenomenon assertion",
            "requested_phenomena": [
                c.entity_id for c in intent.entity_constraints if c.relation == "hasPhenomenon"
            ],
            "actual_phenomena": sorted(store.relations(subject, "hasPhenomenon")),
            "phenomenon_status": (
                "QUERY_PHENOMENON_UNMAPPED"
                if topic_terms
                and not any(c.relation == "hasPhenomenon" for c in intent.entity_constraints)
                else "NOT_REQUESTED"
                if not any(c.relation == "hasPhenomenon" for c in intent.entity_constraints)
                else "SOURCE_RELATION_AVAILABLE"
                if store.relations(subject, "hasPhenomenon")
                else "UNKNOWN"
            ),
            "phenomenon_evidence_status": "SOURCE_RELATION_AVAILABLE"
            if store.relations(subject, "hasPhenomenon")
            else "UNKNOWN",
            "actual_gravity": sorted(store.relations(subject, "hasGravityCondition")),
            "measurement_context": sorted(
                {
                    row["qualifiers"].get("role", "UNKNOWN")
                    for property_id in store.registry.properties
                    for row in store.value_records(subject, property_id)
                }
            ),
            "independent_usefulness": "UNADJUDICATED",
            "scope_limit": "Constraint overlap establishes eligibility, not usefulness or claim transfer.",
        },
        "dimensions": dimensions,
        "matching_constraints": [d for d in dimensions if d["status"] == "MATCH"],
        "differing_constraints": [d for d in dimensions if d["status"] == "DIFFER"],
        "unknown_constraints": [d for d in dimensions if d["status"] == "UNKNOWN"],
        "source_evidence_ids": store.evidence(subject),
        "why_useful": "; ".join(
            [
                f"{d['dimension']} {d['status']}: requested {d['requested']}; actual {d['actual']}"
                for d in dimensions
            ]
        ),
        "cannot_conclude": "Findings cannot be transferred across materials or conditions; category matches do not establish uniform family behavior.",
        "ranking_factors": counts,
        "ranking_score": sum(d["ranking_contribution"] for d in dimensions),
        "ranking_policy": policy,
    }


def load_taxonomy(store, document):
    """Invalid declarative additions are diagnostic; exact projection survives."""
    if not isinstance(document, dict):
        raise TypeError("taxonomy document must be a mapping")
    store.taxonomy_proposals = document.get("proposals", [])
    store.taxonomy_load_errors = []
    edges = document.get("edges", [])
    if not isinstance(edges, list):
        raise TypeError("taxonomy edges must be a list")
    for index, row in enumerate(edges):
        try:
            edge = TaxonomyEdge(**{**row, "evidence_ids": tuple(row["evidence_ids"])})
            add_taxonomy_edge(store, edge)
        except (ValueError, TypeError, LookupError) as exc:
            store.taxonomy_load_errors.append({"edge_index": index, "reason": type(exc).__name__})
