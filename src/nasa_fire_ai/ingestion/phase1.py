"""Reusable, conservative Phase-1 ingestion primitives.

Raw acquisition, candidate extraction, review and publication are deliberately
separate.  This module remains usable with neither network nor LLM credentials.
"""

import csv
import hashlib
import json
import logging
import mimetypes
import re
import urllib.request
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from urllib.error import HTTPError, URLError

from pydantic import BaseModel, model_validator

from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.pdf import extract_pdf
from nasa_fire_ai.normalization import normalize

LOG = logging.getLogger(__name__)


class Artifact(BaseModel):
    artifact_id: str
    source_id: str
    canonical_url: str
    filename: str
    source_type: str
    investigation_id: str | None = None
    document_id: str | None = None
    doi: str | None = None
    source_version: str | None = None
    mime_type: str | None = None
    known_size: int | None = None


class SourceAdapter(ABC):
    """Cache-first adapter contract. Adapters never publish domain facts."""

    @abstractmethod
    def discover(self, query: str | None = None) -> list[dict]: ...
    @abstractmethod
    def fetch_metadata(self, source_id: str) -> dict: ...
    @abstractmethod
    def list_artifacts(self, source_id: str) -> list[Artifact]: ...
    @abstractmethod
    def fetch_artifact(self, artifact: Artifact, raw_dir: Path) -> Path | None: ...
    @abstractmethod
    def fingerprint(self, artifact: Artifact) -> str: ...


class PSIAdapter(SourceAdapter):
    def __init__(self, raw_dir: Path):
        from nasa_fire_ai.ingestion.psi import PSIClient

        self.client = PSIClient(raw_dir)

    def discover(self, query: str | None = None) -> list[dict]:
        return []

    def fetch_metadata(self, source_id: str) -> dict:
        return self.client.get_investigation(source_id).value

    def list_artifacts(self, source_id: str) -> list[Artifact]:
        return [
            Artifact(
                artifact_id=f"{source_id}:experimental-table",
                source_id=source_id,
                investigation_id=source_id,
                document_id=f"{source_id}-experimental-table",
                source_type="PSI experimental table",
                canonical_url=f"https://psi.nasa.gov/geode-py/ws/studies/{source_id}/download",
                filename=f"{source_id}_experimental_table.csv",
                mime_type="text/csv",
            )
        ]

    def fetch_artifact(self, artifact: Artifact, raw_dir: Path) -> Path | None:
        return self.client.get_experimental_table(artifact.source_id).cache_path

    def fingerprint(self, artifact: Artifact) -> str:
        return hashlib.sha256(
            json.dumps(self.fetch_metadata(artifact.source_id), sort_keys=True).encode()
        ).hexdigest()


class HTTPMetadataAdapter(SourceAdapter):
    """Generic official-URL adapter for local files and small official documents."""

    def discover(self, query: str | None = None) -> list[dict]:
        return []

    def fetch_metadata(self, source_id: str) -> dict:
        return {"source_id": source_id}

    def list_artifacts(self, source_id: str) -> list[Artifact]:
        return []

    def fingerprint(self, artifact: Artifact) -> str:
        return hashlib.sha256(artifact.canonical_url.encode()).hexdigest()

    def fetch_artifact(self, artifact: Artifact, raw_dir: Path) -> Path | None:
        destination = raw_dir / artifact.filename
        if destination.exists():
            return destination
        limit = Settings().max_single_download_mb * 1024**2
        if artifact.known_size and artifact.known_size > limit:
            return None
        try:
            request = urllib.request.Request(
                artifact.canonical_url, headers={"User-Agent": "nasa-fire-ai-phase1/0.1"}
            )
            with urllib.request.urlopen(request, timeout=60) as response:
                content = response.read(limit + 1)
            if len(content) > limit:
                return None
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
            return destination
        except (HTTPError, OSError, URLError) as exc:
            LOG.warning("official artifact fetch failed: %s", type(exc).__name__)
            return None


class NTRSAdapter(HTTPMetadataAdapter):
    """NTRS adapter boundary; callers supply a verified NTRS identifier/URL."""

    def fetch_metadata(self, source_id: str) -> dict:
        import httpx

        if not source_id.isdecimal():
            raise ValueError("NTRS identifier must be numeric")
        response = httpx.get(f"https://ntrs.nasa.gov/api/citations/{source_id}", timeout=25)
        response.raise_for_status()
        metadata = response.json()
        if str(metadata.get("id")) != source_id:
            raise ValueError("NTRS returned a different citation identity")
        return metadata

    def discover(self, query: str | None = None) -> list[dict]:
        import httpx

        if not query:
            return []
        response = httpx.get(
            "https://ntrs.nasa.gov/api/citations/search",
            params={"q": query, "page.size": 12},
            timeout=25,
        )
        response.raise_for_status()
        return response.json().get("results", [])[:12]

    def list_artifacts(self, source_id: str) -> list[Artifact]:
        metadata = self.fetch_metadata(source_id)
        return [
            Artifact(
                artifact_id=f"ntrs-{source_id}:{index}",
                source_id=source_id,
                source_type="NTRS",
                document_id=f"ntrs-{source_id}",
                canonical_url="https://ntrs.nasa.gov" + download["links"]["pdf"],
                filename=f"ntrs-{source_id}-{index}.pdf",
                source_version=metadata.get("modified"),
                mime_type="application/pdf",
            )
            for index, download in enumerate(metadata.get("downloads", []))
            if download.get("mimetype") == "application/pdf"
            and download.get("links", {})
            .get("pdf", "")
            .startswith(f"/api/citations/{source_id}/downloads/")
            and not download.get("draft")
        ]


class NASAStandardsAdapter(HTTPMetadataAdapter):
    """Standards are explicit URLs; no unofficial mirror fallback is permitted."""


class TaskBookAdapter(HTTPMetadataAdapter):
    """Task Book metadata is documentary context, never treated as raw observations."""


class CandidateRecord(BaseModel):
    candidate_id: str
    candidate_type: Literal[
        "CandidateMeasurementObservation",
        "CandidateReportedExperimentalObservation",
        "CandidateIntervention",
        "CandidateNASAConclusion",
        "CandidateSafetyImplication",
        "CandidateOpenQuestion",
        "CandidateRequirement",
        "CandidateGuidance",
        "CandidateDesignCriterion",
        "CandidateTestCriterion",
        "CandidatePublicationRelation",
        "CandidateOntologyConcept",
    ]
    normalized_text: str | None = None
    evidence_id: str
    source_document: str
    page: int | None = None
    section: str | None = None
    extraction_method: Literal["structured", "deterministic", "llm"]
    extraction_model: str | None = None
    prompt_version: str | None = None
    term: str | None = None
    source_context: str | None = None
    evidence_span: str | None = None
    local_heading: str | None = None
    source_type: str | None = None
    scope: str | None = None
    uncertainty: str | None = None
    modality: str | None = None
    negation: bool | None = None
    reported_value: float | str | None = None
    reported_unit: str | None = None
    reported_range: str | None = None
    approximation_marker: bool | None = None
    canonical_value: float | None = None
    canonical_unit: str | None = None

    @model_validator(mode="after")
    def requires_explicit_evidence(self):
        if not self.evidence_id or (
            not self.normalized_text and self.candidate_type != "CandidateOntologyConcept"
        ):
            raise ValueError("candidate requires evidence and explicit extracted text")
        if self.extraction_method == "llm" and not self.evidence_span:
            raise ValueError("LLM candidate requires exact evidence_span")
        return self


def checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_id(prefix: str, *parts: str) -> str:
    return f"{prefix}-{hashlib.sha256('|'.join(parts).encode()).hexdigest()[:16]}"


def append_raw_manifest(
    settings: Settings, artifact: Artifact, path: Path, status: str = "fetched"
) -> None:
    """Append only new checksum identities; never edits an existing raw entry."""
    manifest_path = settings.raw_manifest_path
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else []
    digest = checksum(path) if path.exists() else None
    relative = str(path.relative_to(settings.root / "data/raw"))
    if any(
        x.get("source_id") == artifact.source_id
        and x.get("sha256") == digest
        and x.get("filename") == relative
        for x in manifest
    ):
        return
    manifest.append(
        {
            "source_id": artifact.source_id,
            "investigation_id": artifact.investigation_id,
            "document_id": artifact.document_id,
            "artifact_id": artifact.artifact_id,
            "source_type": artifact.source_type,
            "nasa_identifier": artifact.source_id,
            "canonical_url": artifact.canonical_url,
            "doi": artifact.doi,
            "retrieval_timestamp": datetime.now(UTC).isoformat(),
            "source_version": artifact.source_version,
            "filename": relative,
            "mime_type": artifact.mime_type or mimetypes.guess_type(path.name)[0],
            "file_size": path.stat().st_size,
            "sha256": digest,
            "ingestion_batch_id": stable_id("batch", artifact.source_id, digest),
            "status": status,
        }
    )
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")


def segment_document(
    path: Path, source_id: str, document_id: str, registry: EvidenceRegistry
) -> list[str]:
    artifact_checksum = checksum(path)
    # Completed versioned segments are immutable for an immutable raw artifact.
    # Reuse them instead of reopening a large PDF on unchanged re-ingestion.
    cached = registry.db.execute(
        "SELECT evidence_id FROM passages WHERE document_id=? AND checksum=? AND evidence_id LIKE 'E-%' ORDER BY page,start_offset",
        (document_id, artifact_checksum),
    ).fetchall()
    if cached:
        return [row[0] for row in cached]
    pages = (
        extract_pdf(path)
        if path.suffix.lower() == ".pdf"
        else [(1, path.read_text(errors="replace"))]
    )
    ids = []
    headings = re.compile(
        r"^(abstract|introduction|methods?|experimental setup|results?|discussion|conclusions?|requirements?|guidance|future work|recommendations?)$",
        re.IGNORECASE,
    )
    for page, raw in pages:
        text = "\n".join(line.strip() for line in raw.splitlines() if line.strip())
        section = next((line for line in text.splitlines()[:12] if headings.match(line)), None)
        for start in range(0, len(text), 3500):
            passage = text[start : start + 4000]
            if len(passage) < 80:
                continue
            # Text extraction can vary in harmless whitespace/order across
            # PyMuPDF versions. Identity is the immutable artifact checksum +
            # document/page/offset, not an extractor rendering of the passage.
            # Versioned identity: stable for an unchanged artifact/segmentation,
            # distinct for a NASA artifact checksum change.
            eid = stable_id(
                "E", document_id, artifact_checksum, "segment-v2", str(page), str(start)
            )
            registry.add_passage(
                {
                    "evidence_id": eid,
                    "document_id": document_id,
                    "page": page,
                    "section": section,
                    "text": passage,
                    "start_offset": start,
                    "end_offset": start + len(passage),
                    "raw_file": str(path),
                    "checksum": artifact_checksum,
                }
            )
            ids.append(eid)
    return ids


HEADER_KIND = {
    "Calibrated  initial O2 % by vol": ("initial_oxygen", "%"),
    "Calibrated final O2 % by vol": ("final_oxygen", "%"),
    "Initial CO2 % by vol": ("initial_co2", "%"),
    "Final CO2 % by vol": ("final_co2", "%"),
    "Initial CO (ppm)": ("initial_co", "ppm"),
    "Final CO (ppm)": ("final_co", "ppm"),
}


def structured_csv_candidates(
    path: Path, source_id: str, investigation_id: str, registry: EvidenceRegistry
) -> list[CandidateRecord]:
    """Schema-driven table ingestion; it never picks a run by source-specific ID."""
    candidates = []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row_number, row in enumerate(csv.DictReader(handle), start=2):
            run_key, material = (
                row.get("Test #") or row.get("Sample Number"),
                row.get("Fuel Sample Material") or row.get("Material"),
            )
            if not run_key or not material:
                continue
            run_id = f"{investigation_id}-{run_key.strip()}"
            line = ",".join(str(v or "") for v in row.values())
            eid = stable_id(
                "E", source_id, str(row_number), hashlib.sha256(line.encode()).hexdigest()
            )
            registry.add_passage(
                {
                    "evidence_id": eid,
                    "document_id": f"{source_id}-experimental-table",
                    "page": None,
                    "section": "Experimental table",
                    "text": line,
                    "start_offset": row_number,
                    "end_offset": row_number,
                    "raw_file": str(path),
                    "checksum": checksum(path),
                }
            )
            payload = {
                "record_type": "run",
                "id": run_id,
                "investigation_id": investigation_id,
                "sample_id": run_id + "-sample",
                "material": material.strip(),
                "conditions": [],
            }
            for header, (kind, unit) in HEADER_KIND.items():
                value = (row.get(header) or "").strip()
                if not value or value.lower() in {"none", "n/a", "na"}:
                    continue
                try:
                    reported = float(value)
                except ValueError:
                    continue
                try:
                    canonical, canonical_unit = normalize(reported, unit)
                except ValueError:
                    # A recognized table column may retain a source unit before a
                    # unit conversion is deliberately added; never invent one.
                    canonical, canonical_unit = None, None
                payload["conditions"].append(
                    {
                        "kind": kind,
                        "reported_value": reported,
                        "reported_unit": unit,
                        "canonical_value": canonical,
                        "canonical_unit": canonical_unit,
                    }
                )
            candidates.append(
                CandidateRecord(
                    candidate_id=stable_id("candidate", source_id, str(row_number)),
                    candidate_type="CandidateMeasurementObservation",
                    normalized_text=json.dumps(payload, sort_keys=True),
                    evidence_id=eid,
                    source_document=f"{source_id}-experimental-table",
                    section="Experimental table",
                    extraction_method="structured",
                )
            )
    return candidates


def validate_candidate(
    candidate: CandidateRecord, registry: EvidenceRegistry
) -> tuple[str, str | None]:
    if registry.resolve(candidate.evidence_id) is None:
        return "REJECTED", "evidence reference is unresolved"
    if candidate.candidate_type == "CandidateOntologyConcept":
        return "REVIEW_REQUIRED", "new terminology cannot create ontology vocabulary"
    if candidate.term and candidate.term.lower() == "acrylic":
        return "REVIEW_REQUIRED", "ambiguous controlled-lexicon mapping"
    high_risk = {
        "CandidateRequirement",
        "CandidateGuidance",
        "CandidateOpenQuestion",
        "CandidateNASAConclusion",
        "CandidateSafetyImplication",
    }
    if candidate.candidate_type in high_risk:
        if candidate.extraction_method == "llm":
            return "REVIEW_REQUIRED", "LLM-classified high-risk statement requires human review"
        if not candidate.source_context:
            return "REVIEW_REQUIRED", "high-risk statement lacks source-type/section context"
    if (
        candidate.extraction_method == "llm"
        and candidate.candidate_type == "CandidateReportedExperimentalObservation"
    ):
        return "REVIEW_REQUIRED", "LLM reported observation requires human review in Phase 1"
    if candidate.extraction_method == "llm" and candidate.candidate_type == "CandidateIntervention":
        text = (candidate.evidence_span or "").lower()
        if candidate.local_heading and candidate.local_heading.lower() in {
            "approach",
            "methods",
            "relevance/impact",
        }:
            return "REVIEW_REQUIRED", "method/approach text is not a performed intervention"
        if not re.search(r"\b(turned|used|applied|performed|stopped)\b", text):
            return "REVIEW_REQUIRED", "intervention lacks explicit performed-action wording"
    return "VALIDATED", None


def publish_validated(
    candidates: list[CandidateRecord], registry: EvidenceRegistry, output: Path
) -> int:
    """Only validated deterministic structured candidates enter canonical export."""
    existing = json.loads(output.read_text()) if output.exists() else []
    ids = {item.get("id") for item in existing}
    added = 0
    for candidate in candidates:
        status, _ = validate_candidate(candidate, registry)
        if status != "VALIDATED" or candidate.extraction_method != "structured":
            continue
        payload = json.loads(candidate.normalized_text or "{}")
        if payload.get("record_type") != "run" or payload["id"] in ids:
            continue
        evidence = [
            {
                "evidence_id": candidate.evidence_id,
                "source_id": payload["investigation_id"],
                "section": "Experimental table",
            }
        ]
        sample_id = payload["sample_id"]
        existing.append(
            {
                "type": "SampleRecord",
                "id": sample_id,
                "material": payload["material"],
                "evidence_refs": evidence,
            }
        )
        condition_ids = []
        for condition in payload["conditions"]:
            cid = f"{payload['id']}-{condition['kind']}"
            condition_ids.append(cid)
            existing.append(
                {"type": "ConditionRecord", "id": cid, **condition, "evidence_refs": evidence}
            )
        existing.append(
            {
                "type": "ExperimentalRunRecord",
                "id": payload["id"],
                "investigation_id": payload["investigation_id"],
                "sample_id": sample_id,
                "condition_ids": condition_ids,
                "evidence_refs": evidence,
            }
        )
        ids.add(payload["id"])
        added += 1
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(existing, indent=2) + "\n")
    return added
