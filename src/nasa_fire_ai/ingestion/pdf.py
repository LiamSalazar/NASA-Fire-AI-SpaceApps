from pathlib import Path

import pymupdf

# An optional-package advertisement must not precede the runtime CLI's JSON.
# This suppresses that notice only; PDF errors and extraction limits stay visible.
if hasattr(pymupdf, "no_recommend_layout"):
    pymupdf.no_recommend_layout()


def extract_pdf(path: Path):
    with pymupdf.open(path) as doc:
        return [(i + 1, page.get_text("text")) for i, page in enumerate(doc)]


def extract_pdf_tables(path: Path, page_numbers=None):
    """Preserve detected cells and physical locators; scientific interpretation stays staged."""
    tables = []
    with pymupdf.open(path) as doc:
        for index, page in enumerate(doc):
            if page_numbers is not None and index + 1 not in page_numbers:
                continue
            for table in page.find_tables().tables:
                tables.append(
                    {
                        "physical_pdf_page": index + 1,
                        "page_status": "VERIFIED_FROM_PDF_INDEX",
                        "bbox": list(table.bbox),
                        "cells": table.extract(),
                        "cell_bboxes": [list(cell) if cell else None for cell in table.cells],
                        "header": table.header.names,
                        "header_external": table.header.external,
                        "publication_status": "REVIEW_REQUIRED",
                        "limits": "Layout extraction does not approve column roles, units or measurements.",
                    }
                )
    return tables
