# Phase 3C gold reconciliation review

The immutable interpreter receipt file `artifacts/phase3c_final_repair_interpreter_cases_v6.jsonl` was compared field-by-field against its expected `requested_information`. The recomputed discrepancy count is **16**. The proposal file under `docs/documents3cPropose/` informed this review but was not accepted as scientific gold.

| Cases | Count | Proposed disposition | Status |
|---|---:|---|---|
| qi05, qi06, qi07, qi08, qi12, qi13, qi25, qi50 | 8 | `ExperimentalRun` is represented as a target, not necessarily an epistemic information class | `STRUCTURAL_CONTRACT_CORRECTION_PROPOSED` |
| qi14, qi16, qi17, qi18, qi31, qi32, qi33 | 7 | Determine whether the wording explicitly requests an observation, requirement, guidance, open question, conclusion, implication, or broader report | `SEMANTIC_REVIEW_REQUIRED` |
| qi27 | 1 | “What has NASA reported…” does not by itself choose a single epistemic class | `UNRESOLVED` |

The machine-readable record is `artifacts/phase3c_controlled_gold_reconciliation_proposed_v1.json`. Each row retains the question, original gold, current model intent, proposed fields and rationale. It records `historical_gold_modified=false`, `expert_reviewed=false`; no proposal is treated as approved. No revised exact-match metric is reported. In particular, “suppression” or a safety-related topic is not itself a request for `SafetyImplication`.

**Decision:** `GOLD_RECONCILIATION_DECISION = REVIEW_REQUIRED`. Structural proposals can be considered after the contract owner approves them; epistemic class choices need independent domain review. The frozen gold and historical results remain unchanged.
