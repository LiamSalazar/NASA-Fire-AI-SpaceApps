# Phase 3B source-coupling audit

## Inventory before generalization

| Component | Classification | Finding |
|---|---|---|
| `ingestion/psi.py` | FORMAT_NECESSARY | PSI API/cache and CSV acquisition. |
| `ingestion/psi_canonical.py` | SEMANTIC_COUPLING | PSI-98/PSI-25 headers and property meaning are encoded in Python. |
| `scripts/phase15_ingest_flex.py` | SEMANTIC_COUPLING | FLEX labels and records are mapped by source-specific script. |
| `ingestion/phase1.py` | GENERIC_ALREADY | Registry/provenance and candidate workflow are format-neutral. |
| `normalization/units.py` | GENERIC_ALREADY | Explicit reusable conversion table. |
| `query/matching.py` | LEGACY_COMPATIBILITY | V1 field-by-field matcher. |
| `query/v2.py` | CAN_GENERALIZE | Additive property-independent constraint representation. |

## Granular count

The former module count obscured mapping density. The baseline has three source-bound
semantic components and 16 meaningful mappings: 12 PSI-98/PSI-25 header/condition or
source-to-concept mappings in `psi_canonical.py`, one FLEX header alias mapping, and
three source-bound canonical-build interpretations. Generic file/API handling is not
included.

| Metric | Before | After |
| --- | ---: | ---: |
| Source-specific semantic components | 3 | 3 legacy components retained |
| Source-specific semantic mappings | 16 | 16 legacy mappings retained |
| Holdout-specific scientific mappings added | 0 | 0 |
| Generic profiler/resolver components | 0 | 2 |
| Property-specific branches in V2 planner/evaluator | n/a | 0 |
| Hardcoded scientific property fields in QueryIntentV2 | n/a | 0 |

The legacy mappings still power the frozen V1 path and have not been misrepresented as
removed. V2's compatibility metadata is an explicit transition layer, not a new
holdout mapping and not a planner branch.
