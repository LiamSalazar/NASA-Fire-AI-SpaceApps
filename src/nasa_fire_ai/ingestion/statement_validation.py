"""Validation of a statement proposal."""

import os
import re

from nasa_fire_ai.ingestion import clause_cues
from nasa_fire_ai.ingestion.clause_cues import execution
from nasa_fire_ai.ingestion.printed_layout import (
    LIST_MARKER,
    background_or_analysis_span,
    document_conclusion_scope,
    group_section_support,
    item_has_clause,
    list_items,
    list_items_enabled,
    list_items_mode,
    list_lead_with_items,
    page_edge_prefix,
    page_edge_suffix,
    running_headers,
    section_for_span,
)
from nasa_fire_ai.ingestion.quantity_naming import (
    original_heading_scope,
)
from nasa_fire_ai.ingestion.scientific_facets import (
    BACKGROUND_ROLES,
    CLASS_FLEXIBLE_ROLES,
    DOCUMENTARY_ROLE,
    PLAN_GOAL_ROLES,
    PROVENANCE_ROLE,
    ROLES,
    STATEMENT_CLASSES,
    allowed_bases,
    facet_review,
    facets,
    ongoing_activity_roles_enabled,
    ongoing_roles,
    plan_goal_facets_enabled,
    record_facets,
    stated_modality,
)
from nasa_fire_ai.ingestion.scientific_scope import (
    document_investigation,
    document_statement_scope,
    local_investigation_antecedent,
    original_derivation_context,
    test_article_named_by_acronym,
)
from nasa_fire_ai.ingestion.source_spans import (
    locate,
    mentions,
    normalized,
    recover_span,
)
from nasa_fire_ai.ingestion.statement_integrity import role_errors
from nasa_fire_ai.ingestion.subject_recognition import (
    HEADING_SUBJECT_CONFLICT,
    applicable,
    has_class,
    heading_names_subject,
    heading_rule_accepts,
    heading_subject_conflict,
    heading_subject_v3_enabled,
)
from nasa_fire_ai.ingestion.value_phrase import sentence_bounds


def article_terms(semantic):
    """The words that name a test article: the labels, aliases and query terms of the
    registry's ``Sample`` class, and its mentions in the query language."""
    meta = getattr(semantic, "class_metadata", {}).get("Sample", {}) or {}
    terms = [meta.get("label"), *meta.get("aliases", []), *meta.get("query_terms", [])]
    terms += getattr(semantic, "target_mentions", {}).get("Sample", [])
    return sorted({t.strip().lower() for t in terms if t and t.strip()}, key=lambda t: (-len(t), t))


def article_subject_cue(text, semantic):
    """A test article heads the subject of the passive of an applied step in one clause
    ("Four specimens of the second pour were heated"): the nouns are the registry's
    ``Sample`` class, the verbs ``statement_integrity.APPLIED_STEP_VERBS``, and the
    relation is read by ``clause_cues.passive_subject_heads`` with no limit on the words
    between them. False when the registry names no test article."""
    from nasa_fire_ai.ingestion.statement_integrity import APPLIED_STEP_VERBS

    terms = article_terms(semantic)
    return bool(terms) and clause_cues.passive_subject_heads(text, terms, APPLIED_STEP_VERBS)


def validate_statement(item, record, spans, entities, document, semantic, evidence, package):
    """Validate one statement proposal; raises on rejection."""
    from nasa_fire_ai.ingestion.scientific_scope import page_continuation_context

    edge = page_edge_prefix(item["text"], evidence, spans)
    if edge:
        # "Annual Workshop on Thermal Devices 6
        # Figure 4 - ... Bench checks ...": the page edge
        # and a caption line before the sentence are not part of
        # it; the sentence and its support start after them.
        item["text"] = item["text"][len(edge) :]
        for s in spans:
            at = s["quote"].find(item["text"][:40])
            if at > 0:
                s.update(start=s["start"] + at, quote=s["quote"][at:])
        record["page_edge_removed"] = {
            "removed": edge,
            "basis": "RUNNING_PAGE_HEADER_BEFORE_SENTENCE",
        }
    tail = page_edge_suffix(item["text"], evidence)
    if tail:
        # The running footer, its date and page number, and the
        # page's next block after a whole sentence are not part of
        # it; the sentence and its support end before them.
        item["text"] = item["text"][: len(item["text"]) - len(tail)]
        footer = tail.strip().split("\n")[0].strip()
        for s in spans:
            at = s["quote"].find(footer)
            if at > 0:
                kept = s["quote"][:at].rstrip()
                s.update(end=s["start"] + len(kept), quote=kept)
        record["page_edge_removed_after"] = {
            "removed": tail,
            "basis": "RUNNING_PAGE_FOOTER_AFTER_SENTENCE",
        }
    continuation = page_continuation_context(spans, evidence)
    if continuation and item["epistemic"] != "documentary_context":
        record["status"] = "UNRESOLVED"
        record["reasons"].append("CROSS_PAGE_SENTENCE_CONTINUATION_REQUIRES_REVIEW")
        record["source_continuation_context"] = continuation
    exact = next(
        (
            {
                **recover_span(
                    evidence[s["evidence_id"]]["text"],
                    item["text"],
                    s["start"] if normalized(item["text"]) == normalized(s["quote"]) else None,
                ),
                "evidence_id": s["evidence_id"],
            }
            for s in spans
            if normalized(item["text"]) in normalized(s["quote"])
        ),
        None,
    )
    if not exact:
        raise ValueError("STATEMENT_NOT_SUPPORTED_LITERAL_SPAN")
    item["text"] = exact["span"]
    record["statement_location"] = {
        "evidence_id": exact["evidence_id"],
        "start": exact["start"],
        "end": exact["end"],
    }
    from nasa_fire_ai.ingestion.statement_integrity import (
        DATA_PROVENANCE,
        HOLD_CHECKS,
        count_conflict,
        documentary_pointer,
        documented_observation,
        fragment_context,
        observation_cue,
        procedure_without_interpretation,
        procedure_without_outcome,
        progressive_clause,
        purpose_marked,
        reported_outcome,
        rule_or_caveat,
        stated_criterion,
        validity_caveat,
    )
    from nasa_fire_ai.ingestion.study_attribution import (
        _preceding_sentences,
        cited_same_anaphor,
        cited_table_reference,
    )
    from nasa_fire_ai.ingestion.table_continuity import table_region_rows

    # Whole printed table rows are table content; their values
    # stay in row-bound cell records, never one prose claim.
    if table_region_rows(item["text"], document):
        raise ValueError("TABLE_REGION_IS_NOT_A_STATEMENT")
    cited_reading = (
        cited_table_reference(spans, document)
        if item["epistemic"] == "measured_observation" and item["study"] == "current"
        else None
    )
    if cited_reading:
        # "The values given in Table 3 suggest ... The stiffness of
        # the same alloy rises ...": whatever subject was
        # proposed, data read from a cited table are not this
        # study's own observation.
        record["status"] = "UNRESOLVED"
        record["reasons"].append("CITED_TABLE_READING_IS_NOT_CURRENT_OBSERVATION")
        record["cited_context"] = cited_reading
    # Narrative of what was done next asserts no study result.
    if item["epistemic"] == "documentary_context" and (
        documented_observation(item["text"]) and reported_outcome(item["text"])
    ):
        # "The final photo ... shows that the sheet is
        # folded" reports what was observed.
        record["status"] = "UNRESOLVED"
        record["reasons"].append("DOCUMENTARY_ROLE_REPORTS_AN_OBSERVATION")
    same_cited = (
        cited_same_anaphor(spans, document)
        if item["study"] == "current" and item["epistemic"] != "documentary_context"
        else None
    )
    if same_cited:
        # "The results appear in Table 2 [5]. ... The same
        # blends were then run ...": the cited work, again.
        record["status"] = "UNRESOLVED"
        record["reasons"].append("SAME_ANAPHOR_CONTINUES_CITED_WORK")
        record["cited_context"] = same_cited
    fragment = fragment_context(item["text"], record["statement_location"], evidence)
    if fragment:
        record["status"] = "UNRESOLVED"
        record["reasons"].append("STATEMENT_IS_NOT_WHOLE_SOURCE_SENTENCE")
        record["source_fragment_context"] = fragment
    header = next(
        (
            h
            for h in running_headers(evidence)
            # Printed beside its page number, as the page edge prints it,
            # or opening or closing the passage as the page edge does.
            if re.search(
                rf"{re.escape(h)}\s+\d+\b|\b\d+\s+{re.escape(h)}",
                normalized(item["text"]),
            )
            or (
                len(h.split()) >= 5
                and (
                    normalized(re.sub(r"\d+", " ", item["text"])).startswith(h)
                    or normalized(re.sub(r"\d+", " ", item["text"]))
                    .rstrip(" ,.")
                    .endswith(h.rstrip(" ,."))
                )
            )
        ),
        None,
    )
    if header:
        # "Annual Workshop on Thermal Devices 5
        # Cooling Loop Unit ... was mounted": the page's running
        # header is not part of the sentence.
        record["status"] = "UNRESOLVED"
        record["reasons"].append("STATEMENT_INCLUDES_A_RUNNING_PAGE_HEADER")
        record["running_page_header"] = header
    if re.match(r"\s*[a-z)\]]", item["text"]) or re.search(
        r"[\w.+-]+@[\w-]+\.[\w.]+", item["text"]
    ):
        # "rise of pressure) to bring the gas ...": a passage that
        # starts inside a sentence; an e-mail line is a contact block.
        record["status"] = "UNRESOLVED"
        record["reasons"].append("STATEMENT_IS_NOT_WHOLE_SOURCE_SENTENCE")
    if item["epistemic"] == "measured_observation" and (
        purpose_marked(item["text"]) or procedure_without_outcome(item["text"])
    ):
        # "A photo was taken so as to show ..." and "Each was
        # pressed with 20 N" are what was done, not what was observed.
        record["status"] = "UNRESOLVED"
        record["reasons"].append("OBSERVATION_DESCRIBES_A_PROCEDURE")

    def previous_sentence():
        found = _preceding_sentences(spans[0], document, 1) if spans else []
        return found[-1] if found else ""

    def printed_clause():
        """The clause of the printed line that governs the statement: read from the evidence."""
        if not spans:
            return ""
        page = evidence[spans[0]["evidence_id"]]["text"]
        start = spans[0]["start"]
        first = page.rfind("\n\n", 0, start)
        last = page.find("\n\n", start)
        block = page[0 if first < 0 else first + 2 : len(page) if last < 0 else last]
        begin, end = sentence_bounds(page, start, block)
        sentence = page[begin:end]
        from nasa_fire_ai.ingestion.clause_cues import governing_clause

        return governing_clause(sentence, start - begin) or sentence

    context = {"item": item, "clause": printed_clause}
    # The held-for-review checks a role is bound to (``Role.holds``), each behind its own flag.
    for name in ROLES[item["epistemic"]].holds:
        test, reason, enabled = HOLD_CHECKS[name]
        if enabled() and test(item["text"], previous_sentence, context):
            record["status"] = "UNRESOLVED"
            record["reasons"].append(reason)
    if item["epistemic"] == "measured_observation" and re.search(
        r"\b(?:calorimeter|instrument|gauge|meter|sensor|transducer|thermocouple"
        r"|data\s+system|display)s?\s+(?:displayed|displays|recorded|records"
        r"|reported|reports|indicated|indicates|reads|read\s+out)\s+the\b",
        item["text"],
        re.IGNORECASE,
    ):
        # "the meter displayed the mean flow value": how
        # a result is read, not a result read.
        record["status"] = "UNRESOLVED"
        record["reasons"].append("OBSERVATION_DESCRIBES_A_PROCEDURE")
    if item["epistemic"] == "measured_observation":
        # A recording or acceptance rule, a validity caveat and a
        # pointer to where results are printed are not observations.
        for test, reason in (
            (stated_criterion, "OBSERVATION_STATES_A_CRITERION"),
            (rule_or_caveat, "OBSERVATION_STATES_A_RULE_OR_CAVEAT"),
            (documentary_pointer, "OBSERVATION_IS_A_DOCUMENTARY_POINTER"),
        ):
            if test(item["text"]):
                record["status"] = "UNRESOLVED"
                record["reasons"].append(reason)
    if item["epistemic"] in {
        "tentative_interpretation",
        "author_reported_conclusion",
    } and validity_caveat(item["text"]):
        # The conditions under which a comparison holds are a
        # caveat on the analysis, not an interpretation of it.
        record["status"] = "UNRESOLVED"
        record["reasons"].append("INTERPRETATION_STATES_A_VALIDITY_CAVEAT")
    if item["epistemic"] in {
        "tentative_interpretation",
        "author_reported_conclusion",
    } and procedure_without_interpretation(item["text"]):
        record["status"] = "UNRESOLVED"
        record["reasons"].append("INTERPRETATION_DESCRIBES_A_PROCEDURE")
    if item["epistemic"] == "tentative_interpretation" and not re.search(
        r"\b(?:suggest\w*|speculat\w*|possib\w*|likely|probabl\w*|may|might|could"
        r"|appear\w*|seem\w*|indicat\w*|determin\w*|believ\w*|expect\w*|assum\w*"
        r"|estimat\w*|presum\w*|impl(?:y|ies|ied)|due\s+to|because|therefore|thus"
        r"|hence|attribut\w*|explain\w*|concern\w*|would|should|if|unless|whether"
        r"|thought|predict\w*|caus\w*|so|approximat\w*)\b",
        item["text"],
        re.IGNORECASE,
    ):
        # "Quartex-B® consists of 35% Copper and 65% resin"
        # states a fact; a tentative interpretation hedges or infers.
        record["status"] = "UNRESOLVED"
        record["reasons"].append("TENTATIVE_INTERPRETATION_STATES_NO_INFERENCE")
    if item["epistemic"] == "experimental_configuration" and validity_caveat(item["text"]):
        # Nor is it how the test was set up.
        record["status"] = "UNRESOLVED"
        record["reasons"].append("CONFIGURATION_STATES_A_VALIDITY_CAVEAT")
    conflict = (
        count_conflict(record["statement_location"], evidence)
        if item["epistemic"] == "measured_observation"
        else None
    )
    if conflict:
        record["status"] = "UNRESOLVED"
        record["reasons"].append("SOURCE_PRINTS_CONFLICTING_COUNTS")
        record["source_conflict_context"] = conflict
    if item["epistemic"] != "documentary_context" and normalized(item["text"]) in {
        normalized(package["title"]),
        *[normalized(h["quote"]) for h in document.get("layout_headings", {}).values()],
    }:
        raise ValueError("DOCUMENT_HEADING_IS_NOT_OBSERVATION")
    if item["text"].rstrip().endswith(":"):
        # A line that opens a list ("Selected panel types:") is the lead
        # of its items, not a statement of its own.
        raise ValueError("STATEMENT_IS_A_LIST_LEAD")
    if list_items_enabled():
        if list_lead_with_items(item["text"], only_lead=list_items_mode() == "2"):
            # A lead together with its items: the items complete no statement.
            raise ValueError("STATEMENT_IS_A_LIST_LEAD")
        if (
            item["epistemic"] == DOCUMENTARY_ROLE
            and len(list_items(item["text"])) == 1
            and LIST_MARKER.match(item["text"].lstrip())
            and not item_has_clause(item["text"])
        ):
            # A single verbless item states nothing for the role that records
            # what the document is or points to.
            record["status"] = "UNRESOLVED"
            record["reasons"].append("STATEMENT_LIST_ITEM_HAS_NO_CLAUSE")
    errors = role_errors(item)
    if errors:
        raise ValueError(";".join(errors))
    if item["epistemic"] == PROVENANCE_ROLE and not DATA_PROVENANCE.search(item["text"]):
        # Complete only when the clause itself says where data come from.
        raise ValueError("DATA_PROVENANCE_NOT_EXPLICIT_IN_SOURCE")
    facet_holds = facet_review("statements", item)[1]
    if facet_holds:
        # The clause does not settle the claimed facet: held.
        record["status"] = "UNRESOLVED"
        record["reasons"] += [r for r in facet_holds if r not in record["reasons"]]
    derivation = original_derivation_context(item["text"], spans, evidence)
    if derivation and item["epistemic"] in {
        "measured_observation",
        "derived_quantity",
    }:
        record["epistemic_context"] = {
            "basis": "NEAREST_ORIGINAL_DERIVATION_OF_SAME_VARIABLE",
            "support": [derivation],
        }
        spans += locate([derivation], evidence)
        if item["epistemic"] == "measured_observation":
            record["status"] = "UNRESOLVED"
            record["reasons"].append("DERIVED_CONTEXT_IS_NOT_DIRECT_OBSERVATION")
    if item["class_id"] not in semantic.information_classes:
        record["status"] = "UNRESOLVED"
        record["reasons"].append("UNREGISTERED_INFORMATION_CLASS")
    allowed = CLASS_FLEXIBLE_ROLES.get(item["epistemic"]) or (
        (STATEMENT_CLASSES[item["epistemic"]],) if item["epistemic"] in STATEMENT_CLASSES else ()
    )
    if allowed and not any(has_class(item["class_id"], cls, semantic) for cls in allowed):
        raise ValueError("CLASS_EPISTEMIC_CONTRADICTION")
    if any(s not in entities for s in item["subjects"]):
        raise ValueError("UNKNOWN_STATEMENT_ENDPOINT")
    found_facets = facets("statements", item) or {}
    if any(entities[s]["class_id"] == "ExperimentalRun" for s in item["subjects"]) and (
        found_facets.get("statement_type") in {"plan", "goal", "test_criterion", "design_criterion"}
        or (
            found_facets.get("statement_type") == "configuration"
            and (found_facets.get("modality") != "actual" or execution(item["text"]) == "not_done")
        )
    ):
        # A plan, goal or criterion, or a configuration printed as not
        # yet done, names no executed run as its subject.
        raise ValueError("PLANNED_STATEMENT_ATTRIBUTED_TO_EXECUTED_RUN")
    if plan_goal_facets_enabled() and item["epistemic"] in PLAN_GOAL_ROLES:
        # A plan or a goal is a complete record with its facets explicit,
        # and its computed facets never say executed.
        plan_facets = record_facets({"kind": "statements", "proposal": item})
        if plan_facets is None or plan_facets.get("execution_status") == "executed":
            raise ValueError("PLAN_OR_GOAL_READ_AS_EXECUTED")
        record["facets"] = plan_facets
    if (
        found_facets.get("statement_type") == "configuration"
        and found_facets.get("modality") == "actual"
        and execution(item["text"]) == "not_done"
    ):
        # Read as done but printed as future, planned, conditional or
        # prescribed: held for review on any subject, never published.
        record["status"] = "UNRESOLVED"
        record["execution_reading"] = "not_done"
        record["reasons"].append("STATEMENT_PRINTED_AS_NOT_DONE_REQUIRES_REVIEW")
    experimental = {
        "Investigation",
        "ExperimentFamily",
        "ExperimentalRun",
        "Sample",
    }
    background = item.get("scope") == "background"
    if background:
        if item["epistemic"] not in BACKGROUND_ROLES:
            raise ValueError("BACKGROUND_SCOPE_CONTRADICTS_ROLE")
        # The field's background describes no experiment of this study:
        # no experimental subject, scoped to the document only.
        record["proposed_subjects"] = list(item["subjects"])
        item["subjects"] = []
        record["scope_context"] = {
            "basis": "SOURCE_STATES_BACKGROUND_OF_THE_FIELD",
            "scope_is_individual_run": False,
            "distributes_to_members": False,
        }
    if item.get("basis") and item["basis"] not in allowed_bases(item["epistemic"]):
        # A10: the basis the source states must be one the role admits (a simulated result is
        # never a measurement).
        raise ValueError("EVIDENCE_BASIS_CONTRADICTS_ROLE")
    if item.get("execution") == "ongoing" and (
        item["epistemic"] not in ongoing_roles() or stated_modality(item)
    ):
        raise ValueError("ONGOING_EXECUTION_CONTRADICTS_ROLE")
    if (
        item.get("execution") == "ongoing"
        and ongoing_activity_roles_enabled()
        and not progressive_clause(item["text"])
    ):
        # V2: ongoing is accepted only when the governing clause is progressive.
        raise ValueError("ONGOING_EXECUTION_NOT_PROGRESSIVE_IN_SOURCE")
    if (
        not background
        and item["epistemic"] not in {"documentary_context", PROVENANCE_ROLE}
        and (
            not item["subjects"]
            or any(entities[s]["class_id"] not in experimental for s in item["subjects"])
        )
    ):
        record["proposed_subjects"] = list(item["subjects"])
        scoped = original_heading_scope(spans, entities, document)
        if scoped:
            subject, proof = scoped
            record["scope_context"] = {
                "basis": "EXACT_ORIGINAL_EXPERIMENT_GROUP_HEADING",
                "support": proof,
                "proposed_study": item["study"],
            }
            item["subjects"] = [subject]
            item["study"] = entities[subject]["study"]
            spans += locate(proof, evidence)
        elif (
            item["study"] == "current"
            # A material description is not the study's own
            # observation merely because it is printed there.
            and (
                item["epistemic"] != "measured_observation"
                or (
                    observation_cue(item["text"])
                    # Data read from a cited table are not
                    # this study's own observation.
                    and not cited_table_reference(spans, document)
                )
            )
            and (
                root := document_investigation(
                    spans,
                    entities,
                    document,
                    own_body=item["epistemic"] in {"guidance", "normative_requirement"},
                )
            )
        ):
            # The paper's own research section, with one current
            # investigation, scopes the statement to that study;
            # the named materials stay as proposed subjects only.
            record["scope_context"] = {
                "basis": "ORIGINAL_RESEARCH_SECTION_AT_DOCUMENT_INVESTIGATION_SCOPE",
                "support": entities[root]["support"],
                "scope_is_individual_run": False,
                "distributes_to_members": False,
            }
            item["subjects"] = [root]
        else:
            item["subjects"] = []
            record["status"] = "UNRESOLVED"
            record["reasons"].append("STATEMENT_REQUIRES_EXPERIMENTAL_SCOPE")
    if (
        item["epistemic"] in {"measured_observation", "experimental_configuration"}
        and spans
        and all(background_or_analysis_span(s, document) for s in spans)
    ):
        # An observation or setup printed only in background, theory or
        # analysis is not this study's own experiment.
        record["status"] = "UNRESOLVED"
        record["reasons"].append("SUPPORT_ONLY_IN_BACKGROUND_OR_ANALYSIS_SECTION")
    if (
        item["epistemic"] == "derived_quantity"
        and not derivation
        and not re.search(
            r"\b(?:deriv\w*|calculat\w*|infer\w*|fit(?:s|ted)?|gradient|model\w*|simulat\w*|predict\w*)\b",
            item["text"],
            re.IGNORECASE,
        )
    ):
        record["status"] = "UNRESOLVED"
        record["reasons"].append("DERIVATION_NOT_ESTABLISHED_IN_ORIGINAL_PASSAGE")
    configuration_cue = r"\b(?:initial\w*|set\w*|configur\w*|conditions?|maintain\w*|gravity|pressure|temperature|flow|atmospher\w*|oxygen|introduc\w*|ignit\w*|chamber|(?:samples?|specimens?)\s+(?:were|are|was|is)\s+(?:mounted|placed|tested|burned)|(?:was|were)\s+(?:used|employed|applied|added|injected|installed))\b"
    if os.getenv("SCIENCE_CONTRACT_C2", "1") == "1":
        if os.getenv("SCIENCE_PURPOSE_READER", "1") == "1":
            # Plural setting nouns, and the passive of a set-up verb:
            # calibration and adjustment of a measuring system (VIM,
            # JCGM 200:2012, 2.39 and 3.11) and the verbs of putting
            # (Levin 1993, class 9.1), as clause_cues.SETUP_VERBS.
            # Testing itself is execution, not set-up.
            from nasa_fire_ai.ingestion import clause_cues as _cc

            configuration_cue += r"|\b(?:pressures|temperatures|flows)\b" + "|" + _cc.SETUP_PASSIVE
        else:
            # Plural setting nouns also state a configuration (contract
            # candidate C2).
            configuration_cue += r"|\b(?:pressures|temperatures|flows)\b"
    if (
        item["epistemic"] == "experimental_configuration"
        and not re.search(configuration_cue, item["text"], re.IGNORECASE)
        and not (
            # The noun-plus-verb cue above, read by class: a test article
            # that heads the subject of an applied step's passive.
            os.getenv("SCIENCE_CONTRACT_C2", "1") == "1"
            and os.getenv("SCIENCE_PURPOSE_READER", "1") == "1"
            and article_subject_cue(item["text"], semantic)
        )
    ):
        record["status"] = "UNRESOLVED"
        record["reasons"].append("CONFIGURATION_ROLE_NOT_ESTABLISHED_IN_ORIGINAL_PASSAGE")
    change_text = item["text"]
    if os.getenv("SCIENCE_PURPOSE_READER", "1") == "1":
        # A change verb inside a purpose clause is an aim, not an
        # observed change (the one purpose reader).
        from nasa_fire_ai.ingestion import clause_cues

        change_text = clause_cues.strip_purpose(change_text)
    if (
        item["epistemic"] == "experimental_configuration"
        and re.search(
            r"\b(?:increas\w*|decreas\w*|grows?|shrinks?|rises?|falls?)\b",
            change_text,
            re.IGNORECASE,
        )
        and not re.search(
            r"\b(?:controlled|programmed|intentionally|imposed|set\s+to|configured|varied)\b",
            item["text"],
            re.IGNORECASE,
        )
    ):
        record["status"] = "UNRESOLVED"
        record["reasons"].append("CHANGING_OBSERVATION_IS_NOT_ESTABLISHED_CONFIGURATION")
    from nasa_fire_ai.ingestion.statement_integrity import stated_criterion

    # "A part is deemed to have cleared ... when ..." is an acceptance
    # or recording rule, not how the apparatus was configured.
    if item["epistemic"] == "experimental_configuration" and stated_criterion(item["text"]):
        record["status"] = "UNRESOLVED"
        record["reasons"].append("CONFIGURATION_STATEMENT_STATES_A_CRITERION")
    for subject in item["subjects"]:
        section_proof = group_section_support(subject, spans, entities, document)
        from nasa_fire_ai.ingestion.scientific_scope import figure_group_support

        figure_proof = figure_group_support(subject, spans, entities, document)
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
        if document_conclusion_scope(subject, spans, entities, document):
            record["scope_context"] = {
                "basis": "ORIGINAL_CONCLUSION_AT_LITERAL_DOCUMENT_INVESTIGATION_SCOPE",
                "support": entities[subject]["support"],
                "scope_is_individual_run": False,
            }
        elif document_statement_scope(subject, spans, entities, document):
            record["scope_context"] = {
                "basis": "ORIGINAL_RESEARCH_SECTION_AT_DOCUMENT_INVESTIGATION_SCOPE",
                "support": entities[subject]["support"],
                "scope_is_individual_run": False,
                "distributes_to_members": False,
            }
        if subject in entities and not applicable(subject, spans, entities, document):
            proof = local_investigation_antecedent(subject, spans, entities, document)
            if proof:
                spans += locate(proof, evidence)
                record["scope_context"] = {
                    "basis": "UNIQUE_ORIGINAL_PARAGRAPH_STUDY_ANTECEDENT",
                    "support": proof,
                }
    if (
        item["subjects"]
        and item["study"] == "current"
        and not all(
            applicable(s, spans, entities, document)
            or document_statement_scope(s, spans, entities, document)
            for s in item["subjects"]
        )
        and all(
            s in entities
            and (
                # A proposed group the validator holds (a slide
                # title proposed as a group), or a supported group
                # this passage is not shown to belong to, gives the
                # passage no scope of its own; the study's does,
                # and the group stays a proposed subject only. A
                # supported individual run is never rescoped.
                (
                    entities[s]["class_id"] == "ExperimentFamily"
                    or (
                        entities[s].get("validation_status") != "SOURCE_SUPPORTED"
                        and entities[s]["class_id"] == "ExperimentalRun"
                    )
                )
                or (
                    # Specimens, or for a documentary statement (a
                    # figure of the material) the material itself.
                    (
                        entities[s]["class_id"] == "Sample"
                        or (
                            item["epistemic"] == "documentary_context"
                            and entities[s]["class_id"] == "Material"
                        )
                    )
                    # The passage itself names the specimens or their
                    # material ("the third lot of Copper-filled
                    # resin"); a line-break hyphen is not a space. A
                    # set-up step on specimens is the study's own
                    # procedure whether or not it names them.
                    and (
                        (
                            item["epistemic"] == "experimental_configuration"
                            and entities[s]["class_id"] == "Sample"
                        )
                        or mentions(
                            re.split(r"\s*\(", entities[s]["label"])[0],
                            re.sub(r"(?<=\w)-\s+(?=\w)", "-", item["text"]),
                        )
                    )
                )
            )
            for s in item["subjects"]
        )
        and (
            item["epistemic"] != "measured_observation"
            or (
                observation_cue(item["text"])
                and reported_outcome(item["text"])
                and not cited_table_reference(spans, document)
            )
        )
        and (
            root := document_investigation(
                spans,
                entities,
                document,
                own_body=item["epistemic"] in {"guidance", "normative_requirement"},
            )
        )
    ):
        # Specimens whose own group passage is not established are
        # treated like named materials: the paper's own research
        # section scopes the statement to the study, and the
        # specimens stay as proposed subjects only.
        record.setdefault("proposed_subjects", list(item["subjects"]))
        record["scope_context"] = {
            "basis": "ORIGINAL_RESEARCH_SECTION_AT_DOCUMENT_INVESTIGATION_SCOPE",
            "support": entities[root]["support"],
            "scope_is_individual_run": False,
            "distributes_to_members": False,
        }
        item["subjects"] = [root]
    # A background statement takes no experimental subject by design.
    if not background and (
        not item["subjects"]
        or not all(
            applicable(s, spans, entities, document)
            or document_statement_scope(
                s,
                spans,
                entities,
                document,
                # Only a passage that says where data come from or
                # where they are printed names its sources by design.
                cited_named=(
                    item["epistemic"] == "documentary_context"
                    and bool(
                        DATA_PROVENANCE.search(item["text"]) or documentary_pointer(item["text"])
                    )
                )
                # Provenance names its sources by design, read only by
                # the data-provenance reader, never a mere pointer.
                or (
                    item["epistemic"] == PROVENANCE_ROLE
                    and bool(DATA_PROVENANCE.search(item["text"]))
                )
                # What the paper itself recommends or requires is its own.
                or item["epistemic"] in {"guidance", "normative_requirement"},
            )
            or (
                # The source-defined test article, named in context by
                # its acronym (decision 2), recorded as the basis.
                (link := test_article_named_by_acronym(s, spans, entities, document))
                and record.setdefault("scope_context", link) is not None
            )
            or (
                # The one heading governing the statement names it.
                (headed := heading_names_subject(s, spans, entities, document))
                and record.setdefault("scope_context", headed) is not None
            )
            for s in item["subjects"]
        )
    ):
        record["status"] = "UNRESOLVED"
        record["reasons"].append("STATEMENT_SUBJECT_APPLICABILITY_UNRESOLVED")
        # Only where the base rule would have accepted the subject.
        conflict = heading_subject_v3_enabled() and next(
            (
                title
                for s in item["subjects"]
                if heading_rule_accepts(s, spans, entities, document)
                and (title := heading_subject_conflict(s, spans, entities, document))
            ),
            None,
        )
        if conflict:
            record["reasons"].append(HEADING_SUBJECT_CONFLICT)
            record["heading_subject_conflict"] = conflict
    if any(s not in entities for s in item["subjects"]):
        raise ValueError("UNKNOWN_STATEMENT_ENDPOINT")
    for subject in item["subjects"]:
        entity = entities[subject]
        if entity["class_id"] in {"ExperimentalRun", "ExperimentFamily"} and any(
            e["class_id"] == entity["class_id"]
            and e["source_id"] == spans[0]["source_id"]
            and key not in item["subjects"]
            and normalized(e["label"]) != normalized(entity["label"])
            and mentions(e["label"], item["text"])
            for key, e in entities.items()
        ):
            record["status"] = "UNRESOLVED"
            record["reasons"].append("STATEMENT_MULTI_RUN_SCOPE_REQUIRES_REVIEW")
    if item["study"] == "current" and re.search(
        r"\b(?:consistent\s+with|previous|prior|earlier|reported\s+by)\b.*\[\d",
        item["text"],
        re.IGNORECASE | re.DOTALL,
    ):
        record["status"] = "UNRESOLVED"
        record["reasons"].append("CITED_STUDY_APPLICABILITY_REQUIRES_REVIEW")
    if item["study"] != "current":
        record["status"] = "UNRESOLVED"
        record["reasons"].append("CURRENT_OR_CITED_STUDY_UNRESOLVED")
    for subject in item["subjects"]:
        if subject in entities and entities[subject]["study"] != item["study"]:
            raise ValueError("CURRENT_CITED_ATTRIBUTION_CONTRADICTION")
    if (
        item["epistemic"] == "author_reported_conclusion"
        # The model's background mark says what the statement is; a
        # conclusion section or verb is not expected of it.
        and item.get("scope") != "background"
        and not any(
            re.search(r"conclusions?", section_for_span(s, document), re.IGNORECASE) for s in spans
        )
        and not re.search(
            r"\b(?:conclud\w*|results\s+(?:show|indicate|are\s+applicable)|demonstrat\w*|achieved|indicat\w*|(?:is|are)\s+feasible|this\s+(?:shows|indicates))\b",
            item["text"],
            re.IGNORECASE,
        )
    ):
        record["status"] = "UNRESOLVED"
        record["reasons"].append("AUTHOR_ROLE_REQUIRES_CONTEXT_REVIEW")
    record["scope"] = [entities[s]["id"] for s in item["subjects"] if s in entities]
