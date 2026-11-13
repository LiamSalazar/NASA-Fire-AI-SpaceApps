#!/usr/bin/env python3
"""Constrained NVIDIA extraction: candidates only, cached by passage and model."""

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

from openai import APIStatusError, APITimeoutError, OpenAI

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.phase1 import CandidateRecord, stable_id, validate_candidate

PROMPT_VERSION = "phase1-rhetorical-v2"
EXTRACTOR_VERSION = "nvidia-openai-v1"
ALLOWED = {
    "MeasurementObservation": "CandidateMeasurementObservation",
    "ReportedExperimentalObservation": "CandidateReportedExperimentalObservation",
    "Intervention": "CandidateIntervention",
    "NASAConclusion": "CandidateNASAConclusion",
    "SafetyImplication": "CandidateSafetyImplication",
    "Requirement": "CandidateRequirement",
    "Guidance": "CandidateGuidance",
    "DesignCriterion": "CandidateDesignCriterion",
    "TestCriterion": "CandidateTestCriterion",
    "NASAIdentifiedOpenQuestion": "CandidateOpenQuestion",
    "PublicationRelation": "CandidatePublicationRelation",
    "CandidateOntologyConcept": "CandidateOntologyConcept",
}

PROMPT = """Extract only explicit NASA scientific/safety candidates. Return JSON only {\"candidates\":[{\"proposed_type\":type,\"exact_evidence_span\":contiguous quote,\"normalized_content\":faithful restatement,\"scope\":null|string,\"uncertainty\":null|string,\"modality\":null|string,\"negation\":true|false,\"term\":null|string}]}. Types: MeasurementObservation, ReportedExperimentalObservation, Intervention, NASAConclusion, SafetyImplication, Requirement, Guidance, DesignCriterion, TestCriterion, NASAIdentifiedOpenQuestion, PublicationRelation, CandidateOntologyConcept. Return [] often. A title/project name/topic/objective/theme/heading/noun phrase/infrastructure statement/planned capability/future benefit/relevance-impact statement is NOT a conclusion, observation, implication, or open question. Approach/Methods is not an observed result. A question/topic is an OpenQuestion only with explicit unresolved/further-work/knowledge-gap language. Results may support observations; Conclusions may support conclusions; a standard requirement section plus shall may support requirement. Preserve may/might/could/possible/shall/should/must, negation, scope, quantities and units. Never infer causality, applicability, recommendations, or ontology concepts."""


def call(client, settings, text):
    for attempt in range(2):
        try:
            response = client.chat.completions.create(
                model=settings.nvidia_extraction_model,
                messages=[{"role": "system", "content": PROMPT}, {"role": "user", "content": text}],
                temperature=0.0,
                max_tokens=1800,
                stream=False,
                extra_body={"chat_template_kwargs": {"enable_thinking": False}},
            )
            return response.choices[0].message.content
        except (APIStatusError, APITimeoutError):
            if attempt == 1:
                raise
            time.sleep(2**attempt)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--document", required=True)
    parser.add_argument("--pages", nargs="*", type=int)
    parser.add_argument("--limit", type=int, default=3)
    args = parser.parse_args()
    settings = Settings()
    if not (
        settings.nvidia_api_key and settings.nvidia_base_url and settings.nvidia_extraction_model
    ):
        print(json.dumps({"status": "PENDING_CONFIGURATION"}))
        return
    registry = EvidenceRegistry(settings.registry_path)
    query = "SELECT p.*,s.source_type,s.nasa_id,s.title FROM passages p JOIN documents d ON d.document_id=p.document_id JOIN sources s ON s.source_id=d.source_id WHERE p.document_id=?"
    params = [args.document]
    if args.pages:
        query += f" AND page IN ({','.join('?' * len(args.pages))})"
        params.extend(args.pages)
    query += " ORDER BY page,start_offset LIMIT ?"
    params.append(args.limit)
    rows = registry.db.execute(query, params).fetchall()
    client = OpenAI(base_url=settings.nvidia_base_url, api_key=settings.nvidia_api_key)
    stats = {"cached": 0, "candidates": 0, "validated": 0, "review": 0, "rejected": 0}
    batch = stable_id("batch", args.document, settings.nvidia_extraction_model)
    registry.begin_batch(batch, args.document, "NVIDIA candidate extraction")
    for row in rows:
        row = dict(row)
        key = hashlib.sha256(
            "|".join(
                [
                    row["checksum"] or "",
                    hashlib.sha256(row["text"].encode()).hexdigest(),
                    settings.nvidia_extraction_model,
                    EXTRACTOR_VERSION,
                    PROMPT_VERSION,
                ]
            ).encode()
        ).hexdigest()
        cached = registry.db.execute(
            "SELECT response_json FROM extraction_cache WHERE cache_key=?", (key,)
        ).fetchone()
        if cached:
            payload = json.loads(cached[0])
            stats["cached"] += 1
        else:
            try:
                payload = json.loads(call(client, settings, row["text"]))
            except (json.JSONDecodeError, APIStatusError, APITimeoutError):
                registry.db.execute(
                    "INSERT OR REPLACE INTO extraction_cache VALUES (?,?,?,datetime('now'))",
                    (key, "{}", "FAILED"),
                )
                registry.db.commit()
                continue
            registry.db.execute(
                "INSERT OR REPLACE INTO extraction_cache VALUES (?,?,?,datetime('now'))",
                (key, json.dumps(payload), "COMPLETED"),
            )
            registry.db.commit()
        for item in payload.get("candidates", []):
            span = item.get("exact_evidence_span", "")
            if span not in row["text"] or item.get("proposed_type") not in ALLOWED:
                continue
            candidate = CandidateRecord(
                candidate_id=stable_id("llm", row["evidence_id"], span, item["proposed_type"]),
                candidate_type=ALLOWED[item["proposed_type"]],
                normalized_text=item.get("normalized_content") or span,
                evidence_id=row["evidence_id"],
                source_document=args.document,
                page=row["page"],
                section=row["section"],
                extraction_method="llm",
                extraction_model=settings.nvidia_extraction_model,
                prompt_version=PROMPT_VERSION,
                source_context=f"{row['source_type'] or 'unknown source'}; {row['section'] or 'unlabeled section'}",
                term=item.get("term"),
                evidence_span=span,
                local_heading=row["section"],
                source_type=row["source_type"],
                scope=item.get("scope"),
                uncertainty=item.get("uncertainty"),
                modality=item.get("modality"),
                negation=item.get("negation"),
            )
            status, error = validate_candidate(candidate, registry)
            stats["candidates"] += 1
            stats[
                {"VALIDATED": "validated", "REVIEW_REQUIRED": "review", "REJECTED": "rejected"}[
                    status
                ]
            ] += 1
            fingerprint = hashlib.sha256(candidate.model_dump_json().encode()).hexdigest()
            registry.add_candidate(
                {
                    "candidate_id": candidate.candidate_id,
                    "batch_id": batch,
                    "candidate_type": candidate.candidate_type,
                    "payload_json": candidate.model_dump_json(),
                    "evidence_id": candidate.evidence_id,
                    "status": status,
                    "validation_error": error,
                    "fingerprint": fingerprint,
                }
            )
            if status == "REVIEW_REQUIRED":
                registry.review(
                    stable_id("review", candidate.candidate_id),
                    batch,
                    candidate.candidate_id,
                    error or "review",
                    candidate.model_dump_json(),
                )
    print(
        json.dumps(
            {
                "document": args.document,
                "model": settings.nvidia_extraction_model,
                "passages": len(rows),
                **stats,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
