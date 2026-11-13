"""SCIENCE_INSTRUMENT_OBSERVATION: how a run was watched is method, not an observation (invented text)."""

import pytest

from nasa_fire_ai.ingestion.statement_integrity import instrument_setup


@pytest.mark.parametrize(
    "text",
    [
        "Each tray was filmed using two cameras.",
        "The tray was filmed using a high-speed camera.",
        "Each run was recorded by means of a thermocouple array.",
        "The panels were monitored via two infrared sensors.",
    ],
)
def test_a_watching_set_up_is_a_procedure(text):
    assert instrument_setup(text)


@pytest.mark.parametrize(
    "text",
    [
        "Smoldering was observed with a camera.",
        "The coupon was observed to ignite with a bright flame.",
        "It was observed with a camera that the foam charred.",
        "Ignition was recorded by a thermocouple.",
        "The coupon was observed burning with a camera.",
        "Both coupons were observed.",
        "The coupons were mounted with clamps.",
    ],
)
def test_a_reported_outcome_is_not_a_set_up(text):
    assert not instrument_setup(text)


def test_the_check_only_holds(monkeypatch):
    from nasa_fire_ai.ingestion import statement_integrity as si

    monkeypatch.delenv("SCIENCE_INSTRUMENT_OBSERVATION", raising=False)
    assert si.instrument_observation_enabled()
    monkeypatch.setenv("SCIENCE_INSTRUMENT_OBSERVATION", "0")
    assert not si.instrument_observation_enabled()
