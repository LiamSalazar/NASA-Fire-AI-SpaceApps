"""SCIENCE_NUMERIC_UNIT_RANGE (on by default; "0" turns it off): a unit inside a range that ends in a number word does not hide the
number it starts with. Invented text only."""

import pytest
from test_document_extraction import entity, submitted, validate
from test_document_extraction import service as _service
from test_scientific_facets import only, quantity

from nasa_fire_ai.ingestion.document_extraction import Output
from nasa_fire_ai.ingestion.numeric_expressions import same_expression, source_numeric_matches

service = _service
FLAG = "SCIENCE_NUMERIC_UNIT_RANGE"


def values(text):
    return [m.group(1) for m in source_numeric_matches(text)]


@pytest.mark.parametrize(
    "text",
    [
        "the crate mass of 7 kg to zero would give a slope",
        "the stack fell from 7 kg to zero in the run",
    ],
)
def test_the_first_number_of_a_unit_range_ending_in_a_word_is_located(monkeypatch, text):
    monkeypatch.setenv(FLAG, "0")
    assert not any(same_expression(v, "7") for v in values(text))
    monkeypatch.setenv(FLAG, "1")
    assert any(same_expression(v, "7") for v in values(text))


def test_ordinary_numbers_and_ranges_are_unchanged(monkeypatch):
    text = "Between 4 and 6 s, 7 kg to 9 kg and 10,000 Pa at 2/20."
    monkeypatch.setenv(FLAG, "0")
    before = values(text)
    monkeypatch.setenv(FLAG, "1")
    assert values(text) == before


def test_a_value_followed_by_a_unit_range_is_not_absent(service, monkeypatch):
    sentence = "The Alpha run crate mass of 7 kg to zero would give a slope."

    def read(on):
        monkeypatch.setenv(FLAG, "1" if on else "0")
        p = submitted(service, "II. Results\n" + sentence + "\n")
        o = Output().model_dump()
        o["entities"] = [entity(p, "n", "Alpha run", "ExperimentalRun", sentence)]
        o["quantities"] = [
            quantity(p, sentence, "n", "crate mass", "7", "kg", "experimental_configuration")
        ]
        return only(validate(service, p, o)["records"], "quantities")

    assert "QUANTITY_EXPRESSION_ABSENT" in read(False)["reasons"]
    assert "QUANTITY_EXPRESSION_ABSENT" not in read(True)["reasons"]


def test_the_flag_is_on_by_default(monkeypatch):
    text = "the crate mass of 7 kg to zero would give a slope"
    monkeypatch.delenv(FLAG, raising=False)
    assert any(same_expression(v, "7") for v in values(text))
    monkeypatch.setenv(FLAG, "0")
    assert not any(same_expression(v, "7") for v in values(text))
