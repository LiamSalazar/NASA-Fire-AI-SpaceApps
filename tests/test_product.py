from pathlib import Path

import pytest

from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.llm.interfaces import NotConfigured, OpenAIScientificSynthesizer
from nasa_fire_ai.query import parse_query
from nasa_fire_ai.services import build_bundle, scientific_answer

ROOT = Path(__file__).resolve().parents[1]


def test_scientific_answer_comparison_export_and_sources():
    q = "Compare Saffire runs"
    b = build_bundle(parse_query(q), q, ROOT, EvidenceRegistry(Settings().registry_path))
    a = scientific_answer(q, b, ROOT)
    assert a.comparison and "flow_direction" in a.comparison.different_conditions
    assert a.model_dump_json() and all("evidence_id" in s for s in a.sources)


def test_no_direct_preserved_and_future_adapter_disabled():
    q = "unindexed material"
    b = build_bundle(parse_query(q), q, ROOT, EvidenceRegistry(Settings().registry_path))
    a = scientific_answer(q, b, ROOT)
    assert a.direct_evidence_status == "NO_DIRECT_EVIDENCE"
    with pytest.raises(NotConfigured):
        OpenAIScientificSynthesizer().synthesize(a)
