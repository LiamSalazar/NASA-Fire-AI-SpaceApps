import json
from types import SimpleNamespace

import pytest

from nasa_fire_ai.llm.conversation import SonnetConversation
from nasa_fire_ai.llm.evaluation_budget import EvaluationBudget
from nasa_fire_ai.llm.interfaces import ProviderFailure


class FakeMessages:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            model="claude-sonnet-5-5",
            stop_reason="end_turn",
            content=[SimpleNamespace(type="text", text=json.dumps({"retained_indices": [0]}))],
            usage=SimpleNamespace(
                input_tokens=100,
                output_tokens=20,
                cache_read_input_tokens=0,
                cache_creation_input_tokens=0,
            ),
        )


def test_sonnet_uses_shared_contract_cache_and_hard_call_cap(tmp_path, monkeypatch):
    monkeypatch.setenv("NASA_SONNET_EVAL_ENABLED", "1")
    monkeypatch.setenv("NASA_SONNET_EVAL_DIR", str(tmp_path))
    monkeypatch.setenv("NASA_SONNET_EVAL_CALL_CAP", "1")
    provider = SonnetConversation("synthetic", "claude-sonnet-5-5")
    assert provider.provider_identity == "Anthropic"
    assert provider.generation_name == "Sonnet"
    messages = FakeMessages()
    provider.client = SimpleNamespace(
        with_options=lambda **kwargs: SimpleNamespace(messages=messages)
    )
    first = provider.request(
        "relevance_review",
        "Review source checked prose.",
        {"question": "A?", "paragraphs": ["A."], "history": []},
        100,
    )
    assert first == {"retained_indices": [0]}
    assert messages.calls[0]["output_config"]["format"]["type"] == "json_schema"
    assert (
        provider.request(
            "relevance_review",
            "Review source checked prose.",
            {"question": "A?", "paragraphs": ["A."], "history": []},
            100,
        )
        == first
    )
    assert len(messages.calls) == 1
    with pytest.raises(ProviderFailure):
        provider.request(
            "relevance_review",
            "Review source checked prose.",
            {"question": "B?", "paragraphs": ["B."], "history": []},
            100,
        )
    saved = [json.loads(p.read_text()) for p in tmp_path.glob("*.json")]
    assert len(saved) == 1 and saved[0]["cost_usd"] > 0


def test_sonnet_budget_stops_after_rate_limit_receipt(tmp_path, monkeypatch):
    monkeypatch.setenv("NASA_SONNET_EVAL_DIR", str(tmp_path))
    budget = EvaluationBudget()
    budget.save("prior", {"paid_attempt": True, "error": "RateLimitError", "cost_usd": 0})
    with pytest.raises(RuntimeError, match="provider limit"):
        budget.authorize("new", 100, 100)
