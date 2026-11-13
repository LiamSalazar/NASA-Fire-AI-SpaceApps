"""Build, verify, or query the bounded NASA scientific snapshot without an LLM."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nasa_fire_ai.ingestion.hackathon import build_snapshot, verify_snapshot
from nasa_fire_ai.services.search import ScientificSearchService


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("mode", choices=["build", "verify", "ask", "scenario"])
    parser.add_argument("question", nargs="?", default="")
    parser.add_argument(
        "--snapshot", type=Path, default=ROOT / "data/snapshots/hackathon-20261112-scientific-rc14"
    )
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--nemotron", action="store_true")
    parser.add_argument("--research", action="store_true")
    parser.add_argument("--offset", type=int, default=0)
    args = parser.parse_args()
    if args.mode == "build":
        value = build_snapshot(ROOT, args.snapshot)
    elif args.mode == "verify":
        value = verify_snapshot(args.snapshot, ROOT)
    else:
        interpreter = selector = None
        if args.nemotron:
            from nasa_fire_ai.config import Settings
            from nasa_fire_ai.llm.native_interpreter import NvidiaMinimalInterpreter
            from nasa_fire_ai.llm.scientific_selection import NvidiaScientificSelector

            settings = Settings()
            if settings.nvidia_api_key:
                options = (
                    settings.nvidia_api_key,
                    settings.nvidia_base_url,
                    settings.nvidia_phase3_model,
                )
                interpreter = NvidiaMinimalInterpreter(*options)
                selector = NvidiaScientificSelector(*options)
        service = ScientificSearchService(
            args.snapshot, ROOT, interpreter=interpreter, selector=selector
        )
        try:
            if args.mode == "scenario":
                from nasa_fire_ai.query.scenario import ScenarioInput

                scenario = ScenarioInput.model_validate_json(Path(args.question).read_text())
                value = service.analyze_scenario(
                    scenario, assist=args.nemotron, research=args.research, limit=args.limit
                ).model_dump(mode="json")
            else:
                value = service.search(
                    args.question,
                    limit=args.limit,
                    offset=args.offset,
                    assist=args.nemotron,
                    research=args.research,
                ).model_dump(mode="json")
        finally:
            service.close()
    print(json.dumps(value, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
