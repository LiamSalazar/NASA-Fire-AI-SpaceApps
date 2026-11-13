import json
from types import SimpleNamespace

from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.semantic import load_semantic_registry
from nasa_fire_ai.query.controlled_reasoning import (
    ControlledReasoningFlags,
    NemotronControlledReasoner,
    run_ablation,
    validate_expansion,
)
from nasa_fire_ai.query.native import SemanticGraph
from nasa_fire_ai.query.native_interpreter import MinimalInterpretationV2, resolve_minimal
from nasa_fire_ai.query.v2 import EntityConstraintV2, QueryIntentV2

ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]


class FakeClient:
    def __init__(self, body):
        self.body = body
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def with_options(self, **_kwargs):
        return self

    def create(self, **_kwargs):
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(self.body)))],
            usage=SimpleNamespace(prompt_tokens=10, completion_tokens=10),
        )


class StaticReasoner:
    model_identity = "test-model"

    def expand(self, _query, _intent):
        return {"accepted": [], "rejected": [], "error": None, "usage": {"latency_ms": 1}}


def test_expansion_preserves_hard_scientific_surface_and_registry_aliases():
    registry = load_semantic_registry(ROOT / "domain/semantic_registry.yaml")
    language = __import__("yaml").safe_load((ROOT / "domain/query_language_v2.yaml").read_text())
    intent = QueryIntentV2(
        entity_constraints=[
            EntityConstraintV2(relation="hasMaterial", entity_id="PMMA"),
            EntityConstraintV2(relation="hasGravityCondition", entity_id="microgravity"),
        ]
    )
    assert validate_expansion(
        "PMMA in microgravity", "polymethyl methacrylate in low-g", intent, registry, language
    ) == (True, "hard_constraints_preserved")
    assert not validate_expansion(
        "PMMA in microgravity at 0.2 m/s",
        "PMMA experiment in microgravity at 0.3 m/s",
        intent,
        registry,
        language,
    )[0]
    assert not validate_expansion(
        "PMMA in microgravity at 0.2 m/s",
        "PMMA suppression test in microgravity",
        intent,
        registry,
        language,
    )[0]
    assert not validate_expansion(
        "What did NASA observe when the fire grew?",
        "NASA observation of PMMA fire growth in microgravity",
        QueryIntentV2(),
        registry,
        language,
    )[0]


def test_expansion_rejects_negation_and_source_loss():
    registry = load_semantic_registry(ROOT / "domain/semantic_registry.yaml")
    intent = QueryIntentV2(source_constraints=["ntrs-20210011385"])
    assert not validate_expansion(
        "not a direct match from ntrs-20210011385",
        "a direct match from ntrs-20210011385",
        intent,
        registry,
    )[0]
    assert not validate_expansion(
        "find source ntrs-20210011385",
        "find a source about spacecraft fire",
        intent,
        registry,
    )[0]


def test_reranker_rejects_unknown_ids_and_unverifiable_spans():
    registry = load_semantic_registry(ROOT / "domain/semantic_registry.yaml")
    model = NemotronControlledReasoner(
        FakeClient(
            {
                "judgments": [
                    {
                        "evidence_id": "E-valid",
                        "candidate_relevance": "HIGH",
                        "supporting_span": "made-up quote",
                        "constraint_assessments": [
                            {
                                "constraint_index": 0,
                                "status": "MATCH",
                                "supporting_span": "made-up quote",
                            }
                        ],
                        "proposed_evidence_role": "DIRECT",
                        "answer_support": "FULL",
                        "reasons": ["candidate"],
                    },
                    {
                        "evidence_id": "E-invented",
                        "candidate_relevance": "HIGH",
                        "supporting_span": "made-up quote",
                        "constraint_assessments": [],
                        "proposed_evidence_role": "DIRECT",
                        "answer_support": "FULL",
                        "reasons": [],
                    },
                ]
            }
        ),
        "test-model",
        registry,
    )
    intent = QueryIntentV2(
        entity_constraints=[EntityConstraintV2(relation="hasMaterial", entity_id="PMMA")]
    )
    result = model.rerank(
        "PMMA experiment",
        intent,
        [{"evidence_id": "E-valid", "text": "NASA observed PMMA combustion."}],
    )
    assert result["judgments"] == []
    assert {x["reason"] for x in result["invalid"]} == {
        "invalid_supporting_span",
        "outside_candidate_set",
    }


def test_reranker_accepts_only_whitelisted_ids_with_verbatim_context():
    registry = load_semantic_registry(ROOT / "domain/semantic_registry.yaml")
    model = NemotronControlledReasoner(
        FakeClient(
            {
                "judgments": [
                    {
                        "evidence_id": "E-valid",
                        "candidate_relevance": "HIGH",
                        "supporting_span": "NASA observed PMMA combustion.",
                        "proposed_evidence_role": "DIRECT",
                    }
                ]
            }
        ),
        "test-model",
        registry,
    )
    result = model.rerank(
        "PMMA experiment",
        QueryIntentV2(),
        [{"evidence_id": "E-valid", "text": "NASA observed PMMA combustion."}],
    )
    assert len(result["judgments"]) == 1
    assert result["judgments"][0]["supporting_span"] == "NASA observed PMMA combustion."
    assert result["judgments"][0]["authority"] == "UNVERIFIED_MODEL_PROPOSAL"
    assert result["judgments"][0]["classification_effect"] == "NONE"


def test_ablation_keeps_contextual_discovery_out_of_scientific_bundle(tmp_path):
    evidence = EvidenceRegistry(tmp_path / "evidence.sqlite")
    evidence.add_source(
        {"source_id": "SRC", "title": "NASA fire report", "url": "https://nasa.gov/report"}
    )
    evidence.add_document("doc", "SRC", "NASA fire report")
    evidence.add_passage(
        {
            "evidence_id": "E-context",
            "document_id": "doc",
            "page": 1,
            "section": "Results",
            "text": "The report discusses spacecraft fire behavior.",
            "start_offset": None,
            "end_offset": None,
            "raw_file": None,
            "checksum": None,
        }
    )
    registry = load_semantic_registry(ROOT / "domain/semantic_registry.yaml")
    store = SemanticGraph(registry)
    intent = QueryIntentV2(unresolved_mentions=["unknown material"])
    result = run_ablation(
        "unknown material spacecraft fire",
        intent,
        store,
        evidence,
        reasoner=StaticReasoner(),
        flags=ControlledReasoningFlags(query_expansion=True),
        per_query_limit=10,
    )
    assert set(result["configurations"]) == {"A", "B", "C", "D"}
    assert "E-context" in result["configurations"]["B"]["candidate_ids"]
    assert result["bundle"].direct_evidence == []
    assert result["bundle"].related_evidence == []
    assert result["bundle"].evidence_passages == []
    assert result["configurations"]["C"]["contextual_candidates"][0]["canonical_effect"] == "NONE"


def test_controlled_response_labels_candidates_as_unverified_context(tmp_path):
    from nasa_fire_ai.services.native import answer_native_controlled

    evidence = EvidenceRegistry(tmp_path / "evidence.sqlite")
    evidence.add_source(
        {"source_id": "SRC", "title": "NASA fire report", "url": "https://nasa.gov/report"}
    )
    evidence.add_document("doc", "SRC", "NASA fire report")
    evidence.add_passage(
        {
            "evidence_id": "E-context",
            "document_id": "doc",
            "page": 1,
            "section": "Results",
            "text": "The report discusses spacecraft fire behavior.",
            "start_offset": None,
            "end_offset": None,
            "raw_file": None,
            "checksum": None,
        }
    )
    registry = load_semantic_registry(ROOT / "domain/semantic_registry.yaml")
    store = SemanticGraph(registry)
    response = answer_native_controlled(
        QueryIntentV2(unresolved_mentions=["unknown material"]),
        "unknown material spacecraft fire",
        store,
        evidence,
        reasoner=StaticReasoner(),
        flags=ControlledReasoningFlags(query_expansion=True),
    )
    assert response.execution.bundle.discovery_candidates
    assert "not scientific support" in response.rendered_answer
    assert "E-context" in response.rendered_answer
    assert response.execution.bundle.evidence_passages == []


def test_feature_flags_are_opt_in_by_default(monkeypatch):
    for key in (
        "SEMANTIC_QUERY_EXPANSION_ENABLED",
        "CONTEXTUAL_RERANKING_ENABLED",
        "JEV_ADVISORY_TRIAGE_ENABLED",
        "SCIENTIFIC_PARAPHRASE_ENABLED",
    ):
        monkeypatch.delenv(key, raising=False)
    assert ControlledReasoningFlags.from_environment() == ControlledReasoningFlags()


def test_multiple_values_for_one_relation_require_clarification_not_false_conjunction():
    import yaml

    registry = load_semantic_registry(ROOT / "domain/semantic_registry.yaml")
    language = yaml.safe_load((ROOT / "domain/query_language_v2.yaml").read_text())
    query = "PMMA and SIBAL under microgravity"
    proposal = MinimalInterpretationV2(
        operation="search",
        entities=["PMMA", "SIBAL", "microgravity"],
    )
    intent = resolve_minimal(proposal, registry, language, query=query)
    assert {x.relation for x in intent.entity_constraints} >= {"hasMaterial"}
    assert intent.clarification_required
    assert "multiple_values_for_relation:hasMaterial" in intent.ambiguities
    assert intent.comparison is None


def test_contextual_rerank_requires_verbatim_span_for_positive_relevance():
    registry = load_semantic_registry(ROOT / "domain/semantic_registry.yaml")
    model = NemotronControlledReasoner(
        FakeClient(
            {
                "judgments": [
                    {
                        "evidence_id": "E-valid",
                        "candidate_relevance": "HIGH",
                        "supporting_span": "fabricated wording",
                        "answer_support": "FULL",
                    }
                ]
            }
        ),
        "test-model",
        registry,
    )
    result = model.rerank(
        "PMMA fire",
        QueryIntentV2(),
        [{"evidence_id": "E-valid", "text": "NASA reported an experiment."}],
    )
    assert result["judgments"] == []
    assert result["invalid"] == [{"evidence_id": "E-valid", "reason": "invalid_supporting_span"}]


def test_natural_language_controlled_boundary_clarifies_ambiguous_grouping(tmp_path):
    import yaml

    from nasa_fire_ai.services.native import answer_native_controlled_text

    evidence = EvidenceRegistry(tmp_path / "evidence.sqlite")
    registry = load_semantic_registry(ROOT / "domain/semantic_registry.yaml")
    store = SemanticGraph(registry)
    language = yaml.safe_load((ROOT / "domain/query_language_v2.yaml").read_text())

    class FakeInterpreter:
        def interpret_minimal(self, _query):
            return MinimalInterpretationV2(entities=["PMMA", "SIBAL", "microgravity"])

    response = answer_native_controlled_text(
        "PMMA and SIBAL under microgravity",
        store,
        evidence,
        language,
        interpreter=FakeInterpreter(),
        reasoner=StaticReasoner(),
        flags=ControlledReasoningFlags(query_expansion=True, contextual_reranking=True),
    )
    intent = response.execution.bundle.retrieval_metadata["query_intent_v2"]
    assert intent["clarification_required"]
    assert response.controlled_trace["features"] == ControlledReasoningFlags().__dict__
    assert "Please clarify" in response.rendered_answer
    assert not response.execution.bundle.discovery_candidates


def test_source_location_labels_unverified_page_without_fabricating_pdf_location():
    from nasa_fire_ai.services.native import _source_location

    assert _source_location({"page": 1}) == "recorded page 1 (physical PDF page unverified)"
    assert _source_location({"page": 16, "page_location_verified": True}) == "PDF page 16"
    assert _source_location({"page": None, "section": "Results"}) == "Results"


def test_comparison_renderer_shows_recorded_differences_and_unknowns_with_evidence():
    from nasa_fire_ai.models import EvidenceBundle, ExperimentComparison, QueryIntent
    from nasa_fire_ai.services.native import _render_comparison

    bundle = EvidenceBundle(
        query_intent=QueryIntent(),
        direct_evidence=[
            {"id": "S1", "evidence_ids": ["E-S1"]},
            {"id": "S2", "evidence_ids": ["E-S2"]},
        ],
        comparison=ExperimentComparison(
            run_ids=["S1", "S2"],
            shared_conditions={
                "AirflowVelocity": [
                    {"reported_value": 20, "reported_unit": "cm/s", "canonical_value": 0.2}
                ]
            },
            different_conditions={
                "FlowDirection": {
                    "S1": [{"reported_value": "Concurrent"}],
                    "S2": [{"reported_value": "Opposed"}],
                }
            },
            unknown_or_unavailable_conditions=["Pressure"],
        ),
    )
    rendered = "\n".join(_render_comparison(bundle))
    assert "S1: 20 cm/s" in rendered and "S2: 20 cm/s" in rendered
    assert "Concurrent" in rendered and "Opposed" in rendered
    assert (
        "Pressure" in rendered
        and "does not infer statistical significance or causation" in rendered
    )
    assert "E-S1" in rendered and "E-S2" in rendered
