# Phase 1.5 pre-vector retrieval baseline

Executed against the frozen gold with the current FTS5/BM25 and deterministic QueryIntent/graph path:

| Baseline | Questions | Recall@1 | Recall@3 | Recall@5 | Recall@10 | MRR |
|---|---:|---:|---:|---:|---:|---:|
| FTS/BM25 source retrieval | 40 | 0.6250 | 0.8500 | 0.8500 | 0.9000 | 0.7226 |

Documentary-only results were Recall@1 0.6286, Recall@3/5 0.8571, Recall@10 0.9143, MRR 0.7306 (35 questions). Safety/documentary results were 0.6000/0.8000/0.8000/0.8000 and MRR 0.6667 (5 questions). No lexical query returned an empty result.

The deterministic structured baseline covered 10 supported cases: overall status correctness 0.8000; DIRECT 1.0000 (2/2); RELATED 1.0000 (2/2); abstention 0.6667 (4/6); and returned-evidence resolution 0.5833. The latter exposes existing product-path limitations (safety context can appear as direct documentary context for a material word); it was measured, not weakened or relabeled. DIRECT semantics remain canonical identity plus satisfied structured constraints.
