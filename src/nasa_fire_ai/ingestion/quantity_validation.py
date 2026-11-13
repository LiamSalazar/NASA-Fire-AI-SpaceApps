"""Quantity validation: the subject a quantity may take and the checks that keep it."""

import copy
import os
import re

from nasa_fire_ai.ingestion.clause_cues import (
    execution,
    governing_clause,
    locate_value,
    printed_line_bounds,
)
from nasa_fire_ai.ingestion.printed_layout import (
    group_section_support,
    is_caption_line,
    section_for_span,
    subsection_group,
    table_column_prints_value,
    under_group_heading,
)
from nasa_fire_ai.ingestion.quantity_naming import (
    anaphoric_subject,
    applied_column_value,
    continued_sentence,
    explicit_quantity_derivation,
    model_printed_name,
    native_quantity_expression,
    printed_setting_name,
    printed_value_name,
    property_proposal,
    quantity_name_value_binding,
    resolve_source_property,
    setting_verb_of_unit_dimension,
    source_dimension_adjectives,
    staged_name_syntax,
    value_is_applied_input,
    value_sentences,
)
from nasa_fire_ai.ingestion.scientific_facets import ROLES, allowed_bases, facet_review, facets
from nasa_fire_ai.ingestion.scientific_scope import (
    document_statement_scope,
    original_derivation_context,
)
from nasa_fire_ai.ingestion.source_spans import locate, mentions, normalized
from nasa_fire_ai.ingestion.structural_candidates import METHOD_SECTION
from nasa_fire_ai.ingestion.subject_recognition import (
    SUBJECT_CLASSES,
    applicable,
    has_class,
    heading_names_subject,
    label_binding_enabled,
    local_binding,
    printed_label_binding,
    printed_subject_recognition,
    quantity_scope_eligible,
    tested_material_entity,
)


def evidence_veto_quantities():
    """SCIENCE_EVIDENCE_VETO_QUANTITIES (on by default; "0" turns it off): the quantity vetoes read the printed
    line(s) around the located span, never the model's quote alone."""
    return os.getenv("SCIENCE_EVIDENCE_VETO_QUANTITIES", "1") != "0"


def printed_span(span, evidence):
    """The span widened to the printed line(s) it touches (current splitter, no de-wrap), or
    ``None`` when it cannot be placed in its evidence text."""
    text = (evidence.get(span["evidence_id"]) or {}).get("text")
    start, end = span.get("start"), span.get("end")
    if (
        not isinstance(text, str)
        or not isinstance(start, int)
        or not isinstance(end, int)
        or not 0 <= start < end <= len(text)
        or text[start:end] != span.get("quote")
    ):
        return None
    lo, hi = printed_line_bounds(text, start, end)
    return {**span, "start": lo, "end": hi, "quote": text[lo:hi]}


def caption_span(span, evidence):
    """The printed line(s) of the span read from the first character of their first physical
    line: a caption head ("Figure 6.") is a property of the line start, which the sentence cut
    of the splitter can separate from the caption text."""
    wide = printed_span(span, evidence)
    if wide is None:
        return None
    text = evidence[span["evidence_id"]]["text"]
    lo = text.rfind("\n", 0, wide["start"]) + 1
    return {**wide, "start": lo, "quote": text[lo : wide["end"]]}


def _bare(line):
    """The line without its line ending."""
    return line.splitlines()[0] if line.splitlines() else ""


def own_lines(span, value_spans):
    """The lines of ``span`` that hold one of the record's own located value spans (the
    validator's placement of the value, tied to the record's provenance: a table cell stays in
    its table row). A value printed again on another line of the support (a caption that names
    the test pressure, say) is not this record's printed value, so a span that carries none of
    the record's value spans holds no line of the record. With no located value span, every
    line is read as before."""
    lines = span["quote"].splitlines(keepends=True)
    if not value_spans or not own_lines_enabled():
        return [_bare(line) for line in lines]
    mine = [
        (v["start"], v["end"])
        for v in value_spans
        if v.get("evidence_id") == span.get("evidence_id")
        and isinstance(v.get("start"), int)
        and isinstance(v.get("end"), int)
    ]
    kept, offset = [], span.get("start", 0)
    for line in lines:
        end = offset + len(line)
        if any(x < end and y > offset for x, y in mine):
            kept.append(_bare(line))
        offset = end
    return kept


def own_lines_enabled():
    """The caption hold reads the lines of the record's own value spans (on by default)."""
    return os.getenv("SCIENCE_QUANTITY_OWN_VALUE_LINES", "1") != "0"


def validate_quantity_subject(
    item,
    record,
    spans,
    entities,
    document,
    semantic,
    evidence,
    numeric_convention,
    subject_checks=True,
):
    """Validate one quantity proposal for its proposed subject; raises on rejection."""
    from nasa_fire_ai.ingestion.numeric_expressions import (
        parse_numeric_expression,
        same_expression,
        source_numeric_matches,
        split_embedded_unit,
    )

    # Facet cues are read in the clause that governs the value's own printed
    # position, never in a neighbouring clause or sentence. A value that cannot be
    # located gives no cue.
    located = next(
        (
            (s["quote"], offset)
            for s in spans
            if (offset := locate_value(s["quote"], item.get("expression"))) is not None
        ),
        None,
    )
    veto = evidence_veto_quantities()

    def printed_lines():
        # The printed line(s) of each span as they are now (spans grow with scope proofs).
        return [printed_span(s, evidence) for s in spans] if veto else None

    wide_spans = printed_lines()
    if veto and located:
        # The clause is read in the printed line(s) around the located span, not in the quote.
        index = next(
            i
            for i, s in enumerate(spans)
            if locate_value(s["quote"], item.get("expression")) is not None
        )
        wide = wide_spans[index]
        located = (
            (wide["quote"], located[1] + spans[index]["start"] - wide["start"]) if wide else None
        )
    if veto and None in wide_spans:
        # A span that cannot be placed in the evidence is read by no veto: held.
        record["status"] = "UNRESOLVED"
        record["reasons"].append("QUANTITY_PRINTED_LINE_NOT_LOCATED")
    if located:
        value_clause = governing_clause(*located)
        printed = execution(*located)
    else:
        value_clause, printed = "", "uncertain"
    errors, facet_holds = facet_review("quantities", item, sentence=value_clause)
    if errors:
        raise ValueError(";".join(errors))
    if facet_holds:
        # The value's clause does not settle the plan, goal, criterion or
        # modality the record claims: held for review, never published.
        record["status"] = "UNRESOLVED"
        record["reasons"] += [r for r in facet_holds if r not in record["reasons"]]
    if item.get("basis") and item["basis"] not in allowed_bases(item["epistemic"]):
        raise ValueError("EVIDENCE_BASIS_CONTRADICTS_ROLE")
    if value_clause and {"directive_not_executed", "qualifiers_preserved"} & set(
        ROLES[item["epistemic"]].holds
    ):
        from nasa_fire_ai.ingestion.statement_integrity import (
            directive_execution_enabled,
            directive_not_executed,
            qualifier_check_enabled,
            value_qualifier_dropped,
        )

        for enabled, test, reason in (
            (
                directive_execution_enabled,
                lambda: directive_not_executed(value_clause, None, {"item": item}),
                "EXECUTION_NOT_SUPPORTED_BY_DIRECTIVE",
            ),
            (
                qualifier_check_enabled,
                lambda: value_qualifier_dropped(value_clause, item),
                "QUALIFIER_DROPPED_FROM_CLAUSE",
            ),
        ):
            if enabled() and test():
                record["status"] = "UNRESOLVED"
                if reason not in record["reasons"]:
                    record["reasons"].append(reason)
    found_facets = facets("quantities", item) or {}
    printed_not_done = printed == "not_done" and item["epistemic"] in {
        "experimental_configuration",
        "reported_quantity",
    }
    if (
        subject_checks
        and entities.get(item["subject"], {}).get("class_id") == "ExperimentalRun"
        and found_facets.get("statement_type") != "derivation"
        and (found_facets.get("modality") != "actual" or printed_not_done)
    ):
        # A proposed, prescribed, conditional or hypothetical value, or one its
        # clause prints as not yet done, describes no run that was executed.
        raise ValueError("PLANNED_VALUE_ATTRIBUTED_TO_EXECUTED_RUN")
    if found_facets.get("modality") == "actual" and printed_not_done:
        # Read as done by the proposal but printed as future, planned, conditional
        # or prescribed: held for review, whatever its subject; never published.
        record["status"] = "UNRESOLVED"
        record["execution_reading"] = "not_done"
        record["reasons"].append("VALUE_PRINTED_AS_NOT_DONE_REQUIRES_REVIEW")

    numeric = parse_numeric_expression(item["expression"], convention=numeric_convention)
    if numeric["form"] == "LIST":
        # Two set-points are two quantities; one record cannot
        # hold both, and choosing one would invent the binding.
        raise ValueError("QUANTITY_EXPRESSION_LISTS_SEPARATE_VALUES")
    relative = re.fullmatch(
        r"(?P<value>.*?\d\S*)\s+(?P<word>lower|higher|greater|less|smaller|larger|more|faster|slower)",
        (item["expression"] or "").strip(),
        re.IGNORECASE,
    )
    if numeric["status"] == "NOT_NUMERIC" and relative:
        # "17% smaller than X" is a printed relative difference: the comparative
        # word is kept as its qualifier, the value is what the source prints.
        record["relative_comparison"] = {
            "original_expression": item["expression"],
            "comparative": relative["word"],
            "basis": "PRINTED_RELATIVE_DIFFERENCE",
        }
        item["expression"] = relative["value"]
        numeric = parse_numeric_expression(item["expression"], convention=numeric_convention)
        if item["epistemic"] != "derived_quantity":
            raise ValueError("RELATIVE_DIFFERENCE_IS_A_DERIVED_QUANTITY")
    if numeric["status"] == "NOT_NUMERIC":
        # A model may copy the original unit into the expression.
        # Separate it deterministically; the unit must still be
        # bound to the value in the source below.
        split = split_embedded_unit(item["expression"], item["unit"], convention=numeric_convention)
        if split and split["status"] == "UNIT_MISMATCH":
            raise ValueError("QUANTITY_UNIT_NOT_BOUND_TO_EXPRESSION")
        if not split:
            raise ValueError("QUANTITY_NOT_ORIGINAL_NUMERIC_EXPRESSION")
        if normalized(item["label"]) == normalized(item["expression"]):
            raise ValueError("QUANTITY_VALUE_OR_UNIT_IS_NOT_A_QUANTITY_NAME")
        record["expression_normalization"] = {
            "original_expression": item["expression"],
            "original_unit": item["unit"],
            **split,
        }
        item["expression"], item["unit"] = split["expression"], split["unit"]
        numeric = parse_numeric_expression(item["expression"], convention=numeric_convention)
    record["numeric_expression"] = numeric
    subject = entities.get(item["subject"])
    if not subject:
        raise ValueError("UNKNOWN_QUANTITY_ENDPOINT")
    if (
        subject_checks
        and (
            subject["class_id"] in CONDITION_CLASSES
            or has_class(subject["class_id"], "ExperimentalCondition", semantic)
            or has_class(subject["class_id"], "Intervention", semantic)
        )
    ) and not (
        # A condition carries only its own printed magnitude: the same name
        # ("vehicle rotation of 2 RPM") or the value printed in its label
        # ("25 cm/s purge stream").
        normalized(item["label"]) == normalized(subject["label"])
        or mentions(item["expression"] + " " + (item["unit"] or ""), subject["label"])
        or mentions(item["expression"] + (item["unit"] or ""), subject["label"])
    ):
        # A condition or intervention is how a test was set, never what another
        # value describes ("~150 kPa" is not a property of "2900 kPa feed line
        # pressure"). Only the association fails: the value is kept and other
        # subjects are tried.
        raise ValueError("QUANTITY_SUBJECT_IS_A_CONDITION")
    scope_eligible = quantity_scope_eligible(subject, semantic)
    record["native_scope_compatible"] = scope_eligible
    from nasa_fire_ai.ingestion.scientific_scope import (
        figure_group_support,
        test_article_alias_review,
        test_article_named_by_acronym,
    )

    alias_review = test_article_alias_review(item["subject"], spans, entities, document)
    alias_link = alias_review and test_article_named_by_acronym(
        item["subject"], spans, entities, document, value=item["expression"]
    )
    from nasa_fire_ai.ingestion.table_continuity import (
        derived_column_header_enabled,
        header_names,
        header_names_column,
        label_variants,
        table_cell_spans,
        table_row_binding,
    )

    # A table value belongs to the row group its first column
    # names, including continuation rows and footnote-marked
    # labels; the original row is kept as its context.
    table_binding = (
        table_row_binding(
            label_variants(subject["label"], document),
            item["expression"],
            item["unit"],
            {s["page"] for s in spans},
            document,
        )
        if subject.get("validation_status") == "SOURCE_SUPPORTED"
        and all(s["source_id"] == subject["source_id"] for s in spans)
        else None
    )
    if table_binding:
        record["table_row_binding"] = table_binding
    tested_material = (
        not scope_eligible and not table_binding and tested_material_entity(subject, document)
    )
    # A value in the paper's own method section, outside every group's
    # subsection, configures the investigation itself ("tests at the planned
    # cabin setpoint of 61.0 kPa").
    method_scope = (
        subject.get("class_id") == "Investigation"
        and item.get("epistemic") == "experimental_configuration"
        and document_statement_scope(item["subject"], spans, entities, document)
        and all(METHOD_SECTION.search(section_for_span(s, document)) for s in spans)
        # Under a group's own heading the group, not the investigation, is the
        # narrowest documented subject; so are the rows of a table that prints
        # the same value under a column named by its unit or variable.
        and not any(under_group_heading(s, entities, document) for s in spans)
        and not table_column_prints_value(
            document, item.get("expression"), item.get("unit"), item.get("label")
        )
    )
    # A value the study's own text proposes, intends or prescribes (a planned
    # environment, a target, a pass limit) belongs to no executed run; the study's
    # own investigation is its subject, wherever in its own research text it is
    # printed. Cited and background passages stay excluded.
    intended_scope = (
        not method_scope
        and subject.get("class_id") == "Investigation"
        and (
            (found := facets("quantities", item) or {}).get("execution_status") == "planned"
            or found.get("statement_type") == "criterion_value"
            # Non-executed scope (on by default, adopted on the generality audit of
            # 2026-10-27; "0" turns it off): a derived value, or
            # one the model reads as proposed, intended or conditional, describes no
            # executed run either; never a hypothetical one. The subject stays the
            # model's own, never substituted.
            or (
                os.getenv("SCIENCE_NONEXECUTED_SCOPE", "1") == "1"
                and (
                    found.get("statement_type") == "derivation"
                    or found.get("modality") in {"proposed", "intended", "conditional"}
                )
                and not table_column_prints_value(
                    document, item.get("expression"), item.get("unit"), item.get("label")
                )
                # No narrower subject is named in the value's own clause.
                and not any(
                    other != item["subject"]
                    and entity.get("class_id") in SUBJECT_CLASSES
                    and entity.get("validation_status") == "SOURCE_SUPPORTED"
                    and mentions(entity["label"], value_clause)
                    for other, entity in entities.items()
                )
            )
        )
        and document_statement_scope(item["subject"], spans, entities, document)
        and not any(under_group_heading(s, entities, document) for s in spans)
    )
    if intended_scope:
        record["scope_context"] = {
            "basis": "STUDY_OWN_NON_EXECUTED_VALUE_AT_INVESTIGATION_SCOPE",
            "support": subject.get("support", []),
        }
        method_scope = True
    if (
        subject_checks
        and not applicable(item["subject"], spans, entities, document)
        and (scope_eligible or tested_material)
        and not alias_review
        and not table_binding
        and not method_scope
    ):
        # The value's own sentence may print the proposed subject in a form the
        # label match misses; only the proposed subject is ever accepted.
        proposed = record.get("proposed_subject", item["subject"]) == item["subject"]
        recognized = proposed and printed_subject_recognition(item, spans, entities, document)
        # A pronoun opening the value's sentence may name the proposed subject as the
        # one subject of the sentence before it, in the same subsection.
        antecedent = (
            proposed
            and not recognized
            and anaphoric_subject(
                item["subject"], item["expression"], spans, entities, evidence, document
            )
        )
        # The one heading governing the value names the proposed subject.
        headed = (
            proposed
            and not recognized
            and not antecedent
            and heading_names_subject(item["subject"], spans, entities, document, printed_lines())
        )
        if headed:
            record["scope_context"] = headed
        if not recognized and not antecedent and not headed:
            raise ValueError("QUANTITY_SUBJECT_NOT_IN_APPLICABLE_SOURCE")
        if recognized:
            record["subject_recognition"] = recognized
        else:
            record["subject_antecedent"] = antecedent
        # The subject passed the applicability check only through recovery: an
        # identical value whose subject passed it directly stays canonical.
        record["subject_applicability"] = "RECOVERED"
    if (
        not scope_eligible
        and subject["class_id"] == "Material"
        and subject.get("study") == "current"
        and table_binding
        and table_binding["status"] == "UNIQUE"
        and not any(row["lineage"] for row in table_binding["rows"])
    ):
        # One printed row of a current-study table names this material: the value
        # is the material as tested here, never a general property of the material.
        record["scope_context"] = {
            "basis": "CURRENT_STUDY_TABLE_ROW_OF_NAMED_MATERIAL",
            "experimental_scope": "DOCUMENT_INVESTIGATION",
            "general_material_property": False,
        }
    elif tested_material:
        # Prose about a material this document's own table rows establish as
        # tested here (none cited): the material as tested, never in general.
        record["scope_context"] = {
            "basis": "MATERIAL_ESTABLISHED_AS_TESTED_IN_THIS_STUDY",
            "experimental_scope": "DOCUMENT_INVESTIGATION",
            "general_material_property": False,
        }
    elif not scope_eligible:
        record["status"] = "UNRESOLVED"
        record["reasons"].append(
            "QUANTITY_REQUIRES_EXPERIMENTAL_SCOPE_NOT_MATERIAL_CONCEPT"
            if subject["class_id"] == "Material"
            else "QUANTITY_REQUIRES_EXPERIMENTAL_SCOPE"
        )
    candidates = [
        (match, s["quote"])
        for s in spans
        for match in source_numeric_matches(s["quote"])
        if same_expression(match.group(1), item["expression"])
    ]
    if not candidates:
        raise ValueError("QUANTITY_EXPRESSION_ABSENT")
    # What follows each candidate value: in the quote, or (SCIENCE_EVIDENCE_VETO_QUANTITIES) in
    # the printed line(s), so that a quote cut after the number keeps the unit printed after it.
    unit_rests = [quote[match.end() :] for match, quote in candidates]
    if veto:
        unit_rests = [
            (w["quote"] if w else s["quote"])[(s["start"] - w["start"] if w else 0) + match.end() :]
            for s, w in zip(spans, printed_lines(), strict=True)
            for match in source_numeric_matches(s["quote"])
            if same_expression(match.group(1), item["expression"])
        ]
    source_expression = candidates[0][0].group(1)
    if source_expression != item["expression"]:
        # Keep the original writing (for example "−40"), not a
        # model glyph variant of it; the difference is recorded.
        record.setdefault("expression_normalization", {}).update(
            model_expression=item["expression"],
            source_expression=source_expression,
            glyph_basis="SOURCE_GLYPH_VARIANT_OF_SAME_EXPRESSION",
        )
        item["expression"] = source_expression
    if item["unit"] and not any(
        re.match(r"\s*[-‑]?\s*" + re.escape(item["unit"]) + r"(?!\w)", rest) for rest in unit_rests
    ):
        # A table value may state its unit only in its own
        # column header, e.g. "System Pressure (psia)".
        from nasa_fire_ai.ingestion.pdf_quantities import header_unit_binding

        inherited = header_unit_binding(item["expression"], item["unit"], spans, document)
        if not inherited:
            raise ValueError("QUANTITY_UNIT_NOT_BOUND_TO_EXPRESSION")
        record["unit_binding"] = inherited
    if (item["unit"] or "").strip() in {'"', "″", "”"} and all(
        # A quotation mark that closes a quoted number ("the “6”") is no inch mark.
        quote[: match.start()].count("“") > quote[: match.start()].count("”")
        or quote[: match.start()].count('"') % 2
        for match, quote in candidates
    ):
        raise ValueError("QUANTITY_UNIT_NOT_BOUND_TO_EXPRESSION")
    section_proof = group_section_support(item["subject"], spans, entities, document)
    figure_proof = figure_group_support(item["subject"], spans, entities, document)
    if figure_proof:
        record["scope_context"] = {
            "basis": "EXPLICIT_ORIGINAL_FIGURE_GROUP_REFERENCE",
            "support": figure_proof,
            "image_interpretation": False,
        }
        spans += locate(figure_proof, evidence)
    if section_proof:
        record["scope_context"] = {
            "basis": "EXACT_ORIGINAL_GROUP_SUBSECTION",
            "support": section_proof,
        }
        spans += locate(section_proof, evidence)
    if method_scope and not intended_scope and not section_proof and not figure_proof:
        record["scope_context"] = {
            "basis": "ORIGINAL_METHOD_SECTION_AT_DOCUMENT_INVESTIGATION_SCOPE",
            "support": subject.get("support", []),
        }
    if (
        subject_checks
        and not section_proof
        and not figure_proof
        and not method_scope
        and not alias_review
        and not table_binding
        and not local_binding(item["subject"], item["expression"], spans, entities, printed_lines())
        and not (
            label_binding_enabled()
            and record.get("proposed_subject", item["subject"]) == item["subject"]
            and (
                bound := printed_label_binding(
                    item["subject"], item["expression"], item["unit"], spans, entities
                )
            )
            and record.update(label_binding=bound) is None
        )
        and not (
            (joined := continued_sentence(spans, evidence))
            and local_binding(item["subject"], item["expression"], [joined], entities)
            and record.update(sentence_continuation=joined["continuation"]) is None
        )
        and not (
            (
                antecedent := anaphoric_subject(
                    item["subject"], item["expression"], spans, entities, evidence, document
                )
            )
            and record.update(subject_antecedent=antecedent) is None
        )
        and not (
            (
                recognized := record.get("subject_recognition")
                or (
                    record.get("proposed_subject", item["subject"]) == item["subject"]
                    and printed_subject_recognition(item, spans, entities, document)
                )
            )
            and record.update(subject_recognition=recognized) is None
        )
        and not (
            entities[item["subject"]]["class_id"] == "ExperimentFamily"
            and all(
                normalized(
                    document.get("layout_headings", {}).get(s["evidence_id"], {}).get("quote", "")
                )
                == normalized(entities[item["subject"]]["label"])
                for s in spans
            )
        )
    ):
        raise ValueError("QUANTITY_LOCAL_SUBJECT_BINDING_UNRESOLVED")
    if normalized(item["label"]) in {
        normalized(item["expression"]),
        normalized(item["unit"] or ""),
        normalized(item["expression"] + " " + (item["unit"] or "")),
        normalized(item["expression"] + (item["unit"] or "")),
        normalized(item["expression"] + "-" + (item["unit"] or "")),
    }:
        raise ValueError("QUANTITY_VALUE_OR_UNIT_IS_NOT_A_QUANTITY_NAME")
    status, prop = resolve_source_property(semantic, item["label"], item["unit"])
    # Reuse declared dimensional nouns to block, for example,
    # a width assigned the time until that width vanished. This
    # checks compatibility only; it activates no accessor/mapping.
    from nasa_fire_ai.normalization.units import normalize

    noun = normalized(item["label"]).split()[-1:]
    expected_units = {
        definition["unit"]
        for name, definition in getattr(semantic, "source_field_accessors", {}).items()
        if noun and name.split("_")[-1] == noun[0] and definition.get("unit")
    }
    if len(expected_units) == 1 and item["unit"]:
        try:
            original_unit = (
                "s"
                if re.fullmatch(r"seconds?|minutes?|hours?", item["unit"], re.IGNORECASE)
                else normalize(1, item["unit"])[1]
            )
            expected_unit = normalize(1, next(iter(expected_units)))[1]
        except ValueError:
            pass
        else:
            if original_unit != expected_unit:
                raise ValueError("QUANTITY_NAME_UNIT_DIMENSION_CONTRADICTION")
    # SCIENCE_EVIDENCE_VETO_QUANTITIES: the name is looked for, and bound to the value, in the
    # printed line(s) of each span, not in the quote alone.
    name_spans = [w or s for s, w in zip(spans, printed_lines(), strict=True)] if veto else spans
    labels = [item["label"]]
    if prop:
        labels.extend(semantic.properties[prop].aliases)
    adjacent_names = []
    temporal_coordinate = False
    if table_binding:
        # The column header names the variable of every bound
        # cell; the value is located inside its printed row.
        headers = sorted({h["column_header"] or "" for h in table_binding["rows"]})
        if derived_column_header_enabled():
            named = all(
                any(header_names_column(name, h) for name in labels) for h in table_binding["rows"]
            )
        else:
            named = all(any(header_names(name, header) for name in labels) for header in headers)
        if not named:
            raise ValueError("QUANTITY_NAME_IS_NOT_TABLE_COLUMN_HEADER")
        record["quantity_name_support"] = {
            "basis": "ORIGINAL_TABLE_COLUMN_HEADER",
            "original_column_headers": headers,
            "global_alias_activation": "NONE",
        }
        pages = {h["page"] for h in table_binding["rows"]}
        page_texts = [
            {"evidence_id": key, "start": 0, "quote": ref["text"]}
            for key, ref in evidence.items()
            if ref["page"] in pages and ref["source_id"] == spans[0]["source_id"]
        ]
        cells = table_cell_spans(table_binding["rows"], page_texts)
        if len(cells) != len(table_binding["rows"]):
            raise ValueError("QUANTITY_NAME_VALUE_NOT_LOCALLY_BOUND")
        record["quantity_value_spans"] = []
        for cell in cells:
            inner = cell["quote"].find(item["expression"])
            if inner < 0:
                raise ValueError("QUANTITY_NAME_VALUE_NOT_LOCALLY_BOUND")
            record["quantity_value_spans"].append(
                {
                    "evidence_id": cell["evidence_id"],
                    "start": cell["start"] + inner,
                    "end": cell["start"] + inner + len(item["expression"]),
                    "quote": item["expression"],
                    "table_cell": cell["quote"],
                    "table_row": cell["table_row"],
                }
            )
        if table_binding["status"] == "AMBIGUOUS":
            record["status"] = "UNRESOLVED"
            record["reasons"].append("TABLE_VALUE_ROW_WITHIN_GROUP_AMBIGUOUS")
        lineage = [e for h in table_binding["rows"] for e in h["lineage"]]
        if lineage and subject.get("study") == "current":
            record["status"] = "UNRESOLVED"
            record["reasons"].append("TABLE_ROW_LINEAGE_NOT_CURRENT_STUDY")
    elif not any(mentions(label, s["quote"]) for label in labels for s in name_spans):
        adjacent_names = source_dimension_adjectives(item["label"], item["unit"])
        labels.extend(adjacent_names)
        if adjacent_names:
            record["quantity_name_support"] = {
                "basis": "EXPLICIT_POST_VALUE_DIMENSIONAL_ADJECTIVE",
                "original_wordforms": adjacent_names,
                "global_alias_activation": "NONE",
            }
        elif printed := printed_value_name(
            item["label"], item["expression"], item["unit"], name_spans, item.get("epistemic")
        ):
            # The label is the model's; the name it is checked against is printed.
            labels.append(printed["printed_name"])
            record["quantity_name_support"] = printed
        elif setting := printed_setting_name(
            item["label"], item["expression"], item["unit"], name_spans, item.get("epistemic")
        ):
            labels.append(setting["printed_name"])
            record["quantity_name_support"] = setting
        elif proposed := model_printed_name(item, name_spans):
            # The model names the printed words; they must name this value in its clause.
            labels.append(proposed["printed_name"])
            record["quantity_name_support"] = proposed
        if normalized(item["label"]) == "time" and item["unit"] in {
            "s",
            "second",
            "seconds",
            "min",
            "minute",
            "minutes",
            "h",
            "hour",
            "hours",
        }:
            temporal_coordinate = True
            labels.extend(["at", "t"])
            record["quantity_name_support"] = {
                "basis": "EXPLICIT_SOURCE_TEMPORAL_COORDINATE",
                "global_alias_activation": "NONE",
            }
    elif (
        setting := printed_setting_name(
            item["label"], item["expression"], item["unit"], name_spans, item.get("epistemic")
        )
    ) and (
        # Only a label that is the verb itself: a printed noun sharing its stem
        # ("rotation") is named, or not, by the ordinary name syntax.
        normalized(item["label"]) == normalized(setting["printed_name"])
        and setting_verb_of_unit_dimension(setting["printed_name"], item["unit"])
    ):
        # "The drum was rotated at 12.5 RPM" labelled "rotated": the label is
        # printed and is the verb that sets the value. A label that is the verb
        # cannot vouch for itself, so the verb must be a form of a noun of the
        # unit's own dimension ("rotation" for a rotational speed).
        record["quantity_name_support"] = setting
    column = None
    joined = continued_sentence(spans, evidence)
    joined_name = (
        not table_binding
        and joined
        and not any(mentions(label, s["quote"]) for label in labels for s in name_spans)
        and any(mentions(label, joined["quote"]) for label in labels)
    )
    if joined_name:
        # The name was printed before the page break of the same sentence.
        record["sentence_continuation"] = joined["continuation"]
        record["quantity_name_support"] = {
            "basis": "NAME_BEFORE_PAGE_BREAK_OF_SAME_SENTENCE",
            "global_alias_activation": "NONE",
        }
        value_in_joined = quantity_name_value_binding(
            labels, item["expression"], item["unit"], [{**joined, "evidence_id": "", "start": 0}]
        )
        record["quantity_value_spans"] = (
            [
                {
                    "evidence_id": s["evidence_id"],
                    "start": s["start"] + m.start(),
                    "end": s["start"] + m.end(),
                    "quote": m.group(),
                }
                for s in spans
                if s["evidence_id"] != joined["continuation"]["evidence_id"]
                for m in re.finditer(
                    r"(?<![\w.])"
                    + re.escape(item["expression"])
                    + r"\s*[-‑]?\s*"
                    + re.escape(item["unit"] or "")
                    + r"(?!\w)",
                    s["quote"],
                )
            ][:1]
            if value_in_joined
            else []
        )
        column = "JOINED"
    named_in_support = any(mentions(label, s["quote"]) for label in labels for s in name_spans)
    bound_in_support = (
        named_in_support
        and not table_binding
        and quantity_name_value_binding(
            labels,
            item["expression"],
            None if record.get("unit_binding") else item["unit"],
            name_spans,
            adjacent_names,
            temporal_coordinate,
        )
    )
    if not table_binding and not column and not bound_in_support:
        from nasa_fire_ai.ingestion.table_continuity import (
            material_row_labels,
            subject_column_for_value,
        )

        column = subject_column_for_value(
            material_row_labels(subject["label"], document)
            if subject["class_id"] == "Material"
            else label_variants(subject["label"], document),
            labels,
            item["expression"],
            item["unit"],
            document,
        )
        if not column and named_in_support:
            raise ValueError("QUANTITY_NAME_VALUE_NOT_LOCALLY_BOUND")
        from nasa_fire_ai.normalization.units import interpret as interpret_unit

        unit_meaning = interpret_unit(item["unit"])
        if (
            not column
            and prop
            and unit_meaning
            # "burned at 29% O2 and 61 kPa": a pressure unit itself names the
            # one approved property whose name is that dimension.
            and normalized(prop) == unit_meaning["dimension"]
            and semantic.properties[prop].canonical_unit == unit_meaning["canonical_unit"]
        ):
            values = [
                {
                    "evidence_id": s["evidence_id"],
                    "start": s["start"] + m.start(),
                    "end": s["start"] + m.end(),
                    "quote": m.group(),
                }
                for s in name_spans
                for m in re.finditer(
                    r"(?<![\w.])"
                    + re.escape(item["expression"])
                    + r"\s*[-‑]?\s*"
                    + re.escape(item["unit"] or "")
                    + r"(?!\w)",
                    s["quote"],
                )
                # A setting printed without a name of its own ("burned at 29% O2
                # and 61 kPa"), never a value the source names otherwise ("A1
                # special reading was 20 Pa").
                if re.search(
                    r"\b(?:at|and|to|from|under|with)\s*[~≈]?\s*$",
                    s["quote"][max(0, m.start() - 20) : m.start()],
                    re.IGNORECASE,
                )
            ]
            if values:
                column = "UNIT"
                record["quantity_name_support"] = {
                    "basis": "UNIT_ESTABLISHES_APPROVED_PROPERTY",
                    "property_id": prop,
                    "unit": item["unit"],
                    "global_alias_activation": "NONE",
                }
                record["quantity_value_spans"] = values[:1]
        if not column:
            raise ValueError("QUANTITY_NAME_NOT_IN_SOURCE_SUPPORT")
    if (
        not table_binding
        and column
        and not isinstance(column, str)  # not "JOINED" or "UNIT"
        and not bound_in_support
    ):
        # The name comes from this document's own column for the same subject's
        # value; the prose value itself must still be printed in the support.
        record["quantity_name_support"] = {
            "basis": "SAME_SUBJECT_VALUE_UNDER_DOCUMENT_TABLE_COLUMN",
            "table_rows": column,
            "global_alias_activation": "NONE",
        }
        record["quantity_value_spans"] = [
            {
                "evidence_id": s["evidence_id"],
                "start": s["start"] + m.start(),
                "end": s["start"] + m.end(),
                "quote": m.group(),
            }
            for s in name_spans
            for m in re.finditer(
                r"(?<![\w.])"
                + re.escape(item["expression"])
                + r"\s*[-‑]?\s*"
                + re.escape(item["unit"] or "")
                + r"(?!\w)",
                s["quote"],
            )
        ]
    if not table_binding and not column:
        if not any(mentions(label, s["quote"]) for label in labels for s in name_spans):
            raise ValueError("QUANTITY_NAME_NOT_IN_SOURCE_SUPPORT")
        record["quantity_value_spans"] = quantity_name_value_binding(
            labels,
            item["expression"],
            # A header-inherited unit is already bound to its column.
            None if record.get("unit_binding") else item["unit"],
            name_spans,
            adjacent_names,
            temporal_coordinate,
        )
    if not record["quantity_value_spans"]:
        raise ValueError("QUANTITY_NAME_VALUE_NOT_LOCALLY_BOUND")
    if item["epistemic"] == "reported_quantity" and explicit_quantity_derivation(
        labels,
        record["quantity_value_spans"],
        [w or s for s, w in zip(spans, printed_lines(), strict=True)] if veto else spans,
    ):
        raise ValueError("EXPLICIT_DERIVATION_IS_NOT_REPORTED_MEASUREMENT")
    record["mapping"] = {
        "kind": "existing_attribute" if prop else "unresolved_attribute",
        "raw_label": item["label"],
        "status": status,
        "property_id": prop,
    }
    accessor = None
    if not prop and subject["class_id"] == "Sample":
        from nasa_fire_ai.normalization.units import normalize

        stem = re.sub(r"^(?:sample|specimen)\s+", "", normalized(item["label"]))
        name = "sample_" + stem.replace(" ", "_")
        if name not in getattr(semantic, "source_field_accessors", {}):
            # Reuse only word forms of already approved specimen
            # accessors. The original label remains unchanged.
            alternatives = [
                n
                for n in getattr(semantic, "source_field_accessors", {})
                if n.startswith("sample_")
                and stem in source_dimension_adjectives(n.removeprefix("sample_"), item["unit"])
            ]
            if len(alternatives) == 1:
                name = alternatives[0]
        definition = getattr(semantic, "source_field_accessors", {}).get(name)
        try:
            if (
                definition
                and normalize(1, item["unit"] or "")[1] == normalize(1, definition["unit"])[1]
            ):
                accessor = name
        except ValueError:
            pass
        if accessor:
            record["mapping"].update(
                kind="existing_source_attribute",
                status="CANONICAL_SOURCE_ACCESSOR",
                source_accessor=accessor,
                existing_contract=definition,
                activation="NONE",
            )
            record["source_role"] = definition["role"]
            record["native_representation"] = "STAGED_ORIGINAL_SPECIMEN_CHARACTERISTIC"
            if item["epistemic"] == "reported_quantity" and not any(
                re.search(r"\b(?:measur\w*|observ\w*)\b", s["quote"], re.IGNORECASE) for s in spans
            ):
                record["status"] = "UNRESOLVED"
                record["scientific_role_conflict"] = True
                record["reasons"].append("SPECIMEN_CHARACTERISTIC_IS_NOT_ESTABLISHED_MEASUREMENT")
    record["subject"] = entities[item["subject"]]["id"]
    record["native_value_compatible"] = native_quantity_expression(item["expression"])
    if not record["native_value_compatible"]:
        record["native_representation"] = "DEFERRED_PRESERVED_ORIGINAL_LITERAL"
    if item["epistemic"] == "reported_quantity" and any(
        is_caption_line(line)
        for span in ([caption_span(s, evidence) or s for s in spans] if veto else spans)
        for line in own_lines(span, record.get("quantity_value_spans"))
        if item["expression"] and item["expression"] in line
    ):
        # A value printed in a figure or table title states what is shown (often
        # the condition of the tests plotted), not a reported measurement.
        record["status"] = "UNRESOLVED"
        record["reasons"].append("REPORTED_VALUE_PRINTED_IN_A_CAPTION_REQUIRES_REVIEW")
    if alias_link:
        # The sentence printing the value names the source-defined test article by
        # its acronym, outside any procedural or temporal clause.
        record["scope_context"] = alias_link
    elif alias_review:
        record["status"] = "UNRESOLVED"
        record["scope_context"] = alias_review
        record["native_value_compatible"] = False
        record["native_representation"] = "DEFERRED_SOURCE_TEST_ARTICLE_ALIAS_SCOPE"
        record["reasons"].append(TEST_ARTICLE_ALIAS_HOLD)
    from nasa_fire_ai.normalization.units import interpret

    unit_meaning = interpret(item["unit"])
    # A bare F or C is a degree only where the value is named a temperature;
    # otherwise it stays uninterpreted (a farad, a coulomb).
    if (
        not unit_meaning
        and (item["unit"] or "").strip() in {"F", "C"}
        and re.search(r"\btemperatures?\b", item.get("label") or "", re.IGNORECASE)
    ):
        unit_meaning = interpret("°" + item["unit"].strip())
    if unit_meaning:
        record["unit_interpretation"] = unit_meaning
    if status == "CANONICAL_STATE_QUALIFIED":
        record["mapping"]["state_qualified_label"] = item["label"]
    if not prop and not accessor:
        if unit_meaning or (item["unit"] is None and numeric["form"] == "RATIO"):
            # A missing property does not invalidate a bound source
            # quantity: the value stands, its property is staged.
            record["mapping"].update(
                kind="staged_property_proposal",
                status="STAGED_PROPERTY_PROPOSAL",
                property_proposal=property_proposal(item, subject, spans, semantic),
            )
            record["semantic_property_status"] = "STAGED_PROPOSAL_NOT_APPROVED"
            # Without an approved contract, the printed syntax alone must make the
            # label the name of this value; otherwise it may name an object.
            naming = staged_name_syntax(item["label"], record, evidence)
            if not naming and record.get("quantity_name_support", {}).get("basis") == (
                "MODEL_PRINTED_NAME_IN_VALUE_CLAUSE"
            ):
                # The printed words the model named, not its label, must make the
                # syntax that names this value.
                naming = staged_name_syntax(
                    record["quantity_name_support"]["printed_name"], record, evidence
                )
            if naming:
                record["mapping"]["name_value_syntax"] = naming
            else:
                record["status"] = "UNRESOLVED"
                record["reasons"].append("QUANTITY_SEMANTICS_OR_UNIT_UNRESOLVED")
        else:
            record["status"] = "UNRESOLVED"
            record["reasons"].append("QUANTITY_SEMANTICS_OR_UNIT_UNRESOLVED")
    for value in record.get("quantity_value_spans", []):
        # "a humidity 3 to 7% higher than the room", "2% lower in
        # humidity than in a run with ...": the value is a printed
        # difference from another quantity, not the quantity itself.
        after = evidence[value["evidence_id"]]["text"][value["end"] : value["end"] + 80]
        if item["epistemic"] != "derived_quantity" and re.match(
            r"\s*%?\s*(?:higher|lower|greater|less|more|above|below|faster|slower)\s+"
            r"(?:than\b|in\s+[A-Za-z])",
            after,
            re.IGNORECASE,
        ):
            record["status"] = "UNRESOLVED"
            record["relative_comparison"] = {
                "printed_after_value": after.strip()[:40],
                "basis": "PRINTED_RELATIVE_DIFFERENCE",
            }
            record["reasons"].append("RELATIVE_DIFFERENCE_IS_A_DERIVED_QUANTITY")
            break
    if numeric["status"] == "AMBIGUOUS":
        # Candidate readings are preserved; a reviewer chooses.
        record["status"] = "UNRESOLVED"
        record["reasons"].append("NUMERIC_EXPRESSION_AMBIGUOUS")
    # An original count ratio (for example reactions/tests) is
    # dimensionless and kept as written, never divided into a scalar.
    if item["unit"] is None and numeric["form"] != "RATIO":
        record["status"] = "UNRESOLVED"
        record["reasons"].append("QUANTITY_UNIT_UNSPECIFIED")
    if (
        item["epistemic"] == "reported_quantity"
        and table_binding
        and (applied := applied_column_value(table_binding, item["unit"], document, evidence))
    ):
        # "It was struck with 60 J at 7,000 kPa": the document applies
        # this column's values, so the cell is a test setting, not a result.
        record["role_recovery"] = {
            "proposed_epistemic": "reported_quantity",
            "recovered_epistemic": "experimental_configuration",
            "basis": "COLUMN_VALUE_APPLIED_IN_A_TEST_STEP",
            "applied_text": applied,
        }
        item["epistemic"] = "experimental_configuration"
    if item["epistemic"] == "reported_quantity" and re.search(
        r"\b(?:set[\s-]?points?|nominal|target)\b", item["label"], re.IGNORECASE
    ):
        # "held its 3.2 kPa setpoint": a value the source names a setpoint
        # is how the test was set, not a result read from it.
        record["role_recovery"] = {
            "proposed_epistemic": "reported_quantity",
            "recovered_epistemic": "experimental_configuration",
            "basis": "VALUE_NAMED_AS_A_SETTING",
        }
        item["epistemic"] = "experimental_configuration"
    # A bound table cell's role is read from its own column header and table
    # caption, not from the whole page; a prose value's role from its own
    # sentence, not from a neighbouring column ("Initial Pressure") on the page.
    role_text = " ".join(
        [
            (h["column_header"] or "") + " " + (h["table_caption"] or "")
            for h in table_binding["rows"]
        ]
        if table_binding
        else value_sentences(record["quantity_value_spans"], evidence)
    )
    if item["epistemic"] == "reported_quantity" and re.search(
        r"\b(?:will|would|planned|proposed|set\s+to|initial|maintained|specified|simulat\w*|predict\w*|derived|derivative|(?:linear|quadratic|regression|curve|polynomial)\s+fits?|shall|must|standard\s+deviations?|std\.?\s+dev\.?|variances?)\b",
        role_text,
        re.IGNORECASE,
    ):
        # The cue must be printed next to the value itself, never elsewhere on a
        # table page ("Initial Test Pressure" beside a measured AIT).
        near = " ".join(
            evidence[v["evidence_id"]]["text"][max(0, v["start"] - 90) : v["end"] + 60]
            for v in record["quantity_value_spans"]
        )
        setting = re.search(SETTING_ROLE_CUE, near, re.IGNORECASE)
        if table_binding or not setting or re.search(NOT_A_SETTING_CUE, role_text, re.IGNORECASE):
            raise ValueError("CONFIGURATION_OR_DERIVED_IS_NOT_MEASUREMENT")
        # "the MFV held the ~3.2 kPa set-point at the ~2 kg/h draw": the
        # sentence prints how the test was set, so the value is a configuration.
        record["role_recovery"] = {
            "proposed_epistemic": "reported_quantity",
            "recovered_epistemic": "experimental_configuration",
            "basis": "EXPLICIT_SETTING_CUE_IN_VALUE_SENTENCE",
            "printed_cue": setting.group(),
        }
        item["epistemic"] = "experimental_configuration"
    if (
        item["epistemic"] == "reported_quantity"
        and not table_binding
        and value_is_applied_input(record["quantity_value_spans"], evidence)
    ):
        # "It was struck with 60 J": the value is what was applied.
        raise ValueError("APPLIED_TEST_INPUT_IS_NOT_A_MEASUREMENT")
    derivation = next(
        (
            context
            for s in spans
            if (context := original_derivation_context(s["quote"], [s], evidence))
        ),
        None,
    )
    if derivation and item["epistemic"] == "reported_quantity":
        record["status"] = "UNRESOLVED"
        record["scientific_role_conflict"] = True
        record["reasons"].append("DERIVED_CONTEXT_IS_NOT_DIRECT_OBSERVATION")
        record["epistemic_context"] = {
            "basis": "NEAREST_ORIGINAL_DERIVATION_OF_SAME_VARIABLE",
            "support": locate([derivation], evidence),
        }


# A printed cue that the value is how a test was set ...
# "was set to 20 Pa" on the value itself stays a rejected role error
# (test_epistemic_upgrades_rejected): only a held setting is read here.
SETTING_ROLE_CUE = r"\b(?:maintained|set[\s-]?points?)\b"
# ... unless the same sentence makes it a requirement, a plan or a derived value.
NOT_A_SETTING_CUE = (
    r"\b(?:will|would|planned|proposed|specified|required|requirements?|shall|must|"
    r"simulat\w*|predict\w*|derived|derivative|fits?|standard\s+deviations?|"
    r"std\.?\s+dev\.?|variances?)\b"
)

TEST_ARTICLE_ALIAS_HOLD = "TEST_ARTICLE_ALIAS_EXPERIMENTAL_GROUP_SCOPE_REQUIRES_REVIEW"

# The ontology's condition classes (fire_safety.ttl) and interventions: how a test
# was set, never the subject of another value.
CONDITION_CLASSES = frozenset(
    {
        "ExperimentalCondition",
        "AtmosphereCondition",
        "FlowCondition",
        "GravityCondition",
        "PressureCondition",
        "Intervention",
    }
)
SUBJECT_REJECTIONS = frozenset(
    {
        "QUANTITY_SUBJECT_NOT_IN_APPLICABLE_SOURCE",
        "QUANTITY_LOCAL_SUBJECT_BINDING_UNRESOLVED",
        "QUANTITY_SUBJECT_IS_A_CONDITION",
    }
)
SUBJECT_HOLDS = frozenset(
    {
        "QUANTITY_REQUIRES_EXPERIMENTAL_SCOPE",
        "QUANTITY_REQUIRES_EXPERIMENTAL_SCOPE_NOT_MATERIAL_CONCEPT",
    }
)


def validate_quantity(item, record, spans, entities, document, semantic, evidence, convention):
    """Validate a quantity; when only its subject fails, recover or keep the value.

    The proposed subject is revalidated, never silently replaced: every other
    source-supported experimental subject is tried with the full validator, one
    surviving subject is adopted with its provenance, and otherwise the bound
    source value is kept UNRESOLVED without the rejected association.
    """
    original = (copy.deepcopy(item), copy.deepcopy(record), list(spans))

    def attempt(subject_key, subject_checks=True):
        trial_item, trial_record = copy.deepcopy(original[0]), copy.deepcopy(original[1])
        trial_item["subject"] = subject_key
        trial_record["proposal"] = trial_item
        trial_spans = list(original[2])
        trial_record["support_spans"] = trial_spans
        # Printed-subject recognition may only accept the subject the model proposed.
        trial_record["proposed_subject"] = original[0]["subject"]
        validate_quantity_subject(
            trial_item,
            trial_record,
            trial_spans,
            entities,
            document,
            semantic,
            evidence,
            convention,
            subject_checks,
        )
        trial_record.pop("proposed_subject", None)
        return trial_item, trial_record, trial_spans

    def adopt(result):
        trial_item, trial_record, trial_spans = result
        item.clear()
        item.update(trial_item)
        spans[:] = trial_spans
        record.clear()
        record.update(trial_record, proposal=item, support_spans=spans)

    proposed = original[0]["subject"]
    try:
        result = attempt(proposed)
        reason = next((r for r in result[1]["reasons"] if r in SUBJECT_HOLDS), None)
        alias = TEST_ARTICLE_ALIAS_HOLD in result[1]["reasons"]
        if not reason and not alias:
            adopt(result)
            return
    except ValueError as error:
        reason = str(error)
        if reason not in SUBJECT_REJECTIONS or proposed not in entities:
            raise
        result = None
    # A value printed inside one group's own subsection belongs to that group when
    # the model gave it a broader or held subject (the test article, the whole
    # investigation): the group is revalidated in full, never assumed.
    group = subsection_group(original[2], entities, document)
    if group and group != proposed:
        try:
            trial = attempt(group)
        except ValueError:
            trial = None
        if (
            trial
            and not any(r in SUBJECT_HOLDS for r in trial[1]["reasons"])
            and TEST_ARTICLE_ALIAS_HOLD not in trial[1]["reasons"]
            and trial[1].get("scope_context", {}).get("basis") == "EXACT_ORIGINAL_GROUP_SUBSECTION"
        ):
            adopt(trial)
            record["subject_recovery"] = {
                "proposed_subject": entities[proposed]["id"] if proposed in entities else proposed,
                "proposed_subject_rejection": reason
                or (TEST_ARTICLE_ALIAS_HOLD if result is not None else None),
                "method": "VALUE_INSIDE_GROUP_OWN_SUBSECTION_REVALIDATED",
                "recovered_subject": entities[group]["id"],
                "status": "RECOVERED",
            }
            return
    if result is not None and not reason:
        adopt(result)  # the test-article hold stays a hold
        return
    source_ids = {s["source_id"] for s in original[2]}
    passage = " ".join(s.get("quote", "") for s in original[2])
    # A passage that names its own subject ("Gamma was compared. It was
    # struck with 60 J") never gives the value to an entity it does not name.
    names_proposed = proposed in entities and mentions(
        re.split(r"\s*\(", entities[proposed]["label"])[0], passage
    )
    recovered = []
    for key, entity in entities.items():
        if (
            key == proposed
            or entity.get("validation_status") != "SOURCE_SUPPORTED"
            or entity["class_id"] == "Investigation"  # never a silent fallback
            or entity["source_id"] not in source_ids
            or not (quantity_scope_eligible(entity, semantic) or entity["class_id"] == "Material")
            # A condition is the setting of a test, not the subject of its values.
            or has_class(entity["class_id"], "ExperimentalCondition", semantic)
            or (names_proposed and not mentions(re.split(r"\s*\(", entity["label"])[0], passage))
        ):
            continue
        try:
            trial = attempt(key)
        except ValueError:
            continue
        from nasa_fire_ai.ingestion.table_continuity import printed_in_table

        if not trial[1].get("table_row_binding") and any(
            printed_in_table(document, s["page"], trial[0]["expression"]) for s in trial[2]
        ):
            continue  # a table value is bound through its own row, never by proximity
        if not any(r in SUBJECT_HOLDS for r in trial[1]["reasons"]):
            recovered.append((key, trial))
    if len(recovered) > 1:
        from nasa_fire_ai.ingestion.table_continuity import _key, material_row_labels

        # A material and one of its own printed row groups (a batch of it) both
        # fit a row value: the narrower row group is the subject, never both.
        groups = {
            key: {_key(v) for v in material_row_labels(entities[key]["label"], document)}
            for key, _ in recovered
            if entities[key]["class_id"] == "Material"
        }
        recovered = [
            (key, trial)
            for key, trial in recovered
            if not any(
                _key(entities[other]["label"]) in groups.get(key, set())
                for other, _ in recovered
                if other != key
            )
        ]
    basis = {
        "proposed_subject": entities[proposed]["id"],
        "proposed_subject_rejection": reason,
        "method": "FULL_REVALIDATION_WITH_EACH_SOURCE_SUPPORTED_EXPERIMENTAL_SUBJECT",
    }
    if len(recovered) == 1:
        adopt(recovered[0][1])
        record["subject_recovery"] = {
            **basis,
            "recovered_subject": entities[recovered[0][0]]["id"],
            "status": "RECOVERED",
        }
        return
    if result is not None:
        # A held, non-experimental subject stays held as before; leads are recorded.
        adopt(result)
        if recovered:
            record["subject_recovery"] = {
                **basis,
                "status": "UNRESOLVED",
                "alternatives": sorted(entities[key]["id"] for key, _ in recovered),
            }
        return
    if result is None:
        # The value is checked against the source with no subject attached; a
        # value that fails on its own is still rejected for its own reason.
        result = attempt(proposed, subject_checks=False)
    adopt(result)
    record["status"] = "UNRESOLVED"
    record["subject"] = None
    if reason not in record["reasons"]:
        record["reasons"].append(reason)
    record["reasons"].append("QUANTITY_VALUE_PRESERVED_SUBJECT_UNRESOLVED")
    record["subject_recovery"] = {
        **basis,
        "status": "UNRESOLVED",
        "alternatives": sorted(entities[key]["id"] for key, _ in recovered),
    }
