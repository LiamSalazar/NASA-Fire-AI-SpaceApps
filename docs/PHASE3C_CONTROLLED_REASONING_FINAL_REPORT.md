# Phase 3C controlled semantic reasoning — final iteration report

## Outcome

The controlled-reasoning implementation and repository gates are complete for this iteration. The experimental features remain opt-in. Phase 4 readiness remains **NO**: the A/B/C/D regression did not improve objective evidence identity recovery, and there is no independently reviewed scientific-relevance gold with which to measure precision or justify model-based promotion.

## Implemented

- Added bounded Nemotron query expansion and contextual passage reranking behind default-off feature flags. Candidate IDs are whitelisted, high/medium relevance requires an exact passage span, and deterministic native constraints retain decision authority.
- Kept contextual candidates separate from DIRECT and RELATED evidence. Expansion/reranking failures fall back to deterministic V2 retrieval; they cannot create canonical facts or change scientific classifications.
- Added ambiguity handling for several canonical values in one relation slot, avoiding a false conjunctive interpretation for the PMMA/SIBAL case.
- Added a source-backed comparison renderer that exposes shared/different/unknown measurements and explicitly avoids causal or statistical claims.
- Corrected source-location wording so unverified extracted page numbers are not presented as physical PDF pages.
- Preserved original frozen gold and benchmark receipts. Gold reconciliation is a proposal only: 16 discrepancies comprise 8 structural-contract proposals, 7 requiring semantic review, and 1 unresolved; none is approved or described as scientist-reviewed.

## A/B/C/D results

On the exposed 20-case regression (8 objectively scoreable evidence-identity cases, 8 review-required cases, 4 objective no-direct cases), expected evidence identity recall was 7/8 (0.875) for A native, budget-matched A, B expansion, C expansion plus reranking, and D plus Jev. This small-N identity result is not evidence-relevance precision. All configurations retained zero false DIRECT results on the four objective no-direct cases (0/4).

Expansion accepted 7 of 54 proposed formulations and rejected 47. It produced no recovery of the missing expected evidence identity over the budget-matched lexical control. The compact reranker made 18 requests: 14 returned usable judgments and 4 failed (one timeout, two invalid JSON, one validation error). It produced 61 candidate judgments; the 24 HIGH/MEDIUM judgments retained exact verbatim support spans. No independent relevance labels exist, so relevance precision, recall over subjective candidates, and reranker benefit are **not scoreable**.

Jev was used only as advisory triage (25 calls, alias `jev-latest`, observed response model `jev-1.13.0`). Its incremental value is unestablished without independent labels; it remains optional.

## Gold, review and remaining scientific gate

The 11-case review packet contains 224 source-backed candidates, including the eight unresolved cases and additional retrieval candidates. Human reviewer fields remain blank. The 16 requested-information proposals remain unadjudicated. The `qi42` ambiguity now triggers clarification rather than treating PMMA and SIBAL as simultaneous required values on one run. The `qi12` comparison rendering identifies shared airflow, differing oxygen and flow direction, unknown pressure, cites the two run evidence IDs, and does not infer causality or significance.

The local source for NTRS 20040053586 lacks a verifiable physical PDF page map. The user-facing location label therefore marks the stored page integer as unverified. A separate NTRS suppression/open-question passage was verified against physical PDF page 16. No raw source was changed.

## Integrity and quality

`artifacts/phase3c_controlled_integrity_v1.json` reports PASS: canonical and native SHACL conform; SQLite integrity is `ok` with zero foreign-key violations; Evidence Registry counts are 282 sources, 286 documents, and 6,055 passages with 6,055 FTS entries, no missing FTS rows or orphan passages; the native graph contains 20,447 triples and zero broken evidence references; all four staging rows have complete provenance/state. Historical evaluation, raw-source and canonical-data digests remain unchanged. Nine code/config digest differences from the earlier baseline are implementation files; none is a historical evaluation or data file.

Quality commands passed: `uv run ruff format --check .`, `uv run ruff check .`, and `uv run pytest -q` (103 passed; 197 rdflib deprecation warnings). Existing dynamic extensibility results (230/230 and 125/125) were retained, not rerun.

## Decisions

- `GOLD_RECONCILIATION_DECISION = REVIEW_REQUIRED`
- `NEMOTRON_QUERY_EXPANSION_DECISION = KEEP_EXPERIMENTAL`
- `NEMOTRON_CONTEXTUAL_RERANKING_DECISION = KEEP_EXPERIMENTAL`
- `JEV_ADVISORY_DECISION = KEEP_OPTIONAL`
- `SCIENTIFIC_PARAPHRASE_DECISION = KEEP_RESTRICTED`
- `V2_DEFAULT_PATH_DECISION = KEEP_EXPERIMENTAL`
- `READY_FOR_PHASE_4 = NO`

Minimum remaining action is independent scientific adjudication of the 16 gold proposals and the 11-case/224-candidate relevance packet, followed by a separately reported relevance evaluation. Resolve physical page provenance only if a page citation is required. No further architecture phase is implied.

Machine-readable summary: `artifacts/phase3c_controlled_reasoning_final_results_v1.json`.
