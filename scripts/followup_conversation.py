"""One predeclared Nemotron follow-up with the prior actual turn as history."""

import json
from pathlib import Path

from nasa_fire_ai.api import default_service
from nasa_fire_ai.services.conversation import ChatRequest, HistoryMessage

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / "artifacts/scientific_engine_stabilization_v1"


def main():
    case = json.loads((DIRECTORY / "followup_question.json").read_text())
    prior = json.loads((DIRECTORY / "nvidia-droplet_method.json").read_text())
    output = DIRECTORY / "nvidia-droplet_source_followup.json"
    if output.exists():
        raise SystemExit("Follow-up receipt exists; reuse the saved result")
    previous_case = prior["case"]
    service = default_service()
    try:
        response = service.chat(
            ChatRequest(
                message=case["question"],
                history=[
                    HistoryMessage(role="user", content=previous_case["question"]),
                    HistoryMessage(role="assistant", content=prior["response"]["answer"]),
                ],
                max_output_tokens=2500,
            )
        )
        output.write_text(
            json.dumps(
                {
                    "case": case,
                    "response": response.model_dump(mode="json"),
                    "trace": service.traces[response.trace_id],
                },
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )
        print(
            json.dumps(
                {
                    "response_mode": response.provider_status.get("response_mode"),
                    "output": str(output.relative_to(ROOT)),
                }
            )
        )
    finally:
        service.search.close()


if __name__ == "__main__":
    main()
