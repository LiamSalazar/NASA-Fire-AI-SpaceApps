"""Acquire only the pinned team tables and nine official PSI experimental tables."""

import hashlib
import json
import sys
from pathlib import Path
from urllib.parse import quote

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nasa_fire_ai.ingestion.hackathon import digest
from nasa_fire_ai.ingestion.psi import PSIClient

TEAM_COMMIT = "02d00164e3baf3c594c749972c51944dce5b492e"
IDS = ["PSI-98", "PSI-69", "PSI-101", "PSI-102", "PSI-25", "PSI-26", "PSI-99", "PSI-100", "PSI-68"]
STANDARD_URL = (
    "https://standards.nasa.gov/sites/default/files/standards/NASA/B-w/CHANGE-3/3/"
    "2025_06_25_NASA-STD-6001B_w_Change_3_FINAL_Admin-Change-FINAL.pdf"
)


def preserve(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != content:
            raise ValueError("Immutable input differs: " + str(path))
    else:
        with path.open("xb") as stream:
            stream.write(content)


def main():
    receipt_dir = ROOT / "artifacts/hackathon"
    receipt_dir.mkdir(exist_ok=True)
    with httpx.Client(timeout=60, follow_redirects=True) as client:
        response = client.get(
            f"https://api.github.com/repos/Krypton-N/NASA-SPACE-APPS/git/trees/{TEAM_COMMIT}?recursive=1"
        )
        response.raise_for_status()
        tree = response.json()
        inventory = []
        for item in tree["tree"]:
            name = item["path"]
            selected = name.startswith("data/clean/") or (
                name.startswith("data/psi/")
                and "/Experimental table/" in name
                and any("/" + sid + "_" in name for sid in IDS)
            )
            if item["type"] != "blob" or not selected:
                continue
            if item["size"] > 2_000_000:
                raise ValueError("Acquisition limit exceeded")
            path = ROOT / "data/raw/hackathon-team" / name
            if not path.exists():
                response = client.get(
                    f"https://raw.githubusercontent.com/Krypton-N/NASA-SPACE-APPS/{TEAM_COMMIT}/{quote(name)}"
                )
                response.raise_for_status()
                preserve(path, response.content)
            content = path.read_bytes()
            blob = hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()
            if blob != item["sha"]:
                raise ValueError("Git blob mismatch: " + name)
            inventory.append(
                {
                    "path": str(path.relative_to(ROOT)),
                    "upstream_path": name,
                    "git_blob": blob,
                    "sha256": digest(path),
                    "bytes": len(content),
                }
            )
        (receipt_dir / "team_inventory.json").write_text(
            json.dumps({"commit": TEAM_COMMIT, "files": inventory}, indent=2)
        )
        standard = ROOT / "data/raw/hackathon-standards/NASA-STD-6001B-change3.pdf"
        if not standard.exists():
            response = client.get(STANDARD_URL)
            response.raise_for_status()
            if len(response.content) > 5_000_000 or not response.content.startswith(b"%PDF"):
                raise ValueError("Invalid standard download")
            preserve(standard, response.content)
        (receipt_dir / "standard.json").write_text(
            json.dumps(
                {
                    "path": str(standard.relative_to(ROOT)),
                    "url": STANDARD_URL,
                    "sha256": digest(standard),
                    "source_id": "nasa-std-6001b-change3",
                    "title": "NASA-STD-6001B with Change 3",
                    "source_type": "NASA Standard",
                },
                indent=2,
            )
        )
    psi = PSIClient(ROOT / "data/raw/hackathon-psi")
    receipts = []
    for sid in IDS:
        table = psi.get_experimental_table(sid)
        receipts.append(
            {
                "source_id": sid,
                "path": str(table.cache_path.relative_to(ROOT)),
                "url": table.source_url,
                "sha256": digest(table.cache_path),
            }
        )
    (receipt_dir / "official_tables.json").write_text(json.dumps(receipts, indent=2))
    print(
        json.dumps(
            {
                "team_files": len(inventory),
                "official_tables": len(receipts),
                "standard": str(standard.relative_to(ROOT)),
            }
        )
    )


if __name__ == "__main__":
    main()
