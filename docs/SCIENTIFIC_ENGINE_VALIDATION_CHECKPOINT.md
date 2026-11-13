# Scientific engine validation checkpoint

12 November 2026. Boundary saved before substantial console implementation.

## Executive result

**Conditionally ready for an evidence-first research console; scientific conversational release is not accepted.** The fresh 21-scenario campaign met the 85% essential-coverage target narrowly (78/91, **85.71%**) but missed conversational usefulness (16/21, **76.19%**). It exposed two critical wrong-investigation attributions in one SAME-Reflight answer and an incorrect documentary section label. Subsequent cached HTTP regressions correct those demonstrated identity/locator failures; they do **not** establish a new fresh acceptance score. Retain the unfavorable original campaign.

## Final engine configuration

- Runtime commit: **`3ec41fa`** (preceded by `81dd6d6` stabilization). Fresh campaign evaluated `81dd6d6` before the additional corrections.
- Reused snapshot: `data/snapshots/hackathon-20261112-scientific-rc14`, ID `dc3b092ab7a455286f63d3d26c781b040106d2a2027f043609b1a15420888241`.
- Corpus: existing RC14 original PSI/document corpus, curated ontology **psi-curated-v7**, 400,177 triples; original files unchanged. Existing integrity receipt checks 17,774 original cell links and 3,074 graph evidence references.
- Channels: lexical FTS, snapshot-bound documentary vectors, native structured queries, approved RDF relations and hybrid fusion. Vectors require the configured NVIDIA embedding credential; lexical/structured/graph consultation works without keys.
- Generation: NVIDIA Nemotron default; Sonnet remains configurable. Independent local NLI threshold remains 0.92; source, numerical, identity and negative controls remain enabled. No ontology vocabulary added. Compound acronym/title spellings resolve existing entities without creating scientific facts.
- Existing API supports search, process-local conversations, candidate pagination, exact original record lookup, comparisons, typed ontology routes, source and evidence access.

## Retrieval metrics

Thirty frozen source-judged questions: 21 previously unexecuted v7 scenarios plus nine new original-table questions. Original source rows/pages and checksums were inspected independently of retrieved predictions. Judgments are agent-authored, **not blinded independent human adjudication**. These questions are now exposed.

Unique-source ranking is deduplicated within the first 20 retrieved evidence entries. Precision columns are **required-source pool hit-rate lower bounds**, since the judgments are not exhaustive. They must not be presented as exhaustive passage precision.

| Channel | R@5 | R@10 | R@20 | P@5 lower bound | P@10 lower bound | MRR in observed pool | nDCG@10 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Lexical | .6833 | .8000 | .8000 | .1400 | .0833 | .5537 | .6061 |
| Vector | .1167 | .1167 | .1167 | .0267 | .0133 | .1111 | .1102 |
| Structured diagnostic | .0000 | .0000 | .0000 | .0000 | .0000 | .0000 | .0000 |
| Graph | .8000 | .8000 | .8000 | .1667 | .0833 | .8000 | .7973 |
| Lexical + vector | .3833 | .5833 | .6167 | .0800 | .0600 | .2581 | .3229 |
| Production hybrid | **.9000** | **.9333** | **1.0000** | .1867 | .0967 | **.8348** | **.8490** |

The structured diagnostic counts evidence from DIRECT/RELATED query results; these long natural-language questions did not populate that channel. It does not measure exact record-lookup recall. Separate actual HTTP checks retrieved original records and verified their fields against original cells in all **19** table investigations. Source-document recall is not passage coverage, measurement recall or relationship correctness. Those latter recall denominators were **not measured**. Hybrid cross-document examples are included, without a separate cross-document aggregate.

Receipts: [retrieval metrics](../artifacts/scientific_console_release_20261112/retrieval30_metrics.json), [ranked channel results](../artifacts/scientific_console_release_20261112/retrieval30.json), [original record checks](../artifacts/scientific_console_release_20261112/stabilization_http/http_original_records.json).

## Scientific answer metrics

Fresh 21-scenario campaign: all 21 actual HTTP requests succeeded. All 91 frozen essential needs were graded against original source material; no coverage credit was awarded merely for avoiding an unsupported statement.

| Measure | Observed result |
| --- | --- |
| Essential answer coverage | **78/91 = 85.71%** |
| Conversational usefulness | **16/21 = 76.19%**, below target |
| Claim precision, preselected eight-scenario sample | **56/57 = 98.25%** supported final factual paragraphs |
| Contradicted / unsupported / unadjudicable in that sample | **1 / 0 / 0**; contradiction is a false section locator |
| Contradiction rate / unsupported rate in sample | **1.75% / 0%** |
| Critical hallucinations | **0 in the preselected eight; 2 wrong-investigation attributions found elsewhere in the same campaign** |
| Citation resolution | **65/65** registered citations with original files accessible; semantic support is separate |
| Citation support | Four source-review issues recorded; no claim of 100% semantic citation correctness |
| Numerical fidelity | **21/21** explicitly inspected quantity/time fields; not every numeric token |
| Explicit correct abstention, DAFT temperature diagnostic | **0/1**: no temperature invented, but bounded unavailability was not answered explicitly |
| General false-refusal rate | **Not measured**; cached optical controls falsely reject **3/3** valid original paraphrases |
| Context continuity | Saffire-III follow-up preserves S2 and correctly distinguishes S1/S2 direction and camera identifiers |

Claim units are final factual paragraphs, including compound source paragraphs; repetitions are retained and do not establish population reliability. The reviewer was an agent using original files, not a blinded scientist. A small targeted sample cannot certify universal reliability.

Receipts: [complete source adjudication](../artifacts/scientific_console_release_20261112/fresh_source_adjudication.json), [coverage/usefulness](../artifacts/scientific_console_release_20261112/fresh_metrics.json), [claim judgments](../artifacts/scientific_console_release_20261112/fresh_claim_adjudication.json), [claim metrics](../artifacts/scientific_console_release_20261112/fresh_claim_metrics.json), [numerical checks](../artifacts/scientific_console_release_20261112/numerical_fidelity.json), [original source packet](../artifacts/scientific_console_release_20261112/fresh_original_source_packet.json).

## Generalization and stabilization

The v7 questions and source judgments were frozen before scoring. The original campaign is preserved as the fresh baseline. Once a failure was inspected, its question became regression material.

General corrections after that campaign resolve an acronym/suffix spelling against an existing registered title, reject Boolean table cells as section headings, and bind documentary recovery to explicitly named source documents. Actual cached HTTP now retrieves SAME-Reflight **62a** (Kapton, aged, 8.1 cm/s, Rt/R0 1.48, net aging 808 s), reconstructs the correct FLEX **4.0 / 4.1** section, and removes an unrelated sealed-container example from Test 7. No new generation was used. These are regression results, not fresh generalization acceptance. Full normative-condition communication remains incomplete.

Focused engine/B8 checks: **157 passed**; a separate two-turn HTTP receipt-lineage test passed. The final complete technical regression is reserved for the completed console handoff. Restored RC14 assets passed real TCP checks, including expected 503 behavior for missing/incompatible assets. No corpus rebuild was performed.

Receipts: [stabilization checks](../artifacts/scientific_console_release_20261112/stabilization_regression.json), [focused tests](../artifacts/scientific_console_release_20261112/engine_focused_tests.txt), [isolated restored HTTP](../artifacts/scientific_console_release_20261112/restored_http.json).

## Latency and cost

- Fresh 21-request mean wall time **77.42 s**; measured retrieval mean **5.28 s**, local NLI mean **25.27 s**. Remaining time includes source assembly, alignment, generation, composition and cold initialization.
- A receipt-lineage defect truncated provider telemetry after the first turn. Only the first turn has complete provider-call timing: **17.17 s**, four calls, 88,671 input and 1,515 output tokens. Totals for the other 20 turns are **not measured**; do not use the superseded aggregate to claim negligible provider latency. Runtime `3ec41fa` fixes this, with a two-turn HTTP regression. Do not regenerate identical answers to fill missing telemetry.
- Six matched cached optical requests improved from **101.16 s** mean to **45.78 s** (54.75% lower), with unchanged final answers; valid-paraphrase rejection persists. This is a finite cached diagnostic, not a general speed guarantee.
- Reused four archived identical-evidence-package comparisons. Mean generation was **10.78 s Sonnet / 8.35 s Nemotron**, without an established final-answer advantage. This supports retaining the existing default, not claiming universal superiority.
- **Zero new Sonnet calls; zero incremental Sonnet spend.** Configurable Sonnet brake remains at most **USD 15 / 40 calls**. NVIDIA was accessed through the configured free-tier service; an actual billing receipt is unavailable, so actual NVIDIA cost is **not measured**. Historical Sonnet cost of USD 1.064602 is a usage/list-rate estimate, not an invoice or new spend.

Receipts: [corrected timing/cost](../artifacts/scientific_console_release_20261112/fresh_timing_cost_corrected.json), [cached latency](../artifacts/scientific_console_release_20261112/cached_latency_comparison.json), [provider decision](../artifacts/scientific_console_release_20261112/provider_decision.json).

## Critical limitations

Conversational usefulness is below target. Valid paraphrases can still be rejected, normative lists can remain incomplete, responses can repeat source fields or include tangential documentary context, and bounded missing-information answers can be omitted. Generalization has not been re-established after the final identity corrections. Semantic citation correctness is not guaranteed by resolution. Structured source tables, configuration summaries, session entries, derived quantities and actual observations retain distinct roles. No direct evidence does not establish a NASA knowledge gap.

## Integration readiness

Base prefix `/api/v1`:

- `POST /search`: `SearchRequest` → `SearchResult` (`direct`, `related`, `documentary`, `discovery`, `comparison`, bounded candidates).
- `POST /chat`: `ChatRequest` → `ChatResponse` (`answer`, numbered `citations`, `evidence_groups`, `discovery_suggestions`, `conversation_id`). Private diagnostics must not be rendered in the console.
- `GET /conversations/{uuid}/candidates`: bounded candidate continuation.
- `GET /records?investigation=…&identifier=…`: source-scoped original records, `fields`, source evidence, pagination.
- `POST /comparisons`: approved subjects/dimensions → provenance-preserving comparison matrix with MATCH, DIFFER, UNKNOWN, CONFLICT and NOT_COMPARABLE semantics.
- `GET /ontology`, `POST /ontology/navigate`: approved concepts and bounded, evidence-linked typed routes.
- `GET /catalog`, `/sources/{id}`, `/evidence/{id}`: registered source/locator/excerpt access.
- `GET /health`, `/capabilities`, `/readiness`: integration diagnostics; readiness is not scientific acceptance.

Sessions are process-local, bounded and expire after one hour. The API has one scientific worker, no streaming and no server-side request cancellation. Keys remain server-side. No public hosting, merge or push is part of this assignment.

## Decision

Proceed with the standalone scientific console using the real API, explicit evidence categories, original records and visible scientific scope. The backend is technically prepared for this integration. **Do not describe the scientific conversational engine as having passed final acceptance.** The handoff must retain the failed targets, corrected-regression boundary and pending independent human review.
