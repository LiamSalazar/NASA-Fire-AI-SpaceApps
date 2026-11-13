from pathlib import Path

from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.query import parse_query
from nasa_fire_ai.services import build_bundle, render

ROOT = Path(__file__).resolve().parents[1]


def bundle(query):
    return build_bundle(parse_query(query), query, ROOT, EvidenceRegistry(Settings().registry_path))


def test_offline_parser_known_vocabulary_and_numeric_constraint():
    intent = parse_query("Compare Saffire microgravity airflow <= 20 cm/s")
    assert intent.query_mode == "compare"
    assert intent.investigations == ["psi-98"]
    assert intent.flow_velocity.value == 20 and intent.flow_velocity.unit == "cm/s"


def test_combined_bundle_keeps_safety_documentary_evidence_out_of_direct():
    result = bundle(
        "PMMA microgravity suppression what was observed and what open question remains"
    )
    assert not result.direct_evidence and result.no_direct_evidence
    assert result.nasa_identified_open_questions
    assert result.interventions and result.experimental_observations


def test_pure_experimental_query_and_graph_constrained_passages():
    result = bundle("Compare Saffire runs")
    assert {item["id"] for item in result.direct_evidence} >= {"psi-98-S1", "psi-98-S2"}
    assert all("psi-98" in item["evidence_id"] for item in result.evidence_passages)


def test_related_and_no_direct_are_independent_from_open_questions():
    related = bundle("SIBAL Fabric microgravity airflow <= 0.10 m/s")
    assert not related.direct_evidence and related.related_evidence
    absent = bundle("unindexed material xenon combustion")
    assert absent.no_direct_evidence and not absent.nasa_identified_open_questions


def test_renderer_is_extractive_and_evidence_backed():
    result = bundle("PMMA suppression open question")
    output = render(result)
    assert "because" not in output.lower()
    for record in (
        result.nasa_conclusions + result.safety_implications + result.nasa_identified_open_questions
    ):
        assert record["evidence_refs"]
        assert record["evidence_refs"][0]["evidence_id"] in output
