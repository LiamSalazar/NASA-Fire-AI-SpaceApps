"""Application-owned checkpointed maintenance; scheduling is external to queries."""

import json
import sqlite3
import subprocess
import time
import uuid
from datetime import UTC, datetime

import httpx

from nasa_fire_ai.ingestion.autonomous import (
    KnowledgeMaintenance,
    official_download,
    registry_checks,
)
from nasa_fire_ai.ingestion.scientific_proposals import extract_source


def run_cycle(
    root,
    registry,
    semantic_registry,
    settings,
    *,
    query="microgravity combustion",
    identifiers=(),
    dry_run=True,
    offline=False,
    model_enabled=False,
    max_sources=2,
    max_model_calls=1,
    retries=1,
    timeout_seconds=120,
    adapter=None,
):
    if (
        not 1 <= max_sources <= 8
        or not 0 <= retries <= 2
        or not 0 < timeout_seconds <= 600
        or not 0 <= max_model_calls <= 8
    ):
        raise ValueError("Maintenance budget outside bounded limits")
    started = time.monotonic()
    pipeline = KnowledgeMaintenance(root, registry, adapter)
    receipt = {
        "job_id": uuid.uuid4().hex,
        "started_at": datetime.now(UTC).isoformat(),
        "mode": "DRY_RUN" if dry_run else "CONTROLLED",
        "items": [],
        "failures": [],
        "discovery": [],
        "model_enabled": model_enabled,
        "max_model_calls": max_model_calls,
        "model_calls_consumed": 0,
        "scheduler_installed": False,
    }
    if not dry_run:
        registry.db.execute(
            "CREATE TABLE IF NOT EXISTS autonomous_jobs(job_id TEXT PRIMARY KEY, started REAL, status TEXT, receipt_json TEXT)"
        )
        registry.db.commit()
        # SQLite serializes lease acquisition, including across scheduler processes.
        registry.db.execute("BEGIN IMMEDIATE")
        registry.db.execute(
            "UPDATE autonomous_jobs SET status='EXPIRED' WHERE status='RUNNING' AND started < ?",
            (time.time() - 900,),
        )
        if registry.db.execute("SELECT 1 FROM autonomous_jobs WHERE status='RUNNING'").fetchone():
            registry.db.rollback()
            return {**receipt, "status": "BUSY"}
        registry.db.execute(
            "INSERT INTO autonomous_jobs VALUES (?,?,?,?)",
            (receipt["job_id"], time.time(), "RUNNING", "{}"),
        )
        registry.db.commit()
    try:
        selected = list(dict.fromkeys(str(i) for i in identifiers))
        if not selected and not offline:
            try:
                discovered = pipeline.discover(query, semantic_registry)
                receipt["discovery"] = [
                    {k: row[k] for k in ("nasa_id", "title", "status")} for row in discovered
                ]
                for row in discovered:
                    try:
                        official_download(row["metadata"])
                        selected.append(row["nasa_id"])
                    except ValueError:
                        continue
            except (httpx.HTTPError, ValueError, RuntimeError, OSError, sqlite3.Error) as error:
                receipt["failures"].append(
                    {"step": "discovery", "error_type": type(error).__name__}
                )
        if offline and not selected:
            selected = [
                r[0]
                for r in registry.db.execute(
                    "SELECT DISTINCT nasa_id FROM sources WHERE source_id LIKE 'ntrs-%@%' AND status NOT IN ('SUPERSEDED_DOCUMENT','ROLLED_BACK_DOCUMENT')"
                )
            ]
        for identifier in selected[:max_sources]:
            if time.monotonic() - started >= timeout_seconds:
                receipt["failures"].append(
                    {"step": "budget", "reason": "Wall-clock budget exhausted before next source"}
                )
                break
            item = {"nasa_id": identifier, "attempts": 0}
            if offline:
                source = registry.db.execute(
                    "SELECT source_id FROM sources WHERE nasa_id=? AND status NOT IN ('SUPERSEDED_DOCUMENT','ROLLED_BACK_DOCUMENT') ORDER BY (source_id LIKE '%@%') DESC,retrieved_at DESC LIMIT 1",
                    (identifier,),
                ).fetchone()
                item["acquisition"] = {
                    "status": "LOCAL_VERSION" if source else "MISSING_LOCAL_VERSION",
                    "source_id": source[0] if source else None,
                    "downloaded": False,
                }
            else:
                for attempt in range(retries + 1):
                    item["attempts"] = attempt + 1
                    try:
                        result = pipeline.update(identifier, dry_run=dry_run)
                        item["acquisition"] = result
                        if result["status"] != "QUARANTINED":
                            break
                    except (
                        httpx.HTTPError,
                        ValueError,
                        RuntimeError,
                        OSError,
                        sqlite3.Error,
                    ) as error:
                        item["acquisition"] = {
                            "status": "QUARANTINED",
                            "error_type": type(error).__name__,
                        }
                    if attempt < retries:
                        time.sleep(min(2**attempt, 4))
            result = item["acquisition"]
            source_id = result.get("source_id") or (result.get("previous_version") or {}).get(
                "source_id"
            )
            if source_id and not dry_run:
                try:
                    item["extraction"] = extract_source(
                        source_id,
                        registry,
                        semantic_registry,
                        settings,
                        model_enabled=model_enabled
                        and receipt["model_calls_consumed"] < max_model_calls,
                    )
                    receipt["model_calls_consumed"] += item["extraction"].get("new_model_calls", 0)
                except (ValueError, RuntimeError, OSError, sqlite3.Error) as error:
                    item["extraction"] = {
                        "status": "QUARANTINED_EXTRACTION",
                        "error_type": type(error).__name__,
                    }
                    receipt["failures"].append(
                        {
                            "step": "extraction",
                            "nasa_id": identifier,
                            "error_type": type(error).__name__,
                        }
                    )
            if result["status"] in {"QUARANTINED", "MISSING_LOCAL_VERSION"}:
                receipt["failures"].append(
                    {"step": "source", "nasa_id": identifier, "reason": result["status"]}
                )
            receipt["items"].append(item)
        receipt["registry_checks"] = registry_checks(registry)
        valid = all(v in (0, [], "ok") for v in receipt["registry_checks"].values())
        receipt["status"] = "COMPLETE" if valid and not receipt["failures"] else "PARTIAL"
        regression_file = root / "tests/test_autonomous_maintenance.py"
        if not dry_run and regression_file.exists():
            command = ["uv", "run", "pytest", "-q", "tests/test_autonomous_maintenance.py"]
            try:
                checks = subprocess.run(
                    command, cwd=root, capture_output=True, text=True, timeout=30, check=False
                )
                receipt["regression_checks"] = {
                    "command": command,
                    "exit_code": checks.returncode,
                    "output": checks.stdout + checks.stderr,
                }
                if checks.returncode:
                    receipt["status"] = "PARTIAL"
                    receipt["failures"].append(
                        {"step": "regression", "reason": "Relevant engineering tests failed"}
                    )
            except subprocess.TimeoutExpired:
                receipt["status"] = "PARTIAL"
                receipt["failures"].append({"step": "regression", "reason": "Regression timeout"})
        else:
            receipt["regression_checks"] = {
                "execution": "NOT_EXECUTED",
                "reason": "Dry-run or development regression files absent",
            }
        receipt["scientific_precision"] = "NOT_MEASURABLE"
        receipt["canonical_scientific_changes"] = 0
        receipt["regression_boundary"] = (
            "Per-cycle SQLite/reference/FTS invariants and autonomous-maintenance tests when installed; full scientific review remains separately executable"
        )
    except (httpx.HTTPError, ValueError, RuntimeError, OSError, sqlite3.Error) as error:
        receipt["status"] = "FAILED"
        receipt["failures"].append({"step": "cycle", "error_type": type(error).__name__})
    finally:
        receipt["latency_ms"] = (time.monotonic() - started) * 1000
        if not dry_run:
            registry.db.execute(
                "UPDATE autonomous_jobs SET status=?,receipt_json=? WHERE job_id=?",
                (receipt.get("status", "FAILED"), json.dumps(receipt), receipt["job_id"]),
            )
            registry.db.commit()
    return receipt
