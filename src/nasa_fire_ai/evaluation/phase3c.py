"""Resumable Phase-3C evidence and metric utilities."""

import hashlib
import json
import math
import os
import statistics
from pathlib import Path


def digest(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def proportion(numerator, denominator):
    if not denominator:
        return {
            "numerator": numerator,
            "denominator": denominator,
            "estimate": None,
            "status": "NOT_APPLICABLE",
        }
    p = numerator / denominator
    z = 1.959963984540054
    center = (p + z * z / (2 * denominator)) / (1 + z * z / denominator)
    half = (
        z
        * math.sqrt(p * (1 - p) / denominator + z * z / (4 * denominator * denominator))
        / (1 + z * z / denominator)
    )
    return {
        "numerator": numerator,
        "denominator": denominator,
        "estimate": p,
        "wilson95": [max(0, center - half), min(1, center + half)],
        "status": "SMALL_N" if denominator < 10 else "MEASURED",
    }


def latency(values):
    ordered = sorted(values)
    return {
        "n": len(values),
        "median_ms": statistics.median(values) if values else None,
        "p95_ms": ordered[math.ceil(0.95 * len(values)) - 1] if values else None,
        "max_ms": max(values) if values else None,
    }


def freeze_json(path: Path, value):
    """Create immutable result; a rerun must use a distinct pass filename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(value, indent=2, sort_keys=True) + "\n"
    if path.exists():
        if path.read_text() != content:
            raise FileExistsError(f"immutable artifact exists: {path}")
    else:
        with path.open("x") as stream:
            stream.write(content)


def append_result(path: Path, value):
    """Each live result is flushed and synced before proceeding to another case."""
    with path.open("a") as stream:
        stream.write(json.dumps(value, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def field_score(expected, actual):
    e = {json.dumps(x, sort_keys=True) for x in expected}
    a = {json.dumps(x, sort_keys=True) for x in actual}
    tp = len(e & a)
    return {"tp": tp, "fp": len(a - e), "fn": len(e - a)}
