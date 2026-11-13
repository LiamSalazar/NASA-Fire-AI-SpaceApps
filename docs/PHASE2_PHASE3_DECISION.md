# Phase 2 → Phase 3 decision

## Final retrieval architecture

The evidence supports the simplest safe default:

```text
query → deterministic QueryIntent → controlled lexicon + ontology
      → deterministic DIRECT / RELATED matcher
      → Graph-eligible evidence when constraints exist
      → BM25 ranking → provenance-backed EvidenceBundle
```

General documentary search remains BM25. Graph-constrained vector/RRF is retained as an optional evaluation capability only; its perfect result used three cases and an average eligible universe of two passages, so it is insufficient to justify default semantic ranking. Vector rescue is disabled: its oracle analysis recovered 2/4 BM25 misses at top-10 but supplied no deployable failure trigger. Discovery vector/RRF is disabled because BM25 was stronger on the 15-query source-backed Discovery gold.

Retrieval-Augmented Generation does not require vector search. KG + BM25 is a valid retrieval layer for the future grounded generation phase.

## Per-role decisions

| Capability | Method | Decision | Evidence |
|---|---|---|---|
| DIRECT | deterministic canonical constraints | KEEP | Supported-case correctness 1.0000; vectors never enter the decision. |
| RELATED | explicit structured overlap/difference | KEEP | Supported-case correctness 1.0000. |
| General documentary retrieval | BM25 | KEEP | It exceeds global vector and global RRF. |
| Global vector retrieval | embeddings | REJECT | R@1 .4500, MRR .5832 vs BM25 .6250/.7226. |
| Global RRF | BM25 + vector | REJECT | R@1 .5750, MRR .6907; no improvement over BM25. |
| Graph-constrained vector | embeddings | LIMITED | 3-case result is favorable but too small for a default. |
| Graph-constrained RRF | fusion | LIMITED | Same limitation; no new scientific eligibility. |
| BM25 rescue | vector fallback | REJECT | Oracle recovery 2/4 at top-10; no safe trigger. |
| Canonical identity | controlled lexicon + ontology | KEEP | Embeddings remain candidates only. |
| Semantic concept candidates | vector index | KEEP_LIMITED | Useful as review-only candidates; index coverage is 4/12 expected concepts. |
| Discovery vector | vector/RRF | REJECT | BM25 dominates the source-backed Discovery benchmark. |

## Phase-3 input contract

The future QueryInterpreter and grounded synthesizer may receive `QueryIntent`, DIRECT evidence, RELATED evidence, safety knowledge, open questions, sources, and coverage notes. Optional Discovery is disabled by default. A future LLM may not change DIRECT/RELATED status, authority, scope, uncertainty, causality, source evidence, or semantic identity.

`READY_FOR_PHASE_3 = YES`

All required Phase-2 role experiments are complete. The decision does not require vector adoption; it requires that vectors have been evaluated without weakening provenance or scientific semantics.
