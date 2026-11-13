"""One relation registry, generated at load time from the approved ontology.

The ontology (``ontology/fire_safety.ttl``) is the source of truth for which relations exist; the
semantic registry (``domain/semantic_registry.yaml``) says which of them the pipeline selects on,
and the query language (``domain/query_language_v2.yaml``) which words name them. All three are
read, never edited. The endpoint classes of a relation are the ontology's own ``rdfs:domain`` and
``rdfs:range`` when it declares them; it declares none today, so the endpoint contract of
``relation_contracts`` is the only endpoint knowledge and is attached here. A relation with neither
keeps ``endpoints = None``: giving it endpoint classes is an ontology change, not a code change.
"""

import os
from functools import lru_cache
from pathlib import Path

import yaml
from rdflib import OWL, RDF, RDFS, Graph

from nasa_fire_ai.ingestion.relation_contracts import RELATION_ENDPOINTS

ROOT = Path(__file__).resolve().parents[3]


def relation_registry_prompt_enabled():
    """Track B: the model request lists endpoints once (in the ontology context), not twice."""
    return os.getenv("SCIENCE_RELATION_REGISTRY_PROMPT", "0") == "1"


def _local(uri):
    return str(uri).rsplit("#", 1)[-1].rsplit("/", 1)[-1]


@lru_cache(maxsize=8)
def _load(root):
    root = Path(root)
    graph = Graph()
    graph.parse(root / "ontology" / "fire_safety.ttl", format="turtle")
    declared = {}
    for prop in graph.subjects(RDF.type, OWL.ObjectProperty):
        declared[_local(prop)] = {
            "domain": sorted(_local(o) for o in graph.objects(prop, RDFS.domain)) or None,
            "range": sorted(_local(o) for o in graph.objects(prop, RDFS.range)) or None,
        }
    registry = yaml.safe_load((root / "domain" / "semantic_registry.yaml").read_text("utf-8"))
    selected = {
        row["relation_id"]: bool(row.get("selection_scope"))
        for row in registry.get("relations", [])
    }
    language = yaml.safe_load((root / "domain" / "query_language_v2.yaml").read_text("utf-8"))
    mentioned = {}
    for term, row in (language.get("ambiguity_scopes") or {}).items():
        for relation in (row or {}).get("relations", []):
            mentioned.setdefault(relation, []).append(term)
    return declared, selected, mentioned


def relation_registry(root=None):
    """``{relation_id: {...}}`` for every relation the ontology or the semantic registry names.

    Order: the relations that have an endpoint contract, in the contract's order, then the rest by
    name, so every consumer that used the contract's order sees the same order.
    """
    declared, selected, mentioned = _load(str(root or ROOT))
    ids = set(declared) | set(selected) | set(RELATION_ENDPOINTS)
    ordered = [r for r in RELATION_ENDPOINTS if r in ids] + sorted(ids - set(RELATION_ENDPOINTS))
    result = {}
    for rid in ordered:
        found = declared.get(rid, {})
        domain, range_ = found.get("domain"), found.get("range")
        if domain and range_:
            endpoints, source = (frozenset(domain), frozenset(range_)), "ONTOLOGY"
        elif rid in RELATION_ENDPOINTS:
            endpoints, source = RELATION_ENDPOINTS[rid], "CONTRACT"
        else:
            endpoints, source = None, None
        result[rid] = {
            "relation_id": rid,
            "in_ontology": rid in declared,
            "in_registry": rid in selected,
            "selection_scope": selected.get(rid, False),
            "mentioned_by": sorted(mentioned.get(rid, [])),
            "endpoints": endpoints,
            "endpoints_source": source,
        }
    return result


def relations_without_endpoints(root=None):
    return sorted(r for r, row in relation_registry(root).items() if row["endpoints"] is None)


def relation_signature_listing(semantic, root=None):
    """The ``relation_signatures`` of the relationships request: each approved relation that has
    endpoints, with its subject and object classes, in the registry's order."""
    return {
        rid: {
            "subject_classes": sorted(row["endpoints"][0]),
            "object_classes": sorted(row["endpoints"][1]),
        }
        for rid, row in relation_registry(root).items()
        if row["endpoints"] is not None and rid in semantic.relations
    }
