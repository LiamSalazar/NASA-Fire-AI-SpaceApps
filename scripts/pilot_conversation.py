"""Run one frozen paired-pilot turn and retain its complete backend trace."""

import argparse
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUESTIONS = ROOT / "artifacts/scientific_engine_stabilization_v1/pilot_questions.json"


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("provider", choices=["nvidia", "anthropic"])
    parser.add_argument("case_id")
    parser.add_argument("--attempt", type=int, default=1)
    args = parser.parse_args()
    questions = json.loads(QUESTIONS.read_text())["questions"]
    case = next((row for row in questions if row["id"] == args.case_id), None)
    if case is None:
        parser.error("unknown frozen case")
    suffix = f"-attempt-{args.attempt}" if args.attempt > 1 else ""
    output = (
        ROOT
        / "artifacts/scientific_engine_stabilization_v1"
        / f"{args.provider}-{args.case_id}{suffix}.json"
    )
    if output.exists():
        parser.error("saved result exists; reuse it instead of spending on a repeated call")
    os.environ["NASA_SCIENTIFIC_LLM_PROVIDER"] = args.provider
    os.environ["NASA_NLI_DIRECTORY"] = str(ROOT / "data/index/models/nasa-nli")
    if args.provider == "anthropic":
        os.environ["NASA_SONNET_EVAL_ENABLED"] = "1"
    from nasa_fire_ai.api import default_service
    from nasa_fire_ai.services.conversation import ChatRequest

    service = default_service()
    try:
        response = service.chat(ChatRequest(message=case["question"], max_output_tokens=2500))
        trace = service.traces[response.trace_id]
        output.write_text(
            json.dumps(
                {"case": case, "response": response.model_dump(mode="json"), "trace": trace},
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )
        print(
            json.dumps(
                {
                    "case": case["id"],
                    "provider": args.provider,
                    "response_mode": response.provider_status.get("response_mode"),
                    "calls": len(trace.get("provider_calls", [])),
                    "output": str(output.relative_to(ROOT)),
                }
            )
        )
    finally:
        service.search.close()


if __name__ == "__main__":
    main()
