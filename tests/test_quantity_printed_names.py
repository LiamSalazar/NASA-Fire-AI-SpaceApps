"""A quantity named by the words printed after its value; synthetic text, never NASA data."""

import copy

import pytest
from test_document_extraction import entity, submitted, support, validate
from test_document_extraction import service as _service

from nasa_fire_ai.ingestion.document_extraction import Output, printed_value_name

service = _service


def quantity(p, sentence, label, expression, unit, epistemic="experimental_configuration"):
    return {
        "subject": "alpha",
        "label": label,
        "expression": expression,
        "unit": unit,
        "epistemic": epistemic,
        "support": support(p, sentence),
    }


def records_for(service, sentence, *quantities):
    p = submitted(service, "II. Methods\n" + sentence)
    o = Output().model_dump()
    o["entities"] = [
        entity(p, "alpha", "Alpha test series", "ExperimentFamily", "Alpha test series")
    ]
    o["quantities"] = [quantity(p, sentence, *q) for q in quantities]
    return [r for r in validate(service, p, o)["records"] if r["kind"] == "quantities"]


@pytest.mark.parametrize(
    "sentence,expression,unit",
    [
        ("Alpha test series was run in a 1.4 m3 (50 ft3) chamber.", "1.4", "m3"),
        ("Alpha test series was run in a 1.4 m3 chamber.", "1.4", "m3"),
        ("Alpha test series was run in a chamber that is 299 l in volume.", "299", "l"),
    ],
)
def test_a_value_named_by_the_word_printed_after_it(service, sentence, expression, unit):
    # Metamorphic: with or without the author equivalent, and the "in <name>" form,
    # give the same reading; the label stays the model's, the name is printed.
    (record,) = records_for(service, sentence, ("chamber volume", expression, unit))
    assert record["status"] == "SOURCE_SUPPORTED"
    support_basis = record["quantity_name_support"]
    assert support_basis["basis"] == "PRINTED_NAME_AFTER_VALUE"
    assert support_basis["printed_name"] in {"chamber", "volume"}
    assert record["proposal"]["label"] == "chamber volume"


def test_a_label_word_neither_printed_nor_of_the_units_dimension_is_not_named(service):
    sentence = "Alpha test series was run in a 1.4 m3 (50 ft3) chamber."
    (record,) = records_for(service, sentence, ("chamber pressure", "1.4", "m3"))
    assert record["status"] != "SOURCE_SUPPORTED"


def test_one_value_of_a_printed_pair_is_never_given_a_dimension(service):
    sentence = "Alpha test series used 5.2 cm by 14.0 cm samples."
    for label, expression in (("sample width", "5.2"), ("sample length", "14.0")):
        (record,) = records_for(service, sentence, (label, expression, "cm"))
        assert record["status"] != "SOURCE_SUPPORTED"


def test_a_percentage_before_a_constituent_is_not_named_this_way():
    # "made up of 90% Copper" is a composition of something the words do not
    # settle; only a configuration value ("tested at 48% O2") is named this way.
    spans = [{"quote": "The bronze component of Alpha is made up of 90% Copper and 8% Tin."}]
    assert printed_value_name("Copper percentage", "90", "%", spans, "reported_quantity") is None
    tested = [{"quote": "Alpha coupons were tested at 48% O2 and 8.2 psia."}]
    named = printed_value_name("O2 concentration", "48", "%", tested, "experimental_configuration")
    assert named["printed_name"] == "o2"
    assert named["label_words_from_unit_dimension"] == ["concentration"]


def test_one_printed_value_proposed_under_two_names_is_one_quantity(service):
    sentence = "Alpha test series was tested at 37% O2 and 8.2 psia."
    records = records_for(service, sentence, ("O2", "37", "%"), ("oxygen concentration", "37", "%"))
    # The printed "tested at" line may add its own candidate for the same value.
    supported = [
        r
        for r in records
        if r["status"] == "SOURCE_SUPPORTED" and r["proposal"]["expression"] == "37"
    ]
    assert len(supported) >= 2
    assert sum(not r.get("duplicate_of") for r in supported) == 1


def test_two_values_printed_apart_stay_two_quantities(service):
    # Negative for the merge: the same number printed twice is two values.
    sentence = (
        "Alpha test series was tested at 37% O2. Later Alpha test series was tested at 37% O2."
    )
    p = submitted(service, "II. Methods\n" + sentence)
    o = Output().model_dump()
    o["entities"] = [
        entity(p, "alpha", "Alpha test series", "ExperimentFamily", "Alpha test series")
    ]
    one = quantity(p, "Alpha test series was tested at 37% O2.", "O2", "37", "%")
    two = copy.deepcopy(one)
    two["support"] = support(p, "Later Alpha test series was tested at 37% O2.")
    o["quantities"] = [one, two]
    records = [r for r in validate(service, p, o)["records"] if r["kind"] == "quantities"]
    supported = [r for r in records if r["status"] == "SOURCE_SUPPORTED"]
    assert sum(not r.get("duplicate_of") for r in supported) == len(supported)
