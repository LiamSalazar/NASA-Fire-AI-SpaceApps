# Phase 3C controlled scientist-facing pipeline replay

`answer_native_controlled_text` now composes minimal interpretation, deterministic semantic resolution, native execution, opt-in discovery, and a readable deterministic response. A four-case smoke replay used already persisted live Nemotron interpretation receipts (no repeat interpreter calls) and cached expansion/reranking receipts when input digests matched. It is explicitly a **replay smoke test**, not a fresh live interpreter benchmark or independent accuracy set.

| Receipt | Current behavior |
|---|---|
| qi12, S1/S2 comparison | Two native DIRECT runs, nine source passages, zero contextual-only candidates. The response presents shared airflow (20 cm/s), oxygen difference (21.5–21.7% vs approximately 21.5%), concurrent vs opposed flow, unknown pressure, and both table evidence IDs. It states that it does not infer significance or causation. |
| qi24, “Show PMMA tests” | No native DIRECT/RELATED; eight documentary passages and 12 clearly separated contextual candidates. It abstains from a scientific match and labels candidates non-supporting. |
| qi27, “What has NASA reported…” | No DIRECT; the native classifier returns two RELATED run records with material differing and gravity matching; ten passages are available. No `SafetyImplication`/`NASAConclusion` identity is invented from “reported”. Independent relevance remains required. |
| qi42, two materials | Clarification required for `multiple_values_for_relation:hasMaterial`; zero native passages and zero discovery candidates. |

The renderer’s scientific statement gate remains quotation-oriented. No generative paraphrase is accepted or tested here; fallback is safe deterministic presentation, not a claim of full answer relevance. The source location label now says “recorded page N (physical PDF page unverified)” unless the passage is explicitly marked verified. The four receipts are in `artifacts/phase3c_controlled_pipeline_replay_v3.jsonl`; counts and interpretation provenance are in the corresponding summary.
