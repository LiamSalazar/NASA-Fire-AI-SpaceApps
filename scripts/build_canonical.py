#!/usr/bin/env python3
"""Create traceable chunks and conservative canonical records from fetched material."""

import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion import extract_pdf
from nasa_fire_ai.ingestion.phase1 import stable_id

ROOT = Path(__file__).resolve().parents[1]
raw = ROOT / "data/raw"
canonical = ROOT / "data/canonical"
canonical.mkdir(parents=True, exist_ok=True)
manifest = json.loads((raw / "manifest.json").read_text())
reg = EvidenceRegistry(Settings().registry_path)
records = []
all_passages = []
for source in manifest:
    reg.add_source(
        {
            "source_id": source["source_id"],
            "source_type": source["source_type"],
            "nasa_id": source.get("nasa_identifier"),
            "title": source.get("title", source.get("document_id", source["source_id"])),
            "doi": source.get("doi"),
            "url": source.get("canonical_url"),
            "retrieved_at": source.get("retrieval_timestamp"),
            "filename": source.get("filename"),
            "sha256": source.get("sha256"),
            "mime_type": source.get("mime_type"),
            "status": source.get("status"),
        }
    )
    reg.add_document(
        source["source_id"],
        source["source_id"],
        source.get("title", source.get("document_id", source["source_id"])),
    )
    # Phase-1 artifacts have already passed the versioned segmenter during
    # ingestion. Re-segmenting them here used to create a competing identity
    # scheme; legacy seed sources continue through this compatibility path.
    if source.get("artifact_id"):
        continue
    if source.get("status") != "fetched":
        continue
    path = raw / source["filename"]
    source_passage_count = 0
    pages = (
        extract_pdf(path)
        if path.suffix == ".pdf"
        else [(1, re.sub("<[^>]+>", " ", path.read_text(errors="ignore")))]
    )
    for page, text in pages:
        text = " ".join(text.split())
        for start in range(0, len(text), 3600):
            chunk = text[start : start + 4000]
            if len(chunk) < 100:
                continue
            # Match the versioned document-segmentation identity.  This build
            # path must not manufacture a second FTS identity scheme.
            eid = stable_id(
                "E", source["source_id"], source["sha256"], "segment-v2", str(page), str(start)
            )
            row = {
                "evidence_id": eid,
                "document_id": source["source_id"],
                "page": page,
                "section": None,
                "text": chunk,
                "start_offset": start,
                "end_offset": start + len(chunk),
                "raw_file": source["filename"],
                "checksum": source["sha256"],
            }
            reg.add_passage(row)
            all_passages.append((source["source_id"], eid, chunk, page))
            source_passage_count += 1
    # NASA page shells can have no extractable experiment text. Retain only the
    # fetched source metadata as a traceable investigation identity record;
    # do not manufacture conditions, observations, or run rows from it.
    if source_passage_count == 0:
        eid = f"E-{source['source_id']}-metadata"
        text = f"NASA source metadata: {source.get('title', source.get('document_id', source['source_id']))} ({source.get('nasa_identifier', source['source_id'])})."
        row = {
            "evidence_id": eid,
            "document_id": source["source_id"],
            "page": 1,
            "section": "source metadata",
            "text": text,
            "start_offset": 0,
            "end_offset": len(text),
            "raw_file": source["filename"],
            "checksum": source["sha256"],
        }
        reg.add_passage(row)
        all_passages.append((source["source_id"], eid, text, 1))
# Stable investigation entities backed by fetched NASA PSI records (not inferred conditions).
for sid, title, doi in [
    ("psi-25", "BASS-II", "10.60555/4qc4-de67"),
    ("psi-98", "Saffire-I", "10.60555/0t15-1z43"),
]:
    ev = next((e for s, e, _, _ in all_passages if s == sid), None)
    if ev:
        records.append(
            {
                "type": "InvestigationRecord",
                "id": sid,
                "title": title,
                "doi": doi,
                "evidence_refs": [{"evidence_id": ev, "source_id": sid}],
            }
        )

standard_ev = next((e for s, e, _, _ in all_passages if s == "nasa-std-6001"), None)
if standard_ev:
    records.append(
        {
            "type": "NASAStandard",
            "id": "nasa-std-6001",
            "title": "NASA-STD-6001",
            "evidence_refs": [{"evidence_id": standard_ev, "source_id": "nasa-std-6001"}],
        }
    )


def first_matching(source_id, patterns):
    for sid, eid, text, page in all_passages:
        if sid == source_id:
            for p in patterns:
                match = re.search(p, text, re.IGNORECASE)
                if match:
                    left = text.rfind(".", 0, match.start()) + 1
                    right = text.find(".", match.end()) + 1
                    return eid, text[left:right].strip() or text, page
    return None


# A statement is represented only where the official source itself contains an explicit modality/knowledge-gap cue.
for source_id, kind, patterns in [
    (
        "ntrs-20205007829",
        "open_question",
        [
            r"knowledge gap",
            r"additional research",
            r"needs? (to be|for) (developed|addressed)",
            r"open question",
            r"question they need answe",
        ],
    ),
    ("ntrs-20205007829", "nasa_conclusion", [r"generally rated the fire risk very low"]),
    ("ntrs-20150020937", "guidance", [r"recommend", r"guidance", r"design criterion"]),
]:
    found = first_matching(source_id, patterns)
    if found:
        eid, text, page = found
        records.append(
            {
                "type": kind,
                "id": f"{kind}-{source_id}",
                "text": text,
                "evidence_refs": [{"evidence_id": eid, "source_id": source_id, "page": page}],
            }
        )

# PSI-98 entities originate only in the cached NASA experimental-table CSV.
psi_records_path = canonical / "psi98_records.json"
psi_table = raw / "psi" / "PSI-98_experimental_table.csv"
if psi_records_path.exists() and psi_table.exists():
    checksum = hashlib.sha256(psi_table.read_bytes()).hexdigest()
    reg.add_document("psi-98-experimental-table", "psi-98", "PSI-98 Experimental table")
    for line in psi_table.read_text(encoding="utf-8-sig").splitlines()[1:]:
        sample_number = line.split(",", 1)[0]
        if sample_number in {"S1", "S2"}:
            reg.add_passage(
                {
                    "evidence_id": f"E-psi-98-table-{sample_number}",
                    "document_id": "psi-98-experimental-table",
                    "page": None,
                    "section": "Experimental table",
                    "text": line,
                    "start_offset": 0,
                    "end_offset": len(line),
                    "raw_file": "psi/PSI-98_experimental_table.csv",
                    "checksum": checksum,
                }
            )
    records.extend(json.loads(psi_records_path.read_text()))

psi25_records_path = canonical / "psi25_records.json"
psi25_table = raw / "psi" / "PSI-25_experimental_table.csv"
if psi25_records_path.exists() and psi25_table.exists():
    checksum = hashlib.sha256(psi25_table.read_bytes()).hexdigest()
    reg.add_document("psi-25-experimental-table", "psi-25", "PSI-25 Experimental table")
    for line in psi25_table.read_text(encoding="utf-8-sig").splitlines()[1:]:
        if ",B1," in line:
            reg.add_passage(
                {
                    "evidence_id": "E-psi-25-table-B1",
                    "document_id": "psi-25-experimental-table",
                    "page": None,
                    "section": "Experimental table",
                    "text": line,
                    "start_offset": 0,
                    "end_offset": len(line),
                    "raw_file": "psi/PSI-25_experimental_table.csv",
                    "checksum": checksum,
                }
            )
            break
    records.extend(json.loads(psi25_records_path.read_text()))

safety_records_path = canonical / "safety_records.json"
if safety_records_path.exists():
    safety_records = json.loads(safety_records_path.read_text())
    standard_path = raw / "nasa-std-6001-change3.pdf"
    if standard_path.exists():
        checksum = hashlib.sha256(standard_path.read_bytes()).hexdigest()
        reg.add_source(
            {
                "source_id": "nasa-std-6001",
                "source_type": "NASA Standard",
                "nasa_id": "NASA-STD-6001B w/CHANGE 3",
                "title": "Flammability, Offgassing, and Compatibility Requirements and Test Procedures",
                "doi": None,
                "url": "https://standards.nasa.gov/sites/default/files/standards/NASA/B-w/CHANGE-3/3/2025_06_25_NASA-STD-6001B_w_Change_3_FINAL_Admin-Change-FINAL.pdf",
                "retrieved_at": "cached by scripts/ingest_safety.py",
                "filename": "nasa-std-6001-change3.pdf",
                "sha256": checksum,
                "mime_type": "application/pdf",
                "status": "fetched",
            }
        )
        reg.add_document("nasa-std-6001", "nasa-std-6001", "NASA-STD-6001B w/CHANGE 3")
    for record in safety_records:
        for reference in record["evidence_refs"]:
            text = record.get("normalized_text") or record.get("description") or record.get("text")
            reg.add_passage(
                {
                    "evidence_id": reference["evidence_id"],
                    "document_id": record["source_document"],
                    "page": record.get("source_page"),
                    "section": record.get("source_section"),
                    "text": text,
                    "start_offset": None,
                    "end_offset": None,
                    "raw_file": "nasa-std-6001-change3.pdf"
                    if record["source_document"] == "nasa-std-6001"
                    else None,
                    "checksum": hashlib.sha256(standard_path.read_bytes()).hexdigest()
                    if record["source_document"] == "nasa-std-6001" and standard_path.exists()
                    else None,
                }
            )
    records.extend(safety_records)
phase1_records_path = canonical / "phase1_published.json"
if phase1_records_path.exists():
    records.extend(json.loads(phase1_records_path.read_text()))
phase1_documents_path = canonical / "phase1_documents.json"
if phase1_documents_path.exists():
    records.extend(json.loads(phase1_documents_path.read_text()))
reviewed_records_path = canonical / "phase1_reviewed.json"
if reviewed_records_path.exists():
    records.extend(json.loads(reviewed_records_path.read_text()))
phase15_records_path = canonical / "phase15_structured.json"
if phase15_records_path.exists():
    records.extend(json.loads(phase15_records_path.read_text()))
# Legacy curated gold may overlap a generalized re-ingestion (PSI-25 B1).
# Keep the first, curated record and never emit duplicate stable domain IDs.
deduplicated = []
seen_ids = set()
for record in records:
    record_id = record.get("id", record.get("statement_id"))
    if record_id in seen_ids:
        continue
    seen_ids.add(record_id)
    deduplicated.append(record)
records = deduplicated
(canonical / "records.json").write_text(json.dumps(records, indent=2))
print(json.dumps({"records": len(records), "passages": len(all_passages)}, indent=2))
