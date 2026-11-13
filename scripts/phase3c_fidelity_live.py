"""Four bounded new source-context advisory calls, each checkpointed; no publication."""

import hashlib
import json
import sys
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from phase3c_fidelity_campaign import stores

from nasa_fire_ai.config import Settings
from nasa_fire_ai.evaluation.phase3c import append_result, freeze_json
from nasa_fire_ai.evaluation.reconstruction import reconstruct_passage
from nasa_fire_ai.llm.interfaces import NvidiaStructuredClient
from nasa_fire_ai.llm.jev import JevSettings, classify_epistemic, decision_value
from nasa_fire_ai.query.controlled_reasoning import NemotronControlledReasoner


def main():
    path = ROOT / "artifacts/phase3c_fidelity_live_v2.jsonl"
    cached = [json.loads(l) for l in path.read_text().splitlines()] if path.exists() else []
    settings = Settings()
    evidence, store = stores()
    rec = json.loads((ROOT / "artifacts/phase3c_fidelity_reconstruction_v1.json").read_text())
    documentary = {
        eid: reconstruct_passage(eid, evidence, ROOT)
        for eid in [
            "E-safety-saffire-observation",
            "E-safety-saffire-intervention",
            "E-safety-saffire-suppression-open-question",
            "E-safety-suppression-system-implication",
        ]
    }
    freeze_json(ROOT / "artifacts/phase3c_fidelity_documentary_sources_v2.json", documentary)
    approach = next(
        c["value"]
        for c in rec["investigation_contexts"]["psi-25"]["source_comments"]
        if c["name"] == "Approach"
    )
    anaphora = documentary["E-safety-saffire-suppression-open-question"]
    inputs = [
        (
            "NVIDIA",
            "bass_execution_scope",
            {
                "context": approach,
                "run": rec["source_records"]["E-psi-25-table-B1"]["structured_row"],
                "headers": rec["source_records"]["E-psi-25-table-B1"]["original_headers"],
                "question": "Which exact source span establishes gravity for this particular run? If run scope is not linked, say unresolved.",
            },
        ),
        (
            "NVIDIA",
            "anaphoric_question_context",
            {
                "passage": anaphora["registry_passage"]["text"],
                "source_page": anaphora.get("source_page_text", ""),
                "question": "Identify the antecedent of these questions; keep the experimental observation separate from a normative safety inference.",
            },
        ),
        (
            "Jev",
            "anaphoric_question",
            {
                "passage": anaphora["registry_passage"]["text"],
                "source_context": anaphora.get("source_page_text", ""),
            },
        ),
        (
            "Jev",
            "safety_implication",
            {
                "passage": documentary["E-safety-suppression-system-implication"][
                    "registry_passage"
                ]["text"]
            },
        ),
    ]
    prompt = 'Return JSON {"proposals":[{"supporting_span":string,"scope":string,"limitation":string}],"unresolved":boolean}. Quote exact supplied source spans only. Distinguish investigation context from a particular execution. Do not infer gravity or establish new facts. An objective, topic, or title does not prove an experiment outcome. No expert approval.'
    reasoner = None
    for provider, case, payload in inputs:
        if case == "bass_execution_scope":
            continue  # v1 already answers this scope question; do not repeat inference.
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        previous = next(
            (
                r
                for r in cached
                if r["case"] == case
                and r["input_digest"] == digest
                and r.get("status") == "SUCCESS"
            ),
            None,
        )
        if previous:
            print({"case": case, "execution": "CACHED_REPLAY"}, flush=True)
            continue
        row = {
            "provider": provider,
            "case": case,
            "input": payload,
            "input_digest": digest,
            "prompt_version": "fidelity-source-context-v1",
            "execution": "FRESH_INFERENCE",
            "new_calls": 1,
            "replayed_calls": 0,
            "canonical_changes": 0,
            "expert_label": None,
        }
        started = perf_counter()
        try:
            if provider == "NVIDIA":
                if reasoner is None:
                    client = NvidiaStructuredClient(
                        settings.nvidia_api_key,
                        settings.nvidia_base_url,
                        settings.nvidia_phase3_model,
                    )
                    reasoner = NemotronControlledReasoner(
                        client.client, settings.nvidia_phase3_model, store.registry
                    )
                output, usage = reasoner._json_call(prompt, json.dumps(payload), 700)
                row.update(
                    model=settings.nvidia_phase3_model,
                    output=output,
                    usage=usage,
                    prompt_digest=hashlib.sha256(prompt.encode()).hexdigest(),
                )
                proposals = output.get("proposals", [])
                source_text = " ".join(v for v in payload.values() if isinstance(v, str))
                row["proposal_validation"] = [
                    {
                        "span_exact": bool(p.get("supporting_span"))
                        and p["supporting_span"] in source_text,
                        "publication": "REJECTED_FOR_AUTOMATIC_PUBLICATION; scope requires scientist/source validation",
                    }
                    for p in proposals
                ]
            else:
                output = classify_epistemic(payload)
                label, confidence = decision_value(output, "epistemic_type")
                row.update(
                    model=JevSettings().model,
                    output=output,
                    proposal=label,
                    confidence=confidence,
                    usage=None,
                    proposal_validation="ADVISORY_ONLY; rhetorical class does not resolve anaphoric content or scientific applicability",
                )
            row["status"] = "SUCCESS"
        except Exception as error:  # noqa: BLE001
            row.update(status="FAILED", error_type=type(error).__name__)
        row["latency_ms"] = (perf_counter() - started) * 1000
        append_result(path, row)
        print({"case": case, "status": row["status"], "latency_ms": row["latency_ms"]}, flush=True)


if __name__ == "__main__":
    main()
