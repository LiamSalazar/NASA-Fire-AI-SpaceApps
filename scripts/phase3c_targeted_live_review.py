"""Additional bounded source-table and RELATED review proposals, no publication authority."""

import hashlib
import json
import sys
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nasa_fire_ai.config import Settings
from nasa_fire_ai.llm.interfaces import NvidiaStructuredClient
from nasa_fire_ai.query.controlled_reasoning import NemotronControlledReasoner
from nasa_fire_ai.query.v2 import SemanticRegistry


def main():
    path = ROOT / "artifacts/phase3c_targeted_live_review_v1.jsonl"
    assert not path.exists()
    settings = Settings()
    client = NvidiaStructuredClient(
        settings.nvidia_api_key, settings.nvidia_base_url, settings.nvidia_phase3_model
    )
    reasoner = NemotronControlledReasoner(
        client.client, settings.nvidia_phase3_model, SemanticRegistry()
    )
    reports = json.loads((ROOT / "artifacts/phase3c_targeted_psi_publication_v2.json").read_text())
    bass = next(r for r in reports if r["investigation"] == "BASS")
    flex = next(r for r in reports if r["investigation"] == "FLEX-2")
    cases = [
        ("bass_table", {"headers": bass["original_headers"], "rows": bass["rows"][:3]}),
        ("flex2_configuration", {"headers": flex["original_headers"], "rows": flex["rows"][:2]}),
    ]
    scientific = json.loads(
        (ROOT / "artifacts/phase3c_targeted_scientific_cases_v2.json").read_text()
    )
    case = next(r for r in scientific if r["case_id"] == "qi03")
    candidates = case["variants"]["B"]["related"][:5]
    cases.append(
        ("related_review", {"original_query": case["original_query"], "candidates": candidates})
    )
    for kind, payload in cases:
        prompt = (
            'Return JSON {"proposals":[{"candidate_id":string,"relevance":string,"reason":string}],"limitations":[string]}. '
            "Review only the supplied source records and relationship dimensions. UNKNOWN is not MATCH or DIFFER. "
            "Do not assert new science or material equivalence. Distinguish a sample/configuration row from a run. "
            "A material match alone does not answer a requested phenomenon. Proposals are unapproved engineering review."
        )
        content = json.dumps(payload)
        row = {
            "provider": "NVIDIA",
            "model": settings.nvidia_phase3_model,
            "kind": kind,
            "prompt_version": "targeted-structured-related-v1",
            "prompt_digest": hashlib.sha256(prompt.encode()).hexdigest(),
            "input_digest": hashlib.sha256(content.encode()).hexdigest(),
            "input": payload,
            "new_calls": 1,
            "replayed_calls": 0,
            "incremental_value": "NOT_MEASURABLE",
            "canonical_changes": 0,
        }
        started = perf_counter()
        try:
            output, usage = reasoner._json_call(prompt, content, 900)
            if not isinstance(output.get("proposals"), list) or not isinstance(
                output.get("limitations"), list
            ):
                raise TypeError("invalid contract")
            row.update(
                status="CONTRACT_VALID",
                output=output,
                usage=usage,
                semantic_support="REVIEW_REQUIRED",
            )
        except Exception as exc:  # noqa: BLE001
            row.update(status="FAILED", error_type=type(exc).__name__)
        row["latency_ms"] = (perf_counter() - started) * 1000
        with path.open("a") as handle:
            handle.write(json.dumps(row) + "\n")
        print({"kind": kind, "status": row["status"]}, flush=True)


if __name__ == "__main__":
    main()
