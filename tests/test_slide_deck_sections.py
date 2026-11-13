"""A slide's own title is its section; a deck is the presenter's own account; synthetic text."""

from nasa_fire_ai.ingestion.document_extraction import (
    original_research_passage,
    section_for_span,
    slide_deck,
)

SLIDES = [
    "1\nSynthetic Flame Talk\nPresented by: A. Author\n",
    "2\nBackground\n• Earlier coupons burned faster in enriched oxygen\n",
    "3\nCoupon Comparisons\n• Layered coupons at 30% O2 show longer burn lengths than single layers\n",
    "4\nSourcing Status\n• The team has been sourcing commercial fabrics\n",
    "5\nPrior Work\n• Smith et al. showed melting fabrics drip\n",
    "6\nQuestions?\n• Contact the author\n",
]


def document(pages, sections=(), title="Synthetic Flame Talk"):
    segments = [
        {"evidence_id": f"E-{i}", "source_id": "src", "start": 0, "text": text}
        for i, text in enumerate(pages)
    ]
    return {"segments": segments, "sections": list(sections), "package_title": title}


def span(doc, page, quote):
    text = doc["segments"][page]["text"]
    return {
        "evidence_id": f"E-{page}",
        "source_id": "src",
        "start": text.index(quote),
        "quote": quote,
    }


# The structure reader takes the slide number before "Background" for an outline number.
NUMBERED = [{"evidence_id": "E-1", "source_id": "src", "start": 0, "title": "2\nBackground"}]


def test_a_slide_numbered_heading_governs_only_its_own_slide():
    doc = document(SLIDES, NUMBERED)
    assert slide_deck(doc)
    quote = "Layered coupons at 30% O2 show longer burn lengths than single layers"
    assert section_for_span(span(doc, 2, quote), doc) == "Coupon Comparisons"
    assert "Background" in section_for_span(span(doc, 1, "Earlier coupons"), doc)


def test_a_finding_on_a_slide_of_its_own_is_the_presenters_research():
    doc = document(SLIDES, NUMBERED)
    quote = "Layered coupons at 30% O2 show longer burn lengths than single layers"
    assert original_research_passage([span(doc, 2, quote)], doc)
    assert original_research_passage([span(doc, 3, "The team has been sourcing")], doc)


def test_background_prior_work_frame_and_title_slides_are_not_own_research():
    doc = document(SLIDES, NUMBERED)
    assert not original_research_passage([span(doc, 1, "Earlier coupons burned faster")], doc)
    assert not original_research_passage([span(doc, 4, "Smith et al. showed")], doc)
    assert not original_research_passage([span(doc, 5, "Contact the author")], doc)
    assert not original_research_passage([span(doc, 0, "Presented by")], doc)


def test_a_cited_study_on_an_own_slide_stays_cited():
    pages = list(SLIDES)
    pages[2] = "3\nCoupon Comparisons\n• Smith et al. reported longer burn lengths\n"
    doc = document(pages, NUMBERED)
    assert not original_research_passage([span(doc, 2, "Smith et al. reported")], doc)


def test_a_running_header_on_every_page_is_not_a_slide_title():
    # Metamorphic: the same pages under one repeated paper number are a paper, not
    # a deck, and its numbered "Background" section runs on to the next page.
    pages = ["PAPER-2019-01\n" + text.split("\n", 2)[2] for text in SLIDES]
    sections = [{"evidence_id": "E-1", "source_id": "src", "start": 0, "title": "2. Background"}]
    doc = document(pages, sections)
    assert not slide_deck(doc)
    quote = "Layered coupons at 30% O2 show longer burn lengths than single layers"
    assert "Background" in section_for_span(span(doc, 2, quote), doc)
    assert not original_research_passage([span(doc, 2, quote)], doc)
