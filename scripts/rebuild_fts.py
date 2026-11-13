#!/usr/bin/env python3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry

registry = EvidenceRegistry(Settings().registry_path)
registry.rebuild_fts()
print({"fts_passages": registry.db.execute("SELECT count(*) FROM passages_fts").fetchone()[0]})
