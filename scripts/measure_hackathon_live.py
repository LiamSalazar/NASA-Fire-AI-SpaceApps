"""Small, predetermined live text-only NVIDIA probe; never records credentials."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nasa_fire_ai.config import Settings
from nasa_fire_ai.llm.native_interpreter import NvidiaMinimalInterpreter
from nasa_fire_ai.llm.scientific_selection import NvidiaScientificSelector
from nasa_fire_ai.services.search import ScientificSearchService

CASES = [
    ("reported_measurements", "Saffire I measurements", True),
    ("run_comparison", "Compare Saffire I S1 and S2", True),
    ("partial_gravity_negative", "PMMA in a lunar habitat oxygen 22.2 %", False),
]


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument(
        "--snapshot", type=Path, default=ROOT / "data/snapshots/hackathon-20261105-v9"
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    settings = Settings()
    report = {
        "requested_model": settings.nvidia_phase3_model,
        "status": "NOT_CONFIGURED",
        "cases": [],
    }
    if settings.nvidia_api_key:
        options = (settings.nvidia_api_key, settings.nvidia_base_url, settings.nvidia_phase3_model)
        service = ScientificSearchService(
            args.snapshot,
            ROOT,
            interpreter=NvidiaMinimalInterpreter(*options),
            selector=NvidiaScientificSelector(*options),
        )
        try:
            report.update(status="LIVE_EXECUTED", snapshot_id=service.manifest["snapshot_id"])
            for case_id, question, expected_direct in CASES:
                result = service.search(question, assist=True, limit=4)
                row = result.model_dump(mode="json")
                report["cases"].append(
                    {
                        "case_id": case_id,
                        "expected_direct": expected_direct,
                        "direct_control_passed": bool(result.direct) == expected_direct,
                        "result": row,
                    }
                )
                print(
                    json.dumps(
                        {
                            "case_id": case_id,
                            "provider": result.provider["status"],
                            "total_ms": result.metrics["total_ms"],
                            "claims": len(result.claims),
                        }
                    ),
                    flush=True,
                )
        finally:
            service.close()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
