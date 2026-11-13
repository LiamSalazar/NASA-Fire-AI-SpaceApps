"""A page's running header before a whole sentence is cut off, never a sentence; synthetic."""

from nasa_fire_ai.ingestion.document_extraction import page_edge_prefix

HEADER = "Synthetic Conference on Flame Systems"


def pages(*bodies):
    return {
        f"E-{n}": {
            "evidence_id": f"E-{n}",
            "source_id": "src",
            "page": n,
            "text": f"{HEADER}\n{n}\n{body}\n",
        }
        for n, body in enumerate(bodies, start=1)
    }


EVIDENCE = pages(
    "The rig was assembled. Figure 1 shows the rig.\nFigure 1 - Rig Layout\n(side view)",
    "Valve tests followed.",
    "Seal tests began after the",
    "first purge was complete.",
)


def span(page, text):
    return [{"evidence_id": f"E-{page}", "start": 0, "end": len(text), "quote": text}]


def test_a_running_header_and_caption_before_a_whole_sentence_are_cut():
    text = f"{HEADER}\n2\nFigure 2 - Valve Layout\nThe valve closed in 40 ms after each impact."
    edge = page_edge_prefix(text, EVIDENCE, span(2, text))
    assert text[len(edge) :] == "The valve closed in 40 ms after each impact."


def test_a_sentence_continued_from_the_previous_page_is_not_cut():
    # Page 3 ends without a full stop: page 4 opens with the rest of its sentence.
    text = f"{HEADER}\n4\nFirst purge was complete before the valve test began."
    assert page_edge_prefix(text, EVIDENCE, span(4, text)) == ""


def test_a_lowercase_start_a_caption_alone_or_no_header_are_not_cut():
    lower = f"{HEADER}\n2\nthe valve closed in 40 ms after each impact."
    caption = f"{HEADER}\n2\nFigure 2 - Valve Layout With Its Five Ports"
    plain = "Figure 2 - Valve Layout\nThe valve closed in 40 ms after each impact."
    for text in (lower, caption, plain):
        assert page_edge_prefix(text, EVIDENCE, span(2, text)) == ""


def test_a_quotation_closed_before_it_opens_is_not_cut():
    text = f"{HEADER}\n2\nDelivery System” (DS) was set up to heat the valve body."
    assert page_edge_prefix(text, EVIDENCE, span(2, text)) == ""
