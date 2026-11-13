#!/usr/bin/env python3
"""Add one verified NASA source without giving an extractor graph mutation authority."""

import argparse
import json
import logging
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.phase1 import (
    Artifact,
    HTTPMetadataAdapter,
    PSIAdapter,
    append_raw_manifest,
    publish_validated,
    segment_document,
    stable_id,
    structured_csv_candidates,
    validate_candidate,
)


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--psi-id")
    group.add_argument("--local-document", type=Path)
    group.add_argument("--url", help="verified official NASA artifact URL")
    parser.add_argument("--source-id")
    parser.add_argument("--title")
    parser.add_argument("--source-type", default="NASA document")
    parser.add_argument(
        "--publish", action="store_true", help="publish only validated deterministic records"
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    settings = Settings()
    registry = EvidenceRegistry(settings.registry_path)
    if args.psi_id:
        source_id = args.psi_id.lower()
        adapter = PSIAdapter(ROOT / "data/raw/psi")
        artifact = adapter.list_artifacts(args.psi_id)[0]
        path = adapter.fetch_artifact(artifact, ROOT / "data/raw/psi")
        artifact.source_id = source_id
        artifact.investigation_id = source_id
        artifact.document_id = f"{source_id}-experimental-table"
    elif args.local_document:
        path = args.local_document.resolve()
        source_id = f"local-{path.stem}"
        artifact = Artifact(
            artifact_id=source_id,
            source_id=source_id,
            document_id=source_id,
            canonical_url=path.as_uri(),
            filename=path.name,
            source_type="developer-supplied NASA document",
        )
    else:
        if not args.source_id:
            raise SystemExit("--source-id is required with --url")
        host = urllib.parse.urlparse(args.url).hostname or ""
        if not host.endswith("nasa.gov"):
            raise SystemExit("only verified official NASA URLs are accepted")
        source_id = args.source_id
        artifact = Artifact(
            artifact_id=f"{source_id}:document",
            source_id=source_id,
            investigation_id=source_id,
            document_id=source_id,
            canonical_url=args.url,
            filename=f"{source_id}.pdf",
            source_type=args.source_type,
            mime_type="application/pdf",
        )
        path = HTTPMetadataAdapter().fetch_artifact(artifact, ROOT / "data/raw")
    if path is None or not path.exists():
        raise SystemExit("official source unavailable; no substitute was used")
    batch_id = stable_id("batch", source_id, str(path.stat().st_size))
    registry.begin_batch(batch_id, source_id)
    append_raw_manifest(settings, artifact, path)
    registry.add_source(
        {
            "source_id": source_id,
            "source_type": artifact.source_type,
            "nasa_id": artifact.investigation_id,
            "title": args.title or artifact.document_id or source_id,
            "doi": artifact.doi,
            "url": artifact.canonical_url,
            "retrieved_at": "phase1",
            "filename": str(path),
            "sha256": __import__("hashlib").sha256(path.read_bytes()).hexdigest(),
            "mime_type": artifact.mime_type or "application/octet-stream",
            "status": "fetched",
        }
    )
    registry.add_document(
        artifact.document_id or source_id, source_id, artifact.document_id or source_id
    )
    candidates = (
        structured_csv_candidates(path, source_id, source_id, registry)
        if path.suffix.lower() == ".csv"
        else []
    )
    passages = (
        0
        if candidates
        else len(segment_document(path, source_id, artifact.document_id or source_id, registry))
    )
    published_documents = 0
    if args.publish and not candidates and passages:
        output = ROOT / "data/canonical/phase1_documents.json"
        existing = json.loads(output.read_text()) if output.exists() else []
        current = next((record for record in existing if record["id"] == source_id), None)
        evidence_id = registry.db.execute(
            "SELECT evidence_id FROM passages WHERE document_id=? ORDER BY evidence_id LIMIT 1",
            (artifact.document_id or source_id,),
        ).fetchone()[0]
        if current is None:
            existing.append(
                {
                    "type": "PublicationRecord",
                    "id": source_id,
                    "title": args.title or artifact.document_id or source_id,
                    "nasa_id": source_id.removeprefix("ntrs-"),
                    "url": artifact.canonical_url,
                    "evidence_refs": [
                        {
                            "evidence_id": evidence_id,
                            "source_id": source_id,
                        }
                    ],
                }
            )
            output.write_text(json.dumps(existing, indent=2) + "\n")
            published_documents = 1
        elif current["evidence_refs"][0]["evidence_id"] != evidence_id:
            current["evidence_refs"] = [{"evidence_id": evidence_id, "source_id": source_id}]
            output.write_text(json.dumps(existing, indent=2) + "\n")
    outcomes = {"VALIDATED": 0, "REVIEW_REQUIRED": 0, "REJECTED": 0}
    for candidate in candidates:
        status, error = validate_candidate(candidate, registry)
        outcomes[status] += 1
        import hashlib

        fingerprint = hashlib.sha256(candidate.model_dump_json().encode()).hexdigest()
        registry.add_candidate(
            {
                "candidate_id": candidate.candidate_id,
                "batch_id": batch_id,
                "candidate_type": candidate.candidate_type,
                "payload_json": candidate.model_dump_json(),
                "evidence_id": candidate.evidence_id,
                "status": status,
                "validation_error": error,
                "fingerprint": fingerprint,
            }
        )
        if status == "REVIEW_REQUIRED":
            registry.review(
                stable_id("review", candidate.candidate_id),
                batch_id,
                candidate.candidate_id,
                error or "review",
                "{}",
            )
    published = (
        publish_validated(candidates, registry, ROOT / "data/canonical/phase1_published.json")
        if args.publish
        else 0
    )
    print(
        json.dumps(
            {
                "batch_id": batch_id,
                "source_id": source_id,
                "candidates": len(candidates),
                "passages": passages,
                "published_runs": published,
                "published_documents": published_documents,
                "outcomes": outcomes,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
