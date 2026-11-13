"""Source reconstruction for review, without scientific publication authority."""

import csv
import hashlib
import io
import json
from pathlib import Path

from nasa_fire_ai.ingestion.structured_provenance import round_trip


def source_path(root, reported):
    if not reported:
        return None
    path = Path(reported)
    for candidate in (root / path, root / "data/raw" / path):
        if candidate.is_file():
            return candidate
    return None


def reconstruct_passage(evidence_id, registry, root):
    """Preserve exact registry text and independently round-trip available locators.

    CSV logical ordinals are never pages. Metadata URLs remain recorded URLs;
    file digest verification does not imply remote endpoint verification.
    """
    passage = registry.resolve(evidence_id)
    if passage is None:
        return {
            "evidence_id": evidence_id,
            "status": "MISSING_EVIDENCE",
            "limitations": ["Evidence identity absent from registry"],
        }
    source = registry.source_metadata(evidence_id)
    if source:
        registered = registry.db.execute(
            "SELECT * FROM sources WHERE source_id=?", (source["source_id"],)
        ).fetchone()
        source = dict(registered) if registered else source
    result = {
        "evidence_id": evidence_id,
        "registry_passage": passage,
        "source": source,
        "url_verification": "RECORDED_NASA_ENDPOINT; remote availability not checked",
        "limitations": [],
        "verified_location": None,
        "context_before": None,
        "context_after": None,
    }
    path = source_path(root, passage.get("raw_file"))
    checksum = passage.get("checksum")
    if path is None and source:
        path = source_path(root, source.get("filename"))
        checksum = source.get("sha256")
        result["file_resolution_basis"] = "Registered document source filename and digest"
    if path is None:
        result.update(status="MISSING_SOURCE")
        result["limitations"].append("Registered raw file unavailable")
        return result
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    result["raw_file"] = str(path.relative_to(root))
    result["sha256"] = digest
    result["file_digest_valid"] = digest == checksum
    if not result["file_digest_valid"]:
        result.update(status="CHECKSUM_MISMATCH")
        return result
    cells = passage.get("source_cells", [])
    if cells:
        failures = []
        for cell in cells:
            try:
                round_trip(cell, root)
            except (ValueError, OSError, IndexError) as error:
                failures.append(type(error).__name__)
        with path.open(encoding=cells[0]["encoding"], newline="") as handle:
            rows = list(csv.reader(handle))
        ordinal = cells[0]["row_ordinal"]
        result["structured_row"] = rows[ordinal - 1]
        result["original_headers"] = rows[0]
        # A source row can contain commas/newlines. Preserve the registry passage
        # separately and check its serialization instead of trusting offsets.
        buffer = io.StringIO()
        csv.writer(buffer, lineterminator="").writerow(rows[ordinal - 1])
        result["passage_content_valid"] = passage["text"] in {
            ",".join(rows[ordinal - 1]),
            buffer.getvalue(),
        }
        result["verified_location"] = {
            "kind": "CSV_LOGICAL_RECORD",
            "record_ordinal_including_header": ordinal,
            "columns": len(cells),
            "physical_pdf_page": None,
            "cell_round_trip_failures": failures,
        }
        result["context_before"] = rows[max(0, ordinal - 3) : ordinal - 1]
        result["context_after"] = rows[ordinal : ordinal + 2]
        result["status"] = (
            "VERIFIED" if not failures and result["passage_content_valid"] else "REVISE"
        )
        result["limitations"].append(
            "Table row is configuration/data; no observation or conclusion inferred"
        )
    elif path.suffix.lower() == ".pdf":
        import fitz

        location = passage.get("structured_location") or {}
        physical = location.get("physical_pdf_page")
        with fitz.open(path) as document:
            pages = []
            for index, page in enumerate(document):
                text = page.get_text()
                from nasa_fire_ai.ingestion.source_spans import recover_span

                for proposed in dict.fromkeys([passage["text"], passage["text"].removesuffix(".")]):
                    try:
                        span = recover_span(text, proposed)
                    except ValueError:
                        continue
                    pages.append((index + 1, text, span, proposed != passage["text"]))
                    break
            chosen = next((p for p in pages if p[0] == physical), None)
            if chosen is None and len(pages) == 1:
                chosen = pages[0]
            if chosen:
                result["verified_location"] = {"kind": "PDF", "physical_pdf_page": chosen[0]}
                result["source_page_text"] = chosen[1]
                result["exact_supporting_source_span"] = chosen[2]
                result["registry_terminal_period_added"] = chosen[3]
                if chosen[3]:
                    result["limitations"].append(
                        "Registry passage adds a terminal period absent from the original PDF; exact source span preserved separately"
                    )
                result["context_before"] = (
                    document[chosen[0] - 2].get_text() if chosen[0] > 1 else ""
                )
                result["context_after"] = (
                    document[chosen[0]].get_text() if chosen[0] < len(document) else ""
                )
                result["status"] = "VERIFIED"
            else:
                result["status"] = "PARTIAL"
                result["limitations"].append(
                    "Physical page not uniquely corroborated; extracted page is metadata only"
                )
    else:
        text = path.read_text(errors="strict")
        start = text.find(passage["text"])
        if start >= 0 and text.count(passage["text"]) == 1:
            end = start + len(passage["text"])
            result["verified_location"] = {
                "kind": "TEXT",
                "character_start": start,
                "character_end": end,
            }
            result["context_before"] = text[max(0, start - 1500) : start]
            result["context_after"] = text[end : end + 1500]
            result["status"] = "VERIFIED"
        else:
            result["status"] = "PARTIAL"
            result["limitations"].append("Exact unique source span unresolved")
    return result


def identity_record(candidate, store, records, passage_refs):
    """Evidence validity and graph applicability are separate review objects."""
    indexed = {r.get("id", r.get("statement_id")): r for r in records}
    run = indexed.get(candidate["id"])
    sample = indexed.get((run or {}).get("sample_id"))
    dependencies = [indexed[cid] for cid in (run or {}).get("condition_ids", []) if cid in indexed]
    conditions = {
        pid: [
            {**row, "value": row["value"].model_dump(mode="json")}
            for row in store.value_records(candidate["id"], pid)
        ]
        for pid in store.registry.properties
        if store.value_records(candidate["id"], pid)
    }
    return {
        "identity_id": candidate["id"],
        "candidate_id": candidate["id"],
        "evidence_ids": sorted(candidate["evidence_ids"]),
        "source_record_refs": passage_refs,
        "investigation_id": (run or {}).get("investigation_id"),
        "experimental_run_id": (run or {}).get("id"),
        "sample": sample,
        "original_run_record": run,
        "original_scientific_records": dependencies,
        "actual_material": sorted(store.relations(candidate["id"], "hasMaterial")),
        "actual_gravity": sorted(store.relations(candidate["id"], "hasGravityCondition")),
        "actual_phenomena": sorted(store.relations(candidate["id"], "hasPhenomenon")),
        "mapped_conditions": conditions,
        "epistemic_type": "SOURCE_REPORTED_EXPERIMENTAL_CONFIGURATION",
        "observations_or_conclusions": [],
        "technical_checks": {
            "experiment_identity_present": run is not None,
            "specimen_identity_present": sample is not None,
            "material_basis": "original sample label; canonical links do not assert polymer equivalence",
            "quantity_basis": "original record and raw cells retained; display settings not velocity",
            "independent_factual_integrity_judgment": None,
        },
        "limitations": [
            "Run configuration does not by itself establish combustion or suppression outcomes"
        ],
    }


def read_json(path):
    return json.loads(path.read_text())
