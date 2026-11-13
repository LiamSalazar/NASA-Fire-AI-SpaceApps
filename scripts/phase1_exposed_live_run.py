"""Run one already-exposed NASA source live through the ordinary curation services.

Development/regression only. The source must already be exposed (its frozen
evaluation is finished), so this run is never an independent evaluation. The
driver performs no extraction, mapping, JSON correction or approval itself: it
submits the verified original with its official acquisition provenance, then
calls CurationService.prepare_scientific with the configured NVIDIA models, and
records the outputs. Receipts are written to a new exclusive directory; the
SQLite workspace and the original PDF copy stay outside the repository.

Example (Linux or Windows):
    uv run python scripts/phase1_exposed_live_run.py \
        --pdf /path/20090043050.pdf \
        --provenance-from artifacts/phase1_generalizable_ingestion/v4/independent_ptfe/submission.json \
        --workspace /tmp/nasa-ptfe-live --directory artifacts/.../ptfe_live_<commit> \
        --timeout-seconds 1800
"""

import argparse
import gzip
import hashlib
import json
import re
import shutil
import subprocess
import sys
from collections import Counter
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.document_extraction import ExtractionBudget, request_context_limit
from nasa_fire_ai.ingestion.extraction_resources import ProviderEnvelope
from nasa_fire_ai.llm import anthropic_provider
from nasa_fire_ai.llm.scientific_provider import redact_provider_text
from nasa_fire_ai.services.curation import CurationService

CREDENTIAL = re.compile(r"(?:nvapi|sk-ant)-[A-Za-z0-9_\-]{8,}")


def load(path):
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


# Public list prices in USD per million tokens (input, output, cache read, cache
# write), for the receipt's cost estimate only; NVIDIA's endpoint is not billed here.
PRICES = {
    "claude-sonnet-5-5": (2.0, 10.0, 0.20, 2.50),
    "claude-opus-5-5": (4.0, 20.0, 0.20, 5.00),
    "claude-fable-5-1": (10.0, 50.0, 0.25, 12.50),
}


def estimated_cost(model, usage):
    price = PRICES.get(model)
    if not price or not usage:
        return 0.0
    plain = usage.get("input_tokens", usage.get("prompt_tokens") or 0)
    if "input_tokens" not in usage:
        plain -= (usage.get("cache_read_input_tokens") or 0) + (
            usage.get("cache_creation_input_tokens") or 0
        )
    return (
        max(0, plain) * price[0]
        + (usage.get("completion_tokens") or 0) * price[1]
        + (usage.get("cache_read_input_tokens") or 0) * price[2]
        + (usage.get("cache_creation_input_tokens") or 0) * price[3]
    ) / 1e6


def timing_summary(attempts, started, completed):
    """Where a run's time went: provider calls, local work between them, failed attempts.

    Provider seconds are the union of call intervals when calls record their start,
    so calls that overlap count once; local seconds are the rest of the wall clock.
    """
    from datetime import datetime

    wall = (datetime.fromisoformat(completed) - datetime.fromisoformat(started)).total_seconds()
    calls, intervals, causes, requests = [], [], Counter(), Counter()
    for attempt in attempts:
        outcome = attempt.get("outcome") or {}
        transport = outcome.get("transport") or {}
        duration = transport.get("duration_seconds") or 0
        first = transport.get("time_to_first_token_seconds")
        usage = outcome.get("usage") or {}
        if outcome.get("error_type"):
            causes[outcome["error_type"]] += 1
        requests[
            hashlib.sha256(
                json.dumps(
                    [attempt.get("requested_model"), attempt.get("request")], sort_keys=True
                ).encode()
            ).hexdigest()
        ] += 1
        calls.append(
            {
                "stage": attempt.get("stage"),
                "model": attempt.get("requested_model"),
                "seconds": round(duration, 1),
                "first_token_seconds": None if first is None else round(first, 1),
                "generation_seconds": None if first is None else round(duration - first, 1),
                "input_tokens": usage.get("prompt_tokens"),
                "output_tokens": usage.get("completion_tokens"),
                "cache_read_input_tokens": usage.get("cache_read_input_tokens"),
                "cache_creation_input_tokens": usage.get("cache_creation_input_tokens"),
                "estimated_cost_usd": round(
                    estimated_cost(attempt.get("requested_model"), usage), 4
                ),
                "error": outcome.get("error_type"),
            }
        )
        if transport.get("started_at"):
            begin = datetime.fromisoformat(transport["started_at"]).timestamp()
            intervals.append((begin, begin + duration))
    busy = 0.0
    if intervals and len(intervals) == len(calls):
        end = None
        for begin, finish in sorted(intervals):
            if end is None or begin > end:
                busy += finish - begin
                end = finish
            elif finish > end:
                busy += finish - end
                end = finish
    else:
        busy = sum(c["seconds"] for c in calls)
    seconds = sorted(c["seconds"] for c in calls)

    def quantile(q):
        return seconds[min(len(seconds) - 1, int(q * len(seconds)))] if seconds else None

    return {
        "wall_seconds": round(wall, 1),
        "provider_seconds": round(busy, 1),
        "provider_call_seconds_total": round(sum(seconds), 1),
        "local_seconds": round(max(0.0, wall - busy), 1),
        "calls": len(calls),
        "failed_attempts": sum(causes.values()),
        "failure_causes": dict(causes),
        "call_seconds_p50": quantile(0.5),
        "call_seconds_p90": quantile(0.9),
        "call_seconds_max": seconds[-1] if seconds else None,
        "calls_over_240_seconds": sum(s > 240 for s in seconds),
        "input_tokens": sum(c["input_tokens"] or 0 for c in calls),
        "output_tokens": sum(c["output_tokens"] or 0 for c in calls),
        "cache_read_input_tokens": sum(c["cache_read_input_tokens"] or 0 for c in calls),
        "cache_creation_input_tokens": sum(c["cache_creation_input_tokens"] or 0 for c in calls),
        "estimated_cost_usd": round(sum(c["estimated_cost_usd"] for c in calls), 4),
        # The same request sent more than once (retries after a failure included).
        "repeated_identical_requests": sum(n - 1 for n in requests.values() if n > 1),
        "per_call": calls,
    }


def write(path, value):
    # Provider messages may name the key owner's account; receipts never keep it.
    text = redact_provider_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True))
    text += "\n"
    if CREDENTIAL.search(text):
        raise RuntimeError("Refusing to write a receipt containing a credential")
    if path.suffix == ".gz":
        with gzip.open(path, "xt", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
    else:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(text)


def git(*args):
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=False
    ).stdout.strip()


def main():
    launched = datetime.now(UTC).isoformat()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--provenance-from", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=float)
    parser.add_argument("--max-model-calls", type=int)
    # A hard ceiling on a run's input plus output tokens: calls that would pass it
    # are not sent and stay recorded as deferred by the budget.
    parser.add_argument("--max-total-tokens", type=int)
    parser.add_argument("--request-timeout-seconds", type=float)
    args = parser.parse_args()

    out = args.directory if args.directory.is_absolute() else ROOT / args.directory
    workspace = args.workspace.resolve()
    if ROOT in [workspace, *workspace.parents]:
        raise ValueError("The workspace must be outside the repository")
    reference = load(args.provenance_from)["package"]
    data = args.pdf.read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    expected = {i["sha256"] for i in reference["inputs"]}
    if sha not in expected:
        raise ValueError("Original PDF does not match the recorded official source hash")
    out.mkdir(parents=True, exist_ok=False)
    for name in ("domain", "ontology", "data/canonical"):
        if not (workspace / name).exists():
            shutil.copytree(ROOT / name, workspace / name)

    settings = Settings(root=workspace)
    if settings.science_provider == "anthropic" and args.max_total_tokens is None:
        # A billed provider never runs without the per-run spending brake.
        args.max_total_tokens = 500000
    if not settings.science_api_key:
        raise RuntimeError(
            ("ANTHROPIC" if settings.science_provider == "anthropic" else "NVIDIA")
            + "_API_KEY is not configured"
        )
    registry = EvidenceRegistry(workspace / "data/index/evidence.sqlite")
    service = CurationService(workspace, registry)
    started = datetime.now(UTC).isoformat()
    try:
        submission = service.submit(
            reference["title"],
            reference["purpose"],
            [(reference["inputs"][0]["name"], data)],
            reference["creator"],
        )
        # Official acquisition provenance only; never a scientific mapping. The
        # citation on file is re-judged by the current eligibility screening and
        # the label recorded at acquisition is kept beside it.
        provenance = dict(reference.get("source_provenance") or {})
        if provenance.get("metadata"):
            from nasa_fire_ai.ingestion.source_eligibility import assess

            assessment = assess(provenance["metadata"])
            provenance["eligibility_recorded_at_acquisition"] = provenance.get("eligibility")
            provenance["eligibility"] = assessment["eligibility"]
            provenance["eligibility_assessment"] = assessment
        submission["package"]["source_provenance"] = provenance
        submission = service.save(submission["package"], reference["creator"])
        package_id = submission["package"]["id"]
        before = {
            r[0]
            for r in registry.db.execute(
                "SELECT cache_key FROM phase3_cache WHERE cache_kind='scientific_document_attempt'"
            )
        }
        prepared = service.prepare_scientific(
            package_id,
            settings,
            model_enabled=True,
            budget=ExtractionBudget(
                max_model_calls=args.max_model_calls,
                max_total_tokens=args.max_total_tokens,
                timeout_seconds=args.timeout_seconds,
                call_timeout_seconds=args.request_timeout_seconds,
            ),
        )
        attempts = [
            {"cache_key": r[0], **json.loads(r[1])}
            for r in registry.db.execute(
                "SELECT cache_key,payload_json FROM phase3_cache "
                "WHERE cache_kind='scientific_document_attempt'"
            )
            if r[0] not in before
        ]
        completed = datetime.now(UTC).isoformat()
        validation = service.validate(prepared["package"])
        summary = {
            "kind": "PHASE1_EXPOSED_SOURCE_LIVE_RUN",
            "membership": "EXPOSED_DEVELOPMENT_REGRESSION_ONLY",
            "git_head": git("rev-parse", "HEAD"),
            "uncommitted_src_changes": bool(git("status", "--porcelain", "--", "src")),
            "started_at": started,
            "completed_at": completed,
            "package_id": package_id,
            "source_sha256": sha,
            "official_url": (reference.get("source_provenance") or {}).get("source_url"),
            "configuration": {
                "model": settings.scientific_model,
                "provider": settings.science_provider,
                "fallback_models": list(settings.science_fallback_models),
                "vision_model": settings.science_vision_model,
                "endpoint": "https://api.anthropic.com"
                if settings.science_provider == "anthropic"
                else settings.nvidia_base_url or "https://integrate.api.nvidia.com/v1",
                "provider_envelope": asdict(ProviderEnvelope()),
                "request_context_tokens": request_context_limit(settings, ProviderEnvelope()),
                **(
                    {"anthropic_min_max_tokens": anthropic_provider.MIN_MAX_TOKENS}
                    if settings.science_provider == "anthropic"
                    else {}
                ),
                "timeout_seconds": args.timeout_seconds,
                "max_model_calls": args.max_model_calls,
                "max_total_tokens": args.max_total_tokens,
            },
            "digest": prepared["digest"],
            "processing": prepared["processing"],
            "attempts": len(attempts),
            "validation_errors": validation.get("errors", []),
            "source_integrity_errors": service.validate_originals(prepared["package"]),
            "approvals": registry.db.execute("SELECT count(*) FROM research_approvals").fetchone()[
                0
            ],
            "publications": registry.db.execute("SELECT count(*) FROM research_active").fetchone()[
                0
            ],
            "sqlite_integrity": registry.db.execute("PRAGMA integrity_check").fetchone()[0],
            "scientific_acceptance": "NOT_ESTABLISHED_BY_RUN",
        }
        summary["timing"] = timing_summary(attempts, started, completed)
        # Workspace setup before the extraction, and validation after it.
        summary["timing"]["setup_seconds"] = round(
            (datetime.fromisoformat(started) - datetime.fromisoformat(launched)).total_seconds(), 1
        )
        summary["timing"]["post_extraction_seconds"] = round(
            (datetime.now(UTC) - datetime.fromisoformat(completed)).total_seconds(), 1
        )
        write(out / "submission.json", submission)
        write(out / "attempts.json.gz", {"attempts": attempts})
        write(out / "prepared.json.gz", prepared)
        write(out / "validation.json.gz", validation)
        write(out / "summary.json", summary)
        print(json.dumps({k: summary[k] for k in ("package_id", "digest", "attempts")}))
        print(json.dumps(summary["processing"], indent=2)[:4000])
    finally:
        registry.db.close()


if __name__ == "__main__":
    main()
