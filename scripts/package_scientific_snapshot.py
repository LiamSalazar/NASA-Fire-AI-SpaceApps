"""Package a verified snapshot, its exact inputs and optional vector generation."""

import argparse
import hashlib
import json
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nasa_fire_ai.ingestion.hackathon import verify_snapshot


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--vectors", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = verify_snapshot(args.snapshot, ROOT)
    metadata = json.loads((args.vectors / "documentary.metadata.json").read_text())
    if metadata["snapshot_id"] != manifest["snapshot_id"]:
        raise ValueError("Vector snapshot mismatch")
    paths = [ROOT / p for p in manifest["inputs"]]
    paths += [args.snapshot / p for p in ["manifest.json", *manifest["artifacts"]]]
    paths.append(args.vectors / "documentary.metadata.json")
    for kind in ("ids", "vectors"):
        name = metadata[kind + "_file"]
        if Path(name).name != name:
            raise ValueError("Invalid vector path")
        path = args.vectors / name
        if hashlib.sha256(path.read_bytes()).hexdigest() != metadata[kind + "_sha256"]:
            raise ValueError("Vector checksum mismatch")
        paths.append(path)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(args.output, "x:gz") as archive:
        for path in sorted({p.resolve() for p in paths}):
            archive.add(path, arcname=str(path.relative_to(ROOT)))
    print(
        json.dumps(
            {
                "snapshot_id": manifest["snapshot_id"],
                "files": len(set(paths)),
                "package_sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(),
            }
        )
    )


if __name__ == "__main__":
    main()
