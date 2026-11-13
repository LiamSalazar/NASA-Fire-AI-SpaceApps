"""Runnable controlled maintenance; no scheduler is installed by this command."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.autonomous import KnowledgeMaintenance, registry_checks
from nasa_fire_ai.ingestion.semantic import load_semantic_registry


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument(
        "mode",
        choices=[
            "discover",
            "dry-run",
            "controlled-update",
            "review-pending",
            "validation-only",
            "cycle",
            "rollback",
        ],
    )
    parser.add_argument(
        "--execute", action="store_true", help="Execute a controlled cycle; otherwise dry-run"
    )
    parser.add_argument(
        "--offline", action="store_true", help="Reuse registered local source versions"
    )
    parser.add_argument("--max-sources", type=int, default=2)
    parser.add_argument("--max-model-calls", type=int, default=1)
    parser.add_argument("--retries", type=int, default=1)
    parser.add_argument("--timeout-seconds", type=float, default=120)
    parser.add_argument(
        "--extract",
        action="store_true",
        help="Bounded scientific proposal extraction; no automatic scientific approval",
    )
    parser.add_argument("--query", default="microgravity combustion")
    parser.add_argument("--nasa-id")
    parser.add_argument("--source-id")
    parser.add_argument(
        "--interpret",
        action="store_true",
        help="One bounded Nemotron context proposal call; interpretations stay staged",
    )
    parser.add_argument("--registry", type=Path, default=Settings().registry_path)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    # Registry must already exist for non-mutating modes: do not initialize one
    # inadvertently when a path is misspelled.
    if not args.registry.exists() and args.mode != "controlled-update":
        parser.error("Existing registry required for read-only modes")
    evidence = EvidenceRegistry(
        args.registry,
        read_only=not (
            args.mode in {"controlled-update", "rollback"}
            or (args.mode == "cycle" and args.execute)
        ),
    )
    pipeline = KnowledgeMaintenance(ROOT, evidence)
    if args.mode == "cycle":
        from nasa_fire_ai.services.maintenance import run_cycle

        result = run_cycle(
            ROOT,
            evidence,
            load_semantic_registry(ROOT / "domain/semantic_registry.yaml"),
            Settings(),
            query=args.query,
            identifiers=[args.nasa_id] if args.nasa_id else [],
            dry_run=not args.execute,
            offline=args.offline,
            model_enabled=args.extract,
            max_sources=args.max_sources,
            max_model_calls=args.max_model_calls,
            retries=args.retries,
            timeout_seconds=args.timeout_seconds,
        )
    elif args.mode == "rollback":
        if not args.source_id:
            parser.error("--source-id required")
        result = pipeline.rollback_document(args.source_id)
    elif args.mode == "discover":
        result = pipeline.discover(
            args.query, load_semantic_registry(ROOT / "domain/semantic_registry.yaml")
        )
    elif args.mode in {"dry-run", "controlled-update"}:
        if not args.nasa_id:
            parser.error("--nasa-id is required")
        result = pipeline.update(args.nasa_id, dry_run=args.mode == "dry-run")
        if (
            args.interpret
            and args.mode == "controlled-update"
            and result["status"] in {"PUBLISHED", "UNCHANGED", "UNCHANGED_CONTENT"}
        ):
            source_id = result.get("source_id") or (result.get("previous_version") or {}).get(
                "source_id"
            )
            result["context_interpretation"] = pipeline.interpret_source(
                source_id,
                Settings(),
                load_semantic_registry(ROOT / "domain/semantic_registry.yaml"),
            )
    elif args.mode == "review-pending":
        result = evidence.staged_semantic_candidates()
    else:
        result = registry_checks(evidence)
    output = json.dumps(result, indent=2, ensure_ascii=False)
    if args.receipt:
        with args.receipt.open("x") as stream:
            stream.write(output + "\n")
    print(output)


if __name__ == "__main__":
    main()
