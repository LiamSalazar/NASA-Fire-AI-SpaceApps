"""Requests sent ahead obey the spending brake; with an unreached brake they change nothing."""

import json
import shutil
import threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from test_document_extraction import service as _service
from test_document_extraction import submitted

from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.document_extraction import STAGES, ExtractionBudget
from nasa_fire_ai.services.curation import CurationService

ROOT = Path(__file__).resolve().parents[1]

service = _service
USAGE = 10000

TEXT = "II. Methods\n" + "".join(
    f"Section {n}. Run A{n} was tested in a chamber at {n} kPa. "
    + "The synthetic run was repeated with the same igniter coil and the same flow. " * 10
    + "\n\n"
    for n in range(1, 13)
)


def billing_client():
    """A network-free client that bills a fixed usage for every request it receives."""
    client, lock, sent = Mock(), threading.Lock(), []

    def respond(**kwargs):
        payload = json.loads(kwargs["messages"][1]["content"])
        with lock:
            sent.append(kwargs["messages"][1]["content"])
        result = {k: [] for k in STAGES[payload["stage"]]}
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=json.dumps(result)), finish_reason="stop"
                )
            ],
            usage=SimpleNamespace(
                model_dump=lambda: {
                    "prompt_tokens": USAGE - 100,
                    "completion_tokens": 100,
                    "total_tokens": USAGE,
                }
            ),
        )

    client.client.with_options.return_value.chat.completions.create.side_effect = respond
    return client, sent


def run(service, monkeypatch, concurrency, max_total_tokens, text=TEXT):
    monkeypatch.setenv("SCIENCE_WINDOW_CONCURRENCY", str(concurrency))
    package = submitted(service, text)
    client, sent = billing_client()
    result = service.prepare_scientific(
        package["id"],
        Settings(root=service.root),
        model_enabled=True,
        budget=ExtractionBudget(segment_chars=1000, max_total_tokens=max_total_tokens),
        client=client,
    )
    return result, sent


def test_requests_sent_ahead_never_bill_past_the_brake(service, monkeypatch):
    result, sent = run(service, monkeypatch, concurrency=3, max_total_tokens=30000)
    assert len(sent) * USAGE <= 30000
    assert result["processing"]["tokens_consumed_or_reserved"] <= 30000


def test_nothing_is_sent_ahead_once_the_brake_is_reached(service, monkeypatch):
    result, sent = run(service, monkeypatch, concurrency=3, max_total_tokens=10)
    assert sent == []
    assert not result["processing"].get("window_prefetch", {}).get("sent")


def fresh_service(path):
    for name in ("domain", "ontology", "data/canonical"):
        shutil.copytree(ROOT / name, path / name)
    return CurationService(path, EvidenceRegistry(path / "data/index/evidence.sqlite"))


def test_an_unreached_brake_gives_the_same_package_at_any_concurrency(tmp_path, monkeypatch):
    # Equivalence: separate workspaces, so nothing is replayed from a cache; the
    # same requests are each sent once and the prepared packages are identical.
    runs = {}
    for concurrency in (1, 3):
        svc = fresh_service(tmp_path / f"c{concurrency}")
        result, sent = run(svc, monkeypatch, concurrency, max_total_tokens=None)
        runs[concurrency] = (result, sorted(sent))
        svc.registry.db.close()
    (one, sent_one), (three, sent_three) = runs[1], runs[3]
    # The same multiset of requests: sending ahead adds no request and drops none
    # (repeats the stage loop itself makes appear at both concurrencies).
    assert sent_one == sent_three
    assert len(sent_one) == 63
    records = [
        json.dumps(r["package"]["scientific_extraction"]["records"], sort_keys=True)
        for r in (one, three)
    ]
    assert records[0] == records[1]
