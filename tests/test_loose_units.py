"""Units printed apart from their value: inch marks and table header rows; synthetic text."""

import pytest
from test_document_extraction import entity, submitted, support, validate
from test_document_extraction import service as _service

from nasa_fire_ai.ingestion.document_extraction import Output
from nasa_fire_ai.ingestion.pdf_quantities import header_unit_binding, original_table_unit
from nasa_fire_ai.normalization.units import interpret

service = _service


def quantity(service, text, expression, unit):
    p = submitted(service, "II. Methods\n" + text + "\n")
    o = Output().model_dump()
    o["entities"] = [entity(p, "d", "Alpha drum", "Sample", "Alpha drum")]
    o["quantities"] = [
        {
            "subject": "d",
            "label": "burn length",
            "expression": expression,
            "unit": unit,
            "epistemic": "experimental_configuration",
            "support": support(p, text),
        }
    ]
    (record,) = [r for r in validate(service, p, o)["records"] if r["kind"] == "quantities"]
    return record


@pytest.mark.parametrize("mark", ["”", "″", '"'])
def test_an_inch_mark_after_a_number_is_a_length_unit(service, mark):
    assert interpret(mark)["dimension"] == "length"
    record = quantity(service, f"The Alpha drum burn length was 6{mark} at most.", "6", mark)
    assert "QUANTITY_UNIT_NOT_BOUND_TO_EXPRESSION" not in str(record["reasons"]), record


def test_a_quotation_mark_closing_a_quoted_number_is_not_an_inch_mark(service):
    record = quantity(service, "The Alpha drum burn length was labelled “6” in the log.", "6", "”")
    assert record["status"] == "REJECTED"
    assert "QUANTITY_UNIT_NOT_BOUND_TO_EXPRESSION" in str(record["reasons"])


def table(cells):
    return {
        "detected_tables": [
            {
                "cells": cells,
                "header": cells[0],
                "header_external": False,
                "input_sha256": "x",
                "physical_pdf_page": 3,
                "bbox": [0, 0, 1, 1],
            }
        ]
    }


SPANNING = [
    ["", "Extinction slope versus flow", None, ""],
    [None, "Best fit slope\n(s/cm)", "Bound slope (s/cm)", "∆O2% for 95%\ninterval"],
    ["Alpha", "0.00022", "0.00056", "1.9"],
    ["Beta", "0.00040", "0.00065", "2.3"],
]


def test_a_column_name_under_a_spanning_title_row_is_its_header():
    doc = table(SPANNING)
    binding = header_unit_binding("0.00065", "s/cm", [{"page": 3}], doc)
    assert binding and binding["column_index"] == 2
    assert binding["original_column_header"] == "Bound slope (s/cm)"


def test_a_percent_glued_to_a_quantity_symbol_is_the_column_unit():
    doc = table(SPANNING)
    assert header_unit_binding("2.3", "%", [{"page": 3}], doc)
    # Negative: a percent after a number is a value, not the column's unit.
    assert original_table_unit("Width at 95% interval", [])[0] is None
    assert not header_unit_binding("2.3", "s/cm", [{"page": 3}], doc)


def test_a_data_row_ends_the_header_rows():
    # Metamorphic: the same unit printed in a row below the first data row is a
    # cell, not a header.
    cells = [
        ["", "Slope", "Bound", "Shift"],
        ["Alpha", "0.00022", "0.00056", "1.9"],
        [None, "Best fit (s/cm)", "Bound (s/cm)", "∆O2%"],
        ["Beta", "0.00040", "0.00065", "2.3"],
    ]
    doc = table(cells)
    assert not header_unit_binding("0.00065", "s/cm", [{"page": 3}], doc)
    assert not header_unit_binding("2.3", "%", [{"page": 3}], doc)
