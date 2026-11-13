# Phase 3C final readiness decision

**READY_FOR_PHASE_4 = NO.** Phase 3C corrective engineering is closed with
explicit readiness blockers. No Phase 4 work is started.

## Decisions

- `NATIVE_V2_EXECUTOR_DECISION = REVISE`
- `QUERYINTERPRETER_V2_DECISION = REVISE`
- `GENERIC_INGESTION_DECISION = REVISE`
- `GROUNDED_SYNTHESIS_DECISION = REVISE`
- `JEV_TRIAGE_DECISION = KEEP_OPTIONAL`
- `GENERALIZATION_DECISION = LIMITED`
- `V2_DEFAULT_PATH_DECISION = KEEP_EXPERIMENTAL`

The generic executor has substantial positive evidence: the existing
230/230-property and 125/125 post-freeze extensionality benchmarks pass;
native benchmark guards pass; the frozen objective retrieval regression
recovers 11/11 required identities; and DIRECT/RELATED remain structured.
The latest preserved parity second pass reports 39/39 DIRECT and 39/39 RELATED,
but only 9/39 exact evidence-ID parity; the pass was not rerun after the final
retrieval repair. Therefore the broad evidence-selection behavior still needs
independent review before default-path adoption.

## Remaining blockers and smallest justified work

1. Standalone exact interpretation is 11/41; requested-information recall is
   34/50 (0.68); numeric ranges are 15/26. Have a domain reviewer approve the
   intent contract for disputed “observation/suppression/safety implication”
   cases, then correct only demonstrated generic parser defects and evaluate
   on a new frozen set. Do not modify the existing gold.
2. Eight of twenty end-to-end cases are still `REVIEW_REQUIRED`; three positive
   retrieval cases include extra evidence beyond frozen expected IDs. Have an
   independent fire-safety scientist review the supplied packet and assign
   relevance, authority, and no-answer labels before claiming independent
   retrieval accuracy.
3. No new, genuinely unexposed structured NASA combustion experimental dataset
   was acquired. Continue source-metadata screening after the architecture
   freeze; if one is found, freeze it before detailed content inspection and
   report a blind first pass. Do not reuse PSI-142, PSI-99, FLEX, or other
   exposed sources as new evidence.
4. Generative paraphrase fidelity remains unvalidated. Keep the quotation
   boundary and deterministic presentation until independently reviewed
   fidelity examples exist; test whether the fallback answers the query without
   irrelevant evidence.

## Integrity and quality

The additive native projection covers 405/405 canonical runs, retaining 682
validated conditions, 812 relations, and 424 evidence references. It adds no
observed measurement not present in source-backed canonical data; 2,314
unmapped fields remain provenance-backed staging. The 274 supported mmHg
pressure entries convert to Pa; no invalid conversions or broken references
remain.

Ruff format/check pass; pytest passes 91 tests. Canonical and generic SHACL,
SQLite/foreign keys, Evidence Registry references, and FTS coverage/uniqueness
pass. Historical evaluation artifacts were not overwritten. Jev's prior
30-case result remains advisory only (F1 0.8889 versus 0.7500 deterministic
rules); it is not a scientific authority or mandatory dependency.

The measured results and machine-readable receipts are indexed in
`artifacts/phase3c_final_repair_results.json`. This is a readiness decision,
not a restart of architecture design.
