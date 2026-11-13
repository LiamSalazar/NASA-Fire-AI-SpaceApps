# Phase 2 vector rescue evaluation

The frozen global evaluation had four BM25 top-10 misses: `doc-07`, `doc-17`, `doc-20`, and `safety-38`. This is an **oracle** analysis: it assumes gold reveals that BM25 missed. It is not a deployable miss detector.

| Vector rescue of BM25 misses | @1 | @3 | @5 | @10 |
|---|---:|---:|---:|---:|
| Recovered cases (n=4) | 1 | 2 | 2 | 2 |
| Rescue recall | 0.2500 | 0.5000 | 0.5000 | 0.5000 |

No deterministic, gold-independent trigger was demonstrated that reliably identifies those misses, and vector search would unnecessarily introduce candidates on BM25 successes. **Decision: `VECTOR_RESCUE = REJECT` for operation.** The result remains useful research evidence; the implementation stays optional and disabled.
