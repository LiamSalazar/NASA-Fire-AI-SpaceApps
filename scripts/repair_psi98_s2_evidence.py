"""Restore the missing managed PSI-98 S2 table passage from immutable raw input.

This is an idempotent Evidence Registry repair: it neither changes the official
CSV nor changes canonical scientific assertions. The canonical records already
referenced the stable S2 evidence identity.
"""

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry


def main() -> None:
    raw_path = ROOT / "data/raw/psi/PSI-98_experimental_table.csv"
    raw_bytes = raw_path.read_bytes()
    lines = raw_bytes.decode("utf-8").splitlines(keepends=True)
    line = next((value for value in lines if value.startswith("S2,")), None)
    if line is None:
        raise SystemExit("official PSI-98 S2 row is absent from immutable raw table")
    text = line.rstrip("\r\n")
    start = sum(len(value.encode("utf-8")) for value in lines[: lines.index(line)])
    registry = EvidenceRegistry(Settings().registry_path)
    registry.add_passage(
        {
            "evidence_id": "E-psi-98-table-S2",
            "document_id": "psi-98-experimental-table",
            "page": None,
            "section": "Experimental table",
            "text": text,
            "start_offset": start,
            "end_offset": start + len(line.rstrip("\r\n").encode("utf-8")),
            "raw_file": "psi/PSI-98_experimental_table.csv",
            "checksum": hashlib.sha256(raw_bytes).hexdigest(),
        }
    )
    print("restored managed evidence passage E-psi-98-table-S2")


if __name__ == "__main__":
    main()
