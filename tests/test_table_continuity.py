"""Synthetic table continuity, row groups, footnote lineage and row binding; never NASA data."""

import copy

from nasa_fire_ai.ingestion.table_continuity import (
    group_lineage,
    header_names,
    label_variants,
    link_continuation_tables,
    printed_label_forms,
    row_group_identity,
    table_cell_spans,
    table_region_rows,
    table_row_binding,
    table_rows,
)


def printed(cells):
    """Cell values as a PDF page prints them, one per line."""
    return "\n".join(value for row in cells for value in row)


HEADER = ["Material", "Energy (J)", "Condition", "Pressure (kPa)", "Outcomes"]


def table(page, cells, header=None):
    return {
        "input_sha256": "abc",
        "physical_pdf_page": page,
        "bbox": [0, 0, 10, 10],
        "header": header or cells[0],
        "header_external": False,
        "cells": cells,
    }


def document(pages, tables, references=""):
    segments = [
        {"evidence_id": f"E{page}", "source_id": "S", "page": page, "text": text}
        for page, text in pages.items()
    ]
    sections = []
    if references:
        last = max(pages)
        segments.append(
            {"evidence_id": "R", "source_id": "S", "page": last + 1, "text": references}
        )
        sections.append(
            {"evidence_id": "R", "source_id": "S", "start": 0, "end": 10, "title": "References"}
        )
    return {
        "segments": segments,
        "sections": sections,
        "detected_tables": link_continuation_tables(tables),
    }


def two_page_table():
    first = table(
        1,
        [
            HEADER,
            ["aAlpha (Lot 1)", "10", "Wet", "100", "0/20"],
            ["", "10", "Dry", "200", "1/20"],
        ],
    )
    second = table(
        2,
        [
            ["", "10", "Dry", "300", "2/20"],
            ["aBeta", "12", "Wet", "100", "0/20"],
            ["", "12", "Wet", "100", "0/10"],
        ],
    )
    pages = {
        1: "TABLE 1— Synthetic impact data\n" + printed(first["cells"]),
        2: printed(second["cells"]) + "\na-\nSynthetic standard MSFC\n",
    }
    return document(pages, [first, second])


def test_data_first_table_inherits_header_of_the_table_it_continues():
    doc = two_page_table()
    second = doc["detected_tables"][1]
    assert second["header_external"] and second["header"] == HEADER
    assert second["continuation_of"]["physical_pdf_page"] == 1
    # Linking again changes nothing.
    assert link_continuation_tables(doc["detected_tables"]) == doc["detected_tables"]


def test_different_columns_or_a_real_header_is_not_a_continuation():
    first = table(1, [HEADER, ["Alpha", "10", "Wet", "100", "0/20"]])
    narrower = table(2, [["10", "Wet", "100"], ["12", "Dry", "200"]])
    headed = table(2, [["Other", "Name", "Kind", "Note", "Remark"], ["x", "y", "z", "w", "v"]])
    for candidate in (narrower, headed):
        linked = link_continuation_tables([first, candidate])
        assert not linked[1].get("continuation_of")


def test_group_label_carries_down_across_a_continuation_with_legend_backed_marker():
    rows = table_rows(two_page_table())
    alpha = [r for r in rows if r["group_label"] == "Alpha (Lot 1)"]
    assert [r["page"] for r in alpha] == [1, 1, 2]
    assert {r["footnote_marker"] for r in alpha} == {"a"}
    assert alpha[0]["footnote_legend"] == ["Synthetic standard MSFC"]


def test_lowercase_prefix_without_a_printed_legend_is_part_of_the_label():
    doc = two_page_table()
    for segment in doc["segments"]:
        segment["text"] = segment["text"].replace("a-\nSynthetic standard MSFC\n", "")
    labels = {r["group_label"] for r in table_rows(doc)}
    assert "aAlpha (Lot 1)" in labels and "Alpha (Lot 1)" not in labels


def test_label_variants_ignore_pdf_spacing_and_strip_only_backed_markers():
    doc = two_page_table()
    assert label_variants("aAlpha  (Lot 1)", doc) == ["aAlpha  (Lot 1)", "Alpha (Lot 1)"]
    assert label_variants("Gamma", doc) == ["Gamma"]


def test_row_binding_unique_ambiguous_and_group_constant():
    doc = two_page_table()
    unique = table_row_binding(["Alpha (Lot 1)"], "300", "kPa", {1, 2}, doc)
    assert unique["status"] == "UNIQUE"
    assert unique["rows"][0]["row_context"]["Condition"] == "Dry"
    assert unique["rows"][0]["continuation_of"]["physical_pdf_page"] == 1
    assert table_row_binding(["Alpha (Lot 1)"], "999", "kPa", {1, 2}, doc) is None
    constant = table_row_binding(["Beta"], "100", "kPa", {2}, doc)
    assert constant["status"] == "GROUP_CONSTANT"
    energy = table_row_binding(["Alpha (Lot 1)"], "10", "J", {1, 2}, doc)
    assert energy["status"] == "GROUP_CONSTANT" and len(energy["rows"]) == 3
    outcome = table_row_binding(["Beta"], "0/20", None, {2}, doc)
    assert outcome["status"] == "UNIQUE"
    # Two of three Beta rows at 100 kPa: which test row is meant is not established.
    split = copy.deepcopy(doc)
    split["detected_tables"][1]["cells"].append(["", "12", "Dry", "200", "1/10"])
    assert table_row_binding(["Beta"], "100", "kPa", {2}, split)["status"] == "AMBIGUOUS"


def test_row_binding_never_crosses_groups_or_unsupported_pages():
    doc = two_page_table()
    assert table_row_binding(["Beta"], "200", "kPa", {1, 2}, doc) is None
    assert table_row_binding(["Alpha (Lot 1)"], "300", "kPa", {1}, doc) is None


def test_renaming_a_group_consistently_preserves_its_binding():
    doc = two_page_table()
    renamed = copy.deepcopy(doc)
    for t in renamed["detected_tables"]:
        for row in t["cells"]:
            row[0] = row[0].replace("Beta", "Delta")
    for segment in renamed["segments"]:
        segment["text"] = segment["text"].replace("Beta", "Delta")
    before = table_row_binding(["Beta"], "0/10", None, {2}, doc)
    after = table_row_binding(["Delta"], "0/10", None, {2}, renamed)
    assert before["status"] == after["status"] == "UNIQUE"
    assert before["rows"][0]["row_index"] == after["rows"][0]["row_index"]


def test_legends_belong_to_the_table_printed_with_them():
    one = table(5, [HEADER, ["aAlpha", "10", "Wet", "100", "0/20"]])
    two = table(5, [HEADER, ["aBeta", "12", "Dry", "200", "1/20"]])
    text = (
        "TABLE 1— First\n"
        + printed(one["cells"])
        + "\na-\nDetermined by lab one\nTABLE 2— Second [4]\n"
        + printed(two["cells"])
        + "\na-\nObtained from a database\n"
    )
    doc = document({5: text}, [one, two])
    legends = {r["group_label"]: r["footnote_legend"] for r in table_rows(doc)}
    assert legends == {"Alpha": ["Determined by lab one"], "Beta": ["Obtained from a database"]}


def test_lineage_is_cited_only_from_caption_citation_author_legend_or_external_source():
    current = table(3, [HEADER, ["bAlpha", "10", "Wet", "100", "0/20"]])
    cited = table(
        3, [HEADER, ["aBeta", "10", "Wet", "100", "0/20"], ["bAlpha", "9", "Dry", "90", "0/5"]]
    )
    text = (
        "TABLE 1— Current tests\n"
        + printed(current["cells"])
        + "\nb-\nSynthetic standard MSFC\nTABLE 2— Comparison\n"
        + printed(cited["cells"])
        + "\na-\nASTM data of Smith and Jones\nb-\nSynthetic standard MSFC\n"
    )
    refs = "References\n[1] Smith, A. B. and Jones, C., “Synthetic paper,” 1999.\n"
    doc = document({3: text}, [current, cited], references=refs)
    assert group_lineage(["Beta"], doc)["status"] == "CITED_OR_EXTERNAL_ONLY"
    assert group_lineage(["Alpha"], doc)["status"] == "NOT_CONTRADICTED"
    assert group_lineage(["Gamma"], doc) is None
    # Without the reference list the legend names no known author.
    assert group_lineage(["Beta"], document({3: text}, [current, cited]))["status"] == (
        "NOT_CONTRADICTED"
    )


def test_header_names_the_variable_without_partial_matches():
    assert header_names("Reactions/Tests", "Reactions/\nTests")
    assert header_names("impact energy", "Impact Energy (ft-lbs/J)")
    assert not header_names("Test", "Test Conditions")
    assert not header_names("", "Energy (J)")


def test_cell_spans_locate_a_value_only_inside_its_unique_row():
    doc = two_page_table()
    binding = table_row_binding(["Alpha (Lot 1)"], "300", "kPa", {2}, doc)
    page = {"evidence_id": "E2", "start": 0, "quote": doc["segments"][1]["text"]}
    [cell] = table_cell_spans(binding["rows"], [page])
    assert cell["quote"] == "300" and page["quote"][cell["start"] : cell["end"]] == "300"
    duplicated = {**page, "quote": page["quote"] + "\n" + page["quote"]}
    assert table_cell_spans(binding["rows"], [duplicated]) == []


def test_table_region_is_whole_printed_rows_not_prose():
    doc = two_page_table()
    rows_text = printed(doc["detected_tables"][1]["cells"])
    assert table_region_rows(rows_text, doc)
    assert not table_region_rows("Beta was tested at 100 kPa with no reactions.", doc)


def test_row_group_identity_is_found_from_either_printed_form():
    doc = two_page_table()
    for label in ("aAlpha (Lot 1)", "Alpha (Lot 1)", "Alpha  (Lot 1)"):
        identity = row_group_identity(label, doc)
        assert identity["group_label"] == "Alpha (Lot 1)"
        assert identity["group_label_original"] == "aAlpha (Lot 1)"
        assert identity["footnote_marker"] == "a"
        assert identity["footnote_legend"] == ["Synthetic standard MSFC"]
    assert row_group_identity("Gamma", doc) is None
    assert printed_label_forms("Alpha (Lot 1)", doc) == ["Alpha (Lot 1)", "aAlpha (Lot 1)"]
    assert printed_label_forms("aAlpha (Lot 1)", doc) == ["aAlpha (Lot 1)", "Alpha (Lot 1)"]
    assert printed_label_forms("Gamma", doc) == ["Gamma"]


def test_without_a_legend_the_letter_stays_part_of_the_printed_name():
    doc = two_page_table()
    for segment in doc["segments"]:
        segment["text"] = segment["text"].replace("a-\nSynthetic standard MSFC\n", "")
    identity = row_group_identity("aAlpha (Lot 1)", doc)
    assert identity["group_label"] == "aAlpha (Lot 1)" and identity["footnote_marker"] is None
    assert row_group_identity("Alpha (Lot 1)", doc) is None
