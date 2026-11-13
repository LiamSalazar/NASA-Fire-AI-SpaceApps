# Phase 3C controlled A/B/C/D results

## Candidate discovery and objective identity recovery

The live Nemotron run completed the frozen 20 cases. On the eight positive objective identity cases, every configuration recovered the expected ID in **7/8** at @1, @3, @5 and @10 (0.875; Wilson 95% interval approximately 0.529–0.978; `SMALL_N`). Identity MRR@10 was 0.875. A had 3.4 mean candidate IDs, the deterministic top-20 control had 18.7, and B/C/D had 19.4. The 14 additional unique candidates over the budget-matched lexical pool did not recover the missed expected ID. Eight other cases remain review-required and are not scored.

For the four corpus-scoped no-direct cases, the native path produced **0/4 DIRECT**. This checks the invariant, not model truth or the absence of NASA knowledge. Model proposals never modify canonical DIRECT/RELATED.

## Expansion and reranking

Expansion accepted 7 and rejected 47 model formulations, with one timeout. Reranking’s initial large request timed out in 15 cases and failed schema validation in one; the final compact pass returned usable judgments for 14/18 requests, with four failed calls and two no-candidate cases. Across the successful judgments, 24 positive-relevance proposals had exact in-passage spans; eight invalid proposals were rejected. These are proposal-integrity counts, not relevance accuracy.

On the objective identity denominator, C and D did not improve recall. Jev ran 25 advisory classifications with response model `jev-1.13.0` under alias `jev-latest`; D changed candidate order in two cases but there is no independent relevance label to determine whether either change helped. Model/API costs were not provided by the APIs.

## Latency

Expansion: 19 usage-bearing responses, median 2.335 s, p95/max 31.974 s; one request timed out. Compact reranking: 14 usage-bearing responses, median 14.145 s, p95/max 28.129 s; 18 requests total, four failures and two non-applicable empty cases. The previous rerank pass remains separately recorded: 15 timeouts, one validation error, and two successful results. These service costs preclude default enablement.

Machine-readable A/B/C/D evidence: `artifacts/phase3c_controlled_ablation_analysis_v1.json`; case rows: `artifacts/phase3c_controlled_e2e_ablation_cases_v1.jsonl` and `...cases_v4.jsonl`; API receipts: `artifacts/phase3c_controlled_e2e_api_calls_v1.jsonl` and `...api_calls_v4.jsonl`. Review packet v2 contains 224 candidate rows across 11 cases; reviewer fields remain blank.
