"""A condition never carries another value, a printed difference is not an absolute value,
and one entity proposed twice is one entity; synthetic text, never NASA data."""

import pytest
from test_document_extraction import entity, submitted, support, validate
from test_document_extraction import service as _service

from nasa_fire_ai.ingestion.document_extraction import Output

service = _service


def quantities(service, text, entities, items):
    p = submitted(service, "II. Methods\n" + text)
    o = Output().model_dump()
    o["entities"] = [entity(p, *e) for e in entities]
    o["quantities"] = [
        {
            "subject": subject,
            "label": label,
            "expression": expression,
            "unit": unit,
            "epistemic": epistemic,
            "support": support(p, sentence),
        }
        for subject, label, expression, unit, epistemic, sentence in items
    ]
    result = validate(service, p, o)
    return [r for r in result["records"] if r["kind"] == "quantities"], result["entities_by_key"]


@pytest.mark.parametrize(
    "sentence,condition,expression",
    [
        (
            "The 3750 psia supply pressure had a nominal operating pressure of ~200 psia.",
            "3750 psia supply pressure",
            "~200",
        ),
        (
            "For the 4000 psia supply pressure, the nominal operating pressure was ~150 psia.",
            "4000 psia supply pressure",
            "~150",
        ),
    ],
)
def test_a_condition_never_carries_another_value(service, sentence, condition, expression):
    # Metamorphic: other numbers and wording, same reading. The value is kept,
    # never given to the condition.
    records, entities = quantities(
        service,
        sentence,
        [("cond", condition, "PressureCondition", condition)],
        [
            (
                "cond",
                "nominal operating pressure",
                expression,
                "psia",
                "experimental_configuration",
                sentence,
            )
        ],
    )
    (record,) = records
    assert record["status"] != "REJECTED"
    assert record.get("subject") != entities["cond"]["id"]
    assert record["subject_recovery"]["proposed_subject_rejection"] == (
        "QUANTITY_SUBJECT_IS_A_CONDITION"
    )


def test_a_condition_may_carry_its_own_printed_magnitude(service):
    sentence = "The sample was exposed to a 10 cm/s primer flow."
    records, _ = quantities(
        service,
        sentence,
        [("flow", "10 cm/s primer flow", "FlowCondition", "10 cm/s primer flow")],
        [("flow", "primer flow", "10", "cm/s", "experimental_configuration", sentence)],
    )
    (record,) = records
    assert "QUANTITY_SUBJECT_IS_A_CONDITION" not in record["reasons"]


@pytest.mark.parametrize(
    "sentence,expression",
    [
        (
            (
                "Alpha test series was repeated until extinguishments occurred 1% lower in "
                "oxygen concentration than a case where it did not."
            ),
            "1",
        ),
        ("Alpha test series burned at 2% higher in oxygen concentration than Beta.", "2"),
        ("Alpha test series extinguished at a value 3% lower in oxygen concentration.", "3"),
    ],
)
def test_a_printed_difference_is_never_an_absolute_value(service, sentence, expression):
    records, _ = quantities(
        service,
        sentence,
        [("alpha", "Alpha test series", "ExperimentFamily", "Alpha test series")],
        [("alpha", "oxygen concentration", expression, "%", "reported_quantity", sentence)],
    )
    (record,) = records
    assert record["status"] != "SOURCE_SUPPORTED"
    assert "RELATIVE_DIFFERENCE_IS_A_DERIVED_QUANTITY" in record["reasons"]


def test_an_absolute_value_with_a_comparison_elsewhere_is_not_a_difference(service):
    sentence = "Alpha test series was run at 21% oxygen concentration, lower than Beta."
    records, _ = quantities(
        service,
        sentence,
        [("alpha", "Alpha test series", "ExperimentFamily", "Alpha test series")],
        [("alpha", "oxygen concentration", "21", "%", "experimental_configuration", sentence)],
    )
    (record,) = records
    assert "RELATIVE_DIFFERENCE_IS_A_DERIVED_QUANTITY" not in record["reasons"]


def test_one_entity_proposed_twice_is_one_entity_but_a_different_study_is_kept(service):
    text = "Polycarbonate was tested. The polycarbonate samples burned."
    p = submitted(service, "II. Methods\n" + text)
    o = Output().model_dump()
    o["entities"] = [
        entity(p, "a", "Polycarbonate", "Material", "Polycarbonate was tested."),
        entity(p, "b", "polycarbonate", "Material", "The polycarbonate samples burned."),
    ]
    records = [r for r in validate(service, p, o)["records"] if r["kind"] == "entities"]
    supported = [r for r in records if r["status"] == "SOURCE_SUPPORTED"]
    assert len({r["entity_id"] for r in supported}) == 1
    assert sum(not r.get("duplicate_of") for r in supported) == 1
    # Negative: the same name with another study stays a separate proposal.
    o["entities"][1]["study"] = "cited"
    records = [r for r in validate(service, p, o)["records"] if r["kind"] == "entities"]
    supported = [r for r in records if r["status"] == "SOURCE_SUPPORTED"]
    assert sum(not r.get("duplicate_of") for r in supported) == len(supported)
