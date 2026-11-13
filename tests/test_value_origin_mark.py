"""SCIENCE_VALUE_ORIGIN_MARK: the model may mark the study that produced each quantity.

Off (the default) the field is not part of the contract: the request schema, the parser and every
record read as before. On, the field is offered, parsed and kept (invented text)."""

import json

from nasa_fire_ai.ingestion.extraction_parsing import parse_stage_output
from nasa_fire_ai.ingestion.extraction_request import (
    STAGE_INSTRUCTIONS,
    VALUE_ORIGIN_CONTRACT,
    stage_schema,
)

FLAG = "SCIENCE_VALUE_ORIGIN_MARK"
ANCHORS = {"A1": {"evidence_id": "E1", "quote": "x 9 s", "start": 0}}
ITEM = {
    "subject": "K1",
    "label": "x",
    "expression": "9",
    "unit": "s",
    "epistemic": "reported_quantity",
    "support": ["A1"],
}


def quantity_properties():
    return stage_schema("propositions")["$defs"]["Quantity"]["properties"]


def parse(items):
    content = json.dumps({"statements": [], "quantities": items, "concepts": []})
    return parse_stage_output(content, "propositions", ANCHORS, "stop")


def test_the_field_is_not_offered_while_the_flag_is_off(monkeypatch):
    monkeypatch.delenv(FLAG, raising=False)
    assert "study" not in quantity_properties()


def test_the_field_is_offered_with_the_flag_on(monkeypatch):
    monkeypatch.setenv(FLAG, "1")
    assert quantity_properties()["study"]["description"].startswith("The study that produced")


def test_an_unset_study_is_dropped_from_the_parsed_item(monkeypatch):
    monkeypatch.delenv(FLAG, raising=False)
    parsed = parse([ITEM])
    assert "study" not in parsed[0]["quantities"][0]
    monkeypatch.setenv(FLAG, "1")
    parsed = parse([ITEM])
    assert "study" not in parsed[0]["quantities"][0]


def test_a_study_is_refused_while_the_flag_is_off_and_kept_with_it_on(monkeypatch):
    monkeypatch.delenv(FLAG, raising=False)
    off = parse([{**ITEM, "study": "cited"}])
    assert not off[0]["quantities"]
    monkeypatch.setenv(FLAG, "1")
    on = parse([{**ITEM, "study": "cited"}])
    assert on[0]["quantities"][0]["study"] == "cited"


def test_the_contract_line_is_invented_text():
    assert "study" in VALUE_ORIGIN_CONTRACT
    assert "<<role_bullets>>" not in STAGE_INSTRUCTIONS["propositions"]
