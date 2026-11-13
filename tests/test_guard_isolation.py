"""Review of c099faa, group 3 (#20): each publication-safety guard has a test that fails
when that guard alone is disabled (checked by mutating it). Synthetic text; no model call.
"""

import copy

from test_document_extraction import entity, submitted, validate
from test_document_extraction import service as _service
from test_facet_review_fixes import statement_record
from test_publication_safety import projected
from test_scientific_facets import only, quantity, statement

from nasa_fire_ai.ingestion.document_extraction import Output
from nasa_fire_ai.query.native import SemanticGraph, node
from nasa_fire_ai.services.curation import project_package, projected_record_ids

service = _service
STUDY = "Synthetic study"
UNSETTLED = "Oxygen for the next panels: 34 %."


def test_a_configuration_printed_as_future_is_held_with_its_own_reason(service):
    record = statement_record(
        service,
        "The follow-on tests will hold oxygen at 34 % for each panel.",
        "experimental_configuration",
        "ExperimentalCondition",
    )
    assert record["status"] == "UNRESOLVED"
    assert "STATEMENT_PRINTED_AS_NOT_DONE_REQUIRES_REVIEW" in record["reasons"]


def test_a_run_its_support_calls_planned_is_not_an_executed_run(service):
    sentence = "Run B4 is planned for the next campaign."
    p = submitted(service, f"{STUDY}\nII. Methods\n{sentence}\n")
    o = Output().model_dump()
    o["entities"] = [entity(p, "b4", "Run B4", "ExperimentalRun", sentence)]
    (record,) = [
        r
        for r in validate(service, p, o)["records"]
        if r["kind"] == "entities" and r["proposal"]["label"] == "Run B4"
    ]
    assert record["status"] == "REJECTED"
    assert "DOCUMENTARY_OR_PLANNED_IS_NOT_EXECUTED_RUN" in record["reasons"]


def test_a_plan_the_clause_cannot_settle_is_held_through_validation(service):
    record = statement_record(service, UNSETTLED, "planned_activity", "PlannedActivity")
    assert record["status"] == "UNRESOLVED"
    assert "PLAN_READING_UNCERTAIN_REQUIRES_REVIEW" in record["reasons"]


def test_a_proposed_value_the_clause_cannot_settle_is_held_through_validation(service):
    p = submitted(service, f"{STUDY}\nII. Methods\n{UNSETTLED}\n")
    o = Output().model_dump()
    o["entities"] = [entity(p, "inv", STUDY, "Investigation", STUDY)]
    o["quantities"] = [
        quantity(p, UNSETTLED, "inv", "oxygen", "34", "%", "experimental_configuration", "proposed")
    ]
    record = only(validate(service, p, o)["records"], "quantities")
    assert record["status"] == "UNRESOLVED"
    assert "MODALITY_READING_UNCERTAIN_REQUIRES_REVIEW" in record["reasons"]


def test_a_done_reading_is_held_when_an_unsettled_reading_of_the_span_competes(service):
    # The plain reading alone would be accepted (the clause is neither done nor not
    # done); the proposed reading is held as unsettled; together they conflict.
    p = submitted(service, f"{STUDY}\nIII. Results and Discussion\n{UNSETTLED}\n")
    o = Output().model_dump()
    o["entities"] = [entity(p, "inv", STUDY, "Investigation", STUDY)]
    plain = statement(p, UNSETTLED, "experimental_configuration", "ExperimentalCondition", ["inv"])
    o["statements"] = [plain]
    alone = only(validate(service, p, o)["records"], "statements")
    assert alone["status"] == "SOURCE_SUPPORTED", alone["reasons"]
    o["statements"] = [plain, {**plain, "modality": "proposed"}]
    records = [r for r in validate(service, p, o)["records"] if r["kind"] == "statements"]
    done = next(r for r in records if not r["proposal"].get("modality"))
    assert done["status"] == "UNRESOLVED"
    assert "CONFLICTING_MODALITY_READINGS_FOR_SAME_SOURCE_SPAN" in done["reasons"]


def test_two_held_readings_of_one_span_both_stay_in_the_package(service):
    def build(p, o):
        o["entities"] = [entity(p, "inv", STUDY, "Investigation", STUDY)]
        plain = statement(
            p, UNSETTLED, "experimental_configuration", "ExperimentalCondition", ["inv"]
        )
        o["statements"] = [plain, {**plain, "modality": "proposed"}]

    _, _, package = projected(service, UNSETTLED, build)
    kept = {s.get("modality") for s in package["statements"] if s["text"] == UNSETTLED}
    assert kept == {None, "proposed"}


def test_a_prose_statement_matched_by_a_not_done_reading_is_excluded_with_its_modality(service):
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

    records, _, package = projected(service, sentence, build)
    (record,) = [r for r in records if r["kind"] == "statements"]
    assert record["status"] == "SOURCE_SUPPORTED", record["reasons"]
    # The same sentence already in the package as prose: the proposal matches it.
    package["statements"] = [
        {
            "id": "prose-1",
            "text": sentence,
            "class_id": "ExperimentalCondition",
            "epistemic": "experimental_configuration",
            "origin": "prose",
            "evidence_ids": sorted({s["evidence_id"] for s in record["support_spans"]}),
            "scope": [],
        }
    ]
    service.attach_scientific_proposals(package)
    (prose,) = [s for s in package["statements"] if s["id"] == "prose-1"]
    assert prose.get("scientific_proposal_id") == record["id"]
    assert prose["modality"] == "proposed"
    assert prose["included"] is False


def test_a_not_done_value_carried_by_an_older_package_is_never_projected(service):
    sentence = "Panel C3 was burned at 21 % oxygen."

    def build(p, o):
        o["entities"] = [entity(p, "c3", "Panel C3", "Sample", sentence)]
        o["quantities"] = [
            quantity(p, sentence, "c3", "oxygen", "21", "%", "experimental_configuration")
        ]

    _, _, package = projected(service, sentence, build)
    assert package["values"], "the executed value is curated"
    older = copy.deepcopy(package)
    planned = {**copy.deepcopy(older["values"][0]), "modality": "proposed"}
    older["values"] = [planned]
    assert planned["id"] not in projected_record_ids(older)
    store = SemanticGraph(service.property_registry(older))
    project_package(store, older)
    assert node(planned["id"]) not in set(store.graph.subjects())
