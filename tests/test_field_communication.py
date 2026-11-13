"""A correctly verified value must communicate its own field and original record."""

from types import SimpleNamespace

import pytest

from nasa_fire_ai.services.structured_alignment import field_is_communicated, record_anchor_allowed


@pytest.mark.parametrize(
    "text,evidence,expected",
    [
        ("The fuel bottle entry is 40% CH4.", "row-a", False),
        ("The fuel concentration is 40%.", "row-b", False),
        ("The fuel concentration is 40%.", "row-a", True),
        ("A relevant source was cited.", "row-a", False),
    ],
)
def test_same_numeric_value_does_not_merge_fields_or_records(text, evidence, expected):
    definitions = {
        "bottle": SimpleNamespace(aliases=["fuel bottle"]),
        "concentration": SimpleNamespace(aliases=["fuel concentration", "Fuel Conc"]),
    }
    fact = {
        "text": "Original source row lists Fuel Conc as 40%.",
        "field_text": "The record lists Fuel Conc as 40%.",
        "property_id": "concentration",
        "primary_evidence_ids": ["row-a"],
    }
    record = {"property_id": "concentration", "qualifiers": {"source_header": "Fuel Conc"}}
    assert (
        field_is_communicated(
            fact,
            record,
            [{"text": text, "evidence_ids": [evidence]}],
            definitions,
            SimpleNamespace(check=lambda p, h: {"supported": True}),
        )
        is expected
    )


def test_equal_before_after_values_still_require_the_correct_phase():
    fact = {
        "text": "The source lists initial pressure as 4 Pa.",
        "field_text": "The record lists initial pressure as 4 Pa.",
        "property_id": "pressure",
        "primary_evidence_ids": ["row"],
    }
    record = {
        "property_id": "pressure",
        "qualifiers": {"source_header": "Pressure before", "context": "initial"},
    }
    definitions = {"pressure": SimpleNamespace(aliases=["pressure"])}
    model = SimpleNamespace(check=lambda p, h: {"supported": True})
    for text, expected in [
        ("Pressure after was 4 Pa.", False),
        ("Pressure before was 4 Pa.", True),
    ]:
        assert (
            field_is_communicated(
                fact, record, [{"text": text, "evidence_ids": ["row"]}], definitions, model
            )
            is expected
        )


@pytest.mark.parametrize("definition_source,expected", [("table-a", True), ("table-b", False)])
def test_field_definitions_stay_with_their_original_source_table(definition_source, expected):
    store = SimpleNamespace(
        payload=lambda rid: {
            "subject": "definition-row",
            "qualifiers": {"scientific_role": "source_field_definition"},
        },
        sources=lambda subject: (
            [definition_source] if subject in {"definition", "definition-row"} else ["table-a"]
        ),
    )
    assert (
        record_anchor_allowed(
            {"structured_record_id": "definition"}, SimpleNamespace(store=store), {"record"}
        )
        is expected
    )
