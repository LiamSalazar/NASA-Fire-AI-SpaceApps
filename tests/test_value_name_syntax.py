"""How the printed text names a value it carries: a possessive before the value that
modifies its name, a bound printed with its comparator, the starting value of a printed
change, and a percentage before a component; never a part's fraction for the whole, never a
bare word of magnitude. Synthetic text; each case failed before the change."""

import pytest
from test_document_extraction import entity, submitted, support, validate
from test_document_extraction import service as _service

from nasa_fire_ai.ingestion.document_extraction import Output

service = _service


def naming(service, sentence, label, expression, unit, subject_label="liner L1"):
    text = f"II. Methods\nThe {subject_label} was tested.\n{sentence}\n"
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [entity(p, "s1", subject_label, "Material", f"The {subject_label} was tested")]
    o["quantities"] = [
        {
            "subject": "s1",
            "label": label,
            "expression": expression,
            "unit": unit,
            "epistemic": "reported_quantity",
            "support": support(p, sentence),
        }
    ]
    (record,) = [r for r in validate(service, p, o)["records"] if r["kind"] == "quantities"]
    return record.get("mapping", {}).get("name_value_syntax")


@pytest.mark.parametrize(
    ("sentence", "label", "expression", "unit", "basis"),
    [
        (
            "The liner L1 kept its 2.5 psid offset.",
            "offset",
            "2.5",
            "psid",
            "PRINTED_VALUE_MODIFIES_ITS_NAME",
        ),
        (
            "For the liner L1 the char span < 8 cm.",
            "char span",
            "< 8",
            "cm",
            "PRINTED_NAME_BOUNDED_BY_VALUE",
        ),
        (
            "For the liner L1, the char span decreased in the second series from 4 cm to 2 cm.",
            "char span",
            "4",
            "cm",
            "PRINTED_NAME_LINKED_TO_VALUE",
        ),
        (
            "The liner L1 is 30% alumina and 70% silica.",
            "alumina",
            "30",
            "%",
            "PRINTED_PERCENT_OF_COMPONENT",
        ),
    ],
)
def test_a_printed_syntax_names_the_value(service, sentence, label, expression, unit, basis):
    assert naming(service, sentence, label, expression, unit) == basis


@pytest.mark.parametrize(
    ("sentence", "label", "expression", "unit"),
    [
        # A part's fraction is not the whole's.
        ("The outer layer of the liner L1 is 90% wool.", "wool", "90", "%"),
        # A bare word of magnitude names no quantity.
        ("The liner L1 was soaked at levels > 100 mg.", "levels", "> 100", "mg"),
    ],
)
def test_a_part_or_a_bare_magnitude_word_is_not_named(service, sentence, label, expression, unit):
    assert naming(service, sentence, label, expression, unit) is None
