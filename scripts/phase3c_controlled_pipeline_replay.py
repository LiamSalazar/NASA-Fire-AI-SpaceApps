"""Replay prior live language receipts through the current controlled service boundary."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from phase3c_controlled_reasoning import digest, load_jsonl

from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.semantic import project_legacy
from nasa_fire_ai.query.controlled_reasoning import (
    ControlledReasoningFlags,
    NemotronControlledReasoner,
)
from nasa_fire_ai.query.native_interpreter import MinimalInterpretationV2, resolve_minimal
from nasa_fire_ai.services.native import answer_native_controlled

INTERPRETER = ROOT / "artifacts/phase3c_final_repair_interpreter_cases_v6.jsonl"
FIRST = ROOT / "artifacts/phase3c_controlled_e2e_api_calls_v1.jsonl"
RERANK = ROOT / "artifacts/phase3c_controlled_e2e_api_calls_v4.jsonl"
OUTPUT = ROOT / "artifacts/phase3c_controlled_pipeline_replay_v3.jsonl"
CALLS = ROOT / "artifacts/phase3c_controlled_pipeline_replay_api_calls_v3.jsonl"
CASE_IDS = ("qi12", "qi24", "qi27", "qi42")


def main() -> None:
    source_rows = {
        x["case_id"]: x
        for x in load_jsonl(INTERPRETER)
        if x["case_id"] in CASE_IDS and x.get("raw_minimal_extraction")
    }
    if set(source_rows) != set(CASE_IDS):
        raise RuntimeError("One or more frozen live language receipts are missing")
    source_digest = digest(INTERPRETER)
    completed = (
        {x["case_id"]: x for x in load_jsonl(OUTPUT) if x.get("source_digest") == source_digest}
        if OUTPUT.exists()
        else {}
    )

    settings = Settings()
    evidence = EvidenceRegistry(settings.registry_path)
    store = project_legacy(ROOT, evidence)
    language = yaml.safe_load((ROOT / "domain/query_language_v2.yaml").read_text())
    model_cache = {}
    for path in (FIRST, RERANK):
        if path.exists():
            for event in load_jsonl(path):
                key = event.get("cache_key")
                if key:
                    model_cache[key] = event

    def persist_call(event):
        event["source_digest"] = source_digest
        with CALLS.open("a") as stream:
            stream.write(json.dumps(event, ensure_ascii=False) + "\n")
            stream.flush()

    reasoner = NemotronControlledReasoner(
        client=None,
        model=settings.nvidia_phase3_model,
        registry=store.registry,
        language=language,
        event_sink=persist_call,
        cache=model_cache,
    )

    flags = ControlledReasoningFlags(query_expansion=True, contextual_reranking=True)
    for case_id in CASE_IDS:
        if case_id in completed:
            continue
        receipt = source_rows[case_id]
        proposal = MinimalInterpretationV2.model_validate_json(receipt["raw_minimal_extraction"])
        intent = resolve_minimal(proposal, store.registry, language, query=receipt["query"])
        response = answer_native_controlled(
            intent,
            receipt["query"],
            store,
            evidence,
            reasoner=reasoner,
            flags=flags,
        )
        trace = response.controlled_trace or {}
        row = {
            "version": "phase3c-controlled-pipeline-replay-v3",
            "case_id": case_id,
            "query": receipt["query"],
            "source_digest": source_digest,
            "interpreter_receipt_origin": "previously persisted live Nemotron minimal interpretation; replayed without another interpretation call",
            "raw_minimal_extraction": proposal.model_dump(mode="json"),
            "resolved_intent": intent.model_dump(mode="json"),
            "native_direct_entity_ids": [
                x["id"] for x in response.execution.bundle.direct_evidence
            ],
            "native_related_entity_ids": [
                x["id"] for x in response.execution.bundle.related_evidence
            ],
            "native_evidence_ids": [
                x["evidence_id"] for x in response.execution.bundle.evidence_passages
            ],
            "contextual_candidate_ids": [
                x["evidence_id"] for x in response.execution.bundle.discovery_candidates
            ],
            "rendered_answer": response.rendered_answer,
            "grounding_policy": "quotation-only for scientific claims; discovery candidates explicitly non-supporting",
            "fallback": response.fallback,
            "grounding_errors": response.grounding_errors,
            "features": trace.get("features"),
            "model_calls": {
                name: trace.get("configurations", {}).get(name, {}).get("calls", 0)
                for name in "ABCD"
            },
            "expansion": trace.get("configurations", {}).get("B", {}).get("expansion"),
            "reranking": trace.get("configurations", {}).get("C", {}).get("reranking"),
            "interpretation_source_artifact_digest": source_digest,
            "scientific_relevance_status": "NOT_INDEPENDENTLY_REVIEWED",
        }
        with OUTPUT.open("a") as stream:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
            stream.flush()
        completed[case_id] = row
        print(
            json.dumps(
                {
                    "completed": case_id,
                    "clarification": intent.clarification_required,
                    "native_evidence": len(row["native_evidence_ids"]),
                    "contextual_candidates": len(row["contextual_candidate_ids"]),
                }
            ),
            flush=True,
        )

    summary = {
        "version": "phase3c-controlled-pipeline-replay-summary-v3",
        "status": "SMOKE_REPLAY_NOT_INDEPENDENT_END_TO_END_ACCURACY",
        "N": len(completed),
        "case_ids": list(completed),
        "source_digest": source_digest,
        "live_interpreter_calls_this_replay": 0,
        "reasoning_calls_reused_when_prompt_and_input_digest_matched": True,
        "review_required": True,
    }
    ROOT.joinpath("artifacts/phase3c_controlled_pipeline_replay_summary_v3.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n"
    )
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
