#!/usr/bin/env python3
"""Back up registry and deterministically collapse superseded FLEX passage identities."""

import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.phase1 import segment_document

s = Settings()
backup = s.registry_path.with_name(
    f"evidence.pre-phase1-fts-migration-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}.sqlite"
)
shutil.copy2(s.registry_path, backup)
r = EvidenceRegistry(s.registry_path)
# FLEX had no candidates/canonical claim refs. Its old duplicate passages are exact
# migration targets; preserve source artifact/raw PDF and regenerate v2 IDs.
old = [
    x[0]
    for x in r.db.execute("select evidence_id from passages where document_id='ntrs-20150023456'")
]
r.db.executemany("delete from passages_fts where evidence_id=?", [(x,) for x in old])
r.db.execute("delete from passages where document_id='ntrs-20150023456'")
r.db.commit()
ids = segment_document(
    ROOT / "data/raw/ntrs-20150023456.pdf", "ntrs-20150023456", "ntrs-20150023456", r
)
r.rebuild_fts()
print(
    {
        "backup": str(backup),
        "removed_old": len(old),
        "current": len(ids),
        "fts": r.db.execute("select count(*) from passages_fts").fetchone()[0],
    }
)
