# Scientific engine release acceptance — 2026-11-07

The latest backend-owned provenance correction and NO-GO assessment is in
[SCIENTIFIC_ENGINE_PROVENANCE_CORRECTION.md](SCIENTIFIC_ENGINE_PROVENANCE_CORRECTION.md).

## Executive decision

**NOT YET ACCEPTED — SCIENTIFIC ENGINE NOT YET ACCEPTED.**

Do not freeze this backend as scientifically ready for dashboard integration.
Needs-aware context allocation improves a reproduced routing defect and retrieval
is preserved, but reviewed answers still omit essential information. A fresh
experiment also exposed an accepted false claim about missing report data.
The final verifier rejects that saved claim; this replay does not establish fresh
scientific acceptance of the final code.

| Mandatory gate | Decision | Evidence |
| --- | --- | --- |
| 1 — Scientific integrity | Not established; observed acceptance failure | False document-wide absence accepted in fresh evaluation; corrected offline. Other source-attribution/proposition defects remain. |
| 2 — Retrieval preservation | Pass on the limited benchmark | Recall@20 96.1538% before and after; unchanged qrels. |
| 3 — Context coverage | Not passed | Fixed-query supplied page associations improve from 2/12 to 7/12, but page presence and lexical routing still do not establish sufficient requested content. |
| 4 — Conversational quality | Fail in reviewed acceptance runs | Useful natural prose: 6/11 answerable turns in first holdout; 2/11 in fresh experiment, below 85%. |
| 5 — Answer coverage | Fail in reviewed acceptance runs | Essential supported targets communicated: 9/17 and 8/16, below 85%. |
| 6 — Technical stability | Technical checks pass; scientific readiness remains separate | Final regression, snapshot, HTTP, dependencies and provider receipts below. |

All measurements derive from
[`summary.json`](../artifacts/scientific_engine_release_v1/summary.json), its linked
raw receipts and explicit source reviews. These are implementing-agent judgments,
not independent scientist adjudication or statistical generalization.

## Architecture

The existing search, investigation, registry, RDF, comparison, conversation,
Nemotron adapter, verifier, repair loop and API are retained. No scientific data,
ontology, snapshot, dependency, dashboard or external repository was rebuilt.

Nemotron's existing retrieval plan now declares bounded, dynamic information
needs and search terms **before** context allocation. No experiment-specific
requirements or benchmark response dictionary enters production. Offline mode
uses question clauses as search directions. Planning directions are not ontology
vocabulary or scientific findings.

The refactored inventory makes every registered page of an already retrieved
DOCUMENTARY report eligible, replacing the first-six-overview restriction.
The existing inventory then allocates context by marginal information need,
word-based content novelty, source/page diversity and actual serialized evidence
cost. Numerical variants of repeated captions do not automatically count as new
prose; their original numbers, units, subjects and spans remain intact. Selection
has no minimum-source quota and cannot promote applicability.

`services/context_assembly.py` centralizes this allocation and the generator's
serialization. Previously `len(str(anchor))` budgeted duplicated text, registry
objects and context; now accounting uses the exact evidence representation sent
to generation, including JSON separators. This is an evidence-character budget,
not a guarantee about total request tokens. Source identity and provenance travel
with every anchor. The full pool remains accessible through existing discovery
and evidence lookup.

Per-anchor decisions record selection, absence of a routing match, or budget
omission. Public coverage gives need-level candidate counts and supplied/support
contribution; it explicitly does not certify semantic sufficiency. Full decisions
remain in traces. Repair reuses the same allocator, preserves accepted material,
and can address an unused model-planned need. Focus retains planned/unanswered
needs after degraded turns. Generation requests smaller support lists and
self-contained statements. Strict DIRECT/RELATED eligibility is unchanged.

An additional Nemotron source-examination call was implemented and tested as a
bounded exact-quotation selection experiment. Its fresh run introduced misleading
absence assessments, wrong proposed locators and inadequate final coverage. It
was **pruned**, with exact source bundles, tests and all outputs preserved. It is
not an extra production subsystem or a claimed improvement.

## Retrieval

Reconfirmed macro Recall@20 is **96.1538%**, matching the preceding 96.2% rounded
result. The benchmark contains 24 retrieval questions, of which 13 have reviewed
provisional relevance judgments. The known PSI-62 diagnostic-source miss remains;
no missed-source change is hidden. See
[`baseline-recall.json`](../artifacts/scientific_engine_release_v1/baseline-recall.json)
and [`final-recall.json`](../artifacts/scientific_engine_release_v1/final-recall.json).

This establishes preservation on that small incomplete relevance set, not recall
of all NASA literature. Production `search.py`, classification rules and qrels
were not modified.

## Scientific context

Identical saved query jobs were replayed against archived `bde9672` and the new
allocator, without provider calls or revised relevance judgments:

| Exact historical target-page associations | Original | New allocation |
| --- | ---: | ---: |
| Retrieved | 9/12 | 9/12 |
| Parsed into eligible source anchors | 11/12 | 11/12 |
| Initially supplied to generation | 2/12 | 7/12 |

The original nine-to-two discrepancy is reproduced, rather than inferred from
prior prose. Parsing a source into anchors is not scientific examination, and
supplying a page is not supplying its important finding. The distinct live
development run retrieved 11/12 target pages, supplied 9/12, and communicated
only 4/12 complete reviewed propositions. Its queries and generations differ
from the fixed-query replay; these denominators are not interchangeable.

The fresh examination experiment retrieved all 16 essential target-page
associations and supplied 15/16 exact pages, but source inspection found sufficient
essential content for only 13/16 targets. One supplied FOMA page contained apparatus
identity but omitted its component list. Only 8/16 targets reached the final answer.
This directly demonstrates why page hits cannot substitute for content or answer
coverage. These experimental figures do not certify shipping context sufficiency.

Root causes remain distinguishable in receipts:

- **Retrieval:** some exact pages remain missed despite their report being found;
  duplicate local registrations also require explicit identity handling.
- **Examination/context:** terminology routing and budget competition can omit a
  requested dimension. The removed reader also proposed correct quotations with
  incorrect support IDs; literal-source checks rejected those proposals.
- **Generation/verification:** relevant radiometer purposes and accelerometer
  evidence reached generation but disappeared from final prose. Some faithful
  paraphrases receive very low NLI scores; unsupported multi-proposition claims
  can receive high scores.
- **Repair/composition:** accepted secondary sentences can survive while a main
  finding or antecedent is rejected. Reusing a support ID does not establish that
  all facts in that source were communicated. Existing traces distinguish accepted
  repairs from statements actually emitted.

## Conversational quality

All declared runs are retained; there was no favorable-run replacement.
Four complete multi-turn conversations account for 12 of the 40 turns, including
follow-ups, an explicit topic change and recovery after degraded answers. The
remaining turns cover instrumentation, methods, observations, objectives,
comparisons, standards/configuration assessment, ambiguity, exploration and
incomplete evidence across several source families.

| Evaluated version | Turns | Generated mode | Excerpt mode | Metadata mode | Reviewed useful natural turns | Full targets communicated |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Development allocation | 16 | 10 | 6 | 0 | No aggregate usefulness score claimed | 4/12 |
| First frozen holdout | 12 | 9 | 2 | 1 | 6/11 (54.5%) | 9/17 (52.9%) |
| Fresh examination experiment | 12 | 8 | 3 | 1 | 2/11 (18.2%) | 8/16 (50.0%) |

The first holdout's six useful turns include two explicitly **partially useful**
explanations; four were judged useful without that qualifier. Universal-threshold
and universal-law questions remain in receipts but are excluded from answerable
turn denominators. Excerpts can faithfully communicate targets and count for
that target metric; they do not count as generated explanations. Metadata-only
exploration remains accessible but is not credited toward the natural-prose gate.
A turn with unsupported facts is not successful.

The sets differ, so these percentages do not establish a causal effect or a
population success rate. No final-version live acceptance percentage is claimed
after the last safeguard and pruning. Incomplete comparisons include omitted
MIST/GEL dimensions, solid-fuel geometries, Saffire airflow velocity and the
flow/oxygen follow-up. Some fallbacks contain irrelevant but authentic extracts.

## Scientific integrity

Across the retained runs the verifier accepted 68 generated statement proposals
and rejected 356; response bookkeeping identifies 58 communicated generated
claims. These are **verifier decisions**, not scientific precision estimates.
Some accepted proposals are duplicate/repair statements later omitted.

All **137/137** original-span citation checks resolved through the evidence API.
No fabricated evidence ID was found. Nevertheless, source inspection found wrong
or insufficient per-statement supporting passages. Real citations alone are
insufficient for claim acceptance.

Two measured safeguards were added without changing the 0.92 NLI threshold:

1. An unstructured numerical table cannot authorize narrative findings through
   NLI alone. Exact quotations and trusted labelled registry projections retain
   their existing paths. The actual bad table attribution is rejected in
   [`table-attribution-control.json`](../artifacts/scientific_engine_release_v1/table-attribution-control.json).
   A complex faithful-looking prose control still fails NLI; that adverse result
   is retained.
2. A document-wide reporting-absence claim requires explicit source-local
   reporting-absence support. An unrelated negative event cannot prove missing
   records. A fresh answer asserted that translated-test numerical information
   and outcomes were not reported, accepted with entailment **0.946446**.
   The same report's FLEX−037 caption, registered page 71, reports approximately
   **3 mm/s** and an extinction outcome. The final safeguard rejects the saved
   claim in [`absence-attribution-control.json`](../artifacts/scientific_engine_release_v1/absence-attribution-control.json).

These corrections are source-local replay and controls, not fresh recomposition
of the evaluated answers. Source attribution for compound assertions and
procedural identity remain concerns. The existing remedy relationship safeguard,
quantity/unit checks, scientific modality, experimental identity and prohibition
on unverified DISCOVERY findings remain. Final preservation controls pass 12/12
and the existing English adversaries pass 16/16. These small controls do not
establish universal absence of false acceptance. No numerical/unit regression
was observed in those controls; broad numerical reliability is not inferred.

## Generalization

The old regression set and targets are unchanged. The first holdout's 12 new
questions and 17 source targets were hash-frozen before production edits. After
exposure, the source-examination correction was evaluated on 12 fresh questions
and 16 newly frozen targets. Both sets and all failures remain. Neither set may
be described as unseen in future tuning.

Production routing contains no NASA title, experiment ID, target proposition or
question-specific answer. Invented-study tests check input-order invariance,
repetitive-caption competition, missing dimensions, late report pages, exact
budget accounting and source-local table/absence safeguards. The source reviews
are conservative complete-target judgments and explicitly describe partial
coverage; they are not NLI-generated targets or independent scientist grading.

## Stability

The archived baseline passed **3,567 tests with 40 existing skips**. The final
shipping-code suite: **3,574 passed, 40 existing skips, zero failures**. See `baseline-tests/` and
`shipping-tests/` in the receipt directory. Intermediate suites overlapped edits,
are labelled transitional, and are not added to final test counts.

Snapshot verification succeeds with original input, RDF and evidence SQLite
hashes unchanged. Historical frozen evidence checksums match before/after the
final batches. Locked synchronization, dependency compatibility, compile and Ruff
checks pass. No dependency or new model was added; the pinned verifier remains.

Real TCP checks cover the existing chat/search/comparison/scenario/catalogue/
ontology/evidence/source/continuation routes and expected errors. Final no-key
chat works and remains labelled as excerpts. The initial endpoint harness used
an invalid scenario provenance; its expected-200/actual-422 error is preserved,
then corrected in the harness. No API change was needed.

Configured NVIDIA was exercised in 158 recorded calls across 40 HTTP turns, with
1,979,623 recorded tokens; this is receipt usage, not a billing estimate. Two
calls recorded provider errors and three recorded partial outputs. Final source
hashes and the lack of a fresh final scientific campaign are explicit in
`shipping-freeze.json`. Operational success is not scientific acceptance.

## Remaining limitations

**Corpus limits:** the snapshot and provisional relevance set are bounded;
missing or unexamined evidence is not a NASA knowledge gap. Many requested
conditions lack accredited structured applicability. Existing discovery and
original source lookup remain useful.

**Noncritical operational limits:** sessions are process-local and expire; there
is one scientific worker, no public claim streaming, bounded candidates/context,
and per-call rather than overall provider deadlines. External NASA availability
is outside the backend's control; the verified citation tests resolve registered
source text through this API.

**Blocking scientific defects:** incomplete requested dimensions, false rejection
of faithful paraphrases, over-acceptance of compound/source-wide claims, incorrect
support-span selection and insufficient preservation of important content through
repair/composition. The final safety patches correct known failure classes but
have not passed fresh complete scientific acceptance.

The smallest remaining work is within the existing services: verify and retain
individual propositions with their correct source subjects/spans; distinguish
scientific information needs from output instructions; trigger targeted coverage
repair on missing facts rather than reused support IDs; and preserve explicit
subjects after sentence removal. Measure these changes against independently
reviewed paraphrase and source-attribution controls, then freeze fresh acceptance
cases. Do not add another RAG system, ontology, API or general multi-agent layer.

Future cache/performance tuning, shared sessions and a broader adjudicated
relevance set can be separate work. They cannot substitute for the blocking
scientific corrections or justify an integration-ready declaration.

## Final correction checkpoint — 2026-11-07

The closing audit added sentence-local modality alignment, proposition-level
execution records, and final-need coverage based on emitted proposition text
rather than shared source identifiers. Multi-anchor verification now selects an
individual supporting anchor when one is sufficient, preventing unrelated
context from becoming a citation. New general tests cover unrelated modality,
certainty upgrades, source-local absence, numeric tables, proposition coverage,
and support identity.

The required diagnostics are preserved in
[`final-diagnostics-v2.json`](../artifacts/scientific_engine_release_v1/final-diagnostics-v2.json).
A1 replayed the 12-case preserved automatic-context run. A2 was not executed:
this environment has no NVIDIA/Nemotron credential, so no fabricated or
hand-authored “complete context” generation was substituted. A3 executed
deterministic source-local positive/negative controls; it is a structural
control suite, not an NLI precision estimate. Prior live receipts and their
unfavorable coverage judgments remain unchanged.

The full regression was rerun in 16 controlled batches to prevent fixture-copy
temporary storage exhaustion: **3,576 passed, 40 existing skips, zero test
failures**. A single monolithic run is not considered valid when its temporary
filesystem exhausts. The scientific release decision remains **NOT YET ACCEPTED**
because A2 provider comparison is unavailable and the source-reviewed live
acceptance runs remain below the 85% answer-coverage and usefulness targets.

### Live A2 follow-up — 2026-11-08

The repository `.env` supplied a working NVIDIA credential. The diagnostic
[`complete-context-live-v1.json`](../artifacts/scientific_engine_release_v1/complete-context-live-v1.json)
reused the frozen `solid_shapes` question and the same Nemotron explanation
contract. With the saved automatic evidence package, Nemotron generated four
segments covering MIST rods, RTDFS thin sheets, GEL spheres, and the comparison.
With four source-inspected original passages, it also generated four segments
covering those dimensions. The historical final HTTP response communicated only
RTDFS. Its trace records unsupported numerical values against the *cited* spans
for MIST and GEL and failed repair; no relevance organizer omission occurred.
This isolates the observed loss to locator selection and verification/repair,
while the automatic package was sufficient for this particular question.

This experiment does not certify either raw draft as scientifically accepted:
it bypasses final verification, includes only one comparative case, and the
local NLI model was not provisioned for a new complete HTTP acceptance run.
The older checkpoint's A2 unavailable status describes the earlier environment
state; the live follow-up supersedes it only for this one diagnostic case.
The release decision remains **NOT YET ACCEPTED**. The smallest next correction
is source-local locator recovery for each proposition and faithful preservation
through repair, followed by fresh source-inspected complete conversations.

## Dashboard handoff

The existing interface is documented in
[`SCIENTIFIC_ENGINE_DASHBOARD_HANDOFF.md`](SCIENTIFIC_ENGINE_DASHBOARD_HANDOFF.md),
including startup, environment, model/snapshot provisioning, chat/session and
citation contracts, comparisons/scenarios, discovery paging, statuses and an
actual captured English request/response. The backend is available for technical
interface work, **not accepted as the finished scientific engine**. No frontend
or team repository was modified.

## Git

Branch `NASA_hackathon`, worktree `/home/liam/NASA/.worktrees/NASA_hackathon`.
Implementation commit: **`fd22657`**. The accompanying release report
and receipt commit is identified by `git log -1 --oneline` at this handoff.
All work is local; no push or merge. `main` and `diego/research` retain their
pre-task refs. The final worktree is clean after the local commits (checked at handoff).
