"""Structure-preserving source units in the existing evidence registry."""

import hashlib
import re
from pathlib import Path


def register_source_unit(registry, source_id, text, *, section, role="paragraph"):
    """Register an exact span of an existing raw document, never a paraphrase."""
    originals = registry.db.execute(
        "SELECT p.* FROM passages p JOIN documents d USING(document_id) "
        "WHERE d.source_id=? AND raw_file IS NOT NULL ORDER BY start_offset",
        (source_id,),
    ).fetchall()
    for original in originals:
        path = Path(original["raw_file"])
        if not path.is_absolute():
            path = Path(__file__).resolve().parents[3] / "data/raw" / path
        if not path.is_file():
            continue
        physical_page = None
        if path.suffix.lower() == ".pdf":
            import pymupdf

            with pymupdf.open(path) as pdf:
                pages = [(i + 1, p.get_text()) for i, p in enumerate(pdf)]
            matches = [(i, raw) for i, raw in pages if text in raw]
            if not matches:
                continue
            physical_page, raw = matches[0]
        elif path.suffix.lower() in {".txt", ".csv", ".html", ".json"}:
            raw = path.read_text(errors="strict")
        else:
            continue
        start = raw.find(text)
        if start < 0 or not text.strip():
            continue
        eid = "E-context-" + hashlib.sha256((source_id + "\0" + text).encode()).hexdigest()[:20]
        row = {
            "evidence_id": eid,
            "document_id": original["document_id"],
            "page": physical_page,
            "section": section,
            "text": text,
            "start_offset": start,
            "end_offset": start + len(text),
            "raw_file": str(path),
            "checksum": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        if registry.resolve(eid) is None:
            registry.add_passage(row)
            registry.add_evidence_location(
                eid,
                {
                    "unit_type": role,
                    "section": section,
                    "raw_text_start": start,
                    "raw_text_end": start + len(text),
                    "locator_status": "EXACT_RAW_TEXT_SPAN",
                    "physical_pdf_page": physical_page,
                },
            )
        return {
            "evidence_id": eid,
            "text": text,
            "role": role,
            "source_id": source_id,
            "section": section,
        }
    raise ValueError("source unit is not an exact span in the registered source")


def reconstruct_structure(registry, source_id):
    """Retain section transitions and original offsets for selective context windows."""
    row = registry.db.execute(
        "SELECT raw_file FROM passages p JOIN documents d USING(document_id) "
        "WHERE source_id=? AND raw_file LIKE '%.txt' LIMIT 1",
        (source_id,),
    ).fetchone()
    if not row:
        return []
    text = Path(row[0]).read_text()
    heading = re.compile(
        r"(?m)^(?:\d+(?:\.\d+)*\s+[A-Z][^\n]{3,110}|Appendix [A-Z][^\n]*|TABLE [A-Z]?\.?\d+[^\n]*|Summary and Conclusions|Approach|Status|Objectives|Experimental Results)\s*$"
    )
    return [
        {
            "title": m.group(0),
            "start_offset": m.start(),
            "end_offset": m.end(),
            "source_id": source_id,
            "unit_type": "section",
        }
        for m in heading.finditer(text)
    ]
