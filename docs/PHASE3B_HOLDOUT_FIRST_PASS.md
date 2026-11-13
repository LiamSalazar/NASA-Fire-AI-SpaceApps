# Phase 3B blind holdout first pass

The corrected v2 manifest was frozen before content access. This first pass used the
generic PSI table reader/profiler and generic PDF segmentation only; no holdout-specific
scientific mapping was introduced.

| Holdout | Acquisition | Artifact result | Canonical mappings | Staged mappings | Canonical publication |
| --- | --- | --- | ---: | ---: | --- |
| PSI-142 | success | one table, 8 rows, 4 columns | 0 | 4 | none |
| NTRS 20250001364 | success | one-page documentary PDF, 2,359 extracted characters | 0 | 0 | none |

The PSI table's four columns were typed and placed in persistent semantic staging as
`UNKNOWN`; their source, column location, datatype, and generic-profiler provenance are
retained. No unsupported nearest-property assignment occurred. The documentary artifact
was acquired in temporary storage and text-extracted for measurement; it was not
inserted into the frozen baseline corpus/FTS registry, so the baseline scientific state
remains unchanged.

`artifacts/phase3b_holdout_first_pass.json` is the immutable first-pass measurement.
