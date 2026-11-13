"""Real NASA integration and labeled synthetic adversarial scope controls."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from nasa_fire_ai.context import (
    ContextStatement,
    ContextStatus,
    ContextualProposal,
    ScopeResolver,
    SourceLocation,
)
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.semantic import project_legacy
from nasa_fire_ai.query.contextual import attach_context_layer
from nasa_fire_ai.query.native import classify_native
from nasa_fire_ai.query.v2 import EntityConstraintV2, QueryIntentV2
from nasa_fire_ai.services.native import answer_native_text

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def real_context(tmp_path_factory):
    target = tmp_path_factory.mktemp("context") / "evidence.sqlite"
    evidence = EvidenceRegistry(target)
    # Context evaluation does not use the 260 MB historical embedding cache.
    # Copy the source/provenance tables and rebuild FTS, leaving the immutable
    # snapshot untouched and keeping repeated CI fixtures bounded.
    evidence.db.execute(
        "ATTACH DATABASE ? AS frozen",
        (str(ROOT / "artifacts/phase3c_real_context_evidence_v1.sqlite"),),
    )
    for table in [
        "sources",
        "documents",
        "passages",
        "evidence_refs",
        "evidence_locations",
        "structured_cells",
        "document_metadata",
    ]:
        evidence.db.execute(f"INSERT INTO main.{table} SELECT * FROM frozen.{table}")
    evidence.db.execute(
        "INSERT INTO passages_fts(evidence_id,text) SELECT evidence_id,text FROM passages"
    )
    evidence.db.commit()
    evidence.db.execute("DETACH DATABASE frozen")
    with patch.dict(
        "os.environ",
        {
            "ONTOLOGY_GRAPH_ENRICHMENT_ENABLED": "true",
            "SOURCE_KNOWLEDGE_ENRICHMENT_ENABLED": "true",
            "NATIVE_SOURCE_CONTEXT_VALIDATION_ENABLED": "true",
            "SCIENTIFIC_CONTEXT_RESOLUTION_ENABLED": "false",
            "PSI_STRUCTURED_PUBLICATION_ENABLED": "false",
            "FLEX_SOURCE_CORRECTIONS_ENABLED": "false",
        },
    ):
        store = project_legacy(ROOT, evidence)
    attach_context_layer(
        store, evidence, ROOT / "artifacts/phase3c_real_context_applicability_v8.json"
    )
    language = yaml.safe_load((ROOT / "domain/query_language_v2.yaml").read_text())
    yield store, evidence, language
    evidence.db.close()


def activate(monkeypatch):
    for name in [
        "SCIENTIFIC_CONTEXT_RESOLUTION_ENABLED",
        "MICROGRAVITY_FIRST_RETRIEVAL_ENABLED",
        "RELATIONAL_RELATED_RETRIEVAL_ENABLED",
    ]:
        monkeypatch.setenv(name, "true")
    monkeypatch.setenv("CONTEXT_QUERY_LIVE_CALL_BUDGET", "0")


def test_real_native_service_invokes_scope_resolver(real_context, monkeypatch):
    store, evidence, language = real_context
    activate(monkeypatch)
    response = answer_native_text("PMMA in microgravity", store, evidence, language)
    context = response.execution.bundle.retrieval_metadata["scientific_context"]
    assert context["resolver_invoked"]
    assert context["applied_statements"]
    assert "psi-25-B1" in {r["id"] for r in response.execution.bundle.direct_evidence}
    assert not store.relations("psi-25-B1", "hasGravityCondition")
    assert all(
        evidence.resolve(p["evidence_id"]) for p in response.execution.bundle.evidence_passages
    )


def test_public_v2_service_renders_verified_claims_offline(real_context, monkeypatch, tmp_path):
    from nasa_fire_ai.config import Settings
    from nasa_fire_ai.services.phase3 import Phase3AssistantService

    store, evidence, _ = real_context
    activate(monkeypatch)
    monkeypatch.setenv("NATIVE_V2_QUERY_ENABLED", "true")
    monkeypatch.setenv("SCIENTIFIC_SYNTHESIS_ENABLED", "true")
    monkeypatch.setenv("NEMOTRON_SCIENTIFIC_SELECTION_ENABLED", "false")
    service = Phase3AssistantService(
        root=ROOT, settings=Settings(root=tmp_path, nvidia_api_key=None)
    )
    service.registry = evidence
    service._native_store = store
    response = service.answer_query(
        "What did NASA observe about PMMA combustion under microgravity?"
    )
    assert response.answer.generated_claims
    assert response.evidence_bundle.retrieval_metadata["scientific_context"]["resolver_invoked"]
    assert len(response.rendered_answer.split()) < 700
    for claim in response.answer.generated_claims:
        assert all(evidence.resolve(eid) for eid in claim.evidence_ids)
        assert claim.validation_status == "VALIDATED_SUPPLIED_STATEMENT"
    assert "microgravity" in response.rendered_answer
    assert not store.relations("psi-25-B1", "hasGravityCondition")


def test_public_v2_conditions_are_not_observed_outcomes(real_context, monkeypatch, tmp_path):
    from nasa_fire_ai.config import Settings
    from nasa_fire_ai.services.phase3 import Phase3AssistantService

    store, evidence, _ = real_context
    activate(monkeypatch)
    monkeypatch.setenv("NATIVE_V2_QUERY_ENABLED", "true")
    monkeypatch.setenv("SCIENTIFIC_SYNTHESIS_ENABLED", "true")
    monkeypatch.setenv("NEMOTRON_SCIENTIFIC_SELECTION_ENABLED", "false")
    service = Phase3AssistantService(
        root=ROOT, settings=Settings(root=tmp_path, nvidia_api_key=None)
    )
    service.registry = evidence
    service._native_store = store
    response = service.answer_query("Which conditions applied to the Saffire-I experiments?")
    assert "20.0 cm/s" in response.rendered_answer
    assert "not observations" in response.rendered_answer
    assert all(
        claim.epistemic_type in {"experimental_condition", "reported_quantity"}
        for claim in response.answer.generated_claims
    )


def test_real_observation_joins_material_and_earlier_environment(real_context, monkeypatch):
    store, evidence, language = real_context
    activate(monkeypatch)
    response = answer_native_text(
        "What did NASA observe about PMMA combustion under microgravity?", store, evidence, language
    )
    ids = {r["id"] for r in response.execution.bundle.direct_evidence}
    assert "context:bass-film-observation" in ids
    assert "context:saffire-iv-flow-observation" not in ids
    assert "microgravity" in response.rendered_answer


def test_explicit_terrestrial_query_overrides_default(real_context, monkeypatch):
    store, evidence, language = real_context
    activate(monkeypatch)
    response = answer_native_text(
        "What do the investigations report under normal gravity?", store, evidence, language
    )
    assert not response.execution.bundle.retrieval_metadata["context_policy"]["default_preference"]
    ids = {r["id"] for r in response.execution.bundle.direct_evidence}
    assert "context:silicone-ground-observation" in ids
    assert "context:bass-film-observation" not in ids


def test_real_comparison_keeps_gravity_groups_separate(real_context, monkeypatch):
    store, evidence, language = real_context
    activate(monkeypatch)
    response = answer_native_text(
        "How do observations differ between normal gravity and microgravity?",
        store,
        evidence,
        language,
    )
    assert {r["group"] for r in response.execution.bundle.retrieval_metadata["grouped_search"]} == {
        "normal-gravity",
        "microgravity",
    }
    assert not response.execution.plan.intent.clarification_required


def test_v1_style_baseline_remains_without_context_facts(real_context, monkeypatch):
    store, _, _ = real_context
    monkeypatch.setenv("SCIENTIFIC_CONTEXT_RESOLUTION_ENABLED", "false")
    intent = QueryIntentV2(
        targets=["ExperimentalRun"],
        entity_constraints=[
            EntityConstraintV2(relation="hasGravityCondition", entity_id="microgravity")
        ],
    )
    status, detail = classify_native("psi-25-B1", intent, store)
    assert status != "DIRECT"
    assert detail["unknown"]


def test_real_intervention_does_not_acquire_unsourced_gravity(real_context, monkeypatch):
    store, evidence, language = real_context
    activate(monkeypatch)
    response = answer_native_text(
        "What happened after airflow was interrupted and restored?", store, evidence, language
    )
    assert any(
        r["id"] == "context:saffire-iv-flow-observation"
        for r in response.execution.bundle.direct_evidence
    )
    assert (
        store.context_layer.resolver.resolve(
            "context:saffire-iv-flow-observation", "gravity"
        ).status
        == ContextStatus.UNKNOWN
    )


@pytest.mark.parametrize(
    "mutation",
    [
        "fabricated-id",
        "wrong-gravity",
        "wrong-group",
        "document-scope",
        "some",
        "invented-exception",
        "conditional",
        "unrelated-run",
    ],
)
def test_correct_citation_cannot_authorize_wrong_scope(real_context, mutation):
    store, _, _ = real_context
    statement = next(
        s
        for s in store.context_layer.resolver.statements
        if s.statement_id == "gravity-context:silicone-ground-observation"
    )
    spans = statement.support_spans
    proposal = ContextualProposal(
        subject_entity="context:silicone-ground-observation",
        candidate_predicate="hasGravityCondition",
        object_value="normal-gravity",
        source_statement=spans[0]["text"],
        supporting_text=spans[0]["text"],
        context_scope="group",
        quantifier="IDENTIFIED",
        evidence_ids=[s["evidence_id"] for s in spans],
        support_spans=spans,
    )
    changes = {
        "fabricated-id": {"evidence_ids": ["E-made-up"]},
        "wrong-gravity": {"object_value": "microgravity"},
        "wrong-group": {"subject_entity": "context:silicone-flight-observation"},
        "document-scope": {"context_scope": "document"},
        "some": {"quantifier": "SOME"},
        "invented-exception": {"exceptions": ["psi-25-B1"]},
        "conditional": {"applicability_conditions": ["if the system were operated in space"]},
        "unrelated-run": {"subject_entity": "psi-98-S1"},
    }
    result = store.context_layer.validate_model_proposal(
        proposal.model_copy(update=changes[mutation])
    )
    assert result["reasons"]


@pytest.mark.parametrize("quantifier", ["SOME", "UNSPECIFIED", "THEORETICAL"])
def test_synthetic_nonuniversal_quantifiers_never_inherit(quantifier):
    statement = ContextStatement(
        statement_id="synthetic",
        context_type="unseen-dimension",
        value="A",
        entity_ids=["run"],
        evidence_ids=["synthetic-E"],
        original_text="some experiments",
        source_location=SourceLocation(document_id="synthetic"),
        validation_status=ContextStatus.VERIFIED_APPLICABLE_CONTEXT,
        quantifier=quantifier,
    )
    assert (
        ScopeResolver([statement]).resolve("run", "unseen-dimension").status
        == ContextStatus.CONTEXTUAL_CANDIDATE
    )


def test_synthetic_model_priority_cannot_resolve_conflicting_science():
    base = ContextStatement(
        statement_id="synthetic-A",
        context_type="material",
        value="A",
        entity_ids=["run"],
        evidence_ids=["synthetic-E"],
        original_text="material A",
        source_location=SourceLocation(document_id="synthetic"),
        scope="group",
        validation_status=ContextStatus.VERIFIED_APPLICABLE_CONTEXT,
    )
    other = base.model_copy(update={"statement_id": "synthetic-B", "value": "B", "priority": 999})
    assert (
        ScopeResolver([base, other]).resolve("run", "material").status == ContextStatus.CONFLICTED
    )


def test_unreviewed_context_cannot_publish_canonical_relation(real_context):
    store, evidence, _ = real_context
    statement = store.context_layer.resolver.statements[0]
    with pytest.raises(ValueError, match="explicit review"):
        store.add_context_relation(statement, evidence)


def test_manifest_support_is_source_exact(real_context):
    store, evidence, _ = real_context
    assert not store.context_layer.rejected
    for statement in store.context_layer.resolver.statements:
        assert all(
            span["text"] in evidence.resolve(span["evidence_id"])["text"]
            for span in statement.support_spans
        )
        assert all(
            path[-1]["to"] == statement.scope_entity for path in statement.membership_paths.values()
        )


def test_source_digest_manifest_is_available():
    receipt = json.loads((ROOT / "artifacts/phase3c_real_context_freeze_v1.json").read_text())
    assert any(p.startswith("data/raw/") for p in receipt["files"])


def test_actual_app_service_routes_v2_and_preserves_citations(real_context, monkeypatch):
    from nasa_fire_ai.config import Settings
    from nasa_fire_ai.services.phase3 import Phase3AssistantService

    store, evidence, _ = real_context
    activate(monkeypatch)
    monkeypatch.setenv("NATIVE_V2_QUERY_ENABLED", "true")
    service = Phase3AssistantService(
        root=ROOT,
        settings=Settings(root=ROOT, nvidia_api_key=""),
    )
    service._native_store = store
    response = service.answer_query("What did NASA observe about PMMA combustion?")
    assert response.evidence_bundle.direct_evidence
    assert response.evidence_bundle.retrieval_metadata["scientific_context"]["resolver_invoked"]
    assert response.evidence_bundle.retrieval_metadata["context_policy"]["default_preference"]
    assert all(evidence.resolve(e) for e in response.trace.evidence_ids)
    assert "microgravity" in response.rendered_answer
    service.registry.db.close()


def test_verified_context_is_graph_navigable_but_not_canonical(real_context):
    from nasa_fire_ai.query.ontology_navigation import RouteStep, navigate

    store, evidence, _ = real_context
    steps = [RouteStep("hasGravityCondition")]
    assert not navigate(store, "psi-25-B1", steps, evidence)["results"]
    paths = navigate(store, "psi-25-B1", steps, evidence, allow_context=True)["results"]
    assert any(p["entity"] == "microgravity" for p in paths)
    assert all(evidence.resolve(e) for p in paths for s in p["path"] for e in s["evidence_ids"])


def test_real_ground_exceptions_remain_excluded(real_context):
    store, _, _ = real_context
    resolver = store.context_layer.resolver
    for subject in ["context:silicone-ground-observation", "context:bass-ground-rod-observation"]:
        result = resolver.resolve(subject, "gravity")
        assert result.values == ["normal-gravity"]
    assert any(s.exceptions for s in resolver.statements)


def test_real_oxygen_context_is_not_a_local_numeric_rewrite(real_context):
    store, _, _ = real_context
    subject = "context:bass-ground-rod-observation"
    assert not store.values(subject, "OxygenConcentration")
    values = store.context_layer.values(subject, "OxygenConcentration", {})
    assert values
    assert values[0]["value"].reported_value == 21


def test_missing_structured_answer_still_has_contextual_rag(real_context, monkeypatch):
    store, evidence, language = real_context
    activate(monkeypatch)
    response = answer_native_text(
        "What unresolved questions did NASA identify about microgravity fire safety?",
        store,
        evidence,
        language,
    )
    bundle = response.execution.bundle
    assert not bundle.direct_evidence
    assert bundle.retrieval_metadata["selection_trace"]["documentary_candidates"]
    assert bundle.evidence_passages
    assert all(evidence.resolve(p["evidence_id"]) for p in bundle.evidence_passages)
