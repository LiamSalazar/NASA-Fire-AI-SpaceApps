"""Bounded checkpointed new inference; adapters retain existing configuration."""

import hashlib
import json
import sys
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.llm.interfaces import NvidiaStructuredClient
from nasa_fire_ai.llm.jev import JevSettings, classify_epistemic
from nasa_fire_ai.query.controlled_reasoning import NemotronControlledReasoner
from nasa_fire_ai.query.native_interpreter import SYSTEM_PROMPT, MinimalInterpretationV2
from nasa_fire_ai.query.v2 import SemanticRegistry


def main():
    path = ROOT / "artifacts/phase3c_targeted_live_v1.jsonl"
    if path.exists():
        raise FileExistsError(path)
    settings = Settings()
    evidence = EvidenceRegistry(settings.registry_path)
    adapter = NvidiaStructuredClient(
        settings.nvidia_api_key, settings.nvidia_base_url, settings.nvidia_phase3_model
    )
    reasoner = NemotronControlledReasoner(
        adapter.client, settings.nvidia_phase3_model, SemanticRegistry()
    )
    cases = [
        ("intent", SYSTEM_PROMPT, query)
        for query in [
            "BASS tests",
            "BASS-II tests",
            "Does acrylic mean PMMA?",
            "What has NASA reported about suppressing PMMA fires in microgravity?",
        ]
    ]
    for eid in [
        "E-safety-saffire-observation",
        "E-safety-saffire-intervention",
        "E-751f8e0f5230aa68",
    ]:
        passage = evidence.resolve(eid)
        if passage:
            cases.append(
                (
                    "context",
                    'Return JSON {"epistemic_role":string,"complete_question":boolean,"source_span":string,"limitations":string}. Copy an exact source span. Do not infer an antecedent or scientific facts.',
                    passage["text"],
                )
            )
    for kind, prompt, content in cases:
        started = perf_counter()
        row = {
            "provider": "NVIDIA",
            "model": settings.nvidia_phase3_model,
            "prompt_version": "targeted-context-intent-v1",
            "prompt_digest": hashlib.sha256(prompt.encode()).hexdigest(),
            "input": content,
            "input_digest": hashlib.sha256(content.encode()).hexdigest(),
            "new_calls": 1,
            "replayed_calls": 0,
            "kind": kind,
            "scientific_authority": "NONE; independent review pending",
        }
        try:
            output, usage = reasoner._json_call(prompt, content, 800)
            if kind == "intent":
                MinimalInterpretationV2.model_validate(output)
            else:
                span = output.get("source_span")
                if not span or span not in content:
                    raise ValueError("unsupported source span")
            row.update(
                status="CONTRACT_VALID",
                output=output,
                usage=usage,
                scientific_incremental_value="NOT_MEASURABLE",
            )
        except Exception as exc:  # noqa: BLE001 — sanitized provider fallback
            row.update(status="FAILED", error_type=type(exc).__name__)
        row["latency_ms"] = (perf_counter() - started) * 1000
        with path.open("a") as handle:
            handle.write(json.dumps(row) + "\n")
        print(json.dumps({"provider": "NVIDIA", "kind": kind, "status": row["status"]}), flush=True)
    for eid in [
        "E-safety-saffire-observation",
        "E-safety-saffire-intervention",
        "E-751f8e0f5230aa68",
    ]:
        passage = evidence.resolve(eid)
        if not passage:
            continue
        started = perf_counter()
        row = {
            "provider": "Jev",
            "model": JevSettings().model,
            "evidence_id": eid,
            "input_digest": hashlib.sha256(passage["text"].encode()).hexdigest(),
            "prompt_version": "existing-adapter-epistemic-v1",
            "new_calls": 1,
            "replayed_calls": 0,
            "scientific_authority": "ADVISORY_ONLY",
            "incremental_value": "NOT_MEASURABLE",
            "usage": "adapter does not expose token usage",
        }
        try:
            row.update(status="CONTRACT_VALID", output=classify_epistemic(passage))
        except Exception as exc:  # noqa: BLE001 — sanitized provider fallback
            row.update(status="FAILED", error_type=type(exc).__name__)
        row["latency_ms"] = (perf_counter() - started) * 1000
        with path.open("a") as handle:
            handle.write(json.dumps(row) + "\n")
        print(json.dumps({"provider": "Jev", "status": row["status"]}), flush=True)


if __name__ == "__main__":
    main()
