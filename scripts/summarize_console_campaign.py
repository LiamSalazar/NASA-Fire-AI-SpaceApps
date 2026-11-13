"""Summarize observed HTTP cost/timing; never infer scientific answer quality."""

import argparse
import hashlib
import json
import statistics
from pathlib import Path


def summarize(directory):
    rows = []
    for path in sorted(directory.glob("*.json")):
        if path.name.endswith((".trace.json", ".ledger.json")):
            continue
        record = json.loads(path.read_text())
        if "elapsed_seconds" not in record:
            continue
        trace_path = directory / (record["id"] + ".trace.json")
        trace = json.loads(trace_path.read_text()) if trace_path.exists() else {}
        calls = trace.get("provider_calls", [])
        telemetry_complete = bool(calls)
        provider_seconds = sum(c.get("latency_ms", 0) for c in calls) / 1000 if calls else None
        timing = record.get("timings", {})
        rows.append(
            {
                "id": record["id"],
                "http_status": record.get("status"),
                "total_seconds": record["elapsed_seconds"],
                "provider_seconds": provider_seconds,
                **timing,
                "provider_telemetry_complete": telemetry_complete,
                "other_backend_and_transport_seconds": record["elapsed_seconds"]
                - provider_seconds
                - sum(timing.values())
                if telemetry_complete
                else None,
                "provider_calls": len(calls),
                "repair_rounds": len(trace.get("repairs", [])),
                "input_tokens": sum(c.get("usage", {}).get("prompt_tokens", 0) for c in calls),
                "output_tokens": sum(c.get("usage", {}).get("completion_tokens", 0) for c in calls),
                "provider_failures": trace.get("provider_failures", []),
                "response_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    return {
        "cases": rows,
        "completed": len(rows),
        "mean_seconds": {
            key: statistics.mean(row[key] for row in rows if row.get(key) is not None)
            if any(row.get(key) is not None for row in rows)
            else None
            for key in (
                "total_seconds",
                "provider_seconds",
                "retrieval_seconds",
                "nli_seconds",
                "other_backend_and_transport_seconds",
            )
        },
        "recorded_totals": {
            key: sum(row[key] for row in rows)
            for key in ("provider_calls", "repair_rounds", "input_tokens", "output_tokens")
        },
        "complete_provider_telemetry_cases": sum(
            row["provider_telemetry_complete"] for row in rows
        ),
        "provider_telemetry_boundary": "Original fresh campaign loses per-call receipts after its first turn because planning resets the receipt list. Recorded totals are a lower bound, not complete call/token totals. Final runtime fixes receipt lineage; do not regenerate the campaign to fill missing telemetry.",
        "actual_api_cost_usd": None,
        "cost_boundary": "NVIDIA configured free-tier service; no billing receipt is available. Do not infer dollar cost from token counts. No new Sonnet calls.",
        "timing_boundary": "Wall-clock HTTP plus measured search.search and local entailment.check calls. Other backend/transport includes source assembly, alignment, composition and cold initialization; it is not all NLI. No artificial retries.",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Do not overwrite a receipt")
    args.output.write_text(json.dumps(summarize(args.directory), indent=2) + "\n")
