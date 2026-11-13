"""Candidate coverage is independent of scientific eligibility and display budgets."""

from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from nasa_fire_ai.api import create_app
from nasa_fire_ai.services.conversation import ChatRequest, ConversationService
from nasa_fire_ai.services.search import ScientificSearchService
from nasa_fire_ai.services.semantic_support import verify_paraphrase

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "data/snapshots/hackathon-20261105-v9"


@pytest.fixture(scope="module")
def engine():
    service = ScientificSearchService(SNAPSHOT, ROOT)
    yield service
    service.close()


def test_display_limit_does_not_truncate_candidate_pool(engine):
    small = engine.search("combustion diagnostics", limit=2)
    large = engine.search("combustion diagnostics", limit=20)
    assert len(small.candidates) > 20
    assert small.candidates == large.candidates
    assert small.documentary == large.documentary[:2]
    second = engine.search("combustion diagnostics", limit=2, offset=2)
    assert second.documentary == large.documentary[2:4]
    assert small.continuation["next_offsets"]["documentary"] == 2
    assert small.metrics["retrieved_candidates"] > small.metrics["returned_candidates"]


def test_source_diversity_and_unverified_candidates(engine):
    result = engine.search("flame extinction reduced gravity", limit=100)
    sources = {r["source"]["source_id"] for r in result.documentary + result.discovery}
    assert len(sources) > 4
    assert not result.direct
    assert all(not r["verified_relationship"] for r in result.discovery)
    assert all(r["uncertainty_reason"] for r in result.discovery)
    assert len({r["source"]["source_id"] for r in result.documentary[:10]}) > 2


def test_explicit_source_scope_applies_to_all_strategies(engine):
    intent = engine.interpret("combustion diagnostics")
    intent.source_constraints = ["ntrs-20150023456"]
    result = engine.search("combustion diagnostics", intent=intent, limit=100)
    assert result.documentary
    assert {r["source"]["source_id"] for r in result.documentary + result.discovery} == {
        "ntrs-20150023456"
    }


def test_semantic_candidates_add_no_experimental_authority(engine):
    row = engine.registry.db.execute("SELECT evidence_id FROM passages LIMIT 1").fetchone()
    eid = row[0]
    engine.semantic_candidates = lambda query, allowed, limit: [(eid, 0.999)]
    try:
        result = engine.search("unresolved-quasar-phenomenon")
        assert not result.direct and not result.related
        candidate = next(r for r in result.candidates if r.get("evidence_id") == eid)
        assert candidate["category"] in {"DISCOVERY", "DOCUMENTARY"}
        assert candidate["retrieval_routes"][0]["strategy"] == "semantic"
    finally:
        engine.semantic_candidates = None


def test_exact_documentary_excerpt_needs_no_nli_but_scope_and_numbers_still_apply():
    text = "The synthetic specimen may exhibit transient shading."
    anchor = {
        "text": text,
        "category": "DOCUMENTARY",
        "epistemic_type": "documentary_content",
        "spans": [{"evidence_id": "synthetic", "text": text}],
    }
    registry = SimpleNamespace(resolve=lambda eid: {"text": text})
    assert verify_paraphrase(text, [anchor], registry, None)["supported"]
    assert not verify_paraphrase(
        "The synthetic specimen exhibits transient shading.", [anchor], registry, None
    )["supported"]
    anchor["category"] = "DISCOVERY"
    assert not verify_paraphrase(text, [anchor], registry, None)["supported"]


def test_chat_retains_candidates_and_citations_without_provider():
    with TestClient(
        create_app(lambda: ConversationService(ScientificSearchService(SNAPSHOT, ROOT)))
    ) as client:
        data = client.post(
            "/api/v1/chat", json={"message": "droplet combustion diagnostics", "evidence_limit": 2}
        ).json()
        assert data["answer"] and data["citations"]
        assert data["provider_status"]["generated_by"] is None
        assert data["provider_status"]["response_mode"] == "source_excerpts"
        assert data["retrieval"]["retrieved"] > len(data["additional_candidates"])
        url = data["retrieval"]["continuation_url"]
        first = client.get(url + "?limit=3").json()
        second = client.get(url + "?limit=3&offset=3").json()
        assert first["total"] == data["retrieval"]["retrieved"]
        assert first["items"] != second["items"]
        assert "raw_file" not in str(first)
        for citation in data["citations"]:
            evidence = client.get("/api/v1/evidence/" + citation["evidence_id"]).json()
            assert citation["supporting_passage"] in evidence["text"]
        assert client.get("/api/v1/capabilities").json()["languages"] == ["en"]


def test_post_retrieval_expansion_is_bounded_and_preserves_original_eligibility(engine):
    class Provider:
        def plan(self, question, history, max_queries):
            return {"resolved_question": question, "queries": []}

        def refine(self, question, candidates, remaining):
            assert candidates and remaining == 1
            return {
                "resolved_question": "Inspect a distinct diagnostic term",
                "queries": ["camera", "pressure"],
            }

        def explain(self, payload, max_tokens):
            return {"segments": [], "exploration_queries": []}

    service = ConversationService(engine, provider=Provider())
    response = service.chat(ChatRequest(message="unresolved-combustion-diagnostic", max_queries=2))
    trace = service.traces[response.trace_id]
    assert len(trace["queries"]) == 2
    assert trace["queries"][1]["query"] == "camera"
    assert "new_candidates" in trace["queries"][1]
    assert not response.evidence_groups["direct"]
    assert all(r["category"] != "DIRECT" for r in response.additional_candidates)


def test_discovery_source_selection_resolves_real_metadata_only(engine):
    class Provider:
        def plan(self, question, history, max_queries):
            return {"resolved_question": question, "queries": []}

        def explain(self, payload, max_tokens):
            eid = payload["discovery_candidates"][0]["evidence_id"]
            self.eid = eid
            return {
                "segments": [],
                "exploratory_source_ids": [eid, "NASA-INVENTED"],
                "exploration_queries": [],
            }

    provider = Provider()
    service = ConversationService(engine, provider=provider)
    response = service.chat(ChatRequest(message="flame extinction", max_queries=1))
    exploratory = [c for c in response.citations if c["category"] == "DISCOVERY"]
    assert len(exploratory) == 1
    assert exploratory[0]["evidence_id"] == provider.eid
    assert any(c["category"] == "DOCUMENTARY" for c in response.citations)
    assert "has not been established" in response.answer
    assert "NASA-INVENTED" not in response.answer


def test_controlled_terminology_expands_only_search_and_recovers_catalogue(engine):
    result = engine.search("droplet combustion extinction", limit=100)
    routes = result.metrics["candidate_generation"]["steps"]
    assert any(r["strategy"] == "controlled_terminology" for r in routes)
    assert any(r["source"]["source_id"] == "catalog-psi-69" for r in result.discovery)
    assert not result.direct


def test_exploratory_summary_deduplicates_sources_and_retains_broader_pool(engine):
    class Provider:
        def plan(self, question, history, max_queries):
            return {"resolved_question": question, "queries": []}

        def explain(self, payload, max_tokens):
            return {
                "segments": [],
                "exploratory_source_ids": [
                    r["evidence_id"] for r in payload["discovery_candidates"]
                ],
                "exploration_queries": [],
            }

    service = ConversationService(engine, provider=Provider(), max_exploratory_sources=2)
    response = service.chat(
        ChatRequest(message="flame extinction", max_queries=1, evidence_limit=40)
    )
    exploratory = [c for c in response.citations if c["category"] == "DISCOVERY"]
    assert 1 <= len(exploratory) <= 2
    keys = [
        c["source"].get("doi") or c["source"].get("url") or c["source"]["title"]
        for c in exploratory
    ]
    assert len(set(keys)) == len(keys)
    assert response.retrieval["retrieved"] > len(response.citations)
