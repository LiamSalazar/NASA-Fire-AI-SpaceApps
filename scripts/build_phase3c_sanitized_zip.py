from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/phase3c_curation_v1_sanitized.zip"
MANIFEST_OUT = ROOT / "artifacts/phase3c_curation_v1_sanitized_manifest.json"


def tracked_or_changed(prefix: str) -> list[Path]:
    result = subprocess.run(
        ["git", "status", "--short", "--", prefix],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    paths = []
    for line in result.stdout.splitlines():
        if len(line) >= 4:
            path = line[3:]
            if " -> " in path:
                path = path.split(" -> ", 1)[1]
            candidate = ROOT / path
            if candidate.is_file():
                paths.append(candidate)
    return paths


def allowed_artifact(path: Path) -> bool:
    rel = path.relative_to(ROOT / "artifacts/phase3c_curation_v1")
    text = rel.as_posix().lower()
    name = path.name.lower()
    if any(
        part.startswith("__pycache__") or part in {".git", ".pytest_cache", ".ruff_cache"}
        for part in rel.parts
    ):
        return False
    if any(token in name for token in (".env", "secret", "private", "api_key", "token")):
        return False
    if path.suffix.lower() in {
        ".sqlite",
        ".db",
        ".pdf",
        ".html",
        ".csv",
        ".tsv",
        ".npy",
        ".npz",
        ".zip",
    }:
        return False
    if "/workspace/data/raw/" in f"/{text}" or "/workspace/data/submissions/" in f"/{text}":
        return False
    if "/workspace/data/index/" in f"/{text}":
        return False
    if "/workspace/data/canonical/" in f"/{text}" and path.suffix.lower() not in {".nt", ".ttl"}:
        return False
    return path.stat().st_size <= 5_000_000


def copy_file(src: Path, stage: Path, arcname: str) -> None:
    dest = stage / arcname
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="phase3c_sanitized_") as tmp:
        stage = Path(tmp)
        selected: dict[str, Path] = {}

        explicit = [
            "AGENTS.md",
            "README.md",
            "pyproject.toml",
            "uv.lock",
            "app/curation_view.py",
            "app/streamlit_app.py",
            "docs/PHASE3C_CURATION_V1.md",
            "docs/PHASE3C_REASONING_CLOSURE_V1.md",
            "domain/incorporation.yaml",
            "domain/semantic_registry.yaml",
            "ontology/incorporation_mappings.ttl",
        ]
        for rel in explicit:
            path = ROOT / rel
            if path.is_file():
                selected[rel] = path
        for path in tracked_or_changed("src/nasa_fire_ai") + tracked_or_changed("tests"):
            selected[path.relative_to(ROOT).as_posix()] = path
        for path in tracked_or_changed("scripts"):
            if "phase3c" in path.name or path.name == "curate_research.py":
                selected[path.relative_to(ROOT).as_posix()] = path
        artifact_root = ROOT / "artifacts/phase3c_curation_v1"
        for path in artifact_root.rglob("*"):
            if path.is_file() and allowed_artifact(path):
                selected[path.relative_to(ROOT).as_posix()] = path

        for arcname, src in sorted(selected.items()):
            copy_file(src, stage, arcname)

        entries = []
        for path in sorted(stage.rglob("*")):
            if not path.is_file():
                continue
            data = path.read_bytes()
            entries.append(
                {
                    "path": path.relative_to(stage).as_posix(),
                    "size": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
            )
        manifest = {
            "package": "NASA FIRE AI Phase 3C sanitized implementation",
            "generated_from": str(ROOT),
            "file_count": len(entries),
            "total_bytes": sum(item["size"] for item in entries),
            "excluded": [
                ".env and credentials",
                "caches and bytecode",
                "private files",
                "large historical/source inputs",
                "SQLite/vector indexes",
                "nested ZIP archives",
            ],
            "files": entries,
        }
        manifest_path = stage / "PACKAGE_MANIFEST.json"
        manifest_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        MANIFEST_OUT.write_bytes(manifest_path.read_bytes())
        OUT.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(
            OUT, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as archive:
            for path in sorted(stage.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(stage).as_posix())
        zip_hash = hashlib.sha256(OUT.read_bytes()).hexdigest()
        (OUT.with_suffix(OUT.suffix + ".sha256")).write_text(
            f"{zip_hash}  {OUT.name}\n", encoding="utf-8"
        )
        print(
            json.dumps(
                {
                    "zip": str(OUT),
                    "manifest": str(MANIFEST_OUT),
                    "files": len(entries),
                    "bytes": manifest["total_bytes"],
                    "zip_sha256": zip_hash,
                }
            )
        )


if __name__ == "__main__":
    main()
