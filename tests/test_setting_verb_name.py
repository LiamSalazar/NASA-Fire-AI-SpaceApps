"""A configuration's own printed verb names it; synthetic text, never NASA data."""

import pytest
from test_document_extraction import entity, submitted, support, validate
from test_document_extraction import service as _service

from nasa_fire_ai.ingestion.document_extraction import Output

service = _service


def quantity(service, text, label, expression, unit, epistemic="experimental_configuration"):
    p = submitted(service, "II. Methods\n" + text + "\n")
    o = Output().model_dump()
    o["entities"] = [entity(p, "d", "Alpha drum", "Sample", "Alpha drum")]
    o["quantities"] = [
        {
            "subject": "d",
            "label": label,
            "expression": expression,
            "unit": unit,
            "epistemic": epistemic,
            "support": support(p, text),
        }
    ]
    (record,) = [r for r in validate(service, p, o)["records"] if r["kind"] == "quantities"]
    return record


def named_by_verb(record):
    return (record.get("quantity_name_support") or {}).get("basis") == (
        "PRINTED_SETTING_VERB_NAMES_VALUE"
    )


@pytest.mark.parametrize(
    "text,label,expression,unit",
    [
        (
            "The Alpha drum chamber was rotated at 20.4 RPM before the drop.",
            "chamber rotation rate",
            "20.4",
            "RPM",
        ),
        (
            "For the Alpha drum runs, 20 uL was injected at the port.",
            "injection volume",
            "20",
            "uL",
        ),
    ],
)
def test_the_verb_that_sets_a_value_names_it(service, text, label, expression, unit):
    record = quantity(service, text, label, expression, unit)
    assert named_by_verb(record), record["reasons"]
    assert "QUANTITY_NAME_NOT_IN_SOURCE_SUPPORT" not in str(record["reasons"])


@pytest.mark.parametrize(
    "text,label,expression,unit,epistemic",
    [
        # A qualifier the clause does not print leaves the name unprinted (metamorphic).
        (
            "The Alpha drum chamber was rotated at 20.4 RPM before the drop.",
            "centrifuge rotation rate",
            "20.4",
            "RPM",
            "experimental_configuration",
        ),
        # The unit's dimension is not what the label names.
        (
            "The Alpha drum chamber was rotated at 20.4 cm before the drop.",
            "chamber rotation rate",
            "20.4",
            "cm",
            "experimental_configuration",
        ),
        # A reported measurement needs its printed name.
        (
            "The Alpha drum chamber was rotated at 20.4 RPM before the drop.",
            "chamber rotation rate",
            "20.4",
            "RPM",
            "reported_quantity",
        ),
        # A condition states a criterion, not a setting.
        (
            "If the Alpha drum chamber was rotated at 20.4 RPM the run failed.",
            "chamber rotation rate",
            "20.4",
            "RPM",
            "experimental_configuration",
        ),
        # Times are excluded: "burning at 5 s" is a criterion, not what was set.
        (
            "The Alpha drum flame was burning at 5 s after ignition.",
            "flame burning time",
            "5",
            "s",
            "experimental_configuration",
        ),
        # A verb that is not the label's own word names nothing.
        (
            "The Alpha drum chamber was cleaned at 20.4 RPM before the drop.",
            "chamber rotation rate",
            "20.4",
            "RPM",
            "experimental_configuration",
        ),
    ],
)
def test_without_the_printed_verb_or_dimension_the_name_stays_unprinted(
    service, text, label, expression, unit, epistemic
):
    assert not named_by_verb(quantity(service, text, label, expression, unit, epistemic))


@pytest.mark.parametrize(
    "text,label,expression,unit",
    [
        (
            "The Alpha drum chamber was rotated at 20.4 RPM before the drop.",
            "rotated",
            "20.4",
            "RPM",
        ),
    ],
)
def test_a_label_that_is_the_printed_setting_verb_is_named_by_it(
    service, text, label, expression, unit
):
    # The label is printed, and it is the verb that sets the value: the same rule
    # names it as for a label that only spells the verb out.
    record = quantity(service, text, label, expression, unit)
    assert named_by_verb(record), record["reasons"]
    assert "QUANTITY_SEMANTICS_OR_UNIT_UNRESOLVED" not in record["reasons"]


def test_the_printed_verb_and_its_spelled_out_label_name_the_value_alike(service):
    # Metamorphic: "rotated" and "chamber rotation rate" for the same printed clause.
    text = "The Alpha drum chamber was rotated at 20.4 RPM before the drop."
    printed = quantity(service, text, "rotated", "20.4", "RPM")
    spelled = quantity(service, text, "chamber rotation rate", "20.4", "RPM")
    assert named_by_verb(printed) and named_by_verb(spelled)
    assert printed["status"] == spelled["status"]


@pytest.mark.parametrize(
    "text,label,expression,unit,epistemic",
    [
        # A printed word that is not the setting verb ("cleaned ... at") names nothing.
        (
            "The Alpha drum chamber was cleaned at 20.4 RPM before the drop.",
            "cleaned",
            "20.4",
            "RPM",
            "experimental_configuration",
        ),
        # A label that is the verb cannot vouch for itself: "injected" is no form of
        # a volume noun, so only a spelled-out label ("injection volume") is named.
        (
            "For the Alpha drum runs, 20 uL was injected at the port.",
            "injected",
            "20",
            "uL",
            "experimental_configuration",
        ),
        # A reported measurement is not set by a verb.
        (
            "The Alpha drum chamber was rotated at 20.4 RPM before the drop.",
            "rotated",
            "20.4",
            "RPM",
            "reported_quantity",
        ),
        # A condition states a criterion, not a setting.
        (
            "If the Alpha drum chamber was rotated at 20.4 RPM the run failed.",
            "rotated",
            "20.4",
            "RPM",
            "experimental_configuration",
        ),
    ],
)
def test_a_printed_label_that_is_not_the_setting_verb_is_not_named_by_it(
    service, text, label, expression, unit, epistemic
):
    assert not named_by_verb(quantity(service, text, label, expression, unit, epistemic))


def test_a_printed_noun_sharing_the_verbs_stem_is_not_named_by_the_verb(service):
    # Negative: the rule applies only when the label is the verb itself; "rotation",
    # printed elsewhere in the sentence, is left to the ordinary name syntax.
    text = "The Alpha drum rotation began when the chamber was rotated at 20.4 RPM before the drop."
    assert not named_by_verb(quantity(service, text, "rotation", "20.4", "RPM"))
