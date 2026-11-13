"""Statement provenance: where a statement says its data come from."""

import re

from nasa_fire_ai.ingestion.abbreviations import segmentation_view
from nasa_fire_ai.ingestion.clause_cues import ENDOPHORIC_MARKER, SELF_DEIXIS, heads_object_of_from
from nasa_fire_ai.ingestion.printed_layout import background_or_analysis_span
from nasa_fire_ai.ingestion.scientific_facets import PROVENANCE_ROLE
from nasa_fire_ai.ingestion.scientific_scope import document_investigation
from nasa_fire_ai.ingestion.source_spans import mentions, normalized
from nasa_fire_ai.ingestion.subject_recognition import applicable

# Classes a data source may take: the registered source classes, or a staged class
# whose proposed parent is one of them.
PROVENANCE_SOURCE_CLASSES = ("Publication", "Document")


def source_class(record):
    """The source class an entity record has, or None."""
    cls = record["proposal"]["class_id"]
    if cls in PROVENANCE_SOURCE_CLASSES:
        return cls
    parent = (record.get("proposed_term") or {}).get("parent")
    return cls if parent in PROVENANCE_SOURCE_CLASSES else None


def provenance_source_ok(key, records):
    """Whether the entity is a source entity (registered or staged under one) that is
    supported or only waiting for its class to be reviewed."""
    from nasa_fire_ai.ingestion.proposal_states import proposal_state

    return any(
        r["kind"] == "entities"
        and r["proposal"].get("key") == key
        and not r.get("duplicate_of")
        and source_class(r)
        and proposal_state(r) in {"SOURCE_SUPPORTED", "PROPOSED_ONTOLOGY_EXTENSION"}
        for r in records
    )


# The prompt's example sentence; it must satisfy the provenance reader itself.
PROVENANCE_EXAMPLE = "The reference char depth values were obtained from the Marlow panel survey."


def provenance_clause_ok(label, quote):
    """Whether the quote prints the label as what the data were obtained from: after
    the provenance verb, in the same clause, behind "from"; never a pointer
    (Table, Figure ...) and never the object of a method ("from the method of X")."""
    from nasa_fire_ai.ingestion.statement_integrity import DATA_PROVENANCE

    if ENDOPHORIC_MARKER.search(label or ""):
        return False
    for m in DATA_PROVENANCE.finditer(quote):
        # The clause ends at a period that is not an abbreviation's: found on the masked
        # quote, cut from the printed one.
        piece = re.split(r"[.;]", segmentation_view(quote)[m.end() :], maxsplit=1)[0]
        tail = quote[m.end() : m.end() + len(piece)]
        found = re.search(r"\bfrom\b", tail, re.IGNORECASE)
        if not found:
            continue
        rest = normalized(tail[found.end() :])
        at = rest.find(normalized(label))
        if at >= 0 and mentions(label, rest) and heads_object_of_from(rest[:at]):
            return True
    return False


def self_source(key, entities):
    """Whether the source is the current document itself ("the present report", its
    own title), whatever study the model marked it with."""
    from nasa_fire_ai.ingestion.relation_contracts import EXPERIMENT_CLASSES

    label = entities[key]["label"]
    return bool(SELF_DEIXIS.search(normalized(label))) or any(
        e["class_id"] in EXPERIMENT_CLASSES
        and e["study"] == "current"
        and (mentions(e["label"], label) or mentions(label, e["label"]))
        for e in entities.values()
    )


def provenance_source_printed(key, spans, entities, document, evidence=None):
    """The source is the object of the provenance clause, is not a pointer, a method
    or the document itself, and the passage is not cited or background work."""
    from nasa_fire_ai.ingestion.study_attribution import cited_attribution_nearby

    label = entities[key]["label"]
    if self_source(key, entities) or not any(
        provenance_clause_ok(label, sp["quote"]) for sp in spans
    ):
        return False

    def unmarked(sp):
        return {
            **sp,
            "quote": re.sub(
                re.escape(label) + r"\s*\[\d+(?:\s*[,–-]\s*\d+)*\]",
                label,
                sp["quote"],
                flags=re.IGNORECASE,
            ),
        }

    reading = spans
    if evidence is not None:
        # SCIENCE_EVIDENCE_VETO_ENTITIES: the cited and background vetoes read the printed
        # line(s) around each span; a span that cannot be placed is not read (not accepted).
        from nasa_fire_ai.ingestion.entity_validation import evidence_veto_entities
        from nasa_fire_ai.ingestion.quantity_validation import printed_span

        if evidence_veto_entities():
            reading = [printed_span(sp, evidence) for sp in spans]
            if None in reading:
                return False
    return not cited_attribution_nearby([unmarked(sp) for sp in reading], document) and not any(
        background_or_analysis_span(sp, document) for sp in reading
    )


def provenance_source_staged(key, records):
    from nasa_fire_ai.ingestion.proposal_states import proposal_state

    return any(
        r["kind"] == "entities"
        and r["proposal"].get("key") == key
        and proposal_state(r) == "PROPOSED_ONTOLOGY_EXTENSION"
        for r in records
    )


def structure_provenance(records, entities, document):
    """A data_provenance statement counts only with its structure: a printed source
    entity of a source class, a provenance relation from the current study to it (a
    staged one is never approved here) and applicability. Otherwise it is held."""
    from nasa_fire_ai.ingestion.proposal_states import proposal_state
    from nasa_fire_ai.ingestion.relation_contracts import EXPERIMENT_CLASSES

    ok = {"SOURCE_SUPPORTED", "PROPOSED_ONTOLOGY_EXTENSION"}
    sources = {
        r["proposal"]["key"]: r
        for r in records
        if r["kind"] == "entities"
        and not r.get("duplicate_of")
        and source_class(r)
        and proposal_state(r) in ok
        and r["proposal"]["study"] != "current"
    }
    relations = [
        r
        for r in records
        if r["kind"] == "relations" and r["status"] != "REJECTED" and proposal_state(r) in ok
    ]

    def overlap(a, b):
        return any(
            x["evidence_id"] == y["evidence_id"]
            and x["start"] < y["start"] + len(y["quote"])
            and y["start"] < x["start"] + len(x["quote"])
            for x in a
            for y in b
        )

    counted = set()
    for st in records:
        if (
            st["kind"] != "statements"
            or st["proposal"].get("epistemic") != PROVENANCE_ROLE
            or st["status"] == "REJECTED"
            or st.get("duplicate_of")
        ):
            continue
        spans = st["support_spans"]
        quotes = [s["quote"] for s in spans]
        found = [
            k
            for k, e in sources.items()
            if any(mentions(e["proposal"]["label"], q) for q in quotes)
            and k in entities
            and provenance_source_printed(k, spans, entities, document)
        ]
        links = [
            r
            for r in relations
            if r["proposal"]["object"] in found
            and r["proposal"]["subject"] in entities
            and entities[r["proposal"]["subject"]]["class_id"] in EXPERIMENT_CLASSES
            and entities[r["proposal"]["subject"]]["study"] == "current"
            and overlap(r["support_spans"], spans)
        ]
        link = links[0] if links else None
        # The study the provenance is about: the relation's, else the statement's own.
        study_key = (
            link["proposal"]["subject"]
            if link
            else next((k for k in st["proposal"].get("subjects") or [] if k in entities), None)
        )
        applies = (
            study_key is not None
            and st["proposal"]["study"] == "current"
            and (
                applicable(study_key, spans, entities, document)
                or document_investigation(spans, entities, document, own_body=True) == study_key
                or (link and (link.get("context_resolution") or {}).get("basis"))
                == "STUDY_DATA_SOURCE_PRINTED"
            )
        )
        missing = [
            name
            for name, present in (
                ("source_entity", found),
                ("relation", links),
                ("applicability", applies),
            )
            if not present
        ]
        if missing:
            st["status"] = "UNRESOLVED"
            st["reasons"].append("PROVENANCE_STRUCTURE_MISSING")
            st["provenance_structure_missing"] = missing
            continue
        if st["status"] != "SOURCE_SUPPORTED":
            # Held for another reason: it carries no structure and binds no relation.
            continue
        counted.add(link["id"])
        source = sources[link["proposal"]["object"]]
        staged_relation = proposal_state(link) == "PROPOSED_ONTOLOGY_EXTENSION"
        staged_source = proposal_state(source) == "PROPOSED_ONTOLOGY_EXTENSION"
        st["provenance_structure"] = {
            "source_entity": link["proposal"]["object"],
            "source_class": source["proposal"]["class_id"],
            "source_state": "STAGED" if staged_source else "APPROVED",
            "relation": link["id"],
            "relation_term": link["proposal"]["relation"],
            "relation_state": "STAGED" if staged_relation else "APPROVED",
            "study_entity": link["proposal"]["subject"],
            "basis": "SOURCE_ENTITY_AND_PROVENANCE_RELATION_IN_SAME_SPAN",
        }
    for r in records:
        # A relation bound only by the provenance clause counts with a counted statement.
        if (
            r["kind"] == "relations"
            and (r.get("context_resolution") or {}).get("basis") == "STUDY_DATA_SOURCE_PRINTED"
            and r["id"] not in counted
        ):
            r["status"] = "UNRESOLVED"
            r["reasons"].append("PROVENANCE_STRUCTURE_MISSING")
