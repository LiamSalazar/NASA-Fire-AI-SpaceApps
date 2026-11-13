"""Multi-row column headers (SCIENCE_TABLE_DERIVED_COLUMN_HEADER, on by default; "0" turns it off).

A cell's column header is read from every header row: the leaf names the column, the
rows above it are ancestors. Invented tables only (B8).
"""

import copy

from test_document_extraction import entity, submitted, support
from test_document_extraction import service as _service

from nasa_fire_ai.ingestion.document_extraction import Output, validate_output
from nasa_fire_ai.ingestion.document_structure import structure
from nasa_fire_ai.ingestion.table_continuity import link_continuation_tables

service = _service
FLAG = "SCIENCE_TABLE_DERIVED_COLUMN_HEADER"

COATINGS = [
    ["", "Aging response of coatings", None],
    [None, "Mass loss (%)", "Rate (mg/h)"],
    ["Coating X", "4.1", "0.37"],
    ["Coating Y", "5.2", "0.48"],
]
SAMPLES = [
    ["", "Sample 1", None, "Sample 2", None],
    [None, "Time (s)", "Temp (K)", "Time (s)", "Temp (K)"],
    ["Plate P", "12", "300", "15", "310"],
]
SPEEDS = [
    ["", "Ignition shift", None],
    [None, "Delta T (K) at 2 m/s for 90% interval", "Rate (mg/h)"],
    ["Mix Z", "7.5", "0.31"],
]
TWO_SPEEDS = [
    ["", "Ignition shift", None],
    [None, "Delta T (K) at 2 m/s", "Delta T (K) at 4 m/s"],
    ["Mix Z", "7.5", "9.1"],
]
FITS = [
    ["", "Fit results", None, ""],
    [None, "Best fit slope (g/h)", "Interval slope (g/h)", "Shift (K) at 5 m/s for interval"],
    ["Mix Z", "0.11", "0.29", "3.4"],
]
SINGLE = [
    ["Material", "Energy (J)", "Count"],
    ["Mix Z", "10", "3"],
]


def run_record(
    service,
    monkeypatch,
    rows,
    row_label,
    label,
    expression,
    unit,
    flag,
    epistemic="reported_quantity",
):
    if flag:
        monkeypatch.setenv(FLAG, "1")
    else:
        monkeypatch.setenv(FLAG, "0")
    text = "\n".join(v for row in rows for v in row if v)
    package = submitted(
        service, "# Synthetic study\nII. Results\nTABLE 1— Synthetic data\n" + text + "\n"
    )
    document = structure(package, service.root)
    document["detected_tables"] = link_continuation_tables(
        [
            {
                "input_sha256": package["evidence"][0]["checksum"],
                "physical_pdf_page": package["evidence"][0]["page"],
                "bbox": [0, 0, 1, 1],
                "header": rows[0],
                "header_external": False,
                "cells": rows,
            }
        ]
    )
    output = Output().model_dump()
    output["entities"] = [
        entity(package, "root", "Synthetic study", "Investigation", "# Synthetic study"),
        entity(package, "alpha", row_label, "Sample", row_label),
    ]
    output["quantities"] = [
        {
            "subject": "alpha",
            "label": label,
            "expression": expression,
            "unit": unit,
            "epistemic": epistemic,
            "support": support(package, text),
        }
    ]
    records = validate_output(copy.deepcopy(output), package, document, service.semantic)["records"]
    return [r for r in records if not r.get("candidate_origin")][-1]


def accepted(record):
    return record["status"] != "REJECTED" and (
        "QUANTITY_NAME_IS_NOT_TABLE_COLUMN_HEADER" not in record["reasons"]
    )


def named_by_header(record):
    return "QUANTITY_NAME_IS_NOT_TABLE_COLUMN_HEADER" not in record["reasons"]


def go(service, monkeypatch, rows, row, label, value, unit, flag=True, **kw):
    return run_record(service, monkeypatch, rows, row, label, value, unit, flag, **kw)


def test_two_row_header_leaf_is_accepted_only_with_the_flag(service, monkeypatch):
    on = go(service, monkeypatch, COATINGS, "Coating X", "Mass loss", "4.1", "%")
    assert named_by_header(on), on["reasons"]
    assert on["quantity_name_support"]["basis"] == "ORIGINAL_TABLE_COLUMN_HEADER"
    off = go(service, monkeypatch, COATINGS, "Coating X", "Mass loss", "4.1", "%", flag=False)
    assert off["status"] == "REJECTED"
    assert off["reasons"] == ["QUANTITY_NAME_IS_NOT_TABLE_COLUMN_HEADER"]


def test_spanning_title_or_row_name_or_neighbour_column_is_not_the_name(service, monkeypatch):
    for label in ("Aging response of coatings", "Coating X", "Rate"):
        record = go(service, monkeypatch, COATINGS, "Coating X", label, "4.1", "%")
        assert record["status"] == "REJECTED", label
        assert record["reasons"] == ["QUANTITY_NAME_IS_NOT_TABLE_COLUMN_HEADER"], label


def test_value_of_the_neighbouring_fit_column_is_not_the_best_fit(service, monkeypatch):
    record = go(service, monkeypatch, FITS, "Mix Z", "Best fit slope", "0.29", "g/h")
    assert record["status"] == "REJECTED"
    assert record["reasons"] == ["QUANTITY_NAME_IS_NOT_TABLE_COLUMN_HEADER"]
    good = go(service, monkeypatch, FITS, "Mix Z", "Best fit slope", "0.11", "g/h")
    assert named_by_header(good), good["reasons"]


def test_repeated_leaf_needs_its_distinguishing_ancestor(service, monkeypatch):
    bare = go(service, monkeypatch, SAMPLES, "Plate P", "Time", "15", "s")
    assert bare["status"] == "REJECTED"
    assert bare["reasons"] == ["QUANTITY_NAME_IS_NOT_TABLE_COLUMN_HEADER"]
    for label in ("Sample 2 Time", "Time Sample 2"):
        ok = go(service, monkeypatch, SAMPLES, "Plate P", label, "15", "s")
        assert named_by_header(ok), ok["reasons"]
    wrong = go(service, monkeypatch, SAMPLES, "Plate P", "Sample 1 Time", "15", "s")
    assert wrong["reasons"] == ["QUANTITY_NAME_IS_NOT_TABLE_COLUMN_HEADER"]


def test_reported_time_column_per_sample_is_accepted(service, monkeypatch):
    record = go(service, monkeypatch, SAMPLES, "Plate P", "Sample 1 Time", "12", "s")
    assert named_by_header(record), record["reasons"]


def test_head_names_the_column_only_when_it_alone_identifies_one(service, monkeypatch):
    head = go(service, monkeypatch, SPEEDS, "Mix Z", "Delta T", "7.5", "K")
    assert named_by_header(head), head["reasons"]
    full = go(
        service, monkeypatch, SPEEDS, "Mix Z", "Delta T at 2 m/s for 90% interval", "7.5", "K"
    )
    assert named_by_header(full), full["reasons"]
    ambiguous = go(service, monkeypatch, TWO_SPEEDS, "Mix Z", "Delta T", "7.5", "K")
    assert ambiguous["reasons"] == ["QUANTITY_NAME_IS_NOT_TABLE_COLUMN_HEADER"]
    qualified = go(service, monkeypatch, TWO_SPEEDS, "Mix Z", "Delta T at 2 m/s", "7.5", "K")
    assert named_by_header(qualified), qualified["reasons"]
    shared = go(service, monkeypatch, FITS, "Mix Z", "Shift", "3.4", "K")
    assert named_by_header(shared), shared["reasons"]


def test_head_does_not_cross_to_a_prefix_of_another_column(service, monkeypatch):
    record = go(service, monkeypatch, FITS, "Mix Z", "Slope", "0.11", "g/h")
    assert record["reasons"] == ["QUANTITY_NAME_IS_NOT_TABLE_COLUMN_HEADER"]


def test_single_row_header_is_identical_with_and_without_the_flag(service, monkeypatch):
    for label, value, unit in (
        ("Energy", "10", "J"),
        ("Count", "3", None),
        ("Material", "10", "J"),
    ):
        on = go(service, monkeypatch, SINGLE, "Mix Z", label, value, unit)
        off = go(service, monkeypatch, SINGLE, "Mix Z", label, value, unit, flag=False)
        assert (on["status"], on["reasons"]) == (off["status"], off["reasons"]), label


def test_the_flag_is_on_by_default(monkeypatch):
    from nasa_fire_ai.ingestion.table_continuity import derived_column_header_enabled

    monkeypatch.delenv(FLAG, raising=False)
    assert derived_column_header_enabled()
    monkeypatch.setenv(FLAG, "0")
    assert not derived_column_header_enabled()
