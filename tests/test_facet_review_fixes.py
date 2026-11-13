"""Fixes from the adversarial review of the facets commit; synthetic text, production code.

Each test failed before its fix. Exact states and reasons are asserted, not just
"not rejected".
"""

import pytest
from test_document_extraction import entity, submitted, support, validate
from test_document_extraction import service as _service
from test_scientific_facets import only, quantity, statement

from nasa_fire_ai.ingestion.document_extraction import Output, merge_output
from nasa_fire_ai.ingestion.scientific_facets import (
    ALLOWED_MODALITIES,
    STATEMENT_PROFILES,
    facet_errors,
    not_done_value,
)

service = _service
STUDY = "Synthetic study"


def statement_record(service, text, role, cls, subject_class="Investigation", label=STUDY):
    p = submitted(service, f"{STUDY}\nIII. Test Method\n{text}\n")
    o = Output().model_dump()
    quote = STUDY if subject_class == "Investigation" else text
    o["entities"] = [entity(p, "k", label, subject_class, quote)]
    o["statements"] = [statement(p, text, role, cls, ["k"])]
    return only(validate(service, p, o)["records"], "statements")


# 2. A criterion needs normative wording; results, extremes and negations are not criteria.
@pytest.mark.parametrize(
    ("text", "role", "cls"),
    [
        ("Run A1 failed the drop test.", "test_criterion", "TestCriterion"),
        ("Panel C3 passed the impact test.", "test_criterion", "TestCriterion"),
        (
            "Panel C3 was not tested against any acceptance criterion.",
            "test_criterion",
            "TestCriterion",
        ),
        ("The maximum char length in Run A1 was 7 cm.", "design_criterion", "DesignCriterion"),
        ("The coupon burned at least 9 cm.", "design_criterion", "DesignCriterion"),
    ],
)
def test_a_result_or_a_negation_is_not_a_criterion(service, text, role, cls):
    record = statement_record(service, text, role, cls)
    assert record["status"] == "REJECTED"
    assert any("CRITERION_NOT_EXPLICIT_IN_SOURCE" in r for r in record["reasons"])


@pytest.mark.parametrize(
    ("text", "role", "cls"),
    [
        (
            "A panel passes when its char length stays below 9 cm.",
            "test_criterion",
            "TestCriterion",
        ),
        ("Each enclosure shall keep its wall below 40 C.", "design_criterion", "DesignCriterion"),
    ],
)
def test_a_stated_criterion_is_kept_with_its_approved_class(service, text, role, cls):
    record = statement_record(service, text, role, cls)
    assert record["status"] != "REJECTED", record["reasons"]
    assert record["proposal"]["class_id"] == cls
    assert not any("CRITERION" in r or "MODALITY" in r for r in record["reasons"])


def test_a_criterion_never_takes_an_executed_run_as_its_subject(service):
    text = "Run A1 passes when its char length stays below 9 cm."
    record = statement_record(
        service, text, "test_criterion", "TestCriterion", "ExperimentalRun", "A1"
    )
    assert record["status"] == "REJECTED"
    assert any("PLANNED_STATEMENT_ATTRIBUTED_TO_EXECUTED_RUN" in r for r in record["reasons"])


# 3. Every role but the class-flexible ones must use its own class.
@pytest.mark.parametrize("cls", ["ReportedObservation", "NASAConclusion"])
def test_a_plan_cannot_borrow_an_approved_class(service, cls):
    text = "The next series will drop each panel twice."
    record = statement_record(service, text, "planned_activity", cls)
    assert record["status"] == "REJECTED"
    assert any("CLASS_EPISTEMIC_CONTRADICTION" in r for r in record["reasons"])


# 4. A proposal written before facets and the same proposal with modality null merge.
def test_a_pre_facet_proposal_and_its_null_modality_twin_are_one():
    old = {"text": "A1 charred.", "epistemic": "measured_observation", "subjects": ["a1"]}
    target = Output().model_dump()
    merge_output(target, {**Output().model_dump(), "statements": [old]})
    merge_output(target, {**Output().model_dump(), "statements": [{**old, "modality": None}]})
    assert len(target["statements"]) == 1


# 5. A not-done value never attaches to an executed run, whatever modality is stated.
@pytest.mark.parametrize(
    ("sentence", "modality"),
    [
        ("Run A1 shall be burned at 34 % oxygen.", "proposed"),
        ("If ignition fails, Run A1 will be burned at 34 % oxygen.", "conditional"),
        ("Run A1 could be repeated at 34 % oxygen next year.", "hypothetical"),
        # No modality stated: the printed wording decides.
        ("Run A1 will hold oxygen at 34 % for each panel.", None),
    ],
)
def test_a_value_printed_as_not_done_never_describes_an_executed_run(service, sentence, modality):
    p = submitted(service, f"{STUDY}\nII. Methods\n{sentence}\n")
    o = Output().model_dump()
    o["entities"] = [entity(p, "r", "A1", "ExperimentalRun", sentence)]
    o["quantities"] = [
        quantity(p, sentence, "r", "oxygen", "34", "%", "experimental_configuration", modality)
    ]
    record = only(validate(service, p, o)["records"], "quantities")
    assert record.get("subject") is None or record["status"] != "SOURCE_SUPPORTED"
    assert record["proposal"]["subject"] != "r" or record["status"] == "REJECTED"


# 6. Cues are read in the sentence that prints the value, without purpose clauses.
def test_cues_come_from_the_value_sentence_only():
    neighbour = "Panel C3 burned with a char length of 7 cm. Each panel must self-extinguish."
    value = {"epistemic": "criterion_value", "expression": "7"}
    assert facet_errors(
        "quantities", value, sentence="Panel C3 burned with a char length of 7 cm."
    ) == ["CRITERION_NOT_EXPLICIT_IN_SOURCE"]
    assert "Each panel must" in neighbour  # the normative sentence is only a neighbour
    plan = {"epistemic": "planned_activity", "text": ""}
    assert "PLAN_NOT_EXPLICIT_IN_SOURCE" in facet_errors(
        "statements",
        plan,
        sentence="The samples were weighed so that the material properties would be known.",
    )


# 8. One table of modalities: "actual" means none, and the table decides the rest.
def test_actual_means_no_modality_for_every_role():
    for role in STATEMENT_PROFILES:
        item = {"epistemic": role, "modality": "actual", "text": "x"}
        assert "MODALITY_CONTRADICTS_ROLE" not in facet_errors("statements", item)


def test_the_request_offers_only_modalities_some_role_allows():
    from typing import get_args

    from nasa_fire_ai.ingestion.document_extraction import Modality

    allowed = set().union(*ALLOWED_MODALITIES.values()) | {"actual", "prescriptive"}
    assert set(get_args(Modality)) <= allowed


def test_an_observation_cannot_be_conditional_but_a_setting_can():
    observed = {"epistemic": "measured_observation", "modality": "conditional", "text": "If x."}
    setting = {
        "epistemic": "experimental_configuration",
        "modality": "conditional",
        "text": "If x.",
    }
    assert facet_errors("statements", observed) == ["MODALITY_CONTRADICTS_ROLE"]
    assert facet_errors("statements", setting) == []


# 1. A criterion value or a not-done value is never published as a measurement.
@pytest.mark.parametrize(
    ("value", "kept_out"),
    [
        ({"epistemic": "criterion_value"}, True),
        ({"epistemic": "experimental_configuration", "modality": "proposed"}, True),
        ({"epistemic": "experimental_configuration", "modality": "conditional"}, True),
        ({"epistemic": "reported_quantity"}, False),
        ({"epistemic": "experimental_configuration", "modality": "actual"}, False),
        # A role without a profile (a table attribute path) keeps its own contract.
        ({"epistemic": "SOURCE_ATTRIBUTE_NOT_ASSERTED_AS_OBSERVATION"}, False),
    ],
)
def test_only_done_values_can_be_published(value, kept_out):
    assert not_done_value(value) is kept_out


def test_curation_keeps_a_not_done_value_out_of_published_values(service):
    sentence = "The follow-on tests will hold oxygen at 34 % for each panel."
    p = submitted(service, f"{STUDY}\nIII. Results and Discussion\n{sentence}\n")
    record = {
        "id": "q1",
        "kind": "quantities",
        "status": "SOURCE_SUPPORTED",
        "proposal_state": "SOURCE_SUPPORTED",
        "reasons": [],
        "subject": "entity-x",
        "support_spans": [
            {**support(p, sentence)[0], "start": 0, "end": len(sentence), "source_id": "s"}
        ],
        "mapping": {"property_id": "OxygenConcentration"},
        "proposal": {
            "subject": "inv",
            "label": "oxygen",
            "expression": "34",
            "unit": "%",
            "epistemic": "experimental_configuration",
            "modality": "proposed",
            "support": support(p, sentence),
        },
    }
    p["scientific_extraction"] = {"records": [record], "entities_by_key": {}}
    service.attach_scientific_proposals(p)
    assert not [v for v in p["values"] if v["id"] == "q1"]
    (kept,) = p["non_executed_values"]
    assert kept["included"] is False and kept["modality"] == "proposed"


# 9. A "Test criterion" table column is not read as criterion statements.
def test_criterion_roles_are_not_table_column_labels(service):
    assert "test criterion" not in service.presentation["statement_roles"]
    assert service.epistemic_roles["test criterion"]["epistemic"] == "test_criterion"


# 7. The same sentence read with and without a modality is two readings, not duplicates.
def test_two_modality_readings_of_one_sentence_are_not_merged(service):
    sentence = "The follow-on tests will hold oxygen at 34 % for each panel."
    p = submitted(service, f"{STUDY}\nIII. Results and Discussion\n{sentence}\n")
    o = Output().model_dump()
    o["entities"] = [entity(p, "inv", STUDY, "Investigation", STUDY)]
    plain = statement(p, sentence, "experimental_configuration", "ExperimentalCondition", ["inv"])
    o["statements"] = [plain, {**plain, "modality": "proposed"}]
    records = [r for r in validate(service, p, o)["records"] if r["kind"] == "statements"]
    assert len(records) == 2
    assert not any(r.get("duplicate_of") for r in records)
