# Numerical query fidelity (fidelity v4)

The latest audit reproduced exactly: 342 pairs, nine questions, 70 candidate/evidence sets, 68 reused five times and two used once. The historical probe explicitly used an empty linguistic proposal: it never tested numerical extraction. Frozen qi09/qi11/qi35/qi37 lack numeric constraints; qi10/qi34/qi50 retain them. Historical gold remains unchanged.

Actual cached production proposals were replayed through the pre-correction resolver before edits. qi09/qi11/qi34/qi35 retained numbers. qi10's model label `air flow velocity` was unregistered; qi37 omitted oxygen; qi50 kept airflow but an unresolved compound comparison phrase blocked the answer. These are distinct from historical gold/probe defects. Original literal property expressions now take precedence over lossy model mentions, using registry aliases and typed unit validation. Numbers embedded in run IDs are not quantities. Approximation remains APPROX; no tolerance is invented. Unrepresentable disjunctions and mixed-unit ranges require clarification.

| Case | Property/operator | Original → canonical | Final DIRECT / RELATED | Historical loss |
|---|---|---|---:|---|
| qi09 | AirflowVelocity LT | 10 cm/s → 0.1 m/s | 0 / 41 | NO_LOSS_IN_CACHED_PRODUCTION_PATH |
| qi10 | AirflowVelocity LTE | 0.1 m/s → 0.1 m/s | 0 / 41 | RESOLVER_REJECTS_MODEL_PROPERTY_LABEL_air flow velocity |
| qi11 | AirflowVelocity GTE | 20 cm/s → 0.2 m/s | 0 / 29 | NO_LOSS_IN_CACHED_PRODUCTION_PATH |
| qi34 | AirflowVelocity LT | 20 cm/s → 0.2 m/s | 0 / 2 | NO_LOSS_IN_CACHED_PRODUCTION_PATH |
| qi35 | AirflowVelocity LTE | 0.1 m/s → 0.1 m/s | 0 / 2 | NO_LOSS_IN_CACHED_PRODUCTION_PATH |
| qi37 | OxygenConcentration APPROX | 20 % → 0.2 fraction | 0 / 0 | LINGUISTIC_PROPOSAL_OMITS_OXYGEN |
| qi50 | AirflowVelocity EQ | 20 cm/s → 0.2 m/s | 2 / 0 | COMPARISON_AMBIGUITY_BLOCKS_ANSWER; numeric retained |


19/19 literal numeric proposals pass the full native entry-point/planner trace (seven exposed plus twelve frozen synthetic formulations). This measures constraint fidelity, not scientific precision. Strict/inclusive boundaries have different candidate outcomes. Standalone numeric contradictions now remain RELATED only under the existing relational policy; the strict rollback path retains its behavior. Dynamic properties need no property-specific branch. The conservative offline interpreter supplies native access without an API key. Unknown scientific vocabulary remains unapproved.

Final adversarial correction (fidelity v2): a synthetic model proposal supplied `cm/s` absent from “PMMA airflow 10” and added unrequested oxygen, causing an incorrect DIRECT result. The recorded failing test was repaired generically: missing units remain unresolved, model numeric expressions require literal grounding, and unrelated numeric properties are excluded. No NASA record was altered. The final shared-resolver regression retains all 19/19 expected numerical constraints (seven historical proposal replays plus twelve frozen synthetic formulations). Receipts: `phase3c_fidelity_unit_counterexample_v1.json` and `phase3c_fidelity_final_numeric_guard_v1.json`.
