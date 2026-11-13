# Phase 3 results

## System snapshot

The closed baseline remains 286 managed documents, 6,055 passages/FTS rows, 405 runs, approximately 3,831 entities, and approximately 24,014 triples. Phase 3 does not mutate scientific state.

## Implemented interaction layer

`ProposedQueryIntent` and `ValidatedQueryIntent` are separate; validation controls identity, ambiguity, unknown terms, and units. The default retrieval remains KG + FTS5/BM25, with vectors disabled. The synthesizer is bundle-bound and draft validation precedes rendering. Streamlit exposes answer, sources, interpretation, and technical trace.

## Retrieval regression baseline

The closed Phase-2 baseline remains BM25 R@1/R@3/R@5/R@10 `.6250/.8500/.8500/.9000`, MRR `.7226`; DIRECT and RELATED supported-case correctness are both `1.0000`. This implementation does not alter matching or ranker selection.

## Live status

Live NVIDIA access was verified against `nvidia/nemotron-3.5-lightning-30b-a3b`. Authentication and endpoint reachability succeeded. A 50-case concurrent interpreter run made 50 live requests: 33 outputs passed `ProposedQueryIntent` schema validation and 17 failed it (`ProviderFailure`), for an invalid structured-output/fallback rate of `0.3400`. Median interpreter latency was `4171.9 ms`; max was `15833.8 ms`.

The live synthesis evaluation made 10 requests, one for each frozen synthesis case. All 10 failed the `GroundedAnswerDraft` structured-output boundary before grounding validation, so all safely require extractive fallback. Median failed-request latency was `1853.9 ms`; max was `2182.2 ms`. No generated scientific claims were accepted or displayed, and therefore no generated citation or epistemic-preservation metric is falsely reported as successful.

The frozen interpreter file has a pre-existing evaluation defect: it contains case category tags but not reviewed expected `ValidatedQueryIntent` fields. Consequently exact-intent, field precision/recall/F1, entity, numeric, comparison, ambiguity, and clarification correctness cannot be computed defensibly from this run. No expectations were changed after predictions.

## Decisions

`QUERY_INTERPRETER_DECISION = REJECT` (34% invalid structured output and no defensible gold-field score).

`GROUNDED_SYNTHESIS_DECISION = REJECT` (0/10 valid structured drafts; fallback is safe).

`CHAT_INTERFACE_DECISION = READY` (offline/fallback interaction works).

`READY_FOR_PHASE_4 = NO`.
