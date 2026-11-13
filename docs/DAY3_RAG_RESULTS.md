# Day-3 offline ontology-grounded retrieval results

## Executed pipeline

The offline pipeline is: deterministic query parser → validated `QueryIntent` → graph/run matching → eligible evidence IDs → SQLite FTS5 constrained retrieval → `EvidenceBundle` → extractive renderer. No LLM, API key, embeddings, or generated scientific conclusion is used.

## End-to-end examples

1. **PMMA suppression in microgravity** parsed PMMA and microgravity, then returned the direct documentary intervention, observation, NASA conclusion, safety implication, and the explicitly indexed open question. It did not assert a Saffire-IV run identifier or causal mechanism.
2. **Compare SAFFIRE-I runs** parsed as `compare` with investigation `psi-98`, returned direct S1/S2 rows, and restricted sources to their PSI experimental-table evidence IDs.
3. **SIBAL Fabric microgravity airflow <= 0.10 m/s** parsed the numeric constraint, returned no direct run, returned S1/S2 as related with their matching material/gravity and differing 0.20 m/s flow, and created no open question.

## Measurements

- Direct/related/no-direct behavior: covered by end-to-end tests.
- Citation/evidence coverage: every bundle domain record carries evidence references; renderer prints each evidence ID.
- Retrieval Recall@k for the exercised Saffire comparison: 2/2 eligible experimental-table rows returned.
- Unsupported rendered claims: 0; renderer only emits stored normalized text, record IDs, matching differences, and registry passages.
- Existing lightweight evaluation: 15 questions, FTS non-empty for 14, expected source coverage for 4 (the prior corpus-level harness; no LLM evaluation is performed).
- Canonical entities/RDF triples: 48 / 349.
- SHACL: conformant.
- Pytest: 23 passed.

## Current corpus coverage and limits

Parser coverage is intentionally restricted to PMMA, SIBAL Fabric, Saffire, BASS-II, microgravity, airflow units, and safety keywords. Unknown terms fall back to `general_search`; they are not mapped to ontology entities. Graph-constrained retrieval can fall back to eligible evidence passages when their terse CSV rows do not contain the user’s investigation label. The renderer is extractive and does not provide a generative scientific summary.

## Next step

Add expert-reviewed aliases and gold retrieval expectations for additional already-ingested concepts before considering grounded generative synthesis.
