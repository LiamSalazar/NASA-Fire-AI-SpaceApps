"""Anthropic requests get their own size limit before a window is split; NVIDIA keeps its own.

Every test sets or clears ANTHROPIC_SCIENCE_REQUEST_CONTEXT_TOKENS itself, so a local
.env value (for example 65536 to revert) cannot change the outcome.
"""

import dataclasses
from types import SimpleNamespace

import pytest
from test_document_extraction import client_for, entity, submitted
from test_document_extraction import service as _service

from nasa_fire_ai.config import Settings
from nasa_fire_ai.ingestion.document_extraction import (
    ExtractionBudget,
    Output,
    request_context_limit,
)
from nasa_fire_ai.ingestion.extraction_resources import ProviderEnvelope, segment_size

service = _service
VARIABLE = "ANTHROPIC_SCIENCE_REQUEST_CONTEXT_TOKENS"


def anthropic():
    return SimpleNamespace(science_provider="anthropic")


def test_anthropic_requests_have_their_own_limit(monkeypatch):
    monkeypatch.delenv(VARIABLE, raising=False)
    assert request_context_limit(anthropic(), ProviderEnvelope()) == 96000
    monkeypatch.setenv(VARIABLE, "80000")
    assert request_context_limit(anthropic(), ProviderEnvelope()) == 80000


@pytest.mark.parametrize("value", ["131073", "1000000", "4095"])
def test_a_limit_outside_the_guard_is_refused(monkeypatch, value):
    # Past 131,072 a single request could cost about 2 USD of input.
    monkeypatch.setenv(VARIABLE, value)
    with pytest.raises(ValueError, match=VARIABLE):
        request_context_limit(anthropic(), ProviderEnvelope())


def test_nvidia_keeps_its_envelope(monkeypatch):
    monkeypatch.setenv(VARIABLE, "80000")
    envelope = ProviderEnvelope()
    assert request_context_limit(SimpleNamespace(science_provider="nvidia"), envelope) == (
        envelope.context_tokens
    )


def test_windows_do_not_depend_on_the_request_limit(monkeypatch):
    # Metamorphic: the window size comes from the provider envelope only, so a
    # larger Anthropic limit splits fewer requests without changing any window.
    package = {"evidence": [{"text": "A run was tested. " * 4000}]}
    budget = SimpleNamespace(segment_chars=None, max_output_tokens=None)
    sizes = []
    for limit in ("65536", "96000"):
        monkeypatch.setenv(VARIABLE, limit)
        sizes.append(segment_size(package, budget, ProviderEnvelope()))
    assert sizes[0] == sizes[1]


def test_an_anthropic_request_over_the_limit_is_still_split(service, monkeypatch):
    # Negative: the limit moves the split point, it never removes the split.
    monkeypatch.setenv(VARIABLE, "4096")
    p = submitted(service, "II. Methods\n" + "Run A1 used the Beta igniter coil. " * 40 + "\n")
    o = Output().model_dump()
    o["entities"] = [entity(p, "a1", "A1", "ExperimentalRun", "Run A1 used")]
    settings = dataclasses.replace(Settings(root=service.root), science_provider="anthropic")
    result = service.prepare_scientific(
        p["id"],
        settings,
        model_enabled=True,
        budget=ExtractionBudget(max_model_calls=8),
        client=client_for(o),
    )
    outcomes = result["processing"]["outcomes"]
    assert any(o.get("model") == "NEEDS_CONTEXT_SPLIT" for o in outcomes)
    assert result["processing"]["resource_policy"]["request_context_tokens"] == 4096
