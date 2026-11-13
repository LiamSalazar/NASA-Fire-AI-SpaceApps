# Numerical end-to-end results (fidelity v4)

Every question traverses `answer_native_text` → literal/linguistic interpretation → typed expression/unit validation → QueryIntentV2 → native plan → candidate classification → EvidenceBundle → deterministic rendering. Seven cached model proposals are separately replayed, not described as fresh inference. The source-reviewed canonical numeric intent comes from hand-specified literal question gold; it is never a new NASA measurement. A/B comparisons use the same corpus backup. Numeric corrections (C) are separated from opt-in source checks (D); final answer traces use verified citations.

| Case | Property/operator | Original → canonical | Final DIRECT / RELATED | Historical loss |
|---|---|---|---:|---|
| qi09 | AirflowVelocity LT | 10 cm/s → 0.1 m/s | 0 / 41 | NO_LOSS_IN_CACHED_PRODUCTION_PATH |
| qi10 | AirflowVelocity LTE | 0.1 m/s → 0.1 m/s | 0 / 41 | RESOLVER_REJECTS_MODEL_PROPERTY_LABEL_air flow velocity |
| qi11 | AirflowVelocity GTE | 20 cm/s → 0.2 m/s | 0 / 29 | NO_LOSS_IN_CACHED_PRODUCTION_PATH |
| qi34 | AirflowVelocity LT | 20 cm/s → 0.2 m/s | 0 / 2 | NO_LOSS_IN_CACHED_PRODUCTION_PATH |
| qi35 | AirflowVelocity LTE | 0.1 m/s → 0.1 m/s | 0 / 2 | NO_LOSS_IN_CACHED_PRODUCTION_PATH |
| qi37 | OxygenConcentration APPROX | 20 % → 0.2 fraction | 0 / 0 | LINGUISTIC_PROPOSAL_OMITS_OXYGEN |
| qi50 | AirflowVelocity EQ | 20 cm/s → 0.2 m/s | 2 / 0 | COMPARISON_AMBIGUITY_BLOCKS_ANSWER; numeric retained |


Examples disclose requested and source-reported values: qi34 asks below 20 cm/s while S1/S2 report 20 cm/s, so they are RELATED. qi35 asks at most 0.10 m/s (=10 cm/s), and the same rows fail that condition. No source-backed PMMA airflow value was invented from BASS air-display settings. Exact lexical tokens, including 0.10 and percent, are retained in `phase3c_fidelity_numeric_lexical_tokens_v1.json`. An unspecified approximate 20% is not exact equality and cannot yield a newly fabricated tolerance. Candidate-count changes are not relevance metrics. Current/canonical/replayed/frozen traces, full planner constraints and affected-candidate dimensions are preserved in `phase3c_fidelity_numeric_results_v4.json`; repeated scientific/source payloads use shared trace pools.

Final adversarial correction (fidelity v2): a synthetic model proposal supplied `cm/s` absent from “PMMA airflow 10” and added unrequested oxygen, causing an incorrect DIRECT result. The recorded failing test was repaired generically: missing units remain unresolved, model numeric expressions require literal grounding, and unrelated numeric properties are excluded. No NASA record was altered. The final shared-resolver regression retains all 19/19 expected numerical constraints (seven historical proposal replays plus twelve frozen synthetic formulations). Receipts: `phase3c_fidelity_unit_counterexample_v1.json` and `phase3c_fidelity_final_numeric_guard_v1.json`.
