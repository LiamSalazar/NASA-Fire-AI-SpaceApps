"""Deterministic orchestration tests; no model calls or NASA answer fixtures."""

from threading import Event, get_ident
from time import monotonic, sleep
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from nasa_fire_ai.api import create_app
from nasa_fire_ai.services.operations import checkpoint


def wait_status(client, operation, statuses):
    deadline = monotonic() + 5
    while monotonic() < deadline:
        result = client.get("/api/v1/chat/operations/" + operation).json()
        if result["status"] in statuses:
            return result
        sleep(0.01)
    pytest.fail(f"Operation did not enter {statuses}")


@pytest.mark.parametrize("stage", ["retrieval", "generation", "verification"])
def test_cancel_each_stage_preserves_read_lane_and_releases_queue(stage):
    entered, release = Event(), Event()
    committed, owners = [], {}

    class Search:
        def __init__(self):
            self.manifest = {"sources": [{"source_id": "invented-fixture"}]}

        def search(self):
            if stage == "retrieval":
                entered.set()
                assert release.wait(5)

        def close(self):
            pass

    class Provider:
        def explain(self):
            if stage == "generation":
                entered.set()
                assert release.wait(5)

    class Verifier:
        def check(self):
            if stage == "verification":
                entered.set()
                assert release.wait(5)

    def factory():
        service = SimpleNamespace(search=Search(), provider=Provider(), entailment=Verifier())
        owners[id(service)] = get_ident()

        def chat(request):
            assert owners[id(service)] == get_ident()
            service.search.search()
            service.provider.explain()
            service.entailment.check()
            checkpoint("publishing")
            committed.append(request.message)
            return {"answer": request.message}

        service.chat = chat
        return service

    with TestClient(create_app(factory)) as client:
        a = client.post("/api/v1/chat/operations", json={"message": "fixture A"}).json()[
            "operation_id"
        ]
        assert entered.wait(5)
        b = client.post("/api/v1/chat/operations", json={"message": "fixture B"}).json()[
            "operation_id"
        ]
        queued = wait_status(client, b, {"queued"})
        assert queued["queue_position"] == 1
        began = monotonic()
        assert client.get("/api/v1/catalog").status_code == 200
        assert monotonic() - began < 1
        assert len(set(owners.values())) == 2
        path = "/api/v1/chat/operations/"
        assert client.post(path + b + "/cancel").json()["status"] == "canceled"
        assert client.post(path + b + "/cancel").json()["status"] == "canceled"
        assert client.post(path + a + "/cancel").json()["status"] == "cancellation_requested"
        assert client.get(path + a).json()["status"] != "canceled"
        release.set()
        wait_status(client, a, {"canceled"})
        c = client.post(path.rstrip("/"), json={"message": "fixture C"}).json()["operation_id"]
        result = wait_status(client, c, {"completed"})
        assert result["result"]["answer"] == "fixture C"
        assert committed == ["fixture C"]
        assert result["queue_seconds"] >= 0 and result["execution_seconds"] >= 0


def test_queue_has_a_bound_and_cancellation_frees_capacity():
    entered, release = Event(), Event()

    def factory():
        def chat(request):
            entered.set()
            assert release.wait(5)
            checkpoint()
            return {}

        return SimpleNamespace(search=SimpleNamespace(close=lambda: None), chat=chat)

    with TestClient(create_app(factory)) as client:
        ids = []
        try:
            for _ in range(8):
                response = client.post("/api/v1/chat/operations", json={"message": "fixture"})
                assert response.status_code == 202
                ids.append(response.json()["operation_id"])
            assert entered.wait(5)
            assert (
                client.post("/api/v1/chat/operations", json={"message": "overflow"}).status_code
                == 503
            )
            client.post("/api/v1/chat/operations/" + ids[-1] + "/cancel")
            assert (
                client.post("/api/v1/chat/operations", json={"message": "replacement"}).status_code
                == 202
            )
        finally:
            release.set()


def test_real_scientific_routes_respond_during_active_conversation():
    from pathlib import Path

    from nasa_fire_ai.services.conversation import ConversationService
    from nasa_fire_ai.services.search import ScientificSearchService

    root = Path(__file__).resolve().parents[1]
    entered, release = Event(), Event()

    class PausedProvider:
        def plan(self, *args):
            entered.set()
            assert release.wait(60)
            return {}

    def factory():
        return ConversationService(
            ScientificSearchService(
                root / "data/snapshots/hackathon-20261112-scientific-rc14", root
            ),
            provider=PausedProvider(),
        )

    with TestClient(create_app(factory)) as client:
        # Warm the source inventory before measuring steady-state read latency.
        overview = client.get("/api/v1/research/overview").json()
        op = client.post(
            "/api/v1/chat/operations", json={"message": "orchestration fixture"}
        ).json()["operation_id"]
        try:
            assert entered.wait(60)
            began = monotonic()
            material = overview["facets"]["hasMaterial"][0]["id"]
            assert (
                client.get(
                    "/api/v1/research/investigations", params={"material": material}
                ).status_code
                == 200
            )
            records = client.get("/api/v1/records?investigation=psi-100").json()["items"]
            assert (
                client.get(
                    "/api/v1/evidence/" + records[0]["evidence"][0]["evidence_id"]
                ).status_code
                == 200
            )
            assert client.get("/api/v1/research/entities/psi-107/neighbors").status_code == 200
            response = client.post(
                "/api/v1/comparisons",
                json={"subjects": [records[0]["id"], records[1]["id"]], "dimensions": []},
            )
            assert response.status_code == 200 and response.json()["matrix"]
            assert monotonic() - began < 10
            assert client.get("/api/v1/chat/operations/" + op).json()["status"] == "running"
            client.post("/api/v1/chat/operations/" + op + "/cancel")
        finally:
            release.set()
        wait_status(client, op, {"canceled"})


def test_read_factory_does_not_load_conversation_resources():
    def read_factory():
        return SimpleNamespace(search=SimpleNamespace(manifest={"sources": []}, close=lambda: None))

    def expensive_factory():
        pytest.fail("Browsing must not instantiate provider or NLI resources")

    with TestClient(create_app(expensive_factory, read_service_factory=read_factory)) as client:
        assert client.get("/api/v1/catalog").json()["total"] == 0


def test_readiness_reports_the_conversation_lane_resources():
    def factory():
        return SimpleNamespace(
            search=SimpleNamespace(
                manifest={"snapshot_id": "fixture-snapshot"},
                semantic_candidates=object(),
                close=lambda: None,
            ),
            provider=object(),
            entailment=object(),
        )

    def read_factory():
        pytest.fail("Readiness must inspect the actual conversation resources")

    with TestClient(create_app(factory, read_service_factory=read_factory)) as client:
        response = client.get("/api/v1/readiness")
        assert response.status_code == 200
        assert response.json()["scientific_mode"] == "hybrid_conversational"
