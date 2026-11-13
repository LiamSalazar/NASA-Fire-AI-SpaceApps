# Phase 3B generalized architecture

`QueryIntentV2` is additive and experimental. It represents small generic operations, ontology-class targets, entity constraints, typed property constraints, requested information classes, comparisons, and unresolved mentions. V1 remains the production/retrieval baseline.

Property identity and dimensional compatibility are validated by `SemanticRegistry`, not by a growing Pydantic field list. New concepts stay staged candidates; they never become canonical or DIRECT evidence automatically. Generic ingestion/profiling and holdout evaluation remain required before V2 can become a default path.
