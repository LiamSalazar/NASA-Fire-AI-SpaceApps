# Phase 3 query-interpreter error analysis

No live interpreter predictions exist to classify. The frozen error taxonomy is: `ENTITY_MISRESOLUTION`, `SAFE_ALIAS_MISS`, `AMBIGUITY_NOT_PRESERVED`, `WRONG_FIELD`, `WRONG_QUERY_MODE`, `NUMERIC_PARSE_MISS`, `COMPARISON_MISS`, `OVERINTERPRETATION`, `UNDERINTERPRETATION`, `UNKNOWN_TERM_FORCED`, `CONTEXT_REFERENCE_ERROR`, `SCHEMA_ERROR`, and `OTHER`.

Current deterministic regression coverage specifically protects ambiguity preservation for acrylic and velocity/flow, unknown-term abstention, canonical-label precedence, and unit validation.
