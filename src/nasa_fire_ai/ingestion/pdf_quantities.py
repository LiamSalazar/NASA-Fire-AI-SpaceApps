"""Review-only original PDF numeric cells; no scientific mapping or execution."""

import re

from nasa_fire_ai.ingestion.document_structure import identity, table_records


def original_table_unit(header, row):
    """Recognize literal unit syntax in either axis, without converting values."""
    prefix = r"(?:da|[yzafpnumµμcdhkMGTPEZY])?"
    base = r"(?:mol|kat|Hz|Pa|Wb|lm|lx|Bq|Gy|Sv|cd|m|g|s|A|K|N|J|W|C|V|F|Ω|S|T|H)"
    atom = rf"{prefix}{base}(?:\^?[-+]?\d+|[²³])?"
    syntax = rf"(?:{atom}(?:[/*· ]{atom})*|%|ppm|fraction|RPM|psia|Wh|Ah|Whr|Ahr|seconds?|minutes?|hours?)"
    label = row[0].get("original_value") if row else None
    candidates = []
    for axis, text in [("column", header), ("row", label or "")]:
        for match in re.finditer(r"\(([^()]+)\)", text):
            literal = match.group(1)
            candidates.append(
                {
                    "axis": axis,
                    "literal": literal,
                    "recognized_unit_syntax": bool(re.fullmatch(syntax, literal.strip())),
                }
            )
    # A percent sign glued to a quantity symbol ("O2%", "wt%") states the column's
    # unit; a number with a percent sign ("95% confidence") is a value, not a unit.
    for match in re.finditer(r"(?<!\S)\S*[A-Za-z]\S*?%(?=[\s)]|$)", header or ""):
        candidates.append(
            {
                "axis": "column",
                "literal": "%",
                "recognized_unit_syntax": True,
                "basis": "PERCENT_GLUED_TO_QUANTITY_SYMBOL",
                "printed": match.group(0),
            }
        )
    units = {c["literal"] for c in candidates if c["recognized_unit_syntax"]}
    return (next(iter(units)) if len(units) == 1 else None), candidates


def column_header(row, column, document):
    """A column's printed header, including the text-only header rows below the first.

    A table may print a spanning title as its first row and the column names under
    it; every row above the cell's own row that holds no bare number is a header row.
    """
    tables = document.get("detected_tables") or []
    table = tables[row["table_index"]] if row["table_index"] < len(tables) else {}
    first = row["original_headers"][column] if column < len(row["original_headers"]) else None
    lines = [first or ""]
    if not table.get("header_external"):
        for above in (table.get("cells") or [])[1 : row["row_index"]]:
            if any(
                isinstance(c, str) and re.fullmatch(r"[^A-Za-z]*\d[^A-Za-z]*", c.strip())
                for c in above
            ):
                break
            if column < len(above) and above[column]:
                lines.append(above[column])
    return "\n".join(line for line in lines if line)


def header_unit_binding(expression, unit, spans, document):
    """Bind a table value to a unit stated literally in its own column header.

    A cell inherits a unit only from "(unit)", or a percent sign glued to the
    quantity symbol, in the header of the column that contains that exact original
    value on a supporting page. A unit elsewhere in
    the table, caption or text does not bind. No conversion happens here.
    """
    from nasa_fire_ai.ingestion.numeric_expressions import same_expression, same_unit

    pages = {s.get("page") for s in spans}
    for row in table_records(document):
        if row["kind"] != "STRUCTURED_TABLE_RECORD" or row["page"] not in pages:
            continue
        for cell in row["cells"]:
            value = (cell.get("original_value") or "").strip()
            if not value or not same_expression(value, expression):
                continue
            header = column_header(row, cell["column_index"], document)
            _, candidates = original_table_unit(header, [])
            if any(c["axis"] == "column" and same_unit(c["literal"], unit) for c in candidates):
                return {
                    "basis": "ORIGINAL_TABLE_COLUMN_HEADER_UNIT",
                    "original_column_header": header,
                    "page": row["page"],
                    "table_index": row["table_index"],
                    "row_index": row["row_index"],
                    "column_index": cell["column_index"],
                    "conversion": "NONE",
                }
    return None


def pdf_table_quantities(package, document):
    from nasa_fire_ai.ingestion.numeric_expressions import (
        decimal_convention,
        parse_numeric_expression,
    )
    from nasa_fire_ai.ingestion.study_attribution import reference_authors
    from nasa_fire_ai.ingestion.table_continuity import row_lineage, table_rows

    convention = decimal_convention("\n".join(e.get("text", "") for e in package["evidence"]))
    # The printed row group (material, batch) and its footnote lineage are kept
    # as review context; they do not resolve the cell's scientific scope.
    authors = reference_authors(document)
    groups = {
        (r["table_index"], r["row_index"]): {
            "group_label": r["group_label"],
            "group_label_original": r["group_label_original"],
            "footnote_marker": r["footnote_marker"],
            "footnote_legend": r["footnote_legend"],
            "table_caption": r["table_caption"],
            "continuation_of": r["continuation_of"],
            "cited_or_external_lineage": row_lineage(r, authors),
        }
        for r in table_rows(document)
    }
    result = []
    for row in table_records(document):
        if row["kind"] != "STRUCTURED_TABLE_RECORD":
            continue
        evidence = [
            e
            for e in package["evidence"]
            if e["checksum"] == row["input_sha256"] and e["page"] == row["page"]
        ]
        if len(evidence) != 1:
            continue
        e = evidence[0]
        role_cues = [
            {"quote": m.group(), "start": m.start(), "end": m.end()}
            for m in re.finditer(
                r"(?m)^[^\n]*(?:fits?|derived|derivative|calculated|estimated)[^\n]*$",
                e["text"],
                re.IGNORECASE,
            )
        ]
        for cell in row["cells"]:
            original = cell["original_value"]
            if not original:
                continue
            # Grouped thousands, ratios such as reactions/tests, signed and
            # annotated values stay preserved; syntax assigns no scientific role.
            numeric = parse_numeric_expression(
                original.strip(), convention=convention, table_cell=True
            )
            if numeric["status"] == "NOT_NUMERIC":
                continue
            header = cell.get("header") or ""
            unit, unit_candidates = original_table_unit(header, row["cells"])
            key = identity([row["id"], cell["column_index"], original, header])[:24]
            result.append(
                {
                    "id": "pdf-quantity-" + key,
                    "kind": "quantities",
                    "status": "UNRESOLVED",
                    "proposal": {
                        "expression": original,
                        "numeric_expression": numeric,
                        "unit": unit,
                        "original_unit_candidates": unit_candidates,
                        "original_column_header": header,
                        "original_row": row["cells"],
                        "original_row_group": groups.get((row["table_index"], row["row_index"])),
                        "original_page_heading": document.get("layout_headings", {})
                        .get(e["evidence_id"], {})
                        .get("quote"),
                        "original_role_cues": role_cues,
                        "epistemic": "UNRESOLVED_REVIEW_REQUIRED",
                        "subject": "UNRESOLVED_ORIGINAL_TABLE_ROW_COLUMN_SCOPE",
                    },
                    "reasons": [
                        "ORIGINAL_TABLE_QUANTITY_ROLE_AND_EXPERIMENTAL_SCOPE_REQUIRE_REVIEW"
                    ],
                    "support_spans": [
                        {
                            "evidence_id": e["evidence_id"],
                            "source_id": e["source_id"],
                            "checksum": e["checksum"],
                            "page": e["page"],
                            "start": 0,
                            "end": len(e["text"]),
                            "quote": e["text"],
                            "locator": {
                                "page": e["page"],
                                "table_index": row["table_index"],
                                "table_bbox": row["table_bbox"],
                                "row_index": row["row_index"],
                                "column_index": cell["column_index"],
                            },
                        }
                    ],
                    "source_table_record_id": row["id"],
                    "scientific_execution_asserted": False,
                    "scientific_approval": "NONE",
                    "global_vocabulary_activation": "NONE",
                    "native_quantity_representation": "DEFERRED_PRESERVED_ORIGINAL_TABLE_LITERAL",
                }
            )
    return result
