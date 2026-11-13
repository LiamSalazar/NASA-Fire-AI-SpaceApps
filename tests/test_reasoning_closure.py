"""Adversarial controls for the actual emission and research boundaries."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.scientific_proposals import (
    approved_publication_records,
    project_eligible,
    publication_eligibility,
    stage_proposition,
)
from nasa_fire_ai.ingestion.semantic import load_semantic_registry
from nasa_fire_ai.models import EvidenceBundle, QueryIntent
from nasa_fire_ai.query.native import SemanticGraph
from nasa_fire_ai.query.v2 import QueryIntentV2
from nasa_fire_ai.services.investigation import ResearchBudget, evaluate_sufficiency, investigate
from nasa_fire_ai.services.scientific_synthesis import render_scientific

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def evidence(tmp_path):
    registry = EvidenceRegistry(tmp_path / "evidence.sqlite")
    registry.add_source({"source_id": "S", "title": "PMMA combustion", "status": "PUBLIC"})
    registry.add_document("D", "S", "PMMA combustion")
    text = "No flame was observed from PMMA at 21% oxygen. Airflow was restored."
    registry.add_passage(
        {
            "evidence_id": "E",
            "document_id": "D",
            "page": 1,
            "section": "Results",
            "text": text,
            "start_offset": 0,
            "end_offset": len(text),
            "raw_file": "fixture",
            "checksum": "fixture",
        }
    )
    yield registry
    registry.db.close()


def observation(text):
    row = {"id": "R", "text": text, "evidence_ids": ["E"]}
    return EvidenceBundle(
        query_intent=QueryIntent(),
        direct_evidence=[row],
        experimental_observations=[row],
        evidence_passages=[{"evidence_id": "E", "text": text}],
    )


@pytest.mark.parametrize(
    "text",
    [
        "Flame was observed from PMMA at 21% oxygen.",
        "No flame was observed from PMMA at 22% oxygen.",
        "No flame was observed from PMMA at 21 kPa oxygen.",
    ],
)
def test_forged_bundle_cannot_override_registry_source(evidence, text):
    bundle = observation(text)
    answer = render_scientific(bundle, registry=evidence)
    assert text not in answer
    assert bundle.retrieval_metadata["final_emission_gate"]["blocked"] == 1
    assert not bundle.retrieval_metadata["scientific_synthesis"]["selected_claims"]


def test_valid_exact_span_emits_with_receipt(evidence):
    text = "No flame was observed from PMMA at 21% oxygen."
    bundle = observation(text)
    assert text in render_scientific(bundle, registry=evidence)
    assert bundle.retrieval_metadata["claim_verification"][0]["status"] == "SUPPORTED"


@pytest.mark.parametrize(
    "query",
    [
        "What observations show PMMA reignition?",
        "What did NASA observe about PMMA flame spread?",
        "What happened when PMMA airflow was restored?",
    ],
)
def test_type_presence_cannot_satisfy_wrong_phenomenon(evidence, query):
    bundle = observation("No flame was observed from PMMA at 21% oxygen.")
    intent = QueryIntentV2(
        targets=["ExperimentalRun"], requested_information=["ReportedObservation"]
    )
    result = evaluate_sufficiency(query, intent, bundle, evidence)
    assert not result["sufficient"]


def test_wrong_publication_topic_is_missing(evidence):
    bundle = observation("No flame was observed from PMMA at 21% oxygen.")
    intent = QueryIntentV2(targets=["Publication"], requested_information=["Publication"])
    assert not evaluate_sufficiency(
        "Which publications investigate depressurization?", intent, bundle, evidence
    )["sufficient"]


def test_topically_misleading_publication_does_not_cover_distinctive_topic(evidence):
    bundle = observation("No flame was observed from PMMA at 21% oxygen.")
    intent = QueryIntentV2(targets=["Publication"], requested_information=["Publication"])
    assert (
        evaluate_sufficiency(
            "Which NASA publications investigate seawater corrosion of aluminum?",
            intent,
            bundle,
            evidence,
        )["items"][0]["status"]
        == "MISSING"
    )


def test_conflicted_applicability_never_sufficient(evidence):
    bundle = observation("No flame was observed from PMMA at 21% oxygen.")
    bundle.experimental_observations[0]["scientific_applicability"] = {
        "dimensions": [{"status": "CONFLICTED"}]
    }
    intent = QueryIntentV2(
        targets=["ExperimentalRun"], requested_information=["ReportedObservation"]
    )
    assert (
        evaluate_sufficiency("What did PMMA show?", intent, bundle, evidence)["items"][0]["status"]
        == "CONFLICTED"
    )


def test_model_self_approval_cannot_grant_publication():
    proposal = {
        "class_id": "ReportedObservation",
        "quote": "A flame appeared.",
        "evidence_id": "E",
        "publication_eligible": True,
        "canonical_review": "APPROVED",
    }
    assert not publication_eligibility(proposal, [])["eligible"]
    approved = [
        {
            "class_id": "ReportedObservation",
            "text": "A flame appeared.",
            "id": "reviewed",
            "evidence_ids": ["E"],
        }
    ]
    assert publication_eligibility(proposal, [], approved)["eligible"]
    assert not publication_eligibility({**proposal, "quote": "No flame appeared."}, [], approved)[
        "eligible"
    ]


def test_existing_reviewed_contract_replays_without_developer_intervention(evidence, tmp_path):
    import json
    import shutil

    (tmp_path / "domain").mkdir()
    (tmp_path / "data/canonical").mkdir(parents=True)
    shutil.copyfile(
        ROOT / "domain/legacy_semantic_projection.yaml",
        tmp_path / "domain/legacy_semantic_projection.yaml",
    )
    text = "No flame was observed from PMMA at 21% oxygen."
    # Synthetic approved-record fixture, not newly fabricated NASA data.
    row = {
        "id": "approved-fixture",
        "type": "ObservationRecord",
        "text": text,
        "evidence_refs": [{"evidence_id": "E", "source_id": "S"}],
    }
    (tmp_path / "data/canonical/records.json").write_text(json.dumps([row]))
    semantic = load_semantic_registry(ROOT / "domain/semantic_registry.yaml")
    approved = approved_publication_records(tmp_path)
    candidate = stage_proposition(
        {"class_id": "ReportedObservation", "quote": text, "evidence_id": "E"},
        evidence,
        semantic,
        approved_records=approved,
    )
    assert candidate["proposal"]["publication_eligible"]
    store = SemanticGraph(semantic)
    receipt = project_eligible(store, evidence, tmp_path)
    assert receipt["replayed"] == ["approved-fixture"]
    assert store.payload("approved-fixture") == row
    triples = len(store.graph)
    project_eligible(store, evidence, tmp_path)
    assert len(store.graph) == triples


def test_invalid_model_paths_and_circular_actions_terminate(evidence):
    semantic = load_semantic_registry(ROOT / "domain/semantic_registry.yaml")
    store = SemanticGraph(semantic)
    bundle = EvidenceBundle(query_intent=QueryIntent())
    intent = QueryIntentV2(targets=["ExperimentalRun"], requested_information=["NASAConclusion"])
    execution = SimpleNamespace(plan=SimpleNamespace(intent=intent), bundle=bundle)

    class Planner:
        def plan(self, *args, **kwargs):
            return {
                "actions": [
                    {
                        "operation": "ontology_path",
                        "start": "unknown",
                        "query": "combustion",
                        "requirement": "NASAConclusion",
                        "steps": [{"relation": "invented", "direction": "FORWARD"}],
                    }
                ]
            }

    receipt = investigate(
        "What conclusions concern combustion?",
        execution,
        store,
        evidence,
        planner=Planner(),
        budget=ResearchBudget(max_rounds=4, max_actions=3),
    )
    assert len(receipt["model_calls"]) <= 2
    assert len(receipt["completed_actions"]) <= 3
    assert receipt["rejected_actions"]
    assert receipt["stop_reason"]


@pytest.mark.parametrize(
    "research,synthesis", [(False, False), (True, False), (False, True), (True, True)]
)
def test_real_service_flag_matrix_has_mandatory_gate(monkeypatch, research, synthesis):
    from dataclasses import replace

    from nasa_fire_ai.config import Settings
    from nasa_fire_ai.services.phase3 import Phase3AssistantService

    for flag in (
        "NATIVE_V2_QUERY_ENABLED",
        "SCIENTIFIC_CONTEXT_RESOLUTION_ENABLED",
        "SOURCE_KNOWLEDGE_ENRICHMENT_ENABLED",
        "ONTOLOGY_GRAPH_ENRICHMENT_ENABLED",
    ):
        monkeypatch.setenv(flag, "true")
    monkeypatch.setenv("AUTONOMOUS_RESEARCH_ENABLED", str(research).lower())
    monkeypatch.setenv("SCIENTIFIC_SYNTHESIS_ENABLED", str(synthesis).lower())
    monkeypatch.setenv("NEMOTRON_RESEARCH_PLANNING_ENABLED", "false")
    service = Phase3AssistantService(root=ROOT, settings=replace(Settings(), nvidia_api_key=None))
    try:
        response = service.answer_query("What did NASA observe about PMMA combustion?")
        meta = response.evidence_bundle.retrieval_metadata
        assert meta["final_emission_gate"]["enforced"]
        assert meta["claim_verification"]
        assert "radiative quenching" in response.rendered_answer
        assert bool(meta.get("investigation")) == research
    finally:
        service.registry.db.close()


def test_failed_retrieval_keeps_bundle_and_stops(evidence, monkeypatch):
    semantic = load_semantic_registry(ROOT / "domain/semantic_registry.yaml")
    store = SemanticGraph(semantic)
    intent = QueryIntentV2(targets=["ExperimentalRun"], requested_information=["NASAConclusion"])
    bundle = EvidenceBundle(query_intent=QueryIntent())
    execution = SimpleNamespace(plan=SimpleNamespace(intent=intent), bundle=bundle)

    def failure(*args, **kwargs):
        raise TimeoutError("simulated retrieval timeout")

    monkeypatch.setattr("nasa_fire_ai.services.investigation.execute_native", failure)
    monkeypatch.setattr(evidence, "search", failure)
    receipt = investigate("What conclusions concern combustion?", execution, store, evidence)
    assert receipt["final_decision"] == "ABSTAIN"
    assert receipt["action_attempts"] <= ResearchBudget().max_actions
    assert all(
        a.get("failure") == "RETRIEVAL_FAILED"
        for a in receipt["rejected_actions"]
        if a["reason"] == "TimeoutError"
    )
