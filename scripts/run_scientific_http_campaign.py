"""Execute frozen scientific questions against an actual HTTP application."""

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from time import monotonic

import httpx


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    parser.add_argument(
        "--resume-from", type=Path, help="Reuse completed HTTP responses; never regenerate them"
    )
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    campaign = json.loads(args.questions.read_text())
    receipt = {
        "question_file_sha256": hashlib.sha256(args.questions.read_bytes()).hexdigest(),
        "kind": "FRESH_HTTP_GENERATION",
        "provider": "configured production default",
        "max_queries": 2,
        "evidence_limit": 12,
        "max_output_tokens": 2400,
        "implementation_sha256": {
            str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(Path("src/nasa_fire_ai").rglob("*.py"))
        },
        "cases": campaign["cases"],
    }
    (args.output / "campaign.json").write_text(json.dumps(receipt, indent=2) + "\n")
    conversations = {}
    with httpx.Client(timeout=900) as client:
        for case in campaign["cases"]:
            if args.resume_from and (args.resume_from / (case["id"] + ".json")).exists():
                original = args.resume_from / (case["id"] + ".json")
                saved = json.loads(original.read_text())
                if saved.get("status") == 200:
                    saved["execution_kind"] = "REUSED_ORIGINAL_HTTP_RESPONSE"
                    saved["original_response_sha256"] = hashlib.sha256(
                        original.read_bytes()
                    ).hexdigest()
                    saved["original_response_path"] = str(original)
                    (args.output / (case["id"] + ".json")).write_text(
                        json.dumps(saved, indent=2) + "\n"
                    )
                    conversations[case["id"]] = saved["body"]["conversation_id"]
                    continue
            request = {
                "message": case["question"],
                "max_queries": 2,
                "evidence_limit": 12,
                "max_output_tokens": 2400,
            }
            if case.get("followup_of"):
                request["conversation_id"] = conversations[case["followup_of"]]
            started = monotonic()
            try:
                response = client.post(args.url + "/api/v1/chat", json=request)
            except httpx.HTTPError as error:
                (args.output / (case["id"] + ".json")).write_text(
                    json.dumps(
                        {
                            "id": case["id"],
                            "request": request,
                            "error_type": type(error).__name__,
                            "elapsed_seconds": monotonic() - started,
                        },
                        indent=2,
                    )
                    + "\n"
                )
                raise
            result = {
                "id": case["id"],
                "request": request,
                "status": response.status_code,
                "body": response.json(),
                "elapsed_seconds": monotonic() - started,
            }
            (args.output / (case["id"] + ".json")).write_text(json.dumps(result, indent=2) + "\n")
            # Preserve the backend's actual claim decisions with the public
            # scientific receipt, independently of ignored local runtime files.
            trace_id = result["body"].get("trace_id")
            ledger = Path("data/index/claim_ledger") / (str(trace_id) + ".json")
            if trace_id and ledger.is_file():
                shutil.copy2(ledger, args.output / (case["id"] + ".ledger.json"))
            print(case["id"], response.status_code, round(result["elapsed_seconds"], 1), flush=True)
            if response.status_code != 200:
                raise RuntimeError("HTTP campaign failed")
            conversations[case["id"]] = result["body"]["conversation_id"]


if __name__ == "__main__":
    main()
