"""Validation of a relation proposal."""

import re

from nasa_fire_ai.ingestion.clause_cues import setting_mention
from nasa_fire_ai.ingestion.printed_layout import (
    group_section_support,
)
from nasa_fire_ai.ingestion.quantity_naming import (
    heading_binding,
)
from nasa_fire_ai.ingestion.relation_contracts import RELATION_ENDPOINTS
from nasa_fire_ai.ingestion.scientific_facets import (
    structured_provenance_enabled,
)
from nasa_fire_ai.ingestion.scientific_scope import (
    document_investigation,
    subject_label_names_material,
)
from nasa_fire_ai.ingestion.source_spans import (
    locate,
    mentions,
    normalized,
)
from nasa_fire_ai.ingestion.statement_provenance import (
    provenance_source_ok,
    provenance_source_printed,
    provenance_source_staged,
)
from nasa_fire_ai.ingestion.structural_candidates import (
    tested_at_clauses,
)
from nasa_fire_ai.ingestion.subject_recognition import (
    applicable,
    has_class,
    local_binding,
)


def validate_relation(
    item, record, spans, entities, document, semantic, evidence, package, records
):
    """Validate one relation proposal; raises on rejection."""
    if item["subject"] not in entities or item["object"] not in entities:
        raise ValueError("UNKNOWN_RELATION_ENDPOINT")
    if (
        entities[item["subject"]]["source_id"] != spans[0]["source_id"]
        or entities[item["object"]]["source_id"] != spans[0]["source_id"]
    ):
        raise ValueError("CROSS_SOURCE_ATTRIBUTION")
    if (
        entities[item["object"]]["class_id"]
        in {"Investigation", "ExperimentalRun", "ExperimentFamily", "Sample"}
        and entities[item["subject"]]["study"] != entities[item["object"]]["study"]
    ):
        raise ValueError("CURRENT_CITED_ATTRIBUTION_CONTRADICTION")
    endpoint_types = RELATION_ENDPOINTS
    if item["relation"] in endpoint_types and not all(
        any(
            has_class(entities[item[endpoint]]["class_id"], cls, semantic)
            or (
                cls == "GravityCondition"
                and entities[item[endpoint]]["class_id"] == "ExperimentalCondition"
                and any(
                    meta.get("relation") == "hasGravityCondition"
                    and normalized(entities[item[endpoint]]["label"])
                    in {normalized(a) for a in [canonical, *meta.get("aliases", [])]}
                    for canonical, meta in getattr(semantic, "entity_mentions", {}).items()
                )
            )
            for cls in expected
        )
        for endpoint, expected in zip(
            ("subject", "object"), endpoint_types[item["relation"]], strict=True
        )
    ):
        raise ValueError("RELATION_ENDPOINT_CLASS_CONTRADICTION")
    binding = heading_binding(item, spans, entities, document, semantic)
    if binding:
        record["context_resolution"] = binding
        spans += locate(binding["support"], evidence)
    if not binding and item["relation"] == "madeOf":
        # "Alpha (Lot 1)" or "Alpha samples" are made of Alpha by
        # construction of their printed name.
        named = subject_label_names_material(
            entities[item["subject"]]["label"], entities[item["object"]]["label"]
        )
        if named:
            binding = {"status": "SUPPORTED", **named}
            record["context_resolution"] = binding
    if (
        not binding
        and item["relation"] == "hasMaterial"
        and entities[item["subject"]]["class_id"] in {"ExperimentFamily", "ExperimentalRun"}
        and mentions(entities[item["object"]]["label"], entities[item["subject"]]["label"])
    ):
        # "Initial Hexane Wet MFV Manifold Drop Test Series":
        # the group's own printed name says which material it used.
        binding = {
            "status": "SUPPORTED",
            "basis": "GROUP_NAME_NAMES_ITS_MATERIAL",
            "material_label": entities[item["object"]]["label"],
        }
        record["context_resolution"] = binding
    if (
        not binding
        and item["relation"] == "usesSample"
        and entities[item["subject"]]["class_id"] == "Investigation"
        and normalized(entities[item["subject"]]["label"])
        == normalized(document.get("package_title", ""))
        and any(
            re.search(
                r"\b(?:tested|evaluated|examined)\s+(?:was|were)\s+(?:the\s+)?"
                + re.escape(normalized(entities[item["object"]]["label"])),
                normalized(s["quote"]),
            )
            for s in spans
        )
    ):
        # "The valve under test was the Main Feed Valve (MFV)
        # 4.1": the paper names the specimen its own investigation used.
        binding = {
            "status": "SUPPORTED",
            "basis": "DOCUMENT_STATES_THE_SPECIMEN_IT_TESTED",
        }
        record["context_resolution"] = binding
    if (
        not binding
        and item["relation"] == "hasCondition"
        and entities[item["subject"]]["study"] == entities[item["object"]]["study"]
    ):
        from nasa_fire_ai.ingestion.table_continuity import (
            group_rows_printing,
            label_variants,
        )

        rows = group_rows_printing(
            label_variants(entities[item["subject"]]["label"], document),
            entities[item["object"]]["label"],
            document,
        )
        if rows:
            # The subject's own printed rows carry this condition.
            binding = {
                "status": "SUPPORTED",
                "basis": "SUBJECT_TABLE_ROWS_PRINT_CONDITION",
                "rows": rows,
            }
            record["context_resolution"] = binding
    if (
        not binding
        and item["relation"] == "hasCondition"
        and entities[item["object"]].get("validation_status") == "SOURCE_SUPPORTED"
    ):
        # The condition is printed under the heading that names the
        # subject group, or in the clause that says the subject was
        # "tested at" it.
        printed = [
            s for s in spans if setting_mention(entities[item["object"]]["label"], s["quote"])
        ]
        proof = group_section_support(
            item["subject"],
            entities[item["object"]].get("spans", []),
            entities,
            document,
        ) or next(
            (
                found
                for s in printed
                if (found := group_section_support(item["subject"], [s], entities, document))
            ),
            [],
        )
        clause = next(
            (
                c
                for _e, _s, c in tested_at_clauses(
                    entities[item["subject"]]["label"],
                    {e: v["text"] for e, v in evidence.items()},
                )
                if mentions(entities[item["object"]]["label"], c)
            ),
            None,
        )
        if proof:
            binding = {
                "status": "SUPPORTED",
                "basis": "SUBJECT_SUBSECTION_PRINTS_CONDITION",
                "support": proof,
            }
        elif clause:
            binding = {
                "status": "SUPPORTED",
                "basis": "SUBJECT_PRINTED_TESTED_AT_CONDITION",
                "clause": clause.strip(),
            }
        if binding:
            record["context_resolution"] = binding
    if (
        not binding
        and item["relation"] == "belongsToInvestigation"
        and entities[item["object"]]["class_id"] == "Investigation"
        and entities[item["subject"]]["study"] == "current"
        and entities[item["object"]]["study"] == "current"
        and normalized(entities[item["object"]]["label"]) == normalized(package.get("title", ""))
    ):
        deixis = [
            sp
            for sp in spans
            if re.search(
                re.escape(normalized(entities[item["subject"]]["label"]))
                + r"\s+(?:discussed|described|tested|evaluated|studied)\s+in\s+this\s+(?:paper|study|report|work|investigation)\b",
                normalized(sp["quote"]),
            )
        ]
        if deixis:
            # "the coupons described in this paper": this document's own study.
            binding = {
                "status": "SUPPORTED",
                "basis": "SUBJECT_DISCUSSED_IN_THIS_DOCUMENT",
                "support": [{k: deixis[0][k] for k in ("evidence_id", "quote", "start")}],
            }
            record["context_resolution"] = binding
    if item["relation"] == "hasGravityCondition" and not binding:
        from nasa_fire_ai.ingestion.document_context import gravity_binding

        binding = gravity_binding(
            item["subject"], item["object"], spans, entities, document, semantic
        )
        record["context_resolution"] = binding
        if binding["status"] == "CONTRADICTED":
            raise ValueError("LOCAL_SOURCE_CONTEXT_CONTRADICTS_PROPOSED_GRAVITY")
        if binding["status"] == "SUPPORTED":
            spans += locate(binding["support"], evidence)
    if (
        structured_provenance_enabled()
        and not binding
        and item["relation"] not in semantic.relations
        and entities[item["object"]]["study"] != "current"
        and provenance_source_ok(item["object"], records)
        and (
            applicable(item["object"], spans, entities, document)
            or provenance_source_staged(item["object"], records)
        )
        and provenance_source_printed(item["object"], spans, entities, document, evidence)
        and document_investigation(spans, entities, document, own_body=True) == item["subject"]
    ):
        from nasa_fire_ai.ingestion.statement_integrity import DATA_PROVENANCE

        if any(DATA_PROVENANCE.search(sp["quote"]) for sp in spans):
            binding = {
                "status": "SUPPORTED",
                "basis": "STUDY_DATA_SOURCE_PRINTED",
                "support": [{k: spans[0][k] for k in ("evidence_id", "quote", "start")}],
            }
            record["context_resolution"] = binding
    if not all(
        applicable(item[e], spans, entities, document) for e in ("subject", "object")
    ) and not (
        # The material is named inside the subject's own label.
        binding
        and binding.get("basis")
        in {
            "SUBJECT_LABEL_NAMES_MATERIAL",
            "SUBJECT_TABLE_ROWS_PRINT_CONDITION",
            "SUBJECT_SUBSECTION_PRINTS_CONDITION",
            "SUBJECT_PRINTED_TESTED_AT_CONDITION",
            "SUBJECT_DISCUSSED_IN_THIS_DOCUMENT",
            "STUDY_DATA_SOURCE_PRINTED",
        }
        and (
            applicable(item["subject"], spans, entities, document)
            # The heading or the "tested at" clause itself prints the
            # subject; its own anchor need not lie in these spans.
            or (
                binding.get("basis")
                in {
                    "SUBJECT_SUBSECTION_PRINTS_CONDITION",
                    "SUBJECT_PRINTED_TESTED_AT_CONDITION",
                    "STUDY_DATA_SOURCE_PRINTED",
                }
                and entities[item["subject"]].get("validation_status") == "SOURCE_SUPPORTED"
            )
        )
        and (
            entities[item["object"]].get("validation_status") == "SOURCE_SUPPORTED"
            # A staged source class is checked by provenance_source_ok.
            or binding.get("basis") == "STUDY_DATA_SOURCE_PRINTED"
        )
    ):
        raise ValueError("RELATION_SUBJECT_OBJECT_NOT_IN_APPLICABLE_SOURCE")
    # SCIENCE_EVIDENCE_VETO_ENTITIES: a rival subject is searched in the clause of the printed
    # line(s) that holds it (a trim drops it); the binding itself stays required in the quote.
    from nasa_fire_ai.ingestion.entity_validation import evidence_veto_entities

    lines = None
    if evidence_veto_entities():
        from nasa_fire_ai.ingestion.quantity_validation import printed_span

        lines = [printed_span(s, evidence) for s in spans]
    if not (binding and binding["status"] == "SUPPORTED") and not local_binding(
        item["subject"], entities[item["object"]]["label"], spans, entities, lines
    ):
        record["status"] = "UNRESOLVED"
        record["reasons"].append("LOCAL_SUBJECT_BINDING_UNRESOLVED")
    record["subject"] = entities[item["subject"]]["id"]
    record["object"] = entities[item["object"]]["id"]
    if item["relation"] not in semantic.relations:
        record["status"] = "UNRESOLVED"
        record["reasons"].append("UNREGISTERED_RELATION")
    # Co-occurrence is never proof, even for ontology-permitted edges.
    text = " ".join(s["quote"] for s in spans)
    predicates = {
        "hasMaterial": r"\b(?:made\s+(?:of|from)|burn(?:ing|ed)?|samples?\s+of|material)\b",
        "usesSample": r"\b(?:samples?|specimens?|tested\s+(?:was|were)|(?:was|were)\s+tested)\b",
        "hasGravityCondition": r"\b(?:conducted|performed|tested|tests?|experiments?)\b",
        "belongsToInvestigation": r"\b(?:part\s+of|belongs?\s+to|member\s+of|includes?|comprises?|consists?\s+of|conducted\s+(?:as|within))\b",
        "belongsToExperimentFamily": r"\b(?:part\s+of|belongs?\s+to|member\s+of|in\s+(?:group|series)|includes?|comprises?|consists?\s+of)\b",
        "hasCondition": r"\b(?:at|under|maintained|condition|with)\b",
        "hasIntervention": r"\b(?:introduced|initiated|applied|turned|shut|removed)\b",
    }
    if not (binding and binding["status"] == "SUPPORTED") and (
        item["relation"] not in predicates
        or not re.search(predicates[item["relation"]], text, re.IGNORECASE)
    ):
        record["status"] = "UNRESOLVED"
        record["reasons"].append("RELATION_ENTAILMENT_REQUIRES_REVIEW")
    # SCIENCE_EVIDENCE_VETO_ENTITIES: negation and exception are read in the printed line(s)
    # around each located span (a trim drops "not" or "except ..."); entailment above stays on
    # the quote, which is its required cue.
    from nasa_fire_ai.ingestion.entity_validation import printed_reading

    negation_text = " ".join(s["quote"] for s in printed_reading(spans, evidence, record))
    if not (binding and binding["status"] == "SUPPORTED") and re.search(
        r"\b(?:not|without|except|rather\s+than)\b", negation_text, re.IGNORECASE
    ):
        record["status"] = "UNRESOLVED"
        record["reasons"].append("NEGATION_OR_LOCAL_EXCEPTION_REQUIRES_REVIEW")
