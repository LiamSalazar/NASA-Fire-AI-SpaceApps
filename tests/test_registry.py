from nasa_fire_ai.evidence import EvidenceRegistry


def test_fts_and_resolution_without_api_key(tmp_path):
    r = EvidenceRegistry(tmp_path / "x.sqlite")
    r.add_passage(
        {
            "evidence_id": "E1",
            "document_id": "D",
            "page": 1,
            "section": None,
            "text": "microgravity flame spread evidence",
            "start_offset": 0,
            "end_offset": 36,
            "raw_file": "x.pdf",
            "checksum": "a",
        }
    )
    assert r.search("microgravity")[0]["evidence_id"] == "E1"
    assert r.resolve("E1")["page"] == 1


def test_document_metadata_and_evidence_reference_are_registry_only(tmp_path):
    r = EvidenceRegistry(tmp_path / "x.sqlite")
    r.add_document("d", "ntrs-1", "NASA title")
    r.add_document_metadata("d", {"authors": "NASA", "verification_status": "catalog verified"})
    r.add_passage(
        {
            "evidence_id": "E2",
            "document_id": "d",
            "page": 1,
            "section": "Abstract",
            "text": "documentary text",
            "start_offset": 0,
            "end_offset": 16,
            "raw_file": "x.txt",
            "checksum": "checksum",
        }
    )
    assert (
        r.db.execute("select source_id from evidence_refs where evidence_id='E2'").fetchone()[0]
        == "ntrs-1"
    )
    assert (
        r.db.execute("select authors from document_metadata where document_id='d'").fetchone()[0]
        == "NASA"
    )
