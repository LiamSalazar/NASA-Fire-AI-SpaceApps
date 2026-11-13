"""SCIENCE_STANDARD_DESIGNATION: a standard is a document, not a family of experiments (invented labels
that follow the drafting form of references to standards; none belongs to the development set)."""

import pytest

from nasa_fire_ai.ingestion.entity_validation import (
    is_standard_designation,
    standard_designation_enabled,
)


@pytest.mark.parametrize(
    "label",
    [
        "ASTM G124",
        "ASTM G124 test method",
        "ISO 14624",
        "ISO 14624-1:2003",
        "MIL-STD-810G",
        "NFPA 53",
        "IEC 60695-11-10",
        "NASA-STD-9999",
        "NASA STD 9999 Test 2",
        "DIN 4102",
        "UL 94",
    ],
)
def test_a_designation_is_recognised_by_its_form(label):
    assert is_standard_designation(label)


@pytest.mark.parametrize(
    "label",
    [
        "Test 1",
        "Series 3",
        "Run 12",
        "Model T-100",
        "Xylo 200",
        "Pump 12",
        "FLIR A655 camera",
        "Rack char study",
        "Takahashi low gravity tests",
        "the 2019 drop series",
        "",
    ],
)
def test_a_bare_test_number_or_a_product_name_is_not_a_designation(label):
    assert not is_standard_designation(label)


def test_the_flag_is_on_by_default(monkeypatch):
    monkeypatch.delenv("SCIENCE_STANDARD_DESIGNATION", raising=False)
    assert standard_designation_enabled()
    monkeypatch.setenv("SCIENCE_STANDARD_DESIGNATION", "0")
    assert not standard_designation_enabled()
