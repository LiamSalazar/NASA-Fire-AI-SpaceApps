"""Native scientist-facing boundary with conservative generation and offline fallback."""

import json
import os
from dataclasses import dataclass

from nasa_fire_ai.llm.interfaces import ProviderFailure
from nasa_fire_ai.models import GroundedAnswerDraft
from nasa_fire_ai.query.controlled_reasoning import (
    ControlledReasoningFlags,
    run_ablation,
)
from nasa_fire_ai.query.native import NativeExecutionResult, execute_native
from nasa_fire_ai.query.native_interpreter import resolve_minimal
from nasa_fire_ai.query.v2 import QueryIntentV2
from nasa_fire_ai.services.grounding import GroundingResult, GroundingValidator


def _source_location(passage):
    location = passage.get("structured_location", {})
    if location.get("physical_pdf_page"):
        return (
            f"PDF page {location['physical_pdf_page']}, table {location.get('table')}, "
            f"row {location.get('row_identifier')}"
        )
    if passage.get("source_cells"):
        cell = passage["source_cells"][0]
        return f"{cell['table']}, row {cell['row_ordinal']}"
    if passage.get("page") is not None:
        if passage.get("page_location_verified") is True:
            return f"PDF page {passage['page']}"
        return f"recorded page {passage['page']} (physical PDF page unverified)"
    return passage.get("section") or "location unavailable"


def _comparison_value(value):
    if isinstance(value, dict):
        if value.get("raw_expression"):
            expression = str(value["raw_expression"])
            unit = value.get("reported_unit")
            if unit and str(unit).lower() not in expression.lower():
                expression += " " + str(unit)
            return expression
        reported = value.get("reported_value")
        if reported is not None:
            unit = value.get("reported_unit")
            label = f"{reported} {unit}" if unit else str(reported)
            if value.get("approximate"):
                label = "approximately " + label
            if value.get("tolerance") is not None:
                label += f" ± {value['tolerance']} {unit or ''}".rstrip()
            return label
        lower, upper = value.get("lower"), value.get("upper")
        if lower is not None and upper is not None:
            unit = value.get("reported_unit") or value.get("canonical_unit")
            return f"{lower} to {upper} {unit or ''}".rstrip()
    return str(value)


def _render_comparison(bundle):
    comparison = bundle.comparison
    if comparison is None:
        return []
    evidence_by_run = {
        row["id"]: row.get("evidence_ids", [])
        for row in [*bundle.direct_evidence, *bundle.related_evidence]
    }
    lines = ["", "## Comparison", "", f"Runs: {', '.join(comparison.run_ids)}"]
    for heading, values in (
        ("Shared recorded conditions", comparison.shared_conditions),
        ("Different recorded conditions", comparison.different_conditions),
    ):
        if not values:
            continue
        lines.extend(["", f"### {heading}"])
        for property_id, per_run in values.items():
            if heading == "Shared recorded conditions":
                per_run = {run_id: per_run for run_id in comparison.run_ids}
            labels = []
            citations = []
            for run_id, raw_values in per_run.items():
                if not isinstance(raw_values, list):
                    raw_values = [raw_values]
                rendered = "; ".join(_comparison_value(value) for value in raw_values)
                labels.append(f"{run_id}: {rendered or 'value unavailable'}")
                citations.extend(evidence_by_run.get(run_id, []))
            citation_suffix = f" [{', '.join(dict.fromkeys(citations))}]" if citations else ""
            lines.append(f"- {property_id}: {'; '.join(labels)}{citation_suffix}")
    if comparison.unknown_or_unavailable_conditions:
        lines.extend(["", "### Unknown or unavailable conditions"])
        lines.extend(f"- {name}" for name in comparison.unknown_or_unavailable_conditions)
    lines.extend(
        [
            "",
            "This comparison reports recorded values and unavailable fields; it does not infer statistical significance or causation.",
        ]
    )
    return lines


def render_native(bundle):
    """Readable deterministic presentation; science comes only from supplied data."""
    if os.getenv("SCIENTIFIC_SYNTHESIS_ENABLED", "false").lower() == "true":
        from nasa_fire_ai.services.scientific_synthesis import render_scientific

        return render_scientific(bundle)
    intent = bundle.retrieval_metadata.get("query_intent_v2", {})
    if (
        intent.get("clarification_required")
        and not bundle.discovery_candidates
        and not bundle.retrieval_metadata.get("grouped_search")
    ):
        return "Please clarify these terms: " + ", ".join(intent.get("ambiguities", []))
    lines = [
        "## Answer",
        "No DIRECT structured match was established. Documentary evidence and reviewed statements are listed separately."
        if bundle.no_direct_evidence
        else "Source-backed evidence matching the validated constraints is listed below.",
    ]
    for constraint in intent.get("property_constraints", []):
        value = constraint["value"]
        expression = (
            value.get("raw_expression")
            or f"{constraint['operator']} {value.get('reported_value')} {value.get('reported_unit') or ''}"
        )
        lines.append(f"Requested {constraint['property_id']}: {expression}.")
        if constraint["operator"] == "APPROX" and value.get("tolerance") is None:
            lines.append(
                "Approximation has no specified tolerance; exact numeric applicability remains UNKNOWN."
            )
    if bundle.retrieval_metadata.get("conceptual_query", {}).get("active"):
        lines[1] = (
            "This is a terminology or relationship question. The cited documentation is "
            "provided for interpretation; experiment matches do not establish equivalence. "
            "Exact equivalence remains unestablished without an approved identity relation."
        )
        for relation in bundle.retrieval_metadata["conceptual_query"].get("approved_relations", []):
            lines.append(
                f"Approved relation: {relation['subject']} — {relation['predicate']} — {relation['object']} "
                f"[{', '.join(relation['evidence_ids'])}]"
            )
    if bundle.retrieval_metadata.get("grouped_search"):
        lines.append(
            "Results are grouped by each requested concept; these groups do not establish a single experiment satisfying all concepts simultaneously."
        )
    policy = bundle.retrieval_metadata.get("context_policy", {})
    if policy.get("default_preference"):
        lines.append(
            "Research preference: "
            + ", ".join(policy["default_preference"])
            + ". Experimental conditions are established by the cited sources."
        )
    contexts = bundle.retrieval_metadata.get("scientific_context", {})
    if contexts.get("applied_statements"):
        lines.extend(["", "## Applicable scientific context", ""])
        groups = {}
        for statement in contexts["applied_statements"]:
            key = (
                statement["context_type"],
                statement["value"],
                statement["scope"],
                statement.get("scope_entity"),
            )
            if key not in groups:
                groups[key] = {**statement, "entity_ids": list(statement["entity_ids"])}
            else:
                groups[key]["entity_ids"] = list(
                    dict.fromkeys(groups[key]["entity_ids"] + statement["entity_ids"])
                )
        for statement in groups.values():
            entities = statement["entity_ids"]
            labels = ", ".join(entities[:5]) + (
                f" and {len(entities) - 5} other linked records" if len(entities) > 5 else ""
            )
            lines.append(
                f"- {statement['context_type']}: {statement['value']}; applies to {labels}. The {statement['scope']} statement and verified membership establish applicability [{', '.join(statement['evidence_ids'])}]."
            )
            if statement.get("exceptions"):
                lines.append("  Exceptions: " + ", ".join(statement["exceptions"]))
    if intent.get("ambiguities"):
        lines.append("Unresolved interpretations: " + ", ".join(intent["ambiguities"]))
    for heading, items in (
        ("Direct evidence", bundle.direct_evidence),
        ("Related evidence", bundle.related_evidence),
        (
            "Source-backed specimens",
            [r for r in bundle.semantic_records if r.get("class_id") == "Sample"],
        ),
        ("Reported observations", bundle.experimental_observations),
        ("Experimental interventions", bundle.interventions),
        ("Measurements", bundle.measurements),
        ("Reported conditions and source quantities", bundle.conditions),
        ("NASA conclusions", bundle.nasa_conclusions),
        ("NASA safety implications", bundle.safety_implications),
        ("Requirements", bundle.requirements),
        ("Guidance", bundle.guidance),
        ("Design/test criteria", bundle.design_test_criteria),
        ("NASA-identified open questions", bundle.nasa_identified_open_questions),
    ):
        if not items:
            continue
        if heading == "Related evidence":
            groups = bundle.retrieval_metadata.get("related_presentation", {}).get("groups", [])
            if groups:
                representatives = {g["representative_id"] for g in groups}
                items = [item for item in items if item.get("id") in representatives]
                lines.append(
                    f"Related evidence: {len(groups)} condition groups representing "
                    f"{len(bundle.related_evidence)} candidates. All candidate IDs and citations "
                    "remain available in the evidence bundle."
                )
        lines.extend(["", f"## {heading}", ""])
        for item in items:
            text = item.get(
                "normalized_text", item.get("text", item.get("description", item.get("id", "")))
            )
            if isinstance(item.get("value"), dict) and item.get("property_id"):
                label = item["property_id"].removeprefix("source:").replace("_", " ")
                text = f"{label}: {_comparison_value(item['value'])}"
                qualifiers = item.get("qualifiers", {})
                if qualifiers.get("role") == "SOURCE_DERIVED_BURNING_RATE_CONSTANT":
                    text += (
                        " (fitted burning-rate constant; derived from diameter squared versus time)"
                    )
            elif item.get("class_id") == "Sample":
                text = (
                    f"{item.get('id')}; reported material: "
                    f"{item.get('reported_material_description') or item.get('material') or 'not reported'}"
                )
                if qualifiers.get("source_unit_correction"):
                    text += "; unit corroborated in the NASA report; original CSV unit: " + str(
                        qualifiers.get("original_record", {}).get("reported_unit")
                    )
            eids = item.get("evidence_ids", []) or [
                r["evidence_id"] for r in item.get("evidence_refs", [])
            ]
            group_label = (
                f" (requested group: {item['requested_group']})"
                if item.get("requested_group")
                else ""
            )
            lines.append(f"- {text}{group_label} [{', '.join(eids)}]")
            if item.get("request_limits"):
                lines.append("  Applicability limits: " + "; ".join(item["request_limits"]))
            if item.get("scientific_applicability"):
                for dimension in item["scientific_applicability"]["dimensions"]:
                    lines.append(
                        f"  Statement applicability — {dimension['dimension']}: {dimension['status']}; requested: {dimension['requested']}; established: {dimension['actual']}."
                    )
                lines.append("  " + item["applicability_limit"])
            if "matches" in item:
                lines.append(
                    f"  Matches: {item['matches']}; differs: {item['differs']}; unknown: {item['unknown']}; invalid: {item.get('invalid', [])}."
                )
            explanation = item.get("relationship_explanation")
            if explanation:
                for dimension in explanation["dimensions"]:
                    if isinstance(dimension["requested"], dict) and dimension["requested"].get(
                        "value"
                    ):
                        requested = dimension["requested"]
                        value = requested["value"]
                        wording = {
                            "LT": "below",
                            "LTE": "at most",
                            "GT": "above",
                            "GTE": "at least",
                            "EQ": "equal to",
                            "APPROX": "approximately",
                        }.get(requested["operator"], requested["operator"])
                        label = (
                            dimension["dimension"]
                            .replace("AirflowVelocity", "airflow")
                            .replace("OxygenConcentration", "oxygen concentration")
                        )
                        reported = [
                            f"{r['value']['reported_value']} {r['value']['reported_unit'] or ''}".strip()
                            for r in dimension["actual"]
                            if r["value"].get("reported_value") is not None
                        ]
                        if reported and dimension["status"] == "DIFFER":
                            lines.append(
                                f"  Requested {label}: {wording} {value['reported_value']} {value['reported_unit'] or ''}. Reported {label}: {', '.join(reported)}. This experiment is related but does not satisfy the requested {label} condition."
                            )
                    lines.append(
                        f"  {dimension['dimension']}: {dimension['status']}; "
                        f"requested: {dimension['requested']}; actual: {dimension['actual']}."
                    )
                    for relationship in dimension.get("relationships", []):
                        labels = [relationship["requested_concept"]]
                        labels.extend(step["to_concept"] for step in relationship["path"])
                        lines.append(
                            f"  {relationship['relationship_type']}: {' → '.join(labels)} "
                            f"[taxonomy: {', '.join(relationship['taxonomy_evidence_ids'])}]"
                        )
                lines.append("  " + explanation["cannot_conclude"])
    lines.extend(_render_comparison(bundle))
    scientific_ids = {
        eid
        for item in bundle.direct_evidence + bundle.related_evidence
        for eid in item.get("evidence_ids", [])
    }
    contextual_passages = [
        p for p in bundle.evidence_passages if p["evidence_id"] not in scientific_ids
    ]
    if contextual_passages:
        lines.extend(
            [
                "",
                "## Contextual source quotations",
                "",
                "These documentary passages do not establish the requested experimental constraints.",
            ]
        )
        for passage in contextual_passages:
            source = passage.get("source_metadata") or {}
            lines.append(
                f"- {source.get('title') or passage['document_id']} — {_source_location(passage)}: "
                f"{passage['text']} [{passage['evidence_id']}]"
            )
            context = (passage.get("structured_location") or {}).get("context_before")
            if context and passage.get("context_status") == "ANTECEDENT_REVIEW_REQUIRED":
                lines.append(
                    f"  Exact source context for the incomplete reference: {context} [{passage['evidence_id']}]"
                )
    if bundle.discovery_candidates:
        lines.extend(
            [
                "",
                "## Additional contextual sources (not scientific support)",
                "",
                "These passages were discovered as candidates. They have not established the validated scientific constraints and are not DIRECT or RELATED evidence.",
            ]
        )
        for candidate in bundle.discovery_candidates:
            source = candidate.get("source_metadata") or {}
            location = _source_location(candidate)
            lines.append(
                f"- {source.get('title') or source.get('source_id') or 'NASA source'} — {location}; "
                f"{candidate.get('passage', '')} [{candidate['evidence_id']}]"
            )
    lines.extend(
        [
            "",
            "## Coverage and limitations",
            "",
            "Related evidence is not equivalent evidence. Missing direct evidence is not a NASA research gap.",
        ]
    )
    lines.extend(bundle.coverage_notes)
    lines.extend(["", "## Sources", ""])
    for passage in bundle.evidence_passages:
        source = passage.get("source_metadata") or {}
        location = _source_location(passage)
        lines.append(
            f"- {source.get('title', passage['document_id'])} — {source.get('source_id', passage['document_id'])}, {location}; {source.get('url', '')} [{passage['evidence_id']}]"
        )
    lines.extend(
        [
            "",
            "<details><summary>Technical details</summary>",
            "",
            "```json",
            json.dumps(bundle.model_dump(mode="json"), indent=2),
            "```",
            "</details>",
        ]
    )
    return "\n".join(lines)


def validate_native_draft(draft, bundle):
    """Metadata grounding plus exact-source quotation gate.

    Existing metadata validation cannot independently establish paraphrase fidelity.
    Until expert gold exists, only verbatim source passages may become visible claims;
    generated summaries and limitations are not rendered as scientific content.
    """
    result = GroundingValidator().validate(draft, bundle)
    reviewed_ids = {
        r["evidence_id"]
        for field in (
            "experimental_observations",
            "interventions",
            "nasa_conclusions",
            "safety_implications",
            "requirements",
            "guidance",
            "design_test_criteria",
            "nasa_identified_open_questions",
        )
        for item in getattr(bundle, field)
        for r in item.get("evidence_refs", [])
    }
    reviewed_ids.update(
        eid
        for field in (
            "experimental_observations",
            "interventions",
            "nasa_conclusions",
            "safety_implications",
            "requirements",
            "guidance",
            "design_test_criteria",
            "nasa_identified_open_questions",
        )
        for item in getattr(bundle, field)
        for eid in item.get("evidence_ids", [])
    )
    for claim in draft.claims:
        declared = {
            item["statement_type"]
            for field in (
                "nasa_conclusions",
                "safety_implications",
                "requirements",
                "guidance",
                "design_test_criteria",
                "nasa_identified_open_questions",
            )
            for item in getattr(bundle, field)
            if item.get("statement_type")
            and set(claim.evidence_ids).intersection(
                item.get("evidence_ids", [])
                + [r["evidence_id"] for r in item.get("evidence_refs", [])]
            )
        }
        if len(declared) == 1:
            claim.epistemic_type = next(iter(declared))
        if claim.evidence_ids and not set(claim.evidence_ids).intersection(reviewed_ids):
            # A verbatim documentary excerpt is not automatically an observation,
            # conclusion or recommendation. This is presentation metadata only,
            # never a new KG scientific class or a model-established identity.
            claim.epistemic_type = "source_quotation"
            if claim.relationship_status not in {"DIRECT", "RELATED"}:
                claim.relationship_status = "DOCUMENTARY"
    errors = list(result.errors)
    texts = {p["evidence_id"]: [p["text"]] for p in bundle.evidence_passages}
    for field in (
        "experimental_observations",
        "interventions",
        "nasa_conclusions",
        "safety_implications",
        "requirements",
        "guidance",
        "design_test_criteria",
        "nasa_identified_open_questions",
    ):
        for item in getattr(bundle, field):
            ids = item.get("evidence_ids", []) + [
                r["evidence_id"] for r in item.get("evidence_refs", [])
            ]
            text = item.get("normalized_text", item.get("text", item.get("description", "")))
            for eid in ids:
                texts.setdefault(eid, []).append(text)
    for claim in draft.claims:
        if not claim.evidence_ids or not all(
            any(claim.text.strip() == text.strip() for text in texts.get(eid, []))
            for eid in claim.evidence_ids
        ):
            errors.append(
                f"{claim.claim_id}: source quotation required; paraphrase fidelity unreviewed"
            )
    return GroundingResult(valid=not errors, errors=errors)


@dataclass(frozen=True)
class NativeResponse:
    execution: NativeExecutionResult
    draft: GroundedAnswerDraft | None
    rendered_answer: str
    fallback: bool
    grounding_errors: list[str]
    controlled_trace: dict | None = None


def answer_native(intent, query, store, evidence_registry, draft=None):
    result = execute_native(intent, query, store, evidence_registry)
    rendered = render_native(result.bundle)
    accepted = None
    errors = []
    if draft is not None:
        validation = validate_native_draft(draft, result.bundle)
        errors = validation.errors
        if validation.valid:
            accepted = draft
            quoted = "\n".join(f"{c.text} [{', '.join(c.evidence_ids)}]" for c in draft.claims)
            rendered += "\nSource quotations:\n" + quoted
    return NativeResponse(result, accepted, rendered, accepted is None, errors)


def answer_native_controlled(
    intent,
    query,
    store,
    evidence_registry,
    reasoner=None,
    flags: ControlledReasoningFlags | None = None,
    jev_advisor=None,
):
    """Opt-in discovery presentation; canonical execution remains deterministic.

    Contextual candidates are presented in a separate EvidenceBundle slot and
    are never added to the passage whitelist used by grounded claim validation.
    """
    selected_flags = flags or ControlledReasoningFlags.from_environment()
    if intent.clarification_required and not (
        selected_flags.hierarchical_retrieval or selected_flags.relational_related
    ):
        # A clarifying question should not be accompanied by speculative
        # discovery candidates that could look like an answer.
        selected_flags = ControlledReasoningFlags()
    trace = run_ablation(
        query,
        intent,
        store,
        evidence_registry,
        reasoner=reasoner,
        flags=selected_flags,
        jev_advisor=jev_advisor,
    )
    execution: NativeExecutionResult = trace["_native_execution"]
    if (selected_flags.hierarchical_retrieval or selected_flags.relational_related) and (
        (
            intent.ambiguities
            or len({c.relation for c in intent.entity_constraints}) < len(intent.entity_constraints)
        )
        and all(a.startswith("multiple_values_for_relation:") for a in intent.ambiguities)
        and not intent.unresolved_mentions
        and not intent.comparison
        and not any(
            term in query.lower()
            for term in (
                "same experiment",
                "simultaneously",
                "combined material",
                "mixture",
                "contains both",
                "using both",
            )
        )
    ):
        from dataclasses import replace
        from itertools import product

        by_relation = {}
        for constraint in intent.entity_constraints:
            by_relation.setdefault(constraint.relation, []).append(constraint)
        combinations = list(product(*by_relation.values()))
        if len(combinations) <= 8:
            grouped_bundle = execution.bundle.model_copy(deep=True)
            grouped_bundle.direct_evidence = []
            grouped_bundle.related_evidence = []
            grouped_bundle.semantic_records = []
            groups, passage_map = [], {}
            for constraints in combinations:
                branch = intent.model_copy(
                    update={
                        "entity_constraints": list(constraints),
                        "clarification_required": False,
                        "ambiguities": [],
                    }
                )
                branch_result = execute_native(
                    branch,
                    query,
                    store,
                    evidence_registry,
                    hierarchical=selected_flags.hierarchical_retrieval,
                    relational=selected_flags.relational_related,
                )
                group = ", ".join(c.entity_id for c in constraints)
                groups.append(
                    {
                        "group": group,
                        "intent": branch.model_dump(mode="json"),
                        "no_direct": branch_result.bundle.no_direct_evidence,
                    }
                )
                for field in ("direct_evidence", "related_evidence"):
                    getattr(grouped_bundle, field).extend(
                        {**item, "requested_group": group}
                        for item in getattr(branch_result.bundle, field)
                    )
                passage_map.update(
                    {p["evidence_id"]: p for p in branch_result.bundle.evidence_passages}
                )
                grouped_bundle.semantic_records.extend(branch_result.bundle.semantic_records)
            grouped_bundle.evidence_passages = list(passage_map.values())
            grouped_bundle.no_direct_evidence = not bool(grouped_bundle.direct_evidence)
            grouped_bundle.retrieval_metadata["grouped_search"] = groups
            execution = replace(
                execution, bundle=grouped_bundle, eligible_evidence_ids=sorted(passage_map)
            )
    bundle = execution.bundle.model_copy(deep=True)
    contextual = trace["configurations"]["C"]["contextual_candidates"]
    bundle.discovery_candidates = contextual
    bundle.retrieval_metadata["controlled_reasoning"] = {
        "features": trace["features"],
        "expansion": trace["configurations"]["B"].get("expansion"),
        "rerank_error": trace["configurations"]["C"].get("reranking", {}).get("error"),
        "canonical_effect": "NONE",
    }
    controlled_execution = NativeExecutionResult(
        bundle=bundle,
        plan=execution.plan,
        eligible_evidence_ids=execution.eligible_evidence_ids,
        latency_ms=execution.latency_ms,
    )
    return NativeResponse(
        execution=controlled_execution,
        draft=None,
        rendered_answer=render_native(bundle),
        fallback=True,
        grounding_errors=[],
        controlled_trace=trace,
    )


def answer_native_controlled_text(
    query,
    store,
    evidence_registry,
    language,
    interpreter=None,
    reasoner=None,
    flags: ControlledReasoningFlags | None = None,
    context=None,
    jev_advisor=None,
):
    """Natural-language entry point for opt-in discovery with native authority.

    Interpretation failure becomes a clarification response. Expansion and
    contextual reranking are optional; neither can establish canonical science.
    """
    try:
        if interpreter is None:
            from nasa_fire_ai.query.numeric_mentions import DeterministicMinimalInterpreter

            interpreter = DeterministicMinimalInterpreter(store.registry, language)
        proposal = interpreter.interpret_minimal(query)
        intent = resolve_minimal(proposal, store.registry, language, context, query=query)
    except (ProviderFailure, ValueError, LookupError):
        intent = QueryIntentV2(
            unresolved_mentions=[query],
            ambiguities=["query interpretation unavailable"],
            clarification_required=True,
        )
    return answer_native_controlled(
        intent,
        query,
        store,
        evidence_registry,
        reasoner=reasoner,
        flags=flags,
        jev_advisor=jev_advisor,
    )


def answer_native_text(
    query, store, evidence_registry, language, interpreter=None, synthesizer=None, context=None
):
    """Native language-to-response boundary, with no V1 fallback execution.

    Without a configured interpreter, use the conservative registry interpreter.
    Ambiguous terms still require clarification without an external API key.
    A synthesis error never replaces the deterministic scientific presentation.
    """
    try:
        if interpreter is None:
            from nasa_fire_ai.query.numeric_mentions import DeterministicMinimalInterpreter

            interpreter = DeterministicMinimalInterpreter(store.registry, language)
        proposal = interpreter.interpret_minimal(query)
        intent = resolve_minimal(proposal, store.registry, language, context, query=query)
    except (ProviderFailure, ValueError, LookupError):
        intent = QueryIntentV2(
            unresolved_mentions=[query],
            ambiguities=["query interpretation unavailable"],
            clarification_required=True,
        )
    response = answer_native(intent, query, store, evidence_registry)
    if synthesizer is None or intent.clarification_required:
        return response
    try:
        draft = synthesizer.synthesize(response.execution.bundle)
    except (ProviderFailure, ValueError):
        return response
    validation = validate_native_draft(draft, response.execution.bundle)
    if not validation.valid:
        return NativeResponse(
            response.execution, None, response.rendered_answer, True, validation.errors
        )
    quoted = "\n".join(f"{c.text} [{', '.join(c.evidence_ids)}]" for c in draft.claims)
    return NativeResponse(
        response.execution,
        draft,
        response.rendered_answer + "\nSource quotations:\n" + quoted,
        not bool(draft.claims),
        [],
    )
