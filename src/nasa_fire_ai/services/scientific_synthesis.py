"""Conservative claim selection over the existing EvidenceBundle.

This is an extractive presentation boundary. It does not perform entailment of
arbitrary model paraphrases, publish graph facts, or upgrade documentary support.
All omitted records remain available through the original bundle/registry.
"""

import hashlib
import re

from nasa_fire_ai.models import GroundedClaim

CATEGORIES = (
    ("experimental_observations", "observed_result", "Observations"),
    ("interventions", "tested_intervention", "Interventions"),
    ("nasa_conclusions", "nasa_conclusion", "Reported conclusions"),
    ("nasa_identified_open_questions", "open_question", "Explicit research questions"),
    ("requirements", "requirement", "Requirements"),
    ("guidance", "guidance", "Guidance"),
)


def normalize(text):
    return " ".join(str(text).split())


def evidence_ids(record):
    return list(
        dict.fromkeys(
            record.get("evidence_ids", [])
            + [r["evidence_id"] for r in record.get("evidence_refs", []) if r.get("evidence_id")]
        )
    )


def classification(record, bundle):
    if record.get("comparison_row"):
        subjects = set(record["comparison_row"]["subject_levels"])
        if subjects <= {r["id"] for r in bundle.direct_evidence}:
            return "DIRECT"
        if subjects <= {r["id"] for r in bundle.direct_evidence + bundle.related_evidence}:
            return "RELATED"
        return "DOCUMENTARY"
    subject = record.get("structured_record", {}).get("subject", record.get("id"))
    for status, rows in (("DIRECT", bundle.direct_evidence), ("RELATED", bundle.related_evidence)):
        if any(row.get("id") in {subject, record.get("id")} for row in rows):
            return status
    return "DOCUMENTARY"


def effective_context(record, bundle):
    dimensions = list(record.get("scientific_applicability", {}).get("dimensions", []))
    subject = record.get("structured_record", {}).get("subject", record.get("id"))
    for row in bundle.direct_evidence + bundle.related_evidence:
        if row.get("id") in {subject, record.get("id")} and row.get("research_context", {}).get(
            "values"
        ):
            if not any(d.get("dimension") == "hasGravityCondition" for d in dimensions):
                context = row["research_context"]
                dimensions.append(
                    {
                        "dimension": "hasGravityCondition",
                        "actual": context["values"],
                        "status": context["status"],
                        "requested": None,
                    }
                )
            break
    return dimensions


def context_paths(record):
    paths = []
    for dimension in record.get("scientific_applicability", {}).get("dimensions", []):
        for statement in (dimension.get("context_resolution") or {}).get("statements", []):
            paths.append(
                {
                    "statement_id": statement["statement_id"],
                    "context_type": statement["context_type"],
                    "evidence_ids": statement["evidence_ids"],
                    "membership_paths": statement.get("membership_paths", {}),
                    "provenance_path": statement.get("provenance_path", []),
                }
            )
    return paths


def source_support(record, bundle):
    if record.get("comparison_row"):
        return [
            {
                "evidence_id": eid,
                "reference_kind": "deterministic_comparison",
                "comparison_row": record["comparison_row"],
            }
            for eid in evidence_ids(record)
        ]
    if record.get("structured_record"):
        return [
            {
                "evidence_id": eid,
                "structured_record": record["structured_record"],
                "reference_kind": "supplied_structured_value",
            }
            for eid in evidence_ids(record)
        ]
    sources = {p["evidence_id"]: p.get("text", "") for p in bundle.evidence_passages}
    for dimension in record.get("scientific_applicability", {}).get("dimensions", []):
        for statement in (dimension.get("context_resolution") or {}).get("statements", []):
            for span in statement.get("support_spans", []):
                sources[span["evidence_id"]] = span["text"]
    text = record.get("normalized_text", record.get("text", ""))
    return [
        {"evidence_id": eid, "text": text, "reference_kind": "exact_source_span"}
        for eid in evidence_ids(record)
        if normalize(text) and normalize(text) in normalize(sources.get(eid, ""))
    ]


def condition_statements(bundle):
    from nasa_fire_ai.services.native import _comparison_value

    result = []
    eligible = set(bundle.retrieval_metadata.get("explicit_record_subjects", []))
    eligible |= {row.get("id") for row in bundle.direct_evidence}
    eligible |= {row.get("id") for row in bundle.related_evidence if row.get("matches")}
    for row in bundle.semantic_records:
        if row.get("subject") not in eligible and row.get("id") not in eligible:
            continue
        if (
            not row.get("property_id")
            or not isinstance(row.get("value"), dict)
            or not evidence_ids(row)
        ):
            continue
        # Keep exact typed quantity references. Formatting cannot upgrade a
        # specimen characteristic, intervention parameter or duration to an
        # observed combustion outcome.
        subject = row.get("subject")
        identity = bundle.retrieval_metadata.get("subject_identity_context", {}).get(subject, {})
        title = "; ".join(record["title"] for record in identity.get("investigations", []))
        label = identity.get("reported_identifier")
        display_subject = (
            f"{title}, reported record {label} ({subject})" if title and label else str(subject)
        )
        result.append(
            {
                "id": row["id"],
                "text": f"{display_subject}: {row['property_id']} = {_comparison_value(row['value'])}",
                "evidence_ids": evidence_ids(row),
                "structured_record": {
                    key: row.get(key)
                    for key in ("id", "subject", "property_id", "value", "qualifiers")
                },
            }
        )
    return sorted(
        result,
        key=lambda row: (
            row["structured_record"]["property_id"].startswith("source:"),
            row["structured_record"]["property_id"],
            row["structured_record"]["subject"],
        ),
    )


def comparison_statements(bundle):
    """Reproducible computation, explicitly distinct from NASA observations."""
    from nasa_fire_ai.services.native import _comparison_value

    rows = []
    if not bundle.comparison:
        return rows
    for cell in bundle.comparison.matrix:
        if cell["status"] not in {"MATCH", "DIFFER"}:
            continue
        refs = sorted(
            {eid for values in cell["values"].values() for r in values for eid in r["evidence_ids"]}
        )
        labels = [
            subject + " = " + "; ".join(_comparison_value(r["value"]) for r in values)
            for subject, values in cell["values"].items()
        ]
        rows.append(
            {
                "id": "comparison:" + cell["dimension"] + ":" + cell["context"],
                "text": cell["dimension"]
                + " ("
                + cell["context"]
                + "): "
                + cell["status"]
                + ". "
                + "; ".join(labels),
                "evidence_ids": refs,
                "comparison_row": cell,
                "request_limits": [
                    "Deterministic comparison of reported records; no causal inference or overall experimental equivalence"
                ],
            }
        )
    return rows


def documentary_statements(bundle):
    """Complete bounded paragraphs, never arbitrary partial sentences."""
    terms = {
        word
        for word in re.findall(
            r"[a-z]{4,}", bundle.retrieval_metadata.get("scientific_question", "").lower()
        )
        if word
        not in {"what", "which", "about", "nasa", "find", "does", "were", "under", "available"}
    }
    rows = []
    for passage in bundle.evidence_passages:
        for index, paragraph in enumerate(re.split(r"\n[ \t]*\n", passage.get("text", ""))):
            text = paragraph.strip()
            if not 50 <= len(text) <= 700 or not text.endswith((".", "?", "!")):
                continue
            score = len(terms & set(re.findall(r"[a-z]{4,}", text.lower())))
            if score:
                rows.append(
                    {
                        "id": f"{passage['evidence_id']}:paragraph-{index}",
                        "text": text,
                        "evidence_ids": [passage["evidence_id"]],
                        "request_limits": [
                            "Documentary quotation; experimental identity and requested conditions remain unverified"
                        ],
                        "paragraph_relevance": score,
                    }
                )
    return sorted(rows, key=lambda row: (-row["paragraph_relevance"], row["id"]))


def quantity_kind(row):
    qualifiers = row["structured_record"].get("qualifiers") or {}
    return (
        "experimental_condition"
        if qualifiers.get("origin") == "canonical_condition_projection"
        else "reported_quantity"
    )


def validate_selected_claim(claim, bundle):
    """Check full statement identity, scope, type and references, not citations alone."""
    errors = []
    candidates = [
        (
            row,
            row.get("epistemic", epistemic)
            if row.get("epistemic")
            in {"tentative_interpretation", "hypothesis", "derived_quantity"}
            else epistemic,
        )
        for field, epistemic, _ in CATEGORIES
        for row in getattr(bundle, field)
    ]
    candidates += [(row, quantity_kind(row)) for row in condition_statements(bundle)]
    candidates += [(row, "comparison_result") for row in comparison_statements(bundle)]
    if claim.epistemic_type == "source_quotation":
        candidates += [(row, "source_quotation") for row in documentary_statements(bundle)]
        candidates += [
            (
                {
                    "id": p["evidence_id"],
                    "text": p.get("text", ""),
                    "evidence_ids": [p["evidence_id"]],
                },
                "source_quotation",
            )
            for p in bundle.evidence_passages
        ]
    matches = [
        (row, kind)
        for row, kind in candidates
        if normalize(row.get("normalized_text", row.get("text", ""))) == normalize(claim.text)
        and set(claim.evidence_ids) == set(evidence_ids(row))
        and kind == claim.epistemic_type
    ]
    if not matches:
        return ["Claim is not an exact, complete supplied statement of the stated epistemic type"]
    matching = [
        row
        for row, _ in matches
        if claim.scientific_entities == ([row["id"]] if row.get("id") else [])
    ]
    if not matching:
        errors.append("Scientific statement identity changed")
    else:
        row = matching[0]
        if claim.relationship_status != classification(row, bundle):
            errors.append("Scientific applicability classification changed")
        if claim.scope_limits != row.get("request_limits", []):
            errors.append("Required applicability limitation omitted")
        if claim.experimental_context != effective_context(row, bundle):
            errors.append("Experimental conditions changed")
        if claim.graph_paths != context_paths(row):
            errors.append("Context provenance path changed")
    expected = source_support(matching[0], bundle) if matching else []
    if not expected or claim.support_spans != expected:
        errors.append("Statement support references changed")
    return errors


def select_claims(bundle, *, detail_level="standard", complete=False):
    """Deduplicate statements only, never whole experiments or publications."""
    budget = (
        float("inf") if complete else {"concise": 4, "standard": 8, "technical": 24}[detail_level]
    )
    selected, rejected, omitted = [], [], []
    seen = set()
    inventories = [
        (comparison_statements(bundle), "comparison_result", "Deterministic comparison"),
        *[(getattr(bundle, field), epistemic, heading) for field, epistemic, heading in CATEGORIES],
    ]
    requested = set(
        bundle.retrieval_metadata.get("query_intent_v2", {}).get("requested_information", [])
    )
    if not any(rows for rows, _, _ in inventories) and not requested.intersection(
        {
            "ReportedObservation",
            "NASAConclusion",
            "Intervention",
            "OpenQuestion",
            "Requirement",
            "Guidance",
        }
    ):
        for kind in ("experimental_condition", "reported_quantity"):
            inventories.append(
                (
                    [row for row in condition_statements(bundle) if quantity_kind(row) == kind],
                    kind,
                    "Recorded source quantities (not observations)",
                )
            )
    if not any(rows for rows, _, _ in inventories):
        inventories.append(
            (
                documentary_statements(bundle)[:2],
                "source_quotation",
                "Documentary context (not verified experimental support)",
            )
        )
    for inventory, epistemic, heading in inventories:
        for record in inventory:
            record_epistemic = record.get("epistemic")
            claim_epistemic = (
                record_epistemic
                if record_epistemic
                in {"tentative_interpretation", "hypothesis", "derived_quantity"}
                else epistemic
            )
            claim_heading = (
                "Reported " + record_epistemic.replace("_", " ")
                if claim_epistemic != epistemic
                else heading
            )
            text = record.get("normalized_text", record.get("text", ""))
            ids = evidence_ids(record)
            if not text or not ids:
                rejected.append(
                    {"record": record.get("id"), "reason": "Missing source text or evidence"}
                )
                continue
            # An explicit technical modifier must occur in the selected statement,
            # rather than being satisfied by a different topic in the same corpus.
            from nasa_fire_ai.query.conceptual import technical_topic_supported
            from nasa_fire_ai.services.investigation import scoped_topic_text, topic_applicable

            if not technical_topic_supported(
                bundle.retrieval_metadata.get(
                    "scientific_focus_question",
                    bundle.retrieval_metadata.get("scientific_question", ""),
                ),
                text,
            ):
                rejected.append(
                    {
                        "record": record.get("id"),
                        "reason": "Requested technical topic is absent from the proposed statement; no topic applicability inferred",
                    }
                )
                continue
            # Scope stays in identity: identical wording in different experiments
            if not topic_applicable(
                bundle.retrieval_metadata.get(
                    "scientific_focus_question",
                    bundle.retrieval_metadata.get("scientific_question", ""),
                ),
                scoped_topic_text(record),
            ):
                rejected.append(
                    {
                        "record": record.get("id"),
                        "reason": "Requested phenomenon or validated material context absent",
                    }
                )
                continue
            # Scope stays in identity: identical wording in different experiments
            # is NOT silently collapsed into a universal scientific observation.
            key = (normalize(text), tuple(sorted(ids)), record.get("id"), epistemic)
            if key in seen:
                omitted.append({"record": record.get("id"), "reason": "Duplicate statement path"})
                continue
            seen.add(key)
            if len(selected) >= budget:
                omitted.append(
                    {
                        "record": record.get("id"),
                        "reason": "Presentation budget; retained in bundle",
                    }
                )
                continue
            claim = GroundedClaim(
                claim_id="claim-" + hashlib.sha256(repr(key).encode()).hexdigest()[:16],
                text=text,
                epistemic_type=claim_epistemic,
                authority=record.get(
                    "authority",
                    "RESEARCHER_CURATED"
                    if record.get("structured_record", {})
                    .get("qualifiers", {})
                    .get("curation_authority")
                    else "NASA_BACKED",
                ),
                relationship_status=classification(record, bundle),
                evidence_ids=ids,
                scientific_entities=[record["id"]] if record.get("id") else [],
                experimental_context=effective_context(record, bundle),
                support_spans=source_support(record, bundle),
                scope_limits=record.get("request_limits", []),
                graph_paths=context_paths(record),
            )
            errors = validate_selected_claim(claim, bundle)
            if errors:
                rejected.append({"record": record.get("id"), "reason": errors})
            else:
                claim.validation_status = "VALIDATED_SUPPLIED_STATEMENT"
                selected.append((claim_heading, claim))
    ordering = bundle.retrieval_metadata.get("nemotron_scientific_selection", {}).get(
        "accepted_claim_ids", []
    )
    if ordering:
        by_id = {claim.claim_id: (heading, claim) for heading, claim in selected}
        omitted += [
            {
                "record": claim.scientific_entities,
                "reason": "Experimental model selection; retained in complete bundle",
            }
            for _, claim in selected
            if claim.claim_id not in ordering
        ]
        selected = [by_id[cid] for cid in ordering if cid in by_id]
    return selected, {
        "selected_claims": [c.model_dump(mode="json") for _, c in selected],
        "rejected": rejected,
        "omitted": omitted,
        "independent_scientific_review": None,
        "validation_boundary": "Exact supplied statement and metadata; source extraction contracts remain independently reviewable",
    }


def render_scientific(bundle, *, detail_level="standard", registry=None, store=None):
    from nasa_fire_ai.services.intent_answers import render_intent_answer

    specific = render_intent_answer(bundle, detail_level, registry=registry)
    if specific is not None:
        return specific
    selected, receipt = select_claims(bundle, detail_level=detail_level)
    if registry is not None:
        from nasa_fire_ai.services.claim_verification import verify_claim

        verification = [verify_claim(claim, bundle, registry, store=store) for _, claim in selected]
        eligible = {
            row["claim_id"]
            for row in verification
            if row["status"] in {"SUPPORTED", "SUPPORTED_WITH_LIMITATIONS"}
        }
        receipt["rejected"] += [
            {"claim_id": row["claim_id"], "reason": row.get("errors", []), "gate": "FINAL_EMISSION"}
            for row in verification
            if row["claim_id"] not in eligible
        ]
        selected = [(heading, claim) for heading, claim in selected if claim.claim_id in eligible]
        receipt["selected_claims"] = [claim.model_dump(mode="json") for _, claim in selected]
        bundle.retrieval_metadata["claim_verification"] = verification
        bundle.retrieval_metadata["final_emission_gate"] = {
            "enforced": True,
            "eligible_claim_ids": sorted(eligible),
            "blocked": len(verification) - len(eligible),
        }
    bundle.retrieval_metadata["scientific_synthesis"] = receipt
    lines = []
    intent = bundle.retrieval_metadata.get("query_intent_v2", {})
    if intent.get("clarification_required") and not selected:
        lines.append("Please clarify: " + ", ".join(intent.get("ambiguities", [])))
    elif not selected and "ObservationConclusionLink" in bundle.retrieval_metadata.get(
        "investigation", {}
    ).get("requirements", []):
        lines.append(
            "Verified experimental support for the requested conclusions and conditions remains incomplete."
        )
    elif not selected:
        lines.append(
            "The available records identify experiments, but do not establish a selected scientific observation answering this question."
        )
    displayed = set()
    quantities = [
        claim
        for _, claim in selected
        if claim.epistemic_type in {"experimental_condition", "reported_quantity"}
    ]
    if quantities:
        from nasa_fire_ai.services.native import _comparison_value

        rows, subjects = {}, []
        for claim in quantities:
            record = claim.support_spans[0]["structured_record"]
            subject = record["subject"]
            if subject not in subjects:
                subjects.append(subject)
            rows.setdefault(record["property_id"], {})[subject] = (
                f"{_comparison_value(record['value'])} ({claim.relationship_status}) [{', '.join(claim.evidence_ids)}]"
            )
        lines.extend(
            [
                "Recorded source quantities (not observations):",
                "| Source field | " + " | ".join(subjects) + " |",
                "| --- | " + " | ".join("---" for _ in subjects) + " |",
            ]
        )
        for property_id, values in rows.items():
            lines.append(
                "| "
                + property_id
                + " | "
                + " | ".join(values.get(subject, "not selected") for subject in subjects)
                + " |"
            )
        for subject in subjects:
            row = next(
                (
                    row
                    for row in bundle.direct_evidence + bundle.related_evidence
                    if row.get("id") == subject
                ),
                {},
            )
            context = row.get("research_context", {})
            if context.get("values"):
                statements = [
                    statement
                    for statement in bundle.retrieval_metadata.get("scientific_context", {}).get(
                        "applied_statements", []
                    )
                    if subject in statement.get("entity_ids", [])
                    and statement.get("context_type") == "gravity"
                    and statement.get("value") in context["values"]
                ]
                refs = sorted(
                    {eid for statement in statements for eid in statement["evidence_ids"]}
                ) or evidence_ids(row)
                lines.append(
                    f"{subject}: gravity {', '.join(context['values'])}; {context.get('status', 'UNKNOWN')} [{', '.join(refs)}]."
                )
        lines.append(
            "Values and field labels reproduce selected source records; documentary geometry and unclassified quantity roles are not silently reconciled."
        )
    for heading, claim in selected:
        if claim.epistemic_type in {"experimental_condition", "reported_quantity"}:
            continue
        key = (normalize(claim.text), tuple(sorted(claim.evidence_ids)), claim.epistemic_type)
        if key in displayed:
            lines.append(
                f"The same quoted statement also belongs to {', '.join(claim.scientific_entities)} ({claim.relationship_status}); its applicable context follows."
            )
        else:
            lines.append(
                f"{heading} ({claim.relationship_status}): {normalize(claim.text)} [{', '.join(claim.evidence_ids)}]"
            )
            displayed.add(key)
        for dimension in claim.experimental_context:
            actual = dimension.get("actual", [])
            labels = []
            for value in actual if isinstance(actual, list) else [actual]:
                if isinstance(value, dict):
                    quantity = value.get("value", value)
                    labels.append(
                        str(
                            quantity.get("raw_expression")
                            or f"{quantity.get('reported_value', 'unknown')} {quantity.get('reported_unit') or ''}"
                        ).strip()
                    )
                else:
                    labels.append(str(value))
            lines.append(
                f"Applicable {dimension.get('dimension')}: {', '.join(labels) or 'unknown'} ({dimension.get('status')})."
            )
        if claim.scope_limits:
            lines.append("Limits: " + "; ".join(claim.scope_limits))
    # Do not restate broad campaign context over an overriding local exception.
    # Effective per-statement dimensions above are the authoritative display.
    direct_ids = {r.get("id") for r in bundle.direct_evidence}
    runs = [r for r in bundle.direct_evidence if r.get("class_id") == "ExperimentalRun"]
    if not selected and runs:
        lines.append(
            f"{len(runs)} applicable experimental records were retrieved; recorded conditions are available in the evidence details."
        )
    related = [r for r in bundle.related_evidence if r.get("id") not in direct_ids]
    if related:
        lines.append(
            f"Related evidence: {len(related)} additional records differ in requested conditions or address a related question; they are not equivalent experiments."
        )
    conceptual = bundle.retrieval_metadata.get("conceptual_query", {})
    if conceptual.get("active"):
        lines.append(
            "Terminology: experiment matches do not establish material equivalence. Only approved ontology identity relationships can establish an exact equivalence."
        )
        for relation in conceptual.get("approved_relations", []):
            lines.append(
                f"{relation['subject']} — {relation['predicate']} — {relation['object']} [{', '.join(relation['evidence_ids'])}]"
            )
    if bundle.no_direct_evidence:
        lines.append(
            "No DIRECT match was established. Missing evidence in this corpus is not an identified NASA knowledge gap."
        )
    if bundle.retrieval_metadata.get("context_policy", {}).get("default_preference"):
        lines.append(
            "Microgravity is a presentation preference, not an experimental fact or an added mandatory condition."
        )
    investigation = bundle.retrieval_metadata.get("investigation", {})
    if investigation.get("missing_information"):
        lines.append(
            "Unresolved requested information: "
            + ", ".join(investigation["missing_information"])
            + ". Additional retrieval did not establish complete support."
        )
    seen_staged = set()
    for candidate in bundle.retrieval_metadata.get("staged_scientific_knowledge", []):
        proposal = candidate["proposal"]
        text = normalize(proposal["original_wording"])
        if registry is not None:
            source = registry.resolve(candidate["evidence_id"])
            if not source or text not in normalize(source.get("text", "")):
                continue
        if text in seen_staged:
            continue
        if len(seen_staged) >= 2:
            break
        seen_staged.add(text)
        lines.append(
            f"Pending scientific review ({candidate['candidate_type']}, scope {proposal.get('scope')}): “{text}” [{candidate['evidence_id']}]. Experimental attribution and publication remain unapproved."
        )
    lines.append(
        "Full records, source passages and applicability traces remain available in the EvidenceBundle and Evidence Registry."
    )
    return "\n\n".join(lines)
