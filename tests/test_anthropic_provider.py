"""The Anthropic transport with a stand-in client; no live call, synthetic text only."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import anthropic
import httpx2
import pytest

from nasa_fire_ai.config import Settings
from nasa_fire_ai.llm import anthropic_provider
from nasa_fire_ai.llm.anthropic_provider import AnthropicScientificClient, structured_schema
from nasa_fire_ai.llm.scientific_provider import (
    ScientificTransportError,
    complete_scientific,
    redact_provider_text,
)

ROOT = Path(__file__).resolve().parents[1]
# Synthetic keys, built at run time so no key-shaped literal is committed.
KEY = "sk" + "-ant-" + "synthetic0value0000"
NVIDIA_KEY = "nvapi" + "-" + "synthetic0value"

SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "stage",
        "schema": {
            "type": "object",
            "properties": {
                "statements": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "properties": {"anchor": {"type": "string", "minLength": 1}},
                        "required": ["anchor"],
                    },
                }
            },
            "required": ["statements"],
        },
    },
}


def message(text, stop="end_turn"):
    return SimpleNamespace(
        content=[SimpleNamespace(type="thinking"), SimpleNamespace(type="text", text=text)],
        stop_reason=stop,
        stop_details=None,
        model="claude-sonnet-5-5",
        usage=SimpleNamespace(
            input_tokens=100,
            output_tokens=40,
            cache_read_input_tokens=900,
            cache_creation_input_tokens=0,
        ),
    )


class Stream:
    def __init__(self, text, stop):
        self.text, self.stop = text, stop

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def __iter__(self):
        for piece in (self.text[:5], self.text[5:]):
            yield SimpleNamespace(
                type="content_block_delta", delta=SimpleNamespace(type="text_delta", text=piece)
            )

    def close(self):
        pass

    def get_final_message(self):
        return message(self.text, self.stop)


class Messages:
    def __init__(self, owner):
        self.owner = owner

    def stream(self, **request):
        self.owner.requests.append(request)
        if self.owner.error:
            raise self.owner.error
        return Stream(self.owner.text, self.owner.stop)


class FakeSDK:
    def __init__(self, text='{"statements": []}', stop="end_turn", error=None):
        self.text, self.stop, self.error, self.requests = text, stop, error, []
        self.api_key = KEY
        self.messages = Messages(self)
        self.beta = SimpleNamespace(messages=Messages(self))

    def with_options(self, **options):
        self.options = options
        return self


def client(**fake):
    c = AnthropicScientificClient(KEY, "claude-sonnet-5-5")
    c.client = FakeSDK(**fake)
    return c


def call(c, **extra):
    return complete_scientific(
        c,
        model="claude-sonnet-5-5",
        system="Stage instructions.",
        payload="Synthetic source text.",
        max_tokens=10240,
        timeout=60,
        response_format=SCHEMA,
        **extra,
    )


def test_one_call_returns_the_nvidia_shaped_response():
    c = client()
    seen = []
    response = call(c, on_progress=lambda text, meta: seen.append(text))
    assert response.content == '{"statements": []}'
    assert response.finish_reason == "stop"
    assert response.usage["total_tokens"] == 1040 and response.usage["prompt_tokens"] == 1000
    assert response.metadata["served_models"] == ["claude-sonnet-5-5"]
    assert response.metadata["started_at"]
    assert seen[-1] == '{"statements": []}'
    (request,) = c.client.requests
    # Adaptive thinking is on by default: no thinking, temperature or sampling sent.
    assert not {"thinking", "temperature", "top_p", "top_k"} & set(request)
    # The stage asked for 10,240; the floor (default 32,768) leaves room for thinking.
    assert request["max_tokens"] == max(10240, anthropic_provider.MIN_MAX_TOKENS)
    assert request["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert request["output_config"]["effort"] == "high"
    assert request["fallbacks"] == "default"
    assert request["betas"] == ["server-side-fallback-2026-07-01"]
    assert c.client.options["max_retries"] == 0


def test_the_schema_drops_constraints_structured_outputs_rejects():
    schema = structured_schema(SCHEMA["json_schema"]["schema"])
    items = schema["properties"]["statements"]
    assert "minItems" not in items and "minLength" not in items["items"]["properties"]["anchor"]
    assert schema["additionalProperties"] is False
    assert items["items"]["additionalProperties"] is False


def test_without_a_schema_a_fenced_answer_is_plain_json():
    c = client(text='```json\n{"statements": []}\n```')
    response = complete_scientific(
        c,
        model="claude-sonnet-5-5",
        system="Stage instructions.",
        payload="Synthetic source text.",
        max_tokens=10240,
        timeout=60,
        response_format={"type": "json_object"},
    )
    assert response.content == '{"statements": []}'
    assert "format" not in c.client.requests[0]["output_config"]


def test_a_truncated_answer_is_a_length_finish():
    assert call(client(text='{"statements": [', stop="max_tokens")).finish_reason == "length"


def test_a_rate_limit_is_a_rate_limit_and_the_key_never_reaches_the_receipt():
    response = httpx2.Response(
        429,
        headers={"retry-after": "7"},
        request=httpx2.Request("POST", "https://api.anthropic.com/v1/messages"),
    )
    error = anthropic.RateLimitError(
        "slow down",
        response=response,
        body={"error": {"message": "key " + KEY + " over limit"}},
    )
    with pytest.raises(ScientificTransportError) as raised:
        call(client(error=error))
    assert raised.value.kind == "rate_limit" and raised.value.retry_after == "7"
    assert KEY not in raised.value.metadata["provider_message"]


def test_a_receipt_with_either_provider_key_is_refused(tmp_path):
    spec = importlib.util.spec_from_file_location(
        "phase1_exposed_live_run", ROOT / "scripts" / "phase1_exposed_live_run.py"
    )
    script = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(script)
    for i, key in enumerate((KEY, NVIDIA_KEY)):
        with pytest.raises(RuntimeError):
            script.write(tmp_path / f"key{i}.json", {"note": key})
    assert redact_provider_text("key " + KEY, KEY) == "key [REDACTED]"


def test_nvidia_stays_the_default_provider():
    nvidia = Settings(nvidia_api_key="n", anthropic_api_key="a")
    assert nvidia.science_provider == "nvidia" and nvidia.science_api_key == "n"
    chosen = Settings(science_provider="anthropic", anthropic_api_key="a", nvidia_api_key="n")
    assert chosen.scientific_model == "claude-sonnet-5-5"
    assert chosen.science_api_key == "a" and chosen.science_fallback_models == ()
