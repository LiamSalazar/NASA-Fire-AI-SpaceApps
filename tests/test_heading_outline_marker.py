"""A heading's outline marker copied into a label is not part of the name; synthetic headings."""

import pytest

from nasa_fire_ai.ingestion.document_extraction import heading_outline_name


def document(*titles):
    return {"sections": [{"title": t} for t in titles]}


@pytest.mark.parametrize(
    "marker,sibling",
    [("B.", "A."), ("2.1", "2.2"), ("IV.", "III.")],
)
def test_a_copied_outline_marker_is_dropped_from_the_name(marker, sibling):
    # Metamorphic: the same heading with and without its marker names the same group.
    doc = document(f"{sibling} Beta Flow Testing", f"{marker} Alpha Partial Gravity Testing")
    assert heading_outline_name(f"{marker} Alpha Partial Gravity Testing", doc) == (
        "Alpha Partial Gravity Testing"
    )
    assert heading_outline_name("Alpha Partial Gravity Testing", doc) is None


def test_a_lone_initial_or_a_letter_inside_the_name_is_kept():
    # "J." heads no sequence of letter-marked headings, so it is an initial.
    doc = document("J. Smith Apparatus", "2. Methods", "3. Results")
    assert heading_outline_name("J. Smith Apparatus", doc) is None
    assert heading_outline_name("Type A Tests", document("A. Setup", "B. Type A Tests")) is None


def test_a_marker_the_heading_does_not_print_is_not_dropped():
    doc = document("A. Beta Flow Testing", "Alpha Partial Gravity Testing")
    assert heading_outline_name("C. Alpha Partial Gravity Testing", doc) is None
    assert heading_outline_name("B. Alpha Partial Gravity Testing", doc) is None
