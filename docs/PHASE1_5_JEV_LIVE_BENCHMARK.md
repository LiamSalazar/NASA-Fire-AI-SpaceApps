# Phase 1.5 Jev live benchmark

Executed 2026-10-04 against the official TypeSafe API. `GET /v1/models` succeeded and exposed `jev-latest` and `jev-preview`; stable alias `jev-latest` was selected rather than the preview. Responses identify the actual model as `jev-1.13.0`. The run made 31 requests (one model discovery plus 30 bounded System One requests), used 19,666 input and 4,343 output tokens, and returned no pricing/cost field.

Each of the 30 frozen gold cases received two typed decisions in one request: a `noul` rhetorical-triage decision and a closed-set `choice` epistemic class. Jev state contained only source/document context, page, section, local heading, and passage—never gold labels, review decisions, or Nemotron output. Raw response data, selected decisions, probabilities, usage, and latency are stored in `data/eda/phase15_jev_benchmark.json`; no authorization data is stored.

| Task | Accuracy | Precision | Recall | F1 |
|---|---:|---:|---:|---:|
| Jev rhetorical triage | 0.9333 | 0.8889 | 0.8889 | 0.8889 |
| Jev epistemic classification | 0.7333 | macro 0.5083 | macro 0.7714 | macro 0.5733 |
| Deterministic rule classification | 0.8667 | macro 0.6370 | macro 0.6952 | macro 0.6576 |

Triage had one false positive and one false negative (FPR/FNR 0.0476/0.1111). Classification had NONE precision 1.0000 and recall 0.7143; OpenQuestion FPR 0.0000; ReportedExperimentalObservation FPR 0.5000; SafetyImplication precision 0.5000. Median latency was 0.309 s (max 0.410 s). Classification confidence averaged 0.9241 for correct decisions and 0.4975 for incorrect decisions, but two high-confidence errors occurred.

The threshold experiment is exploratory only: at 0.50, triage has 8 TP/1 FP/20 TN/1 FN; at 0.80 it has 5 TP/0 FP/21 TN/4 FN. The sample is too small to productionize a threshold. Jev may be used only as optional, advisory rhetorical-review prioritization through `SEMANTIC_CLASSIFIER_BACKEND=jev`; it must not discard evidence, publish claims, alter DIRECT, or replace validation.

The historical Nemotron audit is not a new full matched benchmark: it proposed non-NONE candidates for all 20 audited rhetorical negatives, while Jev classified 14/20 of that shared-negative subset as NONE. Nemotron remains the candidate-only span extractor because Jev does not extract evidence spans. `JEV_DECISION = ADOPT_FOR_SPECIFIC_TASKS` (advisory rhetorical triage only).
