# Phase 3 query-interpreter evaluation

The implementation provides deterministic regression tests for canonical precedence, safe aliases, ambiguous terms, unknown terms, and numeric parsing. Live NVIDIA execution used `nvidia/nemotron-3.5-lightning-30b-a3b`: 50 requests, 33 schema-valid proposals, 17 `ProviderFailure` schema failures (invalid-output and fallback rate `.3400`), median latency 4171.9 ms, max 15833.8 ms.

The frozen case file contains only IDs, query text, and category tags, not reviewed expected intent fields. That is an evaluation-data defect, so full exact match, field P/R/F1, entity, numeric, comparison, ambiguity, and clarification correctness are intentionally unreported. No expected labels were altered after live predictions.

Candidate-gold preparation is complete in `evals/phase3_query_interpreter_gold_candidate.json`; 26/50 cases are rule-derived `AUTO_HIGH_CONFIDENCE`, while 24 require review. The final live benchmark has not been run after this preparation.
