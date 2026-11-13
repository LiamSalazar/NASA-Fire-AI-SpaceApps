# Relational Related Semantics

This is an additive Phase 3C engineering iteration. NASA raw/canonical inputs, historical gold and historical benchmark artifacts are preserved. No independent scientific adjudication is claimed. Experimental features remain default-off. QueryIntentV2 is retained; no Phase 4 work is started.

`query/native.py` preserves the exact default and adds structured multidimensional explanations. Each requested relation/property receives MATCH, DIFFER or UNKNOWN, requested and actual values, original units, qualifiers, source IDs, and any approved taxonomy path. Invalid values remain explicit and cannot establish a match. Missing source fields are UNKNOWN. Reported/design conditions keep their original context; they do not become observed measurements.

DIRECT requires every mandatory constraint and an unblocked original intent. A category descendant can satisfy only its category dimension; a sibling cannot satisfy an exact material identity. RELATED needs verified overlap or a scoped reviewed path. The experimental declarative anchor policy in `domain/semantic_registry.yaml` prevents gravity alone from admitting a contradictory requested material/phenomenon. No experiment/material names appear in production branching.

Presentation rank is separate from eligibility. The configurable policy weights material/phenomenon, gravity, numerical conditions and missing data. Every dimension records its contribution. Current coefficients are engineering proposals, not scientifically adjudicated universal priorities. Path distance alone does not determine usefulness. Review is required before adopting a domain ranking policy.

The response shows actual concepts, conditions, differences, missing information, taxonomy citations and experiment citations. Source-backed individual results cannot support uniform family behavior; related material findings cannot be transferred. Unresolvable experimental evidence and source-restriction violations are excluded from experimental expansion.

The condition example requests SIBAL at 30 cm/s; PSI-98 S1/S2 report 20 cm/s. Material and microgravity MATCH, airflow DIFFER, with the context retained as reported condition. Evidence IDs are `E-psi-98-table-S1` and `E-psi-98-table-S2`; neither establishes 30 cm/s. The synthetic MaterialA1 query similarly distinguishes its 0.1 m/s design target from the requested 0.2 m/s and missing values on another fixture.

See `artifacts/phase3c_related_constraint_differences_v1.json` and `phase3c_related_scientific_examples_v2.json`.
