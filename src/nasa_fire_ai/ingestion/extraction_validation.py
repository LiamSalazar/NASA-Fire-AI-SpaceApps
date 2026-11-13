"""Validation of a model output against the source: every record is checked, staged or held."""

import copy
import json
import re

from nasa_fire_ai.ingestion.document_structure import identity
from nasa_fire_ai.ingestion.entity_validation import validate_entity
from nasa_fire_ai.ingestion.extraction_parsing import proposal_identity
from nasa_fire_ai.ingestion.ontology_context import relation_signatures
from nasa_fire_ai.ingestion.printed_layout import (
    section_for_span,
)
from nasa_fire_ai.ingestion.proposal_states import adopt_proposed_term
from nasa_fire_ai.ingestion.quantity_naming import (
    qualified_material_heading,
)
from nasa_fire_ai.ingestion.quantity_validation import validate_quantity
from nasa_fire_ai.ingestion.relation_contracts import RELATION_ENDPOINTS
from nasa_fire_ai.ingestion.relation_validation import validate_relation
from nasa_fire_ai.ingestion.scientific_facets import (
    structured_provenance_enabled,
)
from nasa_fire_ai.ingestion.scientific_scope import (
    hold_mentioned_only_materials,
)
from nasa_fire_ai.ingestion.source_spans import (
    locate,
    mentions,
    normalized,
)
from nasa_fire_ai.ingestion.statement_provenance import (
    structure_provenance,
)
from nasa_fire_ai.ingestion.statement_validation import (  # noqa: F401
    article_subject_cue,
    article_terms,
    validate_statement,
)
from nasa_fire_ai.ingestion.structural_candidates import (
    recover_group_classes,
    structure_entity_candidates,
    structure_quantity_candidates,
    structure_relation_candidates,
)
from nasa_fire_ai.ingestion.value_origin import origin_check, origin_check_enabled

# A statement held only because its proposed role contradicts what the
# validator itself detects is revalidated once with the detected role.
ROLE_RECOVERY = (
    (
        {
            "OBSERVATION_STATES_A_CRITERION",
            "CONFIGURATION_STATEMENT_STATES_A_CRITERION",
            "CHANGING_OBSERVATION_IS_NOT_ESTABLISHED_CONFIGURATION",
        },
        {"OBSERVATION_STATES_A_CRITERION", "CONFIGURATION_STATEMENT_STATES_A_CRITERION"},
        ("normative_requirement", "Requirement"),
    ),
    (
        {"DERIVATION_NOT_ESTABLISHED_IN_ORIGINAL_PASSAGE"},
        {"DERIVATION_NOT_ESTABLISHED_IN_ORIGINAL_PASSAGE"},
        ("measured_observation", "ReportedObservation"),
    ),
    (
        {"AUTHOR_ROLE_REQUIRES_CONTEXT_REVIEW"},
        {"AUTHOR_ROLE_REQUIRES_CONTEXT_REVIEW"},
        ("measured_observation", "ReportedObservation"),
    ),
    (
        {"DOCUMENTARY_ROLE_REPORTS_AN_OBSERVATION"},
        {"DOCUMENTARY_ROLE_REPORTS_AN_OBSERVATION"},
        ("measured_observation", "ReportedObservation"),
    ),
)
# Wording that makes a passage an inference rather than a reported result.
INFERENCE = re.compile(
    r"\b(?:suggest\w*|conclu\w*|likely|probabl\w*|due\s+to|because|therefore|thus|hence"
    r"|recommend\w*|attribut\w*|explain\w*|may|might|could|should|believ\w*|expect\w*"
    r"|appears?|seems?|candidate|suitable|acceptable|ideal|best|compatib\w*|outperform\w*"
    r"|superior|better|worse|excellent|promis\w*|great)\b",
    re.IGNORECASE,
)


def recover_statement_roles(records, output, package, document, semantic):
    """Revalidate role-only holds with the role the validator detected."""
    for record in records:
        if record["kind"] != "statements" or record["status"] != "UNRESOLVED":
            continue
        reasons = set(record["reasons"])
        # A recording or acceptance rule applies to the study's procedure, not
        # to one specimen: its subject is revalidated at the study's scope.
        rule_scope = "STATEMENT_SUBJECT_APPLICABILITY_UNRESOLVED" in reasons
        for allowed, required, (epistemic, class_id) in ROLE_RECOVERY:
            if epistemic == "normative_requirement" and rule_scope:
                allowed = allowed | {"STATEMENT_SUBJECT_APPLICABILITY_UNRESOLVED"}
            if not reasons or not reasons <= allowed or not reasons & required:
                continue
            from nasa_fire_ai.ingestion.statement_integrity import (
                observation_cue,
                reported_outcome,
            )

            text = record["proposal"]["text"]
            if (
                "AUTHOR_ROLE_REQUIRES_CONTEXT_REVIEW" in reasons
                and record["proposal"]["epistemic"] == "author_reported_conclusion"
                and (INFERENCE.search(text) or not reported_outcome(text))
            ):
                break  # an inference outside the conclusions stays an interpretation
            if record["proposal"]["epistemic"] not in {
                "documentary_context",
                "author_reported_conclusion",
                "derived_quantity",
                "measured_observation",
                "experimental_configuration",
            }:
                break
            if epistemic == "measured_observation" and not (
                observation_cue(text)
                and re.search(
                    r"\b(?:was|were|shows?|showed|shown|seen|reveals?|revealed|performed|produced"
                    r"|reacted|passed|failed"
                    r"|decreased|increased|indicated?|demonstrated?|observed)\b",
                    text,
                    re.IGNORECASE,
                )
            ):
                break  # a caption or a pointer reports no observed result
            item = {**record["proposal"], "epistemic": epistemic, "class_id": class_id}
            if epistemic == "normative_requirement" and rule_scope:
                roots = [
                    e["key"]
                    for e in output["entities"]
                    if e["class_id"] == "Investigation"
                    and e.get("study") == "current"
                    and normalized(e["label"]) == normalized(document.get("package_title", ""))
                ]
                if len(roots) != 1:
                    break
                item["subjects"] = roots
            trial = {
                "entities": output["entities"],
                "statements": [item],
                "relations": [],
                "quantities": [],
                "concepts": [],
            }
            result = validate_output(trial, package, document, semantic, recover_roles=False)
            match = next(
                (
                    r
                    for r in result["records"]
                    if r["kind"] == "statements" and not r.get("candidate_origin")
                ),
                None,
            )
            if match and match["status"] == "SOURCE_SUPPORTED":
                original = record["proposal"]
                record.update(
                    {k: v for k, v in match.items() if k not in {"id"}},
                    role_recovery={
                        "proposed_epistemic": original["epistemic"],
                        "proposed_class_id": original["class_id"],
                        "held_for": sorted(reasons),
                        "recovered_epistemic": epistemic,
                        "method": "FULL_REVALIDATION_WITH_THE_DETECTED_ROLE",
                        "proposed_subjects": original.get("subjects", []),
                        "rule_scoped_to_study": epistemic == "normative_requirement" and rule_scope,
                    },
                )
            break


CONCLUSION_ROLE_HOLDS = {
    "AUTHOR_ROLE_REQUIRES_CONTEXT_REVIEW",
    "INTERPRETATION_DESCRIBES_A_PROCEDURE",
    "STATEMENT_SUBJECT_APPLICABILITY_UNRESOLVED",
    "STATEMENT_REQUIRES_EXPERIMENTAL_SCOPE",
}


def recover_conclusion_roles(records, output, package, document, semantic):
    """Revalidate a held "conclusion" that is a rule, a data source or a procedure.

    "If the vessel reading climbs past 380°C ... then the onset is logged
    as >380°C" is a recording rule, "The values for the comparison ... were obtained
    from ..." says where data came from, and "The coupons ... were assessed
    with a Model 9 bomb calorimeter" is a method step; none is the authors'
    conclusion. Held only for that role or for its scope, the passage is
    revalidated once with the role its own wording states, at the study's scope.
    """
    from nasa_fire_ai.ingestion.statement_integrity import (
        DATA_PROVENANCE,
        DETECTION_METHOD,
        documentary_pointer,
        procedure_without_interpretation,
        reported_outcome,
        stated_criterion,
    )

    roots = [
        e["key"]
        for e in output["entities"]
        if e["class_id"] == "Investigation"
        and e.get("study") == "current"
        and normalized(e["label"]) == normalized(document.get("package_title", ""))
    ]
    if len(roots) != 1:
        return
    for record in records:
        proposal = record["proposal"]
        reasons = set(record["reasons"])
        if (
            record["kind"] != "statements"
            or record["status"] != "UNRESOLVED"
            or record.get("role_recovery")
            or proposal.get("study") != "current"
            or proposal["epistemic"]
            not in {"author_reported_conclusion", "tentative_interpretation"}
            or not reasons
            or not reasons <= CONCLUSION_ROLE_HOLDS
        ):
            continue
        text = proposal["text"]
        if stated_criterion(text):
            role = ("normative_requirement", "Requirement")
        elif DATA_PROVENANCE.search(text) or documentary_pointer(text):
            role = ("documentary_context", "Publication")
        elif (
            procedure_without_interpretation(text) or DETECTION_METHOD.search(text)
        ) and not reported_outcome(text):
            role = ("experimental_configuration", "ExperimentalCondition")
        else:
            continue
        item = {**proposal, "epistemic": role[0], "class_id": role[1], "subjects": roots}
        trial = {
            "entities": output["entities"],
            "statements": [item],
            "relations": [],
            "quantities": [],
            "concepts": [],
        }
        result = validate_output(trial, package, document, semantic, recover_roles=False)
        match = next(
            (
                r
                for r in result["records"]
                if r["kind"] == "statements" and not r.get("candidate_origin")
            ),
            None,
        )
        if match and match["status"] == "SOURCE_SUPPORTED":
            record.update(
                {k: v for k, v in match.items() if k not in {"id"}},
                role_recovery={
                    "proposed_epistemic": proposal["epistemic"],
                    "proposed_class_id": proposal["class_id"],
                    "held_for": sorted(reasons),
                    "recovered_epistemic": role[0],
                    "method": "FULL_REVALIDATION_WITH_THE_ROLE_ITS_WORDING_STATES",
                    "proposed_subjects": proposal.get("subjects", []),
                    "rule_scoped_to_study": True,
                },
            )


def state_settled_roles(records, held):
    """Settle a setting-versus-result conflict on one table cell from its column's state word.

    "Initial Test Pressure" names the state a test is set to; "Final Test
    Pressure" names the state measured at its end. Only a conflict between
    exactly those two roles on one bound cell is settled; the other reading is
    still held.
    """
    groups = {}
    for record in records:
        if (
            record["id"] in held
            and record["kind"] == "quantities"
            and record.get("table_row_binding")
        ):
            key = tuple((v["evidence_id"], v["start"]) for v in record["quantity_value_spans"])
            groups.setdefault(key, []).append(record)
    settled = {}
    for members in groups.values():
        roles = {r["proposal"]["epistemic"] for r in members}
        if roles != {"experimental_configuration", "reported_quantity"}:
            continue
        headers = {
            h["column_header"] or "" for r in members for h in r["table_row_binding"]["rows"]
        }
        words = {w.lower() for h in headers for w in re.findall(r"[A-Za-z]+", h)}
        dimensions = {"thickness", "diameter", "length", "width", "mass", "weight"}
        if words & {"initial", "set", "nominal", "starting"} and not words & {"final", "measured"}:
            keep = "experimental_configuration"
        elif words & dimensions and not words & {"final", "measured", "loss", "change"}:
            # A specimen's own dimension is how the test was set up.
            keep = "experimental_configuration"
        elif words & {"final", "measured"} and not words & {
            "initial",
            "set",
            "nominal",
            "starting",
        }:
            keep = "reported_quantity"
        else:
            continue
        for r in members:
            settled[r["id"]] = {
                "basis": "COLUMN_STATE_WORD_SETTLES_SETTING_OR_RESULT",
                "column_headers": sorted(headers),
                "kept": r["proposal"]["epistemic"] == keep,
            }
    return settled


# The last validations, by the digest of what was validated: the extraction
# validates an unchanged output again between stages and recovery rounds.
_VALIDATIONS = {}


def validate_output(output, package, document, semantic, recover_roles=True):
    """The validation of this output, recomputed only when the output has changed.

    Callers receive their own copy. A validation that changed the output it was
    given is never reused.
    """
    import hashlib

    def digest():
        return hashlib.sha256(
            json.dumps(output, sort_keys=True, ensure_ascii=False, default=str).encode()
        ).hexdigest()

    key = (
        id(package),
        id(package.get("evidence")),
        len(package.get("evidence") or []),
        id(document),
        id(semantic),
        recover_roles,
        digest(),
    )
    cached = _VALIDATIONS.get(key)
    if cached and cached[0] is package and cached[1] is document and cached[2] is semantic:
        return copy.deepcopy(cached[3])
    result = validated_output(output, package, document, semantic, recover_roles)
    if digest() == key[-1]:
        if len(_VALIDATIONS) > 8:
            _VALIDATIONS.clear()
        _VALIDATIONS[key] = (package, document, semantic, copy.deepcopy(result))
    return result


def validate_concept(item, record, spans, semantic):
    """Validate one concept proposal; raises on rejection."""
    if not any(mentions(item["term"], s["quote"]) for s in spans):
        raise ValueError("CONCEPT_TERM_ABSENT")
    _status, prop = semantic.resolve_property(item["term"])
    matches = [
        c
        for c in semantic.class_metadata
        if normalized(c) == normalized(item["term"])
        or normalized(item["term"])
        in [normalized(t) for t in semantic.class_metadata[c].get("query_terms", [])]
    ]
    matches.extend(
        key
        for key in getattr(semantic, "ontology_datatype_properties", {})
        if normalized(key) == normalized(item["term"])
    )
    record["mapping"] = {
        "kind": "existing_concept" if prop or matches else "minimal_extension_proposal",
        "existing": prop or matches,
        "approved_definitions_examined": sorted(semantic.class_metadata),
        "approved_properties_examined": sorted(semantic.properties),
        "approved_relations_examined": sorted(semantic.relations),
        "approved_datatype_properties_examined": sorted(
            getattr(semantic, "ontology_datatype_properties", {})
        ),
        "activation": "NONE",
    }
    record["status"] = "UNRESOLVED"
    record["reasons"].append(
        "EXISTING_CONCEPT_REUSE_REQUIRED" if prop or matches else "ONTOLOGY_EXTENSION_REVIEW"
    )


def validated_output(output, package, document, semantic, recover_roles=True):
    """Independent validation recomputed from source text and approved contracts.

    SOURCE_SUPPORTED is a bounded lexical/structural validation status, never
    scientific approval. Unproven semantic entailment is review-required.
    """
    evidence = {e["evidence_id"]: e for e in package["evidence"]}
    from nasa_fire_ai.ingestion.numeric_expressions import decimal_convention

    # The document's own unambiguous numerals decide whether "1,250" groups
    # thousands; without that evidence the expression stays ambiguous.
    numeric_convention = decimal_convention(
        "\n".join(e.get("text", "") for e in package["evidence"])
    )
    entities, records, mappings = {}, [], []
    output, class_recovery = recover_group_classes(output, document)
    structural_entities = structure_entity_candidates(output, package, document)
    if structural_entities:
        output = {**output, "entities": output["entities"] + structural_entities}
    key_signatures = {}
    for item in output["entities"]:
        signature = identity(
            [
                normalized(item["label"]),
                item["class_id"],
                item["study"],
                sorted(
                    {evidence.get(s["evidence_id"], {}).get("source_id") for s in item["support"]}
                ),
            ]
        )
        key_signatures.setdefault(item["key"], set()).add(signature)
    ambiguous_keys = {k for k, signatures in key_signatures.items() if len(signatures) > 1}
    structural = structure_relation_candidates(output, document)
    structural_quantities = structure_quantity_candidates(output, package, document)
    for kind in ("entities", "statements", "relations", "quantities", "concepts"):
        extra = {"relations": structural, "quantities": structural_quantities}.get(kind, [])
        own_ids = {proposal_identity(kind, o) for o in output[kind]}
        for original in output[kind] + extra:
            item = copy.deepcopy(original)
            proposal_id = proposal_identity(kind, item)
            if any(original is c for c in extra) and proposal_id in own_ids:
                continue  # the model already proposed exactly this item
            record = {
                "id": proposal_id,
                "kind": kind,
                "proposal": item,
                "status": "SOURCE_SUPPORTED",
                "reasons": [],
                "support_spans": [],
            }
            try:
                spans = locate(item["support"], evidence)
                record["support_spans"] = spans
                adopt_proposed_term(kind, item, record, semantic)
                if kind == "entities":
                    validate_entity(
                        item,
                        record,
                        spans,
                        entities,
                        document,
                        semantic,
                        evidence,
                        package,
                        ambiguous_keys,
                    )
                elif kind == "statements":
                    validate_statement(
                        item, record, spans, entities, document, semantic, evidence, package
                    )
                elif kind == "relations":
                    validate_relation(
                        item,
                        record,
                        spans,
                        entities,
                        document,
                        semantic,
                        evidence,
                        package,
                        records,
                    )
                elif kind == "quantities":
                    validate_quantity(
                        item,
                        record,
                        spans,
                        entities,
                        document,
                        semantic,
                        evidence,
                        numeric_convention,
                    )
                    if origin_check_enabled():
                        origin_check(item, record, spans, entities, document, evidence)
                elif kind == "concepts":
                    validate_concept(item, record, spans, semantic)
                if (
                    kind in {"statements", "quantities"}
                    and item.get("epistemic") in {"measured_observation", "reported_quantity"}
                    and any(
                        re.search(
                            r"\b(?:analysis|model|simulation|prediction)\b",
                            section_for_span(s, document),
                            re.IGNORECASE,
                        )
                        for s in spans
                    )
                ):
                    record["status"] = "UNRESOLVED"
                    record["reasons"].append(
                        "MODEL_OR_ANALYSIS_SECTION_OBSERVATION_ROLE_REQUIRES_REVIEW"
                    )
                    if kind == "quantities":
                        record["native_value_compatible"] = False
                        record["native_representation"] = "DEFERRED_MODEL_OR_ANALYSIS_CONTEXT"
            except (ValueError, TypeError, KeyError) as error:
                record["status"] = "REJECTED"
                record["reasons"].append(str(error))
            if record.get("mapping"):
                mappings.append({"proposal_id": record["id"], **record["mapping"]})
            if kind == "entities" and item.get("key") in entities:
                if record["status"] == "REJECTED":
                    entities.pop(item["key"])
                else:
                    entities[item["key"]]["validation_status"] = record["status"]
            if kind == "entities" and item.get("key") in class_recovery:
                record["class_recovery"] = class_recovery[item["key"]]
            if any(original is c for c in extra) or (
                kind == "entities" and any(original is c for c in structural_entities)
            ):
                record["candidate_origin"] = "PRINTED_SOURCE_STRUCTURE"
            records.append(record)
    if recover_roles:
        recover_statement_roles(records, output, package, document, semantic)
        recover_conclusion_roles(records, output, package, document, semantic)
    # A repaired, explicitly scoped group supersedes an unresolved whole-study
    # typing of that exact source heading. Endpoints are never remapped.
    repaired_groups = {
        (
            r["support_spans"][0]["source_id"],
            normalized(r["proposal"]["label"]),
            r["proposal"]["study"],
        )
        for r in records
        if r["kind"] == "entities"
        and r["status"] == "SOURCE_SUPPORTED"
        and r["proposal"]["class_id"] == "ExperimentFamily"
        and qualified_material_heading(r["proposal"]["label"], document, semantic)
    }
    for r in records:
        if (
            r["kind"] == "entities"
            and r["status"] == "UNRESOLVED"
            and r["proposal"]["class_id"] == "Investigation"
            and "INVESTIGATION_TYPE_SOURCE_ROLE_UNRESOLVED" in r["reasons"]
            and (
                r["support_spans"][0]["source_id"],
                normalized(r["proposal"]["label"]),
                r["proposal"]["study"],
            )
            in repaired_groups
        ):
            r["status"] = "REJECTED"
            r["reasons"].append("SCOPED_GROUP_ROLE_REPAIRED_WITH_ORIGINAL_EVIDENCE")
            entities.pop(r["proposal"]["key"], None)
    for r in records:
        item = r["proposal"]
        endpoints = (
            item.get("subjects", [])
            if r["kind"] == "statements"
            else [item["subject"], item["object"]]
            if r["kind"] == "relations"
            else [item["subject"]]
            if r["kind"] == "quantities"
            else []
        )
        if any(key not in entities for key in endpoints):
            reason = {
                "statements": "UNKNOWN_STATEMENT_ENDPOINT",
                "relations": "UNKNOWN_RELATION_ENDPOINT",
                "quantities": "UNKNOWN_QUANTITY_ENDPOINT",
            }[r["kind"]]
            r["status"] = "REJECTED"
            if reason not in r["reasons"]:
                r["reasons"].append(reason)
    from nasa_fire_ai.ingestion.scientific_scope import consolidate_validated_variants
    from nasa_fire_ai.ingestion.statement_integrity import (
        conflicting_modalities,
        conflicting_roles,
    )

    # One source sentence accepted both as, say, a configuration and as an
    # interpretation contradicts itself; neither reading is promoted.
    held = conflicting_roles(records, evidence)
    modality_conflicts = conflicting_modalities(records)
    settled = state_settled_roles(records, held)
    for record in records:
        if record["id"] in settled:
            record["role_settlement"] = settled[record["id"]]
            if settled[record["id"]]["kept"]:
                continue
        if record["id"] in held:
            record["status"] = "UNRESOLVED"
            record["reasons"].append("CONFLICTING_ROLE_PROPOSALS_FOR_SAME_SOURCE_SPAN")
    for record in records:
        if record["id"] in modality_conflicts:
            record["status"] = "UNRESOLVED"
            record["reasons"].append("CONFLICTING_MODALITY_READINGS_FOR_SAME_SOURCE_SPAN")
    consolidate_validated_variants(records, entities, evidence, document)
    hold_mentioned_only_materials(records, document)
    if structured_provenance_enabled():
        structure_provenance(records, entities, document)
    # Group by underlying reason AND documentary source, not one question per assertion.
    issues = {}
    for record in records:
        if record["status"] != "UNRESOLVED":
            continue
        for reason in record["reasons"]:
            # Scientific uncertainty itself is not a defect; missing subject identity is.
            source = (
                record["support_spans"][0]["source_id"] if record["support_spans"] else "unknown"
            )
            term = (
                record["proposal"].get("term", record["proposal"].get("label", ""))
                if reason in {"ONTOLOGY_EXTENSION_REVIEW", "QUANTITY_SEMANTICS_OR_UNIT_UNRESOLVED"}
                else ""
            )
            key = (reason, source, term)
            choices = sorted(
                {
                    e["label"]
                    for e in entities.values()
                    if e["source_id"] == source
                    and e["class_id"] in {"ExperimentalRun", "Investigation", "ExperimentFamily"}
                }
            )
            question = {
                "CURRENT_OR_CITED_STUDY_UNRESOLVED": "Does this evidence describe the current investigation or a cited earlier study?",
                "STATEMENT_SUBJECT_APPLICABILITY_UNRESOLVED": "Which documented experiment or group do these statements describe?",
                "LOCAL_SUBJECT_BINDING_UNRESOLVED": "Which experimental subject does the stated condition belong to?",
                "CITED_STUDY_APPLICABILITY_REQUIRES_REVIEW": "Which earlier study is being compared here, and which result belongs to it?",
                "ONTOLOGY_EXTENSION_REVIEW": f"How should the source term '{term}' be defined and represented using existing scientific concepts?",
                "QUANTITY_SEMANTICS_OR_UNIT_UNRESOLVED": f"What quantity does '{term}' denote, and what unit does the source establish?",
                "ENTITY_TYPE_SOURCE_ROLE_UNRESOLVED": "Does the source identify an executed run, a specimen, or only a study description?",
            }.get(
                reason,
                "What documented meaning and applicability does this proposed relationship have?",
            )
            issue = issues.setdefault(
                key,
                {
                    "id": "issue-" + identity(key)[:20],
                    "kind": reason,
                    "source_id": source,
                    "dependent_proposals": [],
                    "evidence_ids": [],
                    "support_spans": [],
                    "question": question,
                    "alternatives": choices[:12] + ["Retain unresolved", "Documentary context"],
                    "source_resolution_attempts": [
                        "literal source span",
                        "surrounding section and shared methods",
                        "approved semantic definitions and aliases",
                        "identified subject anchors",
                    ],
                    "status": "SCIENTIFIC_REVIEW_REQUIRED",
                },
            )
            issue["dependent_proposals"].append(record["id"])
            issue["evidence_ids"] = sorted(
                set(issue["evidence_ids"]) | {s["evidence_id"] for s in record["support_spans"]}
            )
            if len(issue["support_spans"]) < 6:
                issue["support_spans"].extend(record["support_spans"][:1])
    result = {
        "records": records,
        "semantic_mappings": mappings,
        "review_requirements": list(issues.values()),
        "entities_by_key": entities,
    }
    from nasa_fire_ai.ingestion.proposal_states import (
        approved_alias_index,
        proposal_state,
        vocabulary_extension_proposals,
    )

    for record in records:
        record["proposal_state"] = proposal_state(record)
    if recover_roles:
        from nasa_fire_ai.ingestion.composition import (
            composition_assertions,
            composition_records,
            explain,
            link_projected_duplicates,
            ontology_extension_proposals,
            scorable_composition_enabled,
        )

        # Composition the document states, staged for review beside the
        # validated records; nothing here enters the graph or the ontology.
        supported = [
            {
                "id": r["entity_id"],
                "label": r["proposal"]["label"],
                "class_id": r["proposal"]["class_id"],
            }
            for r in records
            if r["kind"] == "entities"
            and r["status"] == "SOURCE_SUPPORTED"
            and not r.get("duplicate_of")
            and r.get("entity_id")
        ]
        assertions = composition_assertions(package["evidence"], supported)
        for assertion in assertions:
            assertion["explanation"] = explain(assertion)
        result["composition_proposals"] = assertions
        projected = []
        if scorable_composition_enabled():
            projected = composition_records(
                assertions, entities, supported, evidence, locate, semantic
            )
            for record in projected:
                record["proposal_state"] = proposal_state(record)
            link_projected_duplicates(projected, records)
            records.extend(projected)
        # The vocabulary the document's own supported records need and the
        # approved ontology lacks, staged beside them; never activated here.
        entity_classes = {
            r["entity_id"]: r["proposal"]["class_id"]
            for r in records
            if r["kind"] == "entities" and r.get("entity_id")
        }
        staged_extensions = ontology_extension_proposals(assertions, semantic.relations)
        if projected:
            for extension in staged_extensions:
                extension["supporting_records"] = [r["id"] for r in projected]
        result["ontology_extension_proposals"] = staged_extensions + vocabulary_extension_proposals(
            [r for r in records if r not in projected],
            entity_classes,
            {
                "class": set(semantic.class_metadata),
                "information_class": set(semantic.information_classes),
                "relation": set(semantic.relations),
                "property": set(semantic.properties),
                "aliases": approved_alias_index(semantic),
                # The registry carries no domain or range; the endpoint contract
                # the validator enforces is the known one.
                "relation_endpoints": relation_signatures(semantic, RELATION_ENDPOINTS),
            },
        )
    return result
