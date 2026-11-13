# Nemotron real-context inference

7 fresh NVIDIA calls against actual selected NASA windows; model `nvidia/nemotron-3.5-lightning-30b-a3b`, existing configured base URL and credentials. Five initial calls failed (two timeouts, three invalid schemas); two corrective bounded calls yielded four proposals. Final deterministic validation recovered reversible whitespace in two proposals; two remain rejected (altered PMMA quotation; prospective silicone objective plus nonexact quote). No unreviewed canonical facts published.

| Window | Execution | Latency ms | Error | Proposals |
|---|---|---:|---|---:|
| mixed-silicone | Fresh | 39592 | ValidationError | 0 |
| mixed-pmma | Fresh | 40038 | APITimeoutError | 0 |
| intervention | Fresh | 14043 | ValidationError | 0 |
| mixed-silicone | Fresh | 12338 | none | 2 |
| mixed-pmma | Fresh | 2897 | none | 2 |
| bass-campaign | Fresh | 40440 | APITimeoutError | 0 |
| saffire-campaign | Fresh | 35985 | ValidationError | 0 |


Available usage across five completed calls: {'prompt_tokens': 7096, 'completion_tokens': 10192, 'total_tokens': 17288}. Usage is unavailable for the two timeouts; raw output was not retained for the three initial schema failures. None is estimated. Successful corrective calls take approximately 2.90 and 12.34 seconds. Checkpoints retain input windows, evidence IDs, exact quotations, proposal payloads and validations. Revalidation v5 is explicitly replay of those fresh receipts, not another inference call. The schema correction used at most four proposals and 1,800 output tokens, timeout 40 s, no retries.

The two accepted proposals confirm already reconstructed source scopes. Newly verified independent relationships: 0; extra recovered evidence over C: 0. D replays the checkpoint-assisted context; live calls occurred in extraction, not in each of the 15 query requests (query budget 0). This is not an online live-versus-baseline performance claim. Novel interpretations without validated membership remain staged. Incremental Nemotron value INCONCLUSIVE; schema success is not scientific value. Jev was not called: no comparable independent advisory labels, value INCONCLUSIVE, zero fresh Jev calls.
