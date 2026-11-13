"""SCIENCE_LABEL_BINDING (off by default): a value is bound to the proposed subject whose own
printed label prints it (expression and unit), for any entity class, when no other entity
named in the clause prints it in its label and the clause prints it nowhere else. The value's
normalized expression and unit stay apart from the label; a value is never handed between two
subjects named in one clause. Invented text only (B8).

Positive, negative and metamorphic cases run with the flag on; the flags-off cases pin the
current local binding byte for byte.
"""

import json

import pytest
from test_document_extraction import entity, submitted, validate
from test_document_extraction import service as _service
from test_scientific_facets import only, quantity

from nasa_fire_ai.ingestion.document_extraction import Output

service = _service
RIGS = ["Rig Quill (12 m/s)", "Rig Brook"]
FLAG = "SCIENCE_LABEL_BINDING"
BASIS = "VALUE_PRINTED_INSIDE_SUBJECT_LABEL"
UNBOUND = "QUANTITY_LOCAL_SUBJECT_BINDING_UNRESOLVED"


def flag(monkeypatch, value):
    if value is None:
        monkeypatch.delenv(FLAG, raising=False)
    else:
        monkeypatch.setenv(FLAG, value)


def run(
    service, text, labels, cls, subject, expression, unit, name, role="experimental_configuration"
):
    """Validate one value proposed for ``subject`` (an index into ``labels``)."""
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [
        entity(p, "study", "Synthetic Chamber Survey", "Investigation", "Synthetic Chamber Survey"),
        *[entity(p, f"e{i}", label, cls, label) for i, label in enumerate(labels)],
    ]
    o["quantities"] = [
        quantity(p, text.split("\n")[-1], f"e{subject}", name, expression, unit, role)
    ]
    result = validate(service, p, o)
    record = only(result["records"], "quantities")
    ids = [result["entities_by_key"][f"e{i}"]["id"] for i in range(len(labels))]
    return record, ids


CONDITIONS = (
    "Synthetic Chamber Survey\n"
    "The Rig Quill (12 m/s) and the Rig Brook set the fan speed during the ignition trials."
)
FAMILIES = (
    "Synthetic Chamber Survey\n"
    "The Series 40 kPa runs and the Series 65 kPa runs set the chamber pressure before ignition."
)


# Positive, flag on.


def test_a_condition_keeps_the_value_printed_inside_its_own_label(service, monkeypatch):
    flag(monkeypatch, "1")
    record, ids = run(
        service,
        CONDITIONS,
        RIGS,
        "ExperimentalCondition",
        0,
        "12",
        "m/s",
        "fan speed",
    )
    assert UNBOUND not in record["reasons"]
    assert record["subject"] == ids[0]
    assert record["label_binding"]["basis"] == BASIS
    # Normalized fields stay apart from the printed label.
    assert record["label_binding"]["label"] == "Rig Quill (12 m/s)"
    assert (record["proposal"]["expression"], record["proposal"]["unit"]) == ("12", "m/s")


def test_a_group_keeps_the_value_printed_inside_its_own_label(service, monkeypatch):
    flag(monkeypatch, "1")
    record, ids = run(
        service,
        FAMILIES,
        ["Series 40 kPa", "Series 65 kPa"],
        "ExperimentFamily",
        1,
        "65",
        "kPa",
        "chamber pressure",
    )
    assert UNBOUND not in record["reasons"]
    assert record["subject"] == ids[1]
    assert record["label_binding"]["basis"] == BASIS


# Negative, flag on.


def test_a_value_in_the_competitor_label_is_never_transferred(service, monkeypatch):
    flag(monkeypatch, "1")
    record, ids = run(
        service,
        FAMILIES,
        ["Series 40 kPa", "Series 65 kPa"],
        "ExperimentFamily",
        1,
        "40",
        "kPa",
        "chamber pressure",
    )
    assert record["subject"] != ids[1]
    assert record["subject"] != ids[0]  # never handed to the label that prints it either
    assert "label_binding" not in record


def test_a_value_printed_in_both_labels_binds_to_neither(service, monkeypatch):
    flag(monkeypatch, "1")
    text = (
        "Synthetic Chamber Survey\n"
        "The Series A 40 kPa dry runs and the Series B 40 kPa humid runs set the chamber pressure."
    )
    record, ids = run(
        service,
        text,
        ["Series A 40 kPa dry", "Series B 40 kPa humid"],
        "ExperimentFamily",
        0,
        "40",
        "kPa",
        "chamber pressure",
    )
    assert record["subject"] not in ids
    assert "label_binding" not in record


def test_a_value_also_printed_outside_the_label_binds_to_neither(service, monkeypatch):
    flag(monkeypatch, "1")
    text = (
        "Synthetic Chamber Survey\n"
        "The Series 40 kPa runs and the Series 65 kPa runs set the vent pressure at 40 kPa."
    )
    record, _ = run(
        service,
        text,
        ["Series 40 kPa", "Series 65 kPa"],
        "ExperimentFamily",
        0,
        "40",
        "kPa",
        "vent pressure",
    )
    assert "label_binding" not in record


def test_a_label_number_without_the_unit_does_not_print_the_value(service, monkeypatch):
    flag(monkeypatch, "1")
    text = "Synthetic Chamber Survey\nSeries 40 and Series 65 set the chamber pressure at 40 kPa."
    record, _ = run(
        service,
        text,
        ["Series 40", "Series 65"],
        "ExperimentFamily",
        0,
        "40",
        "kPa",
        "chamber pressure",
    )
    assert "label_binding" not in record


# Metamorphic, flag on.


@pytest.mark.parametrize(
    "text,labels",
    [
        (FAMILIES, ["Series 40 kPa", "Series 65 kPa"]),
        (
            (
                "Synthetic Chamber Survey\n"
                "The Batch 65 kPa runs and the Batch 40 kPa runs set the chamber pressure before ignition."
            ),
            ["Batch 65 kPa", "Batch 40 kPa"],
        ),
    ],
)
def test_renaming_and_reordering_labels_keeps_the_binding_with_its_label(
    service, monkeypatch, text, labels
):
    flag(monkeypatch, "1")
    owner = next(i for i, label in enumerate(labels) if "65 kPa" in label)
    record, ids = run(
        service, text, labels, "ExperimentFamily", owner, "65", "kPa", "chamber pressure"
    )
    assert record["subject"] == ids[owner]
    assert record["label_binding"]["basis"] == BASIS
    other = 1 - owner
    record, ids = run(
        service, text, labels, "ExperimentFamily", other, "65", "kPa", "chamber pressure"
    )
    assert record["subject"] != ids[other]
    assert "label_binding" not in record


def test_the_legacy_sample_binding_is_unchanged_by_the_flag(service, monkeypatch):
    text = "Two coupons: Strip 5 cm wide x 30 cm long and Rod 4 mm diameter were burned."
    labels = ["Strip 5 cm wide x 30 cm long", "Rod 4 mm diameter"]
    flag(monkeypatch, None)
    off, _ = run(service, text, labels, "Sample", 0, "5", "cm", "width")
    flag(monkeypatch, "1")
    on, _ = run(service, text, labels, "Sample", 0, "5", "cm", "width")
    assert off["status"] == "SOURCE_SUPPORTED"
    assert json.dumps(off, sort_keys=True) == json.dumps(on, sort_keys=True)


# Flags off: the current local binding, byte for byte.


def test_flags_off_a_condition_value_stays_unbound(service, monkeypatch):
    flag(monkeypatch, None)
    record, _ = run(
        service,
        CONDITIONS,
        RIGS,
        "ExperimentalCondition",
        0,
        "12",
        "m/s",
        "fan speed",
    )
    assert UNBOUND in record["reasons"]
    assert "label_binding" not in record


@pytest.mark.parametrize(
    "text,labels,cls,subject,expression,unit,name",
    [
        (
            CONDITIONS,
            RIGS,
            "ExperimentalCondition",
            0,
            "12",
            "m/s",
            "fan speed",
        ),
        (
            FAMILIES,
            ["Series 40 kPa", "Series 65 kPa"],
            "ExperimentFamily",
            1,
            "65",
            "kPa",
            "chamber pressure",
        ),
        (
            FAMILIES,
            ["Series 40 kPa", "Series 65 kPa"],
            "ExperimentFamily",
            1,
            "40",
            "kPa",
            "chamber pressure",
        ),
    ],
)
def test_flags_off_output_is_byte_identical(
    service, monkeypatch, text, labels, cls, subject, expression, unit, name
):
    flag(monkeypatch, None)
    unset, _ = run(service, text, labels, cls, subject, expression, unit, name)
    flag(monkeypatch, "0")
    zero, _ = run(service, text, labels, cls, subject, expression, unit, name)
    assert json.dumps(unset, sort_keys=True) == json.dumps(zero, sort_keys=True)


# Review probes: every one of these must refuse with the flag on.

H = "Synthetic Chamber Survey\n"
SERIES = ["Series 40 kPa", "Series 65 kPa"]
PUMPS = ["Pump 300 mm", "Pump 500 mm"]
NEGATIVES = {
    "comma_whereas": (
        "The Series 40 kPa runs and the Series 65 kPa runs were used, whereas the purge pressure was 40 kPa.",
        SERIES,
        "ExperimentFamily",
        "40",
        "kPa",
        "purge pressure",
    ),
    "next_sentence": (
        "The Series 40 kPa runs and the Series 65 kPa runs were used. The vent pressure was 40 kPa.",
        SERIES,
        "ExperimentFamily",
        "40",
        "kPa",
        "vent pressure",
    ),
    "model": (
        "The Pump 300 mm and the Pump 500 mm units held the chamber pressure; each burner had a 300 mm duct.",
        PUMPS,
        "ExperimentFamily",
        "300",
        "mm",
        "duct length",
    ),
    "model_period": (
        "The Pump 300 mm and the Pump 500 mm units were used. The duct length was 300 mm.",
        PUMPS,
        "ExperimentFamily",
        "300",
        "mm",
        "duct length",
    ),
    "other_quantity": (
        "Earlier rigs kept the Kestrel (21 m/s fan, 30 m/s vent) and Lark (25 m/s) set the fan speed.",
        ["Kestrel (21 m/s fan, 30 m/s vent)", "Lark (25 m/s)"],
        "ExperimentalCondition",
        "30",
        "m/s",
        "fan speed",
    ),
    "list_and": (
        "The Kestrel (21 and 30 m/s) and Lark (25 m/s) set the fan speed.",
        ["Kestrel (21 and 30 m/s)", "Lark (25 m/s)"],
        "ExperimentalCondition",
        "30",
        "m/s",
        "fan speed",
    ),
    "range_dash": (
        "The Kestrel (21-30 m/s) and Lark (25 m/s) set the fan speed.",
        ["Kestrel (21-30 m/s)", "Lark (25 m/s)"],
        "ExperimentalCondition",
        "30",
        "m/s",
        "fan speed",
    ),
    "list_comma": (
        "The Kestrel (21, 30 m/s) and Lark (25 m/s) set the fan speed.",
        ["Kestrel (21, 30 m/s)", "Lark (25 m/s)"],
        "ExperimentalCondition",
        "30",
        "m/s",
        "fan speed",
    ),
}


@pytest.mark.parametrize("name", list(NEGATIVES))
def test_a_value_printed_elsewhere_or_in_a_list_is_never_bound(service, monkeypatch, name):
    flag(monkeypatch, "1")
    text, labels, cls, expression, unit, quantity_name = NEGATIVES[name]
    record, ids = run(service, H + text, labels, cls, 0, expression, unit, quantity_name)
    assert "label_binding" not in record
    assert record.get("subject") != ids[0] or UNBOUND not in record["reasons"]
