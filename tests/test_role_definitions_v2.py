"""SCIENCE_ROLE_DEFINITIONS_V2 (Track B, off): revised role definitions and the `basis` wire field."""

import json

import pytest
from test_document_extraction import entity, submitted, support, validate
from test_document_extraction import service as _service

from nasa_fire_ai.ingestion import scientific_facets as sf
from nasa_fire_ai.ingestion.document_extraction import Output
from nasa_fire_ai.ingestion.extraction_parsing import parse_stage_output
from nasa_fire_ai.ingestion.extraction_request import (
    EVIDENCE_BASIS_CONTRACT,
    STAGE_INSTRUCTIONS,
    stage_prompt,
    stage_schema,
)

service = _service
FLAG = "SCIENCE_ROLE_DEFINITIONS_V2"


def properties(name):
    return stage_schema("propositions")["$defs"][name]["properties"]


def test_off_the_bullets_and_the_schema_are_as_before(monkeypatch):
    monkeypatch.delenv(FLAG, raising=False)
    assert "basis" not in properties("Statement") and "basis" not in properties("Quantity")
    assert stage_prompt("propositions").endswith(STAGE_INSTRUCTIONS["propositions"])
    assert "simulation" not in sf.role_bullets("statements")


def test_on_the_definitions_are_revised_and_the_schema_offers_the_basis(monkeypatch):
    monkeypatch.setenv(FLAG, "1")
    bullets = sf.role_bullets("statements")
    assert "never an observation" in bullets and "requested of" in bullets
    assert "considered but not established" in bullets
    assert "basis" in properties("Statement") and "basis" in properties("Quantity")
    assert "simulated" in EVIDENCE_BASIS_CONTRACT


def test_every_revised_definition_is_a_bullet_of_the_same_role():
    for name, role in sf.ROLES.items():
        if role.definition_v2:
            assert role.definition and role.prompt_rank is not None, name


def parse(kind, item):
    body = {"statements": [], "quantities": [], "concepts": [], kind: [item]}
    return parse_stage_output(
        json.dumps(body),
        "propositions",
        {"A1": {"evidence_id": "E1", "quote": "x 9 s", "start": 0}},
        "stop",
    )[0]


QUANTITY = {
    "subject": "K1",
    "label": "x",
    "expression": "9",
    "unit": "s",
    "epistemic": "reported_quantity",
    "support": ["A1"],
}


def test_the_parser_refuses_a_basis_while_off_and_keeps_it_on(monkeypatch):
    monkeypatch.delenv(FLAG, raising=False)
    assert not parse("quantities", {**QUANTITY, "basis": "measured"})["quantities"]
    monkeypatch.setenv(FLAG, "1")
    assert (
        parse("quantities", {**QUANTITY, "basis": "measured"})["quantities"][0]["basis"]
        == "measured"
    )
    assert "basis" not in parse("quantities", QUANTITY)["quantities"][0]


@pytest.mark.parametrize(
    ("role", "basis", "ok"),
    [
        ("measured_observation", "measured", True),
        ("measured_observation", "simulated", False),
        ("measured_observation", "predicted", False),
        ("author_reported_conclusion", "simulated", True),
        ("tentative_interpretation", "predicted", True),
        ("derived_quantity", "computed", True),
        ("documentary_context", "retained", True),
        ("documentary_context", "measured", False),
    ],
)
def test_a_role_admits_only_its_bases(role, basis, ok):
    assert (basis in sf.allowed_bases(role)) is ok


def test_a_simulated_statement_is_not_accepted_as_an_observation(service, monkeypatch):
    monkeypatch.setenv(FLAG, "1")
    text = "The model gave a char depth of twelve millimeters."
    p = submitted(service, "Synthetic Study\nI. Results\n" + text + "\n")
    o = Output().model_dump()
    o["entities"] = [entity(p, "inv", "Synthetic Study", "Investigation", "Synthetic Study")]
    o["statements"] = [
        {
            "subjects": ["inv"],
            "text": text,
            "class_id": "ReportedObservation",
            "epistemic": "measured_observation",
            "study": "current",
            "basis": "simulated",
            "support": support(p, text),
        }
    ]
    record = next(r for r in validate(service, p, o)["records"] if r["kind"] == "statements")
    assert record["status"] == "REJECTED"
    assert "EVIDENCE_BASIS_CONTRADICTS_ROLE" in record["reasons"]
