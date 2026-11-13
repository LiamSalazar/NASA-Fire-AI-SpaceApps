#!/usr/bin/env python3
"""Offline end-to-end retrieval demonstrations; output is extractive only."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.query import parse_query
from nasa_fire_ai.services import build_bundle, render

queries = [
    "What has NASA reported about suppressing PMMA fires in microgravity, what interventions were tested, what outcomes were observed, what safety implications were stated, and what questions remain explicitly open?",
    "Compare the indexed SAFFIRE-I experimental runs and show their reported conditions and outcomes.",
    "Find SIBAL Fabric microgravity airflow <= 0.10 m/s.",
]
registry = EvidenceRegistry(Settings().registry_path)
for query in queries:
    intent = parse_query(query)
    bundle = build_bundle(intent, query, ROOT, registry)
    print(f"\nQUERY: {query}\nINTENT: {intent.model_dump_json()}\n{render(bundle)}")
