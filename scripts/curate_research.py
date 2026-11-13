"""Runtime entry point for isolated scientific preparation and authorized test review."""

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.document_extraction import ExtractionBudget
from nasa_fire_ai.services.curation import CurationService, ReviewPolicy


def initialize_workspace(destination):
    destination = Path(destination).resolve()
    if destination == ROOT:
        raise ValueError("Development workspace must be isolated from the repository")
    destination.mkdir(parents=True, exist_ok=True)
    for name in ("domain", "ontology", "data/canonical"):
        target = destination / name
        if not target.exists():
            shutil.copytree(ROOT / name, target)
    return destination


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    commands = parser.add_subparsers(dest="action", required=True)
    commands.add_parser("initialize")
    submit = commands.add_parser("submit")
    submit.add_argument("--title")
    submit.add_argument("--purpose", default="Scientific ingestion draft")
    submit.add_argument("--ntrs-id")
    submit.add_argument("files", nargs="*", type=Path)
    prepare = commands.add_parser("prepare")
    prepare.add_argument("package_id")
    for command in (submit, prepare):
        command.add_argument("--model", action="store_true")
        command.add_argument(
            "--max-model-calls",
            type=int,
            help="Optional session call ceiling; default adapts to source coverage",
        )
        command.add_argument(
            "--max-total-tokens", type=int, help="Optional aggregate usage ceiling"
        )
        command.add_argument(
            "--timeout-seconds", type=float, help="Optional total session deadline"
        )
        command.add_argument(
            "--recover",
            action="store_true",
            help="Reuse validated prior proposals and target outstanding science",
        )
        command.add_argument("--max-output-tokens", type=int)
        command.add_argument("--segment-chars", type=int)
        command.add_argument("--request-timeout-seconds", type=float)
        command.add_argument(
            "--reasoning-tokens",
            type=int,
            help="Optional thinking allocation; 0 disables reasoning",
        )
        command.add_argument("--retries", type=int, default=2)
        command.add_argument("--no-stream", action="store_true")
    status = commands.add_parser("status")
    status.add_argument("package_id")
    args = parser.parse_args()
    workspace = initialize_workspace(args.workspace)
    if args.action == "initialize":
        print(json.dumps({"workspace": str(workspace), "approval": "isolated development only"}))
        return
    registry = EvidenceRegistry(workspace / "data/index/evidence.sqlite")
    service = CurationService(
        workspace, registry, ReviewPolicy(frozenset({"development-scientist"}), True)
    )
    if args.action == "submit":
        if args.ntrs_id:
            result = service.submit_ntrs(args.ntrs_id, "development-scientist")
        else:
            result = service.submit(
                args.title or "",
                args.purpose,
                [(p.name, p.read_bytes()) for p in args.files],
                "development-scientist",
            )
    if args.action in {"submit", "prepare"}:
        package_id = result["package"]["id"] if args.action == "submit" else args.package_id
        result = service.prepare_scientific(
            package_id,
            Settings(root=workspace),
            model_enabled=args.model,
            budget=ExtractionBudget(
                max_model_calls=args.max_model_calls,
                max_total_tokens=args.max_total_tokens,
                timeout_seconds=args.timeout_seconds,
                recovery_only=args.recover,
                max_output_tokens=args.max_output_tokens,
                segment_chars=args.segment_chars,
                call_timeout_seconds=args.request_timeout_seconds,
                retries=args.retries,
                reasoning_tokens=args.reasoning_tokens,
                stream=not args.no_stream,
            ),
        )
    else:
        result = service.validate(service.get(args.package_id)["package"])
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
