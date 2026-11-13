import json
import re
import sqlite3
from datetime import UTC, datetime
from pathlib import Path


class EvidenceRegistry:
    def __init__(self, path: Path, *, read_only: bool = False, evidence_root: Path | None = None):
        self.evidence_root = evidence_root.resolve() if evidence_root is not None else None
        if read_only:
            self.db = sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        if not read_only:
            self.init()

    def init(self):
        self.db.executescript("""CREATE TABLE IF NOT EXISTS sources(source_id TEXT PRIMARY KEY, source_type TEXT, nasa_id TEXT, title TEXT, doi TEXT, url TEXT, retrieved_at TEXT, filename TEXT, sha256 TEXT, mime_type TEXT, status TEXT);
        CREATE TABLE IF NOT EXISTS documents(document_id TEXT PRIMARY KEY, source_id TEXT, title TEXT);
        CREATE TABLE IF NOT EXISTS passages(evidence_id TEXT PRIMARY KEY, document_id TEXT, page INTEGER, section TEXT, text TEXT, start_offset INTEGER, end_offset INTEGER, raw_file TEXT, checksum TEXT);
        CREATE TABLE IF NOT EXISTS evidence_refs(evidence_id TEXT PRIMARY KEY, source_id TEXT);
        CREATE VIRTUAL TABLE IF NOT EXISTS passages_fts USING fts5(evidence_id UNINDEXED, text);""")
        # Operational ingestion state intentionally stays outside the RDF domain graph.
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS ingestion_batches(batch_id TEXT PRIMARY KEY, source_id TEXT, created_at TEXT, status TEXT, notes TEXT);
        CREATE TABLE IF NOT EXISTS source_artifacts(artifact_id TEXT PRIMARY KEY, batch_id TEXT, source_id TEXT, investigation_id TEXT, document_id TEXT, source_type TEXT, canonical_url TEXT, doi TEXT, retrieval_timestamp TEXT, source_version TEXT, filename TEXT, mime_type TEXT, file_size INTEGER, sha256 TEXT, retrieval_status TEXT);
        CREATE TABLE IF NOT EXISTS candidate_records(candidate_id TEXT PRIMARY KEY, batch_id TEXT, candidate_type TEXT, payload_json TEXT, evidence_id TEXT, status TEXT, validation_error TEXT, fingerprint TEXT UNIQUE);
        CREATE TABLE IF NOT EXISTS review_queue(review_id TEXT PRIMARY KEY, batch_id TEXT, candidate_id TEXT, reason TEXT, status TEXT, detail_json TEXT, created_at TEXT);
        CREATE TABLE IF NOT EXISTS extraction_cache(cache_key TEXT PRIMARY KEY, response_json TEXT, status TEXT, created_at TEXT);
        CREATE TABLE IF NOT EXISTS document_metadata(document_id TEXT PRIMARY KEY, authors TEXT, publication_date TEXT, document_type TEXT, nasa_center TEXT, keywords TEXT, upstream_path TEXT, verification_status TEXT);
        CREATE TABLE IF NOT EXISTS phase3_cache(cache_key TEXT PRIMARY KEY, cache_kind TEXT, payload_json TEXT, created_at TEXT);
        CREATE TABLE IF NOT EXISTS semantic_staging(candidate_id TEXT PRIMARY KEY, candidate_type TEXT, raw_label TEXT, payload_json TEXT, source_id TEXT, evidence_id TEXT, resolution_status TEXT, review_status TEXT, created_at TEXT);
        CREATE TABLE IF NOT EXISTS evidence_locations(evidence_id TEXT PRIMARY KEY, location_json TEXT);
        CREATE TABLE IF NOT EXISTS structured_cells(evidence_id TEXT, column_ordinal INTEGER, locator_json TEXT, PRIMARY KEY(evidence_id,column_ordinal));
        """)
        for column in (
            "reviewer_note TEXT",
            "reviewed_type TEXT",
            "reviewed_at TEXT",
            "original_type TEXT",
        ):
            try:
                self.db.execute(f"ALTER TABLE review_queue ADD COLUMN {column}")
            except sqlite3.OperationalError:
                pass
        self.db.commit()

    def stage_semantic_candidate(self, row: dict):
        """Operational review state only; it cannot mutate the canonical graph."""
        required = {"candidate_id", "candidate_type", "raw_label", "resolution_status"}
        missing = required - set(row)
        if missing:
            raise ValueError(f"staging candidate missing: {sorted(missing)}")
        allowed = {
            "UNKNOWN",
            "KNOWN_AMBIGUOUS",
            "CANDIDATE_NEW_CONCEPT",
            "CANDIDATE_ALIAS",
            "CANDIDATE_RELATION",
            "REJECTED",
        }
        if row["resolution_status"] not in allowed:
            raise ValueError("staging records cannot be canonical")
        existing = self.db.execute(
            "SELECT payload_json FROM semantic_staging WHERE candidate_id=?", (row["candidate_id"],)
        ).fetchone()
        if existing:
            if json.loads(existing[0]) != row:
                raise ValueError("candidate identity conflict; stage a versioned candidate instead")
            return
        self.db.execute(
            "INSERT INTO semantic_staging VALUES (?,?,?,?,?,?,?,?,?)",
            (
                row["candidate_id"],
                row["candidate_type"],
                row["raw_label"],
                json.dumps(row),
                row.get("source_id"),
                row.get("evidence_id"),
                row["resolution_status"],
                row.get("review_status", "PENDING"),
                datetime.now(UTC).isoformat(),
            ),
        )
        self.db.commit()

    def staged_semantic_candidates(self) -> list[dict]:
        rows = self.db.execute(
            "SELECT payload_json,resolution_status,review_status FROM semantic_staging ORDER BY candidate_id"
        ).fetchall()
        return [
            {**json.loads(row[0]), "resolution_status": row[1], "review_status": row[2]}
            for row in rows
        ]

    def get_phase3_cache(self, cache_key: str, cache_kind: str) -> dict | None:
        row = self.db.execute(
            "SELECT payload_json FROM phase3_cache WHERE cache_key=? AND cache_kind=?",
            (cache_key, cache_kind),
        ).fetchone()
        return json.loads(row[0]) if row else None

    def set_phase3_cache(self, cache_key: str, cache_kind: str, payload: dict):
        self.db.execute(
            "INSERT OR REPLACE INTO phase3_cache VALUES (?,?,?,?)",
            (cache_key, cache_kind, json.dumps(payload), datetime.now(UTC).isoformat()),
        )
        self.db.commit()

    def add_source(self, row: dict):
        cols = ", ".join(row)
        self.db.execute(
            f"INSERT OR REPLACE INTO sources ({cols}) VALUES ({', '.join('?' for _ in row)})",
            tuple(row.values()),
        )
        self.db.commit()

    def add_document(self, document_id: str, source_id: str, title: str):
        self.db.execute(
            "INSERT OR REPLACE INTO documents(document_id, source_id, title) VALUES (?,?,?)",
            (document_id, source_id, title),
        )
        self.db.commit()

    def add_document_metadata(self, document_id: str, row: dict):
        """Store documentary provenance outside the scientific domain graph."""
        self.db.execute(
            """INSERT OR REPLACE INTO document_metadata
            (document_id,authors,publication_date,document_type,nasa_center,keywords,upstream_path,verification_status)
            VALUES (?,?,?,?,?,?,?,?)""",
            (
                document_id,
                row.get("authors"),
                row.get("publication_date"),
                row.get("document_type"),
                row.get("nasa_center"),
                row.get("keywords"),
                row.get("upstream_path"),
                row.get("verification_status"),
            ),
        )
        self.db.commit()

    def add_passage(self, row: dict):
        self.db.execute(
            "INSERT OR REPLACE INTO passages VALUES (:evidence_id,:document_id,:page,:section,:text,:start_offset,:end_offset,:raw_file,:checksum)",
            row,
        )
        # FTS5 has no primary-key semantics: delete first so re-ingestion cannot
        # leave stale duplicate searchable rows for the same evidence ID.
        self.db.execute("DELETE FROM passages_fts WHERE evidence_id=?", (row["evidence_id"],))
        self.db.execute(
            "INSERT INTO passages_fts(evidence_id,text) VALUES (?,?)",
            (row["evidence_id"], row["text"]),
        )
        source = self.db.execute(
            "SELECT source_id FROM documents WHERE document_id=?", (row["document_id"],)
        ).fetchone()
        if source:
            self.db.execute(
                "INSERT OR REPLACE INTO evidence_refs(evidence_id,source_id) VALUES (?,?)",
                (row["evidence_id"], source[0]),
            )
        self.db.commit()

    def search(self, query: str, eligible_ids: list[str] | None = None, limit=8):
        # FTS query syntax is not user query syntax. Quote lexical tokens so
        # punctuation such as BASS-II cannot become an FTS operator.
        terms = re.findall(r"[A-Za-z0-9]+", query)
        fts_query = " OR ".join(f'"{term}"' for term in terms) or '""'
        if eligible_ids is not None and not eligible_ids:
            return []
        # Apply eligibility before ranking/truncation. JSON avoids SQLite's
        # variable-count limit when a source has thousands of eligible passages.
        clause = (
            " AND p.evidence_id IN (SELECT value FROM json_each(?))"
            if eligible_ids is not None
            else ""
        )
        params = [fts_query]
        if eligible_ids is not None:
            params.append(json.dumps(eligible_ids))
        params.append(limit * 4 if eligible_ids is None else limit)
        rows = self.db.execute(
            "SELECT p.*, bm25(passages_fts) score FROM passages_fts JOIN passages p USING(evidence_id) LEFT JOIN documents d USING(document_id) LEFT JOIN sources s ON s.source_id=d.source_id WHERE passages_fts MATCH ? AND COALESCE(s.status,'') NOT IN ('SUPERSEDED_DOCUMENT','ROLLED_BACK_DOCUMENT')"
            + clause
            + " ORDER BY score, p.evidence_id LIMIT ?",
            params,
        ).fetchall()
        return [dict(r) for r in rows[:limit]]

    def resolve(self, evidence_id: str):
        row = self.db.execute(
            "SELECT * FROM passages WHERE evidence_id=?", (evidence_id,)
        ).fetchone()
        if not row:
            return None
        result = dict(row)
        raw = result.get("raw_file")
        if raw and self.evidence_root is not None and not Path(raw).is_absolute():
            result["relative_raw_file"] = raw
            resolved = (self.evidence_root / raw).resolve()
            if not resolved.is_relative_to(self.evidence_root):
                raise ValueError("Evidence path escapes configured root")
            result["raw_file"] = str(resolved)
        location = self.db.execute(
            "SELECT location_json FROM evidence_locations WHERE evidence_id=?", (evidence_id,)
        ).fetchone()
        if location:
            result["structured_location"] = json.loads(location[0])
            result["page_location_verified"] = (
                result["structured_location"].get("physical_pdf_page") == result["page"]
                and result["page"] is not None
            )
        cells = self.db.execute(
            "SELECT locator_json FROM structured_cells WHERE evidence_id=? ORDER BY column_ordinal",
            (evidence_id,),
        ).fetchall()
        if cells:
            result["source_cells"] = [json.loads(cell[0]) for cell in cells]
            result["offset_contract"] = result["source_cells"][0]["offset_contract"]
        return result

    def add_evidence_location(self, evidence_id: str, location: dict):
        if self.resolve(evidence_id) is None:
            raise ValueError("location requires an existing evidence ID")
        encoded = json.dumps(location, sort_keys=True)
        existing = self.db.execute(
            "SELECT location_json FROM evidence_locations WHERE evidence_id=?", (evidence_id,)
        ).fetchone()
        if existing and existing[0] != encoded:
            raise ValueError("conflicting evidence location")
        self.db.execute(
            "INSERT OR IGNORE INTO evidence_locations VALUES (?,?)", (evidence_id, encoded)
        )
        self.db.commit()

    def source_metadata(self, evidence_id: str) -> dict | None:
        row = self.db.execute(
            """SELECT s.source_id, s.source_type, s.nasa_id, s.title, s.url
            FROM passages p JOIN documents d USING(document_id)
            JOIN sources s ON s.source_id=d.source_id
            WHERE p.evidence_id=?""",
            (evidence_id,),
        ).fetchone()
        return dict(row) if row else None

    def rebuild_fts(self):
        self.db.execute("DELETE FROM passages_fts")
        self.db.execute(
            "INSERT INTO passages_fts(evidence_id,text) SELECT evidence_id,text FROM passages"
        )
        self.db.commit()

    def begin_batch(self, batch_id: str, source_id: str, notes: str = ""):
        self.db.execute(
            "INSERT OR IGNORE INTO ingestion_batches VALUES (?,?,?,?,?)",
            (batch_id, source_id, datetime.now(UTC).isoformat(), "INGESTED", notes),
        )
        self.db.commit()

    def add_artifact(self, row: dict):
        columns = ", ".join(row)
        self.db.execute(
            f"INSERT OR IGNORE INTO source_artifacts ({columns}) VALUES ({','.join('?' for _ in row)})",
            tuple(row.values()),
        )
        self.db.commit()

    def add_candidate(self, row: dict):
        columns = ", ".join(row)
        self.db.execute(
            f"INSERT OR REPLACE INTO candidate_records ({columns}) VALUES ({','.join('?' for _ in row)})",
            tuple(row.values()),
        )
        self.db.commit()

    def review(
        self, review_id: str, batch_id: str, candidate_id: str, reason: str, detail_json: str
    ):
        self.db.execute(
            "INSERT OR IGNORE INTO review_queue(review_id,batch_id,candidate_id,reason,status,detail_json,created_at) VALUES (?,?,?,?,?,?,?)",
            (
                review_id,
                batch_id,
                candidate_id,
                reason,
                "PENDING",
                detail_json,
                datetime.now(UTC).isoformat(),
            ),
        )
        self.db.commit()

    def decide_review(
        self, review_id: str, status: str, note: str = "", reviewed_type: str | None = None
    ):
        if status not in {"APPROVED", "REJECTED", "NEEDS_MAPPING", "AMBIGUOUS"}:
            raise ValueError("invalid review status")
        row = self.db.execute(
            "SELECT candidate_id FROM review_queue WHERE review_id=?", (review_id,)
        ).fetchone()
        if row is None:
            raise LookupError(review_id)
        original = self.db.execute(
            "SELECT candidate_type FROM candidate_records WHERE candidate_id=?", (row[0],)
        ).fetchone()
        self.db.execute(
            "UPDATE review_queue SET status=?, reviewer_note=?, reviewed_type=?, reviewed_at=?, original_type=COALESCE(original_type,?) WHERE review_id=?",
            (
                status,
                note,
                reviewed_type,
                datetime.now(UTC).isoformat(),
                original[0] if original else None,
                review_id,
            ),
        )
        self.db.execute(
            "UPDATE candidate_records SET status=?, validation_error=? WHERE candidate_id=?",
            ("VALIDATED" if status == "APPROVED" else status, note or status, row[0]),
        )
        self.db.commit()
