"""Opt-in semantic discovery and contextual candidate review.

This module does not modify canonical query execution. It expands documentary
candidate generation and records model proposals in ``discovery_candidates``;
only the native executor can establish DIRECT/RELATED scientific matches.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from time import perf_counter
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from nasa_fire_ai.query.expansion_contracts import DiscoveryHypothesis, validate_discovery
from nasa_fire_ai.query.native import execute_native

PROMPT_VERSION = "phase3c-controlled-discovery-v2"
RERANK_PROMPT_VERSION = "phase3c-contextual-rerank-v5"
MAX_EXPANSIONS = 3
MAX_CANDIDATES = 40
MAX_RERANK_CANDIDATES = 5
MAX_JEV_CANDIDATES = 3
MAX_PASSAGE_CHARS = 700
MAX_SOURCE_CONTEXT_CHARS = 1400


def _enabled(name: str) -> bool:
    return os.getenv(name, "false").strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class ControlledReasoningFlags:
    query_expansion: bool = False
    contextual_reranking: bool = False
    jev_advisory_triage: bool = False
    scientific_paraphrase: bool = False
    selective_reranking: bool = False
    hierarchical_retrieval: bool = False
    relational_related: bool = False

    @classmethod
    def from_environment(cls) -> ControlledReasoningFlags:
        return cls(
            selective_reranking=_enabled("SELECTIVE_CONTEXTUAL_RERANKING_ENABLED"),
            hierarchical_retrieval=_enabled("HIERARCHICAL_SEMANTIC_RETRIEVAL_ENABLED"),
            relational_related=_enabled("RELATIONAL_RELATED_RETRIEVAL_ENABLED"),
            query_expansion=_enabled("SEMANTIC_QUERY_EXPANSION_ENABLED"),
            contextual_reranking=_enabled("CONTEXTUAL_RERANKING_ENABLED"),
            jev_advisory_triage=_enabled("JEV_ADVISORY_TRIAGE_ENABLED"),
            scientific_paraphrase=_enabled("SCIENTIFIC_PARAPHRASE_ENABLED"),
        )


class ExpansionProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    queries: list[str] = Field(default_factory=list, max_length=8)
    hypotheses: list[DiscoveryHypothesis] = Field(default_factory=list, max_length=3)


class ConstraintAssessment(BaseModel):
    model_config = ConfigDict(extra="ignore")
    constraint_index: int = Field(ge=0)
    status: str
    supporting_span: str = ""


class CandidateJudgment(BaseModel):
    model_config = ConfigDict(extra="ignore")
    evidence_id: str
    candidate_relevance: str
    supporting_span: str = ""
    constraint_assessments: list[ConstraintAssessment] = Field(default_factory=list)
    proposed_evidence_role: str = "CONTEXTUAL"
    answer_support: str = "PARTIAL"
    reasons: list[str] = Field(default_factory=list, max_length=5)


class RerankProposal(BaseModel):
    model_config = ConfigDict(extra="ignore")
    judgments: list[CandidateJudgment] = Field(default_factory=list, max_length=MAX_CANDIDATES)


def _digest(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


def _registered_source_context(candidate):
    """Bounded context from an operational, physically verified source locator."""
    location = candidate.get("structured_location") or {}
    if not location.get("physical_pdf_page") or not location.get("checksum"):
        return None
    context = location.get("context_before", "") + "\n" + location.get("context_after", "")
    if not context.strip():
        return None
    return {
        "text": context[:MAX_SOURCE_CONTEXT_CHARS],
        "physical_pdf_page": location["physical_pdf_page"],
        "source_digest": location["checksum"],
        "authority": "DOCUMENTARY_CONTEXT_ONLY; does not establish run conditions",
    }


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+(?:[.+/%-][a-z0-9]+)*", text.lower()))


def _hard_anchors(
    query: str, intent: Any, registry: Any, language: dict | None = None
) -> list[tuple[set[str], ...]]:
    """Return synonym groups that every expansion must preserve.

    The original query is always searched. This guard prevents a generated
    formulation from dropping literal numeric/source/run constraints or known
    registry-backed entity/property concepts. It is intentionally conservative.
    """
    anchors: list[tuple[set[str], ...]] = []
    tokens = _tokens(query)
    for match in re.finditer(
        r"(?<!\w)(?:\d+(?:\.\d+)?)(?:\s*(?:%|cm/s|mm/s|m/s|mmhg|kpa|pa))?",
        query,
        re.IGNORECASE,
    ):
        raw = match.group(0).strip().lower()
        if any(char.isdigit() for char in raw):
            anchors.append((_tokens(raw),))
    for match in re.finditer(
        r"\b(?:not|no|never|without|except|excluding|cannot|can't)\b", query, re.IGNORECASE
    ):
        anchors.append(({match.group(0).lower()},))
    if intent:
        for mention in [*intent.unresolved_mentions, *intent.ambiguities]:
            if not mention.startswith("multiple_values_for_relation:") and _tokens(
                mention
            ).issubset(tokens):
                anchors.append((_tokens(mention),))
        identity_mentions = [c.entity_id for c in intent.entity_constraints]
        identity_mentions.extend(intent.comparison.operands if intent.comparison else [])
        for identity in identity_mentions:
            aliases = {identity}
            if language:
                meta = language.get("entity_mentions", {}).get(identity, {})
                aliases.update(meta.get("aliases", []))
            present = any(_tokens(alias).issubset(tokens) for alias in aliases)
            if present:
                # All surface variants are safe alternatives for this one
                # already reviewed identity; each expansion must retain one.
                anchors.append(tuple(_tokens(alias) for alias in aliases if _tokens(alias)))
            else:
                anchors.append((_tokens(identity),))
        for constraint in intent.property_constraints:
            definition = registry.properties.get(constraint.property_id)
            names = {constraint.property_id.lower()}
            if definition:
                names.update(a.lower() for a in definition.aliases)
            alternatives = [_tokens(alias) for alias in names if alias]
            if any(alternative.issubset(tokens) for alternative in alternatives):
                anchors.append(tuple(alternatives))
            value = constraint.value
            if value.raw_expression:
                anchors.extend(
                    (_tokens(m.group(0)),)
                    for m in re.finditer(
                        r"\d+(?:\.\d+)?(?:\s*(?:%|cm/s|mm/s|m/s|mmhg|kpa|pa))?",
                        value.raw_expression,
                        re.IGNORECASE,
                    )
                )
        if language:
            for requested in intent.requested_information:
                aliases = {requested, *language.get("information_mentions", {}).get(requested, [])}
                present = any(_tokens(alias).issubset(tokens) for alias in aliases)
                if present:
                    anchors.append(tuple(_tokens(alias) for alias in aliases if _tokens(alias)))
        for source_id in intent.source_constraints:
            if _tokens(source_id).issubset(tokens):
                anchors.append((_tokens(source_id),))
    if language:
        for entity_id, meta in language.get("entity_mentions", {}).items():
            aliases = [entity_id, *meta.get("aliases", [])]
            if any(_tokens(alias).issubset(tokens) for alias in aliases):
                anchors.append(tuple(_tokens(alias) for alias in aliases if _tokens(alias)))
        for property_id, definition in registry.properties.items():
            aliases = [property_id, *definition.aliases]
            if any(_tokens(alias).issubset(tokens) for alias in aliases):
                anchors.append(tuple(_tokens(alias) for alias in aliases if _tokens(alias)))
    return [a for a in anchors if a]


def validate_expansion(
    query: str, expanded: str, intent: Any, registry: Any, language: dict | None = None
) -> tuple[bool, str]:
    if not expanded.strip() or len(expanded) > 500:
        return False, "empty_or_overlong"
    from nasa_fire_ai.query.expansion_contracts import numeric_equivalence

    valid_numeric, numeric_reason = numeric_equivalence(query, expanded)
    if not valid_numeric:
        return False, numeric_reason
    # Logical grouping is a hard contract even when all entity words survive.
    from nasa_fire_ai.query.expansion_contracts import PATTERN

    logical = lambda text: re.findall(r"\b(?:and|or)\b|[()]", PATTERN.sub("", text.lower()))
    if logical(query) != logical(expanded):
        return False, "logical_grouping_changed"
    source_tokens = _tokens(query)
    expanded_tokens = _tokens(expanded)
    anchors = _hard_anchors(query, intent, registry, language)
    # Typed quantities allow unit conversions; entity IDs remain lexical anchors.
    anchors = [
        a
        for a in anchors
        if not all(
            any(re.fullmatch(r"[0-9.]+", token) for token in alternative) for alternative in a
        )
    ]
    missing = [
        [sorted(alternative) for alternative in anchor]
        for anchor in anchors
        if not any(alternative.issubset(expanded_tokens) for alternative in anchor)
    ]
    # A numeric surface constraint remains a literal lexical anchor. If the
    # model changes a numeric value or unit, reject that expansion.
    if missing:
        return False, f"hard_anchor_missing:{missing}"
    if language:
        explicit_entities = {c.entity_id for c in intent.entity_constraints}
        explicit_entities.update(intent.comparison.operands if intent.comparison else [])
        for entity_id, meta in language.get("entity_mentions", {}).items():
            aliases = [entity_id, *meta.get("aliases", [])]
            present_in_query = any(_tokens(alias).issubset(source_tokens) for alias in aliases)
            present_in_expansion = any(
                _tokens(alias).issubset(expanded_tokens) for alias in aliases
            )
            if present_in_expansion and not present_in_query and entity_id not in explicit_entities:
                return False, f"added_registered_entity:{entity_id}"
        explicit_properties = {c.property_id for c in intent.property_constraints}
        for property_id, definition in registry.properties.items():
            aliases = [property_id, *definition.aliases]
            present_in_query = any(_tokens(alias).issubset(source_tokens) for alias in aliases)
            present_in_expansion = any(
                _tokens(alias).issubset(expanded_tokens) for alias in aliases
            )
            if (
                present_in_expansion
                and not present_in_query
                and property_id not in explicit_properties
            ):
                return False, f"added_registered_property:{property_id}"
        explicit_information = set(intent.requested_information)
        for class_id, aliases in language.get("information_mentions", {}).items():
            candidates = [class_id, *aliases]
            present_in_query = any(_tokens(alias).issubset(source_tokens) for alias in candidates)
            present_in_expansion = any(
                _tokens(alias).issubset(expanded_tokens) for alias in candidates
            )
            if (
                present_in_expansion
                and not present_in_query
                and class_id not in explicit_information
            ):
                return False, f"added_information_class:{class_id}"
    # Expansions are candidate discovery only; all are separately labeled
    # contextual and cannot weaken the native intent.
    if len(expanded_tokens) < min(2, len(source_tokens)):
        return False, "insufficient_query_content"
    # Unknown scientific wording cannot silently acquire an equivalence claim.
    # Strip only typed quantities, approved synonyms and ordinary request words.
    # Broader discovery remains available through the separate hypothesis contract.
    remaining = [PATTERN.sub("", text.lower()) for text in (query, expanded)]
    groups = []
    if language:
        groups.extend(
            [entity_id, *meta.get("aliases", [])]
            for entity_id, meta in language.get("entity_mentions", {}).items()
        )
        groups.extend(
            [class_id, *aliases]
            for class_id, aliases in language.get("information_mentions", {}).items()
        )
    groups.extend([pid, *meta.aliases] for pid, meta in registry.properties.items())
    for aliases in groups:
        if any(_tokens(a).issubset(source_tokens) for a in aliases if _tokens(a)):
            for index, text in enumerate(remaining):
                for alias in sorted(aliases, key=len, reverse=True):
                    text = re.sub(r"(?<!\w)" + re.escape(alias.lower()) + r"(?!\w)", " ", text)
                remaining[index] = text
    request_words = {
        "what",
        "which",
        "how",
        "about",
        "do",
        "does",
        "did",
        "has",
        "have",
        "the",
        "a",
        "an",
        "of",
        "in",
        "on",
        "at",
        "for",
        "to",
        "from",
        "find",
        "show",
        "tell",
        "me",
        "us",
        "please",
        "evidence",
        "information",
        "research",
        "results",
        "and",
        "or",
    }
    residuals = [_tokens(text) - request_words for text in remaining]
    if residuals[0] != residuals[1]:
        return False, "unverified_semantic_wording_change"
    return True, "hard_constraints_preserved"


class NemotronControlledReasoner:
    """Bounded JSON calls over the already configured NVIDIA client."""

    model_identity: str

    def __init__(
        self,
        client: Any,
        model: str,
        registry: Any,
        language: dict | None = None,
        event_sink: Any = None,
        cache: dict | None = None,
    ):
        self.client = client
        self.model_identity = model
        self.registry = registry
        self.language = language or {}
        self.event_sink = event_sink
        self.cache = cache if cache is not None else {}

    def _emit(self, event_type: str, payload: dict) -> None:
        if self.event_sink:
            self.event_sink({"event_type": event_type, **payload})

    def _json_call(self, system: str, user: str, max_tokens: int) -> tuple[dict, dict]:
        started = perf_counter()
        response = self.client.with_options(timeout=60, max_retries=0).chat.completions.create(
            model=self.model_identity,
            temperature=0,
            stream=False,
            max_tokens=max_tokens,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            response_format={"type": "json_object"},
            extra_body={"chat_template_kwargs": {"enable_thinking": False}, "reasoning_budget": 0},
        )
        content = response.choices[0].message.content or ""
        try:
            parsed = json.loads(content)
        except (json.JSONDecodeError, TypeError) as exc:
            cleaned = content.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            elif cleaned.startswith("```"):
                cleaned = cleaned[3:]
            cleaned = cleaned.removesuffix("```")
            start, end = cleaned.find("{"), cleaned.rfind("}")
            if start < 0 or end <= start:
                raise ValueError("invalid_structured_json") from exc
            try:
                parsed = json.loads(cleaned[start : end + 1])
            except json.JSONDecodeError as nested:
                raise ValueError("invalid_structured_json") from nested
        usage = getattr(response, "usage", None)
        return parsed, {
            "latency_ms": (perf_counter() - started) * 1000,
            "input_tokens": getattr(usage, "prompt_tokens", None),
            "output_tokens": getattr(usage, "completion_tokens", None),
        }

    def expand(self, query: str, intent: Any) -> dict:
        registry_digest = _digest(
            {
                "entities": sorted(self.registry.entities),
                "properties": [p.__dict__ for p in self.registry.properties.values()],
                "language": self.language,
                "classes": sorted(self.registry.class_metadata),
            }
        )
        key = _digest(
            [
                PROMPT_VERSION,
                self.model_identity,
                query,
                intent.model_dump(mode="json"),
                registry_digest,
            ]
        )
        cached = self.cache.get(key)
        if cached:
            return {**cached, "execution_mode": "COMPATIBLE_CACHE_REPLAY", "new_calls": 0}
        system = (
            "Generate at most three short alternate documentary search formulations for NASA fire-safety evidence. "
            'Return JSON {"queries":[string],"hypotheses":[{"query":string,"relationship":"UNVERIFIED_HYPOTHESIS|BROADER_DISCOVERY|NARROWER_DISCOVERY|SIBLING_DISCOVERY|RELATED_PHENOMENON|DOCUMENTARY_SYNONYM","requested_concept":string|null,"proposed_concept":string|null}]}. '
            "queries are strictly equivalent reformulations. hypotheses are exploratory searches, never facts or ontology aliases. "
            "Preserve all explicit materials, conditions, experiment/source identifiers, values, units, ranges, "
            "negation, comparisons, and requested information class in equivalent queries. "
            "Exploratory hypotheses may broaden or narrow search scope; declare unverified relationships honestly. "
            "Never imply that a hypothesis changes canonical constraints or supplies a taxonomy fact. "
            "Use only supplied approved concepts for terminology; keep output concise."
        )
        user = json.dumps(
            {
                "query": query,
                "validated_intent": intent.model_dump(mode="json"),
                "approved_properties": [
                    {"id": p.property_id, "aliases": p.aliases}
                    for p in self.registry.properties.values()
                ],
                "approved_entity_aliases": self.language.get("entity_mentions", {}),
                "approved_information_aliases": self.language.get("information_mentions", {}),
                "requested_classes": intent.requested_information,
            },
            ensure_ascii=False,
        )
        result: dict[str, Any] = {
            "execution_mode": "NEW_INFERENCE",
            "new_calls": 0,
            "version": PROMPT_VERSION,
            "model": self.model_identity,
            "query_digest": _digest(query),
            "intent_digest": _digest(intent.model_dump(mode="json")),
            "registry_digest": registry_digest,
            "cache_key": key,
            "accepted": [],
            "hypotheses": [],
            "rejected": [],
            "error": None,
            "usage": {},
        }
        try:
            result["new_calls"] = 1
            raw, usage = self._json_call(system, user, 500)
            proposal = ExpansionProposal.model_validate(raw)
            result["usage"] = usage
            result["hypotheses"] = [h.model_dump(mode="json") for h in proposal.hypotheses]
            seen = {query.casefold()}
            for candidate in proposal.queries:
                candidate = " ".join(candidate.split())
                if candidate.casefold() in seen:
                    continue
                seen.add(candidate.casefold())
                valid, reason = validate_expansion(
                    query, candidate, intent, self.registry, self.language
                )
                row = {"query": candidate, "accepted": valid, "reason": reason}
                result["accepted" if valid else "rejected"].append(row)
                if len(result["accepted"]) >= MAX_EXPANSIONS:
                    break
        except (ValueError, ValidationError, TimeoutError) as exc:
            result["error"] = type(exc).__name__
        except Exception as exc:  # noqa: BLE001 - sanitize optional external provider failures
            result["error"] = type(exc).__name__
        self.cache[key] = result
        self._emit("query_expansion", result)
        return result

    def rerank(self, query: str, intent: Any, candidates: list[dict]) -> dict:
        candidates = candidates[:MAX_RERANK_CANDIDATES]
        ids = {candidate["evidence_id"] for candidate in candidates}
        if not candidates:
            return {"judgments": [], "error": None, "usage": {}}
        cache_key = _digest(
            [
                RERANK_PROMPT_VERSION,
                self.model_identity,
                query,
                intent.model_dump(mode="json"),
                [
                    (
                        c["evidence_id"],
                        _digest(c.get("text", "")),
                        _digest(_registered_source_context(c)),
                    )
                    for c in candidates
                ],
            ]
        )
        cached = self.cache.get(cache_key)
        if cached and cached.get("error") is None:
            return {**cached, "execution_mode": "COMPATIBLE_CACHE_REPLAY", "new_calls": 0}
        system = (
            "Assess only topical/contextual usefulness of the supplied passages. "
            'Return compact JSON {"judgments":[{"evidence_id":string,"candidate_relevance":"HIGH|MEDIUM|LOW|UNCERTAIN",'
            '"supporting_span":"one exact short verbatim span or empty string","answer_support":"FULL|PARTIAL|NONE"}]}. '
            "Do not decide canonical identity, DIRECT/RELATED, source authority, or scientific truth. "
            "HIGH or MEDIUM requires a verbatim span copied exactly from that candidate. "
            "LOW or UNCERTAIN may use an empty span. Do not invent IDs, quotes, or facts."
            " Registered source context may resolve antecedents but never establish new run conditions. "
            "Supporting spans must still be copied from the candidate's own text."
        )
        hard_constraints = {
            "entities": [c.model_dump(mode="json") for c in intent.entity_constraints],
            "properties": [c.model_dump(mode="json") for c in intent.property_constraints],
            "comparison": intent.comparison.model_dump(mode="json") if intent.comparison else None,
            "requested_information": intent.requested_information,
            "sources": intent.source_constraints,
        }
        user = json.dumps(
            {
                "question": query,
                "validated_intent": hard_constraints,
                "candidates": [
                    {
                        "evidence_id": c["evidence_id"],
                        "source": c.get("source_metadata"),
                        "page": c.get("page"),
                        "section": c.get("section"),
                        "text": c.get("text", "")[:MAX_PASSAGE_CHARS],
                        "registered_source_context": _registered_source_context(c),
                    }
                    for c in candidates
                ],
            },
            ensure_ascii=False,
        )
        result = {
            "execution_mode": "NEW_INFERENCE",
            "new_calls": 0,
            "version": RERANK_PROMPT_VERSION,
            "model": self.model_identity,
            "cache_key": cache_key,
            "judgments": [],
            "invalid": [],
            "error": None,
            "usage": {},
        }
        try:
            result["new_calls"] = 1
            raw, usage = self._json_call(system, user, 900)
            proposal = RerankProposal.model_validate(raw)
            result["usage"] = usage
            passages = {c["evidence_id"]: c.get("text", "") for c in candidates}
            for judgment in proposal.judgments:
                if judgment.evidence_id not in ids:
                    result["invalid"].append(
                        {"evidence_id": judgment.evidence_id, "reason": "outside_candidate_set"}
                    )
                    continue
                if judgment.candidate_relevance not in {"HIGH", "MEDIUM", "LOW", "UNCERTAIN"}:
                    result["invalid"].append(
                        {"evidence_id": judgment.evidence_id, "reason": "invalid_relevance"}
                    )
                    continue
                supporting_span = judgment.supporting_span.strip()
                if supporting_span and supporting_span not in passages[judgment.evidence_id]:
                    result["invalid"].append(
                        {"evidence_id": judgment.evidence_id, "reason": "invalid_supporting_span"}
                    )
                    continue
                if judgment.candidate_relevance in {"HIGH", "MEDIUM"} and not supporting_span:
                    result["invalid"].append(
                        {"evidence_id": judgment.evidence_id, "reason": "missing_supporting_span"}
                    )
                    continue
                valid_assessments = []
                for assessment in judgment.constraint_assessments:
                    span = assessment.supporting_span
                    valid_index = assessment.constraint_index < len(
                        intent.entity_constraints
                    ) + len(intent.property_constraints)
                    if not valid_index or (span and span not in passages[judgment.evidence_id]):
                        result["invalid"].append(
                            {
                                "evidence_id": judgment.evidence_id,
                                "reason": "invalid_constraint_or_span",
                            }
                        )
                        continue
                    if assessment.status not in {"MATCH", "DIFFERS", "UNKNOWN"}:
                        result["invalid"].append(
                            {
                                "evidence_id": judgment.evidence_id,
                                "reason": "invalid_assessment_status",
                            }
                        )
                        continue
                    valid_assessments.append(assessment.model_dump(mode="json"))
                result["judgments"].append(
                    {
                        **judgment.model_dump(mode="json"),
                        "supporting_span": supporting_span,
                        "constraint_assessments": valid_assessments,
                        "authority": "UNVERIFIED_MODEL_PROPOSAL",
                        "classification_effect": "NONE",
                    }
                )
        except (ValueError, ValidationError, TimeoutError) as exc:
            result["error"] = type(exc).__name__
        except Exception as exc:  # noqa: BLE001 - sanitize optional external provider failures
            result["error"] = type(exc).__name__
        result["candidate_input_ids"] = sorted(ids)
        result["candidate_input_digest"] = _digest(
            [
                (
                    c["evidence_id"],
                    _digest(c.get("text", "")),
                    _digest(_registered_source_context(c)),
                )
                for c in candidates
            ]
        )
        result["effective_input_digest"] = _digest(json.loads(user))
        result["registered_source_context_ids"] = [
            c["evidence_id"] for c in candidates if _registered_source_context(c)
        ]
        self.cache[cache_key] = result
        self._emit("contextual_reranking", result)
        return result


def _filter_source_constraints(passages: list[dict], intent: Any, registry: Any) -> list[dict]:
    if not intent.source_constraints:
        return passages
    allowed = set(intent.source_constraints)
    filtered = []
    for passage in passages:
        metadata = registry.source_metadata(passage["evidence_id"]) or {}
        if metadata.get("source_id") in allowed:
            filtered.append(passage)
    return filtered


def run_ablation(
    query: str,
    intent: Any,
    store: Any,
    evidence_registry: Any,
    reasoner: NemotronControlledReasoner | None = None,
    flags: ControlledReasoningFlags | None = None,
    jev_advisor: Any = None,
    baseline_limit: int = 8,
    per_query_limit: int = 20,
) -> dict:
    """Run A/B/C/D on the same corpus; preserve the native bundle as authority.

    A uses the existing executor. B unions bounded FTS candidates from safe
    expansions. C reorders those candidates using contextual proposals. D adds
    an optional Jev rhetorical-class signal without filtering any candidate.
    """
    flags = flags or ControlledReasoningFlags()
    baseline = execute_native(
        intent,
        query,
        store,
        evidence_registry,
        limit=baseline_limit,
        hierarchical=flags.hierarchical_retrieval,
        relational=flags.relational_related,
    )
    baseline_ids = [p["evidence_id"] for p in baseline.bundle.evidence_passages]
    result: dict[str, Any] = {
        "query_digest": _digest(query),
        "intent_digest": _digest(intent.model_dump(mode="json")),
        "model": getattr(reasoner, "model_identity", None),
        "prompt_versions": {"expansion": PROMPT_VERSION, "reranking": RERANK_PROMPT_VERSION},
        "features": flags.__dict__,
        "native_direct_ids": [x["id"] for x in baseline.bundle.direct_evidence],
        "native_related_ids": [x["id"] for x in baseline.bundle.related_evidence],
        "latency_ms": {"native_total": baseline.latency_ms["total"]},
        "configurations": {},
        "errors": [],
    }
    result["_native_execution"] = baseline
    A = {"candidate_ids": baseline_ids, "contextual_candidates": [], "calls": 0}
    result["configurations"]["A"] = A
    expansion = {"accepted": [], "rejected": [], "error": "disabled", "usage": {}}
    if flags.query_expansion and reasoner:
        expansion_started = perf_counter()
        expansion = json.loads(json.dumps(reasoner.expand(query, intent)))
        result["latency_ms"]["query_expansion_current_execution"] = (
            perf_counter() - expansion_started
        ) * 1000
        if expansion.get("usage", {}).get("latency_ms") is not None:
            result["latency_ms"]["query_expansion"] = expansion["usage"]["latency_ms"]
    for raw_hypothesis in expansion.get("hypotheses", []):
        try:
            hypothesis = DiscoveryHypothesis.model_validate(raw_hypothesis)
            valid, reason = validate_discovery(hypothesis, intent, store, evidence_registry)
            row = {
                **hypothesis.model_dump(mode="json"),
                "accepted": valid,
                "reason": reason,
                "contract": "EXPLORATORY_DISCOVERY",
                "canonical_effect": "NONE",
            }
            expansion["accepted" if valid else "rejected"].append(row)
        except (ValueError, LookupError, KeyError, TypeError):
            expansion["rejected"].append({"reason": "invalid_discovery_contract"})
    discovery_active = bool(
        flags.query_expansion
        and reasoner
        and expansion.get("error") is None
        and expansion.get("usage")
    )
    discovery_active |= bool(
        (flags.hierarchical_retrieval or flags.relational_related)
        and (intent.clarification_required or intent.unresolved_mentions)
    )
    formulations = (
        [query] + [x["query"] for x in expansion.get("accepted", [])] if discovery_active else []
    )
    pool: dict[str, dict] = {p["evidence_id"]: dict(p) for p in baseline.bundle.evidence_passages}
    search_traces = []
    if discovery_active:
        for formulation in formulations:
            hits = _filter_source_constraints(
                evidence_registry.search(formulation, limit=per_query_limit),
                intent,
                evidence_registry,
            )
            search_traces.append(
                {"query_digest": _digest(formulation), "hits": [p["evidence_id"] for p in hits]}
            )
            for p in hits:
                p["source_metadata"] = evidence_registry.source_metadata(p["evidence_id"])
                pool.setdefault(p["evidence_id"], p)
                if len(pool) >= MAX_CANDIDATES:
                    break
            if len(pool) >= MAX_CANDIDATES:
                break
    ordered_pool = list(pool.values())[:MAX_CANDIDATES]
    B = {
        "candidate_ids": [p["evidence_id"] for p in ordered_pool],
        "contextual_candidates": [x for x in ordered_pool if x["evidence_id"] not in baseline_ids],
        "expansion": expansion,
        "search_traces": search_traces,
        "calls": expansion.get("new_calls", int(bool(expansion.get("usage")))),
    }
    result["configurations"]["B"] = B
    rerank = {"judgments": [], "invalid": [], "error": "disabled", "usage": {}}
    ranked = ordered_pool
    selective_reason = (
        "ambiguous_or_documentary_pool"
        if intent.ambiguities
        or intent.unresolved_mentions
        or len(baseline.bundle.related_evidence) > 1
        or (not baseline.bundle.direct_evidence and len(ordered_pool) > 1)
        else "adequate_deterministic_evidence"
    )
    result["selective_reranking"] = {
        "enabled": flags.selective_reranking,
        "reason": selective_reason,
    }
    if (
        flags.contextual_reranking
        and reasoner
        and (not flags.selective_reranking or selective_reason != "adequate_deterministic_evidence")
    ):
        rerank_started = perf_counter()
        rerank = reasoner.rerank(query, intent, ordered_pool)
        result["latency_ms"]["reranking_current_execution"] = (
            perf_counter() - rerank_started
        ) * 1000
        result["latency_ms"]["reranking"] = rerank.get("usage", {}).get("latency_ms")
        relevance = {
            j["evidence_id"]: j["candidate_relevance"] for j in rerank.get("judgments", [])
        }
        tiers = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "UNCERTAIN": 3}
        original_order = {p["evidence_id"]: i for i, p in enumerate(ordered_pool)}
        ranked = sorted(
            ordered_pool,
            key=lambda p: (
                tiers.get(relevance.get(p["evidence_id"], "UNCERTAIN"), 3),
                original_order[p["evidence_id"]],
            ),
        )
    judgments = {j["evidence_id"]: j for j in rerank.get("judgments", [])}
    contextual = []
    for p in ranked:
        eid = p["evidence_id"]
        if eid in baseline_ids:
            continue
        contextual.append(
            {
                "evidence_id": eid,
                "status": "CONTEXTUAL_CANDIDATE",
                "passage": p.get("text", ""),
                "page": p.get("page"),
                "section": p.get("section"),
                "source_metadata": p.get("source_metadata")
                or evidence_registry.source_metadata(eid),
                "judgment": judgments.get(eid),
                "canonical_effect": "NONE",
            }
        )
    C = {
        "candidate_ids": [p["evidence_id"] for p in ranked],
        "contextual_candidates": contextual,
        "reranking": rerank,
        "calls": rerank.get("new_calls", int(bool(rerank.get("usage")))),
    }
    result["configurations"]["C"] = C
    D = json.loads(json.dumps(C))
    D["jev"] = {"enabled": flags.jev_advisory_triage, "judgments": [], "error": "disabled"}
    if flags.jev_advisory_triage and jev_advisor:
        advisory = []
        proposal_by_id = {}
        if not intent.requested_information:
            D["jev"] = {
                "enabled": True,
                "judgments": [],
                "error": None,
                "status": "NOT_APPLICABLE_NO_INFORMATION_CLASS_REQUEST",
            }
            result["configurations"]["D"] = D
            result["bundle"] = baseline.bundle
            return result
        try:
            # Jev signals rhetorical class only. It cannot remove candidates,
            # alter canonical results, or override Nemotron hard constraints.
            for candidate in ranked[:MAX_JEV_CANDIDATES]:
                data = dict(candidate)
                data["source_metadata"] = data.get(
                    "source_metadata"
                ) or evidence_registry.source_metadata(data["evidence_id"])
                decision = jev_advisor(data)
                proposal_by_id[data["evidence_id"]] = decision
                advisory.append(
                    {
                        "evidence_id": data["evidence_id"],
                        "proposal": decision,
                        "authority": "ADVISORY_ONLY",
                    }
                )
            requested = set(intent.requested_information)
            equivalents = {
                "ReportedObservation": {"ReportedObservation", "ReportedExperimentalObservation"},
                "OpenQuestion": {"OpenQuestion", "NASAIdentifiedOpenQuestion"},
            }

            def class_alignment(candidate):
                label = proposal_by_id.get(candidate["evidence_id"], {}).get("label")
                return any(label in equivalents.get(target, {target}) for target in requested)

            old_order = {p["evidence_id"]: i for i, p in enumerate(ranked)}
            d_ranked = sorted(
                ranked,
                key=lambda p: (
                    not class_alignment(p) if p["evidence_id"] in proposal_by_id else True,
                    old_order[p["evidence_id"]],
                ),
            )
            D["candidate_ids"] = [p["evidence_id"] for p in d_ranked]
            D["contextual_candidates"] = [candidate for candidate in contextual]
            D["contextual_candidates"].sort(
                key=lambda c: D["candidate_ids"].index(c["evidence_id"])
            )
            D["jev"] = {"enabled": True, "judgments": advisory, "error": None}
        except Exception as exc:  # noqa: BLE001 - optional Jev must fail open to prior ranking
            D["jev"] = {"enabled": True, "judgments": advisory, "error": type(exc).__name__}
    result["configurations"]["D"] = D
    result["bundle"] = baseline.bundle
    # D does not reorder the ranked list: rhetoric class is not topical relevance.
    return result
