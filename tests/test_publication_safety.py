"""Nothing not done is published as done: validation, curation and the projected graph.

Synthetic text and a controlled stand-in for the model; no live call, no NASA data.
"""

import copy

import pytest
from test_document_extraction import client_for, entity, submitted, support, validate
from test_document_extraction import service as _service
from test_scientific_facets import only, quantity, statement

from nasa_fire_ai.config import Settings
from nasa_fire_ai.ingestion.document_extraction import ExtractionBudget, Output
from nasa_fire_ai.query.native import SemanticGraph, node
from nasa_fire_ai.services.curation import project_package

service = _service
STUDY = "Synthetic study"


def projected(service, text, build):
    """Prepare ``text`` with the proposals ``build`` makes, project the package, and
    return (records, the ids present in the projected graph, the package)."""
    p = submitted(service, f"{STUDY}\nIII. Results and Discussion\n{text}\n")
    o = Output().model_dump()
    build(p, o)
    result = service.prepare_scientific(
        p["id"],
        Settings(root=service.root),
        model_enabled=True,
        budget=ExtractionBudget(max_model_calls=6),
        client=client_for(o),
    )
    package = result["package"]
    store = SemanticGraph(service.property_registry(package))
    project_package(store, package)
    subjects = {str(s) for s in store.graph.subjects()}
    in_graph = {
        r["id"]
        for r in package["scientific_extraction"]["records"]
        if str(node(r["id"])) in subjects
    }
    return package["scientific_extraction"]["records"], in_graph, package


@pytest.mark.parametrize(
    "sentence",
    [
        "Panel C3 will be burned again at 34 % oxygen.",
        "The pressure for Panel C3 must not exceed 50 kPa.",
    ],
)
def test_a_value_printed_as_not_done_is_held_and_never_projected(service, sentence):
    value = "34" if "34" in sentence else "50"
    unit = "%" if value == "34" else "kPa"

    def build(p, o):
        o["entities"] = [entity(p, "c3", "Panel C3", "Sample", sentence)]
        o["quantities"] = [
            quantity(
                p,
                sentence,
                "c3",
                "oxygen" if value == "34" else "pressure",
                value,
                unit,
                "experimental_configuration",
            )
        ]

    records, in_graph, package = projected(service, sentence, build)
    record = only(records, "quantities")
    assert record["status"] == "UNRESOLVED"
    assert "VALUE_PRINTED_AS_NOT_DONE_REQUIRES_REVIEW" in record["reasons"]
    assert record["id"] not in in_graph
    assert not [v for v in package["values"] if v["id"] == record["id"]]


def test_a_done_value_with_a_planning_aside_stays_done(service):
    # Metamorphic regression: "as planned" is not this value's modality.
    sentence = "Run A1 was burned at 34 % oxygen as planned."
    p = submitted(service, f"{STUDY}\nII. Methods\n{sentence}\n")
    o = Output().model_dump()
    o["entities"] = [entity(p, "a1", "A1", "ExperimentalRun", sentence)]
    o["quantities"] = [
        quantity(p, sentence, "a1", "oxygen", "34", "%", "experimental_configuration")
    ]
    record = only(validate(service, p, o)["records"], "quantities")
    assert record["status"] != "REJECTED", record["reasons"]
    assert "VALUE_PRINTED_AS_NOT_DONE_REQUIRES_REVIEW" not in record["reasons"]


def test_a_proposed_configuration_statement_is_kept_out_of_the_graph(service):
    sentence = "The follow-on tests will hold oxygen at 34 % for each panel."

    def build(p, o):
        o["entities"] = [entity(p, "inv", STUDY, "Investigation", STUDY)]
        o["statements"] = [
            statement(
                p,
                sentence,
                "experimental_configuration",
                "ExperimentalCondition",
                ["inv"],
                modality="proposed",
            )
        ]

    records, in_graph, package = projected(service, sentence, build)
    record = only(records, "statements")
    kept = [
        s
        for s in package["statements"]
        if s.get("scientific_proposal_id") == record["id"] or s.get("id") == record["id"]
    ]
    assert all(not s.get("included", True) for s in kept)
    assert record["id"] not in in_graph


@pytest.mark.parametrize(
    "sentence",
    [
        "The follow-on tests will hold oxygen at 34 % for each panel.",
        # Verbless: only the conflict between the two readings can hold it.
        "Planned oxygen for each panel: 34 %.",
    ],
)
def test_two_modality_readings_of_one_span_never_publish_a_done_reading(service, sentence):
    from nasa_fire_ai.ingestion.scientific_facets import facets

    p = submitted(service, f"{STUDY}\nIII. Results and Discussion\n{sentence}\n")
    o = Output().model_dump()
    o["entities"] = [entity(p, "inv", STUDY, "Investigation", STUDY)]
    plain = statement(p, sentence, "experimental_configuration", "ExperimentalCondition", ["inv"])
    proposed = {**plain, "modality": "proposed"}
    for order in ([plain, proposed], [proposed, plain]):
        o["statements"] = copy.deepcopy(order)
        records = [r for r in validate(service, p, o)["records"] if r["kind"] == "statements"]
        supported = [r for r in records if r["status"] == "SOURCE_SUPPORTED"]
        statuses = {facets("statements", r["proposal"])["execution_status"] for r in supported}
        assert len(statuses) <= 1
        assert "executed" not in statuses


@pytest.mark.parametrize("cls", ["ReportedObservation", "TestCriterion"])
def test_a_configuration_cannot_take_a_class_outside_its_set(service, cls):
    sentence = "Run A1 was held at 21 % oxygen."
    p = submitted(service, f"{STUDY}\nII. Methods\n{sentence}\n")
    o = Output().model_dump()
    o["entities"] = [entity(p, "a1", "A1", "ExperimentalRun", sentence)]
    o["statements"] = [statement(p, sentence, "experimental_configuration", cls, ["a1"])]
    record = only(validate(service, p, o)["records"], "statements")
    assert record["status"] == "REJECTED"
    assert any("CLASS_EPISTEMIC_CONTRADICTION" in r for r in record["reasons"])


def test_regenerating_twice_gives_the_same_package(service):
    sentence = "The follow-on tests will hold oxygen at 34 % for each panel."

    def build(p, o):
        o["entities"] = [entity(p, "inv", STUDY, "Investigation", STUDY)]
        o["quantities"] = [
            quantity(
                p, sentence, "inv", "oxygen", "34", "%", "experimental_configuration", "proposed"
            )
        ]

    _, _, package = projected(service, sentence, build)
    first = copy.deepcopy(package)
    service.regenerate(package)
    service.regenerate(package)
    assert package["non_executed_values"] == first["non_executed_values"]
    assert package == first or package["values"] == first["values"]


def test_a_saved_criterion_column_returns_to_its_mapping_question(service):
    # A package saved when criterion roles were also table-column roles.
    p = submitted(service, f"{STUDY}\nRun A1 burned.\n")
    p["tables"] = [
        {
            "id": "t1",
            "columns": [
                {
                    "label": "Test criterion",
                    "statement_role": "test criterion",
                    "unit": None,
                    "property_id": None,
                    "role": None,
                    "status": None,
                }
            ],
            "rows": [],
            "evidence_ids": [],
        }
    ]
    service.regenerate(p)
    assert p["tables"][0]["columns"][0]["statement_role"] is None
    assert support(p, "Run A1")  # the package is otherwise intact
