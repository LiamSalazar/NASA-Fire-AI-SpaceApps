"""A model-named printed word names a value only in the value's own clause; synthetic, never NASA data."""

import pytest
from test_document_extraction import entity, submitted, support, validate
from test_document_extraction import service as _service

from nasa_fire_ai.ingestion.document_extraction import Output

service = _service

TEXT = (
    "II. Methods\nThe Alpha drum was cleaned with ethanol. "
    "The Alpha drum was rotated at 20.4 RPM before the drop.\n"
)


def quantity_record(service, printed_name, label="rotation rate"):
    p = submitted(service, TEXT)
    o = Output().model_dump()
    o["entities"] = [entity(p, "d", "Alpha drum", "Sample", "The Alpha drum was rotated")]
    o["quantities"] = [
        {
            "subject": "d",
            "label": label,
            "expression": "20.4",
            "unit": "RPM",
            # A reported value: for a configuration the setting verb itself names it
            # (PRINTED_SETTING_VERB_NAMES_VALUE, tests/test_setting_verb_name.py).
            "epistemic": "reported_quantity",
            "support": support(p, TEXT.split("\n")[1]),
            "printed_name": printed_name,
        }
    ]
    (record,) = [r for r in validate(service, p, o)["records"] if r["kind"] == "quantities"]
    return record


def name_rejected(record):
    return any("QUANTITY_NAME_NOT_IN_SOURCE_SUPPORT" in str(r) for r in record["reasons"])


def test_a_printed_word_of_the_value_clause_names_the_value(service):
    record = quantity_record(service, "rotated")
    assert not name_rejected(record)
    assert record["quantity_name_support"]["basis"] == "MODEL_PRINTED_NAME_IN_VALUE_CLAUSE"
    assert record["quantity_name_support"]["printed_name"] == "rotated"


def test_without_a_printed_name_the_unprinted_label_is_still_rejected(service):
    # Metamorphic baseline: the same proposal without printed_name.
    assert name_rejected(quantity_record(service, None))


@pytest.mark.parametrize(
    "printed_name",
    [
        "cleaned",  # printed, but in another sentence's clause
        "spun",  # not printed at all
        "RPM",  # the unit is not a name
        "20.4 RPM",  # the value is not a name
        "at",  # a joining word alone names nothing
    ],
)
def test_a_printed_name_outside_the_value_clause_does_not_name_it(service, printed_name):
    assert name_rejected(quantity_record(service, printed_name))
