"""Requests sent ahead yield to an earlier window's retry before the brake refuses it.

Network-free: a fake client bills a fixed usage per request and fails chosen
requests once: a connection reset (sent, billing unknown, so the reservation is
kept), a refused connection or a 400 (never billed, so it is released). A brake with room for the whole run's billing plus its largest
reservation leaves every decision of concurrency 1 unchanged at concurrency 3.
"""

import json
import re
import threading
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest
from openai import APIStatusError
from test_document_extraction import submitted
from test_prefetch_brake import TEXT, USAGE, fresh_service

from nasa_fire_ai.config import Settings
from nasa_fire_ai.ingestion import document_extraction
from nasa_fire_ai.ingestion.document_extraction import STAGES, ExtractionBudget


def failure(kind):
    request = httpx.Request("POST", "https://provider.invalid/v1/chat/completions")
    if kind == "refused":
        return httpx.ConnectError("connection refused", request=request)
    if kind == "rejected":
        response = httpx.Response(400, request=request)
        return APIStatusError("bad request", response=response, body=None)
    return httpx.ReadError("connection reset after the request was sent", request=request)


CHEAP = 100


def price(stage, cheap):
    return CHEAP if stage in cheap else USAGE


def failing_client(failures, cheap=()):
    """Bill USAGE per answered request (CHEAP in ``cheap`` stages); fail once each
    (stage, run[, kind]) in ``failures``."""
    client, lock = Mock(), threading.Lock()
    sent, pending = [], set(failures)

    def respond(**kwargs):
        content = kwargs["messages"][1]["content"]
        payload = json.loads(content)
        with lock:
            sent.append(content)
            hit = next(
                (
                    f
                    for f in pending
                    if payload["stage"] == f[0] and re.search(rf"Run {f[1]} was", content)
                ),
                None,
            )
            pending.discard(hit)
        if hit:
            kind = hit[2] if len(hit) > 2 else "reset"
            if kind == "reset":
                # A reset comes after the request was sent: it takes a while, and the
                # requests sent ahead of it finish meanwhile. (time.sleep is patched.)
                threading.Event().wait(0.5)
            raise failure(kind)
        result = {k: [] for k in STAGES[payload["stage"]]}
        total = price(payload["stage"], cheap)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=json.dumps(result)), finish_reason="stop"
                )
            ],
            usage=SimpleNamespace(
                model_dump=lambda: {
                    "prompt_tokens": total - 50,
                    "completion_tokens": 50,
                    "total_tokens": total,
                }
            ),
        )

    client.client.with_options.return_value.chat.completions.create.side_effect = respond
    return client, sent


def run(tmp_path, monkeypatch, name, concurrency, brake, failures=(), cheap=()):
    monkeypatch.setenv("SCIENCE_WINDOW_CONCURRENCY", str(concurrency))
    # Retries wait Retry-After style backoff; the test does not need the wall time.
    monkeypatch.setattr(document_extraction.time, "sleep", lambda seconds: None)
    service = fresh_service(tmp_path / name)
    package = submitted(service, TEXT)
    client, sent = failing_client(failures, cheap)
    result = service.prepare_scientific(
        package["id"],
        Settings(root=service.root),
        model_enabled=True,
        budget=ExtractionBudget(segment_chars=1000, max_total_tokens=brake),
        client=client,
    )
    attempts = [
        json.loads(row[0])
        for row in service.registry.db.execute(
            "SELECT payload_json FROM phase3_cache WHERE cache_kind='scientific_document_attempt'"
        )
    ]
    service.registry.db.close()
    return result, sent, attempts


def decisions(result):
    return [
        (o.get("stage"), o["model"], o.get("attempts")) for o in result["processing"]["outcomes"]
    ]


def records(result):
    return json.dumps(result["package"]["scientific_extraction"]["records"], sort_keys=True)


def roomy_brake(result):
    """The run's whole billing plus its largest reservation: concurrency 1 never stops."""
    processing = result["processing"]
    largest = max(o.get("reserved_tokens_per_attempt", 0) for o in processing["outcomes"])
    return processing["tokens_consumed_or_reserved"] + largest


def retained_reservations(attempts):
    """Reservations kept for requests that left and failed without a known usage."""
    return sum(
        a["outcome"]["reserved_tokens_per_attempt"]
        for a in attempts
        if a.get("state") == "FINISHED"
        and a.get("outcome", {}).get("error_type") == "network"
        and not a["outcome"].get("transport", {}).get("request_not_sent")
    )


def billed(sent, failures, cheap=()):
    every = sum(price(json.loads(content)["stage"], cheap) for content in sent)
    return every - sum(price(f[0], cheap) for f in failures)


@pytest.mark.parametrize("stage", ["relationships", "propositions"])
def test_a_retry_in_window_one_completes_at_concurrency_three(tmp_path, monkeypatch, stage):
    failures = [(stage, "A1")]
    reference, _, _ = run(tmp_path, monkeypatch, "free", 1, None, failures)
    brake = roomy_brake(reference)
    one, sent_one, _ = run(tmp_path, monkeypatch, "one", 1, brake, failures)
    three, sent_three, _ = run(tmp_path, monkeypatch, "three", 3, brake, failures)
    assert decisions(one) == decisions(reference)
    assert "DEFERRED_BUDGET" not in {model for _, model, _ in decisions(three)}
    assert decisions(three) == decisions(one)
    assert records(three) == records(one)
    assert sorted(sent_three) == sorted(sent_one)


def test_billing_stays_under_the_brake_and_the_counter_is_billing_plus_kept_reservations(
    tmp_path, monkeypatch
):
    failures = [("relationships", "A1"), ("identity", "A4")]
    reference, _, _ = run(tmp_path, monkeypatch, "free", 1, None, failures)
    brake = roomy_brake(reference)
    for concurrency in (1, 3):
        result, sent, attempts = run(
            tmp_path, monkeypatch, f"c{concurrency}", concurrency, brake, failures
        )
        assert billed(sent, failures) <= brake
        assert result["processing"]["tokens_consumed_or_reserved"] == billed(
            sent, failures
        ) + retained_reservations(attempts)


@pytest.mark.parametrize(
    "failures",
    [
        [("identity", "A1")],
        [("identity", "A12")],
        [("propositions", "A5")],
        [("relationships", "A1"), ("relationships", "A2")],
        [("identity", "A3"), ("propositions", "A1"), ("relationships", "A7")],
    ],
)
def test_a_brake_with_room_for_the_run_decides_as_concurrency_one(tmp_path, monkeypatch, failures):
    reference, _, _ = run(tmp_path, monkeypatch, "free", 1, None, failures)
    brake = roomy_brake(reference)
    one, sent_one, _ = run(tmp_path, monkeypatch, "one", 1, brake, failures)
    three, sent_three, _ = run(tmp_path, monkeypatch, "three", 3, brake, failures)
    assert decisions(one) == decisions(reference)
    assert decisions(three) == decisions(one)
    assert records(three) == records(one)
    assert sorted(sent_three) == sorted(sent_one)


@pytest.mark.parametrize("kind", ["refused", "rejected"])
def test_a_request_sent_ahead_that_was_never_billed_makes_room_for_window_one(
    tmp_path, monkeypatch, kind
):
    # Window 2 (run A3; window 1 holds A1 and A2) is sent ahead and fails without
    # being billed; window 1 is retried.
    # Relationships bill little, so the brake with room for the run is tight there:
    # the retry fits only once window 2's reservation is released.
    failures = [("relationships", "A3", kind), ("relationships", "A1")]
    cheap = ("relationships",)
    reference, _, _ = run(tmp_path, monkeypatch, "free", 1, None, failures, cheap)
    brake = roomy_brake(reference)
    one, sent_one, _ = run(tmp_path, monkeypatch, "one", 1, brake, failures, cheap)
    three, sent_three, attempts = run(tmp_path, monkeypatch, "three", 3, brake, failures, cheap)
    assert decisions(one) == decisions(reference)
    assert "DEFERRED_BUDGET" not in {model for _, model, _ in decisions(three)}
    assert decisions(three) == decisions(one)
    assert records(three) == records(one)
    assert sorted(sent_three) == sorted(sent_one)
    counter = three["processing"]["tokens_consumed_or_reserved"]
    assert counter >= 0
    assert counter == billed(sent_three, failures, cheap) + retained_reservations(attempts)


@pytest.mark.parametrize(
    "failures",
    [
        [("relationships", "A2", "refused"), ("relationships", "A3", "rejected")],
        [("identity", "A2", "rejected"), ("relationships", "A1", "refused")],
        [("propositions", "A2", "refused"), ("relationships", "A1"), ("identity", "A5")],
    ],
)
def test_the_counter_never_goes_negative_and_is_billing_plus_kept_reservations(
    tmp_path, monkeypatch, failures
):
    reference, _, _ = run(tmp_path, monkeypatch, "free", 1, None, failures)
    for brake in (None, roomy_brake(reference)):
        result, sent, attempts = run(tmp_path, monkeypatch, f"c3_{brake}", 3, brake, failures)
        counter = result["processing"]["tokens_consumed_or_reserved"]
        assert counter >= 0
        assert counter == billed(sent, failures) + retained_reservations(attempts)
        if brake is not None:
            assert decisions(result) == decisions(reference)
