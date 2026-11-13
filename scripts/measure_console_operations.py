"""Measure offline application orchestration without remote generation or evaluation."""

import argparse
import json
from pathlib import Path
from time import monotonic, sleep

import httpx


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--base", default="http://127.0.0.1:8765/api/v1")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    results = {"mode": "offline orchestration; no scientific acceptance campaign", "routes": []}
    with httpx.Client(base_url=args.base, timeout=120) as client:
        ready = client.get("/readiness").raise_for_status().json()
        if ready["generation"] != "NOT_CONFIGURED":
            raise ValueError("Use an offline server; this probe must not call a provider")
        # Warm the immutable scientific presentation inventory.
        overview = client.get("/research/overview").raise_for_status().json()
        operation = (
            client.post(
                "/chat/operations",
                json={"message": "Saffire-III sample S2 airflow", "max_queries": 1},
            )
            .raise_for_status()
            .json()["operation_id"]
        )
        path = "/chat/operations/" + operation
        deadline = monotonic() + 120
        while monotonic() < deadline:
            state = client.get(path).raise_for_status().json()
            if state["status"] == "running":
                break
            sleep(0.05)
        try:
            records = (
                client.get("/records", params={"investigation": "psi-100"})
                .raise_for_status()
                .json()["items"]
            )
            evidence = records[0]["evidence"][0]["evidence_id"]
            checks = [
                ("catalog", "GET", "/catalog", None, None),
                (
                    "material_filter",
                    "GET",
                    "/research/investigations",
                    {"material": overview["facets"]["hasMaterial"][0]["id"]},
                    None,
                ),
                ("records", "GET", "/records", {"investigation": "psi-100"}, None),
                ("evidence", "GET", "/evidence/" + evidence, None, None),
                ("identifier", "GET", "/resolve", {"query": "PSI-100"}, None),
                ("graph", "GET", "/research/entities/psi-107/neighbors", None, None),
                (
                    "comparison",
                    "POST",
                    "/comparisons",
                    None,
                    {"subjects": [r["id"] for r in records[:2]], "dimensions": []},
                ),
            ]
            for name, method, endpoint, params, body in checks:
                began = monotonic()
                response = client.request(method, endpoint, params=params, json=body)
                response.raise_for_status()
                results["routes"].append(
                    {
                        "name": name,
                        "seconds": monotonic() - began,
                        "http_status": response.status_code,
                        "chat_status": client.get(path).json()["status"],
                    }
                )
            queued = (
                client.post("/chat/operations", json={"message": "Saffire-III source records"})
                .raise_for_status()
                .json()
            )
            queued_path = "/chat/operations/" + queued["operation_id"]
            began = monotonic()
            canceled = client.post(queued_path + "/cancel").raise_for_status().json()
            results["queued_cancellation"] = {
                "seconds": monotonic() - began,
                "status": canceled["status"],
            }
        finally:
            began = monotonic()
            initial = client.post(path + "/cancel").raise_for_status().json()
            deadline = monotonic() + 180
            while monotonic() < deadline:
                state = client.get(path).raise_for_status().json()
                if state["status"] in {"completed", "canceled", "failed"}:
                    break
                sleep(0.1)
            results["active_cancellation"] = {
                "initial_status": initial["status"],
                "final_status": state["status"],
                "release_seconds": monotonic() - began,
                "queue_seconds": state["queue_seconds"],
                "execution_seconds": state["execution_seconds"],
            }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
