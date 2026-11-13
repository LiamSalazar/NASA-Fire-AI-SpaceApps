# Phase 3C controlled reasoning ablation protocol

## Frozen material and status

The source is the existing 20-case v6 end-to-end receipt, frozen as `evals/phase3c_controlled_e2e_regression_gold_v1.json` (digest recorded in every result). This is an **exposed regression set**, not an independent holdout. It contains eight objectively scoreable positive evidence identities, four objective corpus-scoped no-direct cases, and eight `REVIEW_REQUIRED` cases. No reviewer labels were added. Gold is never inferred from model predictions.

## Configurations

- A: native V2 execution and existing evidence passage ranking, top eight.
- A-budget-matched: A plus original-query FTS/BM25 results up to the same top-20 query budget, without model expansion.
- B: same candidate budget plus at most three validated Nemotron formulations; original question retained.
- C: B plus contextual reranking and verbatim-span validation.
- D: C plus cached optional Jev rhetorical triage. The live Jev receipts are advisory and are not an independent relevance label.

Corpus, frozen intent, source constraints, native planner and evidence-identity gold are held constant. A-budget-matched is reported because the original B implementation also broadened the raw lexical candidate budget. Candidate expansion and ranking may never alter native DIRECT/RELATED.

## Metrics and limits

Objective expected-identity recall and identity MRR are reported only on the eight positive identity cases, with Wilson intervals and `SMALL_N`. Precision@k, complete scientific relevance, safety authority and no-answer appropriateness are not scoreable without comprehensive independent labels. The four no-direct cases are checked only for accidental native DIRECT results. The eight review-required cases are surfaced in the reviewer packet, not mixed into an accuracy denominator.

Every API call has a per-case persisted receipt with model/prompt or cache identity, candidate IDs, usage when provided, latency, sanitized error type and fallback. First-pass, compact rerank pass and query-level smoke replay are kept in separate artifacts. No API cost is estimated when the provider does not return cost data.
