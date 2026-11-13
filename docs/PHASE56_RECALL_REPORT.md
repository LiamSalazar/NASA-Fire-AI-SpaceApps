# Phases 5–6: English workflow and scientific retrieval refinement

Worktree: `/home/liam/NASA/.worktrees/NASA_hackathon`; branch `NASA_hackathon`.
Baseline: clean `e17110b`. No raw inputs, canonical ontology, historical snapshots,
other branches or dashboard files were modified. No push or merge was performed.

## Baseline and architecture

The audit covered AGENTS.md, CLAUDE.md, CONTINUATION.md, the canonical Phase 1
record, HACKATHON_ENGINE.md, PHASE56_CHAT_API.md, the recent Phase 5–6 report,
search, native execution, investigation, semantic retrieval/verification,
conversation, API, provisioning, dependency lock and evaluation scripts.
The user's explicit hackathon branch and no-push instructions supersede the older
Phase 1 branch/push instructions. No Phase 1 ingestion work was reopened.

The initial focused baseline passed 57 tests. Storage had 7.3 GB free; tests used
bounded task-owned `/dev/shm` directories. The same v9 snapshot was used for both
retrieval measurements: 39 source registrations and 1,277 passages. Source
registrations are not unique investigations; duplicate document registrations
exist. Source authenticity does not establish question relevance.

Reused: ScientificSearchService, QueryIntentV2, native RDF selection, hierarchy
and relational traversal, SemanticRegistry/controlled lexicon, EvidenceRegistry,
FTS5/BM25, the existing investigation loop, claim selection/verification,
comparison, scenario analysis, Nemotron structured generation and HTTP service.
No second RAG pipeline, ontology or corpus was introduced.

Modified workflow:

1. Preserve strict original-question constraints for scientific eligibility.
2. Generate a broader passage pool independently of the response page size.
3. Combine lexical, focused lexical, approved alias and controlled terminology
   searches. Terminology variants use existing mappings and corpus-attested word
   forms; they do not publish new vocabulary or establish equivalence.
4. Fuse ranks, deduplicate original pages and interleave sources before paging.
5. Keep native DIRECT/RELATED gates and qualified documentary/discovery results.
6. Reuse adaptive local investigation; allow post-retrieval model exploration
   while query budget remains. Record new candidates and stop on no new yield.
7. Offer verified prose, exact excerpts and separately qualified source
   exploration, retaining broader candidates outside the main answer.

The default passage pool is 200, not the display limit of 12. Local investigation
budgets are configurable through NASA_RESEARCH_*; NASA_CANDIDATE_LIMIT bounds
the candidate pool. Per-strategy saturation and pool/context omissions remain
visible. These bounds never imply exhaustion of NASA literature.

The semantic-candidate injection boundary can reuse LocalVectorIndex. It was
exercised with a controlled adapter to verify that similarity cannot authorize
DIRECT/RELATED. No corpus vector generation was available or added, so the
measured improvement below is lexical/graph/documentary, not embedding recall.
Explicit citation/reference crawling was not added; existing provenance lookup
and graph routes remain available.

## English operation and verification

Removed SpanishBackTranslator, language detection/cache, back-translation,
translation provisioning and language-specific response branches. Removed direct
dependencies ctranslate2, langid, sacremoses and subword-nmt, plus their unused
transitive packages from uv.lock. Existing operator model directories were not
deleted. Historical bilingual artifacts remain historical; the default
conversation evaluation is now questions_english_v2.json.

Retained the same pinned float32 ONNX NLI model at 0.92. Its multilingual
training is not a translation step. Fresh provisioning downloaded only the
existing model/configuration/tokenizer into task-owned temporary storage.
English queries have no translation call or language-specific retrieval gate.

Preserved evidence identity, exact source spans, original quantities/units,
subject/condition attribution, modality, comparisons, causal restraint, scope
checks and citation resolution. The NLI threshold was not lowered. Rejected
claims can still be repaired without erasing accepted claims. A deterministic
complete documentary identity path makes exact source excerpts usable without
NLI or an API key; it cannot verify changed wording, experimental applicability
or scientific assertions from DISCOVERY.

Sixteen English semantic controls passed using the actual pinned model,
including changed numbers/units, lost conditions, wrong subjects, simulation as
observation, objective as result, causal overstatement, unsupported absence,
term substitution and source instructions. See english-adversaries.json.
This is a small synthetic control set, not a hallucination-rate estimate.

Live generation still exposed false-negative risks: faithful-looking summaries
can be rejected by NLI, mixed source context can trigger modality checks, and
source/run identifiers absent from selected spans trigger numeric rejection.
Some rejections correctly caught unsupported attribution or relevance. These
were not independently adjudicated; no false-positive/false-negative percentage
is claimed. Source excerpts reduce empty answers, but broad free paraphrase
acceptance remains an open calibration problem.

## Recall evaluation

Reproduce with `uv run python scripts/evaluate_recall.py --output NEW.json`.
Questions, source-inspected judgments and receipts are in:

- `evals/phase56/recall_questions.json`: 24 English questions spanning the
  requested combustion, condition, methods, normative and exploratory domains.
- `evals/phase56/recall_qrels_v1.json`: 32 source judgments over 13 questions,
  with real evidence IDs, pages and rationales.
- `artifacts/hackathon_recall_v1/baseline.json`: compact pre-change receipt.
- `revised.json`: initial rank-fusion/source-diversity revision, retained.
- `revised-r2.json` and `coverage-summary.json`: final retrieval and contribution
  measurements, including per-question misses and truncation receipts.

Judgments were inspected against original indexed reports/catalogue records by
the implementation agent before revised measurement. They are provisional and
**not independently scientist-adjudicated**. They distinguish documentary
usefulness from exploratory catalogue relevance, not experimental equivalence.
Unjudged questions have no invented recall scores. Existing exact-condition and
adversarial regressions assess DIRECT/RELATED separately. Independent expanded
qrels covering all five relevance grades remain necessary.

Macro known-document coverage over the 13 source-inspected questions:

| Metric | Baseline | Revised |
| --- | ---: | ---: |
| Recall@10 | 75.51% | 85.64% |
| Recall@20 | 77.44% | 96.15% |
| Recall@50 | 86.41% | 96.15% |
| Recall@100 | 86.41% | 96.15% |
| Known source/question pairs missed in retained results | 6 | 1 |
| Explicit PSI investigation/question pairs recovered | 6/12 | 11/12 |
| Selected source-anchor passages recovered | 20/32 | 26/32 |

These are conditional known-source coverage metrics on an incomplete relevance
pool, not complete literature recall, scientific precision or generalization to
unseen investigations. Reports spanning several studies were not counted as
additional experiments. Baseline combined exposed passage ranks by BM25; revised
ranking uses fusion and diversity. Baseline display limit was already 100 for
this comparison, rather than the narrower production default of 12.

Previously missed catalogue registrations PSI-68 and PSI-69 were recovered for
droplet/extinction questions, and PSI-142 for extinction. They remain exploratory
where relevance/conditions are not established. The remaining known source miss
is PSI-62 for the broad diagnostics question: the record names tomography rather
than the query's generic terminology. Missing mappings and catalogue-only corpus
depth are more relevant here than increasing page size. No question-specific
synonyms or study routing were added to fix it.

Across 24 queries, 4,484 distinct candidate/query pairs were generated; 141
original-page duplicates were suppressed and 506 candidates fell beyond the
bounded pool, with explicit receipts. Lexical retrieval contributed 3,821 new
candidate/query pairs, focused lexical 110, approved aliases 147 and controlled
terminology 406, before deduplication. These contributions depend on execution
order; they are not independent strategy recall estimates.

Unjudged document/query pairs increased from 247 to 317. They cannot honestly be
called irrelevant without review; no precision improvement is claimed. Median
local search time increased from 424 ms to 533 ms, maximum from 1.71 s to 2.04 s
in this measurement. Coverage was prioritized over the small latency increase.

## Conversation, citations and API

The existing POST /api/v1/chat contract is preserved with additive
additional_candidates/retrieval metadata and a bounded continuation endpoint:
`GET /api/v1/conversations/{id}/candidates?offset=...&limit=...`.
Search adds candidates and per-category continuation offsets. Displayed,
retained, classified, support-context and summarized-evidence counts are separate.
Source lookup remains available independently of the main response.

Conversation focus now includes prior candidate metadata. Follow-ups can retain
older candidates as explicitly unverified for the current turn. An explicit
subject change clears old focus; source-guided retrieval coexists with expanded
searches. Candidate memory is bounded and expires with the session.

A separate model selection channel exposes authentic exploratory sources by ID.
The server renders real registry titles, an unverified-relevance notice and real
citations. Model-written scientific relationships cannot enter through this
channel. Proposed search directions remain a different, uncited suggestion type.
Final presentation deduplicates exploratory sources and shows at most three by
default; all retained candidates remain accessible. If no scientific prose is
accepted, useful exact excerpts are still offered alongside exploratory sources.

All seven predeclared turns of the five-turn extinction conversation plus novel
instrumentation/material questions were run twice; no favorable run was selected.
The interim run returned five generated explanations and two excerpt responses.
The retrieval/presentation revision run returned three generated explanations,
one excerpt response and three candidate-only responses before the final
presentation correction. Its 54 citation checks all resolved exact original
passages; all seven responses were DEGRADED because some generation was rejected.
Median latency was 39.73 s, maximum 61.63 s. Both transcripts, source receipts,
provider usage and verification decisions are retained.

The final display-only correction followed those observations: deduplicate
repeated investigation descriptions and avoid candidate-only responses when
useful documentary excerpts exist. It is covered by final focused regression
and a separate release HTTP/Nemotron probe, whose receipt is retained separately.
The full seven-turn live test was not repeated after that display-only correction.
HTTP/citation success is not scientific acceptance. The final acceptance scenario
is **not fully closed**: fluent useful explanation and precise condition-focused
follow-up remain uneven, particularly when NLI rejects all proposed prose.
No claim of complete scientific coverage or universal hallucination prevention
is made.

## Stability and reproduction

The final regression receipts, release HTTP probe, dependency checks and Git
state are recorded in the release checklist below. Existing 40 optional skips
were not added or increased to make the suite pass. Raw/snapshot inputs and the
historical evidence-registry checksum remain unchanged. No ontology vocabulary
or speculative relations were published.

Single-worker/process-local-session limitations remain. External dashboard
integration, independent scientific adjudication, semantic index provisioning,
reference crawling and broad live paraphrase calibration remain outside the
validated capabilities of this refinement.

### Release checklist

- Final actual HTTP/Nemotron instrumentation probe: HTTP 200, generated English
  explanation, two citations resolving exact source passages, 45.12 s; DEGRADED
  because other proposed statements were rejected. It described diagnostics and
  preserved reported quantities, but wording remained unnecessarily repetitive.
  This is a verified operational probe, not an independent scientific grade.
- `uv sync --locked`, `uv pip check`, compileall, Ruff and `git diff --check`
  passed. Eight translation-related packages were removed from the local locked
  environment. No replacement model or paid dependency was introduced.
- Real credential-free TCP/uvicorn smoke checks passed; additive OpenAPI was
  regenerated. The dashboard was untouched. There is no public claim streaming.
- Original snapshot/input/artifact hashes were verified; historical evidence
  bytes stayed unchanged. Source files were not rewritten to satisfy tests.
- Batched regression: **3,551 passed, 40 pre-existing skips, zero failed**.
  After the final display changes, all 31 affected conversation/retrieval tests
  passed again; 50 commit guard tests also passed. Repeated focused runs are not
  added to the full-suite count.
- Final test totals and commit identifiers are recorded in
  `artifacts/hackathon_recall_v1/release.json`. The full batch logs are retained
  beside the regression receipt. Counts exclude repeated focused runs.

Next scientific work should prioritize independently adjudicated relevance and
paraphrase sets, contextual ranking for generic diagnostics terminology, and
less repetitive condition-focused explanations. Broader retrieval is implemented
and measured; universally fluent, scientifically complete multi-turn research
is not established by this delivery.
