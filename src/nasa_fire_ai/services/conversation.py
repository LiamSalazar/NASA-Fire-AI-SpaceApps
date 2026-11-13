"""Bounded conversational orchestration over ScientificSearchService.

Session text provides referents only. Every turn retrieves again from the pinned
snapshot. A rejected paragraph does not discard other supported paragraphs.
"""

import hashlib
import json
import re
from collections import OrderedDict
from time import monotonic
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from nasa_fire_ai.ingestion.scientific_facets import REPORTED_QUANTITY_ROLE
from nasa_fire_ai.llm.interfaces import ProviderFailure
from nasa_fire_ai.services.claim_ledger import persist_claim_ledger
from nasa_fire_ai.services.context_assembly import (
    allocate_context,
    generation_comparison,
    information_needs,
)
from nasa_fire_ai.services.ontology_support import audit_relation
from nasa_fire_ai.services.operations import checkpoint
from nasa_fire_ai.services.semantic_support import verify_paraphrase


class HistoryMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=12000)


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(min_length=1, max_length=12000)
    conversation_id: UUID | None = None
    history: list[HistoryMessage] = Field(default_factory=list, max_length=12)
    detail: Literal["concise", "standard", "technical"] = "standard"
    max_queries: int = Field(default=3, ge=1, le=6)
    evidence_limit: int = Field(default=12, ge=1, le=40)
    max_output_tokens: int = Field(default=4000, ge=256, le=10000)
    scientific_parameters: dict | None = None

    @field_validator("scientific_parameters")
    @classmethod
    def scenario_contract(cls, value, info):
        if value is None:
            return None
        from nasa_fire_ai.query.scenario import ScenarioInput

        return ScenarioInput.model_validate(
            {**value, "question": info.data.get("message", "scenario")}
        ).model_dump(mode="json")

    @field_validator("message")
    @classmethod
    def nonempty(cls, value):
        if not value.strip():
            raise ValueError("Message cannot be blank")
        return value


class ChatResponse(BaseModel):
    schema_version: Literal["scientific-chat-v1"] = "scientific-chat-v1"
    conversation_id: str
    message_id: str
    answer: str
    citations: list[dict] = Field(default_factory=list)
    evidence_groups: dict
    additional_candidates: list[dict] = Field(default_factory=list)
    retrieval: dict = Field(default_factory=dict)
    comparison: dict | None = None
    discovery_suggestions: list[dict] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    provider_status: dict
    trace_id: str
    snapshot_id: str
    generation_status: dict = Field(default_factory=dict)
    verification_status: dict = Field(default_factory=dict)
    answer_completeness: dict = Field(default_factory=dict)
    coverage_summary: dict = Field(default_factory=dict)


def public_evidence(row):
    """Never expose local filenames, checksums or arbitrary file access URLs."""
    keys = (
        "evidence_id",
        "document_id",
        "page",
        "section",
        "text",
        "start_offset",
        "end_offset",
        "structured_location",
        "source_cells",
        "source",
        "category",
    )
    return {k: row[k] for k in keys if k in row}


def catalogue_fields(row):
    """Recognize source-backed JSON catalogue records independently of key order."""
    source_type = row.get("source", {}).get("source_type", "").lower()
    if source_type and "catalog" not in source_type:
        return {}
    try:
        fields = json.loads(row.get("text", ""))
    except (ValueError, TypeError):
        return {}
    return fields if isinstance(fields, dict) and fields.get("title") else {}


def paragraph_spans(text):
    """Whole sentences or short table/procedure paragraphs, never clipped tokens."""
    from nasa_fire_ai.ingestion.abbreviations import split_by_view

    for paragraph in re.split(r"\n\s*\n", text):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        sentences = split_by_view(r"(?<!\b[A-Z]\.)(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚ0-9])", paragraph)
        for sentence in sentences:
            if 15 <= len(sentence) <= 1400:
                yield sentence
            elif len(sentence) > 1400:
                # Long method inventories and lists often have no sentence stops.
                # Keep exact whole printed lines, with an overlapping context line.
                lines = sentence.splitlines(keepends=True)
                start = 0
                while start < len(lines):
                    end = start
                    size = 0
                    while end < len(lines) and size + len(lines[end]) <= 1400:
                        size += len(lines[end])
                        end += 1
                    if end == start:
                        start += 1
                        continue
                    window = "".join(lines[start:end]).strip()
                    if len(window) >= 15:
                        yield window
                    start = max(start + 1, end - 2)


def document_context_window(original, span, limit=1800, radius=1):
    """Exact neighboring source sentences, preserving reference and exceptions."""
    from nasa_fire_ai.ingestion.abbreviations import segmentation_view

    begin = original.find(span)
    if begin < 0:
        return None
    boundaries = [
        0,
        *[m.end() for m in re.finditer(r"[.!?]\s+(?=[A-Z])", segmentation_view(original))],
        len(original),
    ]
    if radius > 1:
        from bisect import bisect_left, bisect_right

        first = max(0, bisect_right(boundaries, begin) - 1 - radius)
        last = min(len(boundaries) - 1, bisect_left(boundaries, begin + len(span)) + radius)
        window = original[boundaries[first] : boundaries[last]].strip()
        return window if len(window) <= limit else None
    before = [position for position in boundaries if position < begin]
    after = [position for position in boundaries if position > begin + len(span)]
    window = original[before[-1] if before else 0 : after[0] if after else len(original)].strip()
    return window if len(window) <= limit else None


def rank_alignment_candidates(text, candidates, scientific_subject=None):
    """Route verification to discriminating source words; never certify a claim.

    Document and section boilerplate must not outweigh a specific apparatus or
    observation. Frequencies are computed from this bounded evidence inventory.
    Printed line-break variants are retrieval tokens only; evidence is untouched.
    """
    from collections import Counter
    from math import log

    from nasa_fire_ai.services.document_sections import quoted_section_content

    routing_text = quoted_section_content(text) or text

    stop = {
        "the",
        "and",
        "for",
        "from",
        "with",
        "that",
        "this",
        "these",
        "those",
        "was",
        "were",
        "are",
        "has",
        "have",
        "report",
        "documentation",
        "source",
    }

    def terms(value):
        raw = set(re.findall(r"[a-z0-9]+", value.casefold()))
        joined = re.sub(r"(?<=[a-z])-\s*\n\s*(?=[a-z])", "", value.casefold())
        return (raw | set(re.findall(r"[a-z0-9]+", joined))) - stop

    query = terms(routing_text)
    documents = [terms(a.get("text", "")) for a in candidates]
    frequency = Counter(term for document in documents for term in document)
    weights = {term: log(1 + len(candidates) / (1 + frequency[term])) for term in query}
    scores = {
        id(a): sum(weights[t] for t in query & document)
        for a, document in zip(candidates, documents, strict=True)
    }
    from nasa_fire_ai.services.context_assembly import desired_source_roles
    from nasa_fire_ai.services.semantic_support import numeric_tokens

    requested_roles = desired_source_roles(text)
    quantities = numeric_tokens(routing_text)
    numeric_matches = (
        {
            id(anchor): bool(quantities & numeric_tokens(anchor.get("text", "")))
            for anchor in candidates
        }
        if quantities
        else {}
    )
    return sorted(
        candidates,
        key=lambda a: (
            a.get("text", "").strip() != routing_text.strip(),
            a.get("category") == "DISCOVERY",
            (
                0
                if scientific_subject in a.get("scientific_subjects", [])
                else 1
                if not a.get("scientific_subjects")
                else 2
            )
            if scientific_subject
            else 0,
            not numeric_matches.get(id(a), False) if quantities else False,
            not bool(requested_roles & set(a.get("source_roles", [])))
            if requested_roles
            else False,
            -scores[id(a)],
            a.get("support_id", ""),
        ),
    )


def compact_conditions(cells):
    from nasa_fire_ai.services.native import _comparison_value

    rows = []
    for cell in cells:
        actual = cell.get("actual")
        if isinstance(actual, list):
            actual = [
                _comparison_value(r["value"]) if isinstance(r, dict) and "value" in r else r
                for r in actual
            ]
        requested = cell.get("requested")
        if isinstance(requested, dict) and "value" in requested:
            requested = _comparison_value(requested["value"])
        rows.append(
            {
                "dimension": cell.get("dimension"),
                "status": cell.get("status"),
                "requested": requested,
                "actual": actual,
            }
        )
    return rows


def describe_comparison(subject, cells):
    descriptions = []
    for cell in compact_conditions(cells):
        dimension, status = cell["dimension"], cell["status"]
        requested, actual = cell["requested"], cell["actual"]
        if status == "MATCH":
            descriptions.append(
                f"For {subject}, recorded {dimension} {actual} matches requested {requested}."
            )
        elif status == "DIFFER":
            descriptions.append(
                f"For {subject}, recorded {dimension} {actual} differs from requested {requested}."
            )
        elif status == "UNKNOWN":
            descriptions.append(
                f"For {subject}, requested {dimension} {requested} remains unavailable in these retrieved records."
            )
        else:
            descriptions.append(
                f"For {subject}, {dimension} has status {status}; requested {requested}, recorded {actual}."
            )
    return " ".join(descriptions)


class ConversationService:
    def __init__(
        self,
        search,
        *,
        provider=None,
        entailment=None,
        max_sessions=200,
        history_characters=24000,
        session_ttl=3600,
        source_characters=60000,
        max_alignment_checks=96,
        candidate_history_limit=1000,
        max_exploratory_sources=3,
        max_repair_attempts=1,
        max_redundancy_checks=12,
    ):
        self.search = search
        self.provider = provider
        self.entailment = entailment
        self.sessions = OrderedDict()
        self.focus = {}
        self.retrieved = {}
        self.max_sessions = max_sessions
        self.history_characters = history_characters
        self.session_ttl = session_ttl
        self.source_characters = source_characters
        self.max_alignment_checks = max_alignment_checks
        self._alignment_checks = 0
        self._total_alignment_checks = 0
        self._alignment_exhausted = False
        self._source_reviews = []
        self.candidate_history_limit = candidate_history_limit
        self.max_exploratory_sources = max_exploratory_sources
        self.traces = OrderedDict()
        if not 0 <= max_repair_attempts <= 2 or not 0 <= max_redundancy_checks <= 64:
            raise ValueError("Conversation repair/redundancy budget outside bounds")
        self.max_repair_attempts = max_repair_attempts
        self.max_redundancy_checks = max_redundancy_checks
        self.inventory_receipt = {}

    def _history(self, request, cid):
        now = monotonic()
        for key, (timestamp, _) in list(self.sessions.items()):
            if now - timestamp > self.session_ttl:
                del self.sessions[key]
                self.focus.pop(key, None)
                self.retrieved.pop(key, None)
        if request.conversation_id and cid not in self.sessions:
            raise LookupError("Unknown or expired conversation")
        history = list(self.sessions.get(cid, (0, []))[1])
        history.extend(m.model_dump() for m in request.history)
        history = history[-12:]
        while history and sum(len(m["content"]) for m in history) > self.history_characters:
            history.pop(0)
        return history

    def _attach_scientific_identity(self, anchor):
        """Bind a passage to source-backed graph subjects, never routing guesses."""
        metadata_scopes = {
            "section_heading",
            "source_record_heading",
            "source_subject_context",
            "source_local_name_definition",
        }
        snapshot = getattr(self.search, "manifest", {}).get("snapshot_id")
        key = None
        if snapshot and anchor.get("document_id") and not anchor.get("typed_fields"):
            key = (
                snapshot,
                anchor["document_id"],
                anchor.get("graph_context_id"),
                tuple(
                    (span["evidence_id"], span["text"], span.get("scope"))
                    for span in anchor.get("spans", [])
                    if span.get("scope") not in metadata_scopes
                ),
            )
            if not hasattr(self, "_scientific_identity_cache"):
                self._scientific_identity_cache = OrderedDict()
            cached = self._scientific_identity_cache.get(key)
            if cached is not None:
                self._scientific_identity_cache.move_to_end(key)
                anchor.update(cached["metadata"])
                anchor["spans"] = [
                    *anchor.get("spans", []),
                    *[dict(s) for s in cached["spans"] if s not in anchor.get("spans", [])],
                ]
                return anchor
        store = getattr(self.search, "store", None)
        resolver = getattr(self.search, "passage_scientific_subjects", None)
        if store is not None and resolver:
            from nasa_fire_ai.services.document_sections import add_section_subject_context

            if not hasattr(self, "_document_section_cache"):
                self._document_section_cache = {}
            add_section_subject_context(
                anchor, self.search.registry, self._document_section_cache, store
            )
        anchor["scientific_subjects"] = resolver(anchor) if resolver else []
        role_resolver = getattr(self.search, "passage_scientific_roles", None)
        anchor["source_roles"] = role_resolver(anchor) if role_resolver else []
        context_resolver = getattr(self.search, "passage_scientific_contexts", None)
        anchor["scientific_context_groups"] = context_resolver(anchor) if context_resolver else []
        anchor["source_aliases"] = (
            sorted(
                {
                    label
                    for subject in anchor["scientific_subjects"]
                    for label in [
                        subject,
                        *store.registry.entity_mentions.get(subject, {}).get("aliases", []),
                    ]
                }
            )
            if store is not None
            else []
        )
        metadata = getattr(self.search.registry, "source_metadata", None)
        title = anchor.get("source_title")
        if not title and metadata and anchor.get("spans"):
            title = (metadata(anchor["spans"][0]["evidence_id"]) or {}).get("title")
            anchor["source_title"] = title
        anchor["identity_context"] = f"Registered source title: {title}." if title else ""
        if anchor["source_aliases"]:
            anchor["identity_context"] += (
                "\nRegistered investigation identity for this source passage: "
                + ", ".join(anchor["source_aliases"])
                + "."
            )
        from nasa_fire_ai.services.document_sections import add_section_context

        if not hasattr(self, "_document_section_cache"):
            self._document_section_cache = {}
        add_section_context(anchor, self.search.registry, self._document_section_cache)
        if key is not None:
            fields = {
                "scientific_subjects",
                "source_roles",
                "scientific_context_groups",
                "source_aliases",
                "source_title",
                "identity_context",
                "method_references",
                "scientific_sections",
                "source_record_references",
            }
            self._scientific_identity_cache[key] = {
                "metadata": {field: anchor[field] for field in fields if field in anchor},
                "spans": [dict(s) for s in anchor["spans"] if s.get("scope") in metadata_scopes],
            }
            if len(self._scientific_identity_cache) > 4096:
                self._scientific_identity_cache.popitem(last=False)
        return anchor

    def _inventory(
        self, results, *, primary_result=None, question="", needs=None, scope_question=""
    ):
        from nasa_fire_ai.services.structured_alignment import (
            record_anchor_allowed,
            record_subjects,
        )

        inventory, seen, size = [], set(), 0
        subjects = record_subjects(results, question)
        needs = information_needs(question, needs)
        primary_result = primary_result or results[0]
        for result in results:
            checkpoint("context")
            index = 0 if result is primary_result else 1
            for claim in result.claims:
                # Strict source projection is already checked by verify_claim.
                spans = [
                    {"evidence_id": span["evidence_id"], "text": span["text"]}
                    for span in claim.get("support_spans", [])
                    if span.get("reference_kind") == "exact_source_span" and span.get("text")
                ]
                if not spans:
                    spans = [
                        {"evidence_id": source["evidence_id"], "text": source["text"]}
                        for source in claim.get("sources", [])
                        if source
                    ]
                if not spans:
                    continue
                key = claim["claim_id"]
                if key in seen:
                    continue
                anchor = {
                    "support_id": key,
                    "text": claim["text"],
                    "spans": spans,
                    "category": claim["relationship_status"] if index == 0 else "DOCUMENTARY",
                    "epistemic_type": claim["epistemic_type"],
                    "subject": claim.get("subject"),
                    "verified_context": ""
                    if " ".join(claim["text"].split())
                    in " ".join("\n".join(span["text"] for span in spans).split())
                    else claim["text"],
                    "projection_verified": True,
                    "conditions": claim.get("experimental_context", []),
                    "required_scope": claim.get("scope_limits", []),
                }
                structured_records = [
                    span.get("structured_record", {})
                    for span in claim.get("support_spans", [])
                    if span.get("structured_record")
                ]
                if structured_records and hasattr(self.search, "store"):
                    from nasa_fire_ai.services.structured_facts import structured_fact

                    fact = structured_fact(
                        structured_records[0].get("id"), self.search.store, self.search.registry
                    )
                    if fact:
                        anchor["deterministic_text"] = fact["text"]
                        anchor["structured_record_id"] = fact["record_id"]
                cost = len(str(anchor))
                seen.add(key)
                size += cost
                inventory.append(anchor)
            if index == 0:
                for row in result.related:
                    refs = row.get("evidence", [])
                    if not refs:
                        continue
                    context = describe_comparison(row["id"], row["constraints"])
                    anchor = {
                        "support_id": "related-" + row["id"],
                        "text": context,
                        "verified_context": context,
                        "category": "RELATED",
                        "epistemic_type": "query_condition_comparison",
                        "spans": [{"evidence_id": refs[0]["evidence_id"], "text": refs[0]["text"]}],
                        "conditions": row["constraints"],
                        "required_scope": [],
                        "comparison_limits": row["limitations"],
                    }
                    cost = len(str(anchor))
                    inventory.append(anchor)
                    size += cost
            if index == 0 and result.comparison:
                missing = result.comparison.get("unknown_or_unavailable_conditions", [])
                refs = {
                    span["evidence_id"]: span
                    for a in inventory
                    if a.get("epistemic_type") == "comparison_result"
                    for span in a["spans"]
                }
                if missing and refs:
                    context = (
                        "For the compared subjects "
                        + str(result.comparison.get("run_ids", []))
                        + ", these dimensions are unavailable in this snapshot comparison: "
                        + str(missing)
                        + ". This is coverage of this comparison, not a NASA knowledge gap."
                    )
                    anchor = {
                        "support_id": "comparison-coverage",
                        "text": context,
                        "verified_context": context,
                        "spans": list(refs.values()),
                        "category": "DOCUMENTARY",
                        "epistemic_type": "comparison_coverage",
                        "conditions": [],
                        "required_scope": [],
                    }
                    inventory.append(anchor)
                    size += len(str(anchor))
            documentary_rows = {
                row["evidence_id"]: row
                for row in [
                    *result.documentary,
                    *[r for r in result.candidates if r.get("category") == "DOCUMENTARY"],
                ]
            }
            # An explicitly identified source record is a structured query result,
            # even if open wording cannot establish DIRECT experimental applicability.
            # Fetch its own evidence before a lexical/context quota can omit it.
            if getattr(self.search, "store", None):
                for subject in set(result.intent.subject_ids) & subjects:
                    for eid in self.search.store.evidence(subject):
                        source = self.search.registry.resolve(eid)
                        metadata = self.search.registry.source_metadata(eid) or {}
                        allowed_sources = result.intent.source_constraints
                        if (
                            source
                            and source.get("source_cells")
                            and (
                                not allowed_sources or metadata.get("source_id") in allowed_sources
                            )
                        ):
                            documentary_rows.setdefault(eid, source)
            # Examine report structure from the SAME retrieved documents. This is
            # source examination, not a new corpus or a scientific relation.
            documents = {
                row["document_id"] for row in documentary_rows.values() if row.get("document_id")
            }
            overview_ids = set()
            for document in sorted(documents):
                # Examine the already-found report before another broad search.
                # All pages remain eligible; source order is not a relevance rule.
                for source in self.search.registry.db.execute(
                    "SELECT * FROM passages WHERE document_id=? ORDER BY page,evidence_id",
                    (document,),
                ):
                    row = dict(source)
                    if row.get("section") == "table_row":
                        # Numeric tables contribute retrieved, scoped records;
                        # document examination does not expand every other row.
                        continue
                    documentary_rows.setdefault(row["evidence_id"], row)
                    if re.search(
                        r"(?im)^\s*(?:abstract|executive summary|introduction|conclusions|scope|purpose)\s*$",
                        row["text"],
                    ):
                        overview_ids.add(row["evidence_id"])
            for row in documentary_rows.values():
                if catalogue_fields(row):
                    continue
                for span in paragraph_spans(row["text"]):
                    key = (row.get("checksum") or row["evidence_id"], row.get("page"), span)
                    if key in seen:
                        continue
                    anchor = {
                        "support_id": "d-"
                        + hashlib.sha256((row["evidence_id"] + span).encode()).hexdigest()[:12],
                        "text": span,
                        "spans": [{"evidence_id": row["evidence_id"], "text": span}],
                        "category": "DOCUMENTARY",
                        "epistemic_type": "documentary_content",
                        "source_role": row.get("structured_location", {}).get("field"),
                        "examination_role": "overview"
                        if row["evidence_id"] in overview_ids
                        else "retrieved_passage",
                        "conditions": [],
                        "required_scope": [],
                    }
                    if (row.get("source_cells") or row.get("section") == "table_row") and hasattr(
                        self.search, "store"
                    ):
                        links = self.search.registry.db.execute(
                            "SELECT name FROM sqlite_master WHERE type='table' AND name='value_cells'"
                        ).fetchone()
                        if links:
                            anchor["typed_fields"] = [
                                {
                                    "id": payload["id"],
                                    "property_id": payload["property_id"],
                                    "aliases": self.search.store.registry.properties[
                                        payload["property_id"]
                                    ].aliases,
                                    "role": payload.get("qualifiers", {}).get("scientific_role"),
                                    "value": payload.get("value"),
                                }
                                for cell in self.search.registry.db.execute(
                                    "SELECT value_id FROM value_cells WHERE evidence_id=?",
                                    (row["evidence_id"],),
                                )
                                if (payload := self.search.store.payload(cell[0])).get(
                                    "property_id"
                                )
                                in self.search.store.registry.properties
                            ]
                    if anchor.get("typed_fields"):
                        from nasa_fire_ai.services.structured_facts import (
                            record_scope_fact,
                            structured_fact,
                        )

                        for field in anchor["typed_fields"]:
                            fact = structured_fact(
                                field["id"], self.search.store, self.search.registry
                            )
                            if not fact:
                                continue
                            fact_key = "value-" + fact["record_id"]
                            if fact_key in seen:
                                continue
                            projected = {
                                **anchor,
                                "support_id": fact_key,
                                "text": fact["text"],
                                "verified_context": fact["text"],
                                "deterministic_text": fact["text"],
                                "structured_record_id": fact["record_id"],
                                "subject": fact["subject"],
                                "projection_verified": True,
                                "epistemic_type": REPORTED_QUANTITY_ROLE,
                                "typed_fields": anchor["typed_fields"],
                                "spans": [fact["primary_span"]]
                                if fact.get("primary_span")
                                else [*anchor["spans"], *fact.get("definition_spans", [])],
                            }
                            if not record_anchor_allowed(projected, self.search, subjects):
                                continue
                            inventory.append(projected)
                            seen.add(fact_key)
                            size += len(str(projected))
                            scope = record_scope_fact(
                                fact["subject"], self.search.store, self.search.registry
                            )
                            scope_key = "scope-" + fact["subject"]
                            if (
                                scope
                                and scope_key not in seen
                                and (not subjects or fact["subject"] in subjects)
                            ):
                                scoped = {
                                    **projected,
                                    "support_id": scope_key,
                                    "text": scope["text"],
                                    "deterministic_text": scope["text"],
                                    "verified_context": scope["text"],
                                    "structured_record_id": fact["subject"],
                                    "projection_kind": "record_scope",
                                    "typed_fields": [],
                                    "epistemic_type": "documentary_content",
                                }
                                inventory.append(scoped)
                                seen.add(scope_key)
                                size += len(str(scoped))
                    if not record_anchor_allowed(anchor, self.search, subjects):
                        continue
                    # Store an exact contextual window. Re-examination may use it
                    # when a standalone sentence lacks its subject or qualifier.
                    window = document_context_window(row["text"], span)
                    if window:
                        anchor["context_window"] = window
                    cost = len(str(anchor))
                    seen.add(key)
                    size += cost
                    inventory.append(anchor)
            discovery_rows = {
                row["evidence_id"]: row
                for row in [
                    *result.discovery,
                    *[
                        r
                        for r in result.candidates
                        if r.get("category") == "DISCOVERY" or catalogue_fields(r)
                    ],
                ]
                if row.get("evidence_id")
            }
            for row in discovery_rows.values():
                fields = catalogue_fields(row)
                if not fields:
                    continue
                key = "catalogue-" + row["evidence_id"]
                if key in seen:
                    continue
                seen.add(key)
                inventory.append(
                    {
                        "support_id": key,
                        "text": row["text"],
                        "spans": [{"evidence_id": row["evidence_id"], "text": row["text"]}],
                        "category": "DISCOVERY",
                        "epistemic_type": "catalogue_metadata",
                        "conditions": [],
                        "required_scope": [
                            "Catalogue metadata; scientific applicability unverified"
                        ],
                    }
                )
        requested_investigations = {
            constraint.entity_id
            for result in results
            for constraint in getattr(getattr(result, "intent", None), "entity_constraints", [])
            if constraint.relation == "belongsToInvestigation"
        }
        from nasa_fire_ai.services.ontology_support import investigation_mentions

        if getattr(self.search, "store", None) is not None:
            requested_investigations.update(
                investigation_mentions(scope_question + " " + question, self.search.store)
            )
        inventory.extend(
            self._graph_context_candidates(
                question + " " + " ".join(need["need"] for need in needs), requested_investigations
            )
        )
        from nasa_fire_ai.services.document_sections import requested_method_passages

        documentary_eids = {
            span["evidence_id"]
            for row in inventory
            if row.get("category") == "DOCUMENTARY"
            for span in row.get("spans", [])
        }
        documents = {
            source["document_id"]
            for eid in documentary_eids
            if (source := self.search.registry.resolve(eid)) and source.get("document_id")
        }
        for passage in requested_method_passages(
            self.search.registry, documents, question, getattr(self, "_document_section_cache", {})
        ):
            key = (
                "section-"
                + hashlib.sha256(
                    (passage["evidence_id"] + str(passage["start"]) + str(passage["end"])).encode()
                ).hexdigest()[:16]
            )
            inventory.append(
                {
                    "support_id": key,
                    "text": passage["text"],
                    "spans": [{"evidence_id": passage["evidence_id"], "text": passage["text"]}],
                    "category": "DOCUMENTARY",
                    "epistemic_type": "documentary_content",
                    "conditions": [],
                    "required_scope": ["Original numbered method section"],
                    "document_id": passage["document_id"],
                    "method_section_context": True,
                    "section_subsection_count": passage["subsection_count"],
                }
            )
        evidence_metadata = {}
        for anchor in inventory:
            eid = anchor["spans"][0]["evidence_id"]
            if eid not in evidence_metadata:
                source = self.search.registry.resolve(eid) or {}
                metadata = self.search.registry.source_metadata(eid) or {}
                evidence_metadata[eid] = {
                    "document_id": source.get("document_id"),
                    "source_id": metadata.get("source_id"),
                    "source_title": metadata.get("title"),
                }
            anchor.update(evidence_metadata[eid])
            scopes = getattr(self.search, "source_scopes", {}).get(anchor.get("source_id"), set())
            anchor["routing_scope"] = (
                "MATCH"
                if scopes & requested_investigations
                else "DIFFERENT"
                if scopes and requested_investigations
                else "UNKNOWN"
            )
            self._attach_scientific_identity(anchor)
        from nasa_fire_ai.services.structured_alignment import expand_source_fields

        by_support = {anchor["support_id"]: anchor for anchor in inventory}
        old_support_ids = set(by_support)
        expand_source_fields(
            by_support,
            self.search,
            record_subjects(results, scope_question + " " + question),
            definitions_only=True,
            investigations=requested_investigations,
        )
        for support_id, anchor in by_support.items():
            if support_id in old_support_ids:
                continue
            self._attach_scientific_identity(anchor)
            anchor["source_roles"] = sorted(
                set(anchor.get("source_roles", []))
                | (
                    {"SourceFieldDefinition"}
                    if anchor.get("definition_scope")
                    else {"SourceAnnotation"}
                )
            )
            scopes = getattr(self.search, "source_scopes", {}).get(anchor.get("source_id"), set())
            if requested_investigations and scopes and requested_investigations.isdisjoint(scopes):
                continue
            anchor["routing_scope"] = "MATCH" if requested_investigations & scopes else "UNKNOWN"
            inventory.append(anchor)
        selected, allocation = allocate_context(inventory, question, needs, self.source_characters)
        size = allocation["context_characters"]
        offered = {s["evidence_id"] for a in inventory for s in a["spans"]}
        supplied = {s["evidence_id"] for a in selected for s in a["spans"]}
        self.inventory_receipt = {
            **allocation,
            "available_anchors": len(inventory),
            "supplied_anchors": len(selected),
            "context_characters": size,
            "omitted_anchors": len(inventory) - len(selected),
            "retrieved_evidence_ids": sorted(
                {
                    row["evidence_id"]
                    for result in results
                    for row in result.candidates
                    if row.get("evidence_id")
                }
            ),
            "available_evidence_ids": sorted(offered),
            "supplied_evidence_ids": sorted(supplied),
            "omitted_evidence_ids": sorted(offered - supplied),
            "available_sources": sorted(
                {a.get("source_id") for a in inventory if a.get("source_id")}
            ),
            "supplied_sources": sorted(
                {a.get("source_id") for a in selected if a.get("source_id")}
            ),
            "boundary": "Context selection is question relevance routing, not scientific validation",
        }
        return selected, len(inventory) - len(selected)

    def _method_scope_allowed(self, anchor):
        """An implicit method clause retains the numbered scope of this turn."""
        expected = getattr(self, "_requested_method_documents", {}).get(anchor.get("document_id"))
        if not expected or anchor.get("typed_fields"):
            return True
        from nasa_fire_ai.services.document_sections import add_section_context

        add_section_context(
            anchor, self.search.registry, getattr(self, "_document_section_cache", {})
        )
        actual = set(anchor.get("method_references", []))
        return bool(actual) and actual <= expected

    def _source_semantic_verdict(self, text, anchors, audit=None):
        """Use the same ontology/scope gate for initial and reexamined evidence."""
        from nasa_fire_ai.services.source_definitions import add_source_definitions

        if not hasattr(self, "_document_definition_cache"):
            self._document_definition_cache = {}
        for anchor in anchors:
            if getattr(self.search, "passage_scientific_subjects", None):
                self._attach_scientific_identity(anchor)
            add_source_definitions(
                text, anchor, self.search.registry, self._document_definition_cache
            )
        if any(not self._method_scope_allowed(anchor) for anchor in anchors):
            return {
                "supported": False,
                "errors": [
                    "Evidence does not preserve the requested numbered method section scope"
                ],
            }
        store = getattr(self.search, "store", None)
        if audit is None:
            audit = audit_relation(text, anchors, store, self.search.registry) if store else {}
        if audit.get("scientific_status") == "ONTOLOGY_INCOMPATIBLE":
            return {
                **audit,
                "supported": False,
                "errors": [audit.get("reason") or "Incompatible scientific scope"],
            }
        from nasa_fire_ai.services.document_sections import section_quotation

        framed = (
            section_quotation(
                anchors[0], self.search.registry, getattr(self, "_document_section_cache", {})
            )
            if len(anchors) == 1 and text.startswith("In source section “")
            else None
        )
        if re.fullmatch(
            r"In source section “[^”]+”, the report states: “.*”", text, re.DOTALL
        ) and (not framed or text != framed["text"]):
            return {
                **audit,
                "supported": False,
                "errors": [
                    "Quoted section attribution does not match the registered source location"
                ],
            }
        if framed and text == framed["text"]:
            verdict = verify_paraphrase(
                framed["quoted_text"], [framed["anchor"]], self.search.registry, self.entailment
            )
            if verdict.get("supported"):
                anchors[0].update(framed["anchor"])
                verdict["verification_mechanism"] = "registered_section_quotation"
        else:
            verdict = verify_paraphrase(text, anchors, self.search.registry, self.entailment)
        if audit.get("scientific_status") == "DOCUMENTARY_CANDIDATE" and verdict.get("supported"):
            audit["scientific_status"] = "DOCUMENT_SUPPORTED"
        return {
            **verdict,
            **audit,
            "verification_mechanism": verdict.get(
                "verification_mechanism", audit.get("verification_mechanism")
            ),
        }

    def _realign_documentary(self, text, anchors, inventory):
        """Re-examine already retrieved sentences on the SAME cited source pages.

        The generator's locator is a proposal. This never upgrades classification,
        changes experimental subjects, or searches another study for a convenient
        value. Every alternative still passes all source and semantic checks.
        """
        allowed_types = {"documentary_content", "source_quotation"}
        from nasa_fire_ai.services.document_sections import quoted_section_content

        quoted = quoted_section_content(text)
        if (
            not self.entailment
            or not anchors
            or any(
                a.get("category") != "DOCUMENTARY" or a.get("epistemic_type") not in allowed_types
                for a in anchors
            )
        ):
            return None
        pages = {span["evidence_id"] for anchor in anchors for span in anchor["spans"]}
        documents = {a.get("document_id") for a in anchors if a.get("document_id")}
        candidates = [
            a
            for a in inventory.values()
            if a.get("category") == "DOCUMENTARY"
            and a.get("epistemic_type") == "documentary_content"
            and (
                {s["evidence_id"] for s in a["spans"]} <= pages or a.get("document_id") in documents
            )
        ]
        # A context omission is not a source absence. Re-examine the cited
        # documents, including passages outside the generation context budget.
        if documents and hasattr(self.search.registry, "db"):
            existing = {(a["spans"][0]["evidence_id"], a["text"]) for a in candidates}
            for document in sorted(documents):
                cached = getattr(self, "_documentary_reexamination_pool", {}).get(document)
                if cached:
                    for original in cached:
                        key = (original["spans"][0]["evidence_id"], original["text"])
                        if key not in existing:
                            candidates.append(
                                {**original, "spans": [dict(s) for s in original["spans"]]}
                            )
                            existing.add(key)
                    if not quoted or any(a["text"] == quoted for a in cached):
                        continue
                for source in self.search.registry.db.execute(
                    "SELECT evidence_id,text,section FROM passages WHERE document_id=? ORDER BY page,evidence_id LIMIT 256",
                    (document,),
                ):
                    if source["section"] == "table_row":
                        # Structured field roles must travel with table claims;
                        # re-examination must not recreate an untyped alternative.
                        continue
                    if cached and (not quoted or quoted not in source["text"]):
                        continue
                    sentences = [] if cached else list(paragraph_spans(source["text"]))
                    if quoted and quoted in source["text"]:
                        sentences.insert(0, quoted)
                    for sentence in sentences:
                        key = (source["evidence_id"], sentence)
                        if key in existing:
                            continue
                        existing.add(key)
                        candidates.append(
                            {
                                "support_id": "review-"
                                + hashlib.sha256(
                                    (source["evidence_id"] + sentence).encode()
                                ).hexdigest()[:12],
                                "text": sentence,
                                "category": "DOCUMENTARY",
                                "epistemic_type": "documentary_content",
                                "document_id": document,
                                "context_window": document_context_window(source["text"], sentence),
                                "conditions": [],
                                "required_scope": [],
                                "source_id": (
                                    self.search.registry.source_metadata(source["evidence_id"])
                                    or {}
                                ).get("source_id"),
                                "spans": [{"evidence_id": source["evidence_id"], "text": sentence}],
                            }
                        )
        for candidate in candidates:
            self._attach_scientific_identity(candidate)
        from nasa_fire_ai.services.ontology_support import leading_investigation

        store = getattr(self.search, "store", None)
        primary = leading_investigation(text, store) if store is not None else None
        candidates = rank_alignment_candidates(text, candidates, (primary or {}).get("id"))
        if not hasattr(self, "_documentary_reexamination_pool"):
            self._documentary_reexamination_pool = {}
        for document in documents:
            self._documentary_reexamination_pool[document] = [
                candidate for candidate in candidates if candidate.get("document_id") == document
            ]
        scored = []
        expanded = []
        for candidate in candidates[:24]:
            # Examined original sentences remain repair candidates even when
            # an earlier model paraphrase cannot be verified against them.
            inventory.setdefault(candidate["support_id"], candidate)
            expanded.append(candidate)
            window = candidate.get("context_window")
            if window and window != candidate["text"]:
                expanded.append(
                    {
                        **candidate,
                        "spans": [
                            {"evidence_id": candidate["spans"][0]["evidence_id"], "text": window}
                        ],
                    }
                )
        for candidate in expanded:
            if self._alignment_checks >= self.max_alignment_checks:
                return None
            self._alignment_checks += 1
            self._total_alignment_checks += 1
            self._attach_scientific_identity(candidate)
            from nasa_fire_ai.services.source_definitions import add_source_definitions

            if not hasattr(self, "_document_definition_cache"):
                self._document_definition_cache = {}
            add_source_definitions(
                text, candidate, self.search.registry, self._document_definition_cache
            )
            check = self._source_semantic_verdict(text, [candidate])
            self._source_reviews.append(
                {
                    "support_id": candidate["support_id"],
                    "evidence_ids": [s["evidence_id"] for s in candidate["spans"]],
                    "supported": check["supported"],
                    "reason": check.get("errors") or check.get("reason"),
                    "probabilities": check.get("probabilities"),
                }
            )
            if check["supported"]:
                return [candidate], {**check, "locator_reexamined": True}
            scored.append((check.get("probabilities", {}).get("entailment", 0), candidate))
        # Joint support may be necessary for a paragraph spanning neighboring
        # complete sentences. This is bounded source checking, not a new RAG.
        ranked = [a for _, a in sorted(scored, key=lambda row: -row[0])[:4]]
        for left, first in enumerate(ranked):
            for second in ranked[left + 1 :]:
                if self._alignment_checks >= self.max_alignment_checks:
                    return None
                self._alignment_checks += 1
                self._total_alignment_checks += 1
                check = self._source_semantic_verdict(text, [first, second])
                if check["supported"]:
                    return [first, second], {**check, "locator_reexamined": True}
        return None

    def _align_claim(self, text, proposed_ids, inventory):
        """Treat model IDs as hints and verify source-local alternatives independently."""

        def assess(anchors):
            from nasa_fire_ai.services.source_definitions import add_source_definitions

            if not hasattr(self, "_document_definition_cache"):
                self._document_definition_cache = {}
            for anchor in anchors:
                add_source_definitions(
                    text, anchor, self.search.registry, self._document_definition_cache
                )
            # Interpret relation semantics before the final source/NLI decision.
            store = getattr(self.search, "store", None)
            audit = audit_relation(text, anchors, store, self.search.registry) if store else {}
            if audit.get("scientific_status") == "ONTOLOGY_INCOMPATIBLE":
                return {
                    **audit,
                    "supported": False,
                    "errors": [
                        audit.get("reason")
                        or "Resolved endpoints violate the approved relation domain or range"
                    ],
                }
            if len(anchors) == 1 and anchors[0].get("deterministic_text") == text:
                from nasa_fire_ai.services.structured_facts import (
                    record_scope_fact,
                    structured_fact,
                )

                renderer = (
                    record_scope_fact
                    if anchors[0].get("projection_kind") == "record_scope"
                    else structured_fact
                )
                fact = (
                    renderer(anchors[0].get("structured_record_id"), store, self.search.registry)
                    if store
                    else None
                )
                if fact and fact["text"] == text:
                    return {
                        "supported": True,
                        **audit,
                        **fact,
                        "scientific_status": "SOURCE_REPRESENTATION_SCOPE"
                        if anchors[0].get("projection_kind") == "record_scope"
                        else "SOURCE_REPORTED_VALUE",
                    }
            return self._source_semantic_verdict(text, anchors, audit)

        # Each proposition receives the configured bounded opportunity to align.
        # Earlier unsupported prose must not starve later independent findings.
        self._alignment_exhausted |= self._alignment_checks >= self.max_alignment_checks
        self._alignment_checks = 0
        from nasa_fire_ai.services.structured_alignment import (
            expand_source_fields,
            record_anchor_allowed,
        )

        expand_source_fields(
            inventory, self.search, getattr(self, "_explicit_record_subjects", None)
        )
        self._active_support_inventory = inventory
        candidates = [
            anchor
            for anchor in inventory.values()
            if record_anchor_allowed(
                anchor,
                self.search,
                getattr(self, "_explicit_record_subjects", None),
                getattr(self, "_requested_investigations", None),
            )
        ]
        from nasa_fire_ai.services.ontology_support import leading_investigation

        store = getattr(self.search, "store", None)
        primary = leading_investigation(text, store) if store is not None else None
        candidates = rank_alignment_candidates(text, candidates, (primary or {}).get("id"))
        permitted = {a["support_id"] for a in candidates}
        hinted = [inventory[i] for i in proposed_ids if i in permitted]
        ordered = list(dict.fromkeys(a["support_id"] for a in hinted + candidates))
        if re.search(
            r"\b(?:table|column|field)s?\b.*\b(?:notes?|definitions?|meaning)\b",
            text,
            re.IGNORECASE,
        ):
            definitions = {
                anchor["support_id"]
                for anchor in candidates
                if anchor.get("definition_scope") == "same_original_table"
            }
            ordered.sort(key=lambda identity: identity not in definitions)
        from nasa_fire_ai.services.document_sections import quoted_section_content

        quoted = quoted_section_content(text)
        for identity in ordered:
            anchor = inventory[identity]
            if anchor.get("epistemic_type") == "documentary_content" and anchor.get(
                "text", ""
            ).strip() in {text.strip(), (quoted or "").strip()}:
                verdict = assess([anchor])
                if verdict["supported"]:
                    return [anchor], {**verdict, "matched_support_ids": [identity]}
        reviews = []
        for identity in ordered[:8]:
            if self._alignment_checks >= self.max_alignment_checks:
                break
            anchor = inventory[identity]
            self._alignment_checks += 1
            self._total_alignment_checks += 1
            verdict = assess([anchor])
            reviews.append(
                {
                    "support_id": identity,
                    "supported": verdict["supported"],
                    "reason": verdict.get("errors") or verdict.get("reason"),
                    "verdict": verdict,
                }
            )
            if verdict["supported"]:
                if (
                    anchor.get("category") == "DOCUMENTARY"
                    and anchor.get("epistemic_type") == "documentary_content"
                    and not verdict.get("deterministic_identity")
                ):
                    localized = self._realign_documentary(text, [anchor], inventory)
                    if localized:
                        localized_anchors, localized_verdict = localized
                        return localized_anchors, {
                            **localized_verdict,
                            "matched_support_ids": [r["support_id"] for r in reviews],
                            "independent_source_localization": True,
                        }
                return [anchor], {
                    **verdict,
                    "matched_support_ids": [r["support_id"] for r in reviews],
                    "locator_reexamined": identity not in proposed_ids,
                }
            window = anchor.get("context_window")
            if window and self._alignment_checks < self.max_alignment_checks:
                contextual = {
                    **anchor,
                    "spans": [{"evidence_id": anchor["spans"][0]["evidence_id"], "text": window}],
                }
                self._alignment_checks += 1
                self._total_alignment_checks += 1
                contextual_verdict = assess([contextual])
                if contextual_verdict["supported"]:
                    return [contextual], {**contextual_verdict, "locator_reexamined": True}
        documentary, examined_documents = [], set()
        for identity in ordered:
            anchor = inventory[identity]
            document = anchor.get("document_id")
            if (
                anchor.get("category") == "DOCUMENTARY"
                and anchor.get("epistemic_type") in {"documentary_content", "source_quotation"}
                and document
                and document not in examined_documents
            ):
                documentary.append(anchor)
                examined_documents.add(document)
                if len(documentary) == 3:
                    break
        store = getattr(self.search, "store", None)
        if store is not None:
            documentary = [
                anchor
                for anchor in documentary
                if audit_relation(text, [anchor], store, self.search.registry).get(
                    "scientific_status"
                )
                != "ONTOLOGY_INCOMPATIBLE"
            ]
        recovered = self._realign_documentary(text, documentary, inventory) if documentary else None
        if recovered:
            anchors, verdict = recovered
            return anchors, {
                **assess(anchors),
                "matched_support_ids": [r["support_id"] for r in reviews],
            }
        # A sentence may faithfully combine dimensions from neighboring
        # passages of one registered document. Keep their document identity
        # together, then run the full verifier on the joint proposition.
        ranked = [inventory[i] for i in ordered[:5]]
        for left, first in enumerate(ranked):
            for second in ranked[left + 1 :]:
                if (
                    not first.get("document_id")
                    or first.get("document_id") != second.get("document_id")
                    or self._alignment_checks >= self.max_alignment_checks
                ):
                    continue
                self._alignment_checks += 1
                self._total_alignment_checks += 1
                verdict = assess([first, second])
                if verdict["supported"]:
                    return [first, second], {
                        **verdict,
                        "matched_support_ids": [r["support_id"] for r in reviews],
                        "locator_reexamined": True,
                    }
        return [], {
            "supported": False,
            "reason": "No verified evidence for proposition",
            "matched_support_ids": [r["support_id"] for r in reviews],
            "alignment_reviews": reviews,
        }

    def _causal_analysis_boundary(self, question, inventory, accepted):
        """Explain the assistant's inference boundary, not a NASA absence claim."""
        causal = r"\b(?:caus\w*|attribut\w*|because|due to)\b"
        if not getattr(self, "_explicit_record_subjects", set()) or not re.search(
            causal, question, re.IGNORECASE
        ):
            return None
        if any(re.search(causal, row.get("text", ""), re.IGNORECASE) for row in accepted):
            return None
        if not any(
            inventory.get(sid, {}).get("projection_verified")
            and inventory.get(sid, {}).get("structured_record_id")
            and inventory.get(sid, {}).get("projection_kind") != "record_scope"
            for row in accepted
            for sid in row.get("support_ids", [])
        ):
            return None
        return "These are recorded source values. I can compare them, but I cannot derive a new causal attribution from the rows alone."

    def _graph_context_candidates(self, question, investigations):
        """Assemble source-validated scientific graph context before generation."""
        from nasa_fire_ai.services.context_assembly import desired_source_roles
        from nasa_fire_ai.services.source_definitions import registered_quotation_fragments

        store = getattr(self.search, "store", None)
        requested = desired_source_roles(question)
        if store is None or not requested:
            return []
        candidates = {}
        for investigation in sorted(investigations):
            for relation in sorted(store.registry.relations):
                for target in sorted(store.relations(investigation, relation)):
                    if requested & set(store.classes(target)):
                        candidates.setdefault(target, investigation)
                        if "SourceReportedFinding" in store.classes(target):
                            for context in store.relations(target, "hasFindingContext"):
                                candidates.setdefault(context, investigation)
        anchors, seen, size = [], set(), 0
        for target, investigation in candidates.items():
            quote = store.payload(target).get("text")
            if not quote or len(quote) > 1800:
                continue
            normalized = " ".join(quote.split())
            # Equal prose from different studies is still distinct evidence.
            if (investigation, normalized) in seen:
                continue
            fragments = registered_quotation_fragments(
                quote, store.evidence(target), self.search.registry, context_id=target
            )
            if not fragments:
                continue
            if len(anchors) >= 6 or size + len(quote) > 6000:
                break
            source = self.search.registry.resolve(fragments[0]["evidence_id"])
            metadata = self.search.registry.source_metadata(source["evidence_id"]) or {}
            anchor = {
                "support_id": "graph-documentary-" + target,
                "text": quote,
                "document_id": source["document_id"],
                "source_id": metadata.get("source_id"),
                "source_title": metadata.get("title"),
                "category": "DOCUMENTARY",
                "epistemic_type": "documentary_content",
                "conditions": [],
                "required_scope": [store.payload(target).get("scope") or "Original source scope"],
                "graph_context_id": target,
                "graph_investigation": investigation,
                "spans": fragments,
            }
            self._attach_scientific_identity(anchor)
            anchors.append(anchor)
            size += len(quote)
            seen.add((investigation, normalized))
        return anchors

    def _graph_source_completion(self, question, inventory, accepted, needs=None):
        """Recover a remaining graph context through the normal claim verifier."""
        from nasa_fire_ai.services.ontology_support import leading_investigation

        if self.entailment is None:
            return []
        unmet = [need for need in (needs or []) if not self._need_is_communicated(need, accepted)]
        if needs is not None and not unmet:
            return []
        proposals = []
        for anchor in self._graph_context_candidates(
            question, getattr(self, "_requested_investigations", set())
        ):
            quote = anchor["text"]
            if needs is not None:
                # Background investigations remain searchable. Automatic repair
                # emits a context only for a still-unmet information need.
                store = getattr(self.search, "store", None)
                relevant = False
                for need in unmet:
                    phrase = need.get("need", "")
                    owner = leading_investigation(phrase, store) if store else None
                    if owner:
                        relevant |= owner["id"] in {
                            anchor.get("graph_investigation"),
                            *anchor.get("scientific_subjects", []),
                        }
                    else:
                        from nasa_fire_ai.services.context_assembly import desired_source_roles

                        if re.search(
                            r"\b(?:each|all)\b", phrase, re.IGNORECASE
                        ) and "Instrument" in desired_source_roles(phrase):
                            relevant |= (
                                ("Instrument" in store.classes(anchor["graph_context_id"]))
                                if store
                                else False
                            )
                        else:
                            relevant |= bool(self.entailment.check(quote, phrase).get("supported"))
                if not relevant:
                    continue
            sentences = list(paragraph_spans(quote))
            if sentences and all(
                any(
                    self.entailment.check(row.get("text", ""), sentence).get("supported")
                    for row in accepted
                )
                for sentence in sentences
            ):
                continue
            inventory[anchor["support_id"]] = anchor
            store = getattr(self.search, "store", None)
            identity = leading_investigation(question, store) if store else None
            label = (
                identity["label"]
                if identity and identity["id"] == anchor["graph_investigation"]
                else (store.payload(anchor["graph_investigation"]).get("title") if store else None)
                or anchor["graph_investigation"]
            )
            proposals.append(
                {
                    "text": f"For {label}, {quote}",
                    "support_ids": [anchor["support_id"]],
                    "repair_of": "coverage-graph-" + anchor["graph_context_id"],
                }
            )
        return proposals

    def _documentary_need_completion(self, needs, inventory, accepted):
        """Route unmet needs to short, section-scoped original quotations.

        Relevance ranking proposes evidence; the normal source verifier must
        still authorize every emitted quotation. Ranking is never coverage.
        """
        import snowballstemmer

        from nasa_fire_ai.services.document_sections import (
            add_section_context,
            continued_source_list,
            section_quotation,
        )
        from nasa_fire_ai.services.ontology_support import investigation_mentions
        from nasa_fire_ai.services.semantic_support import (
            canonical_numeric_text,
            numeric_tokens,
            unstructured_numeric_table,
        )
        from nasa_fire_ai.services.source_definitions import document_definitions

        if getattr(self, "_explicit_record_subjects", set()):
            return []
        stemmer = snowballstemmer.stemmer("english")
        stop = {
            "the",
            "a",
            "an",
            "of",
            "for",
            "in",
            "by",
            "to",
            "and",
            "with",
            "report",
            "reported",
            "source",
        }

        def terms(value):
            return set(stemmer.stemWords(re.findall(r"[a-z][a-z0-9]+", value.casefold()))) - stop

        current_documents = {anchor.get("document_id") for anchor in inventory.values()}
        pool = dict(inventory)
        for document, candidates in getattr(self, "_documentary_reexamination_pool", {}).items():
            if document in current_documents:
                pool.update((anchor["support_id"], anchor) for anchor in candidates)
        eligible = [
            anchor
            for anchor in pool.values()
            if anchor.get("category") == "DOCUMENTARY"
            and anchor.get("epistemic_type") == "documentary_content"
            and not anchor.get("typed_fields")
            and not anchor.get("graph_context_id")
            and 20 <= len(anchor.get("text", "")) <= 900
            and not unstructured_numeric_table(anchor)
        ]
        proposals, used = [], set()
        cache = getattr(self, "_document_section_cache", {})
        definitions = getattr(self, "_document_definition_cache", {})
        for index, need in enumerate(needs):
            if self._need_is_communicated(need, accepted):
                continue
            phrase = need.get("need", "")
            if re.match(r"\s*(?:ensure|avoid|keep|do not|don't)\b", phrase, re.IGNORECASE):
                # Behavioral constraints govern the answer; they are not a
                # request to quote another scientific finding.
                continue
            positive_phrase = re.sub(
                r"\b(?:exclude|excluding|separate from|rather than)\s+[^.;!?]+",
                "",
                phrase,
                flags=re.IGNORECASE,
            )
            qualifications = bool(
                re.search(
                    r"\b(?:qualifications?|limitations?|cautions?|uncertaint\w*|caveats?)\b",
                    positive_phrase,
                    re.IGNORECASE,
                )
            )
            requested_numbers = set(re.findall(r"(?<!\w)\d+(?:\.\d+)?", positive_phrase))
            store = getattr(self.search, "store", None)
            scope_text = phrase + " " + " ".join(need.get("search_terms", []))
            owners = (set(investigation_mentions(scope_text, store)) if store else set()) or set(
                getattr(self, "_requested_investigations", set())
            )
            wanted = terms(positive_phrase)
            ranked = sorted(
                eligible,
                key=lambda anchor: (
                    -int(
                        qualifications
                        and bool(
                            re.search(
                                r"\b(?:uncertain\w*|errors?|assum\w*|limitations?|however|caution\w*)\b",
                                anchor["text"],
                                re.IGNORECASE,
                            )
                        )
                    ),
                    -len(
                        requested_numbers & set(re.findall(r"(?<!\w)\d+(?:\.\d+)?", anchor["text"]))
                    ),
                    -len(wanted & terms(anchor["text"])),
                    len(anchor["text"]),
                ),
            )
            choices = []
            for anchor in ranked[:40]:
                if not self._method_scope_allowed(anchor):
                    continue
                requested_sources = getattr(self, "_requested_document_sources", set())
                if (
                    requested_sources
                    and not owners
                    and anchor.get("source_id") not in requested_sources
                ):
                    continue
                if owners:
                    self._attach_scientific_identity(anchor)
                    explicit_source = anchor.get("source_id") in getattr(
                        self, "_requested_document_sources", set()
                    )
                    if (
                        owners.isdisjoint(anchor.get("scientific_subjects", []))
                        and not explicit_source
                    ):
                        continue
                framed = section_quotation(anchor, self.search.registry, cache)
                qualification_window = qualifications and re.search(
                    r"\b(?:uncertain\w*|errors?|assum\w*|limitations?|however|caution\w*)\b",
                    anchor["text"],
                    re.IGNORECASE,
                )
                if qualification_window or anchor["text"].rstrip().endswith(":"):
                    primary = [s for s in anchor["spans"] if not s.get("scope")]
                    if len(primary) == 1:
                        original = self.search.registry.resolve(primary[0]["evidence_id"]) or {}
                        list_window = continued_source_list(
                            original.get("text", ""), anchor["text"]
                        )
                        window = list_window
                        if not window and qualification_window:
                            window = document_context_window(
                                original.get("text", ""), anchor["text"], limit=900, radius=2
                            )
                        if window:
                            expanded_anchor = {
                                **anchor,
                                "text": window,
                                "spans": [{**primary[0], "text": window}],
                            }
                            expanded_frame = section_quotation(
                                expanded_anchor, self.search.registry, cache
                            )
                            if expanded_frame:
                                anchor, framed = expanded_anchor, expanded_frame
                            elif list_window:
                                # Normative lists retain their independently
                                # checked numbered-method scope even without a
                                # scientific-section quotation frame.
                                anchor, framed = expanded_anchor, None
                if not framed:
                    checked = {**anchor, "spans": list(anchor.get("spans", []))}
                    add_section_context(checked, self.search.registry, cache)
                    if checked.get("source_record_references"):
                        continue
                    primary = [
                        span
                        for span in checked["spans"]
                        if span.get("scope")
                        not in {
                            "section_heading",
                            "source_record_heading",
                            "source_local_name_definition",
                            "source_subject_context",
                        }
                    ]
                    if len(primary) != 1 or anchor["text"] != primary[0]["text"]:
                        continue
                    original = self.search.registry.resolve(primary[0]["evidence_id"]) or {}
                    if primary[0]["text"] not in original.get("text", ""):
                        continue
                    framed = {
                        "text": anchor["text"],
                        "quoted_text": anchor["text"],
                        "anchor": checked,
                    }
                if framed["text"] in used:
                    continue
                document = anchor.get("document_id")
                if document not in definitions:
                    definitions[document] = document_definitions(self.search.registry, document)
                expanded = positive_phrase
                for definition in definitions[document]:
                    expanded = re.sub(
                        r"(?<!\w)" + re.escape(definition["acronym"]) + r"(?!\w)",
                        definition["acronym"] + " " + definition["long_name"],
                        expanded,
                    )
                query_terms = terms(expanded)
                heading_terms = terms(" ".join(framed["anchor"].get("scientific_sections", [])))
                body_terms = terms(framed["quoted_text"])
                overlap = query_terms & (body_terms | heading_terms)
                if len(overlap) < 2 or not query_terms & body_terms:
                    continue
                score = len(query_terms & body_terms) + 3 * len(query_terms & heading_terms)
                # A section introduction discusses an analysis; a printed
                # uncertainty bound supplies its quantitative result. Prefer
                # the latter when requested, retaining the camera/section scope.
                quantitative = bool(
                    re.search(r"\b(?:uncertain\w*|errors?)\b", phrase, re.IGNORECASE)
                    and re.search(r"±|\+\s*/\s*-", framed["quoted_text"])
                )
                comparative = bool(
                    re.search(r"\bcompar\w*\b", phrase, re.IGNORECASE)
                    and re.search(
                        r"\b(?:compared|than|whereas|versus|smaller|larger|higher|lower|ratio)\b",
                        framed["quoted_text"],
                        re.IGNORECASE,
                    )
                )
                quantified_comparison = comparative and bool(
                    numeric_tokens(canonical_numeric_text(framed["quoted_text"]))
                )
                qualifier_evidence = qualifications and bool(
                    re.search(
                        r"\b(?:uncertain\w*|errors?|assum\w*|limitations?|however|caution\w*)\b",
                        framed["quoted_text"],
                        re.IGNORECASE,
                    )
                )
                numeric_focus = len(
                    requested_numbers
                    & set(re.findall(r"(?<!\w)\d+(?:\.\d+)?", framed["quoted_text"]))
                )
                choices.append(
                    (
                        qualifier_evidence,
                        numeric_focus,
                        quantitative or comparative,
                        quantified_comparison,
                        score,
                        -len(framed["quoted_text"]),
                        anchor,
                        framed,
                    )
                )
            if choices:
                *_, anchor, framed = max(choices, key=lambda row: row[:-2])
                anchor.update(framed["anchor"])
                inventory[anchor["support_id"]] = anchor
                used.add(framed["text"])
                proposals.append(
                    {
                        "text": framed["text"],
                        "support_ids": [anchor["support_id"]],
                        "repair_of": f"coverage-documentary-{index}",
                    }
                )
            if len(proposals) >= 4:
                break
        return proposals

    def _source_restatements(self, rejected, inventory, accepted, question="", needs=None):
        """Recover exact, relevant source sentences after unsuccessful paraphrase repair.

        These are new documentary restatements, never acceptance of rejected wording.
        Routing is lexical; scientific support is checked again against original spans.
        """
        from nasa_fire_ai.services.search import words

        rejected = [
            failure
            for failure in rejected
            if failure.get("kind") != "coverage_gap"
            and failure.get("feedback", {}).get("matched_support_ids")
        ]
        if not rejected:
            return []
        table_definition_request = bool(
            re.search(
                r"\b(?:tables?|columns?|entries|entry|rows?|notes)\b", question, re.IGNORECASE
            )
            and any(
                anchor.get("definition_scope") == "same_original_table"
                for anchor in inventory.values()
            )
        )
        if needs and not table_definition_request:
            targeted = self._documentary_need_completion(needs, inventory, accepted)
            if targeted:
                return targeted

        used = {" ".join(row.get("text", "").split()) for row in accepted}
        from nasa_fire_ai.services.document_sections import TEST

        requested_methods = set(TEST.findall(question)) & {
            label for anchor in inventory.values() for label in anchor.get("method_references", [])
        }
        chosen, size = [], 0
        for failure in rejected:
            proposal = failure.get("proposal", {})
            text = proposal.get("text", "")
            if (
                not text
                or failure.get("kind") == "coverage_gap"
                or not failure.get("feedback", {}).get("matched_support_ids")
            ):
                continue
            hints = proposal.get("support_ids", []) or failure.get("feedback", {}).get(
                "matched_support_ids", []
            )
            documents = {inventory[key].get("document_id") for key in hints if key in inventory}
            if not documents:
                continue
            terms = words(text) - {
                "report",
                "source",
                "documentation",
                "describes",
                "states",
                "provided",
                "the",
                "and",
                "that",
                "what",
                "from",
                "with",
                "were",
                "this",
                "these",
            }
            from nasa_fire_ai.services.ontology_support import leading_investigation

            store = getattr(self.search, "store", None)
            subject = leading_investigation(text, store) if store is not None else None
            candidates = []
            explicit = getattr(self, "_explicit_record_subjects", set())
            for anchor in inventory.values():
                from nasa_fire_ai.services.structured_alignment import record_anchor_allowed

                if not record_anchor_allowed(
                    anchor, self.search, explicit, getattr(self, "_requested_investigations", None)
                ):
                    continue
                if (
                    requested_methods
                    and not anchor.get("structured_record_id")
                    and requested_methods.isdisjoint(anchor.get("method_references", []))
                ):
                    continue
                requested = getattr(self, "_requested_investigations", set())
                source_scope = getattr(self.search, "source_scopes", {}).get(
                    anchor.get("source_id"), set()
                )
                if requested and source_scope and requested.isdisjoint(source_scope):
                    continue
                # Automatic quotation repair of a record question needs a
                # positive source association. An unscoped report that shares
                # material/condition words cannot replace that record's facts.
                if (
                    explicit
                    and requested
                    and not requested_methods
                    and not anchor.get("structured_record_id")
                    and requested.isdisjoint(
                        set(source_scope) | set(anchor.get("scientific_subjects", []))
                    )
                ):
                    continue
                if subject and subject["id"] not in anchor.get("scientific_subjects", []):
                    labels = [
                        subject["id"],
                        *store.registry.entity_mentions.get(subject["id"], {}).get("aliases", []),
                    ]
                    if not any(
                        re.search(
                            r"(?<!\w)" + re.escape(label) + r"(?!\w)",
                            anchor.get("text", ""),
                            re.IGNORECASE,
                        )
                        for label in labels
                        if label
                    ):
                        continue
                if not (
                    anchor.get("deterministic_text")
                    or (
                        anchor.get("category") == "DOCUMENTARY"
                        and anchor.get("epistemic_type") == "documentary_content"
                    )
                ):
                    continue
                if anchor.get("document_id") not in documents:
                    continue
                if explicit and anchor.get("structured_record_id"):
                    record = self.search.store.payload(anchor["structured_record_id"])
                    record_subject = (
                        anchor["structured_record_id"]
                        if anchor.get("projection_kind") == "record_scope"
                        else record.get("subject")
                    )
                    if (
                        record_subject not in explicit
                        and record.get("qualifiers", {}).get("scientific_role")
                        != "source_field_definition"
                    ):
                        continue
                if re.match(r"^(?:It|Its|They|Their|This|These)\b", anchor.get("text", "")):
                    continue
                candidates.append(anchor)
            candidates.sort(
                key=lambda anchor: (-len(terms & words(anchor["text"])), len(anchor["text"]))
            )

            def normalized(value):
                return " ".join(re.findall(r"[a-z0-9]+", value.lower()))

            wanted = normalized(text)
            from nasa_fire_ai.services.semantic_support import aligned_properties

            definitions = getattr(getattr(self.search, "store", None), "registry", None)
            definitions = definitions.properties if definitions else {}
            properties = aligned_properties(text, definitions)
            eligible = [
                anchor
                for anchor in candidates
                if anchor.get("structured_record_id")
                and (
                    self.search.store.payload(anchor["structured_record_id"]).get("property_id")
                    in properties
                    or (
                        self.search.store.payload(anchor["structured_record_id"])
                        .get("qualifiers", {})
                        .get("scientific_role")
                        == "source_field_definition"
                        and properties & aligned_properties(anchor["text"], definitions)
                    )
                )
            ]
            selected_properties = set()
            # A documentary word that is also a table header must not force an
            # empty typed-field route. Prefer a discriminating source sentence,
            # then give the next failed proposition its own repair opportunity.
            ranked = rank_alignment_candidates(text, candidates)
            if requested_methods:
                ranked.sort(
                    key=lambda anchor: (
                        not bool(requested_methods & set(anchor.get("method_references", [])))
                    )
                )
            pool = eligible if eligible else ranked[:3]
            for anchor in pool:
                sentence = anchor.get("deterministic_text") or anchor["text"]
                from nasa_fire_ai.services.document_sections import section_quotation

                framed = section_quotation(
                    anchor, self.search.registry, getattr(self, "_document_section_cache", {})
                )
                if framed and not anchor.get("deterministic_text"):
                    anchor.update(framed["anchor"])
                    sentence = framed["text"]
                source_subject = subject
                if not source_subject:
                    scoped = set(anchor.get("scientific_subjects", [])) & set(
                        getattr(self, "_requested_investigations", set())
                    )
                    if len(scoped) == 1:
                        sid = next(iter(scoped))
                        source_subject = {"id": sid, "label": sid}
                if (
                    source_subject
                    and not framed
                    and not anchor.get("deterministic_text")
                    and not leading_investigation(sentence, store)
                ):
                    sentence = f"For {source_subject['label']}, {sentence}"
                from nasa_fire_ai.services.context_assembly import desired_source_roles

                role_match = bool(desired_source_roles(text) & set(anchor.get("source_roles", [])))
                if " ".join(sentence.split()) in used or len(terms & words(sentence)) < (
                    1
                    if anchor.get("deterministic_text")
                    else 2
                    if role_match and source_subject
                    else 3
                ):
                    continue
                record = (
                    self.search.store.payload(anchor["structured_record_id"])
                    if anchor.get("structured_record_id")
                    else {}
                )
                if record and anchor.get("deterministic_text"):
                    from nasa_fire_ai.services.structured_alignment import field_is_communicated
                    from nasa_fire_ai.services.structured_facts import structured_fact

                    fact = structured_fact(
                        anchor["structured_record_id"], store, self.search.registry
                    )
                    if fact and field_is_communicated(
                        fact, record, accepted, definitions, self.entailment
                    ):
                        continue
                context = record.get("qualifiers", {}).get("context")
                phases = {
                    phase
                    for phase in ("initial", "final")
                    if re.search(r"\b" + phase + r"\b", wanted)
                }
                if phases and context in {"initial", "final"} and context not in phases:
                    continue
                signature = (record.get("subject"), record.get("property_id"), context)
                if eligible and signature in selected_properties:
                    continue
                if size + len(sentence) > 6000 or len(chosen) >= 12:
                    return chosen
                chosen.append(
                    {
                        "text": sentence,
                        "support_ids": [anchor["support_id"]],
                        "repair_of": failure["statement_id"],
                    }
                )
                used.add(" ".join(sentence.split()))
                selected_properties.add(signature)
                size += len(sentence)
                if not eligible:
                    break
        return chosen

    def _accept_segments(self, segments, by_id, trace, citations, citation_numbers):
        accepted, rejected, accepted_parents = [], [], []
        live_numbers = {c["number"] for c in citations}
        for key in list(citation_numbers):
            if citation_numbers[key] not in live_numbers:
                del citation_numbers[key]
        if not isinstance(segments, list):
            raise ProviderFailure("Invalid explanation")
        from nasa_fire_ai.services.structured_alignment import expand_source_fields

        # Source links are typed original values, available before reference
        # rejection rather than only after a later numerical claim is checked.
        expand_source_fields(by_id, self.search, getattr(self, "_explicit_record_subjects", None))
        statements = []
        previous_subject = None
        for parent_index, segment in enumerate(segments):
            if not isinstance(segment, dict):
                continue
            text = segment.get("text")
            if isinstance(text, str):
                declared = segment.get("support_ids")
                known_inline = []
                bad_inline = []
                for marker in re.findall(r"\[([^\[\]]+)\]", text):
                    if marker in by_id:
                        known_inline.append(marker)
                        text = text.replace("[" + marker + "]", "")
                    elif re.search(r"[A-Za-z]", marker):
                        declared_ids = declared if isinstance(declared, list) else []
                        literal = any(
                            "[" + marker + "]" in span["text"]
                            for identity in declared_ids
                            if isinstance(identity, str) and identity in by_id
                            for span in by_id[identity]["spans"]
                        )
                        if not literal:
                            bad_inline.append(marker)
                if isinstance(declared, list) and all(isinstance(i, str) for i in declared):
                    segment = {
                        **segment,
                        "support_ids": list(dict.fromkeys(declared + known_inline)),
                        "inline_support_ids": known_inline,
                        "unknown_inline_support_ids": bad_inline,
                    }
            exact_field_projection = isinstance(text, str) and any(
                anchor.get("deterministic_text") == text for anchor in by_id.values()
            )
            # A backend-recovered original paragraph supplies its own local
            # antecedents. Splitting it and substituting the investigation for
            # "It" can change a report, camera or apparatus into the wrong entity.
            original_graph_paragraph = isinstance(text, str) and any(
                anchor.get("graph_context_id")
                and any(
                    " ".join(text.split())
                    == " ".join((f"For {sid}, " + anchor.get("text", "")).split())
                    for sid in [
                        *anchor.get("scientific_subjects", []),
                        *anchor.get("source_aliases", []),
                    ]
                )
                for anchor in by_id.values()
            )
            from nasa_fire_ai.services.document_sections import quoted_section_content

            # Keep a proposed quotation intact. Its body and printed section
            # still require independent source location and verification below.
            original_section_quotation = (
                isinstance(text, str) and quoted_section_content(text) is not None
            )
            from nasa_fire_ai.ingestion.abbreviations import split_by_view

            parts = (
                split_by_view(r"(?<!\b[A-Z]\.)(?<=[.!?])\s+(?=[A-Z])", text)
                if isinstance(text, str)
                and not exact_field_projection
                and not original_graph_paragraph
                and not original_section_quotation
                else [text]
            )
            from nasa_fire_ai.services.ontology_support import leading_investigation

            parent_subject = None
            if isinstance(text, str) and re.match(
                r"^(?:It|Its|They|Their|This|These|The (?:(?:same|previous|latter|former) )?(?:[A-Za-z]*\d[\w.-]*\s+)?(?:record|study|experiment|test|sample|session|entry|table|row))\b",
                text,
            ):
                parent_subject = previous_subject
            store = getattr(self.search, "store", None)
            for part in parts:
                if isinstance(part, str) and store is not None:
                    explicit_subject = leading_investigation(part, store)
                    if explicit_subject:
                        parent_subject = explicit_subject
                # A descriptive apposition often combines a documented fuel
                # and its separately documented sample geometry. Verify both
                # propositions; retain either one if the other fails.
                description = (
                    re.fullmatch(
                        r"(.+?) uses (.+?), (?:specifically )?described (?:elsewhere )?as (.+?)([.!?]?)",
                        part,
                        re.IGNORECASE,
                    )
                    if isinstance(part, str)
                    else None
                )
                if description:
                    subject = description[1].rsplit(",", 1)[-1].strip()
                    if subject and len(subject.split()) <= 8:
                        parts_to_check = [
                            f"{subject} uses {description[2]}.",
                            f"{subject} uses {description[3]}.",
                        ]
                    else:
                        parts_to_check = [part]
                else:
                    parts_to_check = [part]
                statements.extend(
                    {
                        **segment,
                        "text": clause,
                        "original_text": part,
                        "original_parent_text": segment.get("text"),
                        "parent_segment": parent_index,
                        "contextual_subject": parent_subject,
                        "reference_predecessor": len(statements) - 1
                        if isinstance(part, str)
                        and re.match(
                            r"^(?:It|Its|They|Their|These|This(?!\s+(?:report|document)\b))\b",
                            part,
                        )
                        and not original_graph_paragraph
                        and not original_section_quotation
                        and not exact_field_projection
                        else None,
                    }
                    for clause in parts_to_check
                )
            if parent_subject:
                previous_subject = parent_subject
        referents = {}
        verified_statement_indices = set()
        for statement_index, segment in enumerate(statements):
            checkpoint("verification")
            if not isinstance(segment, dict):
                continue
            anchors = []
            text, ids = segment.get("text"), segment.get("support_ids")
            if isinstance(text, str):
                text = re.sub(r"\[\d+\]", "", text).strip()
                context = segment.get("contextual_subject")
                pronoun = re.match(r"^(It|Its)\b", text)
                referent = (context or {}).get("label") or referents.get(
                    segment.get("parent_segment")
                )
                if pronoun and referent:
                    replacement = referent + ("'s" if pronoun[1] == "Its" else "")
                    text = replacement + text[pronoun.end() :]
                elif context and store is not None and not leading_investigation(text, store):
                    text = f"For {context['label']}, {text}"
            if not isinstance(text, str) or not text.strip():
                check = {"supported": False, "reason": "Empty scientific statement"}
            elif (
                segment.get("reference_predecessor") is not None
                and segment["reference_predecessor"] not in verified_statement_indices
            ):
                check = {
                    "supported": False,
                    "reason": "Scientific reference lost its antecedent from the verified explanation",
                }
            elif (
                trace.get("verification_stage") != "fallback"
                and re.match(r"^(?:It|Its|They|Their|This|These)\b", text)
                and not (
                    re.match(r"^This (?:report|document)\b", text)
                    and any(
                        " ".join(text.split()) == " ".join(span["text"].split())
                        for sid in (ids or [])
                        if sid in by_id
                        for span in by_id[sid].get("spans", [])
                    )
                )
            ):
                check = {
                    "supported": False,
                    "reason": "Scientific subject must be explicit before source attribution",
                }
            elif segment.get("unknown_inline_support_ids"):
                check = {"supported": False, "reason": "Unresolvable inline source reference"}
            elif trace.get("verification_stage", "").startswith("repair-") and segment.get(
                "repair_of"
            ) not in trace.get("repair_targets", []):
                check = {
                    "supported": False,
                    "reason": "Repair lacks a valid rejected-statement identity",
                }
            elif re.search(r"https?://|\]\(", text):
                from nasa_fire_ai.services.structured_facts import projection_fact

                original_fields = [
                    a
                    for a in by_id.values()
                    if a.get("deterministic_text") == text and projection_fact(a, self.search)
                ]
                if original_fields:
                    anchors, check = self._align_claim(
                        text, [original_fields[0]["support_id"]], by_id
                    )
                else:
                    # A publication URL can itself be an original typed table
                    # value. It is not a model-created citation. Check its exact
                    # source field first, then independently verify the whole
                    # proposition and the finally selected supporting spans.
                    urls = {url.rstrip(".,;)") for url in re.findall(r"https?://[^\s<>]+", text)}
                    registered = set()
                    for anchor in by_id.values():
                        proof = projection_fact(anchor, self.search)
                        if not proof:
                            continue
                        record = self.search.store.payload(anchor["structured_record_id"])
                        if (
                            record.get("qualifiers", {}).get("scientific_role")
                            == "publication_figure_reference"
                        ):
                            raw = str(
                                record.get("qualifiers", {}).get("original_value") or ""
                            ).strip()
                            if raw in urls:
                                registered.add(raw)
                    if urls and urls <= registered and not re.search(r"\]\(", text):
                        anchors, check = self._align_claim(text, ids or [], by_id)
                        supported_urls = {
                            url.rstrip(".,;)")
                            for anchor in anchors
                            for span in anchor["spans"]
                            for url in re.findall(r"https?://[^\s<>]+", span["text"])
                        }
                        if not urls <= supported_urls:
                            check = {
                                "supported": False,
                                "reason": "Publication reference is absent from the verified source span",
                            }
                    else:
                        check = {
                            "supported": False,
                            "reason": "Model-authored references not permitted",
                        }
            else:
                proposed = [i for i in (ids or []) if isinstance(i, str) and i in by_id]
                try:
                    anchors, check = self._align_claim(text, proposed, by_id)
                except Exception as error:  # noqa: BLE001 - a verifier outage cannot authorize or erase other claims
                    check = {
                        "supported": False,
                        "reason": "Semantic verification unavailable",
                        "error_type": type(error).__name__,
                    }
            if check.get("selected_support_ids"):
                anchors = [
                    a for a in anchors if a.get("support_id") in check["selected_support_ids"]
                ]
            if not check["supported"] and anchors:
                try:
                    aligned = self._realign_documentary(text, anchors, by_id)
                    if aligned:
                        anchors, check = aligned
                except Exception as error:  # noqa: BLE001 - preserve the original failed verdict
                    check["locator_reexamination_error"] = type(error).__name__
            selected_supports = check.get("selected_support_ids")
            if check.get("supported") and selected_supports:
                anchors = [
                    anchor for anchor in anchors if anchor["support_id"] in selected_supports
                ]
            # Comparison prose must retain the experimental owner even when
            # the model omits it. Scope comes from independently verified
            # source associations; the expanded proposition is verified again.
            if (
                check.get("supported")
                and store is not None
                and len(getattr(self, "_requested_investigations", set())) > 1
                and not segment.get("contextual_subject")
                and not leading_investigation(text, store)
            ):
                from nasa_fire_ai.services.ontology_support import investigation_mentions

                owners = {
                    subject
                    for anchor in anchors
                    for subject in anchor.get("scientific_subjects", [])
                }
                if len(owners) == 1 and not investigation_mentions(text, store):
                    owner = next(iter(owners))
                    aliases = store.registry.entity_mentions.get(owner, {}).get("aliases", [])
                    label = min((a for a in aliases if a), key=len, default=owner)
                    scoped_text = f"For {label}, {text}"
                    scoped_check = self._source_semantic_verdict(scoped_text, anchors)
                    if scoped_check.get("supported"):
                        text, check = scoped_text, scoped_check
                        segment["contextual_subject"] = {"id": owner, "label": label}
            known_supports = {anchor["support_id"] for anchor in trace.get("support_inventory", [])}
            trace.setdefault("support_inventory", []).extend(
                anchor
                for anchor in [*by_id.values(), *anchors]
                if anchor["support_id"] not in known_supports
            )
            trace["verification"].append(
                {
                    "statement_id": f"{trace.get('verification_stage', 'draft')}-{statement_index}",
                    "stage": trace.get("verification_stage", "draft"),
                    "parent_segment": segment.get("parent_segment"),
                    "original_parent_text": segment.get("original_parent_text"),
                    "repair_of": segment.get("repair_of"),
                    "inline_support_ids": segment.get("inline_support_ids", []),
                    "proposed_support_ids": ids,
                    "support_ids": [a["support_id"] for a in anchors],
                    "text": text,
                    "original_text": segment.get("original_text"),
                    "contextual_subject": segment.get("contextual_subject"),
                    "reference_predecessor": segment.get("reference_predecessor"),
                    **check,
                }
            )
            if not check["supported"]:
                rejected.append(
                    {
                        "statement_id": f"{trace.get('verification_stage', 'draft')}-{statement_index}",
                        "proposal": {**segment, "text": text},
                        "feedback": check,
                    }
                )
                continue
            entities = check.get("resolved_entities", {})
            if len(entities) == 1 and isinstance(text, str):
                entity = next(iter(entities))
                store = getattr(self.search, "store", None)
                aliases = (
                    [entity, *store.registry.entity_mentions.get(entity, {}).get("aliases", [])]
                    if store is not None
                    else []
                )
                matching = [
                    label
                    for label in aliases
                    if label
                    and re.search(r"(?<!\w)" + re.escape(label) + r"(?!\w)", text, re.IGNORECASE)
                ]
                if matching:
                    referents[segment.get("parent_segment")] = max(matching, key=len)
            if all(a.get("epistemic_type") == "catalogue_metadata" for a in anchors):
                text = (
                    "Exploratory source: "
                    + text.strip()
                    + " Its scientific applicability remains unverified."
                )
            trace.setdefault("accepted_statements", []).append(
                {
                    "text": text,
                    "repair_of": segment.get("repair_of"),
                    "stage": trace.get("verification_stage", "draft"),
                    "support_ids": [a["support_id"] for a in anchors],
                    "evidence_ids": sorted({s["evidence_id"] for a in anchors for s in a["spans"]}),
                    "source_ids": sorted(
                        {a.get("source_id") for a in anchors if a.get("source_id")}
                    ),
                    "epistemic_types": sorted(
                        {a.get("epistemic_type", "unknown") for a in anchors}
                    ),
                }
            )
            markers = []
            for anchor in anchors:
                for span in anchor["spans"]:
                    eid = span["evidence_id"]
                    if eid not in citation_numbers:
                        source = self.search._evidence(eid)
                        location = source.get("structured_location") or {}
                        group_key = (
                            "source",
                            source.get("source", {}).get("source_id"),
                            source.get("page"),
                            source.get("checksum"),
                            location.get("row_ordinal"),
                            location.get("json_pointer"),
                        )
                        if group_key in citation_numbers:
                            citation_numbers[eid] = citation_numbers[group_key]
                        else:
                            citation_numbers[eid] = (
                                max((c["number"] for c in citations), default=0) + 1
                            )
                            citation_numbers[group_key] = citation_numbers[eid]
                            citations.append(
                                {
                                    "number": citation_numbers[eid],
                                    **public_evidence(source),
                                    "evidence_ids": [],
                                    "supporting_passage": span["text"],
                                    "supports": [],
                                    "conditions": anchor["conditions"],
                                    "limitations": anchor.get("required_scope", [])
                                    + anchor.get("comparison_limits", []),
                                    "category": anchor["category"],
                                }
                            )
                    citation = next(c for c in citations if c["number"] == citation_numbers[eid])
                    if eid not in citation["evidence_ids"]:
                        citation["evidence_ids"].append(eid)
                    support = {
                        "evidence_id": eid,
                        "claim_text": text,
                        "support_id": anchor["support_id"],
                        "category": anchor["category"],
                        "passage": span["text"],
                        "support_role": span.get("scope", "primary_source_passage"),
                        "conditions": anchor["conditions"],
                        "limitations": anchor.get("required_scope", [])
                        + anchor.get("comparison_limits", []),
                    }
                    if support not in citation["supports"]:
                        citation["supports"].append(support)
                    marker = f"[{citation_numbers[eid]}]"
                    if marker not in markers:
                        markers.append(marker)
            accepted.append(text.strip() + " " + "".join(markers))
            verified_statement_indices.add(statement_index)
            accepted_parents.append(segment.get("parent_segment"))
        paragraphs = []
        last_parent = None
        for parent, text in zip(accepted_parents, accepted):
            if paragraphs and parent == last_parent:
                paragraphs[-1] += " " + text
            else:
                paragraphs.append(text)
            last_parent = parent
        return paragraphs, rejected

    def _repair_context(self, rejected, inventory, question):
        """Reuse need-aware allocation for focused repairs; preserve original anchors."""
        proposed_ids = {
            i
            for r in rejected
            for i in (r["proposal"].get("support_ids") or [])
            if isinstance(i, str)
        }
        required = [a for a in inventory if a["support_id"] in proposed_ids]
        needs = information_needs(
            question,
            [{"need": r["proposal"].get("text") or question, "search_terms": []} for r in rejected],
        )
        # Copy routing annotations: repair selection must not rewrite the receipt
        # of what the initial generator actually received.
        candidates, _ = allocate_context(
            [dict(a) for a in inventory], question, needs, self.source_characters
        )
        seen = {a["support_id"] for a in required}
        return required + [a for a in candidates if a["support_id"] not in seen]

    def _deduplicate_answer(self, paragraphs, trace):
        """Omit redundant presentation only after both statements passed fidelity checks."""
        from nasa_fire_ai.services.search import words
        from nasa_fire_ai.services.semantic_support import numeric_tokens

        kept, checks = [], 0
        omissions = []

        def literal_view(text):
            text = re.sub(r"\[\d+\]", "", text).strip()
            store = getattr(self.search, "store", None)
            if store is not None and getattr(
                getattr(store, "registry", None), "entity_mentions", None
            ):
                from nasa_fire_ai.services.ontology_support import leading_investigation

                subject = leading_investigation(text, store)
                if subject:
                    text = re.sub(
                        r"^For\s+" + re.escape(subject["label"]) + r",\s*",
                        "",
                        text,
                        flags=re.IGNORECASE,
                    )
            return " ".join(re.sub(r"(?<=[a-z])-\s*\n\s*(?=[a-z])", "-", text).split())

        def literal_scope(text):
            inventory = {a["support_id"]: a for a in trace.get("support_inventory", [])}
            result = set()
            for statement in trace.get("accepted_statements", []):
                if statement.get("text") not in text:
                    continue
                for sid in statement.get("support_ids", []):
                    anchor = inventory.get(sid, {})
                    owners = tuple(sorted(anchor.get("scientific_subjects", [])))
                    evidence = tuple(
                        sorted(
                            {
                                span["evidence_id"]
                                for span in anchor.get("spans", [])
                                if span.get("scope")
                                not in {
                                    "section_heading",
                                    "source_local_name_definition",
                                    "source_subject_context",
                                }
                            }
                        )
                    )
                    if not owners or not evidence or not anchor.get("document_id"):
                        return set()
                    result.add(
                        (
                            anchor["document_id"],
                            anchor.get("structured_record_id"),
                            owners,
                            evidence,
                        )
                    )
            return result

        def scope(text):
            inventory = {a["support_id"]: a for a in trace.get("support_inventory", [])}
            result = set()
            for statement in trace.get("accepted_statements", []):
                if statement.get("text") not in text:
                    continue
                for sid in statement.get("support_ids", []):
                    anchor = inventory.get(sid, {})
                    result.add((anchor.get("document_id"), anchor.get("structured_record_id")))
            return result

        def typed_scope(text):
            store = getattr(getattr(self, "search", None), "store", None)
            if not store:
                return set()
            inventory = {a["support_id"]: a for a in trace.get("support_inventory", [])}
            result = set()
            from nasa_fire_ai.services.semantic_support import aligned_properties

            definitions = getattr(getattr(store, "registry", None), "properties", {})
            explicit_properties = aligned_properties(text, definitions)
            for statement in trace.get("accepted_statements", []):
                if statement.get("text") not in text:
                    continue
                for sid in statement.get("support_ids", []):
                    rid = inventory.get(sid, {}).get("structured_record_id")
                    record = store.payload(rid) if rid else {}
                    if record.get("subject") and record.get("property_id"):
                        for pid in explicit_properties or {record["property_id"]}:
                            result.add((record["subject"], pid))
            return result

        for paragraph in paragraphs:
            plain = re.sub(r"\[\d+\]", "", paragraph).strip()
            duplicate = None
            replaced = []
            for previous in kept:
                old = re.sub(r"\[\d+\]", "", previous).strip()
                # Exact complete source prose, with independently grounded
                # attribution aliases removed, can subsume shorter repeated
                # prose. Distinct studies, records and original pages remain
                # separate even when their wording happens to coincide.
                if literal_scope(plain) and literal_scope(plain) == literal_scope(old):
                    current_literal, old_literal = literal_view(plain), literal_view(old)
                    if current_literal and current_literal in old_literal:
                        duplicate = previous
                        break
                    if old_literal and old_literal in current_literal:
                        replaced.append(previous)
                        continue
                # Equivalent wording does not merge different study records or
                # before/after observations, even when their values coincide.
                phases = lambda text: set(
                    re.findall(r"\b(?:initial|final|before|after)\b", text.lower())
                )
                # An earlier compound statement may already communicate this
                # atomic field. Require the same typed record/property plus
                # phase and numerical containment before one-way entailment.
                if (
                    self.entailment is not None
                    and checks < self.max_redundancy_checks
                    and typed_scope(plain)
                    and typed_scope(plain) <= typed_scope(old)
                    and phases(plain) <= phases(old)
                    and numeric_tokens(plain) <= numeric_tokens(old)
                ):
                    checks += 1
                    if self.entailment.check(old, plain)["supported"]:
                        duplicate = previous
                        break
                if (
                    phases(plain) != phases(old)
                    or scope(plain) != scope(old)
                    or typed_scope(plain) != typed_scope(old)
                ):
                    continue
                if plain == old:
                    duplicate = previous
                    break
                a, b = words(plain), words(old)
                if (
                    self.entailment is None
                    or checks >= self.max_redundancy_checks
                    or numeric_tokens(plain) != numeric_tokens(old)
                    or len(a & b) / max(1, len(a | b)) < 0.55
                ):
                    continue
                checks += 1
                if (
                    self.entailment.check(old, plain)["supported"]
                    and self.entailment.check(plain, old)["supported"]
                ):
                    duplicate = previous
                    break
            if duplicate is None:
                for previous in replaced:
                    kept.remove(previous)
                    omissions.append(
                        {
                            "text": previous,
                            "represented_by": paragraph,
                            "reason": "source_scoped_literal_containment",
                        }
                    )
                kept.append(paragraph)
            else:
                omissions.append(
                    {
                        "text": paragraph,
                        "represented_by": duplicate,
                        "reason": "source_scoped_literal_containment"
                        if literal_scope(plain)
                        and literal_scope(plain) == literal_scope(duplicate)
                        and literal_view(plain) in literal_view(duplicate)
                        else "verified_semantic_redundancy",
                    }
                )
        trace["redundancy_review"] = {"checks": checks, "omissions": omissions}
        return kept

    def _need_is_communicated(self, need, statements):
        """Assess need coverage from emitted proposition text, not source IDs.

        This is deliberately diagnostic: a cited anchor is only a candidate
        until a final statement expresses the requested need.  Entailment is
        used when provisioned. Without semantic verification, need coverage remains
        unconfirmed; lexical overlap cannot establish communicated information.
        """
        phrase = str(need.get("need") or "").strip()
        if not phrase:
            return False
        # A noun-phrase need may not be an NLI hypothesis. Resolve only explicitly
        # named curated fields, and test the emitted text against their complete
        # source facts. Merely exposing the row or citing it is insufficient.
        inventory = getattr(self, "_active_support_inventory", {})
        store = getattr(getattr(self, "search", None), "store", None)
        subjects = getattr(self, "_explicit_record_subjects", set())
        if (
            store
            and self.entailment
            and re.search(r"\b(?:each|all)\b", phrase, re.IGNORECASE)
            and re.search(r"\b(?:instruments?|diagnostics?|methods?)\b", phrase, re.IGNORECASE)
        ):
            from nasa_fire_ai.services.context_assembly import desired_source_roles

            owners = getattr(self, "_requested_investigations", set())
            if owners and "Instrument" in desired_source_roles(phrase):
                contexts = [
                    a
                    for a in self._graph_context_candidates(phrase, owners)
                    if "Instrument" in store.classes(a["graph_context_id"])
                ]
                if contexts:
                    expected = {
                        rid for owner in owners for rid in store.relations(owner, "usesInstrument")
                    }
                    if expected - {a["graph_context_id"] for a in contexts}:
                        return False
                    for context in contexts:
                        rid = context["graph_context_id"]
                        title = store.payload(rid).get("title", "")
                        aligned = [
                            row
                            for row in statements
                            if any(
                                inventory.get(sid, {}).get("graph_context_id") == rid
                                for sid in row.get("support_ids", [])
                            )
                            or (title and title.casefold() in row.get("text", "").casefold())
                        ]
                        if not aligned:
                            return False
                        clauses = [
                            sentence
                            for sentence in paragraph_spans(context["text"])
                            if re.search(
                                r"\b(?:measur\w*|imag(?:e|es|ing)|record\w*|detect\w*|"
                                r"monitor\w*|observ\w*|quantif\w*|overview)\b",
                                sentence,
                                re.IGNORECASE,
                            )
                        ] or [context["text"]]
                        for clause in clauses:
                            normalized = " ".join(clause.split())
                            if not any(
                                normalized in " ".join(row.get("text", "").split())
                                or self.entailment.check(row.get("text", ""), clause).get(
                                    "supported"
                                )
                                for row in aligned
                            ):
                                return False
                    return True
        if (
            store
            and subjects
            and self.entailment
            and not re.search(
                r"\b(?:why|cause|compare|comparison|difference|whether|interpret|uncertain|measured|observed)\b",
                phrase,
                re.IGNORECASE,
            )
        ):
            from nasa_fire_ai.services.structured_facts import structured_fact

            normalized = lambda value: " ".join(re.findall(r"[a-z0-9]+", value.lower()))
            wanted = normalized(phrase)
            from nasa_fire_ai.services.structured_alignment import (
                field_is_communicated,
                field_property_id,
                record_need_text,
                route_need_properties,
                source_field_roles,
            )

            available = {
                field_property_id(store.payload(anchor["structured_record_id"]))
                for anchor in inventory.values()
                if anchor.get("structured_record_id")
                and store.payload(anchor["structured_record_id"]).get("subject") in subjects
            }
            properties = route_need_properties(
                record_need_text(phrase, store, subjects),
                store.registry.properties,
                field_roles=source_field_roles(self.search),
                available_properties=available,
            )
            facts = {}
            phases = {
                phase for phase in ("initial", "final") if re.search(r"\b" + phase + r"\b", wanted)
            }
            for anchor in inventory.values():
                rid = anchor.get("structured_record_id")
                if not rid:
                    continue
                record = store.payload(rid)
                context = record.get("qualifiers", {}).get("context")
                if (
                    record.get("subject") not in subjects
                    or field_property_id(record) not in properties
                ):
                    continue
                if phases and context in {"initial", "final"} and context not in phases:
                    continue
                fact = structured_fact(rid, store, self.search.registry)
                if fact:
                    facts[rid] = fact
            if facts and properties <= {field_property_id(store.payload(rid)) for rid in facts}:
                try:
                    return all(
                        field_is_communicated(
                            fact,
                            store.payload(rid),
                            statements,
                            store.registry.properties,
                            self.entailment,
                        )
                        for rid, fact in facts.items()
                    )
                except (KeyError, RuntimeError, ValueError):
                    return False
        for statement in statements:
            text = str(statement.get("text") or "")
            if self.entailment is not None:
                try:
                    if self.entailment.check(text, phrase).get("supported"):
                        return True
                except (KeyError, RuntimeError, ValueError):
                    pass
        return False

    def candidates(self, conversation_id, offset=0, limit=20):
        self._history(
            ChatRequest(message="candidate lookup", conversation_id=conversation_id),
            str(conversation_id),
        )
        rows = self.retrieved.get(str(conversation_id), [])
        return {
            "items": rows[offset : offset + limit],
            "total": len(rows),
            "offset": offset,
            "limit": limit,
            "next_offset": offset + limit if offset + limit < len(rows) else None,
        }

    def chat(self, request: ChatRequest):
        checkpoint("context")
        self._alignment_checks = 0
        self._total_alignment_checks = 0
        self._alignment_exhausted = False
        self._source_reviews = []
        cid = str(request.conversation_id or uuid4())
        history = self._history(request, cid)
        trace_id = str(uuid4())
        provider_receipts_before_plan = getattr(self.provider, "receipts", [])
        provider_receipt_start = len(provider_receipts_before_plan)
        trace = {
            "trace_id": trace_id,
            "verification": [],
            "queries": [],
            "provider_calls": [],
            "provider_failures": [],
        }
        limitations = []
        queries = [request.message]
        focus = dict(self.focus.get(cid, {}))
        prior_candidates = self.retrieved.get(cid, [])
        if prior_candidates:
            focus["candidate_inventory"] = [
                {
                    "id": row.get("evidence_id", row.get("id")),
                    "source": row.get("source", {}),
                    "category": row.get("category"),
                }
                for row in prior_candidates[:24]
            ]
            focus["retrieved_candidate_count"] = len(prior_candidates)
        use_previous_sources = bool(focus)
        resolved = request.message
        needs = information_needs(resolved)
        status = "UNAVAILABLE" if self.provider is None else "AVAILABLE"
        if self.provider:
            try:
                plan_history = history + (
                    [
                        {
                            "role": "assistant",
                            "content": "Previous retrieval focus (source identifiers, not scientific assertions): "
                            + str(focus),
                        }
                    ]
                    if focus
                    else []
                )
                plan = self.provider.plan(request.message, plan_history, request.max_queries)
                use_previous_sources = bool(plan.get("use_previous_sources", bool(focus)))
                if not isinstance(plan.get("resolved_question"), str) or not isinstance(
                    plan.get("queries"), list
                ):
                    raise ProviderFailure("Invalid retrieval plan")
                resolved = plan["resolved_question"]
                needs = information_needs(resolved, plan.get("information_needs"))
                trace["information_needs"] = needs
                proposals = plan["queries"]
                if (
                    not resolved.strip()
                    or len(resolved) > 12000
                    or any(not isinstance(q, str) or not 1 <= len(q) <= 12000 for q in proposals)
                ):
                    raise ProviderFailure("Invalid retrieval query")
                queries += proposals[: request.max_queries - 1]
            except ProviderFailure:
                trace["provider_failures"].append("planning")
                status = "DEGRADED"
                limitations.append(
                    "Conversational reference resolution unavailable; original question retained."
                )
        elif history:
            limitations.append(
                "Provider unavailable: conversational references require an explicit question."
            )
        # Original message remains the strict eligibility boundary. Resolved context
        # and model search expansions only broaden documentary exploration.
        if resolved != request.message and len(queries) < request.max_queries:
            queries.append(resolved)
        jobs = [(request.message, None)]
        if use_previous_sources and focus.get("source_ids") and request.max_queries > 1:
            scoped = self.search.interpret(resolved)
            scoped.source_constraints = list(focus["source_ids"])
            jobs.append((resolved, scoped))
        for query in dict.fromkeys(queries):
            if len(jobs) >= request.max_queries:
                break
            if (query, None) not in jobs:
                jobs.append((query, None))
        results, focus_result = [], None
        for query, intent in jobs:
            result = self.search.search(
                query,
                intent=intent,
                assist=True,
                research=True,
                limit=request.evidence_limit,
                complete_claims=True,
            )
            results.append(result)
            if intent is not None:
                focus_result = result
            trace["queries"].append(
                {
                    "query": query,
                    "source_scope": intent.source_constraints if intent else [],
                    "metrics": result.metrics,
                }
            )
        if (
            self.provider
            and hasattr(self.provider, "refine")
            and len(results) < request.max_queries
        ):
            try:
                summaries = [
                    {
                        "source": row.get("source", {}),
                        "text": row.get("text", "")[:500],
                        "category": row.get("category"),
                    }
                    for result in results
                    for row in result.documentary[:8] + result.discovery[:4]
                ]
                refinement = self.provider.refine(
                    resolved, summaries, request.max_queries - len(results)
                )
                trace["coverage_review"] = refinement
                extra_queries = refinement.get("queries", [])
                if not isinstance(extra_queries, list):
                    raise ProviderFailure("Invalid coverage review")
                for extra in extra_queries:
                    if len(results) >= request.max_queries:
                        break
                    if not isinstance(extra, str) or not 1 <= len(extra.strip()) <= 12000:
                        raise ProviderFailure("Invalid coverage query")
                    if extra.casefold() in {q.casefold() for q, _ in jobs}:
                        continue
                    result = self.search.search(
                        extra,
                        assist=True,
                        research=True,
                        limit=request.evidence_limit,
                        complete_claims=True,
                    )
                    known = {
                        r.get("evidence_id", r.get("id")) for old in results for r in old.candidates
                    }
                    added = sum(
                        r.get("evidence_id", r.get("id")) not in known for r in result.candidates
                    )
                    results.append(result)
                    jobs.append((extra, None))
                    trace["queries"].append(
                        {
                            "query": extra,
                            "source_scope": [],
                            "metrics": result.metrics,
                            "objective": refinement.get("resolved_question"),
                            "new_candidates": added,
                        }
                    )
                    if not added:
                        trace["research_stop"] = "Additional search produced no new candidates"
                        break
            except ProviderFailure:
                trace["provider_failures"].append("coverage_review")
                status = "DEGRADED"
                limitations.append("Coverage review unavailable; initial retrieval retained.")
        trace["resolved_question"] = resolved
        trace["previous_research_focus"] = focus
        primary = results[0]
        if request.scientific_parameters:
            from nasa_fire_ai.query.scenario import ScenarioInput

            scenario = ScenarioInput.model_validate(
                {**request.scientific_parameters, "question": request.message}
            )
            scenario_result = self.search.analyze_scenario(scenario, limit=request.evidence_limit)
            # Scenario constraints govern all primary results, not just presentation.
            from nasa_fire_ai.services.search import SearchResult

            primary = SearchResult.model_validate(scenario_result.evidence)
            results[0] = primary
            limitations += scenario_result.extrapolation_limits
        inventory_order = (
            ([focus_result] + [r for r in results if r is not focus_result])
            if focus_result
            else results
        )
        inventory, omitted = self._inventory(
            inventory_order,
            primary_result=primary,
            question=resolved,
            needs=needs,
            scope_question=request.message,
        )
        if omitted:
            limitations.append(
                f"Source context budget omitted {omitted} passages; available through evidence lookup."
            )
        groups = {
            "direct": primary.direct,
            "related": primary.related,
            "documentary": [public_evidence(r) for result in results for r in result.documentary],
            "discovery": [
                {
                    **public_evidence(r),
                    "candidate_kind": "retrieved_unaccredited_source",
                    "verified_relationship": False,
                }
                for result in results
                for r in result.discovery
            ],
        }
        # Sanitize nested source objects in experimental groups too.
        for field in ("direct", "related"):
            groups[field] = [
                {**r, "evidence": [public_evidence(e) for e in r["evidence"]]}
                for r in groups[field]
            ]
        pooled, seen_candidates = [], set()
        for result in results:
            checkpoint("context")
            for row in result.candidates:
                key = row.get("evidence_id", row.get("id"))
                if key in seen_candidates:
                    continue
                seen_candidates.add(key)
                candidate = dict(row)
                if result is not primary and candidate.get("category") in {"DIRECT", "RELATED"}:
                    candidate.update(
                        category="DISCOVERY",
                        verified_relationship=False,
                        uncertainty_reason="Expanded search does not establish original question constraints",
                    )
                if "evidence" in candidate:
                    candidate["evidence"] = [public_evidence(e) for e in candidate["evidence"]]
                else:
                    candidate = {
                        **public_evidence(candidate),
                        **{
                            k: v
                            for k, v in candidate.items()
                            if k
                            in {
                                "retrieval_routes",
                                "relevance_reason",
                                "uncertainty_reason",
                                "candidate_kind",
                                "verified_relationship",
                                "limitations",
                            }
                        },
                    }
                pooled.append(candidate)
        if use_previous_sources:
            for row in prior_candidates:
                key = row.get("evidence_id", row.get("id"))
                if key not in seen_candidates:
                    # Prior applicability is relative to an earlier question.
                    candidate = {
                        **row,
                        "category": "DISCOVERY",
                        "verified_relationship": False,
                        "uncertainty_reason": "Retained from earlier retrieval; applicability to this turn has not been established",
                    }
                    pooled.append(candidate)
                    seen_candidates.add(key)
        candidate_history_omitted = max(0, len(pooled) - self.candidate_history_limit)
        pooled = pooled[: self.candidate_history_limit]
        if candidate_history_omitted:
            limitations.append(
                f"Candidate history budget omitted {candidate_history_omitted} older candidates; source lookup and new searches remain available."
            )
        answer, citations, suggestions = [], [], []
        by_id = {a["support_id"]: a for a in inventory}
        self._active_support_inventory = by_id
        trace["support_inventory"] = inventory
        from nasa_fire_ai.services.structured_alignment import record_subjects

        self._explicit_record_subjects = record_subjects(results, resolved)
        self._requested_investigations = {
            constraint.entity_id
            for result in results
            for constraint in result.intent.entity_constraints
            if constraint.relation == "belongsToInvestigation"
        }
        from nasa_fire_ai.services.ontology_support import investigation_mentions

        self._requested_investigations.update(
            investigation_mentions(request.message + " " + resolved, self.search.store)
        )
        from nasa_fire_ai.services.document_sections import TEST, named_source_ids

        self._requested_document_sources = named_source_ids(
            request.message + " " + resolved, self.search.registry
        )

        requested_methods = set(TEST.findall(request.message + " " + resolved))
        self._requested_method_documents = {
            anchor["document_id"]: requested_methods
            for anchor in inventory
            if anchor.get("document_id")
            and requested_methods.intersection(anchor.get("method_references", []))
        }
        trace["evidence_examination"] = self.inventory_receipt
        source_directory = {}
        for eid in {span["evidence_id"] for anchor in inventory for span in anchor["spans"]}:
            source = self.search._evidence(eid)
            source_directory[eid] = {
                key: source.get(key) for key in ("source", "page", "section", "structured_location")
            }

        citation_numbers = {}
        if self.provider:
            try:
                draft = self.provider.explain(
                    {
                        "question": request.message,
                        "resolved_question": resolved,
                        "history": history,
                        "research_focus": focus,
                        "detail": request.detail,
                        "evidence": inventory,
                        "information_needs": self.inventory_receipt.get("allocation_needs", []),
                        "source_directory": source_directory,
                        "related_differences": [
                            {k: r[k] for k in ("id", "constraints", "reason_not_direct")}
                            for r in primary.related
                        ],
                        "comparison": generation_comparison(
                            primary.comparison,
                            request.message + "\n" + resolved,
                            self.search.store.registry.properties,
                        ),
                        "coverage_limits": primary.limitations,
                        "discovery_candidates": list(
                            {
                                r["evidence_id"]: r
                                for r in [
                                    *groups["discovery"],
                                    *[
                                        public_evidence(r)
                                        for r in pooled
                                        if r.get("evidence_id") and catalogue_fields(r)
                                    ],
                                ]
                            }.values()
                        ),
                    },
                    request.max_output_tokens,
                )
                trace["draft"] = draft
                proposed_needs = draft.get("answer_plan", [])
                trace["answer_plan"] = (
                    list(proposed_needs) if isinstance(proposed_needs, list) else []
                )
                planned = {row.get("need") for row in trace["answer_plan"] if isinstance(row, dict)}
                trace["answer_plan"].extend(
                    row
                    for row in trace.get("information_needs", [])
                    if row.get("need") not in planned
                )
                trace["verification_stage"] = "draft"
                segments = draft.get("segments")
                accepted, rejected = self._accept_segments(
                    segments, by_id, trace, citations, citation_numbers
                )
                answer.extend(accepted)
                trace["initial_rejections"] = list(rejected)
                trace["coverage_gaps"] = []
                if not accepted and not rejected:
                    responsive = [
                        a
                        for a in inventory
                        if a.get("category") == "DOCUMENTARY" and a.get("question_term_matches")
                    ]
                    if responsive:
                        gap = {
                            "statement_id": "coverage-0",
                            "kind": "coverage_gap",
                            "proposal": {
                                "text": resolved,
                                "support_ids": [a["support_id"] for a in responsive[:6]],
                            },
                            "feedback": {
                                "reason": "No explanatory statements were proposed despite responsive documentary content. Examine these sources for a supported partial explanation. DIRECT eligibility is not required to describe what a report states. Do not invent missing results or applicability."
                            },
                        }
                        trace["coverage_gaps"].append(gap)
                        rejected = [gap]
                if accepted:
                    planned_needs, seen_needs = [], set()
                    for need in [
                        *trace.get("information_needs", []),
                        *trace.get("answer_plan", []),
                    ]:
                        if not isinstance(need, dict) or not need.get("need"):
                            continue
                        key = " ".join(str(need["need"]).casefold().split())
                        if key not in seen_needs:
                            planned_needs.append(need)
                            seen_needs.add(key)
                    for index, need in enumerate(planned_needs):
                        if not isinstance(need, dict) or not need.get("need"):
                            continue
                        if self._need_is_communicated(need, trace.get("accepted_statements", [])):
                            continue
                        from nasa_fire_ai.services.search import words

                        terms = words(str(need["need"]))
                        responsive = sorted(
                            by_id.values(),
                            key=lambda a: -len(terms & words(a.get("text", ""))),
                        )
                        ids = [
                            a["support_id"]
                            for a in responsive[:6]
                            if terms & words(a.get("text", ""))
                        ]
                        gap = {
                            "statement_id": f"coverage-{index + 1}",
                            "kind": "coverage_gap",
                            "proposal": {"text": need.get("need", resolved), "support_ids": ids},
                            "feedback": {
                                "reason": "No accepted proposition communicates this planned information need. Examine registered passages for a useful supported explanation. Matching terminology does not prove sufficiency; preserve unknowns and omit unsupported relationships."
                            },
                        }
                        trace["coverage_gaps"].append(gap)
                        rejected.append(gap)
                trace["repairs"] = []
                for attempt in range(
                    self.max_repair_attempts if self.entailment is not None else 0
                ):
                    if not rejected:
                        break
                    repair_evidence = self._repair_context(rejected, inventory, resolved)
                    repair_payload = {
                        "question": request.message,
                        "resolved_question": resolved,
                        "history": history,
                        "detail": request.detail,
                        "evidence": repair_evidence,
                        "source_directory": source_directory,
                        "answer_plan": trace["answer_plan"],
                        "information_needs": self.inventory_receipt.get("allocation_needs", []),
                        "already_accepted": list(answer),
                        "rejected_segments": rejected,
                        "repair_instruction": "Correct only the rejected factual statements using the permitted evidence. Each correction must use repair_of to identify its rejected statement. Resolve wrong citations using the source titles and original passages. Preserve numbers, units, subjects and modality. If NLI rejects a faithful-looking paraphrase, use a simpler source-attributed sentence close to the appropriate original wording. Do not repeat or expand already accepted statements. Omit unsupported clauses. Return no correction if the source cannot support one.",
                    }
                    repair = self.provider.explain(repair_payload, request.max_output_tokens)
                    trace["verification_stage"] = f"repair-{attempt + 1}"
                    trace["repair_targets"] = [r["statement_id"] for r in rejected]
                    repaired, remaining = self._accept_segments(
                        repair.get("segments", []),
                        {a["support_id"]: a for a in repair_evidence},
                        trace,
                        citations,
                        citation_numbers,
                    )
                    trace["repairs"].append(
                        {
                            "attempt": attempt + 1,
                            "requested_statements": [r["statement_id"] for r in rejected],
                            "permitted_support_ids": [a["support_id"] for a in repair_evidence],
                            "draft": repair,
                            "accepted": len(repaired),
                            "rejected": len(remaining),
                        }
                    )
                    answer.extend(repaired)
                    rejected = remaining
                    if not repaired:
                        break
                trace["unrepaired_statements"] = list(rejected)
                for query in draft.get("exploration_queries", [])[: request.max_queries]:
                    if (
                        isinstance(query, str)
                        and 0 < len(query) <= 500
                        and not re.search(r"https?://|\]\(", query)
                    ):
                        query = re.sub(r"\[\d+\]", "", query).strip()
                        suggestions.append(
                            {
                                "kind": "unverified_search_idea",
                                "query": query,
                                "verified_relationship": False,
                                "nasa_recommendation": False,
                            }
                        )
                if rejected:
                    status = "DEGRADED"
                    limitations.append(
                        "Some proposed wording lacked sufficient support and was omitted; source records remain accessible."
                    )
            except ProviderFailure:
                trace["provider_failures"].append("generation_or_repair")
                status = "DEGRADED"
                limitations.append(
                    "Conversational provider failed; retrieved evidence remains available."
                )
        if self.provider and self.max_repair_attempts and trace.get("verification"):
            # A failed model repair may itself lack usable attribution. Retain
            # the initial failed propositions and their examination locators,
            # rather than allowing the repair to erase recoverable source facts.
            failures = [
                {
                    "statement_id": row["statement_id"],
                    "proposal": {
                        "text": row["text"],
                        "support_ids": row.get("proposed_support_ids") or [],
                    },
                    "feedback": row,
                }
                for row in trace["verification"]
                if not row.get("supported")
            ]
            restatements = self._source_restatements(
                failures, by_id, trace.get("accepted_statements", []), resolved, needs=needs
            )
            if restatements:
                trace["verification_stage"] = "repair-source"
                trace["repair_targets"] = [row["statement_id"] for row in failures]
                trace["repair_targets"].extend(row["repair_of"] for row in restatements)
                recovered, _ = self._accept_segments(
                    restatements, by_id, trace, citations, citation_numbers
                )
                trace["source_restatement_repair"] = {
                    "proposed": len(restatements),
                    "accepted": len(recovered),
                    "boundary": "Exact source restatements; rejected generated wording remains rejected",
                }
                answer.extend(recovered)
        if self.provider and self.max_repair_attempts:
            graph_completion = self._graph_source_completion(
                request.message + " " + resolved + " " + " ".join(need["need"] for need in needs),
                by_id,
                trace.get("accepted_statements", []),
                needs=needs,
            )
            if graph_completion:
                trace["verification_stage"] = "repair-graph-context"
                trace["repair_targets"] = [proposal["repair_of"] for proposal in graph_completion]
                recovered, failures = self._accept_segments(
                    graph_completion, by_id, trace, citations, citation_numbers
                )
                trace["graph_role_completion"] = {
                    "proposed": len(graph_completion),
                    "accepted": len(recovered),
                    "rejected": len(failures),
                    "boundary": "Source-backed ontology roles route quotations; all normal verification remains active",
                }
                answer.extend(recovered)
            from nasa_fire_ai.services.structured_alignment import complete_record_fields

            completion = complete_record_fields(
                trace.get("information_needs", []),
                by_id,
                self.search,
                trace.get("accepted_statements", []),
                self._explicit_record_subjects,
                self.entailment,
            )
            if completion:
                trace["verification_stage"] = "repair-coverage"
                trace["repair_targets"] = [row["repair_of"] for row in completion]
                recovered, failures = self._accept_segments(
                    completion, by_id, trace, citations, citation_numbers
                )
                trace["structured_coverage_repair"] = {
                    "proposed": len(completion),
                    "accepted": len(recovered),
                    "rejected": len(failures),
                }
                answer.extend(recovered)
        if answer and self.provider and hasattr(self.provider, "organize"):
            try:
                answer = self._deduplicate_answer(answer, trace)
                organization = self.provider.organize(
                    resolved,
                    history
                    + (
                        [
                            {
                                "role": "assistant",
                                "content": "Previous retrieval focus: " + str(focus),
                            }
                        ]
                        if focus
                        else []
                    ),
                    answer,
                )
                indices = organization.get("retained_indices")
                if not isinstance(indices, list) or any(
                    type(i) is not int or not 0 <= i < len(answer) for i in indices
                ):
                    raise ProviderFailure("Invalid relevance selection")
                trace["relevance_review"] = organization
                trace["relevance_omissions"] = [
                    text for i, text in enumerate(answer) if i not in indices
                ]
                # Preserve same-scope scientific content against a superficial
                # relevance veto. A paragraph attributed to another investigation
                # may be omitted when the organizer judges it tangential.
                selected = list(dict.fromkeys(indices))
                requested = getattr(self, "_requested_investigations", set())
                restored = []
                for index, paragraph in enumerate(answer):
                    if index in selected:
                        continue
                    plain = re.sub(r"\[\d+\]", "", paragraph)
                    sources = {
                        sid
                        for statement in trace.get("accepted_statements", [])
                        if statement.get("text") in plain
                        for sid in statement.get("source_ids", [])
                    }
                    scopes = (
                        set().union(*(self.search.source_scopes.get(sid, set()) for sid in sources))
                        if sources and hasattr(self.search, "source_scopes")
                        else set()
                    )
                    if requested and scopes and requested.isdisjoint(scopes):
                        continue
                    restored.append(index)
                restored_text = [answer[i] for i in restored]
                answer = [answer[i] for i in selected + restored]
                trace["relevance_restored"] = restored_text
                trace["relevance_restored_indices"] = restored
                referenced = {
                    int(n) for paragraph in answer for n in re.findall(r"\[(\d+)\]", paragraph)
                }
                citations = [c for c in citations if c["number"] in referenced]
            except ProviderFailure:
                trace["provider_failures"].append("relevance_review")
                status = "DEGRADED"
                limitations.append("Conversational relevance review unavailable.")
        # Candidate selection is not scientific assertion generation. Only the
        # registry title and an explicit uncertainty notice are rendered here.
        exploratory_ids = trace.get("draft", {}).get("exploratory_source_ids", [])
        exploratory_source_keys = set()
        if isinstance(exploratory_ids, list) and (
            not answer
            or re.search(
                r"\b(?:related|other studies|explor(?:e|atory|ation)|candidate sources|discovery)\b",
                resolved,
                re.IGNORECASE,
            )
        ):
            for eid in dict.fromkeys(e for e in exploratory_ids if isinstance(e, str)):
                row = next(
                    (r for r in pooled if r.get("evidence_id") == eid),
                    None,
                )
                if row is None:
                    continue
                original = self.search._evidence(eid)
                if not original:
                    continue
                source = original.get("source", {})
                title = source.get("title") or source.get("source_id")
                source_key = source.get("doi") or source.get("url") or title
                if source_key in exploratory_source_keys:
                    continue
                if len(exploratory_source_keys) >= self.max_exploratory_sources:
                    break
                exploratory_source_keys.add(source_key)
                text = f"Potential source to examine: {title}. Its relevance to the requested scientific conditions has not been established."
                number = max((c["number"] for c in citations), default=0) + 1
                citations.append(
                    {
                        "number": number,
                        **public_evidence(original),
                        "category": "DISCOVERY",
                        "evidence_ids": [eid],
                        "supporting_passage": original["text"],
                        "conditions": [],
                        "limitations": [
                            "Bibliographic candidate only; no verified scientific relationship"
                        ],
                        "supports": [
                            {
                                "evidence_id": eid,
                                "claim_text": text,
                                "support_id": "candidate-" + eid,
                                "category": "DISCOVERY",
                                "passage": original["text"],
                                "conditions": [],
                                "limitations": ["Unverified candidate relevance"],
                            }
                        ],
                    }
                )
                answer.append(text + f" [{number}]")
        trace["generated_paragraphs_before_fallback"] = list(answer)
        planned_ids = {
            identity
            for need in trace.get("answer_plan", [])
            if isinstance(need, dict)
            for identity in need.get("support_ids", [])
            if isinstance(identity, str)
        }
        offered_discovery_ids = {r.get("evidence_id") for r in groups["discovery"]} | {
            r.get("evidence_id") for r in pooled if catalogue_fields(r)
        }

        exploration_only = bool(exploratory_ids and planned_ids) and all(
            (identity in by_id and by_id[identity].get("epistemic_type") == "catalogue_metadata")
            or identity in offered_discovery_ids
            for identity in planned_ids
        )
        if exploration_only and suggestions:
            answer.append(
                "Possible follow-up searches, with relevance still unverified: "
                + "; ".join("“" + s["query"] + "”" for s in suggestions)
                + "."
            )
        local_extracts = False
        if not answer or (
            citations
            and all(c["category"] == "DISCOVERY" for c in citations)
            and not exploration_only
        ):
            # Exact, complete documentary statements remain useful without a provider.
            # Rank for question relevance independently of textual support.
            from nasa_fire_ai.services.investigation import topic_terms

            terms = set(topic_terms(resolved))
            named_subjects = {
                token.upper()
                for token in re.findall(r"\b[A-Z][A-Z0-9]+(?:[-–][A-Z0-9]+)+\b", resolved)
            }
            ranked = sorted(
                (a for a in inventory if a.get("epistemic_type") == "documentary_content"),
                key=lambda a: -len(terms & set(re.findall(r"[\w-]+", a["text"].lower()))),
            )
            chosen, passage_ids = [], set()
            for anchor in ranked:
                span = anchor["spans"][0]
                if named_subjects and not any(
                    name
                    in (
                        (anchor.get("text") or "") + " " + (anchor.get("source_title") or "")
                    ).upper()
                    for name in named_subjects
                ):
                    continue
                if span["evidence_id"] in passage_ids or not terms.intersection(
                    set(re.findall(r"[\w-]+", anchor["text"].lower()))
                ):
                    continue
                passage_ids.add(span["evidence_id"])
                chosen.append({"text": anchor["text"], "support_ids": [anchor["support_id"]]})
                if len(chosen) >= 3:
                    break
            if chosen:
                trace["verification_stage"] = "fallback"
                extracted, _ = self._accept_segments(
                    chosen, by_id, trace, citations, citation_numbers
                )
                answer = extracted + answer
                local_extracts = bool(extracted)
                if extracted:
                    limitations.append(
                        "Showing exact source excerpts; a generated scientific explanation was unavailable."
                    )
        if not answer:
            if suggestions:
                answer = [
                    "These are possible searches to continue, without a verified scientific relationship:\n\n"
                    + "\n".join("- “" + item["query"] + "”" for item in suggestions)
                ]
            else:
                answer = [
                    "A verified conversational explanation is unavailable. Retrieved sources remain accessible in the evidence details."
                ]
            if status == "AVAILABLE":
                status = "DEGRADED"
        from nasa_fire_ai.services.structured_alignment import missing_record_fields

        for lookup in missing_record_fields(
            request.message + "\n" + resolved,
            self.search,
            getattr(self, "_explicit_record_subjects", set()),
        ):
            answer.append(lookup["text"])
            trace.setdefault("system_boundaries", []).append(lookup)
        boundary = self._causal_analysis_boundary(
            request.message + "\n" + resolved, by_id, trace.get("accepted_statements", [])
        )
        if boundary:
            answer.append(boundary)
            trace.setdefault("system_boundaries", []).append(
                {
                    "kind": "causal_inference_policy",
                    "text": boundary,
                    "source_record_ids": sorted(self._explicit_record_subjects),
                    "boundary": "Assistant policy; not a NASA finding or a claim that NASA lacks evidence",
                }
            )
        emitted_text = {" ".join(re.sub(r"\[\d+\]", "", paragraph).split()) for paragraph in answer}
        for citation in citations:
            citation["supports"] = [
                support
                for support in citation["supports"]
                if any(
                    " ".join(support["claim_text"].split()) in paragraph
                    for paragraph in emitted_text
                )
            ]
            citation["evidence_ids"] = list(
                dict.fromkeys(support["evidence_id"] for support in citation["supports"])
            )
            if citation["supports"]:
                first = citation["supports"][0]
                citation.update(public_evidence(self.search._evidence(first["evidence_id"])))
                citation["supporting_passage"] = first["passage"]
                citation["conditions"] = first["conditions"]
                citation["limitations"] = first["limitations"]
                citation["category"] = first["category"]
        reference_order = list(
            dict.fromkeys(
                int(n) for paragraph in answer for n in re.findall(r"\[(\d+)\]", paragraph)
            )
        )
        citations = [c for c in citations if c["number"] in reference_order and c["supports"]]
        if set(reference_order) - {c["number"] for c in citations}:
            raise ProviderFailure("Final answer contains an unregistered citation marker")
        citations.sort(key=lambda c: reference_order.index(c["number"]))
        renumber = {c["number"]: i + 1 for i, c in enumerate(citations)}
        answer = [
            re.sub(r"\[(\d+)\]", lambda match: f"[{renumber[int(match[1])]}]", paragraph)
            for paragraph in answer
        ]
        citations = [{**c, "number": renumber[c["number"]]} for c in citations]
        trace["locator_reexamination_checks"] = self._total_alignment_checks
        trace["alignment_budget_scope"] = "per_proposition"
        trace["source_reviews"] = list(self._source_reviews)
        if self._alignment_exhausted or self._alignment_checks >= self.max_alignment_checks:
            limitations.append(
                "Documentary locator re-examination budget exhausted; unresolved wording was not emitted."
            )
        provider_receipts = getattr(self.provider, "receipts", [])
        # Native planning starts a fresh receipt list each turn; append-only
        # providers retain the original list. Do not slice a new turn by the
        # previous turn's call count.
        receipt_start = (
            provider_receipt_start if provider_receipts is provider_receipts_before_plan else 0
        )
        trace["provider_calls"] = list(provider_receipts)[receipt_start:]
        if any(call.get("partial_generation") for call in trace["provider_calls"]):
            status = "DEGRADED"
            limitations.append(
                "Provider output was incomplete; only complete, verified segments were retained."
            )
        self.traces[trace_id] = trace
        while len(self.traces) > self.max_sessions:
            self.traces.popitem(last=False)
        communicated = [
            a
            for a in trace.get("accepted_statements", [])
            if any(" ".join(a["text"].split()) in paragraph for paragraph in emitted_text)
        ]
        communicated_ids = {sid for a in communicated for sid in a["support_ids"]}
        plan = [need for need in trace.get("answer_plan", []) if isinstance(need, dict)]
        coverage = {
            **{
                k: v
                for k, v in self.inventory_receipt.items()
                if k not in {"selection_decisions", "allocation_needs"}
            },
            "allocation_needs": [
                {
                    **{k: v for k, v in n.items() if k != "candidate_support_ids"},
                    "candidate_anchor_count": len(n["candidate_support_ids"]),
                    "communicated_candidate_support_ids": sorted(
                        set(n["supplied_support_ids"]) & communicated_ids
                    ),
                    "boundary": "Candidate contribution is not verified need sufficiency",
                }
                for n in self.inventory_receipt.get("allocation_needs", [])
            ],
            "reexamined_evidence_ids": sorted(
                {eid for review in self._source_reviews for eid in review["evidence_ids"]}
            ),
            "support_reexamination_recoveries": sum(
                v["supported"] and v.get("locator_reexamined", False) for v in trace["verification"]
            ),
            "communicated_support_ids": sorted(communicated_ids),
            "communicated_evidence_ids": sorted(
                {eid for a in communicated for eid in a["evidence_ids"]}
            ),
            "communicated_sources": sorted({sid for a in communicated for sid in a["source_ids"]}),
            "accepted_but_not_communicated": [
                a for a in trace.get("accepted_statements", []) if a not in communicated
            ],
            "needs": [
                {
                    **need,
                    "communicated": self._need_is_communicated(
                        need,
                        communicated,
                    ),
                    "coverage_basis": "final proposition text aligned to this need; source IDs alone are insufficient",
                }
                for need in plan
            ],
            "boundary": "Context/support coverage and model-declared needs, not independent scientific answer grading",
        }
        generation_records = [v for v in trace["verification"] if v.get("stage") != "fallback"]
        retained = [v for v in generation_records if v["supported"]]
        rejected_count = sum(not v["supported"] for v in generation_records)
        repair_successes = sum(
            v["supported"] and v.get("stage", "").startswith("repair-") for v in generation_records
        )
        failures = trace["provider_failures"] + [
            c["stage"]
            for c in trace["provider_calls"]
            if c.get("error_type") or c.get("partial_generation")
        ]
        generated_text = {
            " ".join(re.sub(r"\[\d+\]", "", p).split())
            for p in trace.get("generated_paragraphs_before_fallback", [])
        }
        scientific = [
            a
            for a in communicated
            if "catalogue_metadata" not in a["epistemic_types"]
            and a["stage"] != "fallback"
            and any(" ".join(a["text"].split()) in paragraph for paragraph in generated_text)
        ]
        if self.provider and scientific and not failures:
            status = "AVAILABLE"
        elif self.provider and not scientific:
            status = "DEGRADED"
        generation_status = {
            "status": "SUCCEEDED"
            if "draft" in trace
            else "FAILED"
            if self.provider
            else "NOT_REQUESTED",
            "provider_availability": "CONFIGURED" if self.provider else "UNAVAILABLE",
            "explanation_status": "VERIFIED_PROSE"
            if scientific
            else "EXTRACTIVE_FALLBACK"
            if local_extracts
            else "EXPLORATORY_LIST"
            if citations
            else "UNAVAILABLE",
            "failure_kinds": sorted(
                {
                    "TIMEOUT" if "Timeout" in c.get("error_type", "") else "PROVIDER_ERROR"
                    for c in trace["provider_calls"]
                    if c.get("error_type")
                }
            ),
            "failure_stages": sorted(set(failures)),
            "repair_attempts": len(trace.get("repairs", [])),
        }
        verification_status = {
            "status": "REPAIRED"
            if repair_successes and not trace.get("unrepaired_statements")
            else "PARTIAL"
            if retained and rejected_count
            else "ACCEPTED"
            if retained
            else "NO_ACCEPTED_GENERATION",
            "rejected_claim_count": rejected_count,
            "retained_claim_count": len(retained),
            "repaired_claim_count": repair_successes,
            "communicated_generated_claim_count": len(scientific),
        }
        completeness = {
            "status": "NO_VERIFIED_EXPLANATION"
            if not scientific
            else "NOT_ASSESSED"
            if not plan
            else "PARTIAL"
            if any(
                not need["communicated"] or need.get("status") in {"partial", "unresolved"}
                for need in coverage["needs"]
            )
            else "DECLARED_NEEDS_COVERED",
            "basis": "Model-declared information needs and communicated support; no independent completeness assertion",
        }
        trace["coverage_summary"] = coverage
        trace["generation_status"] = generation_status
        trace["verification_status"] = verification_status
        response = ChatResponse(
            conversation_id=cid,
            generation_status=generation_status,
            verification_status=verification_status,
            answer_completeness=completeness,
            coverage_summary={
                k: v for k, v in coverage.items() if k != "accepted_but_not_communicated"
            },
            message_id=str(uuid4()),
            answer=(
                "Source excerpts for inspection; a full conversational explanation could not be verified.\n\n"
                if local_extracts
                else ""
            )
            + "\n\n".join(dict.fromkeys(answer)),
            citations=citations,
            evidence_groups=groups,
            additional_candidates=[
                r
                for r in pooled
                if r.get("evidence_id", r.get("id"))
                not in {eid for c in citations for eid in c["evidence_ids"]}
            ][: request.evidence_limit],
            retrieval={
                "retrieved": len(pooled),
                "examined_supports": len(inventory),
                "context_omitted": omitted,
                "candidate_history_omitted": candidate_history_omitted,
                "summarized_evidence": len({e for c in citations for e in c["evidence_ids"]}),
                "candidate_offset": 0,
                "candidate_limit": request.evidence_limit,
                "next_offset": request.evidence_limit
                if len(pooled) > request.evidence_limit
                else None,
                "continuation_url": f"/api/v1/conversations/{cid}/candidates",
                "queries": trace["queries"],
                "boundary": "Bounded retrieved pool; no claim of complete NASA literature coverage",
            },
            comparison=primary.comparison,
            discovery_suggestions=suggestions,
            limitations=limitations + primary.limitations,
            provider_status={
                "status": status,
                "availability": "CONFIGURED" if self.provider else "UNAVAILABLE",
                "failure_stages": sorted(set(failures)),
                "generated_by": getattr(self.provider, "generation_name", "Nemotron")
                if citations
                and not local_extracts
                and any(c["category"] != "DISCOVERY" for c in citations)
                else None,
                "response_mode": "source_excerpts"
                if local_extracts
                else "candidate_metadata"
                if citations and all(c["category"] == "DISCOVERY" for c in citations)
                else "generated"
                if citations
                else "unavailable",
                "semantic_verifier": "local_multilingual_nli" if self.entailment else "UNAVAILABLE",
            },
            trace_id=trace_id,
            snapshot_id=primary.snapshot_id,
        )
        checkpoint("publishing")
        self.retrieved[cid] = pooled
        if not use_previous_sources:
            self.focus.pop(cid, None)
        if citations or inventory:
            self.focus[cid] = {
                "resolved_question": resolved,
                "information_needs": needs,
                "unanswered_needs": [n for n in coverage["needs"] if not n["communicated"]],
                "source_ids": sorted(
                    {
                        c.get("source", {}).get("source_id")
                        for c in citations
                        if c.get("source", {}).get("source_id")
                    }
                )
                or sorted({a["source_id"] for a in inventory if a.get("source_id")}),
            }
        self.sessions[cid] = (
            monotonic(),
            (
                history
                + [
                    {"role": "user", "content": request.message},
                    {"role": "assistant", "content": response.answer},
                ]
            )[-12:],
        )
        self.sessions.move_to_end(cid)
        while len(self.sessions) > self.max_sessions:
            expired, _ = self.sessions.popitem(last=False)
            self.focus.pop(expired, None)
            self.retrieved.pop(expired, None)
        trace["snapshot_id"] = primary.snapshot_id
        persist_claim_ledger(
            trace,
            conversation_id=cid,
            response_id=response.message_id,
            question=request.message,
            answer=response.answer,
            citations=response.citations,
        )
        return response
