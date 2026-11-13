# Phase 3C knowledge completeness decision

- `ONTOLOGY_COVERAGE_DECISION = PARTIAL`
- `CORPUS_COVERAGE_DECISION = PARTIAL`
- `SCIENTIFIC_EXTRACTION_DECISION = KEEP_EXPERIMENTAL`
- `ENTITY_NORMALIZATION_DECISION = ADOPT`
- `GRAPH_PROJECTION_DECISION = ADOPT`
- `GRAPH_SEMANTIC_RETRIEVAL_DECISION = KEEP_EXPERIMENTAL`
- `V1_V2_PARITY_DECISION = PARTIALLY_RESOLVED`
- `NEMOTRON_LIVE_EVALUATION = PASS`
- `JEV_LIVE_EVALUATION = PASS`
- `SCIENTIFIC_RELEVANCE_DECISION = REVIEW_REQUIRED`
- `V2_DEFAULT_PATH_DECISION = KEEP_EXPERIMENTAL`
- `READY_FOR_PHASE_4 = NO`

Adoption applies to source-preserving normalization and explicit-foreign-key projection, not blanket enablement of experimental reasoning. Ontology lacks declarations/constraints and reviewed evidential semantics; corpus discovery is bounded and only eight runtime sources contain canonical records. Independent scientists must adjudicate nomenclature, taxonomy, evidence applicability and missing relation semantics. Remaining engineering: exhaustive scoped source inventory, expanded extraction coverage and a separate validated-native-intent parity campaign. Phase 4 has not begun.

Final checks: 136 pytest tests passed; Ruff format/check passed; final dynamic suites 230/230 and 125/125. Twenty scientific regressions recovered 8/8 required identities with 0/4 incorrect DIRECT promotions. All 630 frozen raw/canonical/gold/historical artifact digests remained unchanged. Active projection is graph v2; first-pass graphs are retained and superseded.
