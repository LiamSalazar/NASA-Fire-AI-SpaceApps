# Native end-to-end corrective results

The actual `answer_native_text()` service was exercised. It resolves minimal
language into validated V2, runs the generic KG and existing BM25 registry,
builds EvidenceBundle, and produces deterministic presentation or validated
source quotations. Runtime guards prohibit V1 matching/building and compatibility
execution. All 20 native guard checks passed.

Gold was frozen before execution. Nineteen inputs reuse compatible persisted
live language predictions; the new document lookup uses a fresh call. This is
an integrated native service benchmark, not 20 new serial end-to-end API calls.
Eight cases lack independent objective relevance gold and remain REVIEW_REQUIRED.
Required evidence identities/no-answer checks score only the other 12 cases.

| Metric | First corrective pass | Resolution-repair pass |
| --- | --- | --- |
| Planning | 20/20 | 20/20 |
| Exact interpretation | 2/20 | 5/20 |
| Objective evidence recovery | 7/12 | 8/12 |
| Full objective success | 1/20 | 2/20 |
| Useful safe fallback under strict objective criteria | 1/20 | 2/20 |
| Synthesis attempts / valid drafts | 6 / 5 | 6 / 4 |
| Accepted source-quotation claims | 2 | 5 |

Full objective success requires exact intended semantics, required evidence or
justified no-answer, and valid source identities. This is intentionally conservative;
it does not substitute for independently reviewed scientific usefulness. Missing
relevance gold is not marked success. Fallback alone is not complete success.
Repaired full success 2/20=0.1000, Wilson 95% 0.0279–0.3010. Recovery 8/12=0.6667,
Wilson 95% 0.3906–0.8619. Independent DIRECT/RELATED and subjective response
relevance rates across the full service set are not established.

The known failures include unresolved numeric expressions (qi11), qualified
comparison operands (qi12), missed observation identity (qi14), missed guidance
(qi17), and missed requested conclusion (qi45). All case outputs, sources,
accepted text, fallback status and grounding errors are in
`phase3c_corrective_e2e_results_v1/v2.jsonl`. These IDs name diagnostic cases;
production code contains no case-ID rules.

Repaired native/synthesis execution latency N=20: median 82.67 ms, p95 40,345.90
ms, maximum 42,662.12 ms. This excludes cached language-call wall time. Separate
language and synthesis timings are persisted; no fresh serial total-latency
claim is made. Citations are valid for 5/5 accepted generated claims, SMALL_N;
zero visible unsupported generated claims does not make unrelated evidence useful.

Coverage limitations: no new structured experimental NASA holdout, no independently
reviewed paraphrase-relevance gold, and no native natural-language new-property
NASA-source case. Dynamic generic execution tests cover new properties separately.
The novel composition campaign is reported separately, not retroactively injected
into these frozen 20 cases. Readiness gate FAILS; V2 remains experimental.
