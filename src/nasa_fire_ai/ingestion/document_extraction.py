"""Bounded scientific interpretation into the existing isolated curation package.

The model supplies proposals. Literal source checks, epistemic safeguards and
subject applicability are computed independently. Nothing grants approval.
"""

import copy
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, wait
from dataclasses import asdict
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

from openai import OpenAIError

from nasa_fire_ai.ingestion.abbreviations import (  # noqa: F401
    segmentation_input_view,
    segmentation_view,
    split_by_view,
)
from nasa_fire_ai.ingestion.clause_cues import (  # noqa: F401
    ENDOPHORIC_MARKER,
    SELF_DEIXIS,
    SETTING_CUE,
    execution,
    governing_clause,
    heads_object_of_from,
    locate_value,
    setting_mention,
    strip_frames,
)
from nasa_fire_ai.ingestion.document_memo import document_memo
from nasa_fire_ai.ingestion.document_structure import (
    context_for,
    identity,
    model_windows,
    structure,
    table_records,
)
from nasa_fire_ai.ingestion.extraction_followup import (  # noqa: F401
    MISSING_FIELD_WORDS,
    MISSING_FIELDS_PER_WINDOW,
    grounded_entities,
    missing_fields,
    unlinked_group_subsections,
)
from nasa_fire_ai.ingestion.extraction_parsing import (  # noqa: F401
    completed_json_prefix,
    expand_entity_refs,
    merge_output,
    parse_model_output,
    parse_stage_output,
    proposal_identity,
    stable_entity_keys,
    without_unset_modality,
)
from nasa_fire_ai.ingestion.extraction_request import (  # noqa: F401
    EVIDENCE_BASIS_CONTRACT,
    PROTOCOL_SYSTEM,
    STAGE_INSTRUCTIONS,
    STAGES,
    VALUE_ORIGIN_CONTRACT,
    focused_schema,
    referenced_definitions,
    source_anchors,
    stage_prompt,
    stage_schema,
    unique_json_fields,
)
from nasa_fire_ai.ingestion.extraction_resources import (  # noqa: F401
    ANTHROPIC_REQUEST_CONTEXT_CEILING,
    ExtractionBudget,
    ProviderEnvelope,
    never_billed,
    output_size,
    reasoning_size,
    record_discarded_prefetch,
    request_context_limit,
    segment_size,
    split_window,
    timeout_for,
)
from nasa_fire_ai.ingestion.extraction_schema import (  # noqa: F401
    CONTRACT,
    PROPOSE_NEW_CLASS,
    PROPOSE_NEW_RELATION,
    Concept,
    Entity,
    Modality,
    Output,
    ProposedTerm,
    Quantity,
    Relation,
    Span,
    Statement,
    Strict,
)
from nasa_fire_ai.ingestion.extraction_validation import (  # noqa: F401
    _VALIDATIONS,
    CONCLUSION_ROLE_HOLDS,
    INFERENCE,
    ROLE_RECOVERY,
    article_subject_cue,
    article_terms,
    recover_conclusion_roles,
    recover_statement_roles,
    state_settled_roles,
    validate_output,
    validated_output,
)
from nasa_fire_ai.ingestion.narrative_candidates import literal_candidates
from nasa_fire_ai.ingestion.ontology_context import relation_signatures  # noqa: F401
from nasa_fire_ai.ingestion.printed_layout import (  # noqa: F401
    _EQUATION_HEADINGS,
    BACKGROUND_SECTION_ROLE,
    CONTINUING_WORDS,
    NUMBERED_HEADING_LINE,
    OUTLINE_MARKER,
    PRINTED_CAPTION_LINE,
    PRINTED_EQUATION,
    SENTENCE_VERB,
    _page_texts,
    acronym_printed_form,
    background_or_analysis_span,
    caption_only_label,
    document_conclusion_scope,
    equation_headings,
    first_page_line,
    governing_major,
    group_section_support,
    heading_level,
    heading_outline_name,
    heading_scheme,
    heading_title,
    joined_page_texts,
    line_units,
    outline_marker_kind,
    page_edge_lines,
    page_edge_prefix,
    page_edge_suffix,
    page_headings,
    page_title,
    previous_page_ends_a_sentence,
    printed_heading_before,
    reads_as_sentence,
    running_headers,
    section_for_span,
    slide_deck,
    slide_heading,
    subsection_group,
    table_column_prints_value,
    titled_pages,
    under_group_heading,
)
from nasa_fire_ai.ingestion.proposal_states import (  # noqa: F401
    adopt_proposed_term,
)
from nasa_fire_ai.ingestion.quantity_naming import (  # noqa: F401
    CONDITION_CLAUSE,
    DIMENSION_NOUNS,
    NAME_STOP_WORDS,
    NAME_VALUE_LINK,
    PRONOUN_START,
    SETTING_VERB_AFTER,
    SETTING_VERB_BEFORE,
    STATE_QUALIFIERS,
    anaphoric_subject,
    applied_column_value,
    continued_sentence,
    explicit_quantity_derivation,
    heading_binding,
    model_printed_name,
    native_quantity_expression,
    original_heading_scope,
    printed_setting_name,
    printed_value_name,
    property_proposal,
    qualified_material_heading,
    quantity_expression_pattern,
    quantity_name_value_binding,
    resolve_source_property,
    setting_verb_of_unit_dimension,
    shared_stem,
    source_dimension_adjectives,
    staged_name_syntax,
    value_is_applied_input,
    value_sentences,
)
from nasa_fire_ai.ingestion.quantity_validation import (  # noqa: F401
    CONDITION_CLASSES,
    NOT_A_SETTING_CUE,
    SETTING_ROLE_CUE,
    SUBJECT_HOLDS,
    SUBJECT_REJECTIONS,
    TEST_ARTICLE_ALIAS_HOLD,
    validate_quantity,
    validate_quantity_subject,
)
from nasa_fire_ai.ingestion.relation_contracts import RELATION_ENDPOINTS
from nasa_fire_ai.ingestion.relation_registry import (
    relation_registry_prompt_enabled,
    relation_signature_listing,
)
from nasa_fire_ai.ingestion.scientific_coverage import (
    missing_fact_report,
    missing_fact_report_enabled,
)
from nasa_fire_ai.ingestion.scientific_facets import (  # noqa: F401
    BACKGROUND_FACET_FIELDS,
    BACKGROUND_ROLES,
    CLASS_FLEXIBLE_ROLES,
    ENVIRONMENT_VALUE_ROLES,
    ENVIRONMENT_VALUE_ROLES_V2,
    ONGOING_ROLES,
    PLAN_GOAL_ROLES,
    PROVENANCE_ROLE,
    ROLE_CHECK_WORDS,
    ROLE_MODALITIES,
    ROLE_OPTIONS,
    ROLE_STUDIES,
    ROLE_VOCABULARY,
    STATEMENT_CLASSES,
    background_facets_enabled,
    facet_errors,
    facet_review,
    facets,
    ongoing_activity_roles_enabled,
    plan_goal_facets_enabled,
    record_facets,
    request_role_vocabulary,
    role_definitions_v2_enabled,
    stated_modality,
    structured_provenance_enabled,
    value_origin_mark_enabled,
)
from nasa_fire_ai.ingestion.scientific_proposals import (
    deterministic_propositions,
    normative_instruction,
)
from nasa_fire_ai.ingestion.scientific_scope import (  # noqa: F401
    NON_RESEARCH_SECTION,
    PRESENTATION_FRAME,
    RESEARCH_SECTION,
    document_investigation,
    document_statement_scope,
    hold_mentioned_only_materials,
    local_investigation_antecedent,
    original_derivation_context,
    original_research_passage,
    outside_own_research,
    subject_label_names_material,
    test_article_named_by_acronym,
)
from nasa_fire_ai.ingestion.seed_terms import exclude_seed_terms, without_seed_aliases
from nasa_fire_ai.ingestion.semantic_candidates import candidate_hygiene_enabled, clean_candidates
from nasa_fire_ai.ingestion.source_spans import (  # noqa: F401
    contiguous_support,
    locate,
    mentions,
    normalized,
    recover_span,
)
from nasa_fire_ai.ingestion.statement_integrity import (  # noqa: F401
    role_errors,
)
from nasa_fire_ai.ingestion.statement_provenance import (  # noqa: F401
    PROVENANCE_EXAMPLE,
    PROVENANCE_SOURCE_CLASSES,
    provenance_clause_ok,
    provenance_source_ok,
    provenance_source_printed,
    provenance_source_staged,
    self_source,
    source_class,
    structure_provenance,
)
from nasa_fire_ai.ingestion.structural_candidates import (  # noqa: F401
    DIMENSION_NOUN,
    GROUP_VALUE,
    METHOD_SECTION,
    SERIES_NAME,
    group_subsection_quantity_candidates,
    heading_regions,
    recover_group_classes,
    structure_entity_candidates,
    structure_quantity_candidates,
    structure_relation_candidates,
    tested_at_clauses,
)
from nasa_fire_ai.ingestion.study_attribution import (  # noqa: F401
    cited_mention_outside_current_names,
)
from nasa_fire_ai.ingestion.subject_recognition import (  # noqa: F401
    HEADING_SUBJECT_CONFLICT,
    IDENTITY_BASES,
    MEDIUM_AFTER,
    MEDIUM_BEFORE,
    SUBJECT_CLASSES,
    applicable,
    binding_clauses,
    has_class,
    heading_names_subject,
    heading_rule_accepts,
    heading_subject_conflict,
    heading_subject_v3_enabled,
    identity_classes,
    label_binding_enabled,
    local_binding,
    material_tested_here,
    names_entity,
    printed_label_binding,
    printed_subject_recognition,
    quantity_scope_eligible,
    resolve_explicit_scopes,
    subject_forms,
    test_medium_only,
    tested_material_entity,
    v2_title,
)
from nasa_fire_ai.ingestion.value_origin import origin_audit, origin_check_enabled
from nasa_fire_ai.llm.interfaces import NvidiaStructuredClient
from nasa_fire_ai.llm.scientific_provider import ScientificTransportError, complete_scientific

# The endpoint classes each approved relation admits (``relation_contracts``). The
# validator rejects a contradiction; the model request states the same table so the
# model does not propose one.


def deterministic(segment, semantic):
    items = deterministic_propositions([segment], semantic, limit=10000)
    # Generic uncertainty markers extend the existing exact-sentence path.
    for m in re.finditer(
        r".+?(?:[.!?](?!\d)(?=\s|$)|$)", segmentation_input_view(segment["text"]), re.DOTALL
    ):
        quote = segment["text"][m.start() : m.end()].strip()
        if 12 <= len(quote) <= 1400 and normative_instruction(quote):
            items.append(
                {"quote": quote, "class_id": "Requirement", "evidence_id": segment["evidence_id"]}
            )
        if 12 <= len(quote) <= 1400 and re.search(
            r"\b(?:hypothes\w*|suggest\w*|may|might|future\s+work|results\s+(?:show|indicate))\b",
            quote,
            re.IGNORECASE,
        ):
            items.append(
                {
                    "quote": quote,
                    "class_id": "NASAConclusion",
                    "evidence_id": segment["evidence_id"],
                }
            )
    if re.search(r"conclusions?", segment["section"], re.IGNORECASE):
        for match in re.finditer(
            r".+?(?:[.!?](?!\d)(?=\s|$)|$)", segmentation_input_view(segment["text"]), re.DOTALL
        ):
            quote = segment["text"][match.start() : match.end()].strip()
            if 30 <= len(quote) <= 1400:
                items.append(
                    {
                        "quote": quote,
                        "class_id": "NASAConclusion",
                        "evidence_id": segment["evidence_id"],
                    }
                )
    result = Output()
    for item in items:
        quote, cls = item["quote"], item["class_id"]
        role = {
            "ReportedObservation": "measured_observation",
            "NASAConclusion": "author_reported_conclusion",
            "OpenQuestion": "open_question",
            "Requirement": "normative_requirement",
            "ExperimentalCondition": "experimental_configuration",
            "Intervention": "experimental_configuration",
        }.get(cls, "documentary_context")
        if re.search(
            r"\b(?:future\s+(?:work|research)|further\s+research)\b", quote, re.IGNORECASE
        ):
            cls, role = "OpenQuestion", "open_question"
        elif re.search(r"\bhypothes\w*\b", quote, re.IGNORECASE):
            cls, role = "NASAConclusion", "hypothesis"
        elif re.search(
            r"\b(?:may(?!\s+\d)|might|suggest\w*|likely|possibly)\b", quote, re.IGNORECASE
        ):
            cls, role = "NASAConclusion", "tentative_interpretation"
        elif re.search(r"\b(?:simulat\w*|predict\w*|numerical\s+model)\b", quote, re.IGNORECASE):
            role = "derived_quantity"
        elif cls == "NASAConclusion" and re.search(
            r"\b(?:were|was|have\s+been)\s+(?:performed|conducted|varied|maintained|measured)|\b(?:flow|oxygen|pressure)\b.*\b(?:turned|varied|measured)\b",
            quote,
            re.IGNORECASE,
        ):
            cls, role = "ExperimentalCondition", "experimental_configuration"
        result.statements.append(
            Statement(
                text=quote,
                class_id=cls,
                epistemic=role,
                support=[
                    Span(
                        evidence_id=segment["evidence_id"],
                        quote=quote,
                        start=segment["start"] + segment["text"].find(quote),
                    )
                ],
            )
        )
    return result.model_dump()


def extraction_semantic(service, package):
    """Inspect the existing RDF schema without activating proposed vocabulary."""
    import yaml

    from nasa_fire_ai.ingestion.semantic import approved_ontology
    from nasa_fire_ai.query.v2 import RelationDefinition

    semantic = service.property_registry(package)
    accessors = service.root / "domain/source_field_accessors.yaml"
    semantic.source_field_accessors = (
        yaml.safe_load(accessors.read_text()).get("fields", {}) if accessors.exists() else {}
    )
    ontology = approved_ontology(service.root)
    for cls, meta in ontology["classes"].items():
        metadata = semantic.class_metadata.setdefault(cls, {"target": True})
        metadata["approved_ontology_parents"] = list(meta["parents"])
        metadata["definition"] = meta["definition"]
        metadata["label"] = meta["label"]
        semantic.target_classes.add(cls)
    for rel in ontology["object_properties"]:
        if rel not in semantic.relations:
            semantic.register_relation(RelationDefinition(rel))
    semantic.ontology_datatype_properties = {
        name: dict(meta) for name, meta in ontology["datatype_properties"].items()
    }
    return semantic


def table_mapping_decisions(service, package, semantic):
    """Reuse approved source attributes before considering ontology extensions."""
    import yaml

    path = service.root / "domain/source_field_accessors.yaml"
    accessors = yaml.safe_load(path.read_text()).get("fields", {}) if path.exists() else {}
    result = []
    for table in package["tables"]:
        for column in table["columns"]:
            label = re.sub(r"\([^)]*\)", "", column["label"]).strip()
            existing = next(
                (key for key in accessors if key.replace("_", " ") == label.lower()), None
            )
            kind = (
                "existing_attribute"
                if column["property_id"]
                else "existing_source_attribute"
                if existing
                else "structural_role"
                if column["role"] or column["statement_role"]
                else "unresolved_attribute"
            )
            result.append(
                {
                    "table_id": table["id"],
                    "raw_label": column["label"],
                    "raw_unit": column["unit"],
                    "kind": kind,
                    "property_id": column["property_id"],
                    "source_accessor": existing,
                    "existing_contract": accessors.get(existing),
                    "representation": "Existing conditionType/value predicates"
                    if existing
                    else None,
                    "proposed_extension": {
                        "kind": "property",
                        "term": label,
                        "reason": "No approved semantic correspondence; determine source meaning before creating a property",
                        "approved": False,
                    }
                    if kind == "unresolved_attribute" and column["unit"]
                    else None,
                    "evidence_ids": table["evidence_ids"],
                    "activation": "NONE",
                }
            )
    return result


def table_quantities(service, package, mappings):
    """Typed original table attributes, including unresolved approved selectors.

    Registry accessors use existing conditionType/value semantics. No new class,
    measurement status or ontology definition is activated for a table column.
    """
    result = []
    for table in package["tables"]:
        from nasa_fire_ai.ingestion.generic import profile_table

        original_units = {
            profile.label: profile.raw_unit for profile in profile_table(table["rows"])
        }
        for index, row in enumerate(table["rows"]):
            from nasa_fire_ai.ingestion.generic import documentary_row

            if documentary_row(row):
                continue
            for column in table["columns"]:
                if column["role"] or column["statement_role"]:
                    continue
                raw = row.get(column["label"], "")
                from nasa_fire_ai.query.numeric_mentions import NUMBER

                if not raw or not re.fullmatch(rf"~?\s*{NUMBER}(?:\s*[-–]\s*{NUMBER})?", raw):
                    continue
                mapping = next(
                    m
                    for m in mappings
                    if m["table_id"] == table["id"] and m["raw_label"] == column["label"]
                )
                unit = original_units[column["label"]]
                if unit is None and re.search(r"\bpercent\b", column["label"], re.IGNORECASE):
                    unit = "%"  # Existing curation percent-header contract.
                value = service.parse_value(raw, unit, None)
                dimension = "UNRESOLVED"
                if unit:
                    from nasa_fire_ai.normalization.units import normalize

                    try:
                        _, canonical = normalize(1, unit)
                        expected = (
                            mapping.get("existing_contract", {}).get("unit")
                            if mapping.get("existing_contract")
                            else None
                        )
                        dimension = (
                            "COMPATIBLE" if expected in {None, canonical} else "CONTRADICTORY"
                        )
                    except ValueError:
                        dimension = "UNSUPPORTED_ORIGINAL_UNIT"
                result.append(
                    {
                        "id": table["id"]
                        + ":attribute:"
                        + str(index)
                        + ":"
                        + identity(column["label"])[:12],
                        "subject": table["id"] + ":run:" + str(index),
                        "table_id": table["id"],
                        "row": index + 1,
                        "column": column["label"],
                        "value": value,
                        "original_header": column["label"],
                        "original_expression": raw,
                        "source_role": mapping.get("existing_contract", {}).get("role")
                        if mapping.get("existing_contract")
                        else None,
                        "semantic_mapping": mapping,
                        "dimensional_validation": dimension,
                        "evidence_ids": [table["evidence_ids"][index]],
                        "epistemic": "SOURCE_ATTRIBUTE_NOT_ASSERTED_AS_OBSERVATION",
                        "scientific_review": "PENDING",
                    }
                )
    return result


def table_row_roles(package):
    """Evidence-bearing role exceptions; every other row remains unreviewed."""
    from nasa_fire_ai.ingestion.generic import documentary_row

    return [
        {
            "subject": table["id"] + ":run:" + str(index),
            "evidence_id": table["evidence_ids"][index],
            "role": "DOCUMENTARY_OR_PLANNED" if documentary_row(row) else "EXECUTION_UNRESOLVED",
            "original_support_cells": documentary_row(row),
            "scientific_approval": "NONE",
        }
        for table in package["tables"]
        for index, row in enumerate(table["rows"])
    ]


def extract_package(service, package, settings, budget, model_enabled=False, client=None):
    """Checkpoint after each successful segment. Failed calls remain retryable."""
    from nasa_fire_ai.ingestion.scientific_coverage import coverage

    started = time.monotonic()
    envelope = ProviderEnvelope()
    request_limit = request_context_limit(settings, envelope)
    # What a request may be billed for as output: Anthropic sends at least its
    # max_tokens floor whatever the stage capacity, so the brake reserves that.
    output_floor = 0
    if getattr(settings, "science_provider", "nvidia") == "anthropic":
        from nasa_fire_ai.llm.anthropic_provider import MIN_MAX_TOKENS

        output_floor = MIN_MAX_TOKENS
    chars = segment_size(package, budget, envelope)
    document = structure(package, service.root, chars)
    semantic = extraction_semantic(service, package)
    contracts = {
        "classes": {
            k: {f: v[f] for f in ("parent", "description", "definition", "label") if f in v}
            for k, v in semantic.class_metadata.items()
        },
        "information_classes": sorted(semantic.information_classes),
        "properties": [asdict(p) for p in semantic.properties.values()],
        "relations": sorted(semantic.relations),
        "aliases": [
            {"aliases": [key, *meta.get("aliases", [])], "relation": meta.get("relation")}
            for key, meta in getattr(semantic, "entity_mentions", {}).items()
            if meta.get("relation") in {"hasMaterial", "hasGravityCondition"}
        ],
        "ontology_datatype_properties": getattr(semantic, "ontology_datatype_properties", {}),
        "digest": service.contract_digest(),
    }
    if exclude_seed_terms():
        # Terms only the seed lexicon names are not sent (SCIENCE_EXCLUDE_SEED_TERMS).
        contracts["aliases"] = without_seed_aliases(contracts["aliases"], service.root, semantic)
    output = Output().model_dump()
    previous = package.get("scientific_extraction", {})
    restoring = bool(
        model_enabled and previous.get("contract") == CONTRACT and previous.get("raw_proposals")
    )
    restored_count = 0
    if restoring:
        checked_previous = validate_output(previous["raw_proposals"], package, document, semantic)
        originals = {
            proposal_identity(kind, item): item
            for kind, items in previous["raw_proposals"].items()
            for item in items
        }
        for r in checked_previous["records"]:
            if r["status"] != "REJECTED":
                # Scope adjudication may add a documented exact-heading binding
                # to the validated record. Replay the original model proposal;
                # derive the binding again instead of changing its identity.
                output[r["kind"]].append(originals[r["id"]])
                restored_count += 1
    recovered_cached_proposals = 0
    if model_enabled and budget.recovery_only:
        # An interrupted preparation may have durable successful stages but no
        # saved package version. Revalidate their original expanded proposals;
        # do not pay to repeat them merely because a prompt/budget later changed.
        combined = copy.deepcopy(output)
        source_ids = {e["evidence_id"] for e in package["evidence"]}
        for (payload,) in service.registry.db.execute(
            "SELECT payload_json FROM phase3_cache WHERE cache_kind IN ('scientific_document_segment','scientific_document_failure')"
        ):
            checkpoint = json.loads(payload)
            if checkpoint.get("contract") != CONTRACT:
                continue
            grounded = Output().model_dump()
            for kind, items in checkpoint.get("output", {}).items():
                if kind not in grounded:
                    continue
                grounded[kind] = [
                    item
                    for item in items
                    if item.get("support")
                    and all(s.get("evidence_id") in source_ids for s in item["support"])
                ]
            merge_output(combined, grounded)
        originals = {
            proposal_identity(kind, item): item
            for kind, items in combined.items()
            for item in items
        }
        restored = Output().model_dump()
        for r in validate_output(combined, package, document, semantic)["records"]:
            if r["status"] != "REJECTED":
                restored[r["kind"]].append(originals[r["id"]])
        recovered_cached_proposals = max(
            0, sum(map(len, restored.values())) - sum(map(len, output.values()))
        )
        output = restored
    recovery_only = budget.recovery_only and (restoring or recovered_cached_proposals > 0)
    for segment in document["segments"]:
        merge_output(output, literal_candidates(segment, semantic))
    calls, tokens, cached, outcomes = 0, 0, 0, []
    if model_enabled and client is None and settings.science_api_key:
        if settings.science_provider == "anthropic":
            from nasa_fire_ai.llm.anthropic_provider import AnthropicScientificClient

            client = AnthropicScientificClient(
                settings.anthropic_api_key,
                settings.scientific_model,
                effort=settings.anthropic_science_effort,
                refusal_fallback=settings.anthropic_science_refusal_fallback,
            )
        else:
            client = NvidiaStructuredClient(
                settings.nvidia_api_key, settings.nvidia_base_url, settings.scientific_model
            )
    for original in document["segments"]:
        if not re.search(r"references|acknowledg", original["section"], re.IGNORECASE):
            merge_output(output, deterministic(original, semantic))
    # The existing package title already identifies its documentary investigation.
    # Reuse it only when it is literally printed at the start of a source, never
    # infer an executed experiment from a title supplied by an uploader.
    title_pattern = (
        r"(?m)^[ \t]*(?:#{1,6}[ \t]+)?("
        + r"\s+".join(re.escape(t) for t in package["title"].split())
        + r")(?=\s|$)"
    )
    for original in package["evidence"]:
        if original.get("page") not in {None, 1}:
            continue
        found = re.search(title_pattern, original["text"][:1500], re.IGNORECASE)
        if found:
            merge_output(
                output,
                {
                    **Output().model_dump(),
                    "entities": [
                        {
                            "key": "original-document-investigation",
                            "label": found.group(1),
                            "class_id": "Investigation",
                            "study": "current",
                            "support": [
                                {
                                    "evidence_id": original["evidence_id"],
                                    "quote": found.group(1),
                                    "start": found.start(1),
                                }
                            ],
                        }
                    ],
                },
            )
    stable_entity_keys(output, package)
    consolidated = Output().model_dump()
    merge_output(consolidated, output)
    output = consolidated
    # Role vocabulary and role check (on by default, measured by variant R): the roles
    # defined from open ontologies and modal-verb conventions, and one closed-list
    # question per window for proposals held or rejected for their role. "0" turns
    # either off.
    role_vocabulary = os.getenv("SCIENCE_ROLE_VOCABULARY", "1") == "1"
    role_check = os.getenv("SCIENCE_ROLE_CHECK", "1") == "1"
    role_for = {}
    # Slide heading scope (off by default until measured): in a slide deck, each
    # anchor is sent under the heading validation reads for it (its own slide's).
    slide_heading_scope = os.getenv("SCIENCE_SLIDE_HEADING_SCOPE", "0") == "1"
    # Tables after the references (off by default until measured): a printed table
    # under the reference heading is windowed, its caption and rows only.
    table_after_references = os.getenv("SCIENCE_TABLE_AFTER_REFERENCES", "0") == "1"
    # Environment subjects (off by default until measured): an environment of earlier
    # work or the target of an assessment is an identity of its own, typed with the
    # approved general class unless its label names a subclass, and its values keep
    # their own role, study and bound.
    environment_subjects_v2 = os.getenv("SCIENCE_ENVIRONMENT_SUBJECTS_V2", "0") == "1"
    environment_subjects = (
        os.getenv("SCIENCE_ENVIRONMENT_SUBJECTS", "0") == "1" or environment_subjects_v2
    )
    # A material named inside a product's name is an identity of its own (off by
    # default until measured).
    product_materials = os.getenv("SCIENCE_PRODUCT_MATERIALS", "0") == "1"
    windows = model_windows(document, chars, tables_after_references=table_after_references)
    recovery_windows = []
    started_provider = False

    def available(reserve):
        return (
            not provider_blocked[0]
            and (budget.max_model_calls is None or calls < budget.max_model_calls)
            and (budget.max_total_tokens is None or tokens + reserve <= budget.max_total_tokens)
            and (
                budget.timeout_seconds is None
                or time.monotonic() - started < budget.timeout_seconds
            )
        )

    provider_blocked = [False]
    # Windows of one stage are independent requests: up to this many are sent
    # ahead of their turn, and each answer is still merged in window order.
    concurrency = max(1, int(os.getenv("SCIENCE_WINDOW_CONCURRENCY", "3")))
    prefetched, prefetch_counts = {}, {"concurrency": concurrency, "sent": 0, "used": 0}
    # Requests sent ahead, with the reservation counted against the brake when sent.
    prefetch_plans, ahead_reserved = {}, {}
    pool = ThreadPoolExecutor(concurrency) if concurrency > 1 else None

    def rate_limited(ahead):
        # A rate limit stops sending ahead: the windows not yet sent wait for
        # their turn, where the ordinary Retry-After backoff applies.
        error = None if ahead.cancelled() else ahead.exception()
        if isinstance(error, ScientificTransportError) and error.kind == "rate_limit":
            prefetch_counts["rate_limited"] = True

    def prefetch(stage_windows, stage):
        nonlocal calls, tokens
        if pool is None or not (model_enabled and client) or recovery_only:
            return
        for window in stage_windows:
            if prefetch_counts.get("rate_limited"):
                return
            planned = process_stage(window, stage, probe=True)
            if planned is None or identity(planned["call"]) in prefetched:
                continue
            # A request goes ahead only if its own turn would send it: at the
            # spending brake or the call limit, nothing more is sent ahead.
            if not available(planned["reserve"]):
                return
            calls += 1
            tokens += planned["reserve"]
            ahead_reserved[identity(planned["call"])] = planned["reserve"]
            remaining = (
                float("inf")
                if budget.timeout_seconds is None
                else budget.timeout_seconds - (time.monotonic() - started)
            )
            prefetched[identity(planned["call"])] = pool.submit(
                complete_scientific,
                client,
                **planned["call"],
                timeout=min(planned["timeout"], remaining),
                stream=budget.stream and getattr(client, "supports_streaming", False) is True,
            )
            prefetched[identity(planned["call"])].add_done_callback(rate_limited)
            prefetch_plans[identity(planned["call"])] = (stage, planned["call"])
            prefetch_counts["sent"] += 1

    def cancel_ahead(ref):
        """Cancel a request sent ahead if it has not left; its reservation is released."""
        nonlocal calls, tokens
        if prefetched[ref].cancel():
            tokens -= ahead_reserved.pop(ref, 0)
            calls -= 1
            prefetched.pop(ref)
            prefetch_counts["cancelled"] = prefetch_counts.get("cancelled", 0) + 1

    def count_usage(ref):
        """Count a finished request sent ahead at its billed usage instead of its reservation.

        A failure that proves the request was never billed releases its reservation.
        """
        nonlocal tokens
        ahead = prefetched[ref]
        if not ahead.done() or ahead.cancelled():
            return
        error = ahead.exception()
        if error is not None:
            if isinstance(error, ScientificTransportError) and never_billed(error):
                tokens -= ahead_reserved[ref]
                ahead_reserved[ref] = 0
            return
        usage = ahead.result().usage
        if usage:
            tokens += usage["total_tokens"] - ahead_reserved[ref]
            ahead_reserved[ref] = usage["total_tokens"]

    def make_room(reserve):
        """Before the brake refuses the foreground, release what requests sent ahead hold.

        The earlier window has priority: requests not yet sent are cancelled (they are
        sent normally at their turn), finished ones are counted at their billed usage,
        and those in flight are waited for and counted the same way.
        """
        if (
            budget.max_total_tokens is None
            or tokens + reserve <= budget.max_total_tokens
            or not prefetched
        ):
            return
        for ref in list(prefetched):
            cancel_ahead(ref)
        for ref in prefetched:
            count_usage(ref)
        if tokens + reserve <= budget.max_total_tokens:
            return
        wait(list(prefetched.values()))
        for ref in prefetched:
            count_usage(ref)

    def settle_prefetch():
        """Unused requests: never sent are released; sent ones are recorded and stay counted.

        A sent request keeps its reservation, adjusted to its billed usage when known,
        unless its error proves it never left this machine.
        """
        nonlocal calls, tokens
        for ref, ahead in list(prefetched.items()):
            stage, call = prefetch_plans.get(ref, (None, {}))
            reserved = ahead_reserved.pop(ref, 0)
            settled = record_discarded_prefetch(service.registry, stage, call, ahead)
            if settled is None or settled["never_sent"]:
                tokens -= reserved
                calls -= 1
            elif settled["usage_tokens"] is not None:
                tokens += settled["usage_tokens"] - reserved
        prefetch_counts["discarded"] = prefetch_counts.get("discarded", 0) + len(prefetched)
        prefetched.clear()

    def process_stage(window, stage, focus=None, subject=None, probe=False):
        nonlocal calls, tokens, cached, started_provider
        prompt = stage_prompt(stage, focus)
        segment = window["members"][0]
        text = "\n".join(s["text"] for s in window["members"])
        if any(m.get("table_region") for m in window["members"]):
            # A window holding a table from back matter takes no reference-list context.
            segment = {**segment, "table_region": True}
        context = context_for(
            {**segment, "text": text}, document, max_chars=max(3500, envelope.context_tokens // 8)
        )
        if stage == "identity":
            # Identity discovery uses the local source, not a long list of prior
            # model proposals to copy. Later tasks retrieve methods/applicability.
            context = {"anchors": [], "available": context["available"], "selected_characters": 0}
            known = []
        else:
            known = grounded_entities(output, package, document, semantic, window, context)
        anchors = source_anchors(window, context, known, package)
        # Short wire references eliminate model copying of hashes. Original stable
        # anchors/keys are retained server-side and expanded only by exact lookup.
        evidence_order = {e["evidence_id"]: i for i, e in enumerate(package["evidence"])}
        ordered = sorted(
            anchors.values(), key=lambda a: (evidence_order[a["evidence_id"]], a["start"], a["end"])
        )
        wire_anchors = {f"A{i + 1}": a for i, a in enumerate(ordered)}
        anchor_refs = {a["id"]: ref for ref, a in wire_anchors.items()}
        wire_entities = {f"K{i + 1}": e["key"] for i, e in enumerate(known)}
        known_groups = {
            normalized(e["label"]): ref
            for ref, e in zip(wire_entities, known, strict=True)
            if e["class_id"] == "ExperimentFamily" and e.get("study") == "current"
        }

        def anchor_scope(anchor):
            # The printed heading an anchor sits under, and the known group that
            # heading names: the narrowest explicit subject for what is printed there.
            heading = printed_heading_before(anchor, document)
            if slide_heading_scope and slide_deck(document):
                # The heading validation reads: its own slide's, never an earlier one.
                title = slide_heading(anchor, document)
                heading = {"title": title} if title else None
            if not heading:
                return {}
            scope = {"heading": heading["title"]}
            group = known_groups.get(normalized(heading_title(heading["title"])))
            if group:
                scope["group"] = group
            return scope

        request = {
            "stage": stage,
            "focus": focus,
            "document_identity": {"title": package["title"]},
            "contracts": contracts,
            "segments": [
                {
                    **{k: member[k] for k in ("page", "start", "end")},
                    "section": section_for_span(member, document),
                }
                for member in window["members"]
            ],
            "original_logical_sections": [
                h
                for h in document["sections"]
                if any(h["evidence_id"] == m["evidence_id"] for m in window["members"])
            ],
            "source_anchors": [
                {
                    "id": ref,
                    **{k: a[k] for k in ("page", "quote")},
                    "statement_eligible": a.get("statement_eligible", True),
                    "in_task": any(
                        a["evidence_id"] == m["evidence_id"]
                        and a["start"] >= m["start"]
                        and a["start"] < m["end"]
                        for m in window["members"]
                    ),
                    **anchor_scope(a),
                }
                for ref, a in wire_anchors.items()
            ],
            "shared_context": {
                "available": context["available"],
                "selected_characters": context["selected_characters"],
            },
            "known_entities": [
                {
                    **{k: e[k] for k in ("label", "class_id", "study")},
                    "key": ref,
                    "support": [
                        anchor_refs[
                            "anchor-"
                            + identity([span["evidence_id"], span["start"], span["end"]])[:20]
                        ]
                        for span in locate(
                            e["support"], {r["evidence_id"]: r for r in package["evidence"]}
                        )
                    ],
                }
                for ref, e in zip(wire_entities, known, strict=True)
            ],
            "schema": stage_schema(stage, compact=True),
        }
        if os.getenv("SCIENCE_ONTOLOGY_CONTEXT", "1") == "1":
            # Ontology snippets for the classes in play, built now from the ontology
            # and registry. On by default (adopted on the generality audit of
            # 2026-10-27); "0" turns it off.
            from nasa_fire_ai.ingestion.ontology_context import ontology_context

            in_play = {e["class_id"] for e in known}
            if stage == "identity":
                # The classes this stage chooses among.
                in_play |= set(identity_classes(semantic))
            if stage == "propositions":
                in_play |= {c for c in STATEMENT_CLASSES.values() if c in semantic.class_metadata}
            # Staged terms come only from a reviewed snapshot, never from this
            # package's own earlier output: an unchanged package must send the same
            # request (and hit the same cache) when it is prepared again.
            staged_snapshot = None
            if os.getenv("SCIENCE_STAGED_CONTEXT", "0") == "1":
                # Track B: reviewed terms of a frozen snapshot, minus those staged
                # from this very PDF (compared by its sha256).
                from nasa_fire_ai.ingestion.ontology_context import (
                    load_staged_snapshot,
                    staged_terms_for,
                )

                staged_snapshot = load_staged_snapshot(os.getenv("SCIENCE_STAGED_SNAPSHOT"))
            request["ontology_context"] = ontology_context(
                in_play,
                semantic,
                RELATION_ENDPOINTS,
                staged=staged_terms_for(
                    {e.get("checksum") for e in package["evidence"]}, staged_snapshot
                )
                if staged_snapshot
                else (),
            )
            if staged_snapshot:
                request["ontology_context"]["staged_snapshot_version"] = staged_snapshot.get(
                    "version"
                )
            request["ontology_context_use"] = (
                "ontology_context describes each class in play: its ancestors, children, "
                "aliases and the relations it can take part in, inherited from its ancestors. "
                "Choose the most specific approved class or relation the source supports. A "
                "term under staged is awaiting review, never approved."
            )
        if os.getenv("SCIENCE_CANDIDATE_CONTRACT", "1") == "1" and stage in {
            "identity",
            "propositions",
        }:
            # SCION's candidate contract: the terms this document prints that the
            # approved vocabulary does not cover, offered with their coverage so a
            # gap is resolved explicitly (reuse, characteristic, specialization, new
            # term, or nothing) instead of silently forced into a listed term. On
            # by default (adopted on the generality audit of 2026-10-27); "0" turns it off.
            from nasa_fire_ai.ingestion.semantic_candidates import (
                candidate_hygiene_request_enabled,
                candidate_inventory,
                clean_candidates,
                window_candidates,
            )

            inventory = document_memo(
                document,
                "semantic_candidates",
                lambda: candidate_inventory(package, document, semantic),
            )
            if candidate_hygiene_request_enabled():
                inventory = document_memo(
                    document,
                    "semantic_candidates_clean",
                    lambda: clean_candidates(inventory, document),
                )
            chosen, eligible = window_candidates(inventory, window["members"])
            term_candidate_counts = {"eligible": eligible, "sent": len(chosen)}
            term_candidates = [
                {
                    "printed": c["label"],
                    "coverage": c["coverage"],
                    **(
                        {"qualifies": c["approved_term"], "qualifies_kind": c["approved_kind"]}
                        if c["coverage"] == "QUALIFIES"
                        else {}
                    ),
                }
                for c in chosen
            ]
        else:
            term_candidates, term_candidate_counts = [], None
        if os.getenv("SCIENCE_CANDIDATE_SNIPPETS", "0") == "1" and "ontology_context" in request:
            # Track B: a snippet for the term each candidate qualifies, and an identity
            # block of the base classes plus the classes the candidates touch.
            from nasa_fire_ai.ingestion.ontology_context import candidate_snippets, snippet

            snippets = candidate_snippets(term_candidates, semantic)
            touched = {s["class"] for s in snippets if "class" in s}
            small = {e["class_id"] for e in known} | touched
            small |= {c for c in IDENTITY_BASES if c in semantic.class_metadata}
            if stage == "propositions":
                small |= {c for c in STATEMENT_CLASSES.values() if c in semantic.class_metadata}
            request["ontology_context"]["approved"] = [
                snippet(c, semantic, RELATION_ENDPOINTS) for c in sorted(small)
            ]
            if snippets:
                request["candidate_snippets"] = snippets
        if term_candidates:
            # Its own key and its own instruction, only when the window has candidates.
            request["source_term_candidates"] = term_candidates
            request["source_term_contract"] = (
                "source_term_candidates lists terms this document prints that the approved "
                "vocabulary does not name (UNCOVERED) or names only in part (QUALIFIES, "
                "with the approved term it qualifies). When an in_task anchor uses one, "
                "resolve it: reuse an approved term when it is equivalent; read a qualifier "
                "as a characteristic of the approved term, not a new class; propose a new "
                "class, relation or concept only when the source prints its meaning, using "
                "the candidate's printed words (proposed_class.term is the CamelCase form of "
                "the printed words). A listed candidate is never a reason to "
                "propose anything; leave unused candidates alone."
            )
        if environment_subjects and stage == "identity":
            request["environment_identity_contract"] = (
                "Identify each environment the in_task anchors print with its own values as "
                "an identity of its own: one reported for an earlier program, mission or cited "
                "work (labelled with that name and its printed values, study cited), and one "
                "a requirement, assessment or test must reach (labelled with its printed "
                "values, study current). "
                + (
                    "Use the approved class ExperimentalCondition, and keep the printed "
                    "values in its label."
                    if environment_subjects_v2
                    else "Use the approved general class ExperimentalCondition "
                    "unless the printed label itself names a subclass (an atmosphere, a "
                    "pressure, a gravity level)."
                )
            )
        if environment_subjects and stage == "propositions":
            request["environment_value_roles"] = (
                ENVIRONMENT_VALUE_ROLES_V2 if environment_subjects_v2 else ENVIRONMENT_VALUE_ROLES
            )
        if background_facets_enabled() and stage == "propositions":
            request["background_facet_contract"] = (
                "A statement may carry scope 'background' when its clause reports the state "
                "of the art or prior knowledge of the field rather than a result of this "
                "study (role author_reported_conclusion or tentative_interpretation), and "
                "execution 'ongoing' when its clause is progressive and reports an activity "
                "as under way, neither completed nor planned (role experimental_configuration "
                "or planned_activity); an activity under way is not a conclusion. Never use "
                "them for this study's observations."
                if ongoing_activity_roles_enabled()
                else "A statement may carry scope 'background' when its clause reports the state "
                "of the art or prior knowledge of the field rather than a result of this "
                "study, and execution 'ongoing' when its clause reports an activity as under "
                "way, neither completed nor planned. Use them only with the role "
                "author_reported_conclusion (or tentative_interpretation for background), "
                "and never for this study's observations, settings or plans."
            )
        if role_definitions_v2_enabled() and stage == "propositions":
            request["evidence_basis_contract"] = EVIDENCE_BASIS_CONTRACT
        if value_origin_mark_enabled() and stage == "propositions":
            request["value_origin_contract"] = VALUE_ORIGIN_CONTRACT
        if structured_provenance_enabled() and stage == "propositions":
            request["data_provenance_role"] = (
                "data_provenance: a statement that names where this study's compared or "
                "reported data come from, as its own record with the Publication class "
                "(for example 'The burn rates of the reference foams were taken from two "
                "earlier vendor reports and a public materials database.'); a figure or "
                "table pointer stays documentary_context."
                + (
                    " Also identify each printed source as a Publication entity (or "
                    "propose a class whose parent is Publication) and link the study to "
                    "it with PROPOSE_NEW_RELATION (parent NONE) when no listed relation "
                    "says where the data came from; for example, for '"
                    + PROVENANCE_EXAMPLE
                    + "' the source is the Marlow panel survey."
                    if structured_provenance_enabled()
                    else ""
                )
            )
        if product_materials and stage == "identity":
            request["product_material_contract"] = (
                "When a product, fabric, part or specimen is named by its material ('a "
                "fabric of fiber X', 'an X-filled polymer', 'a seal with an X filler'), "
                "identify the material X as a Material of its own besides the product."
            )
        if role_vocabulary and stage == "propositions":
            request["role_vocabulary"] = request_role_vocabulary()
        if window["id"] in role_for and stage == "propositions":
            request["role_check"] = role_for[window["id"]]
            request["role_options"] = ROLE_OPTIONS + (
                [PROVENANCE_ROLE] if structured_provenance_enabled() else []
            )
            request["role_modalities"] = ROLE_MODALITIES
            request["role_studies"] = ROLE_STUDIES
            request["role_check_contract"] = (
                "role_check lists proposals from this window that were held or rejected "
                "for their role, each with what was proposed and why it was held. For each, "
                "choose the role in role_options, the modality in role_modalities and the "
                "study in role_studies that its own printed clause supports, read with the "
                "modal-verb conventions of role_vocabulary when present, and return the item "
                "again with them and its subject; return nothing for an item no role fits. "
                "Never change a subject, never invent a clause."
            )
        source_checksums = {e["evidence_id"]: e["checksum"] for e in package["evidence"]}
        local_pages = {(m["page"], source_checksums[m["evidence_id"]]) for m in window["members"]}
        original_tables = [
            {
                "physical_pdf_page": t["physical_pdf_page"],
                "original_cells": t["cells"],
                "original_headers": t["header"],
                "header_external": t["header_external"],
                "semantic_status": "UNAPPROVED_LAYOUT_ONLY_NOT_EXECUTION_EVIDENCE",
            }
            for t in document["detected_tables"]
            if "cells" in t and (t["physical_pdf_page"], t["input_sha256"]) in local_pages
        ]
        if original_tables:
            request["original_tables"] = original_tables
        images, image_receipts = [], []
        if stage == "propositions" and original_tables and settings.science_vision_model:
            from nasa_fire_ai.ingestion.scientific_media import table_page_images

            images, image_receipts = table_page_images(
                package,
                service.root,
                [
                    t
                    for t in document["detected_tables"]
                    if "cells" in t and (t["physical_pdf_page"], t["input_sha256"]) in local_pages
                ],
            )
            request["original_page_images"] = image_receipts
            request["visual_source_policy"] = (
                "Images are original page context, never scientific authority. Use only original "
                "text anchors for proposed facts. Preserve table row/column scope and fit/derived "
                "roles. If image-only attribution cannot be independently established, omit the "
                "scientific assignment and retain the original table for scientist review."
            )
        task_model = settings.science_vision_model if images else settings.scientific_model
        fallback_models = () if images else settings.science_fallback_models
        schema = request["schema"]
        wire_quantities = {}
        if focus == "quantities":
            interim = coverage(
                package,
                document,
                validate_output(output, package, document, semantic),
                outcomes,
                [],
            )
            request["unstructured_quantity_candidates"] = [
                {
                    "page": a["page"],
                    "original_expression_with_unit": q["original_expression_with_unit"],
                    "expression": q["expression"],
                    "unit": q["unit"],
                    "source_anchors": [
                        ref
                        for ref, anchor in wire_anchors.items()
                        if anchor["evidence_id"] == a["evidence_id"]
                        and anchor["start"] <= q["start"]
                        and anchor["end"] >= q["end"]
                    ],
                }
                for a in interim["source_units"]
                if any(
                    a["evidence_id"] == m["evidence_id"]
                    and a["start"] < m["end"]
                    and a["end"] > m["start"]
                    for m in window["members"]
                )
                for q in a["quantity_inventory"]
                if q["state"] == "NOT_STRUCTURED"
            ]
            from nasa_fire_ai.ingestion.table_continuity import printed_in_table

            # Table cells are bound to their rows deterministically; recovery asks
            # only for the prose values a table does not already hold.
            candidates = [
                q
                for q in request["unstructured_quantity_candidates"]
                if q["source_anchors"]
                and not printed_in_table(document, q["page"], q["original_expression_with_unit"])
            ]
            for q in candidates:
                q["source_anchors"] = [
                    min(q["source_anchors"], key=lambda ref: len(wire_anchors[ref]["quote"]))
                ]
            request["unstructured_quantity_candidates"] = []
            for i, q in enumerate(candidates):
                ref = f"Q{i + 1}"
                wire_quantities[ref] = {
                    "expression": q["expression"],
                    "unit": q["unit"],
                    "support": q["source_anchors"],
                }
                request["unstructured_quantity_candidates"].append(
                    {
                        "id": ref,
                        **{
                            k: q[k]
                            for k in ("page", "original_expression_with_unit", "source_anchors")
                        },
                    }
                )
            definition = schema["$defs"]["Quantity"]
            definition["properties"] = {
                "quantity_ref": {
                    "type": "string",
                    **({"enum": list(wire_quantities)} if wire_quantities else {}),
                },
                **{
                    k: definition["properties"][k]
                    for k in (
                        "subject",
                        "label",
                        "epistemic",
                        "modality",
                        "printed_name",
                        *(("study",) if value_origin_mark_enabled() else ()),
                    )
                },
            }
            definition["required"] = [
                k for k in definition["properties"] if k not in {"printed_name", "modality"}
            ]
        if focus == "statements":
            from nasa_fire_ai.ingestion.scientific_coverage import statement_candidates

            missing = statement_candidates(
                package, document, validate_output(output, package, document, semantic)
            )
            request["unstructured_statement_anchors"] = [
                ref
                for ref, anchor in wire_anchors.items()
                if any(
                    c["state"] == "NOT_STRUCTURED"
                    and c["evidence_id"] == anchor["evidence_id"]
                    and c["start"] == anchor["start"]
                    and c["end"] == anchor["end"]
                    for c in missing
                )
            ]
        if focus:
            focused_schema(schema, focus)
            request["task"] = (
                "Extract all source-backed " + focus + " in the task source anchors. "
                "Return ONLY the root key " + focus + ". The wider stage example "
                "does not require other keys for this focused task."
            )
        if focus == "quantities":
            request["task"] = (
                "Recover the listed missing ORIGINAL quantity candidates. Return only quantities. "
                "Each item has quantity_ref (Q identifier), subject (known entity key), label "
                "(exact source quantity name), epistemic (reported_quantity, derived_quantity "
                "or experimental_configuration) and printed_name (the words of the value's own "
                "clause that name it when the label is not printed there, else null). The service preserves the original value/unit/support "
                "by exact Q lookup; do not write or modify them. Use only justified scientific scope."
                " A described specimen dimension is experimental_configuration unless its measurement "
                "is explicitly reported. A value from a fit or derivative is derived_quantity. "
                " Select a subject from that candidate's source_applicable_subjects. "
                "If its list is empty, preserve the gap by omitting the candidate; never substitute "
                "another document-level entity."
            )
            if value_origin_mark_enabled():
                request["task"] += " " + VALUE_ORIGIN_CONTRACT
        if stage == "identity" and focus == "entities":
            request["task"] = (
                "Resolve original experimental identities, including quantified samples and source result headings, using local evidence. "
                "Retain literal sample/specimen names; dimensions alone do not create a run. "
                "Material means the substance itself, without investigation/gravity/result qualifiers. "
                "ExperimentFamily is a source-defined experimental group or comparison context. "
                "A result heading combining test context and material names is a scoped group, "
                "not a newly named material. Keep its full source label and distinguishing qualifiers. "
                "Do not invent individual executed runs. Return only entities."
            )
        if stage == "identity":
            schema["$defs"]["Entity"]["properties"]["class_id"]["enum"] = identity_classes(
                semantic
            ) + [PROPOSE_NEW_CLASS]
            request["vocabulary_extension"] = (
                "When no listed class fits a source-supported entity, set class_id to "
                f"{PROPOSE_NEW_CLASS} and give proposed_class: a new CamelCase term and the "
                "listed class it refines as parent. It is staged for ontology review, "
                "never approved. Prefer a listed class whenever one is equivalent."
            )
        for definition in schema["$defs"].values():
            # Strict shape enforcement is useful; a huge per-token anchor enum can
            # make hosted constrained decoding slow. The independent resolver
            # enforces anchor membership without this provider grammar expansion.
            if "support" in definition["properties"]:
                definition["properties"]["support"]["items"] = {"type": "string"}
        if wire_entities:
            for definition in schema["$defs"].values():
                for field in ("subject", "object"):
                    if field in definition["properties"]:
                        definition["properties"][field]["enum"] = list(wire_entities)
                if "subjects" in definition["properties"]:
                    definition["properties"]["subjects"]["items"]["enum"] = list(wire_entities)
        if "Quantity" in schema["$defs"]:
            checked_entities = validate_output(output, package, document, semantic)[
                "entities_by_key"
            ]
            eligible_keys = [
                ref
                for ref, key in wire_entities.items()
                if key in checked_entities
                and (
                    quantity_scope_eligible(checked_entities[key], semantic)
                    or tested_material_entity(checked_entities[key], document)
                )
            ]
            if eligible_keys:
                schema["$defs"]["Quantity"]["properties"]["subject"]["enum"] = eligible_keys
            if focus == "quantities":
                request["known_entities"] = [
                    e for e in request["known_entities"] if e["key"] in eligible_keys
                ]
                for candidate in request["unstructured_quantity_candidates"]:
                    q = wire_quantities[candidate["id"]]
                    spans = locate(
                        [wire_anchors[ref] for ref in q["support"]],
                        {e["evidence_id"]: e for e in package["evidence"]},
                    )
                    scoped = original_heading_scope(spans, checked_entities, document)
                    from nasa_fire_ai.ingestion.scientific_scope import (
                        figure_group_support,
                        test_article_alias_review,
                    )

                    candidate["source_applicable_subjects"] = [
                        ref
                        for ref in eligible_keys
                        if (
                            applicable(wire_entities[ref], spans, checked_entities, document)
                            and (
                                local_binding(
                                    wire_entities[ref], q["expression"], spans, checked_entities
                                )
                                or (
                                    scoped
                                    and checked_entities[scoped[0]]["id"]
                                    == checked_entities[wire_entities[ref]]["id"]
                                )
                            )
                        )
                        or figure_group_support(
                            wire_entities[ref], spans, checked_entities, document
                        )
                        or test_article_alias_review(
                            wire_entities[ref], spans, checked_entities, document
                        )
                    ]
                    candidate["source_scope_review_only_subjects"] = [
                        ref
                        for ref in candidate["source_applicable_subjects"]
                        if test_article_alias_review(
                            wire_entities[ref], spans, checked_entities, document
                        )
                    ]
                request["contracts"] = {
                    k: contracts[k] for k in ("properties", "aliases", "digest")
                }
        if "Relation" in schema["$defs"]:
            schema["$defs"]["Relation"]["properties"]["relation"]["enum"] = sorted(
                semantic.relations
            ) + [PROPOSE_NEW_RELATION]
            request["vocabulary_extension"] = (
                "When no listed relation states what the source prints between two entities, "
                f"set relation to {PROPOSE_NEW_RELATION} and give proposed_relation: a new "
                "camelCase term and, as parent, the listed relation it qualifies or NONE. It is "
                "staged for ontology review, never approved. Prefer a listed relation "
                "whenever one is equivalent."
            )
            if not relation_registry_prompt_enabled():
                request["relation_signatures"] = relation_signature_listing(semantic)
            if subject is not None:
                ref = next(ref for ref, key in wire_entities.items() if key == subject)
                schema["$defs"]["Relation"]["properties"]["subject"]["enum"] = [ref]
                request["task"] = (
                    "Resolve the relations of known entity " + ref + ", a group, from the "
                    "anchors under its printed heading (group=" + ref + "): the conditions, "
                    "materials, samples and interventions printed there. Return only relations "
                    "whose subject is " + ref + "."
                )
        structured_format = {
            "type": "json_schema",
            "json_schema": {"name": "scientific_" + stage, "schema": schema, "strict": True},
        }
        format_mode = structured_format
        reasoning = reasoning_size(text, budget, envelope)
        if focus == "quantities" and budget.reasoning_tokens is None:
            reasoning = max(reasoning, min(4096, envelope.reasoning_tokens))
        capacity = min(
            envelope.output_tokens,
            output_size(stage, text, len(known), budget, envelope) + reasoning,
        )
        if budget.max_output_tokens is not None:
            capacity = min(capacity, budget.max_output_tokens)
        reasoning = min(reasoning, capacity // 2)
        key = identity(
            [
                CONTRACT,
                prompt,
                request,
                task_model,
                fallback_models,
                budget.max_output_tokens,
                envelope.output_tokens,
                reasoning,
            ]
        )
        replay = service.registry.get_phase3_cache(key, "scientific_document_segment")
        partial = service.registry.get_phase3_cache(key, "scientific_document_failure")
        if probe:
            # What the window's first attempt would send, read without changing
            # anything; a cached or previously failed window is not prefetched.
            if not (model_enabled and client) or replay or partial:
                return None
            payload = json.dumps(request, ensure_ascii=False, separators=(",", ":"))
            sent_bytes = len((prompt + payload + json.dumps(format_mode)).encode())
            if (sent_bytes + len(images) * 4096) // 2 + capacity + 512 > request_limit:
                return None
            return {
                "reserve": sent_bytes + max(capacity, output_floor) + len(images) * 4096,
                "call": {
                    "model": task_model,
                    "system": prompt,
                    "payload": payload,
                    "max_tokens": capacity,
                    "response_format": format_mode,
                    "reasoning_budget": reasoning,
                    "images": images,
                },
                "timeout": timeout_for(capacity, budget, envelope),
            }
        if model_enabled and partial and partial.get("output"):
            merge_output(output, partial["output"])
        outcome = {
            "segment_id": window["id"],
            "stage": stage,
            "focus": focus,
            "cache_key": key,
            "members": [
                {k: member[k] for k in ("id", "evidence_id", "start", "end")}
                for member in window["members"]
            ],
            "evidence_id": segment["evidence_id"],
            "start": segment["start"],
            "end": segment["start"]
            + sum(member["end"] - member["start"] for member in window["members"]),
            "deterministic": "COMPLETE",
            "model": "DISABLED",
            "attempts": 0,
            "source_anchors": len(anchors),
            "known_entities_selected": len(known),
            "reasoning_tokens": reasoning,
            "source_anchor_characters": sum(len(a["quote"]) for a in anchors.values()),
            "proposed_items": sum(len(v) for v in (partial or {}).get("output", {}).values()),
        }
        if term_candidate_counts is not None:
            # How many printed terms the window had before the request's cut.
            outcome["source_term_candidates"] = term_candidate_counts
        last_failure = (partial or {}).get("attempt_receipts", [])
        not_before = (
            last_failure[-1].get("outcome", {}).get("retry_not_before") if last_failure else None
        )
        exhausted = last_failure and last_failure[-1].get("outcome", {}).get("model") in {
            "PARTIAL_SOURCE",
            "PARTIAL_SCHEMA",
            "EMPTY_WITH_SOURCE_CANDIDATES",
        }
        if (
            model_enabled
            and not_before
            and datetime.fromisoformat(not_before).timestamp() > time.time()
        ):
            outcome.update(model="DEFERRED_PROVIDER_RETRY_AFTER", retry_not_before=not_before)
            provider_blocked[0] = True
        elif model_enabled and exhausted and not replay:
            previous = last_failure[-1]["outcome"]
            outcome.update(
                model=previous["model"], replayed_failure=True, recovery=previous.get("recovery")
            )
            cached += 1
        elif model_enabled and replay:
            merge_output(output, replay["output"])
            outcome.update(
                model="CACHE_REPLAY", proposed_items=sum(len(v) for v in replay["output"].values())
            )
            cached += 1
        elif model_enabled and client:
            outcome["model"] = "DEFERRED_BUDGET"
            history = copy.deepcopy((partial or {}).get("attempt_receipts", []))
            retained = copy.deepcopy((partial or {}).get("output", Output().model_dump()))
            feedback, transient_attempts, repairs = None, 0, 0
            model_options = list(dict.fromkeys((task_model, *fallback_models)))
            model_index = 0
            while True:
                body = {**request, **({"validation_feedback": feedback} if feedback else {})}
                payload = json.dumps(body, ensure_ascii=False, separators=(",", ":"))
                # UTF-8 bytes are a conservative tokenizer upper bound, not billed usage.
                sent_bytes = len((prompt + payload + json.dumps(format_mode)).encode())
                reserve = sent_bytes + max(capacity, output_floor) + len(images) * 4096
                outcome.update(
                    request_bytes=len(payload.encode()),
                    reserved_tokens_per_attempt=reserve,
                    output_tokens=capacity,
                )
                # Scheduling estimate is distinct from conservative unknown-billing
                # reservation. English scientific text/IDs are not one token per byte.
                context_estimate = (sent_bytes + len(images) * 4096) // 2 + capacity + 512
                outcome["context_token_estimate"] = context_estimate
                if context_estimate > request_limit:
                    outcome["model"] = "NEEDS_CONTEXT_SPLIT"
                    break
                planned_call = {
                    "model": model_options[model_index],
                    "system": prompt,
                    "payload": payload,
                    "max_tokens": capacity,
                    "response_format": format_mode,
                    "reasoning_budget": reasoning,
                    "images": images,
                }
                # The identical request already sent ahead was counted when it left.
                sent_ahead = identity(planned_call) in ahead_reserved
                if not sent_ahead and not available(reserve):
                    make_room(reserve)
                if not sent_ahead and not available(reserve):
                    if provider_blocked[0]:
                        outcome["model"] = "PROVIDER_BLOCKED"
                    break
                if not sent_ahead:
                    calls += 1
                    tokens += reserve
                outcome["attempts"] += 1
                started_provider = True
                raw, usage, parsed, finish = None, None, Output().model_dump(), None
                for field in (
                    "finish_reason",
                    "usage",
                    "schema_errors",
                    "source_errors",
                    "error_type",
                    "transport",
                ):
                    outcome.pop(field, None)
                attempt = {
                    "contract": CONTRACT,
                    "stage": stage,
                    "request": body,
                    "max_output_tokens": capacity,
                    "requested_model": model_options[model_index],
                    "response_format": format_mode,
                }
                attempt_key = identity([key, calls, time.time_ns()])
                service.registry.set_phase3_cache(
                    attempt_key,
                    "scientific_document_attempt",
                    {**attempt, "state": "REQUESTED", "response_format": format_mode},
                )
                last_progress = [0.0]

                def checkpoint_stream(
                    prefix,
                    metadata,
                    attempt=attempt,
                    attempt_key=attempt_key,
                    last_progress=last_progress,
                ):
                    now = time.monotonic()
                    if (
                        now - last_progress[0] >= 1
                        or metadata.get("finish_reason")
                        or metadata.get("error_type")
                    ):
                        service.registry.set_phase3_cache(
                            attempt_key,
                            "scientific_document_attempt",
                            {
                                **attempt,
                                "state": "RECEIVING",
                                "raw_response": prefix,
                                "transport": metadata,
                            },
                        )
                        last_progress[0] = now

                transient, truncated = False, False
                retry_after = None
                # What this request is counted at now: its reservation, or, for one
                # sent ahead, its billed usage or 0 if that was already settled.
                counted = reserve
                try:
                    remaining = (
                        float("inf")
                        if budget.timeout_seconds is None
                        else budget.timeout_seconds - (time.monotonic() - started)
                    )
                    call = {
                        "model": model_options[model_index],
                        "system": prompt,
                        "payload": payload,
                        "max_tokens": capacity,
                        "response_format": format_mode,
                        "reasoning_budget": reasoning,
                        "images": images,
                    }
                    ahead = prefetched.pop(identity(call), None)
                    counted = ahead_reserved.pop(identity(call), reserve)
                    if prefetch_counts.get("rate_limited"):
                        for ref in list(prefetched):
                            cancel_ahead(ref)
                    if ahead is not None:
                        # The identical request was sent ahead of its turn; its
                        # answer is used exactly as a live one would be.
                        outcome["prefetch"] = "USED"
                        prefetch_counts["used"] += 1
                        try:
                            response = ahead.result()
                        except ScientificTransportError as error:
                            checkpoint_stream(
                                error.content, {**error.metadata, "error_type": error.kind}
                            )
                            raise
                        checkpoint_stream(
                            response.content,
                            {**response.metadata, "finish_reason": response.finish_reason},
                        )
                    else:
                        response = complete_scientific(
                            client,
                            **call,
                            timeout=min(timeout_for(capacity, budget, envelope), remaining),
                            stream=budget.stream
                            and getattr(client, "supports_streaming", False) is True,
                            on_progress=checkpoint_stream,
                        )
                    raw, finish, usage = response.content, response.finish_reason, response.usage
                    outcome.update(finish_reason=finish, usage=usage, transport=response.metadata)
                    if usage:
                        tokens += usage["total_tokens"] - counted
                    if focus:
                        focused = (
                            completed_json_prefix(raw)
                            if finish == "length"
                            else json.loads(raw, object_pairs_hook=unique_json_fields)
                        )
                        if set(focused) != {focus}:
                            raise ValueError("UNEXPECTED_FOCUSED_STAGE_KEYS")
                        raw_for_parse = json.dumps({k: focused.get(k, []) for k in STAGES[stage]})
                    else:
                        raw_for_parse = raw
                    parsed, item_errors = parse_stage_output(
                        raw_for_parse, stage, wire_anchors, finish, wire_quantities
                    )
                    expand_entity_refs(parsed, wire_entities)
                    stable_entity_keys(parsed, package)
                    combined = copy.deepcopy(output)
                    merge_output(combined, parsed)
                    validated = validate_output(
                        {**parsed, "entities": combined["entities"]}, package, document, semantic
                    )
                    parsed_keys = {e["key"] for e in parsed["entities"]}
                    rejected = [
                        {
                            "proposal_id": r["id"],
                            "kind": r["kind"],
                            "reasons": r["reasons"],
                            "proposal": r["proposal"],
                        }
                        for r in validated["records"]
                        if (r["kind"] != "entities" or r["proposal"]["key"] in parsed_keys)
                        and r["status"] == "REJECTED"
                    ]
                    outcome.update(
                        schema_errors=item_errors,
                        source_errors=rejected,
                        proposed_items=sum(len(v) for v in parsed.values()),
                    )
                    merge_output(output, parsed)
                    merge_output(retained, parsed)
                    outcome["proposed_items"] = sum(len(v) for v in retained.values())
                    outcome["model"] = (
                        "PARTIAL_SCHEMA"
                        if item_errors
                        else "PARTIAL_SOURCE"
                        if rejected
                        else "COMPLETE"
                    )
                    if (
                        rejected
                        and not item_errors
                        and any(
                            r["status"] != "REJECTED"
                            and (r["kind"] != "entities" or r["proposal"]["key"] in parsed_keys)
                            for r in validated["records"]
                        )
                    ):
                        # Quarantine independent invalid proposals. Their existence
                        # must not starve later scientific tasks of all processing.
                        outcome["model"] = "COMPLETE_WITH_REJECTIONS"
                    truncated = finish == "length"
                    if (
                        stage == "propositions"
                        and not any(parsed.values())
                        and re.search(
                            r"\b(?:results?|conclusions?|measured|observed)\b|\d\s*(?:mm/s|cm/s|RPM|%|Pa)\b",
                            text,
                            re.IGNORECASE,
                        )
                    ):
                        outcome["model"] = "EMPTY_WITH_SOURCE_CANDIDATES"
                        outcome["recovery"] = "TARGET_SOURCE_CANDIDATES"
                    feedback = {
                        "schema_errors": item_errors,
                        "source_rejections": [
                            {
                                "kind": r["kind"],
                                "reasons": r["reasons"],
                                "label_or_text": r["proposal"].get(
                                    "label", r["proposal"].get("text")
                                ),
                            }
                            for r in rejected
                        ],
                        "instruction": "Correct only the identified defects using supplied original anchors. Do not weaken scope/units/roles. Preserve valid independent proposals; do not invent support.",
                    }
                except ScientificTransportError as error:
                    raw, outcome["transport"] = error.content, error.metadata
                    outcome.update(model="FAILED", error_type=error.kind)
                    retry_after = error.retry_after
                    transient = error.kind in {
                        "rate_limit",
                        "transient_server",
                        "timeout",
                        "network",
                        "deadline",
                        "provider_stream_error",
                    }
                    if error.kind in {"access_denied", "interrupted"}:
                        provider_blocked[0] = True
                    if not usage and never_billed(error):
                        # The request was never processed, so what it is counted at is
                        # released and the spending brake counts only real use.
                        tokens -= counted
                    if error.kind == "request_rejected" and format_mode["type"] == "json_schema":
                        # A provider capability fallback is operational, never a schema relaxation.
                        format_mode = {"type": "json_object"}
                        transient = True
                    if error.content:
                        # A failed stream may still contain independent, closed items.
                        try:
                            parsed, errors = parse_stage_output(
                                error.content, stage, wire_anchors, "length", wire_quantities
                            )
                            expand_entity_refs(parsed, wire_entities)
                            stable_entity_keys(parsed, package)
                            merge_output(output, parsed)
                            merge_output(retained, parsed)
                            outcome["schema_errors"] = errors
                        except (ValueError, TypeError, KeyError):
                            pass
                    feedback = {"transport_error": error.kind}
                except (
                    OpenAIError,
                    ValueError,
                    TypeError,
                    KeyError,
                    IndexError,
                    RuntimeError,
                ) as error:
                    outcome.update(model="FAILED", error_type=type(error).__name__)
                    feedback = {
                        "response_error": type(error).__name__,
                        "instruction": "Return exactly this stage schema with valid supplied source-anchor IDs; no markdown or extra fields.",
                    }
                attempt.update(raw_response=raw, usage=usage, outcome=copy.deepcopy(outcome))
                service.registry.set_phase3_cache(
                    attempt_key,
                    "scientific_document_attempt",
                    {**attempt, "state": "FINISHED"},
                )
                history.append(attempt)
                service.registry.set_phase3_cache(
                    key,
                    "scientific_document_segment"
                    if outcome["model"] in {"COMPLETE", "COMPLETE_WITH_REJECTIONS"}
                    else "scientific_document_failure",
                    {"output": retained, "contract": CONTRACT, "attempt_receipts": history},
                )
                if (
                    outcome["model"]
                    in {"COMPLETE", "COMPLETE_WITH_REJECTIONS", "EMPTY_WITH_SOURCE_CANDIDATES"}
                    or provider_blocked[0]
                ):
                    break
                if truncated:
                    larger = min(envelope.output_tokens, capacity * 2)
                    if budget.max_output_tokens is not None:
                        larger = min(larger, budget.max_output_tokens)
                    if larger > capacity:
                        capacity = larger
                        feedback = None
                        continue
                    outcome["recovery"] = "SPLIT_TRUNCATED_TASK"
                    break
                if transient:
                    empty_deadline = (
                        outcome.get("error_type") in {"deadline", "timeout"} and not raw
                    )
                    if transient_attempts >= budget.retries or (
                        empty_deadline and model_index + 1 < len(model_options) and not retry_after
                    ):
                        if model_index + 1 >= len(model_options) or retry_after:
                            break
                        model_index += 1
                        transient_attempts = 0
                        feedback = None
                        outcome.setdefault("fallbacks", []).append(
                            {
                                "from": model_options[model_index - 1],
                                "to": model_options[model_index],
                                "reason": outcome.get("error_type"),
                                "task_and_evidence_preserved": True,
                            }
                        )
                        continue
                    transient_attempts += 1
                    # Do not wait indefinitely when the operator chose no overall
                    # campaign deadline. Never retry earlier than Retry-After.
                    delay = min(30, 2**transient_attempts)
                    if retry_after:
                        try:
                            delay = max(delay, float(retry_after))
                        except (ValueError, TypeError):
                            try:
                                when = parsedate_to_datetime(str(retry_after))
                                if when.tzinfo is None:
                                    when = when.replace(tzinfo=UTC)
                                delay = max(delay, when.timestamp() - time.time())
                            except (ValueError, TypeError, OverflowError):
                                pass
                    if delay > envelope.request_timeout_seconds:
                        outcome["recovery"] = "DEFERRED_PROVIDER_RETRY_AFTER"
                        outcome["retry_not_before"] = datetime.fromtimestamp(
                            time.time() + delay, UTC
                        ).isoformat()
                        attempt["outcome"] = copy.deepcopy(outcome)
                        service.registry.set_phase3_cache(
                            attempt_key,
                            "scientific_document_attempt",
                            {**attempt, "state": "FINISHED"},
                        )
                        service.registry.set_phase3_cache(
                            key,
                            "scientific_document_failure",
                            {"output": retained, "contract": CONTRACT, "attempt_receipts": history},
                        )
                        provider_blocked[0] = True
                        break
                    if available(reserve):
                        time.sleep(
                            min(
                                delay,
                                float("inf")
                                if budget.timeout_seconds is None
                                else max(0, budget.timeout_seconds - (time.monotonic() - started)),
                            )
                        )
                    feedback = None
                    continue
                if repairs >= budget.recovery_rounds:
                    break
                repairs += 1
        elif model_enabled:
            outcome["model"] = "UNAVAILABLE"
        outcomes.append(outcome)
        return outcome

    def process_task(window, stage, focus=None, result=None):
        if result is None:
            result = process_stage(window, stage, focus)
        failed = result["model"] in {
            "NEEDS_CONTEXT_SPLIT",
            "PARTIAL_SOURCE",
            "PARTIAL_SCHEMA",
            "EMPTY_WITH_SOURCE_CANDIDATES",
        }
        if failed or result.get("recovery") == "SPLIT_TRUNCATED_TASK":
            children = split_window(window)
            if children:
                recovery_windows.extend(children)
                recovered = [process_task(child, stage, focus) for child in children]
                if all(recovered):
                    result["model"] = "RECOVERED_BY_SPLIT"
                    return True
            elif result["model"] == "EMPTY_WITH_SOURCE_CANDIDATES" and focus is None:
                focused = [
                    process_task(window, stage, kind) for kind in ("statements", "quantities")
                ]
                if all(focused):
                    result["model"] = "RECOVERED_BY_FOCUSED_TASK"
                    return True
        return result["model"] in {
            "COMPLETE",
            "COMPLETE_WITH_REJECTIONS",
            "CACHE_REPLAY",
            "DISABLED",
        }

    # Discover identities throughout the source before resolving scientific
    # references. Recovery cannot monopolize an early document window.
    deferred = []
    prior_identity_windows = {
        o["segment_id"]
        for o in previous.get("processing", {}).get("outcomes", [])
        if o["stage"] == "identity"
        and o.get("focus") is None
        and o["model"] in {"COMPLETE", "COMPLETE_WITH_REJECTIONS", "CACHE_REPLAY"}
    }
    # Relationships run after the targeted recovery below: the printed structure
    # already proposes memberships and row conditions, and a deadline must not
    # starve the recovery of omitted source values.
    for stage in [stage for stage in STAGES if stage != "relationships"]:
        if recovery_only and stage != "identity":
            continue
        prefetch(windows, stage)
        for window in windows:
            if recovery_only and stage == "identity" and window["id"] in prior_identity_windows:
                outcomes.append(
                    {
                        "segment_id": window["id"],
                        "stage": stage,
                        "focus": None,
                        "model": "CACHE_REPLAY",
                        "attempts": 0,
                        "members": [
                            {k: m[k] for k in ("id", "evidence_id", "start", "end")}
                            for m in window["members"]
                        ],
                        "basis": "PRIOR_COMPLETED_IDENTITY_WINDOW_WITH_REVALIDATED_ORIGINAL_PROPOSALS",
                    }
                )
                cached += 1
                continue
            result = process_stage(window, stage)
            if result["model"] not in {
                "COMPLETE",
                "COMPLETE_WITH_REJECTIONS",
                "CACHE_REPLAY",
                "DISABLED",
            }:
                deferred.append((window, stage, result))
        settle_prefetch()
        if stage == "propositions" and role_check and model_enabled:
            role_for.update(
                missing_fields(
                    output, package, document, semantic, windows, ROLE_CHECK_WORDS, detail=True
                )
            )
            for window in windows:
                if window["id"] in role_for:
                    process_stage(window, stage)
            role_for.clear()
        if stage == "identity" and model_enabled:
            checked_identities = validate_output(output, package, document, semantic)
            sample_pages = {
                s["evidence_id"]
                for r in checked_identities["records"]
                if r["kind"] == "entities"
                and r["status"] != "REJECTED"
                and r["proposal"]["class_id"] == "Sample"
                for s in r["support_spans"]
            }
            supported_groups = {
                normalized(r["proposal"]["label"])
                for r in validate_output(output, package, document, semantic)["records"]
                if r["kind"] == "entities"
                and r["status"] == "SOURCE_SUPPORTED"
                and r["proposal"]["class_id"] == "ExperimentFamily"
            }
            ambiguous = [
                e
                for e in output["entities"]
                if e["class_id"]
                in {"Material", "Investigation", "GravityCondition", "ExperimentalCondition"}
                and qualified_material_heading(e["label"], document, semantic)
                and normalized(e["label"]) != normalized(package["title"])
                and normalized(e["label"]) not in supported_groups
            ]
            for window in windows:
                missing_quantified_samples = any(
                    m["evidence_id"] not in sample_pages
                    and re.search(r"\b(?:samples?|specimens?)\b", m["text"], re.IGNORECASE)
                    and re.search(r"\d\s*(?:mm|cm|m|g)\b", m["text"])
                    for m in window["members"]
                )
                if missing_quantified_samples or any(
                    any(
                        span["evidence_id"] == member["evidence_id"]
                        for span in e["support"]
                        for member in window["members"]
                    )
                    for e in ambiguous
                ):
                    process_task(window, "identity", "entities")

    def recover_stage(window, stage, focus=None, subject=None):
        """One recovery request, retried once on the window's halves.

        A recovery request can exceed the provider context, or be cut short,
        although the window's ordinary stages fit. It is then asked once more
        on each half; a half that still does not fit stays a reported gap. An
        empty answer that the model finished is not chased into smaller pieces.
        """
        result = process_stage(window, stage, focus, subject)
        if (
            result["model"] in {"NEEDS_CONTEXT_SPLIT", "PARTIAL_SOURCE", "PARTIAL_SCHEMA"}
            or result.get("recovery") == "SPLIT_TRUNCATED_TASK"
            or (
                result["model"] == "EMPTY_WITH_SOURCE_CANDIDATES"
                and result.get("finish_reason") == "length"
            )
        ):
            children = split_window(window)
            if children:
                recovery_windows.extend(children)
                halves = [process_stage(child, stage, focus, subject) for child in children]
                if all(h["model"] in {"COMPLETE", "COMPLETE_WITH_REJECTIONS"} for h in halves):
                    result["model"] = "RECOVERED_BY_SPLIT"
        return result

    # Target omissions detected against original literal quantities. Progress is
    # a shrinking set of source locations, never a model's claim of completeness.
    for window in windows:
        while model_enabled:
            checked = validate_output(output, package, document, semantic)
            inventory = coverage(package, document, checked, outcomes, [])
            gaps = {
                (a["evidence_id"], q["start"], q["end"])
                for a in inventory["source_units"]
                if any(
                    a["evidence_id"] == m["evidence_id"]
                    and a["start"] < m["end"]
                    and a["end"] > m["start"]
                    for m in window["members"]
                )
                for q in a["quantity_inventory"]
                if q["state"] == "NOT_STRUCTURED"
            }
            if not gaps:
                break
            before = len(gaps)
            result = recover_stage(window, "propositions", "quantities")
            updated = coverage(
                package,
                document,
                validate_output(output, package, document, semantic),
                outcomes,
                [],
            )
            remaining = {
                (a["evidence_id"], q["start"], q["end"])
                for a in updated["source_units"]
                for q in a["quantity_inventory"]
                if q["state"] == "NOT_STRUCTURED"
            }
            if len(gaps & remaining) >= before:
                result["coverage_recovery"] = "NO_VERIFIED_QUANTITY_PROGRESS_RETAIN_GAPS"
                break
            result["coverage_recovery"] = "VERIFIED_SOURCE_QUANTITY_PROGRESS"
    if not recovery_only:
        prefetch(windows, "relationships")
        for window in windows:
            result = process_stage(window, "relationships")
            if result["model"] not in {
                "COMPLETE",
                "COMPLETE_WITH_REJECTIONS",
                "CACHE_REPLAY",
                "DISABLED",
            }:
                deferred.append((window, "relationships", result))
        settle_prefetch()
        if model_enabled:
            # A group whose own subsection prints conditions, materials, samples
            # or interventions, but which no accepted relation links yet, gets
            # one request directed at that subsection with the group as subject.
            for group_key, members in unlinked_group_subsections(
                output, package, document, semantic
            ):
                window = {
                    "id": "group-" + identity([group_key, *(m["id"] for m in members)])[:24],
                    "members": members,
                }
                recover_stage(window, "relationships", subject=group_key)
    if recovery_only:
        from nasa_fire_ai.ingestion.scientific_coverage import statement_candidates

        pending_statements = statement_candidates(
            package, document, validate_output(output, package, document, semantic)
        )
        pending = validate_output(output, package, document, semantic)
        unresolved_ids = {
            s["evidence_id"]
            for r in pending["records"]
            if r["kind"] == "statements" and r["status"] == "UNRESOLVED"
            for s in r["support_spans"]
        }
        unresolved_ids.update(
            c["evidence_id"] for c in pending_statements if c["state"] == "NOT_STRUCTURED"
        )
        for window in windows:
            if any(m["evidence_id"] in unresolved_ids for m in window["members"]):
                recover_stage(window, "propositions", "statements")
        for window in windows:
            recover_stage(window, "relationships")
    for window, stage, result in deferred:
        process_task(window, stage, result=result)
    if pool is not None:
        pool.shutdown(wait=False, cancel_futures=True)
    resolve_explicit_scopes(output, document)
    # Resolving a retained unresolved scope can make two proposals identical.
    # Canonicalize again rather than accumulating duplicates on every replay.
    consolidated = Output().model_dump()
    merge_output(consolidated, output)
    output = consolidated
    validation = validate_output(output, package, document, semantic)
    from nasa_fire_ai.ingestion.semantic_candidates import candidate_inventory, link_proposals

    # The document's printed terms with evidence, reconciled against the approved
    # vocabulary once per preparation; every staged term is linked to one or flagged.
    validation["semantic_candidates"] = candidate_inventory(package, document, semantic)
    validation["candidate_link_trace"] = link_proposals(
        [
            p
            for p in validation.get("ontology_extension_proposals") or []
            if p.get("proposal_state") == "PROPOSED_ONTOLOGY_EXTENSION"
        ],
        validation["semantic_candidates"],
    )
    table_mappings = table_mapping_decisions(service, package, semantic)
    quantities = table_quantities(service, package, table_mappings)
    from nasa_fire_ai.ingestion.pdf_quantities import pdf_table_quantities

    original_pdf_quantities = pdf_table_quantities(package, document)
    scientific_coverage = coverage(package, document, validation, outcomes, quantities)
    if restoring:
        scientific_coverage["model_proposed_items"] = max(
            scientific_coverage["model_proposed_items"],
            previous.get("scientific_coverage", {}).get("model_proposed_items", 0),
        )
        if scientific_coverage["model_proposed_items"]:
            scientific_coverage["scientific_completeness"] = "SOURCE_ADJUDICATION_REQUIRED"
    return {
        "contract": CONTRACT,
        "contract_digest": service.contract_digest(),
        "document": document,
        "raw_proposals": output,
        "source_policy": {
            "status": package.get("source_provenance", {}).get(
                "eligibility", "NASA_ASSOCIATION_NOT_ESTABLISHED"
            ),
            "source_provenance": package.get("source_provenance"),
            "third_party_citations": "Bibliographic context; not promoted to NASA findings",
        },
        "table_semantic_mappings": table_mappings,
        "table_quantity_proposals": quantities,
        "pdf_table_quantity_proposals": original_pdf_quantities,
        "scientific_coverage": scientific_coverage,
        "table_row_role_proposals": table_row_roles(package),
        "structured_table_records": table_records(document),
        **validation,
        "processing": {
            "budget": {**asdict(budget), "segment_chars": chars},
            "resource_policy": {
                "provider_envelope": asdict(envelope),
                "request_context_tokens": request_limit,
                "scientific_item_ceiling": None,
                "adaptive": True,
            },
            "model": settings.scientific_model if model_enabled else None,
            "configured_fallback_models": list(settings.science_fallback_models),
            "new_model_calls": calls,
            **({"window_prefetch": prefetch_counts} if prefetch_counts["sent"] else {}),
            **(
                {"origin_audit": origin_audit(validation.get("records", []))}
                if origin_check_enabled()
                else {}
            ),
            **(
                {
                    "missing_facts": missing_fact_report(
                        validation.get("records", []),
                        clean_candidates(validation.get("semantic_candidates", []), document)
                        if candidate_hygiene_enabled()
                        else validation.get("semantic_candidates", []),
                        document,
                        {e["evidence_id"]: e["source_id"] for e in package.get("evidence", [])},
                    )
                }
                if missing_fact_report_enabled()
                else {}
            ),
            "restored_proposals_after_source_validation": restored_count,
            "recovered_cached_proposals_after_source_validation": recovered_cached_proposals,
            "targeted_recovery_mode": recovery_only,
            "scientific_completeness": scientific_coverage["scientific_completeness"],
            "tokens_consumed_or_reserved": tokens,
            "cached_segments": cached,
            "duration_seconds": time.monotonic() - started,
            "outcomes": outcomes,
            "status": "PARTIAL_MODEL_COVERAGE"
            if (model_enabled and scientific_coverage["outstanding_source_units"])
            or any(
                o["model"]
                in {
                    "FAILED",
                    "PARTIAL_SCHEMA",
                    "PARTIAL_SOURCE",
                    "DEFERRED_BUDGET",
                    "UNAVAILABLE",
                    "PROVIDER_BLOCKED",
                    "NEEDS_CONTEXT_SPLIT",
                    "EMPTY_WITH_SOURCE_CANDIDATES",
                }
                for o in outcomes
            )
            else "COMPLETE",
            "deterministic_characters": document["coverage"]["segmented_characters"],
            "model_characters": sum(
                sum(s["end"] - s["start"] for s in w["members"])
                for w in windows
                if all(
                    o["model"]
                    in {
                        "COMPLETE",
                        "CACHE_REPLAY",
                        "RECOVERED_BY_SPLIT",
                        "RECOVERED_BY_FOCUSED_TASK",
                        "COMPLETE_WITH_REJECTIONS",
                    }
                    for o in outcomes
                    if o["segment_id"] == w["id"]
                )
            ),
        },
        "scientific_approval": "NONE",
        "baseline_changes": 0,
    }
