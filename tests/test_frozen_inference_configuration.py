"""The frozen-run configuration check covers the configured provider; synthetic settings only."""

import dataclasses
import importlib.util
from pathlib import Path

from nasa_fire_ai.config import Settings

SPEC = importlib.util.spec_from_file_location(
    "independent_driver_configuration",
    Path(__file__).resolve().parents[1] / "scripts/run_phase1_scientific_validation.py",
)
driver = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(driver)


def anthropic(**changes):
    base = dataclasses.replace(
        Settings(),
        science_provider="anthropic",
        anthropic_science_model="claude-sonnet-5-5",
        anthropic_science_fallback_models=(),
        anthropic_science_effort="high",
    )
    return dataclasses.replace(base, **changes)


def test_an_anthropic_fallback_or_effort_change_stops_a_frozen_run(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_SCIENCE_REQUEST_CONTEXT_TOKENS", raising=False)
    frozen = driver.inference_configuration(anthropic())
    assert frozen["provider"] == "anthropic" and frozen["effort"] == "high"
    fallback = anthropic(anthropic_science_fallback_models=("claude-opus-5-5",))
    assert driver.inference_configuration(fallback) != frozen
    assert driver.inference_configuration(anthropic(anthropic_science_effort="max")) != frozen


def test_an_nvidia_only_change_does_not_stop_an_anthropic_run(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_SCIENCE_REQUEST_CONTEXT_TOKENS", raising=False)
    frozen = driver.inference_configuration(anthropic())
    changed = anthropic(nvidia_science_fallback_models=("other/nvidia-model",))
    assert driver.inference_configuration(changed) == frozen


def test_the_nvidia_configuration_keeps_its_frozen_shape():
    nvidia = dataclasses.replace(Settings(), science_provider="nvidia")
    assert set(driver.inference_configuration(nvidia)) == {
        "model",
        "fallback_models",
        "vision_model",
        "endpoint",
        "provider_envelope",
    }


def test_a_billed_provider_runs_with_a_token_brake_by_default():
    assert driver.default_token_brake(None, anthropic()) == 500000
    assert driver.default_token_brake(200000, anthropic()) == 200000
    nvidia = dataclasses.replace(Settings(), science_provider="nvidia")
    assert driver.default_token_brake(None, nvidia) is None
