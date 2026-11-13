# Phase 3C controlled semantic discovery

## Implementation boundary

The deterministic QueryIntentV2 → native RDF/KG → DIRECT/RELATED → EvidenceBundle path remains the source of scientific authority and the default. New behavior is additive and opt-in through `SEMANTIC_QUERY_EXPANSION_ENABLED`, `CONTEXTUAL_RERANKING_ENABLED`, and `JEV_ADVISORY_TRIAGE_ENABLED`. `SCIENTIFIC_PARAPHRASE_ENABLED` remains disabled. All flags default false.

The controlled path retains two candidate sources: (1) validated structured entities/conditions from the KG, and (2) original-query plus accepted alternate formulations through existing FTS5/BM25. Candidate identity is the Evidence Registry evidence ID. Candidates are deduplicated and source constraints are applied before they are shown. Nemotron proposals are stored in the separate `EvidenceBundle.discovery_candidates` field. They are not added to `evidence_passages`, DIRECT, RELATED, the KG, or any canonical ontology.

The model may propose up to three query formulations and assess contextual usefulness of at most five passages in the final compact reranker. A positive relevance proposal requires a verbatim span contained in the supplied candidate; spans and evidence IDs are checked locally. The proposal remains unverified contextual metadata. Deterministic constraints and source authority remain unchanged. An invalid expansion or unavailable model call falls back to native V2/FTS; an ambiguous intent returns clarification without speculative discovery.

`answer_native_controlled_text` connects minimal linguistic extraction, deterministic `resolve_minimal`, native execution and the controlled candidate presentation. The renderer labels contextual passages as non-supporting; quotation-only grounding remains in force. Comparison output is rendered from the native `ExperimentComparison`, cites the run evidence IDs, shows unavailable fields and expressly avoids statistical or causal inference.

## Reproducibility

The current A/B/C/D regression digest is recorded in `artifacts/phase3c_controlled_ablation_analysis_v1.json`. Per-case model receipts and candidate orders are in `artifacts/phase3c_controlled_e2e_ablation_cases_v1.jsonl` and versioned reranker passes v2–v4. Feature and prompt versions, code digests, request usage, sanitized error types and the frozen gold digest are persisted. Credentials are not included.

## Guardrail

Expansion and reranking increase discovery flexibility only. They do not establish that a passage is a NASA observation, conclusion, requirement, guidance, open question, or scientific identity. Independent relevance review is still required before adopting these modes.
