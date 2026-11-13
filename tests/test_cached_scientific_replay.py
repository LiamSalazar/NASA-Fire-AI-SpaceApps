"""Invalid archived output must reproduce a failure at its own provider stage."""

import runpy
from pathlib import Path

import pytest

from nasa_fire_ai.llm.interfaces import ProviderFailure

MODULE = runpy.run_path(str(Path(__file__).parents[1] / "scripts/replay_scientific_http.py"))


def test_archived_repair_failure_does_not_abort_unrelated_conversations():
    failed = MODULE["parse_cached_generation"]('{"segments":[{"text":"unfinished')
    assert isinstance(failed, MODULE["CachedGenerationFailure"])
    provider = MODULE["CachedPropositions"](
        {
            "q": {
                "queries": [{"query": "q"}],
                "information_needs": [],
                "cached_generations": {"draft": {"segments": []}, "repair-1": failed},
            }
        }
    )
    provider.plan("q", [], 1)
    assert provider.explain({}, 100) == {"segments": []}
    with pytest.raises(ProviderFailure, match="No complete generated segments"):
        provider.explain({}, 100)
    provider.plan("q", [], 1)
    assert provider.explain({}, 100) == {"segments": []}


def test_complete_archived_prefix_retains_only_original_complete_segments():
    original = '{"segments":[{"text":"Invented violet trace."},{"text":"unfinished'
    parsed = MODULE["parse_cached_generation"](original)
    assert parsed["segments"] == [{"text": "Invented violet trace."}]
