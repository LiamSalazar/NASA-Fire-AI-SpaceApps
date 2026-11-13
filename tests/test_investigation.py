from pathlib import Path
from types import SimpleNamespace

import pytest

from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.scientific_proposals import (
    extract_source,
    project_staged,
    search_staged,
    stage_proposition,
)
from nasa_fire_ai.ingestion.semantic import load_semantic_registry
from nasa_fire_ai.models import EvidenceBundle, QueryIntent
from nasa_fire_ai.query.native import SemanticGraph, execute_native
from nasa_fire_ai.query.v2 import EntityConstraintV2, QueryIntentV2
from nasa_fire_ai.services.investigation import ResearchBudget, evaluate_sufficiency, investigate
from nasa_fire_ai.services.maintenance import run_cycle

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def corpus(tmp_path):
    evidence = EvidenceRegistry(tmp_path / "registry.sqlite")
    evidence.add_source(
        {
            "source_id": "S1",
            "nasa_id": "123",
            "title": "Earth tests and cited spacecraft research",
            "status": "PUBLIC",
        }
    )
    evidence.add_document("D1", "S1", "Earth tests")
    text = "Previous microgravity studies are discussed. Tests were performed on Earth at 14.7 psia. No flame was observed from PMMA at 21% oxygen."
    evidence.add_passage(
        {
            "evidence_id": "E1",
            "document_id": "D1",
            "page": 1,
            "section": "Results",
            "text": text,
            "start_offset": 0,
            "end_offset": len(text),
            "raw_file": "immutable.pdf",
            "checksum": "digest",
        }
    )
    semantic = load_semantic_registry(ROOT / "domain/semantic_registry.yaml")
    store = SemanticGraph(semantic)
    store.add_entity("R1", "ExperimentalRun", ["E1"], ["S1"])
    store.add_entity("PMMA", "Sample", ["E1"], ["S1"])
    store.add_relation("R1", "hasMaterial", "PMMA", ["E1"])
    observation = {
        "id": "R1",
        "text": "No flame was observed from PMMA at 21% oxygen.",
        "evidence_ids": ["E1"],
    }
    store.add_entity("R1", "ReportedObservation", ["E1"], ["S1"], observation)
    return evidence, semantic, store


def test_missing_observation_research_recovers_without_relaxing_constraint(corpus):
    evidence, _, store = corpus
    intent = QueryIntentV2(
        targets=["ExperimentalRun"],
        requested_information=["ReportedObservation"],
        entity_constraints=[EntityConstraintV2(relation="hasMaterial", entity_id="PMMA")],
    )
    initial = execute_native(intent, "What did NASA observe about PMMA?", store, evidence)
    initial.bundle.experimental_observations.clear()
    initial.bundle.evidence_passages.clear()
    receipt = investigate("What did NASA observe about PMMA?", initial, store, evidence)
    assert receipt["initial_coverage"]["items"][0]["status"] == "MISSING"
    assert receipt["completed_actions"][0]["operation"] == "native_search"
    assert receipt["completed_actions"][0]["scientific_constraints"] == [
        intent.entity_constraints[0].model_dump(mode="json")
    ]
    assert receipt["final_coverage"]["sufficient"]
    assert len(receipt["completed_actions"]) == 1


def test_configuration_is_not_an_observation_and_budget_is_enforced(corpus):
    evidence, _, store = corpus
    intent = QueryIntentV2(targets=["ExperimentalRun"], requested_information=["NASAConclusion"])
    bundle = EvidenceBundle(
        query_intent=QueryIntent(), direct_evidence=[{"id": "R1", "evidence_ids": ["E1"]}]
    )
    assert not evaluate_sufficiency("What was concluded?", intent, bundle, evidence)["sufficient"]
    execution = SimpleNamespace(plan=SimpleNamespace(intent=intent), bundle=bundle)
    receipt = investigate(
        "What was concluded about combustion?",
        execution,
        store,
        evidence,
        budget=ResearchBudget(max_rounds=2, max_actions=1),
    )
    assert len(receipt["completed_actions"]) == 1
    assert receipt["final_decision"] == "ABSTAIN"
    with pytest.raises(ValueError):
        ResearchBudget(max_rounds=0)


def test_planner_invalid_path_rejected_and_duplicate_operations_do_not_repeat(corpus):
    evidence, _, store = corpus
    intent = QueryIntentV2(targets=["ExperimentalRun"], requested_information=["NASAConclusion"])
    execution = execute_native(intent, "What conclusions concern combustion?", store, evidence)

    class Planner:
        def plan(self, *args, **kwargs):
            action = {
                "operation": "native_search",
                "query": "combustion",
                "requirement": "NASAConclusion",
                "relations": ["inventedRelation"],
            }
            return {"actions": [action, action]}

    receipt = investigate(
        "What conclusions concern combustion?", execution, store, evidence, planner=Planner()
    )
    assert any(a["reason"] == "Unapproved ontology path" for a in receipt["rejected_actions"])
    assert any(a["reason"] == "Duplicate operation" for a in receipt["rejected_actions"])


def test_earth_negative_control_and_numeric_units_rejected(corpus):
    evidence, semantic, _ = corpus
    base = {
        "class_id": "ExperimentalCondition",
        "evidence_id": "E1",
        "quote": "Tests were performed on Earth at 14.7 psia.",
    }
    earth = stage_proposition({**base, "gravity": "microgravity"}, evidence, semantic)
    assert earth["review_status"] == "REJECTED"
    changed = stage_proposition(
        {**base, "quantities": [{"original_expression": "14.7 kPa"}]}, evidence, semantic
    )
    assert "QUANTITY_OR_UNIT_NOT_IN_EXACT_QUOTE" in changed["proposal"]["validation_errors"]
    good = stage_proposition(
        {**base, "quantities": [{"original_expression": "14.7 psia"}]}, evidence, semantic
    )
    assert good["proposal"]["actual_gravity"] == "UNRESOLVED"
    assert good["review_status"] == "PENDING"
    assert not good["proposal"]["publication_eligible"]
    assert good["proposal"]["original_wording"] == base["quote"]


def test_staged_science_is_retrievable_but_never_canonical(corpus):
    evidence, semantic, store = corpus
    receipt = extract_source("S1", evidence, semantic, Settings(), model_enabled=False)
    assert receipt["canonical_scientific_changes"] == 0
    assert search_staged("flame oxygen", evidence)
    count = project_staged(store, evidence)
    assert count
    assert not any(entity.startswith("science-") for entity in store.entities())
    again = extract_source("S1", evidence, semantic, Settings(), model_enabled=False)
    assert again["execution"] == "CACHE_REPLAY" and again["new_model_calls"] == 0
    assert len(evidence.staged_semantic_candidates()) == len(receipt["items"])


def test_failed_extraction_does_not_block_other_sources(corpus, monkeypatch, tmp_path):
    evidence, semantic, _ = corpus
    evidence.add_source(
        {"source_id": "S2", "nasa_id": "456", "title": "Second source", "status": "PUBLIC"}
    )
    seen = []

    def extraction(source, *args, **kwargs):
        seen.append(source)
        if source == "S1":
            raise ValueError("Malformed item")
        return {"status": "STAGED", "new_model_calls": 0}

    monkeypatch.setattr("nasa_fire_ai.services.maintenance.extract_source", extraction)
    receipt = run_cycle(
        tmp_path,
        evidence,
        semantic,
        Settings(),
        identifiers=["123", "456"],
        dry_run=False,
        offline=True,
    )
    assert seen == ["S1", "S2"]
    assert receipt["status"] == "PARTIAL"
    assert receipt["items"][0]["extraction"]["status"] == "QUARANTINED_EXTRACTION"
    assert receipt["items"][1]["extraction"]["status"] == "STAGED"
    assert evidence.db.execute("SELECT status FROM autonomous_jobs").fetchone()[0] == "PARTIAL"


def test_dry_cycle_has_no_database_mutation_and_lease_prevents_overlap(corpus, tmp_path):
    evidence, semantic, _ = corpus
    before = list(evidence.db.iterdump())
    run_cycle(
        tmp_path, evidence, semantic, Settings(), identifiers=["123"], dry_run=True, offline=True
    )
    assert before == list(evidence.db.iterdump())
    first = run_cycle(
        tmp_path, evidence, semantic, Settings(), identifiers=["123"], dry_run=False, offline=True
    )
    evidence.db.execute(
        "UPDATE autonomous_jobs SET status='RUNNING' WHERE job_id=?", (first["job_id"],)
    )
    evidence.db.commit()
    assert (
        run_cycle(
            tmp_path,
            evidence,
            semantic,
            Settings(),
            identifiers=["123"],
            dry_run=False,
            offline=True,
        )["status"]
        == "BUSY"
    )


def test_bibliographic_guard_preserves_sourced_guidance_and_gravity_report():
    from nasa_fire_ai.services.investigation import question_kind

    assert (
        question_kind("Find guidance from source official-source", QueryIntentV2()) == "scientific"
    )
    assert (
        question_kind("What do the investigations report under normal gravity?", QueryIntentV2())
        == "scientific"
    )
    assert (
        question_kind("Which NASA sources discuss nitrogen backfill?", QueryIntentV2())
        == "bibliographic"
    )


def test_interrupted_vector_generation_retains_previous_search(tmp_path, monkeypatch):
    import os

    from nasa_fire_ai.retrieval.semantic import LocalVectorIndex

    index = LocalVectorIndex(tmp_path, "atomic")
    index.write(["E1"], [[1.0, 0.0]], {"model": "test"})
    previous = index.metadata_path.read_bytes()

    def interrupted(*args):
        raise OSError("Interrupted manifest publication")

    with monkeypatch.context() as context:
        context.setattr(os, "replace", interrupted)
        with pytest.raises(OSError):
            index.write(["E2"], [[0.0, 1.0]], {"model": "test"})
    assert index.metadata_path.read_bytes() == previous
    assert index.search([1.0, 0.0])[0][0] == "E1"
    index.write(["E2"], [[0.0, 1.0]], {"model": "test"})
    assert index.search([0.0, 1.0])[0][0] == "E2"
    assert index.sync({"E2": [0.0, 1.0]}, {"model": "test"})["new_or_changed"] == 0


def test_direct_candidate_does_not_satisfy_different_explicit_technical_topic(corpus):
    evidence, _, _store = corpus
    intent = QueryIntentV2(
        targets=["ExperimentalRun"], requested_information=["ReportedObservation"]
    )
    row = {
        "id": "R1",
        "text": "No flame was observed from PMMA at 21% oxygen.",
        "evidence_ids": ["E1"],
    }
    bundle = EvidenceBundle(
        query_intent=QueryIntent(),
        direct_evidence=[row],
        experimental_observations=[row],
        evidence_passages=[evidence.resolve("E1")],
    )
    result = evaluate_sufficiency(
        "What observations support pressure-induced ignition?", intent, bundle, evidence
    )
    assert result["items"][0]["status"] == "MISSING"
    assert not result["sufficient"]


def test_staged_search_respects_source_restrictions_and_archival_status(corpus):
    evidence, semantic, _ = corpus
    extract_source("S1", evidence, semantic, Settings(), model_enabled=False)
    assert search_staged("flame oxygen", evidence, source_ids=["S1"])
    assert not search_staged("flame oxygen", evidence, source_ids=["other-source"])
    evidence.db.execute("UPDATE sources SET status='ROLLED_BACK_DOCUMENT' WHERE source_id='S1'")
    evidence.db.commit()
    assert not search_staged("flame oxygen", evidence)
    assert evidence.resolve("E1")  # Archiving does not invalidate historical citations.


def test_conceptual_partial_support_keeps_documentary_citation(corpus):
    evidence, _, _ = corpus
    intent = QueryIntentV2(operation="EXPLAIN", targets=["Publication"])
    bundle = EvidenceBundle(
        query_intent=QueryIntent(),
        evidence_passages=[evidence.resolve("E1")],
        retrieval_metadata={"conceptual_query": {"active": True, "approved_relations": []}},
    )
    coverage = evaluate_sufficiency("Does acrylic mean PMMA?", intent, bundle, evidence)
    assert coverage["items"][0]["status"] == "PARTIALLY_SUPPORTED"
    assert coverage["items"][0]["evidence_ids"] == ["E1"]
    assert not coverage["sufficient"]


def test_research_replans_after_requirement_is_supported(corpus):
    evidence, _, store = corpus
    text = "Airflow to PMMA was interrupted and later restored."
    evidence.add_passage(
        {
            "evidence_id": "E2",
            "document_id": "D1",
            "page": 2,
            "section": "Intervention",
            "text": text,
            "start_offset": 0,
            "end_offset": len(text),
            "raw_file": "immutable.pdf",
            "checksum": "digest",
        }
    )
    store.add_entity(
        "I1", "Intervention", ["E2"], ["S1"], {"id": "I1", "text": text, "evidence_ids": ["E2"]}
    )
    store.add_relation("I1", "hasMaterial", "PMMA", ["E2"])
    intent = QueryIntentV2(
        targets=["ExperimentalRun"],
        requested_information=["ReportedObservation", "Intervention"],
        entity_constraints=[EntityConstraintV2(relation="hasMaterial", entity_id="PMMA")],
    )
    execution = execute_native(
        intent, "What observations and interventions were reported for PMMA?", store, evidence
    )
    execution.bundle.experimental_observations.clear()
    execution.bundle.interventions.clear()
    execution.bundle.evidence_passages.clear()
    receipt = investigate(
        "What observations and interventions were reported for PMMA?", execution, store, evidence
    )
    assert receipt["final_coverage"]["sufficient"]
    assert [a["requirement"] for a in receipt["completed_actions"]] == [
        "ReportedObservation",
        "Intervention",
    ]
    assert receipt["replanning_decisions"][1]["unresolved"] == ["Intervention"]
    assert "E1" in receipt["replanning_decisions"][1]["evidence_ids"]
