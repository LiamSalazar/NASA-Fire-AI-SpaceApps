"""Validated applicability on the native graph; no canonical fact mutation."""

import hashlib
import json
import os
import re
from pathlib import Path

from rdflib import RDF, Literal

from nasa_fire_ai.context import ContextStatement, ContextStatus, ScopeResolver
from nasa_fire_ai.query.v2 import GenericValue

VERIFIED = {ContextStatus.EXPLICIT_LOCAL, ContextStatus.VERIFIED_APPLICABLE_CONTEXT}


def enabled():
    return os.getenv("SCIENTIFIC_CONTEXT_RESOLUTION_ENABLED", "false").lower() in {
        "true",
        "1",
        "yes",
    }


def query_policy(query, intent, store):
    config = store.registry.selection_policy.get("context", {})
    explicit = [
        c.entity_id
        for c in intent.entity_constraints
        if c.relation == config.get("preference_relation")
    ]
    comparative = any(term in query.lower() for term in config.get("comparative_terms", []))
    active = os.getenv("MICROGRAVITY_FIRST_RETRIEVAL_ENABLED", "true").lower() in {
        "true",
        "1",
        "yes",
    }
    return {
        "enabled": active,
        "explicit_values": explicit,
        "comparative": comparative,
        "default_preference": config.get("preferred_values", [])
        if active and not explicit and not comparative
        else [],
        "preference_relation": config.get("preference_relation"),
        "authority": "retrieval_preference_only",
    }


def prioritize(passages, query, intent, store):
    policy = query_policy(query, intent, store)
    if not policy["default_preference"]:
        return passages
    terms = store.registry.selection_policy.get("context", {}).get("preference_terms", [])
    return sorted(
        passages, key=lambda p: -int(any(term in p.get("text", "").lower() for term in terms))
    )


class ContextLayer:
    """An evidence-validated view of applicability over one native graph."""

    def __init__(self, store, evidence_registry, data):
        self.store = store
        self.evidence = evidence_registry
        self.resolver = ScopeResolver()
        self.rejected = []
        self.records = []
        self.receipts = []
        self.model_receipts = []
        self.live_calls = 0
        self.dimensions = store.registry.selection_policy.get("context", {}).get("dimensions", {})
        self.model_records = set(data.get("model_validated_records", []))
        self.entity_definitions = {e["id"]: e for e in data.get("entities", [])}
        # Scientific identities reside in the existing RDF graph. These nodes
        # explicitly lack canonical approval; registry locators stay outside it.
        from nasa_fire_ai.query.native import NS, node

        for entity in self.entity_definitions.values():
            refs = entity.get("evidence_ids", [])
            if (
                entity["class_id"]
                not in store.registry.target_classes | store.registry.information_classes
                or not refs
                or any(not evidence_registry.resolve(e) for e in refs)
            ):
                self.rejected.append(
                    {"entity": entity["id"], "reason": "invalid_entity_provenance_or_class"}
                )
                continue
            subject = node(entity["id"])
            store.graph.add((subject, RDF.type, node(entity["class_id"])))
            store.graph.add((subject, NS.canonical, Literal(False)))
            store.graph.add((subject, NS.reviewState, Literal("VERIFIED_CONTEXTUAL_APPLICABILITY")))
            store.graph.add((subject, NS.payload, Literal(json.dumps(entity))))
            for eid in refs:
                store.graph.add((subject, NS.evidenceRef, Literal(eid)))
            store.registry.entities.add(entity["id"])
            for sid in entity.get("source_ids", []):
                store.graph.add((subject, NS.source, node(sid)))
        for eid, alias in data.get("query_aliases", {}).items():
            if eid in store.registry.entities and alias.get("relation") in store.registry.relations:
                if not hasattr(store.registry, "entity_mentions"):
                    store.registry.entity_mentions = {}
                store.registry.entity_mentions[eid] = alias
        for row in data.get("statements", []):
            statement = ContextStatement.model_validate(row)
            reason = self.validate(statement)
            if reason:
                self.rejected.append({"statement_id": statement.statement_id, "reason": reason})
            else:
                self.resolver.add(statement)
                self.materialize(statement)
        for record in data.get("scientific_records", []):
            if record["id"] not in store.registry.entities:
                self.rejected.append({"record": record["id"], "reason": "unknown_record_entity"})
                continue
            if not self.exact_support(record.get("support_spans", [])):
                self.rejected.append({"record": record["id"], "reason": "unsupported_record_quote"})
                continue
            self.records.append(record)

    def materialize(self, statement):
        """Represent verified contextual domain relations inside the native RDF graph."""
        from nasa_fire_ai.query.native import NS, node

        for subject in statement.entity_ids:
            if subject in statement.exceptions:
                continue
            record = node("context-relation:" + statement.statement_id + ":" + subject)
            graph = self.store.graph
            graph.add((record, NS.reviewState, Literal("VERIFIED_CONTEXTUAL_APPLICABILITY")))
            graph.add((record, NS.subject, node(subject)))
            if (
                statement.relation in self.store.registry.relations
                and statement.value in self.store.registry.entities
            ):
                graph.add((record, RDF.type, NS.SemanticRelation))
                graph.add((record, NS.relation, node(statement.relation)))
                graph.add((record, NS.object, node(statement.value)))
            elif statement.property_value is not None:
                graph.add((record, RDF.type, NS.SemanticValue))
                graph.add((record, NS.measuredProperty, node(statement.relation)))
                graph.add((record, NS.value, Literal(json.dumps(statement.property_value))))
                graph.add((record, NS.qualifiers, Literal(json.dumps({"scope": statement.scope}))))
            for eid in statement.evidence_ids:
                graph.add((record, NS.evidenceRef, Literal(eid)))
            for step in statement.membership_paths.get(subject, []):
                if step["basis"] != "EXPLICIT_SOURCE_IDENTITY":
                    continue
                membership = node(
                    "context-membership:" + step["from"] + ":" + step["relation"] + ":" + step["to"]
                )
                graph.add((membership, RDF.type, NS.SemanticRelation))
                graph.add((membership, NS.subject, node(step["from"])))
                graph.add((membership, NS.relation, node(step["relation"])))
                graph.add((membership, NS.object, node(step["to"])))
                graph.add(
                    (membership, NS.reviewState, Literal("VERIFIED_CONTEXTUAL_APPLICABILITY"))
                )
                for span in step["support_spans"]:
                    graph.add((membership, NS.evidenceRef, Literal(span["evidence_id"])))

    def exact_support(self, spans):
        return bool(spans) and all(
            span.get("text", "").strip()
            and (record := self.evidence.resolve(span.get("evidence_id", "")))
            and span["text"] in record["text"]
            for span in spans
        )

    def validate(self, statement):
        if statement.relation not in self.dimensions:
            return "relation_or_property_has_no_declarative_context_semantics"
        if (
            statement.relation not in self.store.registry.relations
            and statement.relation not in self.store.registry.properties
        ):
            return "unknown_ontology_predicate"
        if not self.exact_support(statement.support_spans):
            return "non_exact_source_support"
        if statement.original_text not in "\n".join(s["text"] for s in statement.support_spans):
            return "original_statement_not_supported"
        if set(statement.evidence_ids) != {s["evidence_id"] for s in statement.support_spans}:
            return "evidence_set_mismatch"
        if statement.quantifier not in {"ALL", "IDENTIFIED"} or statement.applicability_conditions:
            return "limited_or_conditional_scope_requires_review"
        if statement.validation_status not in VERIFIED:
            return "unverified_statement"
        for subject in statement.entity_ids:
            if subject not in self.store.registry.entities:
                return "unknown_subject"
            if subject in statement.exceptions:
                continue
            path = statement.membership_paths.get(subject)
            if not path:
                return "missing_membership_path"
            previous = subject
            if len(path) > 5:
                return "membership_path_budget_exceeded"
            for step in path:
                if step.get("from") != previous:
                    return "disconnected_membership_path"
                if step.get("relation") not in self.store.registry.relations:
                    return "unknown_membership_relation"
                if not self.exact_support(step.get("support_spans", [])):
                    return "unsupported_membership_evidence"
                target = step.get("to")
                if target not in self.store.registry.entities:
                    return "unknown_membership_endpoint"
                if step.get("basis") == "NATIVE_GRAPH":
                    actual = self.store.relations(previous, step["relation"])
                    if target not in actual and previous not in self.store.relations(
                        target, step["relation"]
                    ):
                        return "membership_edge_absent_from_native_graph"
                elif step.get("basis") == "EXPLICIT_SOURCE_IDENTITY":
                    definition = self.entity_definitions.get(previous, {})
                    if target not in definition.get("scope_entities", []):
                        return "source_scope_identity_not_approved"
                else:
                    return "unapproved_membership_basis"
                previous = target
            if previous != statement.scope_entity:
                return "membership_path_does_not_reach_statement_scope"
        if statement.property_value is not None:
            from nasa_fire_ai.query.v2 import PropertyConstraintV2

            try:
                self.store.registry.validate(
                    PropertyConstraintV2(
                        property_id=statement.relation,
                        operator="EQ",
                        value=GenericValue.model_validate(statement.property_value),
                    )
                )
            except (LookupError, ValueError):
                return "invalid_numeric_value_or_unit"
        return None

    def resolve(self, subject, predicate):
        if predicate not in self.dimensions:
            return None
        result = self.resolver.resolve(subject, self.dimensions[predicate])
        self.receipts.append({"predicate": predicate, **result.model_dump(mode="json")})
        return result

    def relations(self, subject, predicate):
        result = self.resolve(subject, predicate)
        if result and result.status in VERIFIED:
            return set(result.values), result
        return set(), result

    def values(self, subject, predicate, qualifiers):
        result = self.resolve(subject, predicate)
        if result and result.status in VERIFIED:
            return [
                {
                    "value": GenericValue.model_validate(s.property_value),
                    "qualifiers": {},
                    "evidence_ids": s.evidence_ids,
                }
                for s in result.statements
                if s.property_value and not qualifiers
            ]
        return []

    def select_information(self, intent, query):
        requested = set(intent.requested_information)
        if intent.clarification_required or intent.unresolved_mentions:
            return []
        terms = set(re.findall(r"[a-z0-9]+", query.lower())) - set(
            self.store.registry.selection_policy.get("stop_words", [])
        )
        for forms in self.store.registry.selection_policy.get("topical_wordforms", {}).values():
            if terms.intersection(forms):
                terms.update(forms)
        candidates = []
        for record in self.records:
            if requested and record["class_id"] not in requested:
                continue
            if not requested and intent.targets and record["class_id"] not in intent.targets:
                continue
            if intent.source_constraints and not set(record.get("source_ids", [])).intersection(
                intent.source_constraints
            ):
                continue
            applicable_concepts = " ".join(
                s.value for s in self.resolver.statements if record["id"] in s.entity_ids
            )
            if not terms.intersection(
                re.findall(r"[a-z0-9]+", (record["text"] + " " + applicable_concepts).lower())
            ):
                continue
            candidates.append(record["id"])
        return candidates

    def request_limits(self, subject, query):
        record = next((r for r in self.records if r["id"] == subject), None)
        if record is None:
            return []
        config = self.store.registry.selection_policy.get("context", {})
        text = "\n".join(span["text"] for span in record["support_spans"]).lower()
        limits = []
        for cue, forms in config.get("event_requirements", {}).items():
            if cue in query.lower() and not any(form in text for form in forms):
                limits.append("requested_event_not_established:" + cue)
        if any(term.lower() in query.lower() for term in config.get("documented_join_terms", [])):
            limits.append("observation_to_conclusion_support_relation_not_verified")
        return limits

    def validate_model_proposal(self, proposal):
        from nasa_fire_ai.context import validate_proposal

        evidence = {eid: self.evidence.resolve(eid) for eid in proposal.evidence_ids}
        evidence = {eid: row for eid, row in evidence.items() if row is not None}
        checked = validate_proposal(proposal, evidence)
        reasons = []
        if checked.validation_status == "REJECTED":
            reasons.append("source_span_or_identifier_validation_failed")
        matching = [
            s
            for s in self.resolver.statements
            if proposal.subject_entity in s.entity_ids
            and s.relation == proposal.candidate_predicate
            and s.value == proposal.object_value
            and proposal.subject_entity not in s.exceptions
        ]
        if not matching:
            reasons.append("no_verified_same_entity_relation_value_scope")
        elif not any(set(proposal.evidence_ids).intersection(s.evidence_ids) for s in matching):
            from nasa_fire_ai.ingestion.source_spans import recover_span

            equivalent_source = False
            for statement in matching:
                for span in checked.support_spans:
                    for reference in statement.support_spans:
                        if self.evidence.source_metadata(
                            span["evidence_id"]
                        ) != self.evidence.source_metadata(reference["evidence_id"]):
                            continue
                        try:
                            recover_span(reference["text"], span["text"])
                            equivalent_source = True
                        except ValueError:
                            pass
            if not equivalent_source:
                reasons.append("support_not_in_verified_scope")
        if re.search(
            r"\b(?:was sought|will be|planned|hypothes[ei]s|objective|proposed)\b",
            checked.source_statement,
            re.IGNORECASE,
        ):
            reasons.append("prospective_or_objective_quote_does_not_establish_execution")
        if matching and proposal.context_scope not in {s.scope for s in matching}:
            reasons.append("proposal_scope_does_not_match_verified_scope")
        if proposal.quantifier not in {"ALL", "IDENTIFIED"} or proposal.applicability_conditions:
            reasons.append("limited_quantification_or_unverified_conditions")
        if proposal.exceptions or proposal.conflicts:
            reasons.append("exception_or_conflict_requires_review")
        return {
            "proposal": checked.model_dump(mode="json"),
            "reasons": reasons,
            "status": "STAGED_CANDIDATE" if reasons else "VERIFIED_CONTEXTUAL_APPLICABILITY",
            "reference_statements": [s.statement_id for s in matching],
            "provenance_paths": [
                s.membership_paths.get(proposal.subject_entity, []) for s in matching
            ],
            "independent_expert_label": None,
        }

    def interpret_query(self, query, intent, interpreter=None):
        """Optional bounded fresh interpretation, with cache and offline fallback."""
        if os.getenv("NEMOTRON_CONTEXT_INTERPRETATION_ENABLED", "false").lower() != "true":
            return
        budget = min(2, max(0, int(os.getenv("CONTEXT_QUERY_LIVE_CALL_BUDGET", "0"))))
        if budget == 0:
            return
        selected = set(self.select_information(intent, query))
        ordered = sorted(self.records, key=lambda record: record["id"] not in selected)
        keys = [span["evidence_id"] for record in ordered for span in record["support_spans"]]
        passages = []
        for eid in dict.fromkeys(keys):
            p = self.evidence.resolve(eid)
            if (
                len(passages) >= 12
                or sum(len(row["text"]) for row in passages) + len(p["text"]) > 24000
            ):
                break
            passages.append(p)
        cache_key = hashlib.sha256(
            json.dumps(
                {
                    "query": query,
                    "passages": passages,
                    "context": [s.model_dump(mode="json") for s in self.resolver.statements],
                },
                sort_keys=True,
            ).encode()
        ).hexdigest()
        cached = self.evidence.get_phase3_cache(cache_key, "scientific_context_v1")
        if cached:
            validations = cached["validations"]
            self.model_receipts.append({"execution": "CHECKPOINT_REPLAY", "cache_key": cache_key})
        else:
            if self.live_calls >= budget:
                return
            self.live_calls += 1
            from nasa_fire_ai.config import Settings
            from nasa_fire_ai.llm.context import NvidiaContextInterpreter
            from nasa_fire_ai.llm.interfaces import NotConfigured, ProviderFailure

            try:
                if interpreter is None:
                    settings = Settings()
                    interpreter = NvidiaContextInterpreter(
                        settings.nvidia_api_key,
                        settings.nvidia_base_url,
                        settings.nvidia_phase3_model,
                    )
                proposals = interpreter.interpret(
                    query=query,
                    entities=list(self.store.registry.entities),
                    passages=passages,
                    allowed_predicates=list(self.dimensions),
                )
                validations = [self.validate_model_proposal(p) for p in proposals]
            except (NotConfigured, ProviderFailure, ValueError):
                self.model_receipts.append(
                    {
                        "execution": "FRESH_INFERENCE_FAILED_OR_UNCONFIGURED",
                        "canonical_effect": "NONE",
                    }
                )
                return
            self.evidence.set_phase3_cache(
                cache_key, "scientific_context_v1", {"validations": validations}
            )
            self.model_receipts.append(
                getattr(interpreter, "last_receipt", {"execution": "INJECTED_INTERPRETER"})
            )
        self.model_records.update(
            v["proposal"]["subject_entity"] for v in validations if not v["reasons"]
        )


def attach_context_layer(store, evidence_registry, path):
    path = Path(path)
    if path.is_file():
        store.context_layer = ContextLayer(store, evidence_registry, json.loads(path.read_text()))
    return store
