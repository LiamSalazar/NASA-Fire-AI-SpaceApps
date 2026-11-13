"""Contract corrections where the model's reading was right and the check rejected it
(review of the variant C rejections). Synthetic text; each test failed before the change.
"""

import pytest
from test_document_extraction import entity, submitted, support, validate
from test_document_extraction import service as _service

from nasa_fire_ai.ingestion import clause_cues
from nasa_fire_ai.ingestion.document_extraction import Output
from nasa_fire_ai.ingestion.scientific_facets import modality_review

service = _service


@pytest.mark.parametrize(
    "text",
    [
        "If the coupon does not ignite within 10 s, then the result is recorded as a pass.",
        "If the probe reads above 80 C before contact, the value is reported as >80 C.",
        "If two panels char through, the series is scored as a failure.",
    ],
)
def test_a_recording_rule_is_a_criterion(text):
    assert clause_cues.criterion(text) == "criterion"


@pytest.mark.parametrize(
    "text",
    [
        # Metamorphic: the same words told as a past event are not a rule.
        "The result was recorded as a pass after the coupon failed to ignite.",
        "The value of 80 C was reported as the peak.",
    ],
)
def test_a_recorded_past_event_is_not_a_criterion(text):
    assert clause_cues.criterion(text) == "not_criterion"


def test_a_present_passive_is_not_read_as_a_past_event():
    # Without a recording frame the rule is unsettled, never a past result.
    text = "If the probe drifts above the band, the reading is discarded."
    assert clause_cues.criterion(text) != "not_criterion"


@pytest.mark.parametrize(
    ("text", "value"),
    [
        # A done step and the value it sought.
        ("Each liner was coated, seeking to achieve a 2 mm layer.", "2"),
        ("The rig seeks to hold the flow at 5 cm/s.", None),
        ("We seek to reach 30 % oxygen in the chamber.", None),
    ],
)
def test_seeking_to_announces_an_intention(text, value):
    assert modality_review(text, "intended", value) == ([], [])


def test_the_purpose_of_a_done_step_is_not_the_intention_for_its_own_value():
    # Metamorphic: the value of the done step itself, before the purpose, stays done.
    text = "Each liner was coated with 2 mm of paste, seeking to reduce soot."
    assert modality_review(text, "intended", "2")[0] == ["MODALITY_NOT_SUPPORTED_BY_SOURCE"]


@pytest.mark.parametrize(
    ("label", "unit", "dimension"),
    [
        ("peak gas temperature", "F", "temperature"),
        ("wall temperature", "C", "temperature"),
        # A bare F or C on a value not named a temperature stays uninterpreted.
        ("coupling capacitance", "F", None),
        ("charge", "C", None),
    ],
)
def test_a_bare_degree_letter_is_a_temperature_only_on_a_temperature(
    service, label, unit, dimension
):
    text = f"II. Methods\nRun A1 was held at a {label} of 275 {unit}.\n"
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [entity(p, "a1", "A1", "ExperimentalRun", "Run A1 was held")]
    o["quantities"] = [
        {
            "subject": "a1",
            "label": label,
            "expression": "275",
            "unit": unit,
            "epistemic": "experimental_configuration",
            "support": support(p, f"Run A1 was held at a {label} of 275 {unit}."),
        }
    ]
    (record,) = [r for r in validate(service, p, o)["records"] if r["kind"] == "quantities"]
    assert (record.get("unit_interpretation") or {}).get("dimension") == dimension


def test_a_recording_rule_typed_a_test_criterion_is_supported():
    from nasa_fire_ai.ingestion.scientific_facets import facet_review

    text = "If the probe reads above 80 C before contact, the value is reported as >80 C."
    item = {"text": text, "epistemic": "test_criterion"}
    assert facet_review("statements", item) == ([], [])
