"""The relation registry generated from the ontology, the semantic registry and the query language."""

from pathlib import Path

from nasa_fire_ai.ingestion.extraction_request import STAGE_INSTRUCTIONS, stage_prompt
from nasa_fire_ai.ingestion.relation_contracts import RELATION_ENDPOINTS
from nasa_fire_ai.ingestion.relation_registry import (
    relation_registry,
    relation_registry_prompt_enabled,
    relations_without_endpoints,
)

ROOT = Path(__file__).resolve().parent.parent


def test_every_relation_of_the_ontology_and_the_semantic_registry_is_listed():
    registry = relation_registry()
    ttl = (ROOT / "ontology" / "fire_safety.ttl").read_text("utf-8")
    for rid, row in registry.items():
        assert row["in_ontology"] == (f"fs:{rid} a owl:ObjectProperty" in ttl)
    assert {"usesSample", "madeOf", "hasRun"} <= set(registry)
    assert {"hasMaterial", "belongsToInvestigation"} <= set(registry)
    assert (
        registry["hasMaterial"]["in_registry"]
        and registry["belongsToInvestigation"]["selection_scope"]
    )
    assert registry["belongsToInvestigation"]["mentioned_by"] == ["saffire"]


def test_the_endpoint_contract_is_attached_in_its_order_and_nothing_is_invented():
    registry = relation_registry()
    with_endpoints = [r for r, row in registry.items() if row["endpoints"] is not None]
    assert with_endpoints == list(RELATION_ENDPOINTS)
    for rid, row in registry.items():
        if row["endpoints"] is not None:
            assert row["endpoints_source"] == "CONTRACT"
            assert row["endpoints"] == RELATION_ENDPOINTS[rid]


def test_the_relations_without_endpoints_stay_without_them():
    assert relations_without_endpoints() == [
        "belongTo",
        "concerns",
        "hasMeasurement",
        "hasObservation",
        "hasRun",
        "observesPhenomenon",
        "reportedBy",
    ]


def test_the_generation_does_not_touch_the_source_files():
    paths = [
        ROOT / "ontology" / "fire_safety.ttl",
        ROOT / "domain" / "semantic_registry.yaml",
        ROOT / "domain" / "query_language_v2.yaml",
    ]
    before = [p.read_bytes() for p in paths]
    relation_registry()
    assert [p.read_bytes() for p in paths] == before


def test_the_prompt_text_changes_only_behind_the_flag(monkeypatch):
    monkeypatch.delenv("SCIENCE_RELATION_REGISTRY_PROMPT", raising=False)
    assert not relation_registry_prompt_enabled()
    assert stage_prompt("relationships").endswith(STAGE_INSTRUCTIONS["relationships"])
    monkeypatch.setenv("SCIENCE_RELATION_REGISTRY_PROMPT", "1")
    prompt = stage_prompt("relationships")
    assert "relation_signatures" not in prompt and "ontology_context lists" in prompt
