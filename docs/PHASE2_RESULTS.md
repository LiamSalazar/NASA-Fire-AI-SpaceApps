# Phase 2 results

## Frozen corpus and index

The evaluation began from 286 managed documents, 6,054 canonical passages/FTS rows, 405 experimental runs, approximately 3,831 canonical entities, and approximately 24,014 RDF triples. A final provenance repair registered the already-referenced official PSI-98 S2 raw-table row, yielding 6,055 canonical passages/FTS rows without changing scientific content. NVIDIA `nvidia/nemotron-3-embed-1b` supplied 2,048-dimensional vectors for 6,055 passages and 10 approved controlled concepts. The one repaired passage required one new embedding; the immediate repeat synchronization made zero new passage embedding calls. No raw source, canonical scientific record, RDF triple, or controlled alias was modified by an embedding benchmark.

## Global documentary retrieval (40 source-backed queries)

| Method | R@1 | R@3 | R@5 | R@10 | MRR |
|---|---:|---:|---:|---:|---:|
| BM25 | 0.6250 | 0.8500 | 0.8500 | 0.9000 | 0.7226 |
| Vector | 0.4500 | 0.7000 | 0.7250 | 0.8000 | 0.5832 |
| RRF | 0.5750 | 0.7500 | 0.8250 | 0.9000 | 0.6907 |

`GLOBAL_VECTOR_RETRIEVAL = REJECT`; `GLOBAL_HYBRID_RRF = REJECT`.

## Closure experiments

- Graph-constrained ranking: 3 source-backed cases, zero gold removals by graph eligibility, Graph→Vector and Graph→RRF R@1/MRR 1.0000 versus Graph→BM25 .6667/.6667. The denominator and two-passage eligible universe make this a limited result, not default evidence.
- Vector rescue: 4 BM25 top-10 misses; oracle vectors recovered 1 at @1 and 2 at @3/@5/@10. No deployable trigger was demonstrated.
- Semantic resolution: end-to-end Top-1/3/5 .3333; controlled-index coverage 4/12; coverage-conditioned Top-1/3/5 1.0000. The central limitation is concept/index coverage and confusable terminology, not a license to auto-create vocabulary.
- Discovery: a 15-query source-backed gold found BM25 (R@1 .8000, MRR .8556) stronger than vector (.4667/.5873) and RRF (.6667/.7429). All returned candidates remained provenance-resolved and system-suggested; DIRECT/RELATED duplicates were excluded.

## Safety and integrity

DIRECT supported-case correctness remains 1.0000. RELATED supported-case correctness remains 1.0000. A safety-context convenience path that had incorrectly placed interventions in DIRECT was removed; documentary interventions remain evidence-backed but cannot manufacture a structured DIRECT result. The frozen evaluator now reports `NO_DIRECT_EVIDENCE` correctly for the PMMA suppression/open-question case; `PMMA microgravity` remains RELATED because it has explicit shared microgravity and no direct PMMA match. This is an evaluation taxonomy distinction, not semantic inference.

The final default remains deterministic graph constraints plus BM25. Vector infrastructure remains reproducible and disabled by default. Final checks: SHACL conforms, 47 tests pass, and Ruff is clean. See [the final closure](PHASE2_FINAL_CLOSURE.md) and [the Phase-3 decision](PHASE2_PHASE3_DECISION.md).
