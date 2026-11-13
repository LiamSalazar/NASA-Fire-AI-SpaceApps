"""Source-grounded table continuity: continuation headers, row groups and row binding.

Detected PDF tables are kept as extracted. This module only interprets their
layout from evidence that the document itself prints:

* A table whose first row is data, and that directly follows a table with the
  same columns and a real header, continues that table and inherits its header.
* A row whose label cell is empty belongs to the group named above it, also
  across a continuation.
* A leading lowercase letter in a label cell is a footnote marker only when the
  text printed with that table has a legend line for that letter
  ("a- NASA-STD 6001 MSFC").
* A table's lineage is cited or external only when its own caption cites a
  reference ("[4]"), or its footnote legend names an author of the document's
  own reference list or says the data were obtained from elsewhere.

Nothing here assigns scientific roles, conditions or experimental execution.
"""

import os
import re
from itertools import pairwise

from nasa_fire_ai.ingestion.numeric_expressions import (
    parse_numeric_expression,
    same_expression,
    split_embedded_unit,
)
from nasa_fire_ai.ingestion.study_attribution import reference_authors

LEGEND = re.compile(r"(?m)^[ \t]*([a-z])[ \t]*[-–—][ \t]*\n?[ \t]*(\S[^\n]*)")
CAPTION = re.compile(r"(?m)^[ \t]*(?:TABLE|Table)[ \t]+(?:\d+|[IVX]+)[ \t]*(?:[—–:.|-][^\n]*|$)")
CITATION = re.compile(r"\[\d+(?:\s*[,–-]\s*\d+)*\]")
EXTERNAL = re.compile(
    r"\b(?:obtained|taken|adapted|reproduced|compiled|extracted)\s+from\b|\bcourtesy\s+of\b",
    re.IGNORECASE,
)


def _width(row):
    """Column count without trailing empty cells."""
    values = list(row)
    while values and not (values[-1] or "").strip():
        values.pop()
    return len(values)


def _data_like(row):
    """Share of non-empty cells that are numeric or value-with-unit expressions."""
    cells = [(c or "").strip() for c in row if (c or "").strip()]
    if not cells:
        return 0.0
    numeric = 0
    for cell in cells:
        text = re.sub(r"\s+", " ", cell)
        if (
            parse_numeric_expression(text, table_cell=True)["status"] != "NOT_NUMERIC"
            or (split_embedded_unit(text, None) or {}).get("status") == "SPLIT"
        ):
            numeric += 1
    return numeric / len(cells)


def link_continuation_tables(tables):
    """Give a continuation table the header of the table it continues.

    Returns new table dicts; inputs are not modified. A continuation must:
    follow the previous detected table of the same input on the same or the
    next physical page, have the same column count, start with a data-like row,
    and continue a table whose own header row is not data-like.
    """
    result = []
    previous = None
    for table in tables:
        table = dict(table)
        if "cells" in table and table.get("cells"):
            first = table["cells"][0]
            if table.get("continuation_of"):
                pass  # Already linked; linking again changes nothing.
            elif (
                previous is not None
                and previous.get("input_sha256") == table.get("input_sha256")
                and 0 <= table["physical_pdf_page"] - previous["physical_pdf_page"] <= 1
                and _width(first) == _width(previous["header"])
                and _data_like(first) >= 0.5
                and _data_like(previous["header"]) < 0.25
            ):
                inherited = list(previous["header"])[: len(first)]
                table["detected_header"] = table["header"]
                table["header"] = inherited + [""] * (len(first) - len(inherited))
                table["header_external"] = True
                table["continuation_of"] = {
                    "physical_pdf_page": previous["physical_pdf_page"],
                    "bbox": previous["bbox"],
                    "basis": "SAME_COLUMNS_DATA_FIRST_ROW_AFTER_HEADED_TABLE",
                }
            previous = table
        result.append(table)
    return result


def _page_text(document, page):
    return "\n".join(
        s.get("text", "") for s in document.get("segments", []) if s.get("page") == page
    )


def _legend_lines(text):
    letters = {}
    for match in LEGEND.finditer(text):
        letters.setdefault(match.group(1), []).append(match.group(2).strip())
    return letters


def _key(text):
    """Label identity that ignores PDF spacing artifacts ("Kel-F ® 8 1")."""
    return re.sub(r"\s+", "", text or "").lower()


def _norm(text):
    return re.sub(r"\s+", " ", (text or "")).strip().lower()


def split_marker(label, legend_letters):
    """Split a printed footnote marker from a label only when its legend exists."""
    text = (label or "").strip()
    if len(text) == 1 and text in legend_letters:
        return "", text
    match = re.match(r"^([a-z])(?=[A-Z0-9])", text)
    if match and match.group(1) in legend_letters:
        return text[1:].strip(), match.group(1)
    return text, None


def _chains(tables):
    """A table and its continuations form one chain of table indexes."""
    chains = []
    for index, table in enumerate(tables):
        if "cells" not in table or not table.get("cells"):
            continue
        if table.get("continuation_of") and chains and index - 1 in chains[-1]:
            chains[-1].append(index)
        else:
            chains.append([index])
    return chains


def _table_texts(document, tables):
    """The caption and page text printed with each table.

    A page's text is cut at each table caption. When the page's chain-starting
    tables match its captions one to one (a continuation can only precede the
    first caption), each table gets its own piece; otherwise every table on the
    page keeps the whole page text and no caption.
    """
    by_page = {}
    for chain in _chains(tables):
        for index in chain:
            by_page.setdefault(tables[index]["physical_pdf_page"], []).append(index)
    result = {}
    for page, indexes in by_page.items():
        text = _page_text(document, page)
        captions = list(CAPTION.finditer(text))
        bounds = [0, *[m.start() for m in captions], len(text)]
        pieces = [text[a:b] for a, b in pairwise(bounds)]
        starts = [i for i in indexes if not tables[i].get("continuation_of")]
        heads = [i for i in indexes if tables[i].get("continuation_of")]
        if (
            len(starts) == len(captions)
            and len(heads) <= 1
            and (not heads or heads[0] == indexes[0])
        ):
            for index in heads:
                result[index] = {"caption": None, "text": pieces[0], "scoped": True}
            for number, index in enumerate(starts):
                result[index] = {
                    "caption": captions[number].group().strip(),
                    "text": pieces[number + 1],
                    "scoped": True,
                }
        else:
            for index in indexes:
                result[index] = {"caption": None, "text": text, "scoped": False}
    return result


_ROWS_CACHE = {}


def table_rows(document):
    """Data rows of every detected table with their group label and marker.

    The first column names a row's group (material, specimen, batch). An empty
    or marker-only first cell inherits the group above it, including from the
    table a continuation table continues. Validation asks for the rows of one
    document many times, so the result is kept while that table list is alive.
    """
    tables = document.get("detected_tables", [])
    segments = document.get("segments", [])
    levels = derived_column_header_enabled()
    cached = _ROWS_CACHE.get(id(tables))
    if cached and cached[0] is tables and cached[1] is segments and cached[3] == levels:
        return cached[2]
    rows = _table_rows(tables, document)
    if len(_ROWS_CACHE) >= 8:
        _ROWS_CACHE.pop(next(iter(_ROWS_CACHE)))
    _ROWS_CACHE[id(tables)] = (tables, segments, rows, levels)
    return rows


def derived_column_header_enabled():
    """SCIENCE_TABLE_DERIVED_COLUMN_HEADER (on by default; "0" turns it off): multi-row column headers."""
    return os.getenv("SCIENCE_TABLE_DERIVED_COLUMN_HEADER", "1") != "0"


def column_header_levels(table):
    """Per column of a table, its header read from every header row (the one source).

    Header rows are the first printed row plus the rows right under it that hold no
    bare number and no row label. A column's leaf is its last non-empty header cell;
    the cells above it (a spanning title is carried over the empty cells to its right)
    are ancestors. A leaf printed in several columns is "repeated" and is told apart
    only by the nearest ancestor, when that differs between them.
    """
    first = table["header"]
    rows = [first]
    if not table.get("header_external"):
        for below in table["cells"][1:]:
            if any(
                isinstance(c, str) and re.fullmatch(r"[^A-Za-z]*\d[^A-Za-z]*", c.strip())
                for c in below
            ) or (below[0] if below else None):
                break
            rows.append(below)
    width = max(len(r) for r in rows)
    filled = []
    for r in rows:
        carried, out = None, []
        for i in range(width):
            text = (r[i] if i < len(r) else None) or ""
            if text.strip():
                carried = text
            out.append(text if text.strip() else (carried if i > 0 else ""))
        filled.append(out)
    columns = []
    for i in range(width):
        raw = [(r[i] if i < len(r) else None) for r in rows]
        own = [k for k, v in enumerate(raw) if (v or "").strip()]
        if len(rows) == 1 or not own or i == 0:
            columns.append({"leaf": first[i] if i < len(first) else None, "ancestors": []})
            continue
        leaf_row = own[-1]
        ancestors = [filled[k][i] for k in range(leaf_row) if filled[k][i].strip()]
        columns.append({"leaf": raw[leaf_row], "ancestors": ancestors})
    for i, column in enumerate(columns):
        same = [
            j for j, o in enumerate(columns) if j > 0 and _key(o["leaf"]) == _key(column["leaf"])
        ]
        column["repeated"] = i > 0 and bool(_key(column["leaf"])) and len(same) > 1
        qualifier = column["ancestors"][-1] if column["ancestors"] else None
        column["qualifier"] = qualifier
        column["qualifier_distinct"] = bool(qualifier) and all(
            j == i
            or not columns[j]["ancestors"]
            or _key(columns[j]["ancestors"][-1]) != _key(qualifier)
            for j in same
        )
        column["head"] = _head(column["leaf"])
    for i, column in enumerate(columns):
        column["head_unique"] = (
            i > 0
            and bool(_key(column["head"]))
            and all(
                j == i or _key(o["head"]) != _key(column["head"])
                for j, o in enumerate(columns)
                if j > 0
            )
        )
    return columns


_HEAD_CUT = re.compile(r"\s+(?:for|at|with|under|versus|vs\.?|per|in)\s", re.IGNORECASE)


def _head(leaf):
    """A leaf's defined head: without parenthetical groups and the phrase from a preposition."""
    bare = re.sub(r"\([^()]*\)", " ", leaf or "")
    return _HEAD_CUT.split(" " + bare + " ", 1)[0].strip()


def _table_rows(tables, document):
    texts = _table_texts(document, tables)
    rows = []
    for chain in _chains(tables):
        legend, scoped = {}, True
        for index in chain:
            scoped = scoped and texts[index]["scoped"]
            for letter, meanings in _legend_lines(texts[index]["text"]).items():
                legend.setdefault(letter, []).extend(
                    m for m in meanings if m not in legend.get(letter, [])
                )
        caption = texts[chain[0]]["caption"]
        carried = None
        for index in chain:
            table = tables[index]
            header = table["header"]
            levels = column_header_levels(table) if derived_column_header_enabled() else None
            data = table["cells"] if table.get("header_external") else table["cells"][1:]
            for row_index, row in enumerate(data):
                label, marker = split_marker(row[0] if row else "", legend)
                if label:
                    carried = {"label": label, "original": (row[0] or "").strip(), "marker": marker}
                elif carried is not None and marker:
                    carried = {**carried, "marker": marker}
                group = carried
                rows.append(
                    {
                        "table_index": index,
                        "page": table["physical_pdf_page"],
                        "row_index": row_index + 1,
                        "continuation_of": table.get("continuation_of"),
                        "table_caption": caption,
                        "legend_scope": "TABLE_TEXT" if scoped else "WHOLE_PAGE",
                        "group_label": group["label"] if group else None,
                        "group_label_original": group["original"] if group else None,
                        "footnote_marker": group["marker"] if group else None,
                        "footnote_legend": legend.get(group["marker"])
                        if group and group["marker"]
                        else None,
                        "cells": [
                            _header_cell(i, value, header, levels) for i, value in enumerate(row)
                        ],
                    }
                )
    return rows


def _header_cell(i, value, header, levels):
    cell = {
        "column_index": i,
        "header": header[i] if i < len(header) else None,
        "original_value": value,
    }
    if levels is not None and i < len(levels):
        level = levels[i]
        cell["header"] = level["leaf"]
        cell["header_levels"] = {
            k: level[k]
            for k in (
                "ancestors",
                "repeated",
                "qualifier",
                "qualifier_distinct",
                "head",
                "head_unique",
            )
        }
    return cell


def row_lineage(row, authors):
    """Why a table row's data are cited or external, from the printed table."""
    evidence = []
    caption = row.get("table_caption") or ""
    if CITATION.search(caption):
        evidence.append({"basis": "TABLE_CAPTION_CITES_REFERENCE", "quote": caption})
    for meaning in row.get("footnote_legend") or []:
        named = sorted(a for a in authors if re.search(rf"\b{re.escape(a)}\b", meaning))
        if named or CITATION.search(meaning):
            evidence.append(
                {"basis": "FOOTNOTE_NAMES_REFERENCE_AUTHOR", "quote": meaning, "authors": named}
            )
        elif EXTERNAL.search(meaning):
            evidence.append({"basis": "FOOTNOTE_STATES_EXTERNAL_SOURCE", "quote": meaning})
    return evidence


def group_lineage(labels, document):
    """Whether every table row of a group carries cited or external lineage.

    Returns None when the group has no table rows; otherwise a summary whose
    status is CITED_OR_EXTERNAL_ONLY, MIXED or NOT_CONTRADICTED.
    """
    wanted = {_key(v) for v in labels if v}
    authors = reference_authors(document)
    rows = [r for r in table_rows(document) if _key(r["group_label"]) in wanted]
    if not rows:
        return None
    flagged = [(r, row_lineage(r, authors)) for r in rows]
    cited = [(r, e) for r, e in flagged if e]
    status = (
        "CITED_OR_EXTERNAL_ONLY"
        if len(cited) == len(rows)
        else "MIXED"
        if cited
        else "NOT_CONTRADICTED"
    )
    return {
        "status": status,
        "row_count": len(rows),
        "cited_or_external_rows": len(cited),
        "evidence": [
            {
                "page": r["page"],
                "table_index": r["table_index"],
                "row_index": r["row_index"],
                "lineage": e,
            }
            for r, e in cited[:12]
        ],
    }


def row_group_identity(label, document):
    """The printed row group a label names, with or without its footnote marker.

    Returns None when no table prints the label as a row group; otherwise the
    marker-free group label, the form the page prints ("aAlpha (Lot 1)"), the
    legend-backed marker and its legend. Spacing artifacts are ignored.
    """
    for row in table_rows(document):
        if not row["group_label"]:
            continue
        if _key(row["group_label"]) == _key(label) or _key(row["group_label_original"]) == _key(
            label
        ):
            return {
                "group_label": row["group_label"],
                "group_label_original": row["group_label_original"],
                "footnote_marker": row["footnote_marker"],
                "footnote_legend": row["footnote_legend"],
                "page": row["page"],
                "table_index": row["table_index"],
            }
    return None


def printed_in_material_column(label, document):
    """Whether a table prints the label as a row group under a "Material" column."""
    return any(
        row["group_label"]
        and (
            _key(row["group_label"]) == _key(label)
            or _key(row["group_label_original"]) == _key(label)
        )
        and row["cells"]
        and re.search(r"\bmaterials?\b", row["cells"][0].get("header") or "", re.IGNORECASE)
        for row in table_rows(document)
    )


def printed_label_forms(label, document):
    """The label plus every way its row group is printed (with and without marker)."""
    forms = [label]
    identity = row_group_identity(label, document)
    for form in (identity["group_label_original"], identity["group_label"]) if identity else ():
        if form and _key(form) not in {_key(f) for f in forms}:
            forms.append(form)
    return forms


def label_variants(label, document):
    """The label itself plus its form without a legend-backed footnote marker."""
    identity = row_group_identity(label, document)
    if identity and _key(identity["group_label"]) != _key(label):
        return [label, identity["group_label"]]
    return [label]


def subject_column_for_value(group_labels, names, expression, unit, document):
    """The column header under which this document prints the same value for the subject.

    A prose sentence may restate a value of its own table without the variable's
    name ("It was struck with 60 J"). The value counts as named only when
    one of the subject's own rows, with no cited or external lineage, prints the
    same number in the same unit dimension under a header that names the label.
    Returns the matching rows' header/caption/page, or None.
    """
    from nasa_fire_ai.normalization.units import normalize

    try:
        wanted = normalize(1, unit or "")[1]
    except ValueError:
        return None
    keys = {_key(v) for v in group_labels if v}
    authors = reference_authors(document)
    found = []
    for row in table_rows(document):
        if _key(row["group_label"]) not in keys or row_lineage(row, authors):
            continue
        for cell in row["cells"]:
            header = cell["header"] or ""
            if names is not None and not any(
                header_names(n, header) or header_names(n, _unqualified(header)) for n in names
            ):
                continue
            header_unit = re.search(r"\(([^()]*)\)\s*$", header)
            for number, printed in re.findall(
                r"(?<![\w.])(\d[\d,]*(?:\.\d+)?)\s*([A-Za-z°%][\w°%/-]*)?",
                cell["original_value"] or "",
            ):
                if not same_expression(number, expression):
                    continue
                candidates = [printed] if printed else []
                if header_unit:
                    candidates += header_unit.group(1).split("/")
                for candidate in candidates:
                    try:
                        if normalize(1, candidate)[1] == wanted:
                            found.append(
                                {
                                    "page": row["page"],
                                    "column_header": header,
                                    "table_caption": row["table_caption"],
                                    "group_label": row["group_label"],
                                    "original_cell": cell["original_value"],
                                }
                            )
                            break
                    except ValueError:
                        continue
    return found or None


def _unqualified(header):
    """A header without leading state modifiers ("System Pressure" -> "Pressure")."""
    from nasa_fire_ai.ingestion.document_extraction import STATE_QUALIFIERS

    words = re.sub(r"\([^()]*\)", "", header or "").split()
    while len(words) > 1 and words[0].lower() in STATE_QUALIFIERS:
        words = words[1:]
    return " ".join(words)


def group_rows_printing(group_labels, text, document):
    """Rows of the subject's own groups, with no cited lineage, that print this cell text."""
    keys = {_key(v) for v in group_labels if v}
    wanted = _norm(text)
    authors = reference_authors(document)
    return [
        {
            "page": row["page"],
            "table_caption": row["table_caption"],
            "group_label": row["group_label"],
            "column_header": cell["header"],
            "original_cell": cell["original_value"],
        }
        for row in table_rows(document)
        if _key(row["group_label"]) in keys and not row_lineage(row, authors)
        for cell in row["cells"][1:]
        if wanted and _norm(cell["original_value"]) == wanted
    ]


def subject_columns_printing(group_labels, expression, unit, document):
    """Header names (unit removed) under which the subject's own rows print this value."""
    rows = subject_column_for_value(group_labels, None, expression, unit, document) or []
    return sorted({re.sub(r"\s*\([^()]*\)\s*$", "", r["column_header"]).strip() for r in rows})


def printed_in_table(document, page, text):
    """Whether a detected table on that page prints this exact text in one cell."""
    wanted = _norm(text)
    return bool(wanted) and any(
        wanted in _norm(cell)
        for table in document.get("detected_tables", [])
        if table.get("physical_pdf_page") == page
        for row in table.get("cells", [])
        for cell in row
    )


def material_row_labels(label, document):
    """Row-group labels printed for one named material, including a group that
    only adds a parenthetical to the name ("Kel-F® 81" → "Kel-F®81 (PCTFE)")."""
    labels = label_variants(label, document)
    stems = {_key(v) for v in labels}
    for row in table_rows(document):
        group = row["group_label"] or ""
        if any(_key(group).startswith(stem + "(") for stem in stems) and group not in labels:
            labels.append(group)
    return labels


def _cell_matches(cell, expression, unit):
    text = re.sub(r"\s+", " ", (cell or "").strip())
    if not text:
        return False
    if same_expression(text, expression):
        return True
    split = split_embedded_unit(text, unit)
    return bool(
        split
        and split.get("status") == "SPLIT"
        and same_expression(split["expression"], expression)
    )


def table_row_binding(subject_labels, expression, unit, pages, document):
    """Locate the table row(s) of a subject's group that hold an original value.

    Returns None when no row of that group on the supporting pages holds the
    value; otherwise a binding whose status is UNIQUE (one row), GROUP_CONSTANT
    (every row of the group holds it in the same column) or AMBIGUOUS (several
    rows but not all, so the row context, such as the test condition, is not
    established).
    """
    wanted = {_key(v) for v in subject_labels if v}
    rows = table_rows(document)
    authors = reference_authors(document)
    hits = []
    for row in rows:
        if row["page"] not in pages or _key(row["group_label"]) not in wanted:
            continue
        for cell in row["cells"][1:]:
            if _cell_matches(cell["original_value"], expression, unit):
                hits.append(
                    {
                        "page": row["page"],
                        "table_index": row["table_index"],
                        "row_index": row["row_index"],
                        "column_index": cell["column_index"],
                        "column_header": cell["header"],
                        **(
                            {"column_header_levels": cell["header_levels"]}
                            if "header_levels" in cell
                            else {}
                        ),
                        "group_label": row["group_label"],
                        "footnote_marker": row["footnote_marker"],
                        "footnote_legend": row["footnote_legend"],
                        "table_caption": row["table_caption"],
                        "continuation_of": row["continuation_of"],
                        "lineage": row_lineage(row, authors),
                        "row_values": [c["original_value"] for c in row["cells"]],
                        "row_context": {
                            (c["header"] or f"column {c['column_index']}").replace("\n", " "): c[
                                "original_value"
                            ]
                            for c in row["cells"]
                        },
                    }
                )
    if not hits:
        return None
    status = "UNIQUE" if len(hits) == 1 else "AMBIGUOUS"
    columns = {h["column_index"] for h in hits}
    if status == "AMBIGUOUS" and len(columns) == 1:
        # A value shared by every row of the group in that column (for example
        # the impact energy of all of a batch's rows) is a group-level value.
        column = next(iter(columns))
        group_values = [
            row["cells"][column]["original_value"] if column < len(row["cells"]) else ""
            for row in rows
            if _key(row["group_label"]) in wanted
        ]
        if group_values and all(_cell_matches(v, expression, unit) for v in group_values):
            status = "GROUP_CONSTANT"
    return {
        "basis": "ORIGINAL_TABLE_ROW_GROUP",
        "status": status,
        "rows": hits,
        "conversion": "NONE",
    }


def header_names(label, header):
    """Whether a quantity label is the variable named by a column header.

    Spacing, case, punctuation and the header's "(unit)" are ignored; a label
    that is only part of the header name ("Test" for "Test Conditions") is not.
    """

    def key(text):
        text = re.sub(r"\([^()]*\)", "", text or "")
        return re.sub(r"[^0-9a-z]", "", text.lower())

    return bool(key(label)) and key(label) == key(header)


def header_names_column(label, hit):
    """header_names for a bound cell read with multi-row headers (the flag path).

    The label is the column's whole leaf header, the leaf without leading state
    modifiers, or its head when that alone names one column; never an ancestor
    (spanning title). A leaf
    printed in several columns also needs the distinguishing ancestor in the label.
    """
    leaf = hit["column_header"] or ""
    levels = hit.get("column_header_levels")
    if levels and levels["repeated"]:
        # The same leaf is printed in several columns: the label must carry the
        # ancestor that tells this column from the others.
        qualifier = levels["qualifier"]
        return bool(
            levels["qualifier_distinct"]
            and (
                header_names(label, f"{qualifier} {leaf}")
                or header_names(label, f"{leaf} {qualifier}")
            )
        )
    if header_names(label, leaf) or header_names(label, _unqualified(leaf)):
        return True
    # A head (the leaf without its qualifiers, its unit included) names the column
    # only if, on its own, it identifies a single column of the table.
    return bool(levels and levels.get("head_unique") and header_names(label, levels["head"]))


def _sequence(values):
    """Regex for cell values printed consecutively, whatever the line breaks."""
    parts = [
        r"\s+".join(re.escape(word) for word in v.split()) for v in values if (v or "").strip()
    ]
    return r"\s*".join(parts)


def table_cell_spans(hits, spans):
    """Exact source spans of bound table cells, found from their whole row.

    A row's cells are printed consecutively on the page; the full row sequence
    must occur exactly once in a supporting quote, so a repeated value in
    another row is never located by mistake.
    """
    found = []
    for hit in hits:
        values = hit["row_values"]
        target = (values[hit["column_index"]] or "").strip()
        if not target:
            continue
        before = _sequence(values[: hit["column_index"]])
        pattern = (before + r"\s*" if before else "") + "(" + _sequence([target]) + ")"
        after = _sequence(values[hit["column_index"] + 1 :])
        pattern += r"\s*" + after if after else ""
        for span in spans:
            matches = list(re.finditer(pattern, span["quote"]))
            if len(matches) != 1:
                continue
            start, end = matches[0].span(1)
            found.append(
                {
                    "evidence_id": span["evidence_id"],
                    "start": span["start"] + start,
                    "end": span["start"] + end,
                    "quote": span["quote"][start:end],
                    "table_row": {
                        k: hit[k] for k in ("page", "table_index", "row_index", "column_index")
                    },
                }
            )
            break
    return found


def table_region_rows(text, document, minimum_cells=3):
    """Detected table rows printed in full inside a passage.

    A passage that reproduces whole table rows is table content, not a prose
    statement; its values belong to the table's own cell records.
    """
    found = []
    for row in table_rows(document):
        values = [v for v in (c["original_value"] for c in row["cells"]) if (v or "").strip()]
        if len(values) < minimum_cells:
            continue
        if re.search(_sequence(values), text or ""):
            found.append(
                {
                    "page": row["page"],
                    "table_index": row["table_index"],
                    "row_index": row["row_index"],
                }
            )
    return found
