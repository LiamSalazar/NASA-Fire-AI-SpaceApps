# Phase 3B generalization results

## Baseline and freeze

The frozen baseline remained 286 documents, 6,055 FTS passages, 3,831 canonical
entities, and 24,014 RDF triples. The original FLEX/PSI-99 selection was invalidated
as previously exposed. The corrected metadata-only manifest digest is
`799d9b377ceae900a362577ced1a44d9b4f90ccc72dd2cf8978de29fd97edbb5` and the
pre-first-pass implementation freeze is recorded in
`artifacts/phase3b_prefirstpass_freeze.json`.

## Blind first pass and staging

PSI-142 was acquired through the generic PSI path and profiled as one table with eight
rows and four columns. All four unrecognized column semantics were stored as persistent
`UNKNOWN` staging candidates; none was canonized. NTRS 20250001364 was acquired through
the generic document path and text-extracted. Neither source was published to the frozen
baseline corpus. The immutable record is `artifacts/phase3b_holdout_first_pass.json`.

| Metric | Result |
| --- | ---: |
| ZERO_CODE_INGESTION_RATE | 2/2 = 1.0000 |
| ZERO_CODE_STRUCTURED_EXTRACTION_RATE | 1/1 = 1.0000 |
| ZERO_CODE_SEMANTIC_MAPPING_RATE | N/A (0 eligible pre-existing canonical fields) |
| SAFE_NEW_CONCEPT_HANDLING_RATE | 4/4 = 1.0000 |
| FALSE_CANONICALIZATION_RATE | 0/4 = 0.0000 |
| STAGING_PROVENANCE_COMPLETENESS | 4/4 = 1.0000 |

Post-holdout work added a generic textual-operator bug fix and the generic V2
compatibility execution adapter. No holdout-specific scientific code was added; the
blind first-pass figures above are not retroactively changed.

## Query language and retrieval

The frozen reviewed set has 47 standalone representability cases and three
conversational-only cases. V1 represents 39/47 (0.8298); V2 represents 47/47 (1.0000)
through generic targets, information classes, comparisons, entity constraints and
scalar/range/approximate values. This is schema coverage, not LLM accuracy.

For the 39 scored cases, both paths received the same deterministic V1 parser result.
The V2 compatibility execution path then ran against the actual canonical runs and
Evidence Registry: DIRECT parity = 1.0000, RELATED parity = 1.0000, and eligible
evidence parity = 1.0000. The detailed result is
`artifacts/phase3b_v1_v2_parity.json`.

The isolated holdout evaluation index contains two sources and nine passages. Generic
table/document lookup and numeric-identifier retrieval returned the PSI rows;
documentary lookup returned the NTRS passage; an invented-property query returned no
forced canonical result. See `artifacts/phase3b_holdout_query_probes.json`.

## Quality and decisions

Ruff passed; pytest passed (67 tests); SHACL conforms. The baseline graph and FTS count
were unchanged. Staging is separate from the canonical graph and cannot establish
DIRECT.

- `QUERY_INTENT_V2_DECISION = ADOPT`
- `GENERIC_INGESTION_V2_DECISION = ADOPT`
- `SEMANTIC_STAGING_DECISION = ADOPT`
- `GENERIC_RETRIEVAL_V2_DECISION = REVISE`
- `V2_DEFAULT_PATH_DECISION = KEEP_EXPERIMENTAL`
- `READY_FOR_PHASE_4 = NO`

The conservative no-go is due to the V2 retrieval path still being an additive
compatibility adapter over legacy run fields rather than a complete registry-driven
KG/SPARQL executor. It is not caused by unsafe holdout behavior.
