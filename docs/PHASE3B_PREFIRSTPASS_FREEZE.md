# Phase 3B pre-first-pass freeze

The generic implementation was frozen before opening the corrected holdout bodies or
tables. `artifacts/phase3b_prefirstpass_freeze.json` records the holdout-manifest and
implementation digests. The freeze includes the registry-driven QueryIntentV2 planner,
generic constraint evaluator and DIRECT/RELATED classifier, generic column profiler and
resolver, persistent staging storage, generic value/measurement form, and generic SHACL
shapes. The targeted pre-freeze suite passed (8 tests). Any later change must be logged
as post-holdout work and may not rewrite the blind first-pass result.
