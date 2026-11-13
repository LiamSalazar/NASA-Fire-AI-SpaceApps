"""Bounded new extraction pilot using existing adapters; no model publication."""

import hashlib
import json
import sys
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.knowledge import stage_relation_proposal, validate_relation_proposal
from nasa_fire_ai.llm.interfaces import NvidiaStructuredClient
from nasa_fire_ai.llm.jev import classify_epistemic
from nasa_fire_ai.query.controlled_reasoning import NemotronControlledReasoner
from nasa_fire_ai.query.v2 import SemanticRegistry


def main():
    out = ROOT / "artifacts/phase3c_enrichment_live_v1.jsonl"
    if out.exists():
        raise FileExistsError(out)
    settings = Settings()
    evidence = EvidenceRegistry(settings.registry_path)
    adapter = NvidiaStructuredClient(
        settings.nvidia_api_key, settings.nvidia_base_url, settings.nvidia_phase3_model
    )
    reasoner = NemotronControlledReasoner(
        adapter.client, settings.nvidia_phase3_model, SemanticRegistry()
    )
    ids = [
        "E-751f8e0f5230aa68",
        "E-safety-saffire-observation",
        "E-safety-saffire-intervention",
        "E-ae9ebc14b3783086",
        "E-psi-98-table-S2",
    ]
    for eid in ids:
        passage = evidence.resolve(eid)
        if not passage:
            continue
        for provider in ["NVIDIA", "Jev"]:
            row = {
                "provider": provider,
                "evidence_id": eid,
                "new_calls": 1,
                "replayed_calls": 0,
                "exposure": "PREVIOUSLY_EXPOSED_SOURCE",
                "prompt_version": "enrichment-extraction-v2",
                "input_digest": hashlib.sha256(passage["text"].encode()).hexdigest(),
            }
            started = perf_counter()
            try:
                if provider == "NVIDIA":
                    output, usage = reasoner._json_call(
                        'Return JSON {"relations":[{"subject_mention":string,"predicate_candidate":string,"object_mention":string,"supporting_span":string}],"epistemic_role":string}. At most two explicitly stated relations. Copy exact text; preserve numerical values, units, negation and design versus observation. No scientific inference. A table without headers cannot establish column meaning. All relations are pending review.',
                        passage["text"][:7000],
                        750,
                    )
                    row.update(
                        output=output,
                        usage=usage,
                        model=settings.nvidia_phase3_model,
                        validated=[],
                        rejected=[],
                    )
                    for proposal in output.get("relations", []):
                        try:
                            candidate = validate_relation_proposal(
                                {
                                    **proposal,
                                    "source_id": evidence.source_metadata(eid)["source_id"],
                                    "evidence_id": eid,
                                },
                                evidence,
                            )
                            row["validated"].append(
                                {
                                    "candidate": candidate,
                                    "staging": stage_relation_proposal(candidate, evidence),
                                    "status": "SOURCE_SPAN_VALIDATED",
                                    "semantic_status": "REVIEW_REQUIRED",
                                }
                            )
                        except (ValueError, TypeError, KeyError) as exc:
                            row["rejected"].append({"proposal": proposal, "reason": str(exc)})
                else:
                    row["output"] = classify_epistemic(passage)
                row["status"] = "PASS"
            except Exception as exc:  # noqa: BLE001
                error = str(exc)
                for secret in [
                    settings.nvidia_api_key,
                    settings.typesafe_api_key if hasattr(settings, "typesafe_api_key") else None,
                ]:
                    if secret:
                        error = error.replace(secret, "[REDACTED]")
                row.update(status="FAIL", error_type=type(exc).__name__, error=error[:1000])
            row["latency_ms"] = (perf_counter() - started) * 1000
            with out.open("a") as handle:
                handle.write(json.dumps(row) + "\n")
            print(
                json.dumps({k: row[k] for k in ["provider", "evidence_id", "status"]}), flush=True
            )


if __name__ == "__main__":
    main()
