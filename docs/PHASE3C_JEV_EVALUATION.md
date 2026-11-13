# Jev advisory evaluation

The existing TypeSafe/Jev adapter and discovery endpoint were reused. Discovery
returned `jev-latest` and `jev-preview`. Requested model stayed `jev-latest`;
all 30 actual responses identify `jev-1.13.0`. Credentials exist only in the
execution environment. No alternative Jev client was introduced.

The frozen sample reuses existing reviewed labels: nine positive scientific
candidate passages and 21 NONE passages. Each of nine positive epistemic roles
has support one. It is not a newly balanced expert study. No new human review is
claimed. Gold and per-call responses are persisted in corrective v1 files.

| Binary candidate triage | TP | FP | TN | FN | Precision | Recall | F1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A: deterministic rules | 6 | 1 | 20 | 3 | 6/7=0.8571 | 6/9=0.6667 | 0.7500 |
| B: Jev advisory | 8 | 1 | 20 | 1 | 8/9=0.8889 | 8/9=0.8889 | 0.8889 |

False-positive rate both 1/21; false-negative rate rules 3/9 versus Jev 1/9.
Positive precision/recall denominators are SMALL_N. Macro/multiclass production
claims are not supported by one example per scientific role.

Simulated first-K review yields, with nine relevant positives total:

| Configuration | K=5 | K=10 | K=20 |
| --- | --- | --- | --- |
| Rules | 4 | 7 | 7 |
| Jev | 5 | 8 | 9 |
| Rules + advisory priority | 5 | 9 | 9 |

This suggests better priority on this fixed sample, not measured human time
savings. Configuration D (equivalent Nemotron candidate extraction) was not
evaluated because equivalent independently reviewed outputs were unavailable.
No NASA passage was filtered out by Jev; relevant-evidence omission from a hard
filter is zero by architecture, not a classifier-recall success claim.

30 API requests; 12,556 input and 660 output tokens; monetary cost unavailable.
Latency N=30: median 185.94 ms, p95 302.80 ms, max 305.95 ms. No API failures in
this completed set. Per-request overhead is measured; full production extraction
pipeline overhead and actual human review workload are not established.

Decision: KEEP_OPTIONAL. The benchmark artifact initially recorded INCONCLUSIVE;
closure retains the implementation as an optional advisory experiment because
the small set is suggestive, not sufficient for ADOPT. Default remains deterministic
rules. Jev cannot establish authority, change DIRECT/RELATED, publish facts,
approve aliases, or suppress documentary retrieval. Its adoption is not a core
Phase 4 readiness gate.
