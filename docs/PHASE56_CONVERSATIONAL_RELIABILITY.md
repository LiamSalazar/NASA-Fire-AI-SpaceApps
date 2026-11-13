# Conversational reliability checkpoint — 2026-11-07

This checkpoint improves preservation and repair of supported statements. **Full
conversational acceptance remains incomplete.** Useful generated explanations
were more frequent in one repeated core conversation, but that gain was not
consistent in the complete final generation sweep. Difficult comparisons,
instrument explanations and ambiguous questions still lose important information.
Neither successful HTTP requests nor valid citations establish answer quality.

## Baseline and diagnosed losses

Branch `NASA_hackathon`, original HEAD `03d0fc0`, initially clean. The previous
seven-turn receipt reported three generated answers, one excerpt answer and
three metadata listings, all DEGRADED. This was historical, not rerun evidence.
The reproduced original-code baseline uses archived source plus its lexicon and
ontology assets against the unchanged current snapshot. Six successful turns
produced four generated answers and two excerpt fallbacks; all six were marked
DEGRADED. Its first five conversational turns produced three explanations.
An earlier archive setup attempt returned six 503 responses because the archive
lacked lexicon assets. Those failures are retained separately, not excluded
without explanation. The harness now checks assets before calling the provider.

Actual draft/rejection traces revealed these general defects:

- Whole multi-sentence segments were rejected when only one assertion failed.
- Source context was clipped before relevance ordering; displayed documentary
  slices were mistaken for all available evidence. Many repeated run captions
  competed with methodology and overview passages.
- Source text, serialized registry details and pseudo-structured projections
  duplicated context. Prompts approached 41,000 tokens in one first revision.
- Some model text included known support IDs in brackets. Their hexadecimal
  digits were interpreted as scientific quantities and falsely rejected.
- Correct descriptions sometimes cited the wrong passage of the same report.
  Relevant support could be outside the supplied context.
- A joint semantic premise could fail although one actual source sufficed.
- Hyphenated quantity typography and PDF line wrapping caused false mismatches.
- Source excerpts were sometimes incorrectly described as an interpretive
  projection, encouraging abstention from reporting documented findings.
- A source deduplicated into DOCUMENTARY could disappear from the exploratory
  renderer, which accepted only rows still labelled DISCOVERY.
- Relevance pruning could leave stale citation numbers and crash fallback.
- Any rejected draft claim could label otherwise valid final prose DEGRADED.

`baseline-diagnosis.json`, complete draft/repair traces and actual response texts
are under `artifacts/conversation_reliability_v1/`.

## Implementation

The existing search, registry, RDF, scientific classification, conversation,
Nemotron and semantic-support services are reused. No parallel retrieval or
verification architecture, model, dependency, translation path or ontology fact
was introduced. DIRECT and RELATED eligibility are unchanged; `search.py` is
unchanged. English-only generation and the existing pinned NLI verifier remain.
Its multilingual-capable weights are used only for English claims; no
translation or bilingual verification step was introduced.

`services/conversation.py` now verifies sentences independently and retains
their parent paragraph. Each trace identifies draft statements, proposed and
resolved sources, failure reasons, repair identity and final presentation.
Splitting is sentence-based: a sentence containing several propositions can
still be rejected as a unit. Known supplied inline locators are removed from
prose and treated as proposed support IDs; unknown identifiers are rejected.
Actual quantities, units, runs and subjects still undergo verification.

The existing verifier can examine sufficient source subsets and narrow their
citations. Failed documentary attribution can trigger bounded examination of
original passages from the **same document**, including adjacent context and
pages outside the generation pack. Every proposed replacement must resolve to
an exact original span and independently pass the same structural, quantity,
scope, modality and semantic checks. Cross-document or experimental-subject
inference cannot authorize a documentary repair.

One repair attempt is enabled by default (operator range zero to two). Nemotron
receives rejected statements, specific failures, permitted real evidence and a
schema requiring `repair_of`. Accepted content survives failed repairs. Empty
drafts with responsive documentary evidence can receive one coverage repair.
No retry changes source records, promotes classification or relaxes the 0.92
NLI threshold. Pure NLI results have a bounded cache; source-integrity checks
are repeated. Quantity punctuation accepts `8-atm`/`8 atm`, without conversion.

Composition uses a model-declared information-needs plan, question-term ranking,
source diversity and overview reservations before the character budget.
Evidence is serialized once with its scientific role and source identity.
Relevance and bounded bidirectional redundancy checks follow fidelity checks.
Their decisions and omissions remain distinct in traces. Retained candidates,
pagination and retrieval focus survive failed generation. Authentic catalogue
records support attributed catalogue facts, not measured findings. Selected
retrieved candidates remain exploratory even when their retained search view
was DOCUMENTARY; model-proposed directions remain uncited and unverified.

Additive HTTP fields separate `generation_status`, `verification_status`,
`answer_completeness` and `coverage_summary`. Existing `provider_status` and
response contracts remain. A verified final explanation can be AVAILABLE after
draft rejections or successful repair. Excerpts and source listings are still
identified as fallback, never successful explanatory generation. CONFIGURED
means credentials exist, not that the remote service has been proven healthy.

## Live execution evidence

All runs used configured NVIDIA Nemotron, the pinned local verifier and the
same scientific snapshot. Plans record production-file hashes before execution.
Responses are stochastic; these are observed runs, not a controlled estimate
of a population success rate. The 16-turn suite covers a five-turn droplet
conversation plus instrumentation, solid-fuel objectives, smoke uncertainty,
standards, pressure/oxygen, comparison, gravity rationale, ambiguity, unmatched
gravity, methodology and open exploration. Test assertions never encode answers
to these live questions.

The sixteen questions were reused across development revisions, so the frozen
sweep is a regression evaluation, not an independent unseen holdout. The final
two new wording probes provide only limited additional generalization evidence.

| Run | Turns | Generated prose | Excerpt fallback | Accepted repair turns | Exact-span citation checks |
| --- | ---: | ---: | ---: | ---: | ---: |
| Reproduced original code | 6 | 4 | 2 | 0 | 71/71 |
| Revision 1 | 16 | 8 | 8 | 7 | 76/76 |
| Revision 2 core | 6 | 1 | 5 | 1 | 34/34 |
| Revision 3 | 16 | 8 | 8 | 9 | 74/74 |
| Revision 4 | 16 | 10 | 6 | 9 | 77/77 |
| Later release conversation | 5 | 4 | 1 | 4 | 26/26 |
| Standalone exploratory probe | 1 | 1 | 0 | 1 | 6/6 |
| Actual RELATED conditions probe | 1 | 1 | 0 | 1 | 7/7 |
| Final novel instrumentation/exploration probes | 2 | 2 | 0 | See receipts | 5/5 |
| Removed caption-priority experiment | 2 | 0 | 2 | See receipts | 9/9 |
| Complete frozen generation sweep, before final remedy guard | 16 | 11 | 5 | See receipts | 97/97 |

An accepted repair proposal can subsequently be removed as redundant or
irrelevant. The repair column counts verifier acceptance, not necessarily
information delivered. `live-summary.json` separately counts repairs actually
communicated in final prose; this distinction prevents duplicate accepted
rewordings from inflating useful-repair claims.

Revision 2 deferred ten standalone probes after its observed failures; all
sixteen were subsequently run in revisions 3 and 4. No favorable-run selection
replaces these records. A later generic figure-caption penalty was tested on
the final two prompts. Both fell back, including irrelevant excerpt material.
It showed no useful improvement and was removed. Generation-service and prompt
hashes match `live-plan-final-probes.json`; the later source-local verification
guard is separately evaluated below. The two generated answers remain only
partial scientific acceptance. The failed experiment and its hashes remain in
the campaign ledger. Revision 4's full sixteen-turn sweep predates the final
same-document and metadata-presentation fixes; it is not a full final-code sweep.

In the later five-turn conversation, the measurement follow-up explained
recorded fields and imaging diagnostics with citations, rather than simply
listing source titles. The findings turn described reported diameter histories,
burning-rate constants and extinction diameters with the finite-size qualifier.
These are documented descriptions, not new scientific conclusions. The
flow/oxygen follow-up still explained only part of the requested comparison.
The exploratory follow-up fell back. A subsequent standalone exploratory success
does **not** demonstrate that the in-context failure is solved.

The RELATED probe correctly retained the investigation identity and reported
20 cm/s for Saffire runs S1 and S2 versus a requested 30 cm/s. It did not invent
30 cm/s observations. The final exploratory probe explained CIR/MDCA and offered
real CFI/CFI-G/SLICE sources with explicitly unverified applicability. Its final
instrumentation companion described FLEX-048 field-of-view history instead of
adequately explaining what the two imagers measured: faithful but insufficiently
responsive. Some generated answers remain too narrow or repetitive.

The historical/initial status problem is separable from scientific acceptance:
revision 4 records ten AVAILABLE and six DEGRADED responses; release core four
AVAILABLE and one DEGRADED. Repaired drafts alone no longer force degradation.
These statuses do not prove answer completeness. Per-call model identity,
latency, actual recorded token usage and failures are in the receipts. Early
`seconds` includes automated coverage checking; later `response_seconds` is the
HTTP duration. No dollar spend is inferred from token counts.

Across the retained campaigns there were 93 HTTP attempts (including the six
archive setup failures), 307 recorded provider calls and 3,942,715 recorded
tokens. Initial failed-harness usage may be incomplete; these are receipt sums,
not a complete billing statement. No provider calls were added for the final
verifier-only correction.

## Coverage and fidelity measurements

Candidate recall was rerun before and after on the existing provisional set.
Recall@20 remains **96.1538%**, versus the preceding round's original 77.4%
comparison, on only thirteen questions with relevance judgments (24 retrieval
queries overall). One known PSI-62 diagnostics source is still missed. This
round establishes preservation, not a further recall gain or NASA-wide coverage.

Ten source-inspected documentary propositions have explicit case associations
in `evals/phase56/answer_targets_v1.json`. They were frozen before live execution.
Inspection was by the implementing agent, not an independent scientist. The
initial whole-answer NLI communication probe could exceed its context window;
it is not used to claim a coverage percentage. A per-supported-statement replay
avoids that overflow, but remains conservative and disagrees with some clear
source-grounded paraphrases. On the six matched baseline cases it recognized
four of eight target associations; revision 4 recognized two of those eight.
Consequently **an overall target-level answer-coverage gain is not established**.
Detailed checks and qualitative review are retained, including adverse outcomes.

Structured coverage distinguishes available anchors, supplied anchors, sources
reexamined, source evidence communicated, accepted content later omitted, and
model-declared needs. These denominators expose context losses; they are not
independently graded scientific coverage. For example the final imaging probe
had 2,139 available anchors, 35 supplied, and one source communicated. That is
an operational measurement, not evidence that all available anchors were useful.
Broader candidates remain accessible regardless of prose acceptance.

The complete frozen generation sweep has twelve question–target page
associations for those ten propositions: nine target pages were retrieved, two
entered the initial source pack, eleven were checked during source reexamination,
and two exact target pages were represented by accepted prose/excerpts. A
different page may support the same proposition, so these are page-level routing
counts, not answer coverage percentages. The automatic proposition probe
recognized three associations; it is not independent scientific grading.
`target-stage-coverage.json` records every denominator and case association.

The real pinned-verifier controls accepted faithful paraphrases and quantity
typography while rejecting fabricated numbers/units/runs, causal invention,
objective-as-observation and unverified DISCOVERY assertions. All eleven
preservation controls and sixteen existing English adversaries passed. The final
remedy correction expands preservation controls to twelve, all passing. Mixed
answer controls retained the valid assertion and excluded the invalid one.
These small controls do not establish a universal absence of false acceptance.
False rejection of complex, multi-proposition summaries remains a known defect.
The original source, subject, quantity, provenance, scope and citation checks
were preserved; no threshold was lowered to improve acceptance counts.

## Stability and remaining acceptance work

The completed release regression run passed **3,566 tests, 40 existing skips**;
the frozen generation-version run is recorded in `regression-frozen.json`.
The final remedy-corrected suite passed **3,567 tests, 40 existing skips, zero
failures**, recorded with every batch log in `regression-remedy.json`.
Focused HTTP/conversation/synthesis tests passed 42 tests before the remedy
correction, and all 43 after adding its regression. Ruff, compile,
locked dependency synchronization and dependency compatibility checks passed.
No dependency or model provisioning change was required. Actual TCP uvicorn
smoke checks passed with credentials disabled; no-key excerpts remain usable.
Snapshot verification passed, and historical evidence SQLite checksums matched
before/after every full batch run. OpenAPI changes are additive. No dashboard,
raw data, approved vocabulary or historical snapshot was edited.

Important outstanding work is independent scientific grading across a
complete conversation suite, more reliable instrumentation/method
selection, fuller flow/oxygen comparisons, and handling faithful multi-clause
summaries without admitting unsupported clauses. Ambiguous terminology and
unmatched-condition questions still sometimes produce faithful but unhelpful
fallbacks. Relevance pruning and source selection can omit important material;
source fidelity alone cannot solve that problem. Independent scientific review
is still needed. This checkpoint must not be described as fully stabilized.

### Complete generation sweep and false-acceptance repair

The complete frozen sixteen-turn generation campaign finished: eleven generated
answers, five excerpts, 97/97 exact original-span citation checks, eleven turns
with an accepted repair and eight with a repair actually communicated (nineteen
communicated repaired claims). Median HTTP duration was 45.67 seconds. Its
five-turn conversation generated three answers and two excerpts, the same count
as the reproduced baseline. The earlier four-of-five result was not consistent.
The generated instrumentation answer was useful, the normative answer preserved
requirements, and open exploration described CIR/MDCA and SoFIE with real,
explicitly unverified candidate sources. Condition comparisons, pressure/oxygen,
gravity rationale and unmatched-gravity requests still suffered poor fallbacks.
The ambiguity answer still omitted the optical meaning. The comparison answer
exposed internal field names. Full per-turn inspection is in
`source-inspection-frozen.json`; these are implementing-agent source judgments,
not independent scientific adjudication or an aggregate accuracy score.

Inspection found a **real false acceptance**, despite a 0.947976 entailment
score: the methodology answer said LLUV scatter was addressed by interpolation
of droplet history. Source `E-hackathon-8f78928f9a4b3f7a439ecf80` instead describes
LLUV scatter and, separately, estimating extinction droplet diameter after
HiBMs field-of-view loss/reentry. Co-occurrence did not establish the proposed
remedy relationship. Each source span individually scored below 0.02 entailment
for that combined statement. This failure is preserved in the raw receipt,
rather than relabelled as a successful scientific answer.

A final validator-only correction checks reduced remedial clauses such as
“addressed by”, “corrected by” and “mitigated by” against source-local sentences.
A joint premise alone cannot authorize binding a correction to a different
measurement. The failure receives explicit feedback; unrelated accepted
statements survive. Original source quotations are unchanged. The bounded
source-local check can conservatively reject a faithful relationship requiring
multiple sentences; targeted reformulation or excerpts remain available.
The actual saved generation is replayed with its original permitted evidence,
and the new regression includes both the separate-fact trap and faithful remedy
support. The production NLI threshold remains 0.92. This is an offline
post-output correction, not a new paid generation campaign or proof that other
semantic false acceptances cannot occur. Replay and final regression receipts
identify this final verifier version separately from the generation campaign.
`source-replay-remedy.json` confirms rejection of the actual erroneous statement
while retaining seven accepted methodology paragraphs. This is verification
replay, not a newly generated or reorganized final chat response.

## Reproduction and Git

See `artifacts/conversation_reliability_v1/README.md` for commands, receipt scope
and source hashes. Work is local to `NASA_hackathon`. Commits are recorded in
Git history and the final handoff. `main` and `diego/research` retain their
pre-task refs; no push or merge was performed.
Implementation commits are `4835c5d` (statement preservation, repair and
evaluation) and `f4734eb` (source-local remedy attribution). The report and
receipt commit follows these; `git log -3 --oneline` identifies the complete
local checkpoint.
