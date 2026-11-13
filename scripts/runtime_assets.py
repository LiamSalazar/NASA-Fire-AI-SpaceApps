"""Package or restore release-only assets alongside an exact Git checkout.

Never rebuilds scientific data. Originals already tracked by Git are recorded as
requirements rather than duplicated. Provider query/response caches are excluded.
"""

import argparse
import hashlib
import json
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

SNAPSHOT = "data/snapshots/hackathon-20261112-scientific-rc14"
VECTORS = "data/index/hackathon-20261112-scientific-rc14-vectors"
MODEL = "data/index/models/nasa-nli"


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def git(*args, root=ROOT):
    return subprocess.check_output(["git", "-C", str(root), *args]).decode().strip()


def details(root, relative):
    path = root / relative
    if not path.is_file() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("Missing or escaping runtime file: " + relative)
    return {"path": relative, "bytes": path.stat().st_size, "sha256": digest(path)}


def validate(root):
    from nasa_fire_ai.evidence import EvidenceRegistry
    from nasa_fire_ai.ingestion.hackathon import verify_snapshot
    from nasa_fire_ai.retrieval.snapshot_vectors import SnapshotVectors

    snapshot = verify_snapshot(root / SNAPSHOT, root)
    metadata = json.loads((root / VECTORS / "documentary.metadata.json").read_text())

    class IdentityOnly:
        def model_identity(self):
            return metadata["model_id"]

    registry = EvidenceRegistry(
        root / SNAPSHOT / "evidence.sqlite", read_only=True, evidence_root=root
    )
    try:
        assert registry.db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        for row in registry.db.execute(
            "SELECT DISTINCT raw_file FROM passages WHERE raw_file IS NOT NULL"
        ):
            details(root, row[0])
        vectors = SnapshotVectors(root / VECTORS, registry, snapshot["snapshot_id"], IdentityOnly())
        vectors.close()
    finally:
        registry.db.close()
    model = json.loads((root / MODEL / "manifest.json").read_text())
    for row in model["files"]:
        actual = details(root, MODEL + "/" + row["file"])
        if actual["sha256"] != row["sha256"] or actual["bytes"] != row["bytes"]:
            raise ValueError("Verifier asset mismatch")
    return snapshot, metadata, model


def inventory(root):
    manifest = json.loads((root / SNAPSHOT / "manifest.json").read_text())
    paths = set(manifest["inputs"])
    with sqlite3.connect(f"file:{root / SNAPSHOT}/evidence.sqlite?mode=ro", uri=True) as db:
        paths.update(
            row[0]
            for row in db.execute(
                "SELECT DISTINCT raw_file FROM passages WHERE raw_file IS NOT NULL"
            )
        )
    paths.update(SNAPSHOT + "/" + name for name in ["manifest.json", *manifest["artifacts"]])
    metadata = json.loads((root / VECTORS / "documentary.metadata.json").read_text())
    paths.update(
        VECTORS + "/" + name
        for name in ["documentary.metadata.json", metadata["vectors_file"], metadata["ids_file"]]
    )
    model = json.loads((root / MODEL / "manifest.json").read_text())
    paths.update(
        MODEL + "/" + name for name in ["manifest.json", *[r["file"] for r in model["files"]]]
    )
    tracked = set(git("ls-files", "-z", root=root).split("\0"))
    included = [details(root, p) for p in sorted(paths - tracked)]
    required = [details(root, p) for p in sorted(paths & tracked)]
    return included, required


def pack(output):
    snapshot, vectors, model = validate(ROOT)
    included, required = inventory(ROOT)
    total = sum(row["bytes"] for row in included)
    # Conservative bound prevents an incomplete archive when compression is poor.
    if shutil.disk_usage(output.parent).free < total + 32 * 1024**2:
        raise ValueError(
            f"Insufficient space: need {total + 32 * 1024**2} free bytes conservatively"
        )
    if git("branch", "--show-current") != "NASA_hackathon":
        raise ValueError("Expected NASA_hackathon branch")
    commit = git("rev-parse", "HEAD")
    manifest = {
        "format": "nasa-runtime-assets-v1",
        "files": included,
        "required_git_files": required,
        "restoration": "Paths are relative to the exact Git checkout; refuse different existing files.",
    }
    metadata = {
        "git_commit": commit,
        "branch": "NASA_hackathon",
        "remote": git("remote", "get-url", "origin"),
        "snapshot_directory": SNAPSHOT,
        "snapshot_id": snapshot["snapshot_id"],
        "snapshot_version": snapshot["version"],
        "vector_directory": VECTORS,
        "vector_metadata": vectors,
        "model_dependencies": [model],
        "environment_variables": [
            "NVIDIA_API_KEY",
            "NASA_SCIENTIFIC_LLM_PROVIDER",
            "NASA_NLI_DIRECTORY",
            "NASA_SNAPSHOT",
            "NASA_VECTOR_DIRECTORY",
            "ANTHROPIC_API_KEY",
        ],
        "expected_capabilities": [
            "lexical retrieval",
            "original records",
            "RDF navigation",
            "structured comparison",
            "local NLI",
            "hybrid retrieval and generation with private provider credentials",
        ],
        "excluded": [
            {"asset": ".env and credentials", "obtain": "Configure privately on the server."},
            {
                "asset": "embedding-cache.sqlite",
                "obtain": "Created automatically; query cache is not an index dependency.",
            },
            {
                "asset": "private provider archives and historical snapshots",
                "obtain": "Not runtime dependencies.",
            },
            {
                "asset": "original sources and auxiliary files already in Git",
                "obtain": "Exact commit; checked in required_git_files.",
            },
        ],
        "scientific_acceptance": "conditional; frozen observed metrics unchanged",
    }
    instructions = f"""# Restore the release

Requires the exact Git commit {commit}, Python 3.12+, uv and Node 22.22.3.
The ZIP contains only runtime files absent from Git. Never rebuild ingestion.

```bash
git clone --branch NASA_hackathon https://github.com/LiamSalazar/NASA.git NASA_FIRE_AI
cd NASA_FIRE_AI
git checkout {commit}
uv sync --frozen
# Use the SHA-256 delivered separately with this ZIP.
uv run python scripts/runtime_assets.py restore --archive /path/NASA_FIRE_AI_RUNTIME_ASSETS.zip --sha256 ZIP_SHA256
uv run python scripts/serve_scientific_console.py --offline
# Second terminal, from this checkout:
cd apps/scientific-console
npm ci
npm run dev
```

Open http://127.0.0.1:5173. For full generation, stop the offline server,
configure NVIDIA_API_KEY privately in the backend .env (never VITE variables),
then run `uv run python scripts/serve_scientific_console.py`.
The bundled pinned NLI weights load automatically. Provider availability is not
verified by restoration. No API key is needed for source consultation.

The restore command checks the Git commit, every archive member, required Git
inputs, RC14 checksums, original paths, SQLite, vector/corpus compatibility and
NLI weights. It refuses path escapes and conflicting files. It never overwrites
raw inputs. Model MIT declaration and notices are in docs/model_licenses in Git.
If weights need provisioning independently, use:
`uv run python scripts/provision_semantic_verifier.py --output data/index/models/nasa-nli`.
See docs/SCIENTIFIC_CONSOLE_HANDOFF.md for endpoints, cancellation and limitations.
"""
    generated = {
        "RUNTIME_ASSET_MANIFEST.json": json.dumps(manifest, indent=2) + "\n",
        "RELEASE_METADATA.json": json.dumps(metadata, indent=2) + "\n",
        "RESTORE_INSTRUCTIONS.md": instructions,
    }
    sums = [f"{row['sha256']}  {row['path']}" for row in included]
    sums += [
        f"{hashlib.sha256(data.encode()).hexdigest()}  {name}" for name, data in generated.items()
    ]
    generated["SHA256SUMS"] = "\n".join(sums) + "\n"
    with ZipFile(
        output, "x", compression=ZIP_DEFLATED, compresslevel=6, allowZip64=True
    ) as archive:
        for row in included:
            archive.write(ROOT / row["path"], row["path"])
        for name, data in generated.items():
            archive.writestr(name, data)
    verify_archive(output)
    result = {
        "path": str(output),
        "bytes": output.stat().st_size,
        "sha256": digest(output),
        "git_commit": commit,
        "files": len(included),
        "required_git_files": len(required),
    }
    output.with_suffix(output.suffix + ".sha256").write_text(
        result["sha256"] + "  " + output.name + "\n"
    )
    print(json.dumps(result, indent=2))


def verify_archive(archive_path):
    with ZipFile(archive_path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError("Duplicate archive member")
        for name in names:
            path = Path(name)
            if path.is_absolute() or ".." in path.parts or "\\" in name:
                raise ValueError("Unsafe archive member")
        checksums = dict(
            line.split("  ", 1)[::-1] for line in archive.read("SHA256SUMS").decode().splitlines()
        )
        if set(checksums) != set(names) - {"SHA256SUMS"}:
            raise ValueError("Checksum member inventory mismatch")
        for name, expected in checksums.items():
            with archive.open(name) as stream:
                if hashlib.file_digest(stream, "sha256").hexdigest() != expected:
                    raise ValueError("Archive checksum mismatch: " + name)
        manifest = json.loads(archive.read("RUNTIME_ASSET_MANIFEST.json"))
        for row in manifest["files"]:
            info = archive.getinfo(row["path"])
            if info.file_size != row["bytes"] or checksums[row["path"]] != row["sha256"]:
                raise ValueError("Manifest mismatch")
        if set(names) != {row["path"] for row in manifest["files"]} | {
            "SHA256SUMS",
            "RUNTIME_ASSET_MANIFEST.json",
            "RELEASE_METADATA.json",
            "RESTORE_INSTRUCTIONS.md",
        }:
            raise ValueError("Unexpected archive assets")
        return manifest, json.loads(archive.read("RELEASE_METADATA.json"))


def restore(archive_path, expected, destination):
    if digest(archive_path) != expected:
        raise ValueError("ZIP checksum mismatch")
    manifest, metadata = verify_archive(archive_path)
    if git("rev-parse", "HEAD", root=destination) != metadata["git_commit"]:
        raise ValueError("Checkout does not match the release commit")
    for row in manifest["required_git_files"]:
        if details(destination, row["path"]) != row:
            raise ValueError("Required Git input differs: " + row["path"])
    # Preflight all conflicts before creating any assets.
    for row in manifest["files"]:
        target = destination / row["path"]
        if not target.resolve().is_relative_to(destination.resolve()):
            raise ValueError("Escaping restoration path")
        if target.exists() and details(destination, row["path"]) != row:
            raise ValueError("Existing asset differs: " + row["path"])
    with ZipFile(archive_path) as archive:
        for row in manifest["files"]:
            target = destination / row["path"]
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(row["path"]) as source, target.open("xb") as output:
                    shutil.copyfileobj(source, output, 1024 * 1024)
            if details(destination, row["path"]) != row:
                raise ValueError("Restored asset mismatch")
    snapshot, _, _ = validate(destination)
    print(
        json.dumps(
            {
                "restored": True,
                "snapshot_id": snapshot["snapshot_id"],
                "git_commit": metadata["git_commit"],
                "files": len(manifest["files"]),
            }
        )
    )


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("action", choices=["pack", "verify", "restore"])
    parser.add_argument("--archive", type=Path, default=ROOT / "NASA_FIRE_AI_RUNTIME_ASSETS.zip")
    parser.add_argument("--sha256")
    parser.add_argument("--destination", type=Path, default=ROOT)
    args = parser.parse_args()
    if args.action == "pack":
        pack(args.archive.resolve())
    elif args.action == "verify":
        verify_archive(args.archive)
        print(json.dumps({"integrity": "verified", "sha256": digest(args.archive)}))
    elif args.sha256:
        restore(args.archive, args.sha256, args.destination.resolve())
    else:
        parser.error("restore requires --sha256")


if __name__ == "__main__":
    main()
