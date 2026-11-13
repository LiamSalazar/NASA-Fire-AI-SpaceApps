# Final native end-to-end results

The service path used was natural language → persisted live Nemotron minimal
proposal → current deterministic V2 resolution → native graph/evidence
selection → FTS5/BM25 → EvidenceBundle → deterministic quotation/fallback
presentation. Runtime guards passed in all 20 cases; no V1 compatibility
executor was called. The previous live linguistic output was reused, so this is
not a new 20-call serial API benchmark and language latency is not restated.

Post-repair service results: planning guard 20/20; exact semantic interpretation
6/20; objective evidence/no-answer recovery 11/12; strict full objective
success 2/20; and useful safe fallback under the objective denominator 11/20.
Eight cases remain `REVIEW_REQUIRED`. The test records contain actual intent,
prior intent, query trace, candidate IDs, evidence omissions, source metadata,
rendered answer, fallback, and native latency.

Native retrieval median/p95/max was approximately 69.2/139.8/159.6 ms (N=20).
This excludes cached language interpretation and no new synthesis call was
made. Historical bounded synthesis remains quotation-gated; unrestricted
paraphrase fidelity has no independently reviewed gold. A rejected generation
is not counted as safe-system success. No visible unsupported scientific claim
is promoted by this repair pass, but the result is not interpreted as proof of
paraphrase safety.

The largest remaining failures are standalone information/class resolution,
range interpretation (15/26 endpoint correctness), exact evidence-set
precision, and response usefulness across the eight review-required cases.
The native executor itself passes dynamic generic-property regression but the
product path remains experimental pending language and independent relevance
review.
