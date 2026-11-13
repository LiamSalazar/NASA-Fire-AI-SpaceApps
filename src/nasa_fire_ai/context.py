"""Source-backed scientific context and scope resolution.

Context is a resolution aid, not a source of scientific facts.  This module
deliberately keeps proposed statements separate from the canonical RDF graph.
Only an already approved ontology relation, reviewed endpoints, and resolvable
evidence can be published through the native graph.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class ContextStatus(StrEnum):
    EXPLICIT_LOCAL = "EXPLICIT_LOCAL"
    VERIFIED_APPLICABLE_CONTEXT = "VERIFIED_APPLICABLE_CONTEXT"
    CONTEXTUAL_CANDIDATE = "CONTEXTUAL_CANDIDATE"
    CONFLICTED = "CONFLICTED"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ContextType(StrEnum):
    GRAVITY = "gravity"
    MATERIAL = "material"
    ATMOSPHERE = "atmosphere"
    APPARATUS = "apparatus"
    INTERVENTION = "intervention"
    PHENOMENON = "phenomenon"
    MEASUREMENT = "measurement"
    INVESTIGATION = "investigation"
    CAMPAIGN = "campaign"
    OTHER = "other"


class SourceLocation(BaseModel):
    document_id: str
    source_id: str | None = None
    section: str | None = None
    page: int | None = None
    paragraph: str | None = None
    table: str | None = None
    caption: str | None = None


class ScientificSourceUnit(BaseModel):
    """A structure-preserving documentary unit used by extraction and review."""

    unit_id: str
    unit_type: Literal[
        "title", "section", "subsection", "paragraph", "table", "caption", "footnote"
    ]
    text: str
    location: SourceLocation
    parent_unit_id: str | None = None
    experiment_ids: list[str] = []
    metadata: dict[str, str] = {}


def context_statement_from_unit(
    unit: ScientificSourceUnit,
    *,
    statement_id: str,
    context_type: str,
    value: str,
    entity_ids: list[str],
    evidence_ids: list[str],
    status: ContextStatus = ContextStatus.CONTEXTUAL_CANDIDATE,
    scope: str = "local",
    exceptions: list[str] | None = None,
) -> ContextStatement:
    """Create a staged statement while retaining the original source unit.

    Callers must supply entity and evidence links from deterministic extraction
    or reviewed model output; this function never guesses them from prose.
    """
    return ContextStatement(
        statement_id=statement_id,
        context_type=context_type,
        value=value,
        entity_ids=entity_ids,
        evidence_ids=evidence_ids,
        original_text=unit.text,
        source_location=unit.location,
        scope=scope,
        exceptions=exceptions or [],
        validation_status=status,
    )


class ContextStatement(BaseModel):
    """A source statement whose applicability can be reviewed independently."""

    statement_id: str
    context_type: str
    value: str
    entity_ids: list[str] = Field(min_length=1)
    evidence_ids: list[str] = Field(min_length=1)
    original_text: str
    source_location: SourceLocation
    scope: str = "local"
    applicability_conditions: list[str] = []
    exceptions: list[str] = []
    conflicts: list[str] = []
    validation_status: ContextStatus = ContextStatus.CONTEXTUAL_CANDIDATE
    provenance_path: list[str] = []
    relation: str | None = None
    priority: int = 0
    quantifier: Literal["ALL", "IDENTIFIED", "SOME", "UNSPECIFIED", "THEORETICAL"] = "IDENTIFIED"
    support_spans: list[dict] = []
    membership_paths: dict[str, list[dict]] = {}
    property_value: dict | None = None
    scope_entity: str | None = None
    canonical_review: Literal["PENDING", "APPROVED"] = "PENDING"


class ContextResolution(BaseModel):
    entity_id: str
    context_type: str
    requested_value: str | None = None
    status: ContextStatus
    values: list[str] = []
    statements: list[ContextStatement] = []
    exceptions: list[str] = []
    conflicts: list[str] = []
    reason: str


class ContextualProposal(BaseModel):
    """Untrusted structured model output; never a canonical graph assertion."""

    subject_entity: str
    candidate_predicate: str
    object_value: str
    source_statement: str
    supporting_text: str
    context_scope: str
    applicability_conditions: list[str] = []
    exceptions: list[str] = []
    evidence_ids: list[str] = Field(min_length=1)
    validation_status: Literal["PROPOSED", "ACCEPTED_FOR_REVIEW", "REJECTED"] = "PROPOSED"
    support_spans: list[dict] = []
    conflicts: list[str] = []
    uncertainty: str | None = None
    source_id: str | None = None
    quantifier: Literal["ALL", "IDENTIFIED", "SOME", "UNSPECIFIED", "THEORETICAL"] = "UNSPECIFIED"
    proposed_path: list[dict] = []


@dataclass(frozen=True)
class ContextQueryPolicy:
    """Presentation/retrieval preference only; it never changes graph facts."""

    default_context_type: str = "gravity"
    preferred_values: tuple[str, ...] = ("microgravity",)
    explicit_values_override_default: bool = True
    inheritance_enabled: bool = False

    def for_query(self, explicit_values: Iterable[str] = ()) -> dict:
        explicit = [str(value) for value in explicit_values if str(value).strip()]
        return {
            "default_preference": None if explicit else list(self.preferred_values),
            "explicit_values": explicit,
            "explicit_values_override_default": self.explicit_values_override_default,
            "inheritance_enabled": self.inheritance_enabled,
            "authority": "retrieval_and_presentation_policy_only",
        }


DEFAULT_CONTEXT_POLICY = ContextQueryPolicy()


@dataclass
class ScopeResolver:
    """Resolve applicability using evidence and explicit scope, never scores alone."""

    statements: list[ContextStatement] = field(default_factory=list)

    def add(self, statement: ContextStatement) -> None:
        self.statements.append(statement)

    def extend(self, statements: Iterable[ContextStatement]) -> None:
        for statement in statements:
            self.add(statement)

    def resolve(
        self, entity_id: str, context_type: str, requested_value: str | None = None
    ) -> ContextResolution:
        candidates = [
            statement
            for statement in self.statements
            if statement.context_type == context_type and entity_id in statement.entity_ids
        ]
        if not candidates:
            return ContextResolution(
                entity_id=entity_id,
                context_type=context_type,
                requested_value=requested_value,
                status=ContextStatus.UNKNOWN,
                reason="no source-backed statement applies to this entity",
            )

        applicable = [s for s in candidates if entity_id not in set(s.exceptions)]
        exceptions = sorted({x for s in candidates for x in s.exceptions if x == entity_id})
        if any(s.validation_status == ContextStatus.CONFLICTED for s in applicable):
            return ContextResolution(
                entity_id=entity_id,
                context_type=context_type,
                requested_value=requested_value,
                status=ContextStatus.CONFLICTED,
                statements=applicable,
                conflicts=sorted({s.value for s in applicable}),
                reason="source conflict has not been resolved",
            )
        authoritative = [
            s
            for s in applicable
            if s.validation_status
            in {ContextStatus.EXPLICIT_LOCAL, ContextStatus.VERIFIED_APPLICABLE_CONTEXT}
            and s.quantifier in {"ALL", "IDENTIFIED"}
            and not s.applicability_conditions
        ]
        if not authoritative:
            return ContextResolution(
                entity_id=entity_id,
                context_type=context_type,
                requested_value=requested_value,
                status=ContextStatus.NOT_APPLICABLE
                if exceptions
                else ContextStatus.CONTEXTUAL_CANDIDATE,
                values=sorted({s.value for s in applicable}),
                statements=applicable,
                exceptions=exceptions,
                reason="only candidate context exists"
                if not exceptions
                else "explicit exception excludes entity",
            )

        # Execution/local statements outrank campaign or document-wide context.
        # Conflicts are preserved when statements at the same applicable scope
        # disagree; ranking cannot decide a scientific contradiction.
        scope_rank = {
            "local": 3,
            "execution": 3,
            "run": 3,
            "group": 2,
            "campaign": 1,
            "document": 0,
        }
        best_rank = max(scope_rank.get(s.scope, 0) for s in authoritative)
        authoritative = [s for s in authoritative if scope_rank.get(s.scope, 0) == best_rank]
        values = sorted({s.value for s in authoritative})
        if len(values) > 1 or any(s.conflicts for s in authoritative):
            return ContextResolution(
                entity_id=entity_id,
                context_type=context_type,
                requested_value=requested_value,
                status=ContextStatus.CONFLICTED,
                values=values,
                statements=authoritative,
                exceptions=exceptions,
                conflicts=values,
                reason="authoritative source statements disagree; no value selected",
            )
        value = values[0]
        matching = [s for s in authoritative if s.value == value]
        status = (
            ContextStatus.EXPLICIT_LOCAL
            if any(s.validation_status == ContextStatus.EXPLICIT_LOCAL for s in matching)
            else ContextStatus.VERIFIED_APPLICABLE_CONTEXT
        )
        if requested_value is not None and value != requested_value:
            return ContextResolution(
                entity_id=entity_id,
                context_type=context_type,
                requested_value=requested_value,
                status=ContextStatus.NOT_APPLICABLE,
                values=values,
                statements=matching,
                exceptions=exceptions,
                reason="verified context differs from requested value",
            )
        return ContextResolution(
            entity_id=entity_id,
            context_type=context_type,
            requested_value=requested_value,
            status=status,
            values=values,
            statements=matching,
            exceptions=exceptions,
            reason="source-backed context applies at entity scope",
        )


def validate_proposal(
    proposal: ContextualProposal, evidence: dict[str, dict]
) -> ContextualProposal:
    """Accept only exact evidence IDs and supporting text already supplied by RAG."""

    from nasa_fire_ai.ingestion.source_spans import recover_span

    valid = bool(proposal.supporting_text.strip() and proposal.source_statement.strip())
    resolved_spans = []
    spans = proposal.support_spans or [
        {"evidence_id": eid, "text": proposal.supporting_text} for eid in proposal.evidence_ids
    ]
    if set(proposal.evidence_ids) != {s.get("evidence_id") for s in spans}:
        valid = False
    for evidence_id in proposal.evidence_ids:
        record = evidence.get(evidence_id)
        if record is None:
            valid = False
            break
        text = str(record.get("text", record.get("passage", "")))
        cited = [s for s in spans if s.get("evidence_id") == evidence_id]
        try:
            for span in cited:
                recovered = recover_span(text, span.get("text", ""))
                resolved_spans.append({**span, "text": recovered["span"], "locator": recovered})
        except ValueError:
            valid = False
            break
    try:
        recovered_statement = recover_span(
            "\n".join(str(s.get("text", "")) for s in resolved_spans), proposal.source_statement
        )
    except ValueError:
        valid = False
        recovered_statement = None
    # Legacy single-span callers can supply a complete source statement while
    # choosing a narrower supporting quote; it must still be source-exact.
    if not proposal.support_spans:
        valid = len(resolved_spans) == len(proposal.evidence_ids)
        try:
            for eid in proposal.evidence_ids:
                text = str(
                    evidence.get(eid, {}).get("text", evidence.get(eid, {}).get("passage", ""))
                )
                recover_span(text, proposal.supporting_text)
                recovered_statement = recover_span(text, proposal.source_statement)
        except ValueError:
            valid = False
    return proposal.model_copy(
        update={
            "validation_status": "ACCEPTED_FOR_REVIEW" if valid else "REJECTED",
            "support_spans": resolved_spans if valid else proposal.support_spans,
            "source_statement": recovered_statement["span"]
            if valid and recovered_statement
            else proposal.source_statement,
        }
    )
