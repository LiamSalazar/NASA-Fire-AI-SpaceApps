# Phase 3C controlled reasoning final decision

## Decisions

- `GOLD_RECONCILIATION_DECISION = REVIEW_REQUIRED`
- `NEMOTRON_QUERY_EXPANSION_DECISION = KEEP_EXPERIMENTAL`
- `NEMOTRON_CONTEXTUAL_RERANKING_DECISION = KEEP_EXPERIMENTAL`
- `JEV_ADVISORY_DECISION = KEEP_OPTIONAL`
- `SCIENTIFIC_PARAPHRASE_DECISION = KEEP_RESTRICTED`
- `V2_DEFAULT_PATH_DECISION = KEEP_EXPERIMENTAL`
- `READY_FOR_PHASE_4 = NO`

The controlled path preserves native V2 evidence authority and now supports safe candidate-only expansion/reranking, source-span checks, query clarification for unresolved same-relation grouping, clearer comparison presentation, and honest citation-location wording. Yet it did **not** improve exposed objective identity recall (7/8 for all A–D modes), expansion accepted only 7/54 proposals, reranking still failed four calls in the compact pass, and relevance precision cannot be scored. Eight cases still need independent relevance review. Therefore there is no defensible basis to turn controlled discovery on by default or declare the scientist-facing product ready for Phase 4.

The final repository gates for this iteration have now completed: Ruff format and lint pass, pytest is 103/103, canonical and native SHACL conform, SQLite and foreign keys pass, the Evidence Registry has 6,055/6,055 FTS passages with no orphans, the native graph has 20,447 triples with no broken evidence references, and staging provenance is complete for all four rows. Historical evaluation/raw/canonical-data digests remain unchanged. See `artifacts/phase3c_controlled_integrity_v1.json`. These engineering checks do not substitute for independent relevance review.

## Minimum remaining work

1. Have an independent fire-safety/scientific reviewer adjudicate the 16 proposed requested-information differences and the 11-case relevance packet; retain all labels and disagreements with provenance.
2. Re-evaluate the frozen `REVIEW_REQUIRED` cases and qi24/qi27/comp01/comp11 distractors against reviewer labels. Only then calculate precision/recall, no-answer correctness and whether expansion/reranking help.
3. Evaluate the full language-to-answer path on a separately frozen set. The four-case replay is not a new live accuracy result; the existing interpreter benchmark remains imperfect.
4. Obtain a local/source-verifiable page map for NTRS 20040053586 before showing a physical page citation; page 1 remains an unverified extracted-location integer.
5. Continue to keep paraphrase generation disabled until independent fidelity labels support it.

The engineering implementation and reproducible experiment are documented in the companion controlled-reasoning, ablation, provenance and error-analysis reports. No new architecture phase is proposed and Phase 4 has not started.
