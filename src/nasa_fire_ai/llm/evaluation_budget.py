"""Local, content-addressed spending brake for controlled Sonnet evaluations."""

import hashlib
import json
import os
from pathlib import Path


class EvaluationBudget:
    def __init__(self):
        self.directory = Path(os.getenv("NASA_SONNET_EVAL_DIR", "data/index/sonnet_evaluation"))
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.cap_usd = min(float(os.getenv("NASA_SONNET_EVAL_USD_CAP", "15")), 15.0)
        self.cap_calls = min(int(os.getenv("NASA_SONNET_EVAL_CALL_CAP", "40")), 40)
        self.input_limit = int(os.getenv("NASA_SONNET_EVAL_MAX_INPUT_TOKENS", "50000"))
        self.output_limit = int(os.getenv("NASA_SONNET_EVAL_MAX_OUTPUT_TOKENS", "10000"))

    def key(self, model, stage, system, payload, schema, max_tokens):
        contract = {
            "provider": "anthropic",
            "model": model,
            "stage": stage,
            "system": system,
            "payload": payload,
            "schema": schema,
            "max_tokens": max_tokens,
        }
        serialized = json.dumps(contract, ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(serialized.encode()).hexdigest(), len(serialized.encode())

    def cached(self, key):
        path = self.directory / f"{key}.json"
        return json.loads(path.read_text()) if path.exists() else None

    def authorize(self, key, input_bytes, max_tokens):
        # UTF-8 bytes upper-bound token count for text; allow protocol overhead.
        maximum_input = input_bytes + 2048
        if maximum_input > self.input_limit or max_tokens > self.output_limit:
            raise RuntimeError("Sonnet evaluation request exceeds configured token limits")
        records = [json.loads(p.read_text()) for p in self.directory.glob("*.json")]
        if any(
            r.get("error") in {"RateLimitError", "AuthenticationError", "PermissionDeniedError"}
            or r.get("error_status") in {402, 429}
            for r in records
        ):
            raise RuntimeError("Sonnet evaluation stopped after provider limit or credit failure")
        attempts = [r for r in records if r.get("paid_attempt")]
        spent = sum(float(r.get("cost_usd", 0)) for r in attempts)
        reserve = sum(
            float(r.get("reserved_max_usd", 0))
            for r in attempts
            if r.get("error") and not r.get("usage")
        )
        estimated_max = maximum_input * 2 / 1_000_000 + max_tokens * 10 / 1_000_000
        if len(attempts) >= self.cap_calls or spent + reserve + estimated_max > self.cap_usd:
            raise RuntimeError("Sonnet evaluation call or USD cap reached")
        # Reserve before calling; failed/unknown-billing attempts retain their bound.
        self.save(
            key,
            {
                "paid_attempt": True,
                "reserved_max_usd": estimated_max,
                "error": "pending",
                "cost_usd": 0,
            },
        )

    def save(self, key, record):
        path = self.directory / f"{key}.json"
        temp = self.directory / f".{key}.tmp"
        temp.write_text(json.dumps(record, ensure_ascii=False, sort_keys=True))
        temp.replace(path)
        path.chmod(0o600)


def sonnet_cost_usd(usage):
    """Published Sonnet 5.5 input/output rates, including provider cache usage."""
    usage = usage or {}
    return (
        usage.get("input_tokens", 0) * 2
        + usage.get("cache_creation_input_tokens", 0) * 2.5
        + usage.get("cache_read_input_tokens", 0) * 0.1
        + usage.get("completion_tokens", 0) * 10
    ) / 1_000_000
