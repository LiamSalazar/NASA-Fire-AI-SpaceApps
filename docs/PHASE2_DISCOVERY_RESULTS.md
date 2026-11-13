# Phase 2 Discovery evaluation

Discovery is a `SYSTEM_SUGGESTED` relationship to an official NASA passage, not a NASA claim and not DIRECT or RELATED evidence. A source-backed 15-query Discovery set was frozen from documentary questions in the existing retrieval gold. Every item records target source/evidence IDs, why it may be useful, and why it has no deterministic DIRECT or RELATED relation. Direct and Related IDs were excluded before ranking.

| Discovery method | n | R@1 | R@3 | R@5 | R@10 | MRR | P@1 | P@3 | P@5 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| BM25 | 15 | 0.8000 | 0.9333 | 0.9333 | 0.9333 | 0.8556 | 0.8000 | 0.5333 | 0.4000 |
| Vector | 15 | 0.4667 | 0.6667 | 0.6667 | 0.8000 | 0.5873 | 0.4667 | 0.4222 | 0.3467 |
| RRF | 15 | 0.6667 | 0.7333 | 0.8667 | 0.9333 | 0.7429 | 0.6667 | 0.4889 | 0.4267 |

Direct duplicate rate and Related duplicate rate were both 0.0 because those evidence IDs were excluded. Provenance coverage was 1.0 and the deterministic reason template had zero unsupported scientific-inference reasons. Vector and RRF did not beat BM25 for this gold; vector also showed the expected topic-neighbor false-discovery risk.

**Decision: `DISCOVERY_VECTOR = REJECT`.** The typed `DiscoveryCandidate` model remains available for controlled future research, but Discovery is disabled from the default Phase-3 EvidenceBundle. A future review may separately evaluate BM25-only documentary exploration; it must retain the same `SYSTEM_SUGGESTED` authority and exclusion rules.
