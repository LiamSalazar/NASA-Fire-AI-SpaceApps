"""A set-up or planned step is what was done, not what was observed; synthetic text."""

import pytest

from nasa_fire_ai.ingestion.statement_integrity import procedure_without_outcome


@pytest.mark.parametrize(
    "text",
    [
        "The valve impacts were performed manually to control the sequence.",
        "Before the series, the valve was set up with a nitrogen supply.",
        "The first series was to perform 40 dry impacts.",
        "The port was injected with 20 uL of oil.",
    ],
)
def test_a_set_up_or_planned_step_is_a_procedure(text):
    assert procedure_without_outcome(text)


@pytest.mark.parametrize(
    "text",
    [
        "The valve performed nominally during the entire series.",
        "The valve was set up with nitrogen and no ignition occurred.",
        "Impacts were performed and the valve passed every functional test.",
    ],
)
def test_a_step_with_its_outcome_is_an_observation(text):
    # Metamorphic: the same steps with a printed outcome report what happened.
    assert not procedure_without_outcome(text)


@pytest.mark.parametrize(
    "text",
    [
        # What a step was for is not what happened.
        "The chiller was adjusted to reduce the valve body temperature for the last runs.",
        "Five impacts were then executed with the oil load in the inlet port.",
    ],
)
def test_a_step_with_only_its_purpose_is_a_procedure(text):
    assert procedure_without_outcome(text)


@pytest.mark.parametrize(
    "text",
    [
        # Metamorphic: "to" before a determiner or an outcome word is not a purpose.
        "The sample was heated to the point of ignition.",
        "Samples were exposed to flame and burned completely.",
        "The pressure was adjusted to 30 kPa and the flame extinguished.",
    ],
)
def test_an_outcome_after_to_is_still_an_outcome(text):
    assert not procedure_without_outcome(text)


@pytest.mark.parametrize(
    "text",
    [
        # A judgement is not a step, so its "to" is not a purpose.
        "The variation was considered to have a minimal impact on the results.",
        # Metamorphic regressions found by replay: a run count with a measured value,
        # and a mechanism, are not procedures.
        "Sixty test runs were executed with typical impact times of ~360 msec.",
        "In this configuration the sample was directly heated by the igniter flame.",
    ],
)
def test_judgements_measurements_and_mechanisms_are_not_procedures(text):
    assert not procedure_without_outcome(text)


def test_a_pointer_to_a_figure_is_not_an_outcome():
    step = "As shown in Figure 12, the chiller was adjusted to reduce the body temperature."
    assert procedure_without_outcome(step)
    # Metamorphic: the same pointer before a reported outcome still reports it.
    assert not procedure_without_outcome(
        "As shown in Figure 12, the chiller was adjusted and the coupon ignited."
    )
