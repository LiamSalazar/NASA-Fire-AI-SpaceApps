# Corrective QueryInterpreterV2 results

Model: `nvidia/nemotron-3.5-lightning-30b-a3b`. Temperature 0, non-streaming,
thinking disabled, 1,000-token bounded output, 40-second timeout, bounded retries.
Nemotron extracts minimal language; deterministic registry resolution supplies
canonical identities. No V3 or property-specific schema fields were introduced.

Frozen historical gold remains unchanged. The live set contains 39 supported
reviewed standalone cases, two conversational cases, and 30 existing template
compositions. Unsupported contract-gap cases were not silently given invented
reviewed gold. This run therefore cannot substantiate 47/47 executed coverage.

## Results and version separation

The first corrective live pass scored 6/39 exact standalone intents (0.1538).
A later generic deterministic reconciliation removed contradictions such as
approved known aliases simultaneously appearing in the unknown slot. Reusing
the SAME persisted minimal predictions yields 10/39 (0.2564; Wilson 95%
0.1457–0.4108). This is post-benchmark repair, not a second zero-shot model run.
The defective historical pass scored 0/39 on this supported subset.

| Field, repaired standalone resolution | Precision | Recall | F1 |
| --- | --- | --- | --- |
| Targets | 39/39 | 39/39 | 1.0000 |
| Entity constraints | 33/33 | 33/35 | 0.9706 |
| Property constraints | 5/5 | 5/6 | 0.9091 |
| Requested information | 10/13 | 10/26 | 0.5128 |

Structured-valid: 39/39; operation: 37/39; numeric value/operator/unit: each
5/6, SMALL_N; comparison: 2/3, SMALL_N; ambiguity: 37/39; unknown handling:
23/39; clarification: 36/39; fallback on completed valid calls: 0/39.
Standalone range and approximation gold support is 0: NOT_APPLICABLE, not 100%.
Underinterpretation is 18/39; overinterpretation 3/39 under the field-set metric.
Latency N=39: median 3,064.95 ms, p95 17,708.14 ms, maximum 20,310.66 ms.
These are completed latest-call timings; earlier failed attempts are preserved
separately and are not erased from the service-failure record.

Conversational exact intent: 0/2, SMALL_N. Existing compositions exact: 1/30.
Their numeric value is 26/30, operator and unit each 29/30, range 9/20, explicit
approximation preservation 10/10. Entity F1 0.9231; property F1 0.5424; requested
information F1 0. These older compositions represent only three pattern families.
The new ten-family intent-first composition campaign has separate gold/results:
`phase3c_corrective_compositional_*_v1`; do not pool it with historical cases.

Novel composition gold: 30 surfaces, 27 previously unseen capability combinations,
nine new combination signatures. First attempt: 27/30 structured-valid, three
service timeouts; after one bounded retry, 30/30 valid, 3/30 exact (0.1000).
Successful first-attempt predictions were reused, not called again.
The retry-pass results are v2; v1 remains immutable. Targets precision/recall
25/30 each, F1 0.8333; entities 39/39 each, F1 1.0000; properties 21/24 each,
F1 0.8750; information precision 21/22, recall 21/24, F1 0.9130.
Numeric and unit correctness 24/24, operator 21/24, range 6/6 SMALL_N,
approximation preservation 0/3 and comparison 0/3, both SMALL_N; ambiguity 20/30,
unknown handling 15/30. Latest successful-call latency N=30: median 5,305.76 ms,
p95 28,684.30 ms, maximum 29,233.23 ms. Three original 40-second failures are
preserved and excluded from that latest-success latency; total API attempts 33.
These failures reinforce REVISE rather than justify a generalization success claim.

## Diagnosis and safety

`artifacts/phase3c_corrective_error_matrix_v1.json` records expected and actual
fields for all 71 historical cases. Good target/entity performance does not
compensate for missing information genres, unresolved comparisons, or poor
unknown handling. The adapted deterministic parser comparison is stored by
category in the resolution-repair summary; this evidence does not justify a
claim that Nemotron materially improves the complete intent contract.

Protected terms retain ambiguity: bare velocity is not airflow, acrylic is not
PMMA, and bare Saffire is not Saffire-I. Model-proposed associations cannot
override those protections. Approximation without explicit tolerance remains
non-exact; no universal ±5% exists. Numeric ranges, scientific notation, inclusive
operators, and explicit tolerances are handled generically, but live composition
results demonstrate continuing failures.

Decision: REVISE. Repair requested-information resolution, compound numeric
expressions and qualified operands. Preserve gold and pre-repair predictions;
evaluate subsequent fixes in a separately versioned pass.
