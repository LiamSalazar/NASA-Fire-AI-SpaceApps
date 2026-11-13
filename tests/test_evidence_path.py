"""One evidence-path builder: the printed parents of a span. Invented text only (B8)."""

from nasa_fire_ai.ingestion import printed_layout as pl


def document():
    return {
        "segments": [{"evidence_id": "e1", "source_id": "s"}],
        "sections": [
            {"evidence_id": "e1", "source_id": "s", "start": 0, "title": "B. Blue Valve Testing"},
            {"evidence_id": "e1", "source_id": "s", "start": 80, "title": "C. Green Valve Testing"},
        ],
        "layout_headings": {"e1": {"evidence_id": "e1", "start": 0, "quote": "Page head"}},
        "figures": [
            {
                "evidence_id": "e1",
                "source_id": "s",
                "number": "2",
                "start": 120,
                "end": 170,
                "first_line_end": 150,
                "quote": "Figure 2 - Pressures During the Blue Valve Test Series",
            }
        ],
    }


SPAN = {
    "evidence_id": "e1",
    "source_id": "s",
    "start": 30,
    "end": 70,
    "quote": "Times ranged from 40-48 ms (Figure 2).",
}


def test_path_lists_the_parents_nearest_first():
    kinds = [s["kind"] for s in pl.evidence_path(SPAN, document())]
    assert kinds == ["sentence", "subsection_heading", "layout_heading", "referenced_caption"]


def test_the_subsection_step_is_the_nearest_heading_before_the_span():
    path = pl.evidence_path(SPAN, document())
    assert pl.path_step(path, "subsection_heading")["quote"] == "B. Blue Valve Testing"
    later = {**SPAN, "start": 90}
    path = pl.evidence_path(later, document())
    assert pl.path_step(path, "subsection_heading")["quote"] == "C. Green Valve Testing"


def test_steps_can_be_restricted():
    path = pl.evidence_path(SPAN, document(), steps=("referenced_caption",))
    assert [s["kind"] for s in path] == ["referenced_caption"]
    assert path[0]["number"] == "2"


def test_readers_agree_with_the_heading_lookup():
    doc = document()
    for start in (0, 30, 90, 200):
        span = {**SPAN, "start": start}
        assert pl.subsection_heading_of(span, doc) == pl.printed_heading_before(span, doc)


def test_a_reference_notation_gives_the_same_caption_step():
    doc = document()
    for quote in ("(Figure 2)", "(see Figure 2)", "in Fig. 2"):
        path = pl.evidence_path({**SPAN, "quote": quote}, doc, steps=("referenced_caption",))
        assert [s["number"] for s in path] == ["2"]
