"""Typed navigation over the existing native graph and its approved ontology.

Association paths report connectivity, never inheritance or causal support.
"""

from collections import deque
from dataclasses import dataclass

from rdflib import OWL, RDF, RDFS

from nasa_fire_ai.query.native import NS, identity, node


@dataclass(frozen=True)
class RouteStep:
    relation: str
    direction: str = "FORWARD"


def schema_closure(graph, concept, predicate, budget=64):
    if predicate not in {RDFS.subClassOf, RDFS.subPropertyOf}:
        raise ValueError("only typed schema inheritance is permitted")
    found, queue = {concept}, deque([concept])
    while queue and len(found) < budget:
        for parent in sorted(graph.objects(queue.popleft(), predicate), key=str):
            if parent not in found and len(found) < budget:
                found.add(parent)
                queue.append(parent)
    return found


def navigate(store, start, steps, evidence_registry, max_depth=5, budget=128, allow_context=False):
    """Execute a declared route. Every edge and endpoint retains evidence IDs."""
    if len(steps) > max_depth or budget < 1:
        raise ValueError("route exceeds traversal budget")
    paths = [{"entity": start, "path": [], "visited": {start}}]
    examined = 0
    truncated = False
    for step in steps:
        # Bound each requested hop independently. A large investigation must
        # not spend every later hop's allowance just enumerating its records.
        level_examined = 0
        definition = store.registry.relations.get(step.relation)
        if definition is None or definition.status != "CANONICAL":
            raise LookupError(step.relation)
        if step.direction not in {"FORWARD", "REVERSE"}:
            raise ValueError("unknown route direction")
        eligible_relations = {
            relation
            for relation, meta in store.registry.relations.items()
            if meta.status == "CANONICAL"
            and node(step.relation)
            in schema_closure(store.graph, node(relation), RDFS.subPropertyOf)
        }
        next_paths = []
        for path in paths:
            match, endpoint = (
                (NS.subject, NS.object) if step.direction == "FORWARD" else (NS.object, NS.subject)
            )
            for record in sorted(store.graph.subjects(match, node(path["entity"])), key=str):
                actual_relation = store.graph.value(record, NS.relation)
                if actual_relation is None or identity(actual_relation) not in eligible_relations:
                    continue
                states = {str(s) for s in store.graph.objects(record, NS.reviewState)}
                allowed_states = (
                    {"APPROVED", "VERIFIED_CONTEXTUAL_APPLICABILITY"}
                    if allow_context
                    else {"APPROVED"}
                )
                if states and not states.issubset(allowed_states):
                    continue
                if level_examined >= budget:
                    truncated = True
                    break
                level_examined += 1
                examined += 1
                refs = sorted(str(e) for e in store.graph.objects(record, NS.evidenceRef))
                if not refs or any(evidence_registry.resolve(e) is None for e in refs):
                    continue
                for obj in store.graph.objects(record, endpoint):
                    actual = identity(obj)
                    if actual in path["visited"]:
                        continue
                    next_paths.append(
                        {
                            "entity": actual,
                            "visited": path["visited"] | {actual},
                            "path": path["path"]
                            + [
                                {
                                    "from": path["entity"],
                                    "to": actual,
                                    "relation": identity(actual_relation),
                                    "requested_relation": step.relation,
                                    "direction": step.direction,
                                    "evidence_ids": refs,
                                    "semantics": "ASSOCIATION",
                                }
                            ],
                        }
                    )
            if level_examined >= budget:
                truncated = True
                break
        paths = next_paths
    unique = {}
    for path in paths:
        path.pop("visited")
        payload = store.payload(path["entity"])
        path["entity_details"] = {
            "classes": sorted(store.classes(path["entity"])),
            **{
                key: payload[key]
                for key in (
                    "title",
                    "text",
                    "reported_identifier",
                    "value",
                    "instrument_attributes",
                )
                if payload.get(key) is not None
            },
        }
        path["classification"] = "RELATED"
        path["limits"] = "Connectivity does not establish causality, inheritance or applicability."
        key = (path["entity"], tuple((p["relation"], p["from"], p["to"]) for p in path["path"]))
        unique[key] = path
    return {
        "results": list(unique.values()),
        "examined": examined,
        "budget_per_step": budget,
        "truncated": truncated,
    }


def ontology_inventory(graph):
    return {
        "classes": sorted(str(x) for x in graph.subjects(RDF.type, OWL.Class)),
        "object_properties": sorted(str(x) for x in graph.subjects(RDF.type, OWL.ObjectProperty)),
        "datatype_properties": sorted(
            str(x) for x in graph.subjects(RDF.type, OWL.DatatypeProperty)
        ),
        "class_hierarchies": sorted(
            [str(s), str(o)] for s, o in graph.subject_objects(RDFS.subClassOf)
        ),
        "property_hierarchies": sorted(
            [str(s), str(o)] for s, o in graph.subject_objects(RDFS.subPropertyOf)
        ),
        "domains": sorted([str(s), str(o)] for s, o in graph.subject_objects(RDFS.domain)),
        "ranges": sorted([str(s), str(o)] for s, o in graph.subject_objects(RDFS.range)),
    }
