"""Freeze the pre-publication evidence universe from preserved historical identities."""

import hashlib
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "data/index/phase3c_targeted_existing_snapshot_v1.sqlite"
assert not path.exists()
source = sqlite3.connect(ROOT / "data/index/evidence.sqlite")
snapshot = sqlite3.connect(path)
source.backup(snapshot)
snapshot.execute("DELETE FROM passages_fts WHERE evidence_id LIKE 'E-targeted-%'")
snapshot.execute("DELETE FROM evidence_refs WHERE evidence_id LIKE 'E-targeted-%'")
snapshot.execute("DELETE FROM passages WHERE evidence_id LIKE 'E-targeted-%'")
snapshot.execute("DELETE FROM documents WHERE document_id LIKE '%-targeted-table-v1'")
ids = [
    r["source_id"]
    for r in json.loads(
        (ROOT / "artifacts/phase3c_enrichment_source_inventory_v1.json").read_text()
    )
]
snapshot.execute(
    "DELETE FROM sources WHERE source_id NOT IN (SELECT value FROM json_each(?))",
    (json.dumps(ids),),
)
snapshot.commit()
counts = {
    table: snapshot.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
    for table in ["sources", "documents", "passages"]
}
snapshot.close()
receipt = ROOT / "artifacts/phase3c_targeted_corpus_snapshot_v1.json"
assert not receipt.exists()
receipt.write_text(
    json.dumps(
        {
            "path": str(path.relative_to(ROOT)),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "counts": counts,
            "method": "SQLite backup with only additive targeted documents/passages/sources removed; preserved legacy evidence identities. Operational caches not scientific inputs.",
        },
        indent=2,
    )
)
print(counts)
