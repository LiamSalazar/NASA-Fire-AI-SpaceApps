#!/usr/bin/env python3
"""Collapse duplicate evidence locations without touching raw artifacts or claims."""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry

r = EvidenceRegistry(Settings().registry_path)
referenced = set()
for path in (ROOT / "data/canonical").glob("*.json"):
    try:
        for item in json.loads(path.read_text()):
            for ref in item.get("evidence_refs", []):
                referenced.add(ref.get("evidence_id"))
    except (json.JSONDecodeError, TypeError):
        pass
groups = r.db.execute(
    """select document_id,checksum,page,start_offset
    from passages
    where checksum is not null and start_offset is not null
    group by document_id,checksum,page,start_offset having count(*)>1"""
).fetchall()
removed = 0
migrated = 0
for g in groups:
    rows = r.db.execute(
        "select evidence_id from passages where document_id=? and checksum is ? and page is ? and start_offset is ?",
        tuple(g),
    ).fetchall()
    ids = [x[0] for x in rows]
    keep = (
        next((x for x in ids if x in referenced), None)
        or next((x for x in ids if re.fullmatch(r"E-[0-9a-f]{16}", x)), None)
        or min(ids)
    )
    for old in ids:
        if old == keep:
            continue
        for c in r.db.execute(
            "select candidate_id,payload_json from candidate_records where evidence_id=?", (old,)
        ).fetchall():
            payload = json.loads(c["payload_json"])
            payload["evidence_id"] = keep
            r.db.execute(
                "update candidate_records set evidence_id=?,payload_json=? where candidate_id=?",
                (keep, json.dumps(payload), c["candidate_id"]),
            )
            migrated += 1
        r.db.execute("delete from passages where evidence_id=?", (old,))
        removed += 1
r.rebuild_fts()
print(
    {
        "groups": len(groups),
        "removed": removed,
        "candidate_refs_migrated": migrated,
        "passages": r.db.execute("select count(*) from passages").fetchone()[0],
        "fts": r.db.execute("select count(*) from passages_fts").fetchone()[0],
    }
)
