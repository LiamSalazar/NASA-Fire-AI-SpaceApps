# Phase 2 hybrid retrieval results

Deterministic RRF retaining BM25/vector ranks produced Recall@1/3/5/10 = 0.5750/0.7500/0.8250/0.9000 and MRR 0.6907. It recovered vector recall but did not beat BM25 at any cutoff or MRR. Hybrid ranking remains provenance-preserving and does not participate in DIRECT or RELATED classification; it is not the default.
