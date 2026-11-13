"""Bounded official-source maintenance using the existing Evidence Registry.

Automatic contract: immutable public NASA document identities and exact physical
PDF page text only. Scientific interpretation is staged, never self-approved.
"""

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import httpx
import pymupdf

from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.phase1 import NTRSAdapter

CONTRACT = "official-ntrs-document-pages-v1"


def sha(value):
    return hashlib.sha256(value).hexdigest()


def registry_checks(registry):
    db = registry.db
    return {
        "sqlite_integrity": db.execute("PRAGMA integrity_check").fetchone()[0],
        "foreign_keys": [list(row) for row in db.execute("PRAGMA foreign_key_check")],
        "missing_documents": db.execute(
            "SELECT count(*) FROM passages p LEFT JOIN documents d USING(document_id) WHERE d.document_id IS NULL"
        ).fetchone()[0],
        "missing_sources": db.execute(
            "SELECT count(*) FROM documents d LEFT JOIN sources s USING(source_id) WHERE s.source_id IS NULL"
        ).fetchone()[0],
        "missing_fts": db.execute(
            "SELECT count(*) FROM passages WHERE evidence_id NOT IN (SELECT evidence_id FROM passages_fts)"
        ).fetchone()[0],
        "duplicate_fts": db.execute(
            "SELECT count(*) FROM (SELECT evidence_id FROM passages_fts GROUP BY evidence_id HAVING count(*) != 1)"
        ).fetchone()[0],
        "fts_mismatches": db.execute(
            "WITH f AS MATERIALIZED (SELECT evidence_id,text FROM passages_fts) SELECT count(*) FROM f JOIN passages p USING(evidence_id) WHERE p.text != f.text"
        ).fetchone()[0],
    }


def official_download(metadata):
    identifier = str(metadata.get("id", ""))
    if not identifier.isdecimal() or metadata.get("distribution") != "PUBLIC":
        raise ValueError("Only identified public NTRS citations are eligible")
    for download in metadata.get("downloads", []):
        link = download.get("links", {}).get("pdf", "")
        url = urljoin("https://ntrs.nasa.gov", link)
        parsed = urlsplit(url)
        if (
            download.get("mimetype") == "application/pdf"
            and not download.get("draft")
            and parsed.scheme == "https"
            and parsed.netloc == "ntrs.nasa.gov"
            and parsed.path.startswith(f"/api/citations/{identifier}/downloads/")
        ):
            return url
    raise ValueError("No eligible official public PDF download")


class KnowledgeMaintenance:
    def __init__(self, root: Path, registry: EvidenceRegistry, adapter=None):
        self.root, self.registry = root, registry
        self.adapter = adapter or NTRSAdapter()

    def discover(self, query, semantic_registry):
        # Ontology/approved vocabulary supplies scope, not a competing taxonomy.
        labels = {str(key).lower() for key in semantic_registry.class_metadata}
        labels.update(str(key).lower() for key in semantic_registry.properties)
        records = []
        for metadata in self.adapter.discover(query):
            text = " ".join(
                [
                    metadata.get("title", ""),
                    metadata.get("abstract", ""),
                    *metadata.get("keywords", []),
                ]
            ).lower()
            recognized = [
                label
                for label in sorted(labels)
                if len(label) > 3 and label in re.sub(r"[^a-z0-9]", "", text)
            ]
            records.append(
                {
                    "nasa_id": str(metadata.get("id")),
                    "title": metadata.get("title"),
                    "modified": metadata.get("modified"),
                    "ontology_terms": recognized,
                    "status": "RELEVANCE_REVIEW_REQUIRED",
                    "metadata": metadata,
                    "independent_relevance": None,
                }
            )
        return records

    def update(self, identifier, *, dry_run=True, refresh=False):
        metadata = self.adapter.fetch_metadata(identifier)
        url = official_download(metadata)
        fingerprint = sha(json.dumps(metadata, sort_keys=True).encode())
        db = self.registry.db
        # Dry-run does not create a state table or write a cache.
        exists = db.execute(
            "SELECT 1 FROM sqlite_master WHERE name='maintenance_versions'"
        ).fetchone()
        previous = (
            db.execute(
                "SELECT * FROM maintenance_versions WHERE nasa_id=? AND metadata_sha=? AND contract=? AND status='PUBLISHED'",
                (identifier, fingerprint, CONTRACT),
            ).fetchone()
            if exists
            else None
        )
        plan = {
            "nasa_id": identifier,
            "url": url,
            "metadata_sha": fingerprint,
            "contract": CONTRACT,
            "mode": "DRY_RUN" if dry_run else "CONTROLLED_UPDATE",
            "previous_version": dict(previous) if previous else None,
            "scientific_publication": "NONE; document/provenance contract only",
        }
        if previous and not refresh:
            return {**plan, "status": "UNCHANGED", "downloaded": False, "index_rebuilt": False}
        if dry_run:
            return {**plan, "status": "ACQUISITION_PENDING"}
        db.execute(
            "CREATE TABLE IF NOT EXISTS maintenance_versions(nasa_id TEXT, metadata_sha TEXT, contract TEXT, content_sha TEXT, source_id TEXT, status TEXT, receipt_json TEXT, PRIMARY KEY(nasa_id, metadata_sha, contract, content_sha))"
        )
        if sum(bool(row[5]) for row in db.execute("PRAGMA table_info(maintenance_versions)")) == 3:
            with db:
                db.execute(
                    "ALTER TABLE maintenance_versions RENAME TO maintenance_versions_legacy_v1"
                )
                db.execute(
                    "CREATE TABLE maintenance_versions(nasa_id TEXT,metadata_sha TEXT,contract TEXT,content_sha TEXT,source_id TEXT,status TEXT,receipt_json TEXT,PRIMARY KEY(nasa_id,metadata_sha,contract,content_sha))"
                )
                db.execute(
                    "INSERT INTO maintenance_versions SELECT * FROM maintenance_versions_legacy_v1"
                )
        db.commit()
        try:
            # No off-domain redirects, credentials, or unbounded response buffering.
            with httpx.stream("GET", url, timeout=25, follow_redirects=False) as response:
                response.raise_for_status()
                parts, size = [], 0
                for part in response.iter_bytes():
                    size += len(part)
                    if size > 50 * 1024**2:
                        raise ValueError("PDF acquisition exceeds 50 MiB limit")
                    parts.append(part)
                content = b"".join(parts)
            return self.publish_document(metadata, content, fingerprint, plan)
        except (httpx.HTTPError, ValueError, RuntimeError, pymupdf.FileDataError) as error:
            receipt = {
                **plan,
                "status": "QUARANTINED",
                "error_type": type(error).__name__,
                "reason": str(error)
                if isinstance(error, ValueError)
                else "Network or parser failure; no scientific publication",
                "canonical_scientific_changes": 0,
            }
            db.execute(
                "INSERT OR REPLACE INTO maintenance_versions VALUES (?,?,?,?,?,?,?)",
                (identifier, fingerprint, CONTRACT, None, None, "QUARANTINED", json.dumps(receipt)),
            )
            db.commit()
            return receipt

    def publish_document(self, metadata, content, fingerprint, plan):
        if not content.startswith(b"%PDF-"):
            raise ValueError("Downloaded content is not a PDF")
        digest = sha(content)
        identifier = str(metadata["id"])
        source_id = f"ntrs-{identifier}@{digest[:20]}"
        document_id = f"document-{source_id}"
        db = self.registry.db
        if db.execute("SELECT 1 FROM documents WHERE document_id=?", (document_id,)).fetchone():
            receipt = {
                **plan,
                "status": "UNCHANGED_CONTENT",
                "content_sha": digest,
                "source_id": source_id,
                "index_rebuilt": False,
            }
            db.execute(
                "INSERT OR REPLACE INTO maintenance_versions VALUES (?,?,?,?,?,?,?)",
                (
                    identifier,
                    fingerprint,
                    CONTRACT,
                    digest,
                    source_id,
                    "PUBLISHED",
                    json.dumps(receipt),
                ),
            )
            db.commit()
            return receipt
        with pymupdf.open(stream=content, filetype="pdf") as pdf:
            if pdf.page_count > 200:
                raise ValueError("Bounded parser accepts at most 200 pages")
            pages = [(index + 1, page.get_text("text")) for index, page in enumerate(pdf)]
        if (
            not any(text.strip() for _, text in pages)
            or sum(len(text) for _, text in pages) > 1_000_000
        ):
            raise ValueError("No searchable text, or document exceeds extraction budget")
        directory = self.root / "data/raw/autonomous"
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"ntrs-{identifier}-{digest}.pdf"
        if path.exists():
            if sha(path.read_bytes()) != digest:
                raise ValueError("Immutable raw-file collision")
        else:
            with path.open("xb") as stream:
                stream.write(content)
        receipt = {
            **plan,
            "status": "PUBLISHED",
            "source_id": source_id,
            "document_id": document_id,
            "content_sha": digest,
            "raw_file": str(path.relative_to(self.root)),
            "pages": len(pages),
            "evidence_ids": [],
            "canonical_scientific_changes": 0,
            "published_contract": "Document identity + original page text; no experimental assertion",
            "index_rebuilt": True,
        }
        older = [
            row[0]
            for row in db.execute(
                "SELECT DISTINCT source_id FROM maintenance_versions WHERE nasa_id=? AND status='PUBLISHED' AND content_sha!=?",
                (identifier, digest),
            )
        ]
        receipt["superseded_document_sources"] = older
        # One atomic publication includes identity, citations, locations and FTS.
        # A failed transaction leaves the immutable acquired PDF for inspection.
        with db:
            for previous_source in older:
                db.execute(
                    "UPDATE sources SET status='SUPERSEDED_DOCUMENT' WHERE source_id=?",
                    (previous_source,),
                )
                db.execute(
                    "UPDATE maintenance_versions SET status='SUPERSEDED' WHERE source_id=?",
                    (previous_source,),
                )
            db.execute(
                "INSERT INTO sources(source_id,source_type,nasa_id,title,url,retrieved_at,filename,sha256,mime_type,status) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    source_id,
                    "NTRS",
                    identifier,
                    metadata.get("title"),
                    plan["url"],
                    datetime.now(UTC).isoformat(),
                    str(path.relative_to(self.root)),
                    digest,
                    "application/pdf",
                    "DOCUMENT_VERIFIED",
                ),
            )
            db.execute(
                "INSERT INTO documents VALUES (?,?,?)",
                (document_id, source_id, metadata.get("title")),
            )
            for page, text in pages:
                if not text.strip():
                    continue
                eid = "E-auto-" + sha(f"{document_id}:{page}:{text}".encode())[:24]
                receipt["evidence_ids"].append(eid)
                db.execute(
                    "INSERT INTO passages VALUES (?,?,?,?,?,?,?,?,?)",
                    (
                        eid,
                        document_id,
                        page,
                        f"Physical PDF page {page}",
                        text,
                        0,
                        len(text),
                        str(path),
                        digest,
                    ),
                )
                db.execute("INSERT INTO evidence_refs VALUES (?,?)", (eid, source_id))
                db.execute("INSERT INTO passages_fts VALUES (?,?)", (eid, text))
                db.execute(
                    "INSERT INTO evidence_locations VALUES (?,?)",
                    (
                        eid,
                        json.dumps(
                            {
                                "physical_pdf_page": page,
                                "locator_status": "EXACT_PDF_PAGE_TEXT",
                                "source_version": digest,
                            }
                        ),
                    ),
                )
            db.execute(
                "INSERT OR REPLACE INTO maintenance_versions VALUES (?,?,?,?,?,?,?)",
                (
                    identifier,
                    fingerprint,
                    CONTRACT,
                    digest,
                    source_id,
                    "PUBLISHED",
                    json.dumps(receipt),
                ),
            )
            checks = registry_checks(self.registry)
            if checks["sqlite_integrity"] != "ok" or any(
                checks[key]
                for key in (
                    "foreign_keys",
                    "missing_documents",
                    "missing_sources",
                    "missing_fts",
                    "duplicate_fts",
                    "fts_mismatches",
                )
            ):
                raise ValueError(
                    "Registry integrity gate failed; publication transaction rolled back"
                )
            receipt["publication_gates"] = checks
        return receipt

    def stage(self, proposal):
        """Deduplicate exact source-span proposals, keeping interpretation staged."""
        evidence = self.registry.resolve(proposal.get("evidence_id", ""))
        span = proposal.get("evidence_span", "")
        if not evidence or not span or span not in evidence["text"]:
            return {
                "status": "REJECTED",
                "reason": "Source span unsupported",
                "canonical_changes": 0,
            }
        context = proposal.get("contextual_proposal")
        if context:
            error = self.context_proposal_error(context)
            if error:
                return {"status": "REJECTED", "reason": error, "canonical_changes": 0}
        candidate = {
            "candidate_id": "maintenance-"
            + sha(json.dumps(proposal, sort_keys=True).encode())[:24],
            "candidate_type": "CandidateRelation",
            "raw_label": span,
            "resolution_status": "CANDIDATE_RELATION",
            "evidence_id": proposal["evidence_id"],
            "proposal": proposal,
            "review_status": "PENDING",
        }
        # Confidence/provider prose does not create a new scientific review.
        semantic_key = {
            "evidence_id": proposal["evidence_id"],
            "span": span,
            "context": {
                key: (context or {}).get(key)
                for key in (
                    "subject_entity",
                    "candidate_predicate",
                    "object_value",
                    "context_scope",
                    "exceptions",
                    "applicability_conditions",
                )
            },
        }
        candidate["candidate_id"] = (
            "maintenance-" + sha(json.dumps(semantic_key, sort_keys=True).encode())[:24]
        )
        existing = self.registry.db.execute(
            "SELECT resolution_status FROM semantic_staging WHERE candidate_id=?",
            (candidate["candidate_id"],),
        ).fetchone()
        if existing:
            return {
                "status": "REJECTED" if existing[0] == "REJECTED" else "STAGED_CANDIDATE",
                "candidate_id": candidate["candidate_id"],
                "duplicate_review_avoided": True,
                "canonical_changes": 0,
            }
        candidate["source_id"] = self.registry.db.execute(
            "SELECT source_id FROM documents WHERE document_id=?", (evidence["document_id"],)
        ).fetchone()[0]
        self.registry.stage_semantic_candidate(candidate)
        priority = (
            "HIGH"
            if re.search(r"\b(?:shall|must|safety|risk|contradict)\b", span, re.IGNORECASE)
            else "SCOPE_REVIEW"
        )
        self.registry.review(
            "review-" + candidate["candidate_id"],
            "knowledge-maintenance",
            candidate["candidate_id"],
            "Unapproved scientific scope/interpretation",
            json.dumps(
                {
                    "priority": priority,
                    "source_evidence_id": proposal["evidence_id"],
                    "scientific_review": None,
                    "publication_eligible": False,
                }
            ),
        )
        return {
            "status": "STAGED_CANDIDATE",
            "candidate_id": candidate["candidate_id"],
            "canonical_changes": 0,
            "scientific_review": None,
        }

    def context_proposal_error(self, proposal):
        import yaml

        from nasa_fire_ai.ingestion.semantic import load_semantic_registry

        registry = load_semantic_registry(self.root / "domain/semantic_registry.yaml")
        predicate = proposal.get("candidate_predicate")
        if predicate not in registry.relations:
            return "Proposed relation is not approved registry vocabulary"
        language = yaml.safe_load((self.root / "domain/query_language_v2.yaml").read_text())
        value = str(proposal.get("object_value", ""))
        mention = language.get("entity_mentions", {}).get(value, {})
        if mention and mention.get("relation") != predicate:
            return "Object belongs to a different scientific relation"
        forms = [value, *mention.get("aliases", [])]
        text = " ".join(span.get("text", "") for span in proposal.get("support_spans", []))
        normalized = " ".join(text.lower().split())
        if not any(
            re.search(
                r"(?<!\w)" + re.escape(" ".join(form.lower().split())) + r"(?!\w)", normalized
            )
            for form in forms
            if form
        ):
            return "Quoted evidence does not establish the proposed contextual value; membership alone is insufficient"
        return None

    def revalidate_staged_contexts(self):
        receipts = []
        for candidate in self.registry.staged_semantic_candidates():
            proposal = candidate.get("proposal", {}).get("contextual_proposal")
            if not proposal:
                continue
            error = self.context_proposal_error(proposal)
            if error:
                self.registry.db.execute(
                    "UPDATE semantic_staging SET resolution_status='REJECTED',review_status='REJECTED' WHERE candidate_id=?",
                    (candidate["candidate_id"],),
                )
                self.registry.db.execute(
                    "UPDATE review_queue SET status='REJECTED',reviewer_note=? WHERE candidate_id=?",
                    (error, candidate["candidate_id"]),
                )
            receipts.append(
                {
                    "candidate_id": candidate["candidate_id"],
                    "status": "REJECTED" if error else "STAGED_CANDIDATE",
                    "reason": error,
                    "scientific_publication": False,
                }
            )
        self.registry.db.commit()
        return receipts

    def interpret_source(self, source_id, settings, semantic_registry):
        """One optional live request; checkpoint by source/model/prompt contract."""
        from nasa_fire_ai.llm.context import NvidiaContextInterpreter
        from nasa_fire_ai.llm.interfaces import ProviderFailure

        if not settings.nvidia_api_key:
            return {"execution": "NOT_CALLED", "reason": "No configured NVIDIA key"}
        rows = self.registry.db.execute(
            "SELECT p.* FROM passages p JOIN documents d USING(document_id) WHERE d.source_id=? ORDER BY page",
            (source_id,),
        ).fetchall()
        if not rows:
            return {"execution": "NOT_CALLED", "reason": "No published source units"}
        key = sha(
            json.dumps(
                {
                    "source": source_id,
                    "model": settings.nvidia_phase3_model,
                    "prompt": NvidiaContextInterpreter.prompt_version,
                    "contract": "maintenance-context-stage-v1",
                },
                sort_keys=True,
            ).encode()
        )
        cached = self.registry.get_phase3_cache(key, "maintenance_context")
        if cached and not cached.get("error_type"):
            return {**cached, "execution": "HISTORICAL_REPLAY"}
        passages = []
        # First introduction + final sections, bounded exact original pages.
        for row in [rows[0], *reversed(rows[-3:])]:
            if row["evidence_id"] in {p["evidence_id"] for p in passages}:
                continue
            if sum(len(p["text"]) for p in passages) + len(row["text"]) <= 6000:
                passages.append(
                    {
                        "evidence_id": row["evidence_id"],
                        "source_id": source_id,
                        "section": row["section"],
                        "text": row["text"],
                    }
                )
        # All reviewed registry relations are permissible proposal vocabulary;
        # none becomes a verified fact merely by appearing in this output.
        allowed = sorted(semantic_registry.relations)
        interpreter = NvidiaContextInterpreter(
            settings.nvidia_api_key, settings.nvidia_base_url, settings.nvidia_phase3_model
        )
        result = {
            "execution": "FRESH_INFERENCE",
            "source_window": passages,
            "scientific_publications": 0,
            "outcomes": [],
            "independent_review": None,
        }
        try:
            proposals = interpreter.interpret(
                query="Identify actual experimental context and scope exceptions. Separate prior cited research and recommendations from the author's tests. Propose only exact source-supported relations; document identity alone cannot establish a run's membership.",
                entities=[rows[0]["document_id"]],
                passages=passages,
                allowed_predicates=allowed,
            )
            for proposal in proposals:
                if proposal.validation_status == "REJECTED" or not proposal.support_spans:
                    result["outcomes"].append(
                        {"proposal": proposal.model_dump(mode="json"), "status": "REJECTED"}
                    )
                else:
                    span = proposal.support_spans[0]
                    result["outcomes"].append(
                        {
                            "proposal": proposal.model_dump(mode="json"),
                            "staging": self.stage(
                                {
                                    "evidence_id": span["evidence_id"],
                                    "evidence_span": span["text"],
                                    "contextual_proposal": proposal.model_dump(mode="json"),
                                    "membership_verification": "REVIEW_REQUIRED",
                                }
                            ),
                        }
                    )
        except (ProviderFailure, ValueError) as error:
            result["error_type"] = type(error).__name__
        result["provider_receipt"] = getattr(interpreter, "last_receipt", {})
        self.registry.set_phase3_cache(key, "maintenance_context", result)
        return result

    def rollback_document(self, source_id):
        """Unpublish ONLY this pipeline's document, never delete immutable inputs."""
        db = self.registry.db
        if not db.execute(
            "SELECT 1 FROM maintenance_versions WHERE source_id=? AND status='PUBLISHED'",
            (source_id,),
        ).fetchone():
            raise ValueError("Rollback target is not an active maintenance publication")
        with db:
            ids = [
                row[0]
                for row in db.execute(
                    "SELECT evidence_id FROM evidence_refs WHERE source_id=?", (source_id,)
                )
            ]
            # Archive publication, not evidence: historical citations must resolve.
            db.execute(
                "UPDATE sources SET status='ROLLED_BACK_DOCUMENT' WHERE source_id=?",
                (source_id,),
            )
            db.execute(
                "UPDATE maintenance_versions SET status='ROLLED_BACK' WHERE source_id=?",
                (source_id,),
            )
            previous = db.execute(
                "SELECT source_id FROM sources WHERE status='SUPERSEDED_DOCUMENT' AND nasa_id=(SELECT nasa_id FROM maintenance_versions WHERE source_id=? LIMIT 1) ORDER BY retrieved_at DESC LIMIT 1",
                (source_id,),
            ).fetchone()
            if previous:
                db.execute(
                    "UPDATE sources SET status='DOCUMENT_VERIFIED' WHERE source_id=?",
                    (previous[0],),
                )
                db.execute(
                    "UPDATE maintenance_versions SET status='PUBLISHED' WHERE source_id=?",
                    (previous[0],),
                )
        return {"status": "ROLLED_BACK", "raw_preserved": True, "unpublished_evidence": len(ids)}
