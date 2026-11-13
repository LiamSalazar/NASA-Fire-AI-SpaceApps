# Handoff: everything since Sunday 2026-10-18, for a new agent

Written 2026-10-22 at HEAD `10692ba`, branch `diego/research`. Read this first, then `AGENTS.md` (immutable rules, which prevail), `CLAUDE.md` (vision and working rules), `CONTINUATION.md` and the canonical record `artifacts/phase1_generalizable_ingestion/v6/milestone13/phase1_plan.md`. Do not replan what those files already decide.

## 1. The project in five lines

- NASA FIRE AI turns official NASA microgravity-combustion and fire-safety documents into evidence-anchored scientific knowledge (entities, relations, quantities, statements, staged ontology extensions). Every statement must stay traceable to the printed source.
- Six phases; we are in **Phase 1, generalizable scientific ingestion**, which is **not closed** (`PHASE1_COMPLETE=NO`).
- Main code: `src/nasa_fire_ai/ingestion/document_extraction.py` (~8,900 lines: windows, model stages, validation, recovery, orchestration), `src/nasa_fire_ai/ingestion/proposal_states.py`, `src/nasa_fire_ai/llm/scientific_provider.py` (NVIDIA transport) and `anthropic_provider.py`, `src/nasa_fire_ai/services/curation.py`.
- Development sources (regression material only, never proof of generalization): PTFE, ignition, regulator, textiles (and LUCI). Each has frozen v4 targets: PTFE 34, ignition 29, regulator 32, textiles 29.
- Phase 1 closes only on frozen, independent, heterogeneous evaluation (`docs/PHASE1_MASTER_DIRECTIVE.md` §19), ending with the holdout NTRS 20170004702, still **not acquired** on purpose.

## 2. Rules you must follow (non-negotiable)

- Work only on `diego/research`. Never `main`. No PR unless asked.
- Commits authored `Diegomed11 <diegomad473@gmail.com>`, **no assistant trailers**, LF endings (`git ls-files --eol` before committing; `core.autocrlf=false`).
- `PYTHONUTF8=1` on Windows. `uv sync`, `uv run ruff format --check src tests`, `uv run ruff check src tests`, `uv run pytest -q`.
- **Full pytest before every push, 0 failed, read from a saved output file** (never `pytest | tail && git push`). Current count: **954 passed**. Run it in the main checkout: it needs ignored local data (`data/index/*.sqlite`, `artifacts/phase3c_*`).
- Secrets only in `.env`; never print or commit them. Before committing receipts scan for `nvapi-`, `sk-ant-`, `req_` and provider account identifiers. Never commit `.env`, `ClaudeDiego/`, sqlite files, PDFs or zips.
- **No live model runs** (NVIDIA or Anthropic). Diego, 2026-10-22: no more live runs until the **replay** meets recall ≥ 0.80 and precision ≥ 0.95 per source with 0 critical errors; then a run is only proposed, and needs Diego's written authorization. Measure with pytest, unit/metamorphic/negative tests and offline replays (0 model calls).
- NVIDIA stays the default provider and must keep working. `SCIENCE_PROVIDER=anthropic` with `claude-sonnet-5-5` is the development model. Do not change the production model or provider (Liam decides).
- Never modify the scorer, the frozen targets, the global ontology baseline or source PDFs.
- **No overfitting:** no paper-specific mappings, identifiers, vocabularies or benchmark-value validators. Every new rule is classified (general science, document structure, or semantic with evidence), records the source that motivated it and its effect on the other sources, and gets metamorphic and negative tests. Mark single-source rules "single-source, suspect".
- Report replay (revalidated saved outputs) apart from live runs; report every run, never pick the best one.
- Small packages: one logical commit each, tests and ruff green, pushed, and `phase1_plan.md` plus `CONTINUATION.md` updated.

## 3. What happened since Sunday (≈155 commits)

### Oct 18–20: v6 milestones 1–8 (rules by printed structure)
Many document-structure and semantic rules, each replayed on all sources: staged properties only when the print names the value; holds for validity caveats, background/theory text, instruments typed as interventions, labels that are values; proposals from printed table structure (groups, materials, specimens, batch groups); prose-value recovery from sentence, pronoun and table; a targeted quantity-recovery stage before relationships; lab units (litre, ft³, ft²); setpoint/nominal/target values as settings; values in a group's own subsection. Receipts in `artifacts/phase1_generalizable_ingestion/v6/milestone1..8/`. Holdout registered before acquisition (`v6/holdout_registration/`).

### Oct 20–21: milestones 9–13 (live evaluation B on NVIDIA, adjudication)
- Record-by-record precision reviews, provider-failure analysis, rejection audits, adjudicated targets (`milestone9..12/`).
- Milestone 13 (`v6/milestone13/`): evaluation B round at `b4be17d`; the miss diagnosis of 104 target-run pairs: rejected by a rule 66 %, accepted but graded wrong 21 %, not proposed 12 %, window lost 0.
- Orchestration: per-document recomputation once (`ae420ab`), timing summaries (`ae642ed`), **window prefetch** with `SCIENCE_WINDOW_CONCURRENCY` (default 3; `3e746b1`), validation reuse by digest (`24f09e3`), duplicate folding (`4b189de`).
- **Anthropic transport** (`09bef51`), chosen only by `SCIENCE_PROVIDER=anthropic`; token ceiling `--max-total-tokens` as a **spending brake** (a call that would pass it is not sent and is recorded `DEFERRED_BUDGET`; it never truncates content).
- Pilot: Sonnet 5.5 vs Opus 5.5 → Sonnet kept as the development model (`milestone13/pilot_anthropic/`).

### Oct 21–22: the milestone 13 work packages (`phase1_plan.md` table)
- **0.x** persistence: `CLAUDE.md`, `docs/PHASE1_MASTER_DIRECTIVE.md`, master plan PDF, canonical record, `CONTINUATION.md`.
- **1.1** capability table (`capabilities.md`); **1.2** classification of the 69 rejected pairs: A 19 must stay rejected, B 20 contract too rigid, C 30 incomplete association; **1.3** the scorer does not require global publication.
- **2.1a–d, 2.2, 2.3** ontology evolution: one proposal state per record; staged class/relation extension proposals; the model request may propose a new class or relation through sentinels `PROPOSE_NEW_CLASS` / `PROPOSE_NEW_RELATION` with an approved parent (staged, never approved); isolated structural validation; proposed-extension items kept in the package; reuse analysis (reuse, subclass vs attribute, qualified vs new relation, instance vs class).
- **3.1–3.5** precision/recall by structure: setting verb names a value; slide-deck sections and scope; "prior to <verb>" is a procedure; units printed apart from values (inch marks, spanning headers, `%` glued to a symbol); running page headers cut off; materials only mentioned outside own research are held; group scope fallback (3.2b). 3.5: the targeted recovery already offers the missed values; the limit is subject eligibility (immutable applicability contract).
- **Point A** (replay, 0 calls): PTFE 28/34; 29 historical negatives 0 critical; the §13 gate is not met.
- **Package 4**: three live Sonnet rounds, 6.12 USD. Round 1 at `dc6f342` exposed a schema defect (undefined `ProposedTerm`, every identity request HTTP 400), fixed in `a6d967b`. Recall PTFE 28, ignition 12–13, regulator 8–9, textiles 10.
- **Block 3b** fixes (`package4/fixes.md`): 1 series named in captions as group candidates (`aae1ef9`), 2 running footer closes a sentence (`9e9a9b1`), 3 setting verb as staged name, restricted (`544fddd`, `ced629a`), 5 brake releases a provably unsent request (`d48fa0e`, `7aba3f3`). Fixes 4 (A × B dimensions) and 6 (math-font glyphs) not done, with reasons. Fix 7 waits for Liam.
- B8: a prompt example nearly copied a frozen ignition quote; replaced (`8801aa2`), guarded by `tests/test_prompt_has_no_source_phrases.py`.
- Corrected miss diagnosis (`9af6a50`), feasibility table (`package4/feasibility/`), statement role card in the propositions request (on); admissible-subject menu (off: fails the PTFE prejudgment, `07d01f6`).
- Anthropic request limit 96,000 estimated tokens (`5c4676b`), `max_tokens` floor 32,768 (`5951f75`), ceiling 131,072 and frozen-configuration check (`effcb21`).
- **Package 5** (`milestone13/package5/README.md`): two live Sonnet rounds at `07709c0`, 4.23 USD. Recall PTFE 28/34 both; ignition 9 and 16/29; regulator 15/32 both; textiles 11 and 12/29. Pooled recall 0.51 / 0.57, precision 0.925 / 0.938, **0 critical**. 0 splits, 0 deferrals.
- Heading outline letter not part of an entity's name (`65acb94`, from ignition round 1).
- **Spending brake vs prefetch** (today, all network-free tests in `tests/test_prefetch_brake.py`, `test_discarded_prefetch.py`, `test_prefetch_make_room.py`, `test_window_prefetch.py`):
  - `824af5f`: requests sent ahead obey the brake and are counted when sent (before, concurrency 3 could bill 720k under a 30k brake).
  - `4ba8a23`: `make_room` — before the brake refuses a foreground request, cancel requests sent ahead that have not left, count finished ones at billed usage, wait for those in flight; `ahead_reserved` holds each one's current count.
  - `10692ba`: `never_billed(error)` (a 400 `request_rejected`, or `network` with `request_not_sent`) is the single rule; a request sent ahead that failed unbilled releases its reservation in `make_room`; the foreground releases `counted`, so nothing is released twice. With a brake that fits the run's billing plus its largest reservation, concurrency 3 decides exactly as concurrency 1.
- Spend so far: Anthropic $14.03 of the monthly $100 (pilot 3.68 + package 4 6.12 + package 5 4.23).

## 4. Where things stand

- **Gate not met.** Only PTFE reaches recall ≥ 0.80. Ignition 0.31–0.55, regulator 0.47, textiles 0.38–0.41. Precision pooled ~0.93. 0 critical errors in every run.
- Feasibility (`package4/feasibility/feasibility.md`): textiles cannot reach 24/29 whatever rules or model do until Liam decides items (a), (c), (d) below. Ignition and regulator have room only by combining validator and request changes.
- No runs in progress. Worktree `../nasa-p21` is idle (detached at `dfc05f1`); ignore it.

## 5. Waiting on Liam (do not implement until he decides)

Full text: `artifacts/phase1_generalizable_ingestion/v6/milestone13/package4/liam/PROPOSAL_FOR_LIAM.md`.
- (a) New roles: statement roles for plans/goals; quantity roles for criteria and targets; and whether a correct but staged record counts for recall.
- (b) Fix 7: a test article named by its acronym (POR) identifies the one specimen; touches the immutable applicability contract; risk of a false attribution measured.
- (c) Whether a `documentary_context` record with the exact sentence satisfies a target whose role does not exist yet.
- (d) Three contracts the frozen targets contradict (textiles statements-18, -19, quantities-05..07): relax, change target, or accept as known misses.
- (e) Review and freeze the draft target finders for ignition, regulator, textiles (`finders_draft.json`).
- (h) `hasComponent` review; whether "was set to" names a value; Sonnet as primary model; 2.1b sentinels (never used in 20 live runs: keep inert, redesign, or remove).
- Notice B8 applies to ignition runs since 2026-10-21.

## 6. What you can do next without Liam and without runs

From `phase1_plan.md` "Detected and not yet addressed" and `CONTINUATION.md`:
- Replay-measured general fixes for ignition/regulator rejections (largest miss cause): use `package4/target_miss_diagnosis.md` and `feasibility/`.
- Regulator wet series merged into one group by the model: a structure-based split candidate.
- Group restatements and planned procedures typed as executed groups (3.4 pending part).
- Each change: rule classification, motivating source, replay on all sources (`review_tools/replay_all.sh`, `diff_all.py`, `exposed_compare.py`), the 29 historical negatives with 0 critical, PTFE ≥ 28/34 with the official scorer (`scripts/score_scientific_review.py`), tests, then record it in `package4/fixes.md` (or a new package folder), `phase1_plan.md` and `CONTINUATION.md`.
- Offline replay: `uv run python scripts/phase1_offline_replay.py <prepared.json.gz> --output <new dir>`.
- Package 6 (stability, leave-one-source-out, freeze, holdout) is **not** to be started.
