"""Phase-3 orchestration with an optional bounded native V2 investigation loop."""

import hashlib
import os
import time
from pathlib import Path

from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.llm.interfaces import (
    GroundedSynthesisLLM,
    NvidiaGroundedSynthesizer,
    NvidiaQueryInterpreter,
    ProviderFailure,
    QueryInterpreterLLM,
)
from nasa_fire_ai.models import (
    AnswerResponse,
    ConversationContext,
    ExecutionTrace,
    GroundedAnswerDraft,
    ProposedQueryIntent,
)
from nasa_fire_ai.query.phase3 import (
    deterministic_proposal,
    lexicon_digest,
    ontology_digest,
    validate_proposed_intent,
)
from nasa_fire_ai.services.grounding import GroundingValidator
from nasa_fire_ai.services.pipeline import build_bundle
from nasa_fire_ai.services.product import scientific_answer
from nasa_fire_ai.services.renderer import render, render_grounded


class Phase3AssistantService:
    def __init__(
        self,
        root: Path | None = None,
        settings: Settings | None = None,
        interpreter: QueryInterpreterLLM | None = None,
        synthesizer: GroundedSynthesisLLM | None = None,
    ):
        self.root = root or Path(__file__).resolve().parents[3]
        self.settings = settings or Settings()
        self.registry = EvidenceRegistry(self.settings.registry_path)
        model = self.settings.nvidia_phase3_model
        self.interpreter = interpreter or (
            NvidiaQueryInterpreter(
                self.settings.nvidia_api_key, self.settings.nvidia_base_url, model
            )
            if self.settings.nvidia_api_key
            else None
        )
        self.synthesizer = synthesizer or (
            NvidiaGroundedSynthesizer(
                self.settings.nvidia_api_key, self.settings.nvidia_base_url, model
            )
            if self.settings.nvidia_api_key
            else None
        )
        self._interpretation_cache: dict[str, object] = {}

    def _cache_key(self, query: str, context: ConversationContext | None) -> str:
        model = self.interpreter.model_identity if self.interpreter else "deterministic"
        prompt = (
            self.interpreter.prompt_version if self.interpreter else "deterministic-proposal-v1"
        )
        raw = "|".join(
            [
                query,
                model,
                prompt,
                "phase3-proposed-v1",
                lexicon_digest(),
                ontology_digest(),
                (context or ConversationContext()).model_dump_json(),
            ]
        )
        return hashlib.sha256(raw.encode()).hexdigest()

    def answer_query(
        self,
        query: str,
        conversation_context: ConversationContext | None = None,
        detail_level: str = "standard",
    ) -> AnswerResponse:
        if detail_level not in {"concise", "standard", "technical"}:
            raise ValueError("detail_level must be concise, standard, or technical")
        if os.getenv("NATIVE_V2_QUERY_ENABLED", "false").lower() == "true":
            return self._answer_native_query(query, conversation_context, detail_level)
        began = time.perf_counter()
        trace = ExecutionTrace(raw_query=query)
        key = self._cache_key(query, conversation_context)
        interpretation_start = time.perf_counter()
        proposal = self._interpretation_cache.get(key)
        if proposal is None:
            cached = self.registry.get_phase3_cache(key, "validated-interpretation-proposal")
            if cached:
                proposal = ProposedQueryIntent.model_validate(cached)
        if proposal is None:
            if self.interpreter:
                try:
                    proposal = self.interpreter.interpret(query)
                    trace.model_metadata["interpreter"] = self.interpreter.metadata()
                except (ProviderFailure, ValueError) as exc:
                    trace.fallback_status.append(f"interpreter fallback: {type(exc).__name__}")
                    proposal = deterministic_proposal(query)
            else:
                trace.fallback_status.append("interpreter fallback: provider unavailable")
                proposal = deterministic_proposal(query)
            self._interpretation_cache[key] = proposal
            self.registry.set_phase3_cache(
                key,
                "validated-interpretation-proposal",
                proposal.model_dump(mode="json"),  # type: ignore[union-attr]
            )
        elif self.interpreter is None:
            # Cache content was produced under an identical model/ontology/lexicon key;
            # still disclose that no live LLM was used for this request.
            trace.fallback_status.append(
                "interpreter fallback: provider unavailable (cached proposal)"
            )
        trace.proposed_intent = proposal  # type: ignore[assignment]
        validated = validate_proposed_intent(proposal, query, conversation_context)  # type: ignore[arg-type]
        trace.validated_intent = validated
        trace.validation_actions = validated.validation_actions
        trace.latency_ms["interpretation"] = (time.perf_counter() - interpretation_start) * 1000

        retrieval_start = time.perf_counter()
        bundle = build_bundle(validated.intent, query, self.root, self.registry)
        bundle.coverage_notes.extend(
            ["Ambiguous terms were not used as canonical retrieval constraints."]
            if validated.ambiguities
            else []
        )
        bundle.retrieval_metadata = {"architecture": "KG + FTS5/BM25", "vectors_enabled": False}
        trace.evidence_ids = [p["evidence_id"] for p in bundle.evidence_passages]
        trace.latency_ms["retrieval"] = (time.perf_counter() - retrieval_start) * 1000

        draft: GroundedAnswerDraft | None = None
        synthesis_start = time.perf_counter()
        if self.synthesizer:
            try:
                candidate = self.synthesizer.synthesize(bundle)
                result = GroundingValidator().validate(candidate, bundle)
                trace.grounding_valid = result.valid
                if not result.valid:
                    raise ProviderFailure(
                        "grounding validation rejected draft: " + "; ".join(result.errors)
                    )
                draft = candidate
                trace.model_metadata["synthesizer"] = self.synthesizer.metadata()
            except (ProviderFailure, ValueError) as exc:
                trace.fallback_status.append(f"synthesis fallback: {type(exc).__name__}")
        else:
            trace.fallback_status.append("synthesis fallback: provider unavailable")
        trace.latency_ms["synthesis_and_validation"] = (
            time.perf_counter() - synthesis_start
        ) * 1000

        answer = scientific_answer(query, bundle, self.root)
        if draft:
            answer.generated_claims = draft.claims
            answer.coverage_notes = list(
                dict.fromkeys(answer.coverage_notes + draft.coverage_notes)
            )
            rendered = render_grounded(draft, answer, detail_level)
        else:
            rendered = render(bundle)
        trace.latency_ms["total"] = (time.perf_counter() - began) * 1000
        return AnswerResponse(
            answer=answer,
            rendered_answer=rendered,
            validated_intent=validated,
            evidence_bundle=bundle,
            draft=draft,
            trace=trace,
        )

    def _answer_native_query(self, query, context, detail_level="standard"):
        """Route the existing app/service envelope through the native V2 executor."""
        import yaml

        from nasa_fire_ai.ingestion.semantic import project_legacy
        from nasa_fire_ai.models import QueryIntent, ScientificAnswer, ValidatedQueryIntent
        from nasa_fire_ai.services.native import answer_native_text

        signature = (
            tuple(
                tuple(row)
                for row in self.registry.db.execute(
                    "SELECT package_id,digest FROM research_active ORDER BY package_id"
                )
            )
            if self.registry.db.execute(
                "SELECT 1 FROM sqlite_master WHERE name='research_active'"
            ).fetchone()
            else (),
            tuple(
                tuple(row)
                for row in self.registry.db.execute(
                    "SELECT candidate_id,review_status,resolution_status FROM semantic_staging ORDER BY candidate_id"
                )
            ),
            self.registry.db.execute("PRAGMA data_version").fetchone()[0],
            tuple(
                tuple(row)
                for row in self.registry.db.execute(
                    "SELECT source_id,status FROM sources ORDER BY source_id"
                )
            ),
            tuple(
                self.registry.db.execute(
                    "SELECT (SELECT count(*) FROM documents),(SELECT max(rowid) FROM documents),(SELECT count(*) FROM passages),(SELECT max(rowid) FROM passages)"
                ).fetchone()
            ),
            tuple(
                (path.name, path.stat().st_mtime_ns, path.stat().st_size)
                for path in sorted((self.root / "data/canonical").glob("*.json"))
            ),
            tuple(
                (flag, os.getenv(flag, "false"))
                for flag in (
                    "SCIENTIFIC_CONTEXT_RESOLUTION_ENABLED",
                    "SOURCE_KNOWLEDGE_ENRICHMENT_ENABLED",
                    "ONTOLOGY_GRAPH_ENRICHMENT_ENABLED",
                )
            ),
        )
        if (
            not hasattr(self, "_native_store")
            or getattr(self, "_native_graph_signature", signature) != signature
        ):
            self._native_store = project_legacy(self.root, self.registry)
        self._native_graph_signature = signature
        language = yaml.safe_load((self.root / "domain/query_language_v2.yaml").read_text())
        response = answer_native_text(
            query, self._native_store, self.registry, language, context=context
        )
        if os.getenv("AUTONOMOUS_RESEARCH_ENABLED", "false").lower() == "true":
            from nasa_fire_ai.services.investigation import ResearchBudget, investigate

            planner = None
            if (
                os.getenv("NEMOTRON_RESEARCH_PLANNING_ENABLED", "false").lower() == "true"
                and self.settings.nvidia_api_key
            ):
                from nasa_fire_ai.llm.research import NvidiaResearchPlanner

                planner = NvidiaResearchPlanner(
                    self.settings.nvidia_api_key,
                    self.settings.nvidia_base_url,
                    self.settings.nvidia_phase3_model,
                    self.registry,
                )
            investigate(
                query,
                response.execution,
                self._native_store,
                self.registry,
                budget=ResearchBudget(
                    max_rounds=int(os.getenv("RESEARCH_MAX_ROUNDS", "3")),
                    max_actions=int(os.getenv("RESEARCH_MAX_ACTIONS", "8")),
                    max_candidates=int(os.getenv("RESEARCH_MAX_CANDIDATES", "8")),
                    timeout_seconds=float(os.getenv("RESEARCH_TIMEOUT_SECONDS", "30")),
                ),
                planner=planner,
            )
        intent = response.execution.plan.intent
        # This is the established display envelope only. Execution has already
        # completed using QueryIntentV2 and the native graph.
        display = QueryIntent(
            materials=[
                c.entity_id for c in intent.entity_constraints if c.relation == "hasMaterial"
            ],
            investigations=[
                c.entity_id
                for c in intent.entity_constraints
                if c.relation == "belongsToInvestigation"
            ],
            gravity_conditions=[
                c.entity_id
                for c in intent.entity_constraints
                if c.relation == "hasGravityCondition"
            ],
        )
        validated = ValidatedQueryIntent(
            intent=display,
            raw_query=query,
            raw_unresolved_terms=intent.unresolved_mentions,
            ambiguities=intent.ambiguities,
            clarification_required=intent.clarification_required,
            clarification="Scientific scope needs clarification."
            if intent.clarification_required
            else None,
            validation_actions=[
                "QueryIntentV2 native execution; compatibility intent is display-only"
            ],
            ontology_digest=ontology_digest(),
            lexicon_digest=lexicon_digest(),
        )
        bundle = response.execution.bundle
        bundle.retrieval_metadata["scientific_question"] = query
        from nasa_fire_ai.services.curation import scientific_focus

        bundle.retrieval_metadata["scientific_focus_question"] = scientific_focus(
            query, self._native_store
        )
        from nasa_fire_ai.ingestion.scientific_proposals import search_staged

        bundle.retrieval_metadata["staged_scientific_knowledge"] = search_staged(
            query, self.registry
        )
        rendered_answer = response.rendered_answer
        if intent.schema_version == "query-intent-v2":
            from nasa_fire_ai.services.scientific_synthesis import render_scientific

            if (
                os.getenv("NEMOTRON_SCIENTIFIC_SELECTION_ENABLED", "false").lower() == "true"
                and self.settings.nvidia_api_key
            ):
                from nasa_fire_ai.llm.scientific_selection import NvidiaScientificSelector

                selector = NvidiaScientificSelector(
                    self.settings.nvidia_api_key,
                    self.settings.nvidia_base_url,
                    self.settings.nvidia_phase3_model,
                )
                bundle.retrieval_metadata["nemotron_scientific_selection"] = selector.select(
                    query,
                    bundle,
                    synthesis=os.getenv("NEMOTRON_SCIENTIFIC_SYNTHESIS_ENABLED", "false").lower()
                    == "true",
                )
            rendered_answer = render_scientific(
                bundle, detail_level=detail_level, registry=self.registry, store=self._native_store
            )
        bundle.query_intent = display
        status = (
            "DIRECT_EVIDENCE"
            if bundle.direct_evidence
            else "RELATED_EVIDENCE"
            if bundle.related_evidence
            else "NO_DIRECT_EVIDENCE"
        )
        answer = ScientificAnswer(
            query=query,
            query_intent=display,
            direct_evidence_status=status,
            direct_evidence=bundle.direct_evidence,
            related_evidence=bundle.related_evidence,
            experimental_interventions=bundle.interventions,
            observations=bundle.experimental_observations,
            measurements=bundle.measurements,
            nasa_conclusions=bundle.nasa_conclusions,
            safety_implications=bundle.safety_implications,
            requirements=bundle.requirements,
            guidance=bundle.guidance,
            design_test_criteria=bundle.design_test_criteria,
            nasa_identified_open_questions=bundle.nasa_identified_open_questions,
            publications=bundle.publications,
            sources=bundle.evidence_passages,
            comparison=bundle.comparison,
            coverage_notes=bundle.coverage_notes,
            generated_claims=bundle.retrieval_metadata.get("scientific_synthesis", {}).get(
                "selected_claims", []
            ),
        )
        trace = ExecutionTrace(
            raw_query=query,
            validated_intent=validated,
            validation_actions=validated.validation_actions,
            evidence_ids=[p["evidence_id"] for p in bundle.evidence_passages],
            model_metadata={
                "query_intent_v2": intent.model_dump(mode="json"),
                "scientific_context": bundle.retrieval_metadata.get("scientific_context", {}),
                "investigation": bundle.retrieval_metadata.get("investigation", {}),
            },
            latency_ms=response.execution.latency_ms,
        )
        return AnswerResponse(
            answer=answer,
            rendered_answer=rendered_answer,
            validated_intent=validated,
            evidence_bundle=bundle,
            trace=trace,
        )
