"""Three justified pilot retries using the existing Jev adapter contract."""

import json
import sys
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.llm.jev import classify_epistemic

out = ROOT / "artifacts/phase3c_knowledge_jev_retry_v1.jsonl"
if out.exists():
    raise FileExistsError(out)
evidence = EvidenceRegistry(Settings().registry_path)
for eid in ["E-751f8e0f5230aa68", "E-safety-saffire-observation", "E-safety-saffire-intervention"]:
    started = perf_counter()
    row = {
        "case_id": eid,
        "new_calls": 1,
        "reason": "Initial pilot used unsupported question/choices fields; retry through unchanged existing classify_epistemic adapter",
        "execution_mode": "NEW_LIVE_REQUEST",
    }
    try:
        row["output"] = classify_epistemic({"text": evidence.resolve(eid)["text"][:7000]})
        row["status"] = "PASS"
    except Exception as exc:  # noqa: BLE001 - bounded service boundary
        row["status"] = "FAIL"
        row["error"] = type(exc).__name__
        if getattr(exc, "response", None) is not None:
            row["http_status"] = exc.response.status_code
    row["latency_ms"] = (perf_counter() - started) * 1000
    with out.open("a") as handle:
        handle.write(json.dumps(row) + "\n")
    print(json.dumps({"case_id": eid, "status": row["status"]}), flush=True)
