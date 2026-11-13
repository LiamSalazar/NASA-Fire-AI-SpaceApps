"""One fresh, frozen HTTP campaign with private timing receipts and no retries."""

import argparse
import json
import threading
import time
from pathlib import Path

import httpx
import uvicorn

from nasa_fire_ai.api import create_app, default_service


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--wait-for-cached", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    if args.wait_for_cached:
        deadline = time.monotonic() + 1800
        while len(list(args.wait_for_cached.glob("free-*.trace.json"))) < 6:
            if time.monotonic() > deadline:
                raise RuntimeError("Cached campaign incomplete; no second NLI worker started")
            time.sleep(5)
        time.sleep(5)
    active = []
    timings = {}

    def factory():
        svc = default_service()
        if not svc.provider or not svc.entailment:
            raise RuntimeError("Fresh evaluation requires generation and independent verifier")
        active.append(svc)
        for owner, method, label in [
            (svc.search, "search", "retrieval_seconds"),
            (svc.entailment, "check", "nli_seconds"),
        ]:
            original = getattr(owner, method)

            def measured(*a, _original=original, _label=label, **kw):
                started = time.monotonic()
                try:
                    return _original(*a, **kw)
                finally:
                    timings[_label] = timings.get(_label, 0) + time.monotonic() - started

            setattr(owner, method, measured)
        return svc

    server = uvicorn.Server(
        uvicorn.Config(create_app(factory), host="127.0.0.1", port=8768, log_level="warning")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.1)
    if not server.started:
        raise RuntimeError("HTTP server did not start")
    campaign = json.loads(args.questions.read_text())
    conversations = {}
    try:
        with httpx.Client(base_url="http://127.0.0.1:8768", timeout=900) as client:
            for case in campaign["cases"]:
                timings.clear()
                request = {
                    "message": case["question"],
                    "max_queries": 2,
                    "evidence_limit": 12,
                    "max_output_tokens": 2400,
                }
                if case.get("followup_of"):
                    request["conversation_id"] = conversations[case["followup_of"]]
                start = time.monotonic()
                try:
                    response = client.post("/api/v1/chat", json=request)
                    body = response.json()
                    record = {
                        "id": case["id"],
                        "request": request,
                        "status": response.status_code,
                        "body": body,
                        "elapsed_seconds": time.monotonic() - start,
                        "timings": dict(timings),
                    }
                    if response.status_code == 200:
                        conversations[case["id"]] = body["conversation_id"]
                        trace = active[-1].traces[body["trace_id"]]
                        (args.output / (case["id"] + ".trace.json")).write_text(
                            json.dumps(trace, indent=2, default=str)
                        )
                        ledger = Path("data/index/claim_ledger") / (body["trace_id"] + ".json")
                        if ledger.exists():
                            (args.output / (case["id"] + ".ledger.json")).write_bytes(
                                ledger.read_bytes()
                            )
                except (httpx.HTTPError, KeyError) as error:
                    record = {
                        "id": case["id"],
                        "request": request,
                        "error_type": type(error).__name__,
                        "elapsed_seconds": time.monotonic() - start,
                    }
                (args.output / (case["id"] + ".json")).write_text(
                    json.dumps(record, indent=2, default=str)
                )
                print(
                    case["id"],
                    record.get("status", record.get("error_type")),
                    round(record["elapsed_seconds"], 1),
                    flush=True,
                )
    finally:
        server.should_exit = True
        thread.join(timeout=30)


if __name__ == "__main__":
    main()
