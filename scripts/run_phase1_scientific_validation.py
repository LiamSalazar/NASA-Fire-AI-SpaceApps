"""Execute ordinary submission/preparation services in a new isolated workspace.

No extraction, JSON correction, scientific mappings or approval live in this driver.
The optional final investigation requires a prospectively frozen v3 contract.
"""

import argparse
import hashlib
import json
import os
import shutil
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.document_extraction import ExtractionBudget
from nasa_fire_ai.ingestion.extraction_resources import ProviderEnvelope
from nasa_fire_ai.services.curation import CurationService

SOURCES = {
    "luci": ("holdout_first_pass", "20250010653"),
    "bass": ("development_run1", "20150008961"),
    "depress": ("development_run1", "20260003546"),
    "psi": ("development_run1", "PSI-98"),
}


def write(path, value):
    with path.open("x") as f:
        json.dump(value, f, indent=2, ensure_ascii=False)


def inference_configuration(settings):
    """What a frozen run's inference depends on, for the configured provider.

    NVIDIA's dictionary is the one existing freezes record. Anthropic's records its
    own model, fallbacks, effort, endpoint, request limit and max_tokens floor, so
    a change to any of them (an Opus fallback, a higher effort) stops a frozen run,
    and a change to NVIDIA settings alone does not.
    """
    if settings.science_provider == "anthropic":
        from nasa_fire_ai.ingestion.document_extraction import request_context_limit
        from nasa_fire_ai.llm import anthropic_provider

        return {
            "provider": "anthropic",
            "model": settings.scientific_model,
            "fallback_models": list(settings.anthropic_science_fallback_models),
            "vision_model": settings.science_vision_model,
            "effort": settings.anthropic_science_effort,
            "endpoint": os.getenv("ANTHROPIC_BASE_URL") or "https://api.anthropic.com",
            "provider_envelope": asdict(ProviderEnvelope()),
            "request_context_tokens": request_context_limit(settings, ProviderEnvelope()),
            "anthropic_min_max_tokens": anthropic_provider.MIN_MAX_TOKENS,
        }
    return {
        "model": settings.scientific_model,
        "fallback_models": list(settings.nvidia_science_fallback_models),
        "vision_model": settings.nvidia_science_vision_model,
        "endpoint": settings.nvidia_base_url or "https://integrate.api.nvidia.com/v1",
        "provider_envelope": asdict(ProviderEnvelope()),
    }


def commit_source_reference(directory, freeze, package, attempt_count):
    """Fail closed before reserved inference; ordinary ingestion needs no gold."""
    path = directory / "source_reference.json"
    reference = json.loads(path.read_text())
    membership = freeze["evaluation"]
    if (
        reference.get("membership") != membership["membership"]
        or str(reference.get("source_ntrs_id")) != membership["ntrs_id"]
    ):
        raise ValueError("Reference does not match prospective evaluation membership")
    if reference.get("source_sha256") not in {m["sha256"] for m in package["inputs"]}:
        raise ValueError("Reference belongs to a different original source")
    targets = reference["targets"]
    plan = freeze.get("source_review_plan", {})
    if len(targets) < plan.get("minimum_targets", 24) or len({t["id"] for t in targets}) != len(
        targets
    ):
        raise ValueError("Reference denominator is incomplete or duplicates targets")
    evidence = {e["evidence_id"]: e for e in package["evidence"]}
    for target in targets:
        original = evidence[target["evidence_id"]]
        if (
            original["text"][target["start"] : target["end"]] != target["quote"]
            or original["source_id"] != target["source_id"]
        ):
            raise ValueError("Reference is not an exact original source span")
    for kind in ("entities", "quantities", "statements", "relations"):
        if sum(t["kind"] == kind for t in targets) < plan.get("minimum_" + kind, 0):
            raise ValueError("Reference lacks the prospectively required " + kind)
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    commitment = directory / "source_reference_commitment.json"
    if commitment.exists():
        if json.loads(commitment.read_text())["sha256"] != sha:
            raise ValueError("Prospectively committed source reference changed")
    else:
        if attempt_count:
            raise ValueError("Inference began before source reference commitment")
        write(
            commitment,
            {
                "registered_at": datetime.now(UTC).isoformat(),
                "sha256": sha,
                "membership": membership["membership"],
                "source_sha256": reference["source_sha256"],
                "model_attempts": 0,
            },
        )


def default_token_brake(max_total_tokens, settings):
    """The run's token brake: as given, or 500,000 for a billed provider (Anthropic)."""
    if max_total_tokens is None and settings.science_provider == "anthropic":
        return 500000
    return max_total_tokens


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", choices=[*SOURCES, "holdout", "reserved"])
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--timeout-seconds", type=float)
    parser.add_argument("--recover", action="store_true")
    parser.add_argument("--max-model-calls", type=int)
    # The per-run spending brake; a billed provider defaults to 500,000 tokens.
    parser.add_argument("--max-total-tokens", type=int)
    parser.add_argument("--ntrs-id")
    parser.add_argument("--freeze", type=Path)
    parser.add_argument("--acquire-only", action="store_true")
    parser.add_argument("--request-timeout-seconds", type=float)
    args = parser.parse_args()
    out = args.directory.resolve()
    if args.source == "reserved":
        if not args.ntrs_id or not args.freeze:
            parser.error("A reserved investigation requires --ntrs-id and --freeze")
        freeze = json.loads(args.freeze.read_text())
        if freeze["evaluation"]["ntrs_id"] != args.ntrs_id:
            raise ValueError("Reserved investigation differs from prospective membership")
        for name, sha in freeze["files"].items():
            if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != sha:
                raise ValueError("Frozen implementation changed: " + name)
        settings = Settings()
        if inference_configuration(settings) != freeze["configuration"]:
            raise ValueError("Frozen inference configuration changed")
    if args.source == "holdout":
        freeze = json.loads(
            (
                ROOT / "artifacts/phase1_generalizable_ingestion/v3/final_contract_freeze.json"
            ).read_text()
        )
        for name, sha in freeze["files"].items():
            if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != sha:
                raise ValueError("Final contract changed: " + name)
    out.mkdir(parents=True, exist_ok=args.resume)
    invocation = len(list(out.glob("implementation_*.json"))) + 1
    write(
        out / f"implementation_{invocation}.json",
        {
            str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for directory in ("src", "scripts", "ontology", "domain")
            for p in sorted((ROOT / directory).rglob("*"))
            if p.is_file() and "__pycache__" not in p.parts
        },
    )
    with ZipFile(out / f"implementation_{invocation}.zip", "x", ZIP_DEFLATED) as archive:
        for name in json.loads((out / f"implementation_{invocation}.json").read_text()):
            archive.write(ROOT / name, name)
    started = datetime.now(UTC).isoformat()
    workspace = out / "workspace"
    for name in ("domain", "ontology", "data/canonical"):
        if not (workspace / name).exists():
            shutil.copytree(ROOT / name, workspace / name)
    registry = EvidenceRegistry(workspace / "data/index/evidence.sqlite")
    service = CurationService(workspace, registry)
    settings = Settings(root=workspace)
    if args.resume:
        submission = json.loads((out / "submission.json").read_text())
        version = len(list(out.glob("prepared_*.json"))) + 1
    else:
        if args.source in {"holdout", "reserved"}:
            submission = service.submit_ntrs(args.ntrs_id or "20240006315", "phase1-validation")
        else:
            campaign, identifier = SOURCES[args.source]
            historical = ROOT / "artifacts/phase1_generalizable_ingestion/v1" / campaign
            package = json.loads((historical / (identifier + "_baseline.json")).read_text())[
                "package"
            ]
            originals = [
                (item["name"], (historical / "workspace" / item["stored_input"]).read_bytes())
                for item in package["inputs"]
            ]
            submission = service.submit(
                package["title"], package["purpose"], originals, package["creator"]
            )
            # Preserve official acquisition provenance, never a scientific mapping.
            submission["package"]["source_provenance"] = package.get("source_provenance")
            submission = service.save(submission["package"], package["creator"])
        write(out / "submission.json", submission)
        version = 1
    if args.acquire_only:
        print(
            json.dumps(
                {"package_id": submission["package"]["id"], "state": "ACQUIRED_WITHOUT_INFERENCE"}
            )
        )
        registry.db.close()
        return
    earlier_attempts = {
        r[0]
        for r in registry.db.execute(
            "SELECT cache_key FROM phase3_cache WHERE cache_kind='scientific_document_attempt'"
        )
    }
    if args.source == "reserved" and not args.offline:
        commit_source_reference(out, freeze, submission["package"], len(earlier_attempts))
    max_total_tokens = default_token_brake(args.max_total_tokens, settings)
    prepared = service.prepare_scientific(
        submission["package"]["id"],
        settings,
        model_enabled=not args.offline,
        budget=ExtractionBudget(
            max_model_calls=args.max_model_calls,
            max_total_tokens=max_total_tokens,
            timeout_seconds=args.timeout_seconds,
            recovery_only=args.recover,
            call_timeout_seconds=args.request_timeout_seconds,
        ),
    )
    attempts = [
        {"cache_key": r[0], **json.loads(r[1])}
        for r in registry.db.execute(
            "SELECT cache_key,payload_json FROM phase3_cache WHERE cache_kind='scientific_document_attempt'"
        )
        if r[0] not in earlier_attempts
    ]
    write(
        out / f"attempts_{version}.json",
        {
            "started_at": started,
            "completed_at": datetime.now(UTC).isoformat(),
            "attempts": attempts,
        },
    )
    write(out / f"prepared_{version}.json", prepared)
    write(out / f"validation_{version}.json", service.validate(prepared["package"]))
    (out / f"package_{version}.zip").write_bytes(
        service.export_package(submission["package"]["id"])
    )
    write(
        out / f"summary_{version}.json",
        {
            "source": args.source,
            "package_id": submission["package"]["id"],
            "max_total_tokens": max_total_tokens,
            "digest": prepared["digest"],
            "processing": prepared["processing"],
            "scientific_coverage": prepared["package"]["scientific_extraction"][
                "scientific_coverage"
            ],
            "source_integrity_errors": service.validate_originals(prepared["package"]),
            "approvals": registry.db.execute("SELECT count(*) FROM research_approvals").fetchone()[
                0
            ],
            "publications": registry.db.execute("SELECT count(*) FROM research_active").fetchone()[
                0
            ],
            "sqlite_integrity": registry.db.execute("PRAGMA integrity_check").fetchone()[0],
        },
    )
    print(
        json.dumps(
            {
                "source": args.source,
                "directory": str(out),
                "status": prepared["processing"]["status"],
                "new_model_calls": prepared["processing"]["new_model_calls"],
                "scientific_completeness": prepared["processing"]["scientific_completeness"],
            }
        )
    )
    registry.db.close()


if __name__ == "__main__":
    main()
