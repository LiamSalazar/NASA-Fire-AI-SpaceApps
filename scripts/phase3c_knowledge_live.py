"""Bounded live pilot; outputs remain proposals and are checkpointed per call."""

import hashlib
import json
import sys
from pathlib import Path
from time import perf_counter

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.knowledge import validate_relation_proposal
from nasa_fire_ai.ingestion.semantic import project_legacy
from nasa_fire_ai.llm.interfaces import NvidiaStructuredClient
from nasa_fire_ai.llm.jev import ask
from nasa_fire_ai.query.controlled_reasoning import NemotronControlledReasoner
from nasa_fire_ai.query.native import execute_native
from nasa_fire_ai.query.offline_parser import parse_query
from nasa_fire_ai.query.v2 import v1_to_v2

ART = ROOT / "artifacts"
OUT = ART / "phase3c_knowledge_live_calls_v1.jsonl"


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    settings = Settings()
    evidence = EvidenceRegistry(settings.registry_path)
    store = project_legacy(ROOT, evidence)
    adapter = NvidiaStructuredClient(
        settings.nvidia_api_key, settings.nvidia_base_url, settings.nvidia_phase3_model
    )
    reasoner = NemotronControlledReasoner(
        adapter.client,
        settings.nvidia_phase3_model,
        store.registry,
        yaml.safe_load((ROOT / "domain/query_language_v2.yaml").read_text()),
    )

    def checkpoint(row):
        with OUT.open("a") as handle:
            handle.write(json.dumps(row) + "\n")
        print(
            json.dumps(
                {
                    "component": row["component"],
                    "case_id": row["case_id"],
                    "status": row.get("status", "RECORDED"),
                }
            ),
            flush=True,
        )

    for eid in [
        "E-751f8e0f5230aa68",
        "E-safety-saffire-observation",
        "E-safety-saffire-intervention",
    ]:
        passage = evidence.resolve(eid)
        if not passage:
            checkpoint(
                {
                    "component": "extraction",
                    "case_id": eid,
                    "status": "MISSING_PASSAGE",
                    "new_calls": 0,
                }
            )
            continue
        metadata = evidence.source_metadata(eid)
        system = (
            'Propose at most two relations stated explicitly in the supplied passage. Return JSON {"relations":[{"subject_mention":string,"predicate_candidate":string,"object_mention":string,"supporting_span":string}]}. '
            "All mentions must be exact substrings of the exact supporting span. Do not infer taxonomy, causality, observations from design values, or experimental applicability. Empty relations are permitted. Output is pending scientific review."
        )
        row = {
            "component": "extraction",
            "case_id": eid,
            "new_calls": 1,
            "model": settings.nvidia_phase3_model,
            "prompt_version": "knowledge-extraction-v1",
            "input_digest": hashlib.sha256(passage["text"].encode()).hexdigest(),
            "execution_mode": "NEW_LIVE_REQUEST",
        }
        try:
            output, usage = reasoner._json_call(system, passage["text"][:7000], 650)
            row.update(
                {
                    "status": "PASS",
                    "output": output,
                    "usage": usage,
                    "validated_proposals": [],
                    "rejected": [],
                }
            )
            for proposal in output.get("relations", []):
                try:
                    candidate = validate_relation_proposal(
                        {**proposal, "evidence_id": eid, "source_id": metadata["source_id"]},
                        evidence,
                    )
                    row["validated_proposals"].append(candidate)
                except (ValueError, TypeError) as exc:
                    row["rejected"].append({"proposal": proposal, "reason": str(exc)})
        except Exception as exc:  # noqa: BLE001 - bounded external service boundary
            row.update({"status": "FAIL", "error": type(exc).__name__})
        checkpoint(row)
        started = perf_counter()
        try:
            result = ask(
                {"text": passage["text"][:7000]},
                {
                    "role": {
                        "type": "choice",
                        "question": "Which passage role is explicit? This is advisory, not scientific verification.",
                        "choices": ["OBSERVATION", "INTERVENTION", "DESIGN", "CONTEXT", "UNKNOWN"],
                    }
                },
            )
            checkpoint(
                {
                    "component": "jev_advisory",
                    "case_id": eid,
                    "new_calls": 1,
                    "execution_mode": "NEW_LIVE_REQUEST",
                    "status": "PASS",
                    "latency_ms": (perf_counter() - started) * 1000,
                    "output": result,
                }
            )
        except Exception as exc:  # noqa: BLE001 - bounded external service boundary
            checkpoint(
                {
                    "component": "jev_advisory",
                    "case_id": eid,
                    "new_calls": 1,
                    "status": "FAIL",
                    "error": type(exc).__name__,
                }
            )

    for case_id, query in [
        ("qi19", "What about acrylic fires?"),
        ("qi27", "What has NASA reported about PMMA suppression?"),
        ("qi11", "Find PMMA experiments with airflow velocity >= 20 cm/s"),
    ]:
        intent = v1_to_v2(parse_query(query))
        expansion = reasoner.expand(query, intent)
        checkpoint(
            {
                "component": "exploratory_planning",
                "case_id": case_id,
                "status": "FAIL" if expansion.get("error") else "PASS",
                **expansion,
            }
        )
        result = execute_native(intent, query, store, evidence)
        candidates = [
            {**p, "candidate_role": "CONTEXTUAL"} for p in result.bundle.evidence_passages[:5]
        ]
        if candidates:
            rerank = reasoner.rerank(query, intent, candidates)
            checkpoint(
                {
                    "component": "reranking",
                    "case_id": case_id,
                    "status": "FAIL" if rerank.get("error") else "PASS",
                    **rerank,
                }
            )
    rows = [json.loads(line) for line in OUT.read_text().splitlines()]
    summary = {
        "calls": {
            component: sum(r.get("new_calls", 0) for r in rows if r["component"] == component)
            for component in sorted({r["component"] for r in rows})
        },
        "successful": sum(r.get("status") == "PASS" for r in rows),
        "attempted": len(rows),
        "independent_scientific_relevance": "REVIEW_REQUIRED",
        "monetary_cost": "NOT_AVAILABLE",
        "canonical_facts_published_from_model": 0,
    }
    (ART / "phase3c_knowledge_live_summary_v1.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
