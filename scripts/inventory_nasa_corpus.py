#!/usr/bin/env python3
"""Validate and report the curated official-source inventory; it does not crawl."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
catalog = yaml.safe_load((ROOT / "data/catalog/nasa_fire_corpus.yaml").read_text())
for item in catalog["sources"]:
    if item["ingestion_status"] != "not_ingested" and not item.get("canonical_url"):
        raise SystemExit(f"missing canonical URL for {item['source_id']}")
print(
    {
        "catalog_records": len(catalog["sources"]),
        "ingested": sum(x["ingestion_status"].startswith("ingested") for x in catalog["sources"]),
        "pending": sum(x["ingestion_status"] == "not_ingested" for x in catalog["sources"]),
    }
)
