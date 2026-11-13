"""Evidence-bearing extraction coverage; character coverage is never scientific recall."""

import os
import re
from collections import Counter

from nasa_fire_ai.ingestion.document_structure import identity, table_records

CUES = re.compile(
    r"\b(?:tests?|experiments?|runs?|groups?|samples?|specimens?|measur\w*|observ\w*|"
    r"results?|conclu\w*|hypothes\w*|may|might|must|shall|except|extinct\w*|ignit\w*)\b",
    re.IGNORECASE,
)


def statement_candidates(package, document, validation):
    """Literal prose anchors requiring classification, never scientific gold.

    Coverage requires a matching statement text, not just a nearby support span
    or a documentary entity mentioning the same page.
    """
    from nasa_fire_ai.ingestion.document_extraction import normalized, source_anchors

    window = {"members": document["segments"]}
    anchors = source_anchors(window, {"anchors": []}, [], package)
    result = []
    for anchor in anchors.values():
        if not anchor.get("statement_eligible", True):
            continue
        text = anchor["quote"]
        if len(re.findall(r"[A-Za-z]{2,}", text)) < 5 or not CUES.search(text):
            continue
        if not re.search(
            r"\b(?:is|are|was|were|has|have|achieved|provides?|guide|observ\w*|measur\w*|increas\w*|decreas\w*|show\w*|conclud\w*|may|might|must|shall)\b",
            text,
            re.IGNORECASE,
        ):
            continue
        matching = [
            r
            for r in validation["records"]
            if r["kind"] == "statements"
            and r["status"] != "REJECTED"
            and normalized(text) in normalized(r["proposal"]["text"])
            and any(s["evidence_id"] == anchor["evidence_id"] for s in r["support_spans"])
        ]
        result.append(
            {
                **{k: anchor[k] for k in ("id", "evidence_id", "page", "start", "end", "quote")},
                "proposal_ids": [r["id"] for r in matching],
                "state": "RETAINED_STATEMENT" if matching else "NOT_STRUCTURED",
            }
        )
    return result


def coverage(package, document, validation, outcomes, table_quantities):
    from nasa_fire_ai.ingestion.document_extraction import quantity_expression_pattern

    # SI symbols and their prefixes are recognition syntax, not inferred NASA
    # measurements or ontology definitions. Original unit strings remain unchanged.
    prefix = r"(?:da|[yzafpnumµμcdhkMGTPEZY])?"
    base = r"(?:mol|kat|Hz|Pa|Wb|lm|lx|Bq|Gy|Sv|cd|m|g|s|A|K|N|J|W|C|V|F|Ω|S|T|H)"
    atom = rf"{prefix}{base}(?:(?:\^)?[-+]?\d+|[²³])?"
    si = rf"{atom}(?:[/*·]{atom})*"
    words = r"(?i:seconds?|minutes?|hours?|lit(?:er|re)s?|microns?|joules?|watts?|kelvins?|pascals?|percent|fraction|degC|degF)"
    units = rf"(?:RPM|psia|mmHg|°C|°F|%|{words}|{si})"
    literal_quantity = re.compile(
        rf"(?<![\w.])(?P<expression>{quantity_expression_pattern()})\s*[-‑]?\s*(?P<unit>{units})(?!\w)"
    )
    records = [r for r in validation["records"] if not r.get("duplicate_of")]
    prose = statement_candidates(package, document, validation)
    anchors = []
    for segment in document["segments"]:
        if re.search(r"references|acknowledg", segment["section"], re.IGNORECASE):
            continue
        text = segment["text"]
        quantities = [
            {
                "original_expression_with_unit": m.group(),
                "expression": m["expression"],
                "unit": m["unit"],
                "start": segment["start"] + m.start(),
                "end": segment["start"] + m.end(),
            }
            for m in literal_quantity.finditer(text)
        ]
        if (
            not quantities
            and not CUES.search(text)
            and not re.search(r"conclusion|outcome|finding", segment["section"], re.IGNORECASE)
        ):
            continue
        supporting = [
            r
            for r in records
            if any(
                s["evidence_id"] == segment["evidence_id"]
                and s["start"] < segment["end"]
                and s["end"] > segment["start"]
                for s in r["support_spans"]
            )
        ]
        states = Counter(r["status"] for r in supporting)
        for q in quantities:
            quantity_records = [
                r
                for r in supporting
                if r["kind"] == "quantities"
                and any(
                    s["evidence_id"] == segment["evidence_id"]
                    and s["start"] <= q["start"]
                    and s["end"] >= q["end"]
                    and r["proposal"]["expression"] in q["original_expression_with_unit"]
                    for s in r.get("quantity_value_spans", [])
                )
            ]
            q["proposal_ids"] = [r["id"] for r in quantity_records]
            q["source_supported_proposals"] = sum(
                r["status"] == "SOURCE_SUPPORTED" for r in quantity_records
            )
            q["unresolved_proposals"] = sum(r["status"] == "UNRESOLVED" for r in quantity_records)
            q["state"] = (
                "STRUCTURED_CANDIDATE"
                if any(
                    r["status"] != "REJECTED"
                    and r.get("native_scope_compatible", True)
                    and not r.get("scientific_role_conflict", False)
                    for r in quantity_records
                )
                else "NOT_STRUCTURED"
            )
        anchors.append(
            {
                "id": "coverage-"
                + identity([segment["evidence_id"], segment["start"], segment["end"]])[:20],
                **{
                    k: segment[k]
                    for k in ("evidence_id", "source_id", "page", "start", "end", "section")
                },
                "scientific_cues": CUES.findall(text),
                "quantity_inventory": quantities,
                "proposal_statuses": dict(states),
                "proposal_ids": [r["id"] for r in supporting],
                "state": "HAS_SOURCE_SUPPORTED_STRUCTURE"
                if states["SOURCE_SUPPORTED"]
                else "UNRESOLVED_STRUCTURE"
                if states["UNRESOLVED"]
                else "NOT_STRUCTURED",
            }
        )
    quantities = [q for a in anchors for q in a["quantity_inventory"]]
    # PDF tables often place units only in column headers. Retain their source
    # cells separately; adjacent-unit prose matching must not claim table recall.
    numeric_cells = []
    for row in table_records(document):
        for cell in row.get("cells", []):
            value = cell["original_value"]
            if not value or not re.fullmatch(quantity_expression_pattern(), value.strip()):
                continue
            header = cell.get("header") or ""
            unit = re.search(r"\(([^()]+)\)", header)
            numeric_cells.append(
                {
                    "table_record_id": row["id"],
                    "input_sha256": row["input_sha256"],
                    "page": row["page"],
                    "table_index": row["table_index"],
                    "row_index": row["row_index"],
                    "column_index": cell["column_index"],
                    "original_expression": value,
                    "original_column_header": header,
                    "header_unit_candidate": unit.group(1) if unit else None,
                    "original_row": row["cells"],
                    "table_bbox": row["table_bbox"],
                    "state": "SOURCE_CELL_RETAINED_SEMANTIC_SCOPE_UNRESOLVED",
                    "scientific_execution_asserted": False,
                }
            )
    outstanding = [
        a["id"]
        for a in anchors
        if a["state"] == "NOT_STRUCTURED"
        or any(q["state"] == "NOT_STRUCTURED" for q in a["quantity_inventory"])
    ]
    model_items = sum(o.get("proposed_items", 0) for o in outcomes)
    return {
        "basis": "Literal source-cue/quantity inventory plus independent proposal validation; NOT comprehensive scientific recall or expert gold",
        "read_content": document["coverage"],
        "scientific_content_identified": {
            "candidate_units": len(anchors),
            "literal_quantity_occurrences": len(quantities),
            "numeric_pdf_table_cells": len(numeric_cells),
        },
        "scientific_information_structured": dict(
            Counter(r["kind"] + ":" + r["status"] for r in records)
        ),
        "source_supported_relationships": sum(
            r["kind"] == "relations" and r["status"] == "SOURCE_SUPPORTED" for r in records
        ),
        "unresolved": sum(r["status"] == "UNRESOLVED" for r in records),
        "rejected": sum(r["status"] == "REJECTED" for r in records),
        "superseded_inference_variants": sum(
            bool(r.get("duplicate_of")) for r in validation["records"]
        ),
        "table_quantity_candidates": len(table_quantities),
        "pdf_table_quantity_inventory": numeric_cells,
        "native_quantity_representation_deferred": sum(
            r.get("native_value_compatible") is False for r in records
        ),
        "detected_quantity_occurrences_structured": sum(
            q["state"] == "STRUCTURED_CANDIDATE" for q in quantities
        ),
        "literal_proposition_candidates": prose,
        "unstructured_proposition_candidates": sum(p["state"] == "NOT_STRUCTURED" for p in prose),
        "model_proposed_items": model_items,
        "inaccessible_content": document["limitations"],
        "source_units": anchors,
        "outstanding_source_units": outstanding,
        "scientific_completeness": "NOT_ESTABLISHED"
        if not model_items
        else "SOURCE_ADJUDICATION_REQUIRED",
        "empty_model_is_scientific_success": False,
    }


# --- Missing facts (SCIENCE_MISSING_FACT_REPORT, report only) ---------------------------------------


def missing_fact_report_enabled():
    return os.getenv("SCIENCE_MISSING_FACT_REPORT", "0") == "1"


def missing_fact_report(records, candidates, document, evidence=None):
    """The printed terms of the body that no active record covers.

    A candidate is reported when its coverage is ``UNCOVERED`` and no active record (any status but
    REJECTED) has a support span over one of its occurrences or carries its label. It reports and
    never adds, changes or requests anything: ``{printed, evidence_id, start, coverage, qualifies,
    section, nearest_record_ids}`` for the first occurrence of each, with counts per source.
    ``evidence`` maps an evidence id to its source id (from the package).
    """
    from nasa_fire_ai.ingestion.printed_layout import section_for_span
    from nasa_fire_ai.ingestion.source_spans import normalized

    active = [r for r in records if r.get("status") != "REJECTED" and not r.get("duplicate_of")]
    spans = {}
    labels = set()
    for r in active:
        for span in r.get("support_spans") or []:
            spans.setdefault(span["evidence_id"], []).append((span["start"], span["end"], r["id"]))
        label = (r.get("proposal") or {}).get("label")
        if isinstance(label, str):
            labels.add(normalized(label))
    report = []
    for candidate in candidates:
        if candidate.get("coverage") != "UNCOVERED" or normalized(candidate["label"]) in labels:
            continue
        places = candidate.get("evidence") or []
        if not places or any(
            s < p["end"] and p["start"] < e
            for p in places
            for s, e, _ in spans.get(p["evidence_id"], [])
        ):
            continue
        first = places[0]
        near = sorted(
            spans.get(first["evidence_id"], []),
            key=lambda t: min(abs(t[0] - first["start"]), abs(t[1] - first["start"])),
        )[:3]
        report.append(
            {
                "printed": first["quote"],
                "evidence_id": first["evidence_id"],
                "start": first["start"],
                "coverage": candidate["coverage"],
                "qualifies": candidate.get("approved_term"),
                "section": section_for_span(first, document),
                "nearest_record_ids": [rid for _, _, rid in near],
                "source_id": (evidence or {}).get(first["evidence_id"]),
            }
        )
    per_source = {}
    for item in report:
        per_source[item["source_id"]] = per_source.get(item["source_id"], 0) + 1
    return {"count": len(report), "per_source": per_source, "items": report}
