"""Ontology snippets: the semantic context of the classes a passage is about.

Instead of only a global list of allowed class and relation names, the model can be
shown, for each class actually in play, what the approved ontology and the
SemanticRegistry say about it: its ancestors and children, the relations it can take
part in (inherited from its ancestors), the classes at the other end, its aliases,
and whether it is an information class. This is the ontology-snippet mechanism of
ODKE+ (arXiv 2509.04696), built here from this repository's own ontology and
registry at request time, never from a static prompt.

Staged, unapproved extension proposals are listed apart, with their state, so that
extraction stays compatible with them without treating them as approved.

Nothing here decides anything: a snippet is context for the model and for review.
"""


def parents(cls, semantic):
    from nasa_fire_ai.ingestion.semantic import approved_parents

    return approved_parents(cls, semantic.class_metadata)


def lineage(cls, semantic):
    """A class and its ancestors, nearest first; cycle-safe; several parents allowed."""
    order, seen, frontier = [], set(), [cls]
    while frontier:
        following = []
        for current in frontier:
            if current in seen:
                continue
            seen.add(current)
            order.append(current)
            following.extend(sorted(parents(current, semantic)))
        frontier = following
    return order


def children(cls, semantic):
    return sorted(c for c in semantic.class_metadata if cls in parents(c, semantic))


def relation_signatures(semantic, endpoints=None):
    """Each relation's subject and object classes: the registry's own domain and range,
    or the endpoint contract the validator enforces when the registry has none."""
    signatures = {}
    for rid, definition in sorted(semantic.relations.items()):
        domain = list(getattr(definition, "domain", None) or [])
        range_ = list(getattr(definition, "range", None) or [])
        if not (domain and range_) and endpoints and rid in endpoints:
            domain, range_ = (sorted(side) for side in endpoints[rid])
        signatures[rid] = (domain, range_)
    return signatures


def snippet(cls, semantic, endpoints=None):
    """What the approved semantics say about one class."""
    if cls not in semantic.class_metadata:
        return {"class": cls, "status": "NOT_IN_APPROVED_ONTOLOGY"}
    meta = semantic.class_metadata[cls]
    ancestry = lineage(cls, semantic)
    as_subject, as_object = [], []
    for rid, (domain, range_) in relation_signatures(semantic, endpoints).items():
        if domain and set(domain) & set(ancestry):
            as_subject.append({"relation": rid, "object_classes": sorted(range_)})
        if range_ and set(range_) & set(ancestry):
            as_object.append({"relation": rid, "subject_classes": sorted(domain)})
    result = {
        "class": cls,
        "status": "APPROVED",
        "ancestors": ancestry[1:],
        "children": children(cls, semantic),
        "aliases": sorted(meta.get("query_terms") or []),
        "information_class": cls in getattr(semantic, "information_classes", set()),
        "documentary": bool(meta.get("documentary")),
        "relations_as_subject": as_subject,
        "relations_as_object": as_object,
    }
    if meta.get("definition"):
        result["definition"] = meta["definition"]
    return result


def staged_snippet(proposal):
    """A staged extension proposal as context: its state is never 'approved'."""
    result = {
        "term": proposal["term"],
        "kind": proposal["kind"],
        "status": proposal.get("status", "STAGED_FOR_ONTOLOGY_REVIEW"),
    }
    for key in ("parent", "proposed_parents", "domain", "range"):
        if proposal.get(key):
            result[key] = proposal[key]
    return result


def ontology_context(classes, semantic, endpoints=None, staged=()):
    """Snippets for the classes in play, in a stable order (a changing order would make
    identical requests differ), plus the staged terms they may need."""
    # Only terms still awaiting review: a rejected or superseded term is not offered,
    # and an approved one is approved vocabulary, listed with the classes if in play.
    pending = [
        p
        for p in staged
        if p.get("term")
        and p.get("review_status", "PENDING") not in {"REJECTED", "SUPERSEDED", "APPROVED"}
        and p["term"] not in semantic.class_metadata
        and p["term"] not in semantic.relations
    ]
    return {
        "approved": [snippet(c, semantic, endpoints) for c in sorted(set(classes))],
        "staged": [
            staged_snippet(p) for p in sorted(pending, key=lambda p: (p["kind"], p["term"]))
        ],
    }


# O1 (SCIENCE_STAGED_CONTEXT): reviewed staged terms from a frozen snapshot, never
# the registry as it stands, and never a term staged from the document being read.
STAGED_SNAPSHOT_REVIEWED = "REVIEWED"


def build_staged_snapshot(candidates, digest_for_source, *, version, reviewed):
    """A frozen, versioned snapshot of reviewed staged terms.

    ``candidates`` are the rows of the registry's staged semantic candidates;
    ``digest_for_source`` maps a source id to the PDF sha256 it was read from;
    ``reviewed`` is the set of terms a reviewer has marked reviewed. A term the
    pipeline did not produce from a document (no origin digest) is left out, so
    only terms a new document could also produce can reach a request. Only
    snippet fields and the origins are kept; evidence quotes and labels from the
    origin text are dropped.
    """
    terms = {}
    for candidate in candidates:
        proposal = candidate.get("proposal") or {}
        term = proposal.get("term")
        if (
            not term
            or term not in reviewed
            or candidate.get("review_status", "PENDING") in {"REJECTED", "SUPERSEDED", "APPROVED"}
        ):
            continue
        digest = digest_for_source(candidate.get("source_id"))
        if not digest:
            continue
        entry = terms.setdefault(
            term,
            {
                **{
                    k: proposal[k]
                    for k in ("term", "kind", "parent", "proposed_parents", "domain", "range")
                    if proposal.get(k)
                },
                "review_status": STAGED_SNAPSHOT_REVIEWED,
                "origins": [],
            },
        )
        origin = {"source_id": candidate.get("source_id"), "pdf_sha256": digest}
        if origin not in entry["origins"]:
            entry["origins"].append(origin)
    return {"version": version, "terms": sorted(terms.values(), key=lambda t: t["term"])}


def staged_terms_for(document_digests, snapshot):
    """The snapshot's reviewed terms that did not come from this document.

    ``document_digests`` is the PDF sha256 of the document (or a collection of
    them). The digest is compared, not the source id: the same PDF read twice has
    two source ids. A term reaches a document only if a new, unseen document
    would also have it.
    """
    if isinstance(document_digests, str):
        document_digests = {document_digests}
    digests = {d for d in document_digests if d}
    return [
        {k: v for k, v in term.items() if k != "origins"}
        for term in (snapshot or {}).get("terms", [])
        if term.get("review_status") == STAGED_SNAPSHOT_REVIEWED
        and not digests & {o.get("pdf_sha256") for o in term.get("origins", [])}
    ]


def load_staged_snapshot(path):
    import json
    from pathlib import Path

    if not path or not Path(path).is_file():
        return None
    return json.loads(Path(path).read_text(encoding="utf-8"))


# O3 (SCIENCE_CANDIDATE_SNIPPETS): one snippet for the approved term each
# candidate qualifies, and an identity block that lists only the base classes and
# the classes the candidates touch.
def candidate_snippets(candidates, semantic):
    """What the approved registry says about the term each QUALIFIES candidate names."""
    out = {}
    for candidate in candidates:
        term = candidate.get("qualifies")
        if not term or term in out:
            continue
        if term in semantic.class_metadata:
            meta = semantic.class_metadata[term]
            out[term] = {
                "class": term,
                "ancestors": lineage(term, semantic)[1:],
                "aliases": sorted(meta.get("query_terms") or []),
            }
        elif term in semantic.relations:
            definition = semantic.relations[term]
            out[term] = {
                "relation": term,
                "domain": list(getattr(definition, "domain", None) or []),
                "range": list(getattr(definition, "range", None) or []),
            }
    return [out[k] for k in sorted(out)]
