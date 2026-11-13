"""Bounded evidence investigation over the existing V2 executor and registry.

Operational state is a receipt, never a scientific truth store. Retrieval cannot
promote documentary text or staged proposals to experimentally applicable facts.
"""

import hashlib
import re
import sqlite3
from dataclasses import asdict, dataclass
from time import perf_counter

from nasa_fire_ai.query.conceptual import is_conceptual_question, technical_topic_supported
from nasa_fire_ai.query.native import execute_native
from nasa_fire_ai.services.scientific_synthesis import classification, source_support

FIELDS = {
    "ReportedObservation": "experimental_observations",
    "Intervention": "interventions",
    "NASAConclusion": "nasa_conclusions",
    "OpenQuestion": "nasa_identified_open_questions",
    "Requirement": "requirements",
    "Guidance": "guidance",
    "SafetyImplication": "safety_implications",
    "Measurement": "measurements",
    "ExperimentalCondition": "conditions",
    "Publication": "publications",
}
STOP = {
    "what",
    "which",
    "does",
    "nasa",
    "about",
    "under",
    "between",
    "when",
    "were",
    "made",
    "their",
    "with",
    "that",
    "from",
    "have",
    "been",
    "into",
    "mean",
    "publications",
    "discuss",
    "technique",
    "experiments",
    "observations",
    "conclusions",
    "conditions",
    "support",
}


def question_kind(query, intent):
    if is_conceptual_question(query):
        return "conceptual"
    if re.search(
        r"\b(?:publications?|bibliograph\w*|papers?|documents?)\b|\b(?:which|find|list|show|discover)\b.{0,25}\b(?:reports|sources)\b",
        query,
        re.IGNORECASE,
    ) and not re.search(r"\b(?:observed|happened|concluded|measurements?)\b", query, re.IGNORECASE):
        return "bibliographic"
    if intent.operation == "COMPARE":
        return "comparison"
    return "scientific"


def information_requirements(query, intent):
    kind = question_kind(query, intent)
    if kind == "conceptual":
        return ["ConceptualRelationship"]
    if kind == "bibliographic":
        return ["Publication"]
    required = [x for x in intent.requested_information if x in FIELDS]
    if re.search(r"\b(?:conditions?|configuration|configured|environment)\b", query, re.IGNORECASE):
        required.append("ExperimentalCondition")
    if re.search(
        r"\b(?:unresolved|open|future research|remaining questions)\b", query, re.IGNORECASE
    ):
        required.append("OpenQuestion")
    if (
        re.search(r"\b(?:support|supporting|basis for)\b", query, re.IGNORECASE)
        and "NASAConclusion" in required
    ):
        required += ["ReportedObservation", "ObservationConclusionLink"]
    return list(dict.fromkeys(required)) or ["ExperimentalRun"]


def evaluate_sufficiency(query, intent, bundle, registry):
    """Conservative question-specific coverage; lexical matches prove no entailment."""
    items = []
    for requirement in information_requirements(query, intent):
        state, ids, reason = "MISSING", [], "No applicable source-backed item of the requested type"
        if requirement == "ConceptualRelationship":
            support = bundle.retrieval_metadata.get("conceptual_query", {})
            relations = support.get("approved_relations", [])
            ids = [eid for row in relations for eid in row.get("evidence_ids", [])]
            approved_ids = list(ids)
            if not ids:
                terms = set(topic_terms(query))
                ids = [
                    passage["evidence_id"]
                    for passage in bundle.evidence_passages
                    if terms.intersection(
                        set(re.findall(r"[\w-]+", passage.get("text", "").lower()))
                    )
                ]
            state = (
                "SUPPORTED"
                if approved_ids and all(registry.resolve(eid) for eid in approved_ids)
                else "PARTIALLY_SUPPORTED"
                if bundle.evidence_passages
                else "MISSING"
            )
            reason = (
                "Approved terminology relations"
                if state == "SUPPORTED"
                else "Documentary terminology does not establish total material equivalence"
            )
        elif requirement == "Publication":
            ids = [
                p["evidence_id"]
                for p in bundle.evidence_passages
                if registry.source_metadata(p["evidence_id"])
                and publication_topic_supported(
                    query,
                    p.get("text", "")
                    + " "
                    + (registry.source_metadata(p["evidence_id"]) or {}).get("title", ""),
                )
            ]
            state = "SUPPORTED" if ids else "MISSING"
            reason = "Publication identity and matching source passages; independent topical relevance remains reviewable"
        elif requirement == "ObservationConclusionLink":
            paths = bundle.retrieval_metadata.get("verified_observation_conclusion_links", [])
            ids = [eid for row in paths for eid in row.get("evidence_ids", [])]
            state = "SUPPORTED" if ids else "MISSING"
            reason = "Requires explicit reviewed attribution; co-occurrence in a publication is insufficient"
        elif requirement == "ExperimentalRun":
            rows = bundle.direct_evidence
            ids = [
                eid for row in rows for eid in row.get("evidence_ids", []) if registry.resolve(eid)
            ]
            state = (
                "PARTIALLY_SUPPORTED"
                if ids
                else "RELATED_ONLY"
                if bundle.related_evidence
                else "MISSING"
            )
            reason = "Experiment identity alone does not establish requested scientific information"
        else:
            rows = getattr(bundle, FIELDS[requirement])
            if requirement == "ExperimentalCondition":
                from nasa_fire_ai.services.scientific_synthesis import (
                    condition_statements,
                    quantity_kind,
                )

                rows = rows + [
                    row
                    for row in condition_statements(bundle)
                    if quantity_kind(row) == "experimental_condition"
                ]
            direct, partial, related, conflicted = [], [], [], []
            for row in rows:
                refs = row.get("evidence_ids", []) or [
                    r["evidence_id"] for r in row.get("evidence_refs", [])
                ]
                if not refs or not all(registry.resolve(eid) for eid in refs):
                    continue
                # Structured quantities require original records; prose requires exact spans.
                if not source_support(row, bundle) and not row.get("value"):
                    continue
                dimensions = row.get("scientific_applicability", {}).get("dimensions", [])
                if any(d.get("status") == "CONFLICTED" for d in dimensions):
                    conflicted.extend(refs)
                    continue
                if not technical_topic_supported(
                    query, row.get("normalized_text", row.get("text", row.get("property_id", "")))
                ):
                    continue
                if not topic_applicable(query, scoped_topic_text(row)):
                    related.extend(refs)
                    continue
                if requirement == "ReportedObservation" and re.search(
                    r"\b(?:restor\w*|interrupt\w*)\b", query, re.IGNORECASE
                ):
                    statement = row.get("normalized_text", row.get("text", ""))
                    if not re.search(
                        r"\b(?:restor\w*|interrupt\w*|turned.{0,30}(?:on|off)|flow.{0,30}(?:back|stop\w*))\b",
                        statement,
                        re.IGNORECASE,
                    ):
                        related.extend(refs)
                        continue
                status = classification(row, bundle)
                if status == "DIRECT" and not row.get("request_limits"):
                    direct.extend(refs)
                elif status == "RELATED":
                    related.extend(refs)
                else:
                    partial.extend(refs)
            ids = conflicted or direct or partial or related
            state = (
                "CONFLICTED"
                if conflicted
                else "SUPPORTED"
                if direct
                else "PARTIALLY_SUPPORTED"
                if partial
                else "RELATED_ONLY"
                if related
                else "MISSING"
            )
        if ids and requirement in FIELDS and requirement != "Publication":
            reason = f"Exact source-backed requested items; scientific applicability {state}"
        items.append(
            {
                "requirement": requirement,
                "requested_information": query,
                "entities": [c.entity_id for c in intent.entity_constraints],
                "explicit_conditions": [
                    c.model_dump(mode="json")
                    for c in intent.entity_constraints + intent.property_constraints
                ],
                "epistemic_type": requirement,
                "scope": "Original V2 constraints and per-record experimental applicability",
                "comparison_groups": intent.comparison.model_dump(mode="json")
                if intent.comparison
                else None,
                "acceptable_evidence_types": [requirement],
                "status": state,
                "evidence_ids": sorted(set(ids)),
                "missing_evidence": [] if state == "SUPPORTED" else [requirement],
                "reason": reason,
            }
        )
    return {
        "items": items,
        "sufficient": all(x["status"] in {"SUPPORTED", "NOT_APPLICABLE"} for x in items),
        "independent_scientific_precision": "NOT_MEASURABLE",
    }


def topic_applicable(query, text):
    """Necessary topic wording, never a sufficient scientific support contract."""
    families = (
        (r"depressuri\w*", r"depressuri\w*"),
        (r"reignit\w*", r"reignit\w*"),
        (r"extinguish\w*", r"extinguish\w*|extinct\w*"),
        (r"airflow|air flow", r"airflow|air flow|flow"),
        (r"pmma|polymethyl", r"pmma|polymethyl"),
        (r"flame spread", r"flame spread|spread rate"),
    )
    return all(
        not re.search(wanted, query, re.IGNORECASE) or re.search(required, text, re.IGNORECASE)
        for wanted, required in families
    )


def publication_topic_supported(query, text):
    if not topic_applicable(query, text):
        return False
    generic = {
        "investigate",
        "investigates",
        "investigating",
        "report",
        "reports",
        "research",
        "papers",
        "documents",
        "sources",
        "spacecraft",
        "fire",
        "suppression",
        "find",
        "list",
        "show",
        "identify",
        "identified",
    }
    topics = set(topic_terms(query)) - generic
    return bool(topics) and all(
        re.search(rf"(?<!\w){re.escape(term)}(?:s|ed|ing)?(?!\w)", text, re.IGNORECASE)
        for term in topics
    )


@dataclass(frozen=True)
class ResearchBudget:
    max_rounds: int = 3
    max_actions: int = 8
    max_candidates: int = 8
    timeout_seconds: float = 30
    max_model_calls: int = 2
    max_model_tokens: int = 8000

    def __post_init__(self):
        if not (
            1 <= self.max_rounds <= 10
            and 1 <= self.max_actions <= 32
            and 1 <= self.max_candidates <= 64
            and 0 < self.timeout_seconds <= 300
            and 0 <= self.max_model_calls <= 2
            and 0 <= self.max_model_tokens <= 16000
        ):
            raise ValueError("Research budget outside bounded operational limits")


def topic_terms(query):
    return list(
        dict.fromkeys(
            w for w in re.findall(r"[\w-]+", query.lower()) if len(w) > 3 and w not in STOP
        )
    )


def scoped_topic_text(row):
    text = row.get("normalized_text", row.get("text", ""))
    for dimension in row.get("scientific_applicability", {}).get("dimensions", []):
        if dimension.get("dimension") == "hasMaterial" and dimension.get("status") in {
            "MATCH",
            "EXPLICIT_LOCAL",
            "VERIFIED_APPLICABLE_CONTEXT",
        }:
            text += " " + " ".join(str(x) for x in dimension.get("actual", []))
    return text


def merge_bundle(target, extra):
    for field in [
        *FIELDS.values(),
        "direct_evidence",
        "related_evidence",
        "semantic_records",
        "evidence_passages",
    ]:
        rows = getattr(target, field)
        known = {row.get("id", row.get("evidence_id", repr(row))) for row in rows}
        for row in getattr(extra, field):
            key = row.get("id", row.get("evidence_id", repr(row)))
            if key not in known:
                rows.append(row)
                known.add(key)
    target.no_direct_evidence = not target.direct_evidence


def next_actions(query, intent, coverage, store, bundle):
    """Rebuild alternatives from current discoveries and unresolved requirements."""
    actions = []
    terms = topic_terms(query)
    known_evidence = {p["evidence_id"] for p in bundle.evidence_passages}
    discoveries = sorted(
        {
            row.get("subject")
            for row in bundle.semantic_records
            if row.get("subject") in store.registry.entities
        }
    )
    discoveries += [
        row.get("id")
        for row in bundle.direct_evidence + bundle.related_evidence
        if row.get("id") in store.registry.entities and row.get("id") not in discoveries
    ]
    for item in coverage["items"]:
        if item["status"] in {"SUPPORTED", "NOT_APPLICABLE"}:
            continue
        requirement = item["requirement"]
        if requirement in FIELDS and requirement != "Publication":
            aliases = store.registry.class_metadata.get(requirement, {}).get("query_terms", [])
            term = aliases[0] if aliases else re.sub(r"([a-z])([A-Z])", r"\1 \2", requirement)
            actions.append(
                {
                    "operation": "native_search",
                    "query": " ".join(terms + [term]),
                    "requirement": requirement,
                    "objective": "Recover missing typed evidence with original constraints",
                    "expected_evidence_type": requirement,
                }
            )
        for entity in discoveries[:4]:
            # Existing edges determine paths; an LLM never supplies new graph facts.
            from nasa_fire_ai.query.native import NS, node

            for relation in sorted(store.registry.relations):
                records = [
                    record
                    for record in store.graph.subjects(NS.subject, node(entity))
                    if store.graph.value(record, NS.relation) == node(relation)
                ]
                if any(
                    {str(eid) for eid in store.graph.objects(record, NS.evidenceRef)}
                    - known_evidence
                    for record in records
                ):
                    actions.append(
                        {
                            "operation": "ontology_path",
                            "query": query,
                            "requirement": requirement,
                            "objective": "Follow a newly discovered entity's existing provenance-bearing relation",
                            "start": entity,
                            "steps": [{"relation": relation, "direction": "FORWARD"}],
                            "expected_evidence_type": requirement,
                        }
                    )
        for constraint in intent.entity_constraints[:1]:
            actions.append(
                {
                    "operation": "ontology_path",
                    "query": query,
                    "requirement": requirement,
                    "objective": "Recover approved relation provenance",
                    "start": constraint.entity_id,
                    "steps": [{"relation": constraint.relation, "direction": "REVERSE"}],
                    "expected_evidence_type": "ASSOCIATION",
                }
            )
        for entity in discoveries[:2]:
            actions.append(
                {
                    "operation": "document_search",
                    "query": " ".join([entity, *terms]),
                    "requirement": requirement,
                    "objective": "Resolve discovered experimental identity in source text",
                    "expected_evidence_type": "Publication",
                }
            )
        actions.append(
            {
                "operation": "document_search",
                "query": " ".join(terms),
                "requirement": requirement,
                "objective": "Recover original passages",
                "expected_evidence_type": "Publication",
            }
        )
    return actions


def action_identity(action):
    import json

    return (
        action.get("operation"),
        str(action.get("query", "")).casefold().strip(),
        action.get("start"),
        json.dumps(action.get("steps", []), sort_keys=True),
    )


def investigate(query, execution, store, registry, *, budget=None, planner=None):
    budget = budget or ResearchBudget()
    began = perf_counter()
    intent, bundle = execution.plan.intent, execution.bundle
    state = {
        "question": query,
        "intent": intent.model_dump(mode="json"),
        "requirements": information_requirements(query, intent),
        "explicit_constraints": [
            c.model_dump(mode="json")
            for c in intent.entity_constraints + intent.property_constraints
        ],
        "domain_preferences": bundle.retrieval_metadata.get("context_policy", {}).get(
            "default_preference", []
        ),
        "budget": asdict(budget),
        "completed_actions": [],
        "action_attempts": 0,
        "rejected_actions": [],
        "model_calls": [],
        "replanning_decisions": [],
        "rounds": 1,
    }
    seen = {action_identity({"operation": "native_search", "query": query})}
    coverage = evaluate_sufficiency(query, intent, bundle, registry)
    state["initial_coverage"] = coverage
    while True:
        if (
            state["rounds"] >= budget.max_rounds
            or state["action_attempts"] >= budget.max_actions
            or perf_counter() - began >= budget.timeout_seconds
            or coverage["sufficient"]
        ):
            break
        actions = next_actions(query, intent, coverage, store, bundle)
        tokens_used = sum(
            (r.get("usage") or {}).get("total_tokens", 0) for r in state["model_calls"]
        )
        if (
            planner
            and actions
            and len(state["model_calls"]) < budget.max_model_calls
            and budget.max_model_tokens - tokens_used > 0
        ):
            receipt = planner.plan(
                query,
                intent,
                coverage,
                store.registry,
                max_tokens=budget.max_model_tokens - tokens_used,
                timeout=min(10, max(0.1, budget.timeout_seconds - (perf_counter() - began))),
                research_state={
                    "completed_actions": [
                        {
                            "operation": a["operation"],
                            "query": a["query"],
                            "requirement": a["requirement"],
                            "new_evidence_ids": a["new_evidence_ids"],
                        }
                        for a in state["completed_actions"]
                    ],
                    "discovered_entities": sorted(
                        {
                            r.get("id")
                            for r in bundle.direct_evidence + bundle.related_evidence
                            if r.get("id") in store.registry.entities
                        }
                    )[:12],
                    "evidence": [
                        {"evidence_id": p["evidence_id"], "text": p.get("text", "")[:160]}
                        for p in bundle.evidence_passages[:3]
                    ],
                    "remaining_budget": asdict(budget),
                },
            )
            state["model_calls"].append(receipt)
            actions = receipt.get("actions", []) + actions
        available = []
        for proposal in actions:
            if action_identity(proposal) in seen:
                state["rejected_actions"].append({**proposal, "reason": "Duplicate operation"})
            else:
                available.append(proposal)
        if not available:
            state["stop_reason"] = "No unexecuted justified alternatives"
            break
        action = available[0]
        state["action_attempts"] += 1
        state["replanning_decisions"].append(
            {
                "after_action_count": len(state["completed_actions"]),
                "evidence_ids": sorted({p["evidence_id"] for p in bundle.evidence_passages}),
                "unresolved": [
                    x["requirement"] for x in coverage["items"] if x["status"] != "SUPPORTED"
                ],
                "selected_action": action,
            }
        )
        if any(
            item["requirement"] == action.get("requirement") and item["status"] == "SUPPORTED"
            for item in coverage["items"]
        ):
            state["rejected_actions"].append(
                {**action, "reason": "Requirement already supported by completed retrieval"}
            )
            continue
        operation, search_query = action.get("operation"), action.get("query", "")
        key = action_identity(action)
        if key in seen:
            state["rejected_actions"].append({**action, "reason": "Duplicate operation"})
            continue
        seen.add(key)
        if (
            operation not in {"native_search", "document_search", "ontology_path"}
            or not isinstance(search_query, str)
            or not search_query.strip()
            or len(search_query) > 1000
            or action.get("requirement") not in state["requirements"]
        ):
            state["rejected_actions"].append(
                {**action, "reason": "Unsupported operation or unresolved requirement"}
            )
            continue
        if action.get("relations") and any(
            r not in store.registry.relations for r in action["relations"]
        ):
            state["rejected_actions"].append({**action, "reason": "Unapproved ontology path"})
            continue
        start = perf_counter()
        previous_ids = {p["evidence_id"] for p in bundle.evidence_passages}
        if operation == "ontology_path":
            from nasa_fire_ai.query.ontology_navigation import RouteStep

            try:
                if action.get("start") not in store.registry.entities:
                    raise LookupError("Unknown graph start")
                steps = [RouteStep(**step) for step in action.get("steps", [])]
                if (
                    not steps
                    or len(steps) > 3
                    or any(step.relation not in store.registry.relations for step in steps)
                ):
                    raise ValueError("Invalid graph path depth")
                result = store.explore_route(
                    action["start"], steps, registry, max_depth=3, budget=budget.max_candidates * 8
                )
                recovered = sorted(
                    {
                        eid
                        for path in result["results"][: budget.max_candidates]
                        for step in path["path"]
                        for eid in step["evidence_ids"]
                    }
                )
                if intent.source_constraints:
                    recovered = [
                        eid
                        for eid in recovered
                        if (registry.source_metadata(eid) or {}).get("source_id")
                        in intent.source_constraints
                    ]
                action = {**action, "path_receipt": result}
                known = {p["evidence_id"] for p in bundle.evidence_passages}
                bundle.evidence_passages.extend(
                    registry.resolve(eid) for eid in recovered if eid not in known
                )
            except (ValueError, LookupError, TypeError) as error:
                state["rejected_actions"].append({**action, "reason": type(error).__name__})
                continue
        elif operation == "native_search":
            retry_intent = intent.model_copy(deep=True)
            if action["requirement"] in store.registry.information_classes:
                retry_intent.requested_information = [action["requirement"]]
            try:
                extra = execute_native(
                    retry_intent, search_query, store, registry, limit=budget.max_candidates
                )
            except (TimeoutError, OSError, sqlite3.Error, ValueError) as error:
                state["rejected_actions"].append(
                    {**action, "reason": type(error).__name__, "failure": "RETRIEVAL_FAILED"}
                )
                continue
            recovered = [p["evidence_id"] for p in extra.bundle.evidence_passages]
            merge_bundle(bundle, extra.bundle)
        else:
            eligible = [
                row[0]
                for row in registry.db.execute(
                    "SELECT p.evidence_id FROM passages p JOIN documents d USING(document_id) JOIN sources s USING(source_id) WHERE s.status NOT IN ('ROLLED_BACK','SUPERSEDED')"
                )
                if not intent.source_constraints
                or (registry.source_metadata(row[0]) or {}).get("source_id")
                in intent.source_constraints
            ]
            try:
                passages = registry.search(
                    search_query, eligible_ids=eligible, limit=budget.max_candidates
                )
            except (TimeoutError, OSError, sqlite3.Error, ValueError) as error:
                state["rejected_actions"].append(
                    {**action, "reason": type(error).__name__, "failure": "RETRIEVAL_FAILED"}
                )
                continue
            recovered = [p["evidence_id"] for p in passages]
            known = {p["evidence_id"] for p in bundle.evidence_passages}
            for passage in passages:
                passage["source_metadata"] = registry.source_metadata(passage["evidence_id"])
                if passage["evidence_id"] not in known:
                    bundle.evidence_passages.append(passage)
        state["rounds"] += 1
        updated = evaluate_sufficiency(query, intent, bundle, registry)
        state["completed_actions"].append(
            {
                **action,
                "scientific_constraints": state["explicit_constraints"],
                "cost": {"candidate_limit": budget.max_candidates},
                "stopping_condition": "Supported requirements, exhausted alternatives or budget",
                "recovered_evidence_ids": recovered,
                "new_evidence_ids": sorted(set(recovered) - previous_ids),
                "coverage_before": coverage,
                "coverage_after": updated,
                "latency_ms": (perf_counter() - start) * 1000,
            }
        )
        coverage = updated
    state["final_coverage"] = coverage
    state.setdefault(
        "stop_reason",
        "Requirements supported" if coverage["sufficient"] else "Execution budget exhausted",
    )
    state["missing_information"] = [
        x["requirement"] for x in coverage["items"] if x["status"] != "SUPPORTED"
    ]
    state["final_decision"] = (
        "ANSWER"
        if coverage["sufficient"]
        else "PARTIAL_ANSWER"
        if any(x["evidence_ids"] for x in coverage["items"])
        else "ABSTAIN"
    )
    state["latency_ms"] = (perf_counter() - began) * 1000
    state["remaining_budget"] = {
        "actions": budget.max_actions - state["action_attempts"],
        "rounds": budget.max_rounds - state["rounds"],
        "seconds": max(0, budget.timeout_seconds - state["latency_ms"] / 1000),
    }
    state["receipt_id"] = hashlib.sha256(
        repr((query, state["completed_actions"])).encode()
    ).hexdigest()[:20]
    bundle.retrieval_metadata["investigation"] = state
    return state
