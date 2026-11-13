#!/usr/bin/env python3
"""Import verified upstream NTRS text into the documentary registry only.

The upstream text is a cached textual representation whose NTRS identifier and
canonical NASA citation URL are checked against the upstream catalog.  It is
therefore usable for search, but this script deliberately creates no canonical
scientific records or RDF triples.
"""

import argparse
import csv
import hashlib
import json
import shutil
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.phase1 import segment_document, stable_id


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verified(row: dict, source: Path) -> bool:
    identifier = (row.get("id") or "").strip()
    url = (row.get("url") or "").strip()
    parsed = urlparse(url)
    return (
        identifier.isdigit()
        and parsed.scheme == "https"
        and parsed.netloc == "ntrs.nasa.gov"
        and f"/citations/{identifier}" in parsed.path
        and source.is_file()
        and source.stat().st_size > 0
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream", type=Path, required=True)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    upstream = args.upstream.resolve() / "data" / "ntrs"
    catalog = upstream / "catalog.csv"
    target_root = ROOT / "data/raw/upstream_nasa_space_apps/ntrs"
    target_root.mkdir(parents=True, exist_ok=True)
    registry = EvidenceRegistry(Settings().registry_path)
    manifest_path = ROOT / "data/catalog/phase15_ntrs_import.json"
    prior = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    start = time.monotonic()
    report = {
        "catalog_records": 0,
        "verified": 0,
        "imported": 0,
        "duplicate": 0,
        "missing_text": 0,
        "failed_verification": 0,
        "segmented": 0,
        "passages_added": 0,
    }
    with catalog.open(encoding="utf-8-sig", errors="replace", newline="") as handle:
        rows = list(csv.DictReader(handle))
    report["catalog_records"] = len(rows)
    for index, row in enumerate(rows):
        if args.limit is not None and index >= args.limit:
            break
        raw_rel = (row.get("txt") or "").replace("\\", "/")
        source = upstream / raw_rel
        if not source.is_file() or not source.stat().st_size:
            report["missing_text"] += 1
            continue
        if not verified(row, source):
            report["failed_verification"] += 1
            continue
        report["verified"] += 1
        checksum = digest(source)
        ntrs_id = row["id"].strip()
        target = target_root / f"{ntrs_id}-{checksum[:16]}.txt"
        if not target.exists():
            shutil.copy2(source, target)
            report["imported"] += 1
        elif digest(target) == checksum:
            report["duplicate"] += 1
        else:  # An immutable destination must never be overwritten.
            raise RuntimeError(f"checksum conflict for immutable artifact {target}")
        source_id = f"ntrs-{ntrs_id}"
        document_id = f"ntrs-upstream-{ntrs_id}-{checksum[:16]}"
        registry.add_source(
            {
                "source_id": source_id,
                "source_type": "NTRS " + (row.get("sti_type") or "document"),
                "nasa_id": ntrs_id,
                "title": row.get("title") or source_id,
                "doi": None,
                "url": row["url"],
                "retrieved_at": "Phase-1.5 upstream import",
                "filename": str(target.relative_to(ROOT)),
                "sha256": checksum,
                "mime_type": "text/plain",
                "status": "UPSTREAM_NTRS_TEXT_VERIFIED",
            }
        )
        registry.add_document(document_id, source_id, row.get("title") or source_id)
        registry.add_document_metadata(
            document_id,
            {
                "authors": row.get("authors"),
                "publication_date": row.get("date"),
                "document_type": row.get("sti_type"),
                "nasa_center": row.get("center"),
                "keywords": row.get("keywords"),
                "upstream_path": str(source.relative_to(args.upstream.resolve())),
                "verification_status": "catalog-NTRS-ID-and-canonical-URL-verified; upstream-text-checksum-recorded",
            },
        )
        artifact_id = stable_id("artifact", source_id, checksum)
        registry.add_artifact(
            {
                "artifact_id": artifact_id,
                "batch_id": "phase15-ntrs-upstream-import",
                "source_id": source_id,
                "investigation_id": None,
                "document_id": document_id,
                "source_type": "NTRS extracted text",
                "canonical_url": row["url"],
                "doi": None,
                "retrieval_timestamp": "Phase-1.5 upstream import",
                "source_version": checksum,
                "filename": str(target.relative_to(ROOT)),
                "mime_type": "text/plain",
                "file_size": target.stat().st_size,
                "sha256": checksum,
                "retrieval_status": "VERIFIED_CACHED_TEXT",
            }
        )
        before = registry.db.execute(
            "SELECT count(*) FROM passages WHERE document_id=? AND checksum=?",
            (document_id, checksum),
        ).fetchone()[0]
        ids = segment_document(target, source_id, document_id, registry)
        report["segmented"] += 1
        report["passages_added"] += max(0, len(ids) - before)
        prior[document_id] = {
            "source_id": source_id,
            "ntrs_id": ntrs_id,
            "canonical_url": row["url"],
            "title": row.get("title"),
            "checksum": checksum,
            "raw_file": str(target.relative_to(ROOT)),
            "source_text_path": str(source.relative_to(args.upstream.resolve())),
            "verification_status": "catalog-NTRS-ID-and-canonical-URL-verified; upstream-text-checksum-recorded",
            "passage_count": len(ids),
        }
    manifest_path.write_text(json.dumps(prior, indent=2, sort_keys=True) + "\n")
    registry.rebuild_fts()
    report["elapsed_seconds"] = round(time.monotonic() - start, 3)
    report["total_documents"] = registry.db.execute("SELECT count(*) FROM documents").fetchone()[0]
    report["total_passages"] = registry.db.execute("SELECT count(*) FROM passages").fetchone()[0]
    report["total_fts_rows"] = registry.db.execute("SELECT count(*) FROM passages_fts").fetchone()[
        0
    ]
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
