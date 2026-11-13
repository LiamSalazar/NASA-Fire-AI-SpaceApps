"""Fresh parity with explicit intent, snapshot and discrepancy receipts."""

import importlib.util
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "native_campaign", ROOT / "scripts/phase3c_native_benchmarks.py"
)
campaign = importlib.util.module_from_spec(spec)
spec.loader.exec_module(campaign)
OUT = ROOT / "artifacts/phase3c_knowledge_native_checks_v1"
OUT.mkdir(exist_ok=True)
campaign.ART = OUT
campaign.check_freeze = lambda: None
os.environ["ONTOLOGY_GRAPH_ENRICHMENT_ENABLED"] = "false"
campaign.parity()
