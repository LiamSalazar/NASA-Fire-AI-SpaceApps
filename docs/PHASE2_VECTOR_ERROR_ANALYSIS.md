# Phase 2 vector error analysis

The error taxonomy is `SEMANTIC_OVERGENERALIZATION`, `CONFUSABLE_PROPERTY`, `WRONG_MATERIAL`, `WRONG_PHENOMENON`, `WRONG_SOURCE_CONTEXT`, `DOCUMENTARY_TOPIC_MATCH_ONLY`, `MISSING_CANONICAL_CONTEXT`, `RANKING_FAILURE`, and `AMBIGUOUS_QUERY`.

Closure examples:

- `flame-spread velocity` ranked `flow:airflow_velocity` first when the expected flame-spread concept was absent from the controlled index: **CONFUSABLE_PROPERTY**.
- Eight of twelve unambiguous semantic cases were **GOLD_CONCEPT_NOT_IN_CONTROLLED_INDEX**, so the headline 0.3333 score is primarily coverage-limited.
- Oracle vector rescue recovered only 2/4 BM25 misses at top-10: **RANKING_FAILURE / limited rescue value**.
- Discovery vector/RRF underperformed BM25 and can retrieve topic context rather than the reviewed NASA source: **DOCUMENTARY_TOPIC_MATCH_ONLY**.

No score is interpreted as scientific confidence. Similarity remains a retrieval score only.

The mandatory confusable checks remain airflow versus flame-spread velocity, extinction versus suppression, suppression versus quenching, burning rate versus flame-spread rate, and oxygen concentration versus oxygen partial pressure.
