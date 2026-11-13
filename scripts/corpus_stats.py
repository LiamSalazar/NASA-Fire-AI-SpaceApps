#!/usr/bin/env python3
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
records = (
    json.loads((ROOT / "data/canonical/records.json").read_text())
    if (ROOT / "data/canonical/records.json").exists()
    else []
)
db = sqlite3.connect(ROOT / "data/index/evidence.sqlite")


def count(table):
    return db.execute(f"SELECT count(*) FROM {table}").fetchone()[0]


by_type = {}
for r in records:
    by_type[r["type"]] = by_type.get(r["type"], 0) + 1
print(
    json.dumps(
        {
            "canonical_entities": len(records),
            "canonical_by_type": by_type,
            "sources": count("sources"),
            "documents": count("documents"),
            "fts_passages": count("passages"),
            "candidate_records": count("candidate_records"),
            "review_pending": db.execute(
                "SELECT count(*) FROM review_queue WHERE status='PENDING'"
            ).fetchone()[0],
        },
        indent=2,
    )
)
