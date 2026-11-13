# Scientific retrieval final decision

Implemented and validated dependency-ready corrections; independent scientific relevance remains unadjudicated. Source-backed publication is deliberately limited to verified run/sample identities and corroborated source quantities. No Phase 4 work began.

```text
QUERY_INTENT_CORRECTION = ADOPT
CONCEPTUAL_QUERY_HANDLING = KEEP_EXPERIMENTAL
RELATED_SELECTION = KEEP_EXPERIMENTAL
EPISTEMIC_CLASSIFICATION = REVIEW_REQUIRED
FLEX_FIELD_SEMANTICS = PARTIALLY_RESOLVED
PSI_DATASET_PUBLICATION = PARTIAL
SOURCE_PROVENANCE = PARTIALLY_VERIFIED
V1_V2_PARITY = PARTIALLY_RESOLVED
NEMOTRON_INCREMENTAL_VALUE = INCONCLUSIVE
JEV_INCREMENTAL_VALUE = INCONCLUSIVE
INDEPENDENT_SCIENTIFIC_RELEVANCE = REVIEW_REQUIRED
V2_DEFAULT_PATH = KEEP_EXPERIMENTAL
READY_FOR_PHASE_4 = NO
```

Quality: 170 tests; ruff format/check, canonical/native/literal SHACL, registered ontology relations, SQLite and manual reference integrity, FTS completeness, evidence resolution and secret exclusion pass. 746 immutable historical digests are unchanged, including 22 gold files and 399 historical artifacts. Row/cell checks and scientific-source identity suites are executed, not inferred from SHACL.

Remaining blockers: independently judge RELATED usefulness/contamination and epistemic labels; strengthen broad conceptual ontology relationship answers; review five operational mappings; validate unresolved structured PSI numeric roles and run identities; verify older provenance beyond the scoped tables; retain explicit V1 historical limitations. A larger candidate set, derived-value accessibility, more run identities and passing engineering tests do not establish scientist-approved answer quality. Independent scientific precision, recall, nDCG, response usefulness and attribution accuracy are NOT MEASURABLE with zero expert labels.
