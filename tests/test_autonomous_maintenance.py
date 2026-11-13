import json

import httpx
import pymupdf
import pytest

from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.autonomous import (
    KnowledgeMaintenance,
    official_download,
    registry_checks,
)


def metadata():
    return {
        "id": 123,
        "title": "Synthetic controlled source fixture",
        "distribution": "PUBLIC",
        "downloads": [
            {
                "mimetype": "application/pdf",
                "links": {"pdf": "/api/citations/123/downloads/test.pdf"},
            }
        ],
    }


def pdf():
    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_text((72, 72), "Synthetic fixture: no flame was observed.")
        return document.tobytes()


class Adapter:
    def fetch_metadata(self, identifier):
        return metadata()


def pipeline(tmp_path):
    return KnowledgeMaintenance(tmp_path, EvidenceRegistry(tmp_path / "evidence.sqlite"), Adapter())


def test_dry_run_does_not_create_pipeline_state(tmp_path):
    instance = pipeline(tmp_path)
    before = list(instance.registry.db.iterdump())
    assert instance.update("123")["status"] == "ACQUISITION_PENDING"
    assert before == list(instance.registry.db.iterdump())


def test_publication_idempotence_and_rollback(tmp_path, monkeypatch):
    instance = pipeline(tmp_path)
    requests = []
    content = pdf()

    def handler(request):
        requests.append(request)
        return httpx.Response(200, content=content)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(httpx, "stream", client.stream)
    first = instance.update("123", dry_run=False)
    assert first["status"] == "PUBLISHED"
    second = instance.update("123", dry_run=False)
    assert second["status"] == "UNCHANGED" and len(requests) == 1
    assert not second["index_rebuilt"]
    eid = first["evidence_ids"][0]
    assert instance.registry.resolve(eid)["page_location_verified"]
    assert registry_checks(instance.registry)["sqlite_integrity"] == "ok"
    invalid = instance.stage({"evidence_id": eid, "evidence_span": "fabricated observation"})
    assert invalid["status"] == "REJECTED"
    proposal = {"evidence_id": eid, "evidence_span": "no flame was observed."}
    assert instance.stage(proposal)["status"] == "STAGED_CANDIDATE"
    instance.stage(proposal)
    assert len(instance.registry.staged_semantic_candidates()) == 1
    assert instance.rollback_document(first["source_id"])["raw_preserved"]
    assert instance.registry.resolve(eid) is not None
    assert instance.registry.search("flame") == []
    assert list((tmp_path / "data/raw/autonomous").glob("*.pdf"))


def test_invalid_pdf_quarantined_without_registry_pollution(tmp_path, monkeypatch):
    instance = pipeline(tmp_path)
    client = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, content=b"not a PDF"))
    )
    monkeypatch.setattr(httpx, "stream", client.stream)
    result = instance.update("123", dry_run=False)
    assert result["status"] == "QUARANTINED"
    assert instance.registry.db.execute("SELECT count(*) FROM documents").fetchone()[0] == 0
    assert (
        json.loads(
            instance.registry.db.execute(
                "SELECT receipt_json FROM maintenance_versions"
            ).fetchone()[0]
        )["canonical_scientific_changes"]
        == 0
    )


def test_external_or_private_download_rejected():
    data = metadata()
    data["downloads"][0]["links"]["pdf"] = (
        "https://example.com/api/citations/123/downloads/test.pdf"
    )
    with pytest.raises(ValueError):
        official_download(data)


def test_atomic_publication_failure_retains_consistent_database(tmp_path, monkeypatch):
    instance = pipeline(tmp_path)
    client = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, content=pdf()))
    )
    monkeypatch.setattr(httpx, "stream", client.stream)
    original = registry_checks

    def failed_gate(registry):
        return {**original(registry), "missing_fts": 1}

    monkeypatch.setattr("nasa_fire_ai.ingestion.autonomous.registry_checks", failed_gate)
    result = instance.update("123", dry_run=False)
    assert result["status"] == "QUARANTINED"
    assert instance.registry.db.execute("SELECT count(*) FROM documents").fetchone()[0] == 0
    assert original(instance.registry)["sqlite_integrity"] == "ok"
    monkeypatch.setattr("nasa_fire_ai.ingestion.autonomous.registry_checks", original)
    recovered = instance.update("123", dry_run=False)
    assert recovered["status"] == "PUBLISHED"
    assert original(instance.registry)["missing_fts"] == 0


def test_changed_content_supersedes_document_and_rollback_restores(tmp_path, monkeypatch):
    instance = pipeline(tmp_path)
    values = [pdf()]
    client = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, content=values[0]))
    )
    monkeypatch.setattr(httpx, "stream", client.stream)
    first = instance.update("123", dry_run=False)
    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_text((72, 72), "Synthetic revision fixture, not NASA data.")
        values[0] = document.tobytes()
    second = instance.update("123", dry_run=False, refresh=True)
    assert second["status"] == "PUBLISHED"
    assert second["superseded_document_sources"] == [first["source_id"]]
    assert (
        instance.registry.db.execute(
            "SELECT status FROM sources WHERE source_id=?", (first["source_id"],)
        ).fetchone()[0]
        == "SUPERSEDED_DOCUMENT"
    )
    assert instance.registry.resolve(first["evidence_ids"][0])
    instance.rollback_document(second["source_id"])
    assert (
        instance.registry.db.execute(
            "SELECT status FROM sources WHERE source_id=?", (first["source_id"],)
        ).fetchone()[0]
        == "DOCUMENT_VERIFIED"
    )
    assert len(list((tmp_path / "data/raw/autonomous").glob("*.pdf"))) == 2


def test_context_value_not_established_by_correct_citation_is_rejected(tmp_path, monkeypatch):
    from pathlib import Path

    instance = pipeline(tmp_path)
    client = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, content=pdf()))
    )
    monkeypatch.setattr(httpx, "stream", client.stream)
    first = instance.update("123", dry_run=False)
    instance.root = Path(__file__).resolve().parents[1]
    eid = first["evidence_ids"][0]
    span = "no flame was observed."
    result = instance.stage(
        {
            "evidence_id": eid,
            "evidence_span": span,
            "contextual_proposal": {
                "candidate_predicate": "hasGravityCondition",
                "object_value": "microgravity",
                "support_spans": [{"evidence_id": eid, "text": span}],
            },
        }
    )
    assert result["status"] == "REJECTED"
    assert "contextual value" in result["reason"]
    data = metadata()
    data["distribution"] = "PRIVATE"
    with pytest.raises(ValueError):
        official_download(data)
