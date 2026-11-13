"""Actual snapshot HTTP checks; fake generation tests only exercise the boundary."""

import json
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from nasa_fire_ai.api import create_app
from nasa_fire_ai.llm.interfaces import ProviderFailure
from nasa_fire_ai.services.conversation import ChatRequest, ConversationService
from nasa_fire_ai.services.search import ScientificSearchService
from nasa_fire_ai.services.semantic_support import verify_paraphrase

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "data/snapshots/hackathon-20261105-v9"


@pytest.fixture
def client():
    def factory():
        return ConversationService(ScientificSearchService(SNAPSHOT, ROOT))

    with TestClient(create_app(factory)) as client:
        yield client


def test_health_capabilities_validation_and_cors(client):
    assert client.get("/api/v1/health").status_code == 200
    assert client.get("/api/v1/capabilities").json()["streaming"] is False
    for message in ["", " ", "x" * 12001]:
        assert client.post("/api/v1/chat", json={"message": message}).status_code == 422
    assert (
        client.post("/api/v1/chat", json={"message": "fire", "max_queries": 7}).status_code == 422
    )
    assert (
        client.post("/api/v1/chat", json={"message": "fire", "provider_key": "secret"}).status_code
        == 422
    )
    allowed = client.options(
        "/api/v1/chat",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"},
    )
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
    rejected = client.options(
        "/api/v1/chat",
        headers={"Origin": "https://evil.invalid", "Access-Control-Request-Method": "POST"},
    )
    assert "access-control-allow-origin" not in rejected.headers
    assert client.post("/api/v1/chat", content=b"x" * 200001).status_code == 413


def test_offline_chat_context_unknown_session_and_evidence(client):
    response = client.post("/api/v1/chat", json={"message": "PMMA oxygen 22.2 %"})
    assert response.status_code == 200
    data = response.json()
    assert data["provider_status"]["status"] == "UNAVAILABLE"
    assert data["provider_status"]["generated_by"] is None
    assert data["evidence_groups"]["direct"]
    eid = data["evidence_groups"]["direct"][0]["evidence"][0]["evidence_id"]
    evidence = client.get("/api/v1/evidence/" + eid)
    assert evidence.status_code == 200
    assert evidence.json()["text"]
    assert "raw_file" not in evidence.json()
    followup = client.post(
        "/api/v1/chat",
        json={"message": "Which of those?", "conversation_id": data["conversation_id"]},
    )
    assert followup.status_code == 200
    assert followup.json()["conversation_id"] == data["conversation_id"]
    assert (
        client.post(
            "/api/v1/chat", json={"message": "fire", "conversation_id": str(uuid4())}
        ).status_code
        == 404
    )
    assert client.get("/api/v1/evidence/missing").status_code == 404


def test_search_comparison_scenario_catalog_ontology_source(client):
    result = client.post(
        "/api/v1/search", json={"query": "Saffire I airflow 30 cm/s", "limit": 3}
    ).json()
    assert result["related"] and not result["direct"]
    assert "raw_file" not in str(result)
    assert result["related"][0]["different_dimensions"]
    compare = client.post("/api/v1/comparisons", json={"subjects": ["psi-98-S1", "psi-98-S2"]})
    assert compare.status_code == 200
    assert compare.json()["matrix"]
    assert (
        client.post("/api/v1/comparisons", json={"subjects": ["invented", "unknown"]}).status_code
        == 404
    )
    scenario = client.post(
        "/api/v1/scenarios",
        json={
            "scenario_id": "test",
            "question": "lunar habitat PMMA",
            "provenance": "team_simulator",
            "simulator_results": [{"prediction": 999}],
        },
    )
    assert scenario.status_code == 200
    assert not scenario.json()["evidence"]["direct"]
    catalog = client.get("/api/v1/catalog?limit=2").json()
    assert len(catalog["items"]) == 2 and catalog["total"] > 2
    assert client.get("/api/v1/ontology?limit=2").status_code == 200
    sid = catalog["items"][0]["source_id"]
    assert client.get("/api/v1/sources/" + sid).status_code == 200
    assert client.get("/api/v1/catalog?limit=101").status_code == 422


class LogicalEntailment:
    """Synthetic entailment fixture, never used to measure scientific fidelity."""

    def check(self, premise, hypothesis):
        return {"supported": "FABRICATED" not in hypothesis, "synthetic": True}


class DraftProvider:
    def __init__(self):
        self.receipts = []

    def plan(self, question, history, max_queries):
        self.history = history
        return {"resolved_question": question, "queries": []}

    def explain(self, payload, max_tokens):
        anchor = next(a for a in payload["evidence"] if a["category"] == "DOCUMENTARY")
        return {
            "segments": [
                {"text": anchor["text"], "support_ids": [anchor["support_id"]]},
                {"text": "FABRICATED result", "support_ids": [anchor["support_id"]]},
                {"text": "Untraceable assertion", "support_ids": ["invented"]},
            ],
            "exploration_queries": ["airflow and detection conditions"],
        }


def test_partial_rejection_preserves_useful_information_and_context():
    engine = ScientificSearchService(SNAPSHOT, ROOT)
    provider = DraftProvider()
    service = ConversationService(engine, provider=provider, entailment=LogicalEntailment())
    try:
        response = service.chat(ChatRequest(message="NASA-STD-6001 requirements"))
        assert response.citations and "[1]" in response.answer
        assert "FABRICATED" not in response.answer
        assert response.provider_status["status"] == "AVAILABLE"
        assert response.verification_status["status"] == "PARTIAL"
        assert response.discovery_suggestions[0]["verified_relationship"] is False
        service.chat(
            ChatRequest(message="What about that method?", conversation_id=response.conversation_id)
        )
        assert provider.history[0]["content"] == "NASA-STD-6001 requirements"
        assert provider.history[1]["role"] == "assistant"
    finally:
        engine.close()


def test_provider_failure_and_missing_semantic_verifier():
    class Broken(DraftProvider):
        def plan(self, *args):
            raise ProviderFailure("private transport error")

        def explain(self, *args):
            raise ProviderFailure("private transport error")

    engine = ScientificSearchService(SNAPSHOT, ROOT)
    try:
        service = ConversationService(engine, provider=Broken())
        response = service.chat(ChatRequest(message="FLEX extinction"))
        assert response.provider_status["status"] == "DEGRADED"
        assert response.evidence_groups["discovery"] or response.evidence_groups["documentary"]
        assert "private transport" not in response.model_dump_json()
    finally:
        engine.close()


@pytest.mark.parametrize(
    "text,category,source_exists",
    [
        ("Temperature was 999 K.", "DIRECT", True),
        ("Temperature was 20 Pa.", "DIRECT", True),
        ("Temperature was 20 K.", "DISCOVERY", True),
        ("Temperature was 20 K.", "DIRECT", False),
    ],
)
def test_numeric_unit_source_and_discovery_adversaries(text, category, source_exists):
    class Registry:
        def resolve(self, eid):
            return {"text": "Temperature was 20 K."} if source_exists else None

    anchor = {
        "text": "Temperature was 20 K.",
        "category": category,
        "spans": [{"text": "Temperature was 20 K.", "evidence_id": "SYNTHETIC"}],
    }
    assert not verify_paraphrase(text, [anchor], Registry(), LogicalEntailment())["supported"]


def test_numeric_only_query_regression_and_unknown_explicit_context(client):
    # A property-only request previously referenced an import inside an empty
    # entity loop in constraint_explanation.
    result = client.post(
        "/api/v1/search",
        json={
            "query": "Give experimentally observed flame spread in a lunar habitat at oxygen 27.3 % and pressure 74.1 kPa."
        },
    )
    assert result.status_code == 200
    assert not result.json()["direct"]


def test_history_bounds_and_session_expiry():
    engine = ScientificSearchService(SNAPSHOT, ROOT)
    service = ConversationService(engine, max_sessions=1, session_ttl=0)
    try:
        first = service.chat(ChatRequest(message="pressure"))
        with pytest.raises(LookupError):
            service.chat(ChatRequest(message="and oxygen?", conversation_id=first.conversation_id))
    finally:
        engine.close()


def test_initialization_failure_is_service_unavailable():
    def broken():
        raise ValueError("private snapshot path and checksum")

    with TestClient(create_app(broken)) as client:
        response = client.post("/api/v1/search", json={"query": "fire"})
        assert response.status_code == 503
        assert "private snapshot" not in response.text


def test_bounded_read_worker_queues_overlapping_operations():
    import threading
    from concurrent.futures import ThreadPoolExecutor
    from types import SimpleNamespace

    started, release = threading.Event(), threading.Event()

    class Search:
        def search(self, **kwargs):
            started.set()
            assert release.wait(timeout=10)
            return {"synthetic": True}

        def close(self):
            pass

    with (
        TestClient(create_app(lambda: SimpleNamespace(search=Search()))) as client,
        ThreadPoolExecutor(2) as executor,
    ):
        first = executor.submit(client.post, "/api/v1/search", json={"query": "logical fixture"})
        assert started.wait(timeout=10)
        second = executor.submit(client.post, "/api/v1/search", json={"query": "overlap"})
        try:
            assert client.get("/api/v1/health").status_code == 200
            assert not second.done()
        finally:
            release.set()
        assert first.result().status_code == second.result().status_code == 200


def test_truncated_generation_recovers_only_complete_segments():
    from nasa_fire_ai.llm.conversation import complete_segments_prefix

    output = (
        '{"segments":[{"text":"Complete statement","support_ids":["known"]},{"text":"unfinished'
    )
    recovered = complete_segments_prefix(output)
    assert recovered == {
        "segments": [{"text": "Complete statement", "support_ids": ["known"]}],
        "exploration_queries": [],
    }
    with pytest.raises(ProviderFailure):
        complete_segments_prefix('{"segments":[{"text":"unfinished')


def test_documentary_pagination_advances_sources(client):
    first = client.post(
        "/api/v1/search", json={"query": "NASA-STD-6001 requirements", "limit": 2}
    ).json()
    second = client.post(
        "/api/v1/search", json={"query": "NASA-STD-6001 requirements", "limit": 1, "offset": 1}
    ).json()
    assert len(first["documentary"]) == 2
    assert [r["evidence_id"] for r in second["documentary"]] == [
        first["documentary"][1]["evidence_id"]
    ]


def test_scenario_parameters_validate_before_running_science(client):
    assert (
        client.post(
            "/api/v1/chat", json={"message": "fire", "scientific_parameters": {"unexpected": True}}
        ).status_code
        == 422
    )


def test_buffered_provider_failure_preserves_complete_objects_and_redacts_errors(
    tmp_path, monkeypatch
):
    from types import SimpleNamespace

    monkeypatch.setenv("NASA_GENERATION_ARCHIVE", str(tmp_path / "generations"))

    from nasa_fire_ai.llm.conversation import NemotronConversation

    class Stream:
        def __iter__(self):
            yield SimpleNamespace(
                model="SYNTHETIC-MODEL",
                usage=None,
                choices=[
                    SimpleNamespace(
                        finish_reason=None,
                        delta=SimpleNamespace(
                            content='{"segments":[{"text":"Synthetic statement","support_ids":["fixture"]},'
                        ),
                    )
                ],
            )
            raise RuntimeError("PRIVATE TRANSPORT MESSAGE")

        def close(self):
            self.closed = True

    class Client:
        def with_options(self, **options):
            self.options = options
            return self

        @property
        def chat(self):
            return SimpleNamespace(completions=self)

        def create(self, **kwargs):
            self.request = kwargs
            self.stream = Stream()
            return self.stream

    provider = NemotronConversation("SYNTHETIC-KEY", None, "SYNTHETIC-MODEL", timeout_seconds=95)
    provider.client = Client()
    result = provider.request(
        "explanation", "Synthetic protocol test", {"evidence": [{"support_id": "fixture"}]}, 1000
    )
    assert result["segments"][0]["support_ids"] == ["fixture"]
    archives = list((tmp_path / "generations").glob("*.json"))
    assert len(archives) == 1
    saved = json.loads(archives[0].read_text())
    assert saved["kind"] == "UNTRUSTED_PROVIDER_GENERATION"
    assert '"Synthetic statement"' in saved["raw_content"]
    assert "PRIVATE TRANSPORT MESSAGE" not in archives[0].read_text()
    assert "SYNTHETIC-KEY" not in archives[0].read_text()
    assert provider.receipts[-1]["generation_archive"] == archives[0].name
    assert provider.receipts[-1]["partial_generation"]
    assert provider.client.options == {"timeout": 95, "max_retries": 0}
    assert provider.client.stream.closed
    assert "PRIVATE TRANSPORT" not in str(provider.receipts)
    assert provider.client.request["stream"] is True


def test_followup_refreshes_previous_sources_after_degraded_turn():
    engine = ScientificSearchService(SNAPSHOT, ROOT)

    class ContextProvider(DraftProvider):
        def plan(self, question, history, max_queries):
            self.history = history
            return {
                "resolved_question": question,
                "queries": [],
                "use_previous_sources": bool(history),
            }

    provider = ContextProvider()
    service = ConversationService(engine, provider=provider, entailment=LogicalEntailment())
    try:
        first = service.chat(ChatRequest(message="NASA-STD-6001 requirements"))
        assert service.focus[first.conversation_id]["source_ids"]
        previous = service.focus[first.conversation_id]["source_ids"]
        second = service.chat(
            ChatRequest(
                message="Which test method does it describe?", conversation_id=first.conversation_id
            )
        )
        jobs = service.traces[second.trace_id]["queries"]
        assert any(job["source_scope"] == previous for job in jobs)
        assert all("Previous retrieval focus" not in job["query"] for job in jobs)
        assert len(jobs) <= 3
    finally:
        engine.close()


def test_documentary_locator_reexamination_stays_on_supplied_page():
    from types import SimpleNamespace

    class Registry:
        def resolve(self, eid):
            return {"text": "Definition A. Detail A."}

    class ExactLogicalSupport:
        def check(self, premise, hypothesis):
            return {"supported": hypothesis in premise}

    def anchor(identity, page, text, category="DOCUMENTARY"):
        return {
            "support_id": identity,
            "category": category,
            "epistemic_type": "documentary_content",
            "text": text,
            "spans": [{"evidence_id": page, "text": text}],
            "conditions": [],
        }

    service = ConversationService(
        SimpleNamespace(registry=Registry()), entailment=ExactLogicalSupport()
    )
    hint = anchor("hint", "page-one", "Definition A.")
    local = anchor("local", "page-one", "Detail A.")
    foreign = anchor("foreign", "page-two", "Detail A.")
    assert service._realign_documentary("Detail A.", [hint], {"foreign": foreign}) is None
    result = service._realign_documentary("Detail A.", [hint], {"local": local, "foreign": foreign})
    assert result[0][0]["support_id"] == "local"
    assert result[1]["locator_reexamined"]
    assert (
        service._realign_documentary(
            "Detail A.", [anchor("direct", "page-one", "Definition A.", "DIRECT")], {"local": local}
        )
        is None
    )


def test_english_verifier_guards_source_term_identity_generically():
    import snowballstemmer

    from nasa_fire_ai.services.semantic_support import LocalEntailment

    verifier = LocalEntailment.__new__(LocalEntailment)
    verifier._infer = lambda premise, hypothesis: {
        "supported": True,
        "probabilities": {"entailment": 0.99, "contradiction": 0.001},
    }
    verifier.stemmer = snowballstemmer.stemmer("english")
    verdict = verifier.check("The sample contained methanol.", "The sample contained ethanol.")
    assert not verdict["supported"]
    assert verdict["potential_term_substitutions"]


def test_output_preserves_reported_units_despite_normalized_metadata():
    class Registry:
        def resolve(self, eid):
            return {"text": "The recorded flow was 20 cm/s."}

    anchor = {
        "text": "The recorded flow was 20 cm/s.",
        "category": "DIRECT",
        "verified_context": "Normalized flow is 0.2 m/s.",
        "spans": [{"evidence_id": "SYNTHETIC", "text": "The recorded flow was 20 cm/s."}],
    }
    verdict = verify_paraphrase(
        "The recorded flow was 0.2 m/s.", [anchor], Registry(), LogicalEntailment()
    )
    assert not verdict["supported"]
    assert "Changed or unsupported numeric value/unit" in verdict["errors"]


def test_provider_failure_receipt_records_validation_status_without_authentication_messages(
    tmp_path, monkeypatch
):
    from types import SimpleNamespace

    from nasa_fire_ai.llm.conversation import NemotronConversation
    from nasa_fire_ai.llm.interfaces import ProviderFailure

    monkeypatch.setenv("NASA_GENERATION_ARCHIVE", str(tmp_path))

    class RequestError(Exception):
        status_code = 401

        @property
        def body(self):
            return {
                "error": {"code": "invalid_api_key", "message": "PRIVATE AUTHENTICATION DETAIL"}
            }

    class Client:
        def with_options(self, **options):
            return self

        @property
        def chat(self):
            return SimpleNamespace(completions=self)

        def create(self, **kwargs):
            raise RequestError()

    provider = NemotronConversation("SYNTHETIC-KEY", None, "SYNTHETIC-MODEL")
    provider.client = Client()
    with pytest.raises(ProviderFailure):
        provider.request("planning", "Synthetic protocol", {"question": "Fixture?"}, 200)
    assert provider.receipts[-1]["http_status"] == 401
    assert provider.receipts[-1]["provider_error_code"] == "invalid_api_key"
    archive = next(tmp_path.glob("*.failure.json"))
    assert "PRIVATE AUTHENTICATION DETAIL" not in archive.read_text()
    assert "SYNTHETIC-KEY" not in archive.read_text()


def test_http_followup_retains_receipts_when_provider_resets_its_turn_list():
    class PerTurnProvider(DraftProvider):
        def plan(self, question, history, max_queries):
            self.receipts = [{"stage": "planning", "latency_ms": 13}]
            return super().plan(question, history, max_queries)

        def explain(self, payload, max_tokens):
            self.receipts.append({"stage": "explanation", "latency_ms": 17})
            return {"segments": []}

    active = []

    def factory():
        service = ConversationService(
            ScientificSearchService(SNAPSHOT, ROOT), provider=PerTurnProvider()
        )
        active.append(service)
        return service

    with TestClient(create_app(factory)) as client:
        first = client.post("/api/v1/chat", json={"message": "Violet sensor catalogue"}).json()
        second = client.post(
            "/api/v1/chat",
            json={
                "message": "Which source describes that sensor?",
                "conversation_id": first["conversation_id"],
            },
        ).json()
        for response in (first, second):
            calls = active[0].traces[response["trace_id"]]["provider_calls"]
            assert any(c["stage"] == "planning" for c in calls)
            assert any(c["stage"] == "explanation" for c in calls)
