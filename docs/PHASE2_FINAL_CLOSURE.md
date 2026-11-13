# Phase 2 final closure

## A. Fixed baseline

| Global documentary retrieval (n=40) | R@1 | R@3 | R@5 | R@10 | MRR |
|---|---:|---:|---:|---:|---:|
| BM25 | .6250 | .8500 | .8500 | .9000 | .7226 |
| Vector | .4500 | .7000 | .7250 | .8000 | .5832 |
| RRF | .5750 | .7500 | .8250 | .9000 | .6907 |

Global vectors and global RRF are rejected for default use.

## B. Graph-constrained ranking

Three source-backed structured cases were eligible; average/median eligible universe was 2 of 6,055 passages, with no gold passage removed. Graph→BM25 scored R@1/R@3/R@5/R@10/MRR .6667/.6667/.6667/.6667/.6667. Graph→Vector and Graph→RRF each scored 1.0000 at every cutoff and MRR. The result is limited by the denominator, not a passage gap: the missing pre-existing S2 reference was restored from the immutable official table during closure. It does not justify a default ranker change.

## C. Vector rescue

Of four global BM25 top-10 misses, oracle vector rescue recovered 1 at @1 and 2 at @3/@5/@10. This is insufficient and lacks a gold-independent trigger. It is rejected operationally.

## D. Semantic resolution

End-to-end frozen Top-1/3/5 is .3333/.3333/.3333 for 12 unambiguous cases. Four expected IDs are present in the 10-concept controlled index (33.33% coverage); coverage-conditioned Top-1/3/5 is 1.0000/1.0000/1.0000. Eight outcomes are concept/index coverage gaps rather than ranking mistakes. The flame-spread/airflow confusion confirms why semantic proximity cannot establish scientific identity.

## E. Discovery

The 15-case source-backed Discovery gold excludes DIRECT and RELATED candidates before ranking. BM25: R@1 .8000, R@3/.R@5/R@10 .9333/.9333/.9333, MRR .8556. Vector: .4667/.6667/.6667/.8000, MRR .5873. RRF: .6667/.7333/.8667/.9333, MRR .7429. Precision@1/3/5 was .8000/.5333/.4000 for BM25, .4667/.4222/.3467 vector, and .6667/.4889/.4267 RRF. Duplicate DIRECT/RELATED rate was zero; provenance coverage 1.0; unsupported Discovery reasons zero. Vector Discovery is rejected.

## F. Abstention

The prior status-style abstention score was .6667. Removing a genuine bug that classified safety-context interventions as DIRECT yields .8333. The remaining mismatch is `PMMA microgravity`: expected `NO_DIRECT_EVIDENCE`, actual `RELATED` because shared microgravity is explicitly structured while material differs. It preserves no DIRECT claim. This gold-status policy distinction is retained visibly rather than hidden by vector retrieval.

## G. Final decisions

```text
GLOBAL_VECTOR_RETRIEVAL       = REJECT
GLOBAL_HYBRID_RRF             = REJECT
GRAPH_CONSTRAINED_VECTOR      = LIMITED
GRAPH_CONSTRAINED_HYBRID      = LIMITED
VECTOR_RESCUE                 = REJECT
SEMANTIC_CONCEPT_CANDIDATES   = KEEP_LIMITED
DISCOVERY_VECTOR              = REJECT
```

## H. Default architecture

Structured query: deterministic QueryIntent → controlled lexicon/ontology → DIRECT or RELATED matcher → graph-eligible evidence → BM25 ranking. General documentary query: BM25. Vector indexes are optional/reproducible and disabled operationally. RAG does not require vector retrieval.

## I. Quality gate

Canonical state remains 286 documents, 6,055 canonical passages/FTS rows, 405 runs, approximately 3,831 entities, and approximately 24,014 triples. Every canonical scientific evidence reference now resolves to a managed passage. DIRECT and RELATED supported-case correctness remain 1.0000. Final checks: SHACL conforms; `pytest -q` passed 47 tests; Ruff format and lint passed; logical passage duplicates, FTS orphans, candidate orphans, review orphans, and canonical evidence-reference gaps are all zero.

`READY_FOR_PHASE_3 = YES`
