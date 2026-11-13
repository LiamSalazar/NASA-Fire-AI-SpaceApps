from nasa_fire_ai.evidence import EvidenceRegistry


def test_registry_passage_replacement_is_idempotent(tmp_path):
    registry = EvidenceRegistry(tmp_path / "evidence.sqlite")
    registry.add_document("psi-98-experimental-table", "psi-98", "table")
    row = {
        "evidence_id": "E-psi-98-table-S2",
        "document_id": "psi-98-experimental-table",
        "page": None,
        "section": "Experimental table",
        "text": "S2,official row",
        "start_offset": 10,
        "end_offset": 25,
        "raw_file": "psi/PSI-98_experimental_table.csv",
        "checksum": "fixture",
    }
    registry.add_passage(row)
    registry.add_passage(row)
    assert registry.resolve(row["evidence_id"])["text"] == row["text"]
    assert registry.db.execute("SELECT count(*) FROM passages_fts").fetchone()[0] == 1
