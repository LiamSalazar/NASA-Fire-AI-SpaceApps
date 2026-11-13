"""Windows sent ahead of their turn change nothing but time; synthetic text, no live call."""

import json
import shutil
import threading
import time

from test_document_extraction import ROOT, client_for, entity, submitted, support

from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence.registry import EvidenceRegistry
from nasa_fire_ai.ingestion.document_extraction import ExtractionBudget, Output
from nasa_fire_ai.services.curation import CurationService

TEXT = "".join(
    f"# Run A{i} methods\n\nRun A{i} was tested in microgravity in the Synthetic study.\n\n"
    + "Unclassified documentary context. " * 60
    + f"\n\n# Run A{i} results\n\nA{i} flame extinguished.\n\n"
    for i in range(1, 7)
)


def extraction(tmp_path, monkeypatch, concurrency, delay=0.0):
    monkeypatch.setenv("SCIENCE_WINDOW_CONCURRENCY", str(concurrency))
    root = tmp_path / f"c{concurrency}"
    for name in ("domain", "ontology", "data/canonical"):
        shutil.copytree(ROOT / name, root / name)
    registry = EvidenceRegistry(root / "data/index/evidence.sqlite")
    service = CurationService(root, registry)
    package = submitted(service, TEXT)
    output = Output().model_dump()
    output["entities"] = [
        entity(package, f"a{i}", f"A{i}", "ExperimentalRun", f"Run A{i} was tested")
        for i in range(1, 7)
    ]
    output["statements"] = [
        {
            "text": f"A{i} flame extinguished.",
            "class_id": "ReportedObservation",
            "epistemic": "measured_observation",
            "subjects": [f"a{i}"],
            "study": "current",
            "support": support(package, f"A{i} flame extinguished."),
        }
        for i in range(1, 7)
    ]
    client = client_for(output)
    create = client.client.with_options.return_value.chat.completions.create
    respond, seen, busy, peak = create.side_effect, [], [0], [0]
    lock = threading.Lock()

    def slow(**kwargs):
        with lock:
            busy[0] += 1
            peak[0] = max(peak[0], busy[0])
        time.sleep(delay)
        seen.append(json.dumps(kwargs["messages"], sort_keys=True))
        with lock:
            busy[0] -= 1
        return respond(**kwargs)

    create.side_effect = slow
    result = service.prepare_scientific(
        package["id"],
        Settings(root=root),
        model_enabled=True,
        budget=ExtractionBudget(segment_chars=1000, stream=False),
        client=client,
    )
    registry.db.close()
    return result, sorted(seen), peak[0]


def comparable(result):
    extraction = result["package"]["scientific_extraction"]
    processing = {k: v for k, v in extraction["processing"].items() if k != "window_prefetch"}
    return extraction["records"], processing["new_model_calls"], result["package"]["statements"]


def test_concurrency_changes_neither_requests_nor_output(tmp_path, monkeypatch):
    one, requests_one, peak_one = extraction(tmp_path, monkeypatch, 1, delay=0.05)
    three, requests_three, peak_three = extraction(tmp_path, monkeypatch, 3, delay=0.05)
    assert peak_one == 1 and peak_three > 1
    # Metamorphic: the same requests reach the provider and the same records result.
    assert requests_one == requests_three
    assert comparable(one) == comparable(three)
    prefetch = three["package"]["scientific_extraction"]["processing"]["window_prefetch"]
    assert prefetch["used"] > 0
    assert prefetch["sent"] == prefetch["used"] + prefetch["discarded"] + prefetch.get(
        "cancelled", 0
    )
    assert "window_prefetch" not in one["package"]["scientific_extraction"]["processing"]


def test_a_rate_limit_stops_sending_ahead(tmp_path, monkeypatch):
    import httpx
    from openai import RateLimitError

    calls = [0]

    def limited(respond):
        def create(**kwargs):
            calls[0] += 1
            if calls[0] == 1:
                request = httpx.Request("POST", "https://example.invalid/v1/chat/completions")
                response = httpx.Response(429, headers={"retry-after": "0"}, request=request)
                raise RateLimitError("slow down", response=response, body=None)
            return respond(**kwargs)

        return create

    monkeypatch.setattr(
        "test_window_prefetch.client_for",
        lambda output, _make=client_for: _wrap(_make(output), limited),
    )
    result, _, _ = extraction(tmp_path, monkeypatch, 3, delay=0.05)
    prefetch = result["package"]["scientific_extraction"]["processing"]["window_prefetch"]
    assert prefetch.get("rate_limited") is True
    # The run still completes: the limited window retries on its turn.
    assert any("flame extinguished" in s["text"] for s in result["package"]["statements"])


def _wrap(client, limited):
    create = client.client.with_options.return_value.chat.completions.create
    create.side_effect = limited(create.side_effect)
    return client
