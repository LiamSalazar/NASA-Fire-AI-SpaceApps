# Phase 3 end-to-end error analysis

No live LLM end-to-end benchmark ran, so no success rate or error counts are claimed. The implemented trace separates: `QUERY_INTERPRETATION`, `ENTITY_RESOLUTION`, `AMBIGUITY`, `NUMERIC_INTERPRETATION`, `RETRIEVAL`, `RANKING`, `EVIDENCE_BUNDLE`, `SYNTHESIS_OMISSION`, `UNSUPPORTED_CLAIM`, `CITATION_ERROR`, `EPISTEMIC_TRANSFORMATION`, `MODALITY_ERROR`, `NEGATION_ERROR`, `SCOPE_ERROR`, `CAUSALITY_ERROR`, `CONVERSATION_REFERENCE`, `FALLBACK_FAILURE`, and `OTHER`.

The tested offline path returns deterministic/extractive output if either LLM stage is unavailable.
