# Phase 2 retrieval comparison

| Context | Method | Denominator | R@1 | R@3 | R@5 | R@10 | MRR | Outcome |
|---|---|---:|---:|---:|---:|---:|---:|---|
| Global documentary | BM25 | 40 | .6250 | .8500 | .8500 | .9000 | .7226 | Keep |
| Global documentary | Vector | 40 | .4500 | .7000 | .7250 | .8000 | .5832 | Reject |
| Global documentary | RRF | 40 | .5750 | .7500 | .8250 | .9000 | .6907 | Reject |
| Graph constrained | Graph→BM25 | 3 | .6667 | .6667 | .6667 | .6667 | .6667 | Baseline |
| Graph constrained | Graph→Vector | 3 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | Limited only |
| Graph constrained | Graph→RRF | 3 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | Limited only |
| Discovery | BM25 | 15 | .8000 | .9333 | .9333 | .9333 | .8556 | Strongest |
| Discovery | Vector | 15 | .4667 | .6667 | .6667 | .8000 | .5873 | Reject |
| Discovery | RRF | 15 | .6667 | .7333 | .8667 | .9333 | .7429 | Reject |

BM25 wins on exact report/document wording, source-title queries, and the source-backed Discovery set. Vector helps a constrained title-vs-table lexical mismatch, but the graph already establishes the scientifically eligible universe and retains the table evidence deterministically. Hybrid never surpasses BM25 on the meaningful global or Discovery denominators.

Vector does not establish scientific identity: the semantic seed's flame-spread query ranked airflow velocity first when the expected concept was absent from the controlled index. The default retrieval architecture is therefore deterministic graph constraints plus BM25, with vectors optional and disabled.
