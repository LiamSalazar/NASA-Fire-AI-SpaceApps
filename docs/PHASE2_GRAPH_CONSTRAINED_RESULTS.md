# Phase 2 graph-constrained ranking

## Contract

The graph establishes the eligible evidence universe from deterministic `QueryIntent` fields and existing canonical relations before any ranker runs. Vector similarity never creates eligibility and ranking cannot alter DIRECT, RELATED, matches, differs, or ambiguity.

## Executed subset

Three source-backed cases from the frozen structured gold could be ranked against managed passage evidence. The deterministic graph returned two existing Saffire-I evidence references per query, an average and median eligible universe of 2 out of 6,055 passages (99.967% reduction). No gold target was removed by graph filtering. A closure integrity audit restored the pre-existing missing S2 table passage from the immutable official CSV, bringing the managed registry to 6,055 passages and eliminating the canonical-reference gap.

| Method | Denominator | R@1 | R@3 | R@5 | R@10 | MRR |
|---|---:|---:|---:|---:|---:|---:|
| Graph → BM25 | 3 | 0.6667 | 0.6667 | 0.6667 | 0.6667 | 0.6667 |
| Graph → vector | 3 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| Graph → RRF | 3 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |

This small denominator is not proof of generalization. It shows a bounded advantage where title words do not occur in a table passage. The production structured matcher already retains eligible table evidence as deterministic fallback, so no semantic ranker is needed to establish scientific matching.

**Decision:** `GRAPH_CONSTRAINED_VECTOR = LIMITED`; `GRAPH_CONSTRAINED_HYBRID = LIMITED`. Both remain optional evaluation capabilities, not defaults.

Machine-readable output: `data/eda/phase2_closure_evaluation.json` and `evals/phase2_graph_constrained_gold.json`.
