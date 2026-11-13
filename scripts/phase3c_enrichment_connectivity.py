"""Minimal bounded requests through existing authorized adapters."""

import json
import sys
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nasa_fire_ai.config import Settings
from nasa_fire_ai.llm.interfaces import NvidiaStructuredClient
from nasa_fire_ai.llm.jev import classify_epistemic
from nasa_fire_ai.query.controlled_reasoning import NemotronControlledReasoner
from nasa_fire_ai.query.v2 import SemanticRegistry

out = ROOT / "artifacts/phase3c_enrichment_connectivity_v1.json"
if out.exists():
    raise FileExistsError(out)
s = Settings()
client = NvidiaStructuredClient(s.nvidia_api_key, s.nvidia_base_url, s.nvidia_phase3_model)
model = NemotronControlledReasoner(client.client, s.nvidia_phase3_model, SemanticRegistry())
rows = []
for provider in ["NVIDIA", "Jev"]:
    started = perf_counter()
    row = {"provider": provider, "new_calls": 1, "execution_mode": "NEW_LIVE_REQUEST"}
    try:
        if provider == "NVIDIA":
            output, usage = model._json_call(
                'Return JSON {"status":"ok"}.', "Connectivity check only.", 30
            )
            row.update(output=output, usage=usage, model=s.nvidia_phase3_model)
        else:
            row["output"] = classify_epistemic({"text": "Connectivity check. No scientific claim."})
        row["status"] = "PASS"
    except Exception as exc:  # noqa: BLE001 - bounded provider boundary
        row.update(status="FAIL", error=type(exc).__name__)
        if getattr(exc, "response", None) is not None:
            row["http_status"] = exc.response.status_code
    row["latency_ms"] = (perf_counter() - started) * 1000
    rows.append(row)
out.write_text(json.dumps(rows, indent=2))
print(json.dumps([{"provider": r["provider"], "status": r["status"]} for r in rows]))
