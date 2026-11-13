"""Launch a real credential-free uvicorn socket, exercise chat, and stop it."""

import argparse
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output must be new")
    with socket.socket() as socket_probe:
        socket_probe.bind(("127.0.0.1", 0))
        port = socket_probe.getsockname()[1]
    env = {
        **os.environ,
        "NVIDIA_API_KEY": "",
        "OPENAI_API_KEY": "",
        "ANTHROPIC_API_KEY": "",
        "NASA_NLI_DIRECTORY": "",
    }
    process = subprocess.Popen(
        [
            "uv",
            "run",
            "uvicorn",
            "nasa_fire_ai.api:app",
            "--app-dir",
            "src",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    base = f"http://127.0.0.1:{port}"
    try:
        for _ in range(100):
            try:
                with urllib.request.urlopen(base + "/api/v1/health", timeout=1) as stream:
                    health = json.load(stream)
                break
            except (urllib.error.URLError, TimeoutError):
                time.sleep(0.1)
        else:
            raise RuntimeError("HTTP server did not start")
        request = urllib.request.Request(
            base + "/api/v1/chat",
            data=json.dumps({"message": "PMMA oxygen 22.2 %"}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=30) as stream:
            response = json.load(stream)
        assert response["provider_status"]["status"] == "UNAVAILABLE"
        assert response["provider_status"]["generated_by"] is None
        assert response["evidence_groups"]["direct"]
        from nasa_fire_ai.api import create_app

        (ROOT / "docs/PHASE56_OPENAPI.json").write_text(
            json.dumps(create_app().openapi(), indent=2) + "\n"
        )
        args.output.write_text(
            json.dumps(
                {
                    "transport": "real_tcp_uvicorn",
                    "health": health,
                    "provider_status": response["provider_status"],
                    "snapshot_id": response["snapshot_id"],
                    "counts": {k: len(v) for k, v in response["evidence_groups"].items()},
                    "passed": True,
                },
                indent=2,
            )
            + "\n"
        )
        print("Real HTTP offline chat passed")
    finally:
        process.terminate()
        process.wait(timeout=10)


if __name__ == "__main__":
    main()
