"""Modal verbs read by the conventions of ISO/IEC/IEEE 29148 and the NASA Systems Engineering
Handbook: a permission ("may/can be used", "is permitted") is guidance; "will" states an
intent, so a planned clause supports modality intended. Synthetic text."""

import pytest

from nasa_fire_ai.ingestion.document_extraction import role_errors
from nasa_fire_ai.ingestion.scientific_facets import modality_review


@pytest.mark.parametrize(
    "text",
    [
        "A steel clamp can be used to hold the coupon edge.",
        "Thicker foil may be used when the rig runs hot.",
        "A second igniter is permitted for thick coupons.",
    ],
)
def test_a_permission_is_guidance(text, monkeypatch):
    monkeypatch.setenv("SCIENCE_MODAL_29148", "0")
    assert "GUIDANCE_NOT_EXPLICIT_IN_SOURCE" not in role_errors(
        {"text": text, "epistemic": "guidance"}
    )


@pytest.mark.parametrize(
    "text",
    [
        "Thicker foil may be used when the rig runs hot.",
        "A second igniter is permitted for thick coupons.",
    ],
)
def test_a_permission_is_guidance_with_the_modal_reading_on(text, monkeypatch):
    monkeypatch.setenv("SCIENCE_MODAL_29148", "1")
    assert "GUIDANCE_NOT_EXPLICIT_IN_SOURCE" not in role_errors(
        {"text": text, "epistemic": "guidance"}
    )


def test_can_is_a_capability_not_a_permission_with_the_modal_reading_on(monkeypatch):
    # ISO/IEC Directives Part 2, clause 7: "can" states possibility or capability.
    text = "A steel clamp can be used to hold the coupon edge."
    monkeypatch.setenv("SCIENCE_MODAL_29148", "1")
    assert "GUIDANCE_NOT_EXPLICIT_IN_SOURCE" in role_errors({"text": text, "epistemic": "guidance"})
    monkeypatch.setenv("SCIENCE_MODAL_29148", "0")
    assert "GUIDANCE_NOT_EXPLICIT_IN_SOURCE" not in role_errors(
        {"text": text, "epistemic": "guidance"}
    )


def test_a_done_use_is_not_guidance():
    # Metamorphic: the same words told as a done step carry no permission.
    errors = role_errors(
        {"text": "A steel clamp was used to hold the coupon edge.", "epistemic": "guidance"}
    )
    assert "GUIDANCE_NOT_EXPLICIT_IN_SOURCE" in errors


@pytest.mark.parametrize(
    "text",
    ["The coupons will be retested at the drop tower.", "Flight testing is planned for next year."],
)
def test_a_planned_clause_supports_an_intention(text):
    assert modality_review(text, "intended") == ([], [])


def test_a_done_clause_is_not_an_intention():
    assert modality_review("The coupons were retested at the drop tower.", "intended")[0]
