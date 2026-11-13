"""Validation of an entity proposal."""

import os
import re

from nasa_fire_ai.ingestion.clause_cues import strip_frames
from nasa_fire_ai.ingestion.document_structure import identity
from nasa_fire_ai.ingestion.printed_layout import (
    acronym_printed_form,
    background_or_analysis_span,
    caption_head,
    caption_only_label,
    caption_reader_enabled,
    heading_outline_name,
)
from nasa_fire_ai.ingestion.quantity_naming import (
    qualified_material_heading,
)
from nasa_fire_ai.ingestion.source_spans import (
    contiguous_support,
    locate,
    mentions,
    normalized,
)
from nasa_fire_ai.ingestion.subject_recognition import (
    has_class,
    material_tested_here,
    test_medium_only,
)

# SCIENCE_STANDARD_DESIGNATION: a standard or test method is a document, not a family of experiments
# (the ontology keeps them apart: fs:NASAStandard is a Publication). The form of a designation is
# fixed by the drafting rules for references to standards (ISO/IEC Directives, Part 2): the issuing
# body (capitals), the type of document (capitals, optional), the number (digits, with a part or an
# edition suffix). No body is listed. A label that is such a designation, alone or followed by the
# word method, test or procedure and a number, is not an ExperimentFamily; a bare "Test 1", a
# mixed-case product name or an equipment model followed by its noun is not a designation.
DESIGNATION = re.compile(
    r"^\s*[A-Z]{2,8}(?:[-\s]+(?:[A-Z]{1,4})(?=[-\s]*\d|[-\s]+[A-Z]{1,4}\b))*"
    r"[-\s]*[A-Z]{0,2}\d{1,6}[A-Za-z]?(?:[-.:]\d{1,4})*"
    r"(?:\s+(?:test\s+method|method|test|procedure|standard)(?:\s+\d+)?)?\s*$",
    re.IGNORECASE | re.ASCII,
)


def standard_designation_enabled():
    return os.getenv("SCIENCE_STANDARD_DESIGNATION", "1") != "0"


def is_standard_designation(label):
    """Whether a label has the form of a reference to a standard (issuing body, number)."""
    text = label or ""
    # The issuing body is written in capitals; a lower-case or mixed-case first word is a name.
    first = re.match(r"\s*([A-Za-z]+)", text)
    return bool(
        first and first.group(1).isupper() and len(first.group(1)) >= 2 and DESIGNATION.match(text)
    )


UNKNOWN_STUDY_EXEMPT = frozenset({"Material", "GravityCondition", "CombustionPhenomenon"})


def evidence_veto_entities():
    """SCIENCE_EVIDENCE_VETO_ENTITIES (on by default; =0 turns it off): the entity and relation vetoes that read
    the quote (often the bare label) read the printed line(s) around the located span."""
    return os.getenv("SCIENCE_EVIDENCE_VETO_ENTITIES", "1") != "0"


def printed_reading(spans, evidence, record):
    """The spans widened to their printed line(s) (flag on), else the spans themselves. A span
    that cannot be placed in its evidence is read by no veto: the record is held."""
    if not evidence_veto_entities():
        return spans
    from nasa_fire_ai.ingestion.quantity_validation import printed_span

    wide = [printed_span(s, evidence) for s in spans]
    if None in wide:
        record["status"] = "UNRESOLVED"
        if "ENTITY_PRINTED_LINE_NOT_LOCATED" not in record["reasons"]:
            record["reasons"].append("ENTITY_PRINTED_LINE_NOT_LOCATED")
        return [w or s for s, w in zip(spans, wide, strict=True)]
    return wide


def validate_entity(
    item, record, spans, entities, document, semantic, evidence, package, ambiguous_keys
):
    """Validate one entity proposal; raises on rejection."""
    from nasa_fire_ai.ingestion.numeric_expressions import split_embedded_unit

    if item["key"] in ambiguous_keys:
        raise ValueError("AMBIGUOUS_ENTITY_KEY")
    from nasa_fire_ai.ingestion.table_continuity import (
        printed_label_forms,
        row_group_identity,
    )

    printed = row_group_identity(item["label"], document)
    if (
        printed
        and printed["footnote_marker"]
        and normalized(item["label"]) != normalized(printed["group_label"])
    ):
        # "aAlpha (Lot 1)": a legend-backed footnote marker printed
        # with a row group label is an annotation, not the name.
        record["label_normalization"] = {
            "original_label": item["label"],
            "label": re.sub(r"\s+", " ", printed["group_label"]),
            "footnote_marker": printed["footnote_marker"],
            "footnote_legend": printed["footnote_legend"],
            "basis": "LEGEND_BACKED_FOOTNOTE_MARKER_ON_ROW_GROUP_LABEL",
        }
        item["label"] = record["label_normalization"]["label"]
    if item["class_id"] == "Material" and qualified_material_heading(
        item["label"], document, semantic
    ):
        raise ValueError("SCOPED_RESULT_HEADING_IS_NOT_MATERIAL_SUBSTANCE")
    if item["class_id"] == "GravityCondition" and re.search(
        r"\b(?:experiments?|tests?|groups?|runs?|stud(?:y|ies)|samples?|results?|comparison|updates?)\b",
        item["label"],
        re.IGNORECASE,
    ):
        raise ValueError("EXPERIMENT_NAME_IS_NOT_GRAVITY_CONDITION")
    if (
        item["class_id"] == "Sample"
        and re.search(
            r"\b(?:photos?|images?|videos?|records?|data)\b",
            item["label"],
            re.IGNORECASE,
        )
    ) or (
        item["class_id"] == "Material"
        and re.search(
            r"\b(?:locker|apparatus|assembly|camera|hardware)\b",
            item["label"],
            re.IGNORECASE,
        )
    ):
        record["status"] = "UNRESOLVED"
        record["reasons"].append("ENTITY_TYPE_SOURCE_ROLE_UNRESOLVED")
    if item["class_id"] in {"ExperimentFamily", "ExperimentalCondition"} and (
        (
            re.search(
                r"\b(?:facility|facilities|tower|centrifuge|tunnel|laboratory|lab"
                r"|test\s+cell|chamber|apparatus|tester|rig)\b(?:\s*\([^()]*\))*\s*$",
                item["label"],
                re.IGNORECASE,
            )
            and not re.search(
                r"\b(?:tests?|testing|experiments?|series|runs?)\b",
                item["label"],
                re.IGNORECASE,
            )
        )
        or (
            item["class_id"] == "ExperimentFamily"
            and re.search(
                r"\b(?:overview|methodology|solutions?|strategy|assessment|background"
                r"|introduction|summary|conclusions?|status|objectives?|approach|plan)\s*$",
                item["label"],
                re.IGNORECASE,
            )
        )
    ):
        # "DTC 3.0 second free-fall shaft", "Testing Methodology": an
        # apparatus or a document's own section title, not a group.
        record["status"] = "UNRESOLVED"
        record["reasons"].append("APPARATUS_OR_SECTION_TITLE_IS_NOT_EXPERIMENT_GROUP")
    if item["class_id"] == "Sample" and re.fullmatch(
        r"(?:the\s+|a\s+|an\s+)?(?:(?:non-?)?(?:reacting|reactive|reacted|burned|burnt"
        r"|unburned|circular|round|square|tested|untested|pre-?test|post-?test|typical"
        r"|single|individual|other|another|same|first|second|third|last|new|previous)\s+)"
        r"{1,2}(?:samples?|specimens?|coupons?)",
        item["label"].strip(),
    ):
        # "reacting sample", "circular sample": a description of
        # some specimen, not a specimen or group the source names.
        record["status"] = "UNRESOLVED"
        record["reasons"].append("GENERIC_DESCRIPTION_IS_NOT_A_SPECIMEN_IDENTITY")
    from nasa_fire_ai.ingestion.study_attribution import cited_attribution_nearby

    reading = printed_reading(spans, evidence, record)
    if (
        item.get("study") == "current"
        and has_class(item["class_id"], "ExperimentalCondition", semantic)
        and spans
        and all(cited_attribution_nearby([s], document) for s in reading)
    ):
        # "Their measurements suggest ... at room pressure": a condition
        # of the cited work, not of this study.
        record["status"] = "UNRESOLVED"
        record["reasons"].append("CONDITION_NAMED_ONLY_IN_CITED_WORK")
    if item["class_id"] == "ExperimentalCondition" and re.search(
        r"(?:\bmechanical\s+impact|\bimpact\s+test\w*|\btest\s+\d+|\btest\s+program\w*"
        r"|\bstandard|\bstd\b.*|\bignition\s+temperature"
        r"(?:\s*\(\s*AIT\s*\))?|\bheat\s+of\s+combustion|\btests?|\btesting|\btesters?)\s*$",
        item["label"],
        re.IGNORECASE,
    ):
        # A test method or a measured property is not a state the
        # experiment was held in ("heat of combustion").
        record["status"] = "UNRESOLVED"
        record["reasons"].append("TEST_OR_PROPERTY_IS_NOT_A_CONDITION")
    if item["class_id"] == "Intervention" and re.search(
        r"\b(?:calorimeters?|heaters?|wires?|plummets?|testers?|chambers?|apparatus"
        r"|assembly|camera|hardware|instruments?|tests?|tube|cup|vessel|valve)\b",
        item["label"],
        re.IGNORECASE,
    ):
        # An instrument or a test method is not an action applied
        # to the experiment ("ignition wire", "Drop Hammer Test").
        record["status"] = "UNRESOLVED"
        record["reasons"].append("APPARATUS_OR_METHOD_IS_NOT_AN_INTERVENTION")
    if (
        item["class_id"] == "Material"
        and item.get("study") == "current"
        and test_medium_only(item["label"], reading)
        and not material_tested_here(item["label"], document)
    ):
        # "pressurized with GOX", "submerged in LOX", "cooled with
        # Nitrogen": the medium of the test, not a material tested.
        record["status"] = "UNRESOLVED"
        record["reasons"].append("TEST_MEDIUM_IS_NOT_A_TESTED_MATERIAL")
    if item["class_id"] not in semantic.class_metadata:
        record["status"] = "UNRESOLVED"
        record["reasons"].append("UNREGISTERED_CLASS_NEEDS_SEMANTIC_REVIEW")
    if item["class_id"] == "ExperimentFamily" and (
        (
            bool(caption_head(item["label"]))
            if caption_reader_enabled()
            else re.match(
                r"(?:Figure|Fig\.?|Table)\s*(?:[-–—]\s*\d+|\d+\s*[-–—:.])",
                item["label"],
                re.IGNORECASE,
            )
        )
        # The label is the body of a printed caption ("Figure 4:
        # Wool blend cloth (Brand-Q), 6.5 kPa limiting oxygen data").
        or caption_only_label(item["label"], evidence)
        # An environment is a condition, not a family of experiments.
        or (
            re.search(
                r"\b(?:environment|atmosphere|gravity|flow)\s*$",
                item["label"],
                re.IGNORECASE,
            )
            and not re.search(
                r"\b(?:tests?|testing|experiments?|series|campaign|program)\b",
                item["label"],
                re.IGNORECASE,
            )
        )
    ):
        record["status"] = "UNRESOLVED"
        record["reasons"].append("CAPTION_IS_NOT_ESTABLISHED_EXPERIMENT_IDENTITY")
    if (
        item["class_id"] == "ExperimentFamily"
        and re.match(r"Phase\s+(?:\d+|[IVX]+)\b", item["label"], re.IGNORECASE)
        and any(
            re.search(
                r"\b(?:strategy|roadmap|planned|will|if)\b",
                s["quote"],
                re.IGNORECASE,
            )
            for s in reading
        )
        and not any(
            re.search(
                r"\b(?:tests?|experiments?|samples?|specimens?)\s+(?:was|were)\s+(?:performed|conducted|tested|burned)\b",
                s["quote"],
                re.IGNORECASE,
            )
            for s in reading
        )
    ):
        record["status"] = "UNRESOLVED"
        record["research_execution_role"] = "STRATEGIC_OR_PLANNED_PHASE"
        record["reasons"].append("STRATEGIC_PHASE_IS_NOT_ESTABLISHED_EXPERIMENT_GROUP")
    if item["class_id"] == "Sample" and re.fullmatch(
        r"(?:thin(?:ner)?|thick(?:er)?|several|various|different|candidate)\s+(?:materials?|samples?|specimens?|fuels?)",
        item["label"],
        re.IGNORECASE,
    ):
        record["status"] = "UNRESOLVED"
        record["reasons"].append("ENTITY_TYPE_SOURCE_ROLE_UNRESOLVED")
    if item["study"] == "current" and any(
        re.search(
            r"\b(?:previous|prior|earlier|cited)\s+(?:stud(?:y|ies)|work|experiments?|tests?)\s+"
            + re.escape(item["label"])
            + r"\b",
            s["quote"],
            re.IGNORECASE,
        )
        for s in reading
    ):
        raise ValueError("CITED_RESEARCH_IS_NOT_CURRENT_EXPERIMENT")
    if (
        item["study"] == "current"
        and item["class_id"] in {"Investigation", "ExperimentFamily"}
        and any(
            re.search(
                re.escape(normalized(item["label"]))
                + r"\s+(?:(?:which|that)\s+)?(?:will\s+(?:fly|launch|test|investigate|study|perform|burn)|is\s+(?:planned|scheduled))\b",
                normalized(s["quote"]),
            )
            for s in reading
        )
    ):
        record["status"] = "UNRESOLVED"
        record["research_execution_role"] = "PLANNED_FUTURE_RESEARCH"
        record["reasons"].append("FUTURE_RESEARCH_IS_NOT_CURRENT_INVESTIGATION")
    label_spans = contiguous_support(spans, evidence)
    forms = printed_label_forms(item["label"], document)
    if not any(mentions(f, s["quote"]) for f in forms for s in label_spans):
        heading = next(
            (
                h
                for h in document.get("sections", [])
                if normalized(
                    re.sub(
                        r"^(?:\d+(?:\.\d+)*[.)]?|[A-Z][.)]|[IVXLCDM]+[.)])\s+",
                        "",
                        h.get("title", ""),
                    )
                )
                == normalized(item["label"])
            ),
            None,
        )
        outline = None if heading else heading_outline_name(item["label"], document)
        if outline:
            # The model copied the heading's outline marker ("B. ...");
            # the record keeps the printed name without it.
            heading = next(
                h
                for h in document.get("sections", [])
                if normalized(h.get("title", "")) == normalized(item["label"])
            )
            record["label_normalization"] = {
                "printed_label": item["label"],
                "basis": "HEADING_OUTLINE_MARKER_IS_NOT_PART_OF_THE_NAME",
            }
            item["label"] = outline
        # "MFV 4.1, unit 17" for the printed "Main Feed
        # Valve (MFV) 4.1, unit 17".
        acronym = (
            None
            if heading
            else acronym_printed_form(item["label"], [s["quote"] for s in label_spans])
        )
        if not heading and not acronym:
            raise ValueError("ENTITY_LABEL_ABSENT_FROM_SUPPORT")
    if not any(mentions(f, s["quote"]) for f in forms for s in label_spans) and acronym:
        record["label_normalization"] = {
            "original_label": item["label"],
            "label": acronym,
            "basis": "PRINTED_NAME_WITH_ITS_ACRONYM",
        }
        item["label"] = acronym
    elif not any(mentions(f, s["quote"]) for f in forms for s in label_spans):
        # "A. Omega Range Facility (ORF) Downward ... Trials":
        # the document's own section heading names the group.
        heading_spans = locate(
            [
                {
                    "evidence_id": heading["evidence_id"],
                    "quote": heading["title"],
                    "start": heading["start"],
                }
            ],
            evidence,
        )
        spans += heading_spans
        label_spans = heading_spans
        record["identity_support"] = "PRINTED_SECTION_HEADING"
    if not any(mentions(item["label"], s["quote"]) for s in spans):
        marked = [f for f in forms[1:] if any(mentions(f, s["quote"]) for s in spans)]
        if marked:
            # The page prints the name with its footnote marker.
            record["identity_support"] = {
                "basis": "LEGEND_BACKED_FOOTNOTE_MARKER_ON_ROW_GROUP_LABEL",
                "printed_form": marked[0],
                "footnote_marker": printed["footnote_marker"],
                "footnote_legend": printed["footnote_legend"],
            }
        else:
            record["identity_support"] = {
                "basis": "CONTIGUOUS_ORIGINAL_SOURCE_SPANS",
                "support": label_spans,
            }
    if (
        has_class(item["class_id"], "ExperimentalCondition", semantic)
        and item["class_id"] != "ExperimentalCondition"
    ):
        meta = semantic.class_metadata.get(item["class_id"], {})
        stem = re.sub(r"Condition$", "", meta.get("label") or item["class_id"])
        terms = [stem, *meta.get("query_terms", [])]
        approved_condition = item["class_id"] == "GravityCondition" and any(
            m.get("relation") == "hasGravityCondition"
            and normalized(item["label"])
            in {normalized(a) for a in [canonical, *m.get("aliases", [])]}
            for canonical, m in getattr(semantic, "entity_mentions", {}).items()
        )
        if not approved_condition and not any(mentions(t, item["label"]) for t in terms if t):
            record["status"] = "UNRESOLVED"
            record["reasons"].append("CONDITION_SUBTYPE_REQUIRES_SOURCE_OR_APPROVED_ALIAS")
    metadata = (
        package.get("source_provenance", {}).get("metadata", {})
        if package.get("source_provenance")
        else {}
    )
    names = []
    for affiliation in metadata.get("authorAffiliations", []):
        meta = affiliation.get("meta", {})
        names.extend(
            [
                meta.get("author", {}).get("name", ""),
                meta.get("organization", {}).get("name", ""),
            ]
        )
    tokens = lambda value: set(re.findall(r"\w+", normalized(value)))
    if any(tokens(item["label"]) == tokens(name) for name in names if name):
        raise ValueError("AUTHOR_OR_ORGANIZATION_IS_NOT_EXPERIMENTAL_SUBJECT")
    if item["class_id"] == "Investigation" and not (
        re.search(
            r"\b(?:investigation|experiment|study|project)\b",
            item["label"],
            re.IGNORECASE,
        )
        or any(
            re.search(
                re.escape(normalized(item["label"]))
                + r"\s+(?:investigation|experiment|study|project)\b",
                normalized(span["quote"]),
                re.IGNORECASE,
            )
            for span in spans
        )
        or normalized(item["label"]) == normalized(package.get("title", ""))
    ):
        record["status"] = "UNRESOLVED"
        record["reasons"].append("INVESTIGATION_TYPE_SOURCE_ROLE_UNRESOLVED")
    if re.search(
        r"\b(?:was|were|is|are|would|will|grows|increases|decreases|achieved|remains|indicating)\b",
        item["label"],
        re.IGNORECASE,
    ):
        record["status"] = "UNRESOLVED"
        record["reasons"].append("STATEMENT_IS_NOT_NAMED_ENTITY")
    # "72 ft-lbs (98J)" is a value with its unit, not a named
    # intervention, material or specimen. A bare number may
    # still be a run label ("Run 3"), so only value+unit counts.
    from nasa_fire_ai.normalization.units import interpret

    value_label = re.match(r"\s*[~<>≈]?\s*[-−]?\d[\d,]*(?:\.\d+)?\s*(?P<rest>.*)", item["label"])
    words = value_label["rest"].split() if value_label else []
    # "0.4 inches", "35 Joules of work", "7 degrees C/min":
    # the label opens with a value in an interpreted unit.
    opens_with_value = any(
        interpret(" ".join(words[:k]))
        # Only the value itself, "of <quantity>" or an equivalent may
        # follow; "100% aramid weave cloth" or "29% O2 at 61 kPa" name things.
        and re.fullmatch(r"(?:of\s+\w+)?\s*(?:\([^()]*\))?", " ".join(words[k:]))
        for k in range(1, min(3, len(words)) + 1)
    )
    if (split_embedded_unit(item["label"], None) or {}).get(
        "status"
    ) == "SPLIT" or opens_with_value:
        record["status"] = "UNRESOLVED"
        record["reasons"].append("NUMERIC_VALUE_IS_NOT_A_NAMED_ENTITY")
    eid = (
        package["id"]
        + ":entity:"
        + identity(
            [
                spans[0]["source_id"],
                item["class_id"],
                normalized(item["label"]),
                item["study"],
                item["key"] if item["class_id"] == "Sample" else None,
            ]
        )[:20]
    )
    relation = {
        "Material": "hasMaterial",
        "GravityCondition": "hasGravityCondition",
    }.get(item["class_id"])
    approved = (
        [
            canonical
            for canonical, meta in getattr(semantic, "entity_mentions", {}).items()
            if meta.get("relation") == relation
            and normalized(item["label"])
            in {normalized(a) for a in [canonical, *meta.get("aliases", [])]}
        ]
        if relation
        else []
    )
    if len(approved) == 1:
        eid = approved[0]
        record["mapping"] = {
            "kind": "approved_alias_reuse",
            "existing": eid,
            "raw_label": item["label"],
            "activation": "NONE",
        }
    record["entity_id"] = eid
    if item["key"] in entities and entities[item["key"]]["id"] != eid:
        raise ValueError("AMBIGUOUS_ENTITY_KEY")
    entities[item["key"]] = {
        **item,
        "id": eid,
        "source_id": spans[0]["source_id"],
        "spans": spans,
    }
    # The spans now include any heading support added above.
    planned_reading = printed_reading(spans, evidence, record)
    if item["class_id"] == "ExperimentalRun" and any(
        re.search(
            r"\b(?:planned|proposed|cancelled|canceled|not\s+(?:performed|conducted)|pre[- ]test\s+flow\s+vis\w*)\b",
            # "as planned" says a run went as planned, not that it was one.
            strip_frames(s["quote"]),
            re.IGNORECASE,
        )
        for s in planned_reading
    ):
        raise ValueError("DOCUMENTARY_OR_PLANNED_IS_NOT_EXECUTED_RUN")
    if item["class_id"] == "ExperimentalRun" and not any(
        re.search(
            r"\b(?:run|test|case)\s+(?:(?:number|no\.?|#)\s*)?" + re.escape(item["label"]) + r"\b",
            normalized(s["quote"]),
            re.IGNORECASE,
        )
        for s in spans
    ):
        record["status"] = "UNRESOLVED"
        record["reasons"].append("ENTITY_TYPE_SOURCE_ROLE_UNRESOLVED")
    if item["class_id"] == "ExperimentalRun" and not any(
        re.search(
            r"\b(?:tested|performed|conducted|burned|measured|observed|ignited|recorded)\b",
            s["quote"],
            re.IGNORECASE,
        )
        for s in spans
    ):
        record["status"] = "UNRESOLVED"
        record["reasons"].append("EXECUTION_NOT_DOCUMENTED")
    if (
        standard_designation_enabled()
        and item["class_id"] == "ExperimentFamily"
        and is_standard_designation(item["label"])
    ):
        # "NASA STD 6001 Test 1" names a standard test method: a document, not a family of runs.
        record["status"] = "UNRESOLVED"
        record["reasons"].append("EXPERIMENT_FAMILY_IS_A_STANDARD_DESIGNATION")
        record["class_hint"] = "NASAStandard"
    if item["study"] == "unknown" and item["class_id"] not in UNKNOWN_STUDY_EXEMPT:
        record["status"] = "UNRESOLVED"
        record["reasons"].append("CURRENT_OR_CITED_STUDY_UNRESOLVED")
    if (
        item["class_id"] not in {"Investigation", "Material"}
        and item["study"] != "cited"
        and spans
        and all(background_or_analysis_span(s, document) for s in spans)
    ):
        # Named only in background, theory or analysis: a concept the
        # paper discusses, not an entity of its own experiment.
        record["status"] = "UNRESOLVED"
        record["reasons"].append("SUPPORT_ONLY_IN_BACKGROUND_OR_ANALYSIS_SECTION")
    if item["study"] in {"current", "cited"} and item["class_id"] in {
        "Material",
        "Sample",
    }:
        from nasa_fire_ai.ingestion.table_continuity import (
            group_lineage,
            material_row_labels,
        )

        lineage = group_lineage(material_row_labels(item["label"], document), document)
        # A comparator printed only in cited or externally
        # sourced table rows was not established as tested here;
        # one printed only in this study's rows is not only cited.
        if item["study"] == "current" and lineage and lineage["status"] == "CITED_OR_EXTERNAL_ONLY":
            record["status"] = "UNRESOLVED"
            record["reasons"].append("CURRENT_STUDY_LINEAGE_NOT_ESTABLISHED")
            record["lineage_context"] = lineage
        if item["study"] == "cited" and lineage and lineage["status"] == "NOT_CONTRADICTED":
            record["status"] = "UNRESOLVED"
            record["reasons"].append("CITED_STUDY_CONTRADICTED_BY_CURRENT_TABLE_ROWS")
            record["lineage_context"] = lineage
