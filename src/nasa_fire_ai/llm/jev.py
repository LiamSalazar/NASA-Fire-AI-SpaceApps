"""Optional TypeSafe Jev typed-decision client, with no scientific write authority."""

import os
from dataclasses import dataclass
from typing import Any

import httpx

from nasa_fire_ai.config import load_project_environment

load_project_environment()


@dataclass(frozen=True)
class JevSettings:
    api_key: str | None = os.getenv("TYPESAFE_API_KEY")
    base_url: str = os.getenv("TYPESAFE_BASE_URL", "https://api.typesafe.ai")
    model: str = os.getenv("JEV_MODEL", "jev-latest")

    def endpoint(self, path: str) -> str:
        return self.base_url.rstrip("/") + "/v1/" + path.lstrip("/")

    @property
    def advisory_triage_enabled(self) -> bool:
        """Opt-in only; callers still must preserve deterministic validation."""
        return os.getenv("SEMANTIC_CLASSIFIER_BACKEND", "rule").lower() == "jev"


def _headers(settings: JevSettings) -> dict[str, str]:
    if not settings.api_key:
        raise RuntimeError("Jev is not configured; set TYPESAFE_API_KEY")
    return {"Authorization": f"Bearer {settings.api_key}"}


def list_models(settings: JevSettings | None = None) -> dict[str, Any]:
    """Discover account-visible models. No model name is invented by the client."""
    settings = settings or JevSettings()
    response = httpx.get(settings.endpoint("models"), headers=_headers(settings), timeout=30)
    response.raise_for_status()
    return response.json()


def ask(
    state: str | dict[str, Any],
    questions: dict[str, dict[str, Any]],
    settings: JevSettings | None = None,
) -> dict[str, Any]:
    """Submit bounded typed decisions to System One; never creates candidate facts."""
    settings = settings or JevSettings()
    if not questions:
        raise ValueError("at least one typed Jev question is required")
    response = httpx.post(
        settings.endpoint("systemone"),
        headers=_headers(settings),
        json={"model": settings.model, "state": state, "questions": questions},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def decision_value(response: dict[str, Any], question_id: str) -> tuple[str | None, float | None]:
    """Parse explicit typed-decision envelopes without guessing a label."""
    container = (
        response.get("answers") or response.get("questions") or response.get("results") or response
    )
    answer = container.get(question_id) if isinstance(container, dict) else None
    if not isinstance(answer, dict):
        return None, None
    value = answer.get("value", answer.get("choice", answer.get("answer")))
    confidence = answer.get("confidence", answer.get("probability", answer.get("score")))
    if isinstance(value, dict):
        value = value.get("label", value.get("value"))
    return (
        str(value) if value is not None else None,
        float(confidence) if isinstance(confidence, (int, float)) else None,
    )


def classify_epistemic(
    state: dict[str, Any], settings: JevSettings | None = None
) -> dict[str, Any]:
    """A fixed closed-set routing decision for evaluation/review only."""
    return ask(
        state,
        {
            "epistemic_type": {
                "type": "choice",
                "instructions": (
                    "Classify rhetorical function only. Choose NONE for a title, project name, "
                    "objective, approach, infrastructure, relevance/impact text, noun phrase, "
                    "or text without an explicit supported claim. Do not infer science."
                ),
                "criteria": {
                    "Intervention": "an action explicitly performed in an experiment",
                    "ReportedExperimentalObservation": "an explicitly observed experimental event",
                    "NASAConclusion": "an explicit NASA conclusion",
                    "SafetyImplication": "an explicit operational/safety implication",
                    "Requirement": "an explicit normative requirement",
                    "Guidance": "explicit guidance",
                    "DesignCriterion": "explicit design criterion",
                    "TestCriterion": "explicit test criterion",
                    "NASAIdentifiedOpenQuestion": "explicit unresolved research need",
                    "NONE": "no supported epistemic claim",
                },
            }
        },
        settings,
    )


def triage_claim(state: dict[str, Any], settings: JevSettings | None = None) -> dict[str, Any]:
    """Bounded yes/no candidate-extraction triage, not a truth decision."""
    return ask(
        state,
        {
            "contains_candidate_claim": {
                "type": "noul",
                "instructions": (
                    "Does this passage explicitly contain a scientific or experimental claim suitable "
                    "for candidate extraction? Count only an actual intervention, observation, conclusion, "
                    "safety implication, normative statement, or explicit unresolved research need."
                ),
                "criteria": {
                    "true": "An explicit supported candidate claim is present.",
                    "false": "Title, project/theme, objective, approach, infrastructure, relevance/impact, noun phrase, or background only.",
                },
            }
        },
        settings,
    )
