# Real-context Phase 3C final adoption and readiness

Implemented and operationally exercised the existing experimental native V2 path. Real source contexts are usable without changing canonical run facts; no parallel graph, QueryIntentV3 or Phase 4. Partial decisions reflect bounded curator-prepared extraction, model schema failures/no incremental discoveries, unverified conclusion joins and absent independent review—not a missing engineering integration.

```text
MICROGRAVITY_DEFAULT_POLICY = ADOPT
REAL_SOURCE_CONTEXT_EXTRACTION = PARTIAL
BASS_II_CONTEXT_APPLICABILITY = VERIFIED
SAFFIRE_I_CONTEXT_APPLICABILITY = VERIFIED
MIXED_GRAVITY_EXCEPTION_HANDLING = VALIDATED
NON_GRAVITY_CONTEXT_REASONING = PARTIAL
SCIENTIFIC_SCOPE_RESOLUTION = KEEP_EXPERIMENTAL
ONTOLOGY_GRAPH_INTEGRATION = PARTIAL
NEMOTRON_CONTEXTUAL_VALUE = INCONCLUSIVE
JEV_ADVISORY_VALUE = INCONCLUSIVE
END_TO_END_CONTEXTUAL_REASONING = PARTIAL
SCIENTIFIC_ATTRIBUTION = REVIEW_REQUIRED
INDEPENDENT_SCIENTIFIC_RELEVANCE = REVIEW_REQUIRED
V2_DEFAULT_PATH = KEEP_EXPERIMENTAL
READY_FOR_PHASE_4 = NO
```

Source-backed BASS-II and Saffire-I pilot applicability is technically verified, not independently endorsed. Microgravity preference is adopted; source interpretation, scope and graph integration stay flagged experimental. No full automatic corpus-wide adoption. Remaining dependencies: independent scientific relevance/attribution labels; broader run memberships and phenomenon semantics; validated observation-to-conclusion relations; generic source extraction beyond prepared windows; successful useful new model discoveries. Jev remains optional advisory and unmeasured.

Reproduction: `uv run python scripts/phase3c_real_context.py --extract` originally generated versioned extraction trials; use receipts v8 for the final context index, not the historic v1 trial. Final A/B/C/D evaluation invoked `phase3c_real_context.evaluate()` with VERSION v10 and the immutable isolated evidence snapshot. Quality stages: `scripts/phase3c_real_context_quality.py` (commands, integrity, regressions, identities). Outputs are create-only checkpoint receipts; choose a new output version for another run. Production opt-in: NATIVE_V2_QUERY_ENABLED=true and SCIENTIFIC_CONTEXT_RESOLUTION_ENABLED=true; default preference is already true, API call budget defaults zero. Disable NATIVE_V2_QUERY_ENABLED for V1 rollback.

## Engineering handoff

Modified: `domain/query_language_v2.yaml`, `domain/semantic_registry.yaml`, `ontology/semantic_shapes.ttl`; ingestion `semantic.py`; query `native.py`, `native_interpreter.py`, `hierarchy.py`, `ontology_navigation.py`, `v2_execution.py`; services `native.py`, `phase3.py`. Extended context foundations in `context.py` and `llm/context.py`; added `ingestion/contextual.py`, `query/contextual.py`, real-source end-to-end tests and three versioned campaign/quality/report scripts. Existing QueryIntentV2, SemanticRegistry, source registry/FTS, native graph executor, NVIDIA adapter and V1 rollback are reused. The operational context index is `data/index/scientific_context_v2.json`; canonical files remain unchanged.

Six final actual `Phase3AssistantService.answer_query` calls also completed against a fresh projection from the active registry, with no injected store and zero query-time live API calls. Every request invoked context resolution and retained resolvable citations. The complete production service receipt is `artifacts/phase3c_real_context_production_service_v14.json`.

Artifact index: `artifacts/phase3c_real_context_artifact_index_v13.json`. Five-plus complete real-source answer examples are in `docs/PHASE3C_REAL_CONTEXT_ANSWERS_V1.md`; enriched source metadata is in `artifacts/phase3c_real_context_representative_traces_v12.json`. Independent reviewer fields are blank. Phase 4 readiness: NO.
