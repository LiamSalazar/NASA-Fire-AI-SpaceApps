# Exploratory Query Validation

This is an additive Phase 3C engineering iteration. NASA raw/canonical inputs, historical gold and historical benchmark artifacts are preserved. No independent scientific adjudication is claimed. Experimental features remain default-off. QueryIntentV2 is retained; no Phase 4 work is started.

Equivalent reformulations and discovery hypotheses now have separate contracts. Equivalent formulations must preserve registered entities, source restrictions, requested classes, logical grouping, negation and typed quantities. Generic numeric expressions retain comparison operators, values, normalized dimensions, ranges, tolerances and endpoint uncertainty. Natural-language range endpoints with unspecified inclusion remain UNKNOWN at the boundary; explicitly inclusive/exclusive ranges retain that semantics. Existing explicitly structured closed-interval constraints remain backward compatible.

`>= 20 cm/s` → `> 20 cm/s` is rejected as `numeric_operator_changed`; `10 cm/s` → `0.10 m/s` is accepted. Approximation cannot become equality, and tolerances cannot disappear. Unsupported units retain unresolved tokens and cannot be silently treated as known dimensional conversions. The numerical grammar is intentionally bounded; unsupported forms can be rejected rather than assumed equivalent.

`DiscoveryHypothesis` declares BROADER_DISCOVERY, NARROWER_DISCOVERY, SIBLING_DISCOVERY, RELATED_PHENOMENON, DOCUMENTARY_SYNONYM or UNVERIFIED_HYPOTHESIS. Declared hierarchy directions require graph validation. Other formulations remain non-authoritative documentary hypotheses. They never change original QueryIntentV2, mandatory constraints, ontology mappings, measurements or scientific eligibility. Unverified hypotheses are not equivalent reformulations.

The existing Nemotron adapter accepts the bounded additive hypothesis schema, preserves exact-span validation for reranking and records sanitized receipts. Cache receipts distinguish current calls from compatible replay, including registry/language compatibility. Source constraints filter every documentary hypothesis search. Model and Jev failures leave deterministic evidence intact.

Historical model searches were revalidated under the new contract: 3 equivalent formulations accepted, 51 equivalent formulations rejected, and 24 previously proposed searches separately tested as UNVERIFIED_HYPOTHESIS under revised deterministic post-processing. These were not new v2 model inferences. No live API call occurred. qi31 cannot acquire SafetyImplication as a canonical requested class from an expansion.

See `artifacts/phase3c_related_expansions_v1.json`, `phase3c_related_numeric_operators_v1.json`, and the generic regression tests.
