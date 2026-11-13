#!/usr/bin/env python3
"""Fetch/cache NASA PSI data, then create PSI-98 canonical records from raw CSV."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nasa_fire_ai.ingestion import PSIClient, parse_experimental_table
from nasa_fire_ai.ingestion.psi_canonical import canonicalize_psi25_b1, canonicalize_psi98


def main():
    client = PSIClient(ROOT / "data/raw/psi")
    psi98_metadata = client.get_investigation("PSI-98")
    client.get_versions("PSI-98")
    psi98_files = client.list_files("PSI-98")
    table = client.get_experimental_table("PSI-98")
    entities, runs = canonicalize_psi98(parse_experimental_table(table.value), table.cache_path)
    canonical = ROOT / "data/canonical"
    canonical.mkdir(parents=True, exist_ok=True)
    (canonical / "psi98_records.json").write_text(json.dumps(entities, indent=2))
    (canonical / "runs.json").write_text(json.dumps(runs, indent=2))
    # PSI-25 table supports a deliberately small clean-row sample, not bulk ingestion.
    client.get_investigation("PSI-25")
    client.get_versions("PSI-25")
    client.list_files("PSI-25")
    psi25_table = client.get_experimental_table("PSI-25")
    psi25_entities, _ = canonicalize_psi25_b1(parse_experimental_table(psi25_table.value))
    (canonical / "psi25_records.json").write_text(json.dumps(psi25_entities, indent=2))
    print(
        json.dumps(
            {
                "psi98_rows": len(runs),
                "psi98_file_groups": len(psi98_files.value["files"]),
                "psi25_rows": 1 if psi25_entities else 0,
                "metadata": str(psi98_metadata.cache_path),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
