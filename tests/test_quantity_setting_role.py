"""A value whose own sentence prints how the test was set; synthetic text, never NASA data."""

import pytest
from test_document_extraction import entity, submitted, support, validate
from test_document_extraction import service as _service

from nasa_fire_ai.ingestion.document_extraction import Output

service = _service


def record_for(service, sentence, label, expression, unit):
    p = submitted(service, "II. Methods\n" + sentence)
    o = Output().model_dump()
    o["entities"] = [
        entity(p, "alpha", "Alpha test series", "ExperimentFamily", "Alpha test series")
    ]
    o["quantities"] = [
        {
            "subject": "alpha",
            "label": label,
            "expression": expression,
            "unit": unit,
            "epistemic": "reported_quantity",
            "support": support(p, sentence),
        }
    ]
    (record,) = [r for r in validate(service, p, o)["records"] if r["kind"] == "quantities"]
    return record


@pytest.mark.parametrize(
    "sentence,expression",
    [
        ("Alpha test series maintained the 4 psid set-point at the 1 pph demand.", "1"),
        ("Alpha test series maintained a 1 pph demand at its 4 psid set-point.", "1"),
        (
            "Alpha test series maintained its 4 psid setpoint with approximately 1 pph demand.",
            "approximately 1",
        ),
    ],
)
def test_a_value_in_a_sentence_that_prints_a_setting_is_a_configuration(
    service, sentence, expression
):
    # Metamorphic: the cue's wording and position do not change the reading.
    record = record_for(service, sentence, "demand", expression, "pph")
    assert record["status"] != "REJECTED"
    assert record["proposal"]["epistemic"] == "experimental_configuration"
    assert record["role_recovery"]["basis"] == "EXPLICIT_SETTING_CUE_IN_VALUE_SENTENCE"


@pytest.mark.parametrize(
    "sentence,label,expression,unit",
    [
        # A requirement, not a setting of this test.
        (
            (
                "Alpha test series exceeded the required cleanliness level of 1 mg/ft2 "
                "specified and maintained by the standard."
            ),
            "cleanliness level",
            "1",
            "mg/ft2",
        ),
        # A value the sentence itself says was set: the model's role error stays
        # visible, as test_epistemic_upgrades_rejected requires.
        ("Alpha test series pressure was set to 20 Pa.", "pressure", "20", "Pa"),
        # A planned value.
        ("Alpha test series will be maintained at a 1 pph demand.", "demand", "1", "pph"),
        # A simulated value.
        (
            "Alpha test series maintained the flow while simulating a 1 pph demand.",
            "demand",
            "1",
            "pph",
        ),
    ],
)
def test_a_requirement_plan_or_simulation_stays_rejected(
    service, sentence, label, expression, unit
):
    record = record_for(service, sentence, label, expression, unit)
    assert record["status"] == "REJECTED"
    assert record["reasons"][0] == "CONFIGURATION_OR_DERIVED_IS_NOT_MEASUREMENT"


def test_a_setting_cue_far_from_the_value_or_an_initial_column_recovers_nothing(service):
    # "Initial" names a table column as often as a setting, and a cue elsewhere
    # in a long passage does not describe this value.
    far = (
        "Alpha test series maintained the chamber purge with dry gas for many minutes "
        "before each and every run was started by the operators, and afterwards the "
        "sample reached an ignition temperature of 400 C."
    )
    record = record_for(service, far, "ignition temperature", "400", "C")
    assert "role_recovery" not in record
    initial = "Alpha test series recorded an initial value and a 400 C ignition temperature."
    record = record_for(service, initial, "ignition temperature", "400", "C")
    assert "role_recovery" not in record


def test_a_measured_value_without_a_setting_cue_keeps_its_role(service):
    record = record_for(service, "Alpha test series showed a 1 pph leak.", "leak", "1", "pph")
    assert "role_recovery" not in record
    assert record["proposal"]["epistemic"] == "reported_quantity"
