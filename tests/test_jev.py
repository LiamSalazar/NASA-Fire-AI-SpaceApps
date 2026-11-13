import pytest

from nasa_fire_ai.llm.jev import JevSettings, ask, decision_value, list_models


def test_missing_credential_fails_before_network():
    with pytest.raises(RuntimeError, match="TYPESAFE_API_KEY"):
        list_models(JevSettings(api_key=None))


def test_jev_advisory_triage_is_explicitly_opt_in(monkeypatch):
    monkeypatch.delenv("SEMANTIC_CLASSIFIER_BACKEND", raising=False)
    assert not JevSettings(api_key="test").advisory_triage_enabled
    monkeypatch.setenv("SEMANTIC_CLASSIFIER_BACKEND", "jev")
    assert JevSettings(api_key="test").advisory_triage_enabled


def test_typed_response_parser_handles_choice_and_score():
    assert decision_value({"answers": {"q": {"choice": "NONE", "confidence": 0.91}}}, "q") == (
        "NONE",
        0.91,
    )
    assert decision_value({"results": {"q": {"value": {"label": "Guidance"}}}}, "q") == (
        "Guidance",
        None,
    )


def test_request_uses_official_systemone_contract(monkeypatch):
    captured = {}

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"answers": {"q": {"value": "NONE"}}}

    def fake_post(url, headers, json, timeout):
        captured.update(url=url, headers=headers, json=json, timeout=timeout)
        return Response()

    monkeypatch.setattr("nasa_fire_ai.llm.jev.httpx.post", fake_post)
    settings = JevSettings(api_key="test", base_url="https://api.typesafe.ai", model="jev-1.13.0")
    answer = ask({"passage": "title"}, {"q": {"type": "choice"}}, settings)
    assert answer["answers"]["q"]["value"] == "NONE"
    assert captured["url"] == "https://api.typesafe.ai/v1/systemone"
    assert captured["json"]["model"] == "jev-1.13.0"
