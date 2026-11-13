"""Restore a scientific asset package without overwriting different existing files."""

import argparse
import hashlib
import json
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.hackathon import verify_snapshot
from nasa_fire_ai.retrieval.snapshot_vectors import SnapshotVectors


def restore(package, destination, expected):
    actual = hashlib.file_digest(package.open("rb"), "sha256").hexdigest()
    if actual != expected:
        raise ValueError("Package checksum mismatch")
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    created = existing = 0
    with tarfile.open(package, "r:gz") as archive:
        members = archive.getmembers()
        for member in members:
            path = Path(member.name)
            if not member.isfile() or path.is_absolute() or ".." in path.parts:
                raise ValueError("Invalid package member")
            target = destination / path
            if not target.resolve().is_relative_to(destination):
                raise ValueError("Escaping package path")
            if target.exists():
                with archive.extractfile(member) as source, target.open("rb") as present:
                    if (
                        hashlib.file_digest(source, "sha256").digest()
                        != hashlib.file_digest(present, "sha256").digest()
                    ):
                        raise ValueError("Existing file differs: " + member.name)
        for member in members:
            target = destination / member.name
            if target.exists():
                existing += 1
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.extractfile(member) as source, target.open("xb") as output:
                while chunk := source.read(1024 * 1024):
                    output.write(chunk)
            created += 1
    manifests = [
        destination / member.name
        for member in members
        if member.name.startswith("data/snapshots/") and member.name.endswith("/manifest.json")
    ]
    if len(manifests) != 1:
        raise ValueError("Expected exactly one restored snapshot")
    snapshot = manifests[0].parent
    manifest = verify_snapshot(snapshot, destination)
    vectors = destination / "data/index" / (snapshot.name + "-vectors")
    metadata = json.loads((vectors / "documentary.metadata.json").read_text())

    class IdentityOnly:
        def model_identity(self):
            return metadata["model_id"]

    registry = EvidenceRegistry(
        snapshot / "evidence.sqlite", read_only=True, evidence_root=destination
    )
    adapter = SnapshotVectors(vectors, registry, manifest["snapshot_id"], IdentityOnly())
    adapter.close()
    registry.db.close()
    return {
        "snapshot_id": manifest["snapshot_id"],
        "package_sha256": actual,
        "created_files": created,
        "identical_existing_files": existing,
        "snapshot_verified": True,
        "vectors_verified": True,
    }


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    args = parser.parse_args()
    print(json.dumps(restore(args.package, args.destination, args.sha256), indent=2))


if __name__ == "__main__":
    main()
