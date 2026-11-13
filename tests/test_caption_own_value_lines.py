"""The caption hold reads the lines of the record's own located value spans.

A value printed in a table cell and again in a figure caption: the caption line is not the
record's printed value. A value the validator places on a caption line is still held. Invented
text only."""

import pytest

from nasa_fire_ai.ingestion.printed_layout import is_caption_line
from nasa_fire_ai.ingestion.quantity_validation import own_lines

PAGE = (
    "Figure 3 - Waxed cord burn at 7,500 kPa, post test photo\n"
    "TABLE 2 - Burn data\n"
    "Cord  Pressure  Result\n"
    "W1  7,500  pass\n"
    "W2  7,500  pass\n"
)


def span_of(text, quote, at=0):
    start = text.index(quote, at)
    return {"evidence_id": "E1", "start": start, "end": start + len(quote), "quote": quote}


def hit(support, values):
    return any(is_caption_line(line) and "7,500" in line for line in own_lines(support, values))


def test_a_table_cell_value_is_not_held_for_the_caption_that_prints_it_again():
    cell = PAGE.index("7,500", PAGE.index("W1"))
    values = [{"evidence_id": "E1", "start": cell, "end": cell + 5, "quote": "7,500"}]
    support = span_of(PAGE, "7,500")  # the model's quote lands on the caption's number
    assert is_caption_line(PAGE.splitlines()[0])
    assert not hit({**support, "quote": PAGE.splitlines()[0]}, values)


def test_a_value_the_validator_places_on_the_caption_line_is_held():
    values = [span_of(PAGE, "7,500")]
    first_line = PAGE.splitlines()[0]
    support = {"evidence_id": "E1", "start": 0, "end": len(first_line), "quote": first_line}
    assert hit(support, values)


def test_no_located_value_span_reads_every_line_as_before():
    first_line = PAGE.splitlines()[0]
    support = {"evidence_id": "E1", "start": 0, "end": len(first_line), "quote": first_line}
    assert hit(support, None)
    assert hit(support, [])


def test_only_the_line_that_holds_a_value_span_counts():
    upto = PAGE.index("W1") + len("W1  7,500  pass")
    support = {"evidence_id": "E1", "start": 0, "end": upto, "quote": PAGE[:upto]}
    pos = PAGE.index("7,500", PAGE.index("W1"))
    kept = own_lines(support, [{"evidence_id": "E1", "start": pos, "end": pos + 5}])
    assert kept == ["W1  7,500  pass"]


@pytest.mark.parametrize("flag", ["0"])
def test_the_flag_off_reads_every_line(monkeypatch, flag):
    monkeypatch.setenv("SCIENCE_QUANTITY_OWN_VALUE_LINES", flag)
    first_line = PAGE.splitlines()[0]
    support = {"evidence_id": "E1", "start": 0, "end": len(first_line), "quote": first_line}
    cell = PAGE.index("7,500", PAGE.index("W1"))
    assert hit(support, [{"evidence_id": "E1", "start": cell, "end": cell + 5}])
