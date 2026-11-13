# Phase 3 grounded-synthesis evaluation

Claim-level contracts and deterministic rejection tests are implemented. In particular, claims without evidence, unknown evidence IDs, evidence outside a bundle, and invented NASA open questions are rejected. Live execution against `nvidia/nemotron-3.5-lightning-30b-a3b` made 10 requests over the frozen synthesis cases. All 10 returned invalid `GroundedAnswerDraft` structured output and were rejected before any draft claim could become visible. Median request latency was 1853.9 ms; max 2182.2 ms.

Generated drafts: 0; accepted generated claims: 0; unsupported visible claims: 0; extractive fallback required: 10/10. Citation coverage and evidence validity for accepted generated claims are undefined (zero-denominator), not 1.0. The safe runtime result is extractive fallback.
