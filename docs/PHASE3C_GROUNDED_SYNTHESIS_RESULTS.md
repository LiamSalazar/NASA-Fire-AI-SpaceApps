# Phase 3C corrective grounded synthesis

The complete-source quotation gate is retained. Evidence-ID membership alone
does not establish paraphrase fidelity. No independently reviewed paraphrase
gold exists; therefore generative scientific paraphrases remain disabled.
Deterministic headings, transitions, source listings and structured-record
presentation improve readability without inventing scientific content.

The actual native service renders readable DIRECT and RELATED evidence, reviewed
observations, NASA conclusions, requirements, guidance, criteria, open questions,
coverage and sources. Technical JSON is expandable, not the default scientific
answer. Unclassified documentary excerpts are `source_quotation` with DOCUMENTARY
presentation status, never automatically NASA observations. Reviewed design/test
criterion status is preserved. These are presentation metadata, not new KG science.

## Bounded live results

First corrective service pass: six synthesis attempts, five structurally valid
drafts, two generated/accepted claims. Separately versioned repaired service pass:
six attempts, four valid drafts, five generated/accepted claims, zero rejected
claims among valid drafts. Two unsuccessful draft/API attempts are preserved;
they are not counted as scientific fidelity successes.

Accepted citation coverage and evidence validity: 5/5, SMALL_N. Visible unsupported
generated claims: 0/5. This is a narrow exact-quotation result, not a guarantee of
zero hallucinations across the whole product. Several valid quotations appeared
in responses whose retrieval did not answer the intended question. Safe but
unhelpful responses remain product failures.

No accepted unknown or out-of-bundle evidence IDs. Exact quotations plus reviewed
metadata prevent accepted text changes to negation, modality, units or scope.
The test suite rejects negation-dropping partial quotes and invented open questions.
Independent accuracy rates for causal, modality, scope, authority and paraphrase
fidelity remain NOT_EVALUATED; do not manufacture separate 100% scores.

Final metadata repair was checked offline against persisted responses and the
original query, without new NVIDIA calls:
`artifacts/phase3c_corrective_final_quote_audit_v2.json`. The earlier audit v1
reconstructed with empty query text and lost a requirement record; it is preserved
as an audit-harness failure, not a model error. v2 corrects that reconstruction.

Synthesis latency N=6 on repaired service pass: median 14,943.69 ms, p95/max
40,219.47 ms. This includes bounded timeouts. Unbounded retries were not used.
Decision: REVISE. Retain deterministic/extractive usefulness and the quotation
boundary; obtain independently reviewed paraphrase-fidelity and response-relevance
labels before relaxing generation.
