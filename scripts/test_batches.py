"""Run disjoint pytest batches with bounded, task-owned temporary storage."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New receipt directory")
    parser.add_argument("--temp-root", type=Path, default=Path("/dev/shm"))
    parser.add_argument("--batch-size", type=int, default=18)
    args = parser.parse_args()
    if not 1 <= args.batch_size <= 50:
        parser.error("batch-size must be in 1..50")
    args.output.mkdir(parents=True, exist_ok=False)
    files = sorted(str(p.relative_to(ROOT)) for p in (ROOT / "tests").glob("test_*.py"))
    receipt = {"files": files, "batches": [], "complete": False, "credentials_disabled": True}

    def implementation():
        paths = sorted((ROOT / "src/nasa_fire_ai").rglob("*.py"))
        paths += sorted((ROOT / "tests").glob("*.py"))
        paths += sorted((ROOT / "domain").rglob("*.yaml"))
        paths += sorted((ROOT / "ontology").rglob("*.ttl"))
        return {
            str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in paths
        }

    receipt["implementation_sha256_before"] = implementation()
    historical = ROOT / "artifacts/phase3c_real_context_evidence_v1.sqlite"

    def checksum():
        if historical.is_file():
            with historical.open("rb") as stream:
                return hashlib.file_digest(stream, "sha256").hexdigest()
        return None

    receipt["historical_sha256_before"] = checksum()
    env = {**os.environ, "NVIDIA_API_KEY": "", "ANTHROPIC_API_KEY": "", "OPENAI_API_KEY": ""}
    try:
        for start in range(0, len(files), args.batch_size):
            if shutil.disk_usage(args.temp_root).free < 2_000_000_000:
                receipt["stopped_reason"] = "Less than 2 GB free; no user files removed"
                break
            began = perf_counter()
            batch_files = files[start : start + args.batch_size]
            with tempfile.TemporaryDirectory(prefix="nasa-tests-", dir=args.temp_root) as scratch:
                command = [
                    "uv",
                    "run",
                    "pytest",
                    "-q",
                    *batch_files,
                    "--basetemp=" + scratch + "/pytest",
                    "--tb=short",
                    "--disable-warnings",
                ]
                log = args.output / f"batch-{start // args.batch_size}.txt"
                with log.open("w") as stream:
                    result = subprocess.run(
                        command,
                        cwd=ROOT,
                        env=env,
                        stdout=stream,
                        stderr=subprocess.STDOUT,
                        check=False,
                    )
                receipt["batches"].append(
                    {
                        "files": batch_files,
                        "returncode": result.returncode,
                        "seconds": perf_counter() - began,
                        "log": log.name,
                        "summary": log.read_text().splitlines()[-1:],
                    }
                )
                print(json.dumps(receipt["batches"][-1]), flush=True)
            (args.output / "results.json").write_text(json.dumps(receipt, indent=2))
        else:
            receipt["complete"] = True
    finally:
        receipt["historical_sha256_after"] = checksum()
        receipt["implementation_sha256_after"] = implementation()
        receipt["implementation_unchanged"] = (
            receipt["implementation_sha256_before"] == receipt["implementation_sha256_after"]
        )
        (args.output / "results.json").write_text(json.dumps(receipt, indent=2))
    if (
        not receipt["complete"]
        or not receipt["implementation_unchanged"]
        or any(b["returncode"] for b in receipt["batches"])
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
