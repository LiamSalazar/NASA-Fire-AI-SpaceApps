"""Tables after the references (SCIENCE_TABLE_AFTER_REFERENCES, off by default): a printed
table under the reference heading is windowed as its caption and rows only; reference-list
text is never windowed, and a reference line naming a table is not a table caption.
Request side only; synthetic documents (B8)."""

import json

from test_document_extraction import submitted
from test_slide_heading_scope import fresh as _fresh
from test_slide_heading_scope import requests_for

from nasa_fire_ai.ingestion.document_structure import model_windows, printed_table_regions

fresh = _fresh

FLAG = ["SCIENCE_TABLE_AFTER_REFERENCES"]


def seg(id_, section, text, start=0):
    return {
        "id": id_,
        "evidence_id": "E-" + id_,
        "source_id": "s",
        "page": 1,
        "start": start,
        "end": start + len(text),
        "section": section,
        "layout_heading": None,
        "text": text,
        "section_transitions": [],
    }


BACK = (
    "[1] A. Author, Kiln ramp tests, 1999.\n"
    "\n"
    "Table 9: Crack widths\n"
    "Plate A 0.4\n"
    "Plate B 0.7\n"
    "[2] B. Author, Glaze studies, 2001.\n"
)


def windowed(segments, on):
    windows = model_windows({"segments": segments}, 6500, tables_after_references=on)
    return [m["text"] for w in windows for m in w["members"]]


def test_off_by_default_back_matter_is_not_windowed():
    segments = [seg("a", "II. Methods", "Plates were fired.\n"), seg("b", "References", BACK)]
    assert windowed(segments, False) == ["Plates were fired.\n"]
    assert model_windows({"segments": segments}, 6500) == model_windows(
        {"segments": segments}, 6500, tables_after_references=False
    )


def test_a_printed_table_after_the_reference_heading_is_windowed_without_the_references():
    segments = [seg("a", "II. Methods", "Plates were fired.\n"), seg("b", "References", BACK)]
    texts = windowed(segments, True)
    assert texts == ["Plates were fired.\n", "Table 9: Crack widths\nPlate A 0.4\nPlate B 0.7"]
    assert not any("Author" in t for t in texts)


def test_the_table_member_keeps_its_original_locator():
    whole = seg("b", "References", BACK, start=100)
    (window,) = model_windows({"segments": [whole]}, 6500, tables_after_references=True)
    (member,) = window["members"]
    begin = member["start"] - whole["start"]
    assert whole["text"][begin : begin + len(member["text"])] == member["text"]
    assert member["end"] - member["start"] == len(member["text"])
    assert member["id"] != whole["id"]


def test_a_reference_line_naming_a_table_is_not_a_table_caption():
    for text in (
        "[1] A. Author, see table 9 in the cited report, 1999.\n",
        "[3] C. Author, widths reported in\nTable 12 Of the cited report, 12 pages, 2003.\n",
        "4. D. Author, Table 13: values, 2004.\n",
        "Author, E. F., Table 14 Data, 2005.\n",
    ):
        assert printed_table_regions(text) == [], text
        assert windowed([seg("b", "References", text)], True) == [], text


def test_a_wrapped_reference_after_an_initial_a_year_or_an_abbreviation_is_no_caption():
    for text in (
        "[1] Arden, P., Brook, Q. R.\nTable 3: Kiln drift data, Kiln J. 12\n(1988) 33-40.\n",
        "[1] Arden, P., Kiln sets, 1993.\nTable 2 Plates of the survey, Kiln J. 4\n(1993) 1-9.\n",
        "[1] Arden P, Brook Q, Kiln sets, pp.\nTable 5 Plates of the survey, Kiln J. 4\n(1993) 1-9.\n",
    ):
        assert printed_table_regions(text) == [], text


def test_entries_after_a_table_are_not_rows():
    rows = "Table 9: Crack widths\nPlate A 0.4\nPlate B 0.7\n"
    for entry in (
        "Cole R, Dane S. Kiln cracks. Kiln J 1990;12:33-40.\n",
        "Cole R (1990) Kiln cracks. Kiln J 12, 33-40.\n",
        "van Dorn, K. Kiln cracks, 1990.\n",
        "[3] Cole, R. Kiln cracks, 1990.\n",
        "3. Cole R. Kiln cracks 12.\n",
        "Kiln cracks in glazed tiles, doi 10.1000/x12\n",
    ):
        (region,) = printed_table_regions(rows + entry)
        assert (rows + entry)[region[0] : region[1]] == rows.rstrip("\n"), entry
    text = rows + "\nCole R, Dane S.\nKiln text 12\n"
    (region,) = printed_table_regions(text)
    assert text[region[0] : region[1]] == rows.rstrip("\n")


def test_a_caption_with_no_printed_rows_is_not_a_table():
    text = (
        "[1] A. Author, Kiln tests, 1999.\nTable 15: Not reproduced here.\n[2] B. Author, 2001.\n"
    )
    assert printed_table_regions(text) == []


def test_acknowledgments_stay_out_whatever_the_flag():
    text = "We thank the kiln staff for 3 weeks of help.\n"
    assert windowed([seg("b", "Acknowledgments", text)], True) == []


def test_the_window_is_the_same_whatever_the_reference_entries_around_it():
    other = BACK.replace("Kiln ramp tests", "Unrelated survey of 40 tiles").replace(
        "[2] B. Author, Glaze studies, 2001.\n",
        "[2] Z. Writer, Other work, 1987.\n[3] Y. W., 1990.\n",
    )
    assert windowed([seg("b", "References", BACK)], True) == windowed(
        [seg("b", "References", other)], True
    )


def test_renaming_the_table_moves_only_its_caption_text():
    renamed = BACK.replace("Table 9: Crack widths", "Table 11: Gap sizes")
    (a,) = windowed([seg("b", "References", BACK)], True)
    (b,) = windowed([seg("b", "References", renamed)], True)
    assert a.split("\n")[1:] == b.split("\n")[1:]
    assert b.startswith("Table 11: Gap sizes")


TEXT = (
    "Synthetic Tile Study\n"
    "I. Introduction\nEarlier work fired glazed tiles [1].\n"
    "II. Methods\nTile T1 was fired at 1200 C.\n"
    "III. Results\nTile T1 cracked 2 mm.\n"
    "References\n"
    "[1] A. Author, Tests were conducted in a gas kiln, 1999.\n"
    "\n"
    "Table 9: Crack widths of plates\n"
    "Plate A 0.4 mm\n"
    "Plate B 0.7 mm\n"
    "[2] B. Author, Glaze studies, 2001.\n"
)


def quotes(sent):
    return [a["quote"] for p in sent for a in p.get("source_anchors", [])]


def test_flag_on_sends_the_table_rows_and_never_reference_list_text(fresh, monkeypatch):
    service = fresh()
    sent = requests_for(service, monkeypatch, submitted(service, TEXT), FLAG)
    assert any("Plate B 0.7" in q for q in quotes(sent))
    assert not any("A. Author" in q or "B. Author" in q for q in quotes(sent))
    assert not any("A. Author" in json.dumps(p) for p in sent)


def test_flag_off_sends_no_table_row_from_back_matter(fresh, monkeypatch):
    service = fresh()
    sent = requests_for(service, monkeypatch, submitted(service, TEXT))
    assert sent and not any("Plate B 0.7" in q for q in quotes(sent))


def test_a_document_without_back_matter_tables_is_sent_exactly_as_with_the_flag_off(
    fresh, monkeypatch
):
    text = TEXT.split("\nTable 9")[0] + "\n[2] B. Author, Glaze studies, 2001.\n"
    off, on = fresh(), fresh()
    a = requests_for(off, monkeypatch, submitted(off, text))
    b = requests_for(on, monkeypatch, submitted(on, text), FLAG)
    assert a and json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


VANCOUVER = (
    "Synthetic Tile Study\n"
    "II. Test Article\nThe Glazed Floor Tile was fired at 1200 C.\n"
    "References\n"
    "Arden P, Brook Q. Kiln tests. Kiln J 1990;12:33-40.\n"
    "\n"
    "Table 9: Crack widths\n"
    "Plate A 0.4 mm\n"
    "Plate B 0.7 mm\n"
    "Cole R, Dane S. Glaze studies. Kiln J 2001;3:1-9.\n"
    "Eve T (1999) More glaze work 14.\n"
)


def test_flag_on_vancouver_references_after_the_table_are_never_sent(fresh, monkeypatch):
    service = fresh()
    sent = requests_for(service, monkeypatch, submitted(service, VANCOUVER), FLAG)
    assert any("Plate B 0.7" in q for q in quotes(sent))
    blob = json.dumps(sent)
    assert "Cole R" not in blob and "Eve T" not in blob and "Arden P" not in blob
