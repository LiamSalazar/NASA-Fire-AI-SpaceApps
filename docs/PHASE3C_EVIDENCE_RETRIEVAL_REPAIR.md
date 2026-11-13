# Phase 3C corrective evidence retrieval

The native graph and the existing FTS5/BM25 registry now cooperate. Eligible
evidence IDs are filtered inside SQL before ranking and truncation, rather than
filtering an already truncated global result list. Source metadata is recovered
through passage → document → source, including passages without a redundant
`evidence_refs` row. Structured relation/value evidence remains attached to its
subject. Measurement-only requests do not receive unrelated safety statements.

Requested epistemic classes select existing reviewed records, subject to lexical
relevance. They do not reclassify arbitrary passages. Three older automatically
classified statements are quarantined in the native projection. Historical
canonical files and V1 behavior remain unchanged.

## Objective retrieval evaluation

`evals/phase3c_corrective_retrieval_gold_v1.json` was frozen before execution.
It contains nine existing reviewed statement identities, two immutable run/
condition probes, and one unavailable-source probe. Expected identity follows
existing reviewed records or directly verifiable canonical data, not V1 or model
predictions. Source phrases are mostly lexical; this is not independent expert
validation of paraphrase relevance.

- Positive evidence recovery: 11/11, 1.0000.
- Recall@1/3/5/10: each 11/11, 1.0000; MRR 11/11, 1.0000.
- Reviewed epistemic record recovery: 9/9, SMALL_N.
- Unavailable-source no-answer: 1/1, SMALL_N.
- Exhaustive precision@k and subjective evidence relevance: NOT_REVIEWED.

Results: `artifacts/phase3c_corrective_retrieval_summary_v1.json` and case JSONL.
Wilson intervals are stored with measured proportions. These small, near-exact
queries do not establish broad scientific retrieval accuracy.

## Compatibility and regression

On 39 historical supported inputs, DIRECT parity is 37/39 (0.9487), RELATED
parity 39/39 (1.0000), and exact evidence-ID parity 5/39 (0.1282). The two DIRECT
disagreements are BASS queries: the native path sees the expanded source-backed
projection, whereas the historical V1 execution view contains only two runs.
V1 empty results are not scientific truth. Documentary additions/omissions still
need relevance review; they are not automatically improvements.

Full case differences are in
`artifacts/phase3c_corrective_native_checks_v1/phase3c_native_parity.json`.
`artifacts/phase3c_corrective_relevance_review_packet_v1.json` preserves the
unreviewed disagreements for independent review. Evidence eligibility and
scientific-answer-input parity were not separately established as exact rates.

The 40-source BM25 regression retains Recall@1=25/40, @3=34/40, @5=34/40,
@10=36/40. MRR is 0.7267361, versus historical 0.7225694: deterministic
evidence-ID tie ordering changes reciprocal ranks. This is a disclosed ranking
difference, not an unchanged MRR claim. No global vector retrieval was enabled.

## Remaining failures

Actual natural-language end-to-end retrieval recovers required evidence in only
8/12 objectively scorable cases. Observation, guidance, and conclusion queries
can lose relevant records when genre-only language has insufficient lexical
overlap. Qualified comparison operands can remain unresolved. Exact source-backed
benchmarks passing does not repair these failures. Fix generic genre/topic
selection and qualified entity resolution, then evaluate against independently
reviewed relevance gold; do not append all safety records to every answer.
