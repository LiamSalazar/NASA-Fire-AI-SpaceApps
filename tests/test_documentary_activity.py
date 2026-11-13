"""SCIENCE_DOCUMENTARY_ACTIVITY: a documentary statement is not an agent's activity under way (invented text)."""

import pytest

from nasa_fire_ai.ingestion.statement_integrity import (
    HOLD_CHECKS,
    documentary_activity,
    documentary_activity_enabled,
)


@pytest.mark.parametrize(
    "text",
    [
        "The panel crew has been procuring flame-retardant cloth for the next series.",
        "The group is steadily building a new mounting scheme.",
        "Engineers were testing alternative holders during the winter.",
        "The vendor has been quietly improving the coating.",
    ],
)
def test_an_activity_under_way_is_held(text):
    assert documentary_activity(text)


@pytest.mark.parametrize(
    "text",
    [
        "Table 2 lists the panel thicknesses.",
        "Figure 3 is showing the char depth against time.",
        "This report describes the foam tests.",
        "The coatings were selected from the vendor catalogue.",
        "The following is the list of panels.",
        "The next section is interesting for coating choice.",
    ],
)
def test_a_pointer_or_a_plain_description_is_not_held(text):
    assert not documentary_activity(text)


def test_the_check_is_on_by_default_and_bound_to_the_role(monkeypatch):
    from nasa_fire_ai.ingestion.scientific_facets import ROLES

    monkeypatch.delenv("SCIENCE_DOCUMENTARY_ACTIVITY", raising=False)
    assert documentary_activity_enabled()
    monkeypatch.setenv("SCIENCE_DOCUMENTARY_ACTIVITY", "0")
    assert not documentary_activity_enabled()
    assert "documentary_activity" in ROLES["documentary_context"].holds
    assert "documentary_activity" in HOLD_CHECKS


def test_a_sentence_wrapped_over_lines_is_read_as_one():
    assert documentary_activity("The cloth crew is steadily \nbuilding the three-step plan")
