# Phase 1.5 frozen retrieval gold

`evals/phase1_5_retrieval_gold.json` is frozen at version `phase1.5-frozen-2026-10-04` and contains 50 source-backed questions: 35 documentary-title lookups across imported NTRS topic families, five safety/documentary queries, eight deterministic structured queries, and two abstention/confusable-term queries.

Each lexical item supplies expected source IDs; structured items supply expected `DIRECT`, `RELATED`, or `NO_DIRECT_EVIDENCE` status. The 30-case epistemic set is separately frozen in `evals/phase1_5_epistemic_gold.json`: nine existing curated/reviewed positives, 20 human-audited rejected rhetorical candidates, and one policy-reviewed title-only negative. No case was created from model output or benchmark results.
