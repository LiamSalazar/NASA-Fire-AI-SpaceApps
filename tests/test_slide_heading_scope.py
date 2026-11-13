"""Slide heading scope (SCIENCE_SLIDE_HEADING_SCOPE, off by default): in a slide deck each
anchor is sent under the heading validation reads for it, its own slide's heading or title,
never a heading printed on an earlier slide. Request side only; synthetic documents (B8)."""

import json
import shutil
from types import SimpleNamespace
from unittest.mock import Mock

import pymupdf
import pytest
from test_document_extraction import ROOT, submitted

from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.document_extraction import STAGES, ExtractionBudget, section_for_span
from nasa_fire_ai.ingestion.document_structure import structure
from nasa_fire_ai.services.curation import CurationService

FLAGS = ("SCIENCE_SLIDE_HEADING_SCOPE", "SCIENCE_TABLE_AFTER_REFERENCES", "SCIENCE_STRUCTURE_FIXES")

SLIDES = [
    ("Synthetic Tile Talk", ["Presented by A. Author"]),
    ("Background", ["Glazed tiles were first fired in a kiln."]),
    ("Tile Rules", ["Crack width stays below 3 mm."]),
    ("Tile Results", ["Coarse glaze cracked 2 mm.", "Results", "Fine glaze cracked 4 mm."]),
    ("Summary", ["Coarse glaze passes."]),
]


@pytest.fixture
def fresh(tmp_path):
    """A new service per call: no request is answered from an earlier run's cache."""
    made = []

    def make():
        root = tmp_path / f"s{len(made)}"
        for name in ("domain", "ontology", "data/canonical"):
            shutil.copytree(ROOT / name, root / name)
        registry = EvidenceRegistry(root / "data/index/evidence.sqlite")
        made.append(registry)
        return CurationService(root, registry)

    yield make
    for registry in made:
        registry.db.close()


def requests_for(service, monkeypatch, package, flags=(), env=None, answer=None):
    for name in FLAGS:
        monkeypatch.delenv(name, raising=False)
    for name in flags:
        monkeypatch.setenv(name, "1")
    for name, value in (env or {}).items():
        monkeypatch.setenv(name, value)
    sent = []

    def respond(**kwargs):
        payload = json.loads(kwargs["messages"][1]["content"])
        sent.append(payload)
        result = {k: [] for k in STAGES[payload["stage"]]}
        if answer:
            result.update(answer(payload))
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=json.dumps(result)), finish_reason="stop"
                )
            ],
            usage=None,
        )

    client = Mock()
    client.client.with_options.return_value.chat.completions.create.side_effect = respond
    service.prepare_scientific(
        package["id"],
        Settings(root=service.root),
        model_enabled=True,
        budget=ExtractionBudget(max_model_calls=40),
        client=client,
    )
    return sent


def deck_pdf(slides=SLIDES):
    pdf = pymupdf.open()
    for title, lines in slides:
        page = pdf.new_page(width=960, height=540)
        page.insert_text((60, 60), title, fontsize=32)
        for i, line in enumerate(lines):
            page.insert_text((60, 140 + 50 * i), line, fontsize=18)
    return pdf.tobytes()


def deck(service, slides=SLIDES, data=None):
    # The same bytes when given: a PDF written twice differs in its metadata.
    data = data or deck_pdf(slides)
    return service.submit(slides[0][0], "Slides", [("deck.pdf", data)], "t")["package"]


def headings_of(sent, quote):
    return {
        a.get("heading") for p in sent for a in p.get("source_anchors", []) if quote in a["quote"]
    }


def validation_heading(service, package, page, quote):
    """The heading validation reads for a printed quote (``section_for_span``)."""
    document = structure(package, service.root)
    evidence = next(e for e in package["evidence"] if e["page"] == page)
    span = {"evidence_id": evidence["evidence_id"], "start": evidence["text"].find(quote)}
    assert span["start"] >= 0
    heading = section_for_span(span, document)
    return None if heading == "UNSPECIFIED" else heading


def test_off_by_default_an_anchor_keeps_the_earlier_slides_heading(fresh, monkeypatch):
    service = fresh()
    sent = requests_for(service, monkeypatch, deck(service))
    assert "Background" in headings_of(sent, "Crack width stays")


def test_a_slide_heading_governs_its_own_slide_only(fresh, monkeypatch):
    service = fresh()
    sent = requests_for(service, monkeypatch, deck(service), ["SCIENCE_SLIDE_HEADING_SCOPE"])
    assert headings_of(sent, "Crack width stays") == {"Tile Rules"}
    assert headings_of(sent, "Coarse glaze passes") == {"Summary"}


def test_a_heading_printed_inside_a_slide_governs_what_follows_it_on_that_slide(fresh, monkeypatch):
    service = fresh()
    sent = requests_for(service, monkeypatch, deck(service), ["SCIENCE_SLIDE_HEADING_SCOPE"])
    assert headings_of(sent, "Coarse glaze cracked") == {"Tile Results"}
    assert headings_of(sent, "Fine glaze cracked") == {"Results"}


def test_the_request_heading_is_the_validation_heading_for_every_anchor(fresh, monkeypatch):
    service = fresh()
    package = deck(service)
    sent = requests_for(service, monkeypatch, package, ["SCIENCE_SLIDE_HEADING_SCOPE"])
    anchors = {(a["page"], a["quote"], a.get("heading")) for p in sent for a in p["source_anchors"]}
    assert anchors
    for page, quote, heading in anchors:
        assert heading == validation_heading(service, package, page, quote), quote


def test_a_paper_is_sent_exactly_as_with_the_flag_off(fresh, monkeypatch):
    text = (
        "Synthetic Tile Study\n"
        "I. Introduction\nEarlier work fired glazed tiles [1].\n"
        "II. Methods\nTile T1 was fired at 1200 C.\n"
        "III. Results\nTile T1 cracked 2 mm.\n"
    )
    off, on = fresh(), fresh()
    a = requests_for(off, monkeypatch, submitted(off, text))
    b = requests_for(on, monkeypatch, submitted(on, text), ["SCIENCE_SLIDE_HEADING_SCOPE"])
    assert a and json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_renaming_a_slide_title_renames_only_its_own_anchors_heading(fresh, monkeypatch):
    renamed = [(("Panel Rules" if t == "Tile Rules" else t), lines) for t, lines in SLIDES]
    first, second = fresh(), fresh()
    a = requests_for(first, monkeypatch, deck(first), ["SCIENCE_SLIDE_HEADING_SCOPE"])
    b = requests_for(second, monkeypatch, deck(second, renamed), ["SCIENCE_SLIDE_HEADING_SCOPE"])
    assert headings_of(b, "Crack width stays") == {"Panel Rules"}
    for quote in ("Glazed tiles were", "Coarse glaze cracked", "Fine glaze cracked", "passes"):
        assert headings_of(a, quote) == headings_of(b, quote), quote


def test_an_earlier_slide_heading_does_not_reach_a_later_slide(fresh, monkeypatch):
    extra = [*SLIDES[:2], ("Introduction", ["Kilns differ in ramp rate."]), *SLIDES[2:]]
    first, second = fresh(), fresh()
    a = requests_for(first, monkeypatch, deck(first), ["SCIENCE_SLIDE_HEADING_SCOPE"])
    b = requests_for(second, monkeypatch, deck(second, extra), ["SCIENCE_SLIDE_HEADING_SCOPE"])
    for quote in ("Crack width stays", "Coarse glaze cracked", "Fine glaze cracked"):
        assert headings_of(a, quote) == headings_of(b, quote), quote


def test_the_slide_heading_is_one_function_shared_with_validation():
    from nasa_fire_ai.ingestion import document_extraction

    assert callable(document_extraction.slide_heading)
