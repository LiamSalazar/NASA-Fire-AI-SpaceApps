# Phase 3C controlled reasoning error analysis

This analysis distinguishes observed mechanics from unreviewed scientific judgments. Eight cases in the regression remain `REVIEW_REQUIRED`; no model-generated label is presented as expert truth.

| Case | Observed result | Error/risk classification |
|---|---|---|
| qi24 “Show PMMA tests” | Native A includes `E-382165f1a4516fa8` at rank 1. The compact contextual model moved it to rank 3; it remains in the top 3. | Ranking changed in an unreviewed case; relevance cannot be inferred from the ID alone. |
| qi27 “What has NASA reported…” | A is empty; original BM25 plus expansions did not retrieve `E-382165f1a4516fa8`. All three model formulations were rejected for added registered concepts; the v4 reranker call returned invalid JSON. Resolved intent has no requested-information class for broad “reported”. | Requested-information/terminology gap plus candidate-generation miss; not evidence that the document is irrelevant or that NASA has no direct source. |
| comp01 / comp11 | Native structured tables and documentary candidates are present; comp11’s final reranker schema validation failed. | Numeric/source relevance remains review-required; do not label prior audit distractors scientifically irrelevant without review. |
| qi12 S1/S2 | Both PSI-98 table IDs are native DIRECT candidates. The deterministic renderer now shows shared airflow, differing oxygen concentration and flow direction, unavailable pressure, and both source row IDs. | Useful structured comparison; no significance or causal inference is made. |
| qi18 open questions | The source-backed statement “Additional focused tests may be required…” is retrieved. | Whether a methodological need is a formally NASA-identified open question requires review; the renderer does not independently reclassify it. |
| qi42 PMMA and SIBAL | The generic resolver detects more than one value in the `hasMaterial` relation slot and requests clarification. Native output has no direct evidence or speculative candidates. | Correct abstention because QueryIntentV2 has no disjunction/union operator; no false conjunctive run is asserted. |

Additional safety tests ensure that expansion anchors retain values, units, negation and source IDs; evidence IDs remain whitelisted; positive rerank labels require verbatim spans; unresolved grouping suppresses speculative discovery; and citation page numbers are not overstated. An unknown source or absent canonical direct match is never described as a research gap.

The full exact text, source records, rankings, expansions, model proposals, deterministic validation and blank reviewer fields are in `artifacts/phase3c_controlled_case_diagnostics_v1.json` and `artifacts/phase3c_controlled_scientific_relevance_review_packet_v2.json`.
