"""A running footer after a whole sentence closes it, with the page's next block; synthetic."""

from nasa_fire_ai.ingestion.document_extraction import page_edge_suffix

FOOTER = "Synthetic Conference on Flame Systems"
DATE = "March 3-5, 2031"


def pages(*bodies, date=True):
    return {
        f"E-{n}": {
            "evidence_id": f"E-{n}",
            "source_id": "src",
            "page": n,
            "text": f"Synthetic Agency\n{n}\n{body}\n{FOOTER}\n" + (f"{DATE}\n" if date else ""),
        }
        for n, body in enumerate(bodies, start=1)
    }


EVIDENCE = pages("• Coupons burned longer", "• Seals held", "• Valves closed", "• Pumps ran")
SENTENCE = "•\nLayered coupons at 30% O2 show longer burn lengths than single layers"


def test_the_footer_its_date_page_number_and_the_next_block_are_cut():
    text = f"{SENTENCE}\n{FOOTER}\n{DATE}\n3\nExamples of Coupon Layups\nKnit\nWoven"
    tail = page_edge_suffix(text, EVIDENCE)
    assert text[: len(text) - len(tail)] == SENTENCE


def test_a_footer_closing_the_passage_is_cut():
    text = f"• Certification testing will be performed at the test facility\n{FOOTER}\n{DATE}"
    tail = page_edge_suffix(text, EVIDENCE)
    assert text[: len(text) - len(tail)].endswith("at the test facility")


def test_the_same_sentence_with_or_without_the_date_line_gives_the_same_cut():
    # Metamorphic: the footer's companion line is page furniture, not content.
    plain = pages("• Coupons burned longer", "• Seals held", "• Valves closed", date=False)
    with_date = f"{SENTENCE}\n{FOOTER}\n{DATE}\n2\nNext Block"
    without = f"{SENTENCE}\n{FOOTER}\n2\nNext Block"
    assert with_date[: len(with_date) - len(page_edge_suffix(with_date, EVIDENCE))] == SENTENCE
    assert without[: len(without) - len(page_edge_suffix(without, plain))] == SENTENCE


def test_a_sentence_that_continues_after_the_footer_is_not_cut():
    # Across a page break the sentence goes on in lowercase: the existing header
    # hold applies instead.
    text = (
        f"The seal was inspected after the\n{FOOTER}\n{DATE}\n4\nfirst purge and showed no damage."
    )
    assert page_edge_suffix(text, EVIDENCE) == ""


def test_a_short_fragment_or_a_passage_without_a_footer_is_not_cut():
    short = f"• Coupons\n{FOOTER}\n{DATE}\nNext Block"
    assert page_edge_suffix(short, EVIDENCE) == ""
    assert page_edge_suffix(SENTENCE, EVIDENCE) == ""


def test_a_line_printed_on_few_pages_is_not_a_footer():
    text = f"{SENTENCE}\nSynthetic Results Of The Flame Test\n{DATE}\nNext Block"
    assert page_edge_suffix(text, EVIDENCE) == ""
