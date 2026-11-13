# NASA FIRE AI: instructions for development agents

Read this file, then `AGENTS.md` (immutable rules, which prevail), before changing anything. Then open the canonical record `artifacts/phase1_generalizable_ingestion/v6/milestone13/phase1_plan.md` and `CONTINUATION.md`, and continue at the first work package not done. Do not replan what is already decided.

## What NASA FIRE AI is

An end-to-end platform that turns official NASA research on microgravity combustion, flame behaviour, fire safety, materials, experimental conditions, suppression and *Flame in Freefall* into versioned, evidence-grounded scientific knowledge, and lets scientists consult it. It is not a generic document chatbot.

**Sources.** Only official NASA material and collaborations with verifiable NASA participation in this domain, with relevant terrestrial comparisons. The catalogue cutoff is October 2026.

**Two subsystems:**
- **Knowledge creation:** acquire and preserve originals; understand document structure; interpret experiments, measurements, observations and conclusions; reuse the ontology; stage justified extensions; validate independently; ask the scientist only when necessary.
- **Knowledge consultation:** natural-language questions over the KG and the original documents, DIRECT versus RELATED evidence, comparisons that keep conditions apart, historical and refuted status, and the original source always reachable.

## Six phases

Phases are functional milestones, not rigid walls.
1. **Generalizable scientific ingestion (current priority).** Heterogeneous NASA sources become isolated, evidence-anchored curation packages, with entities, relations, quantities, scope, uncertainty and staged semantic extensions.
2. **Autonomous curation and ontology evolution.** Reuse, compatible extension, minimal closed-form scientist questions, previews and corrections, and local confirmation.
3. **Workspaces, history and versioning.** Git-like baseline plus isolated deltas, attribution, rollback, and promotion by authorized developers only.
4. **NASA scientific library.** An inventoried 2026 corpus, processed incrementally with coverage denominators. Unexposed sources are reserved for evaluation.
5. **Research and consultation.** Evidence-grounded answers, comparison, dashboards, and the original viewer. System analysis is never presented as a NASA finding.
6. **Integrated product release.** Security, recovery, performance and an end-to-end demonstration, independent of NASA institutional infrastructure.

**Boundary between phases 1 and 2.** Phase 1 autonomously discovers, interprets, maps, validates and *stages* knowledge and the semantic extensions it needs. Phase 2 provides the scientist-facing clarification, correction and approval. Phase 1 must not stop at a concept Phase 2 will later review, and its outputs must not need remodelling for Phase 2.

## Strict science, adaptive knowledge

- **Immutable integrity contracts.** Never weaken these to raise recall: source identity, original bytes and expressions, experiment identity and applicability, values, units and qualifiers, epistemic roles, attribution, uncertainty, historical status, authorization, transactional integrity and version compatibility.
- **Adaptive semantic contracts:** classes, properties, quantities, relations, composition, configurations and new concepts. The approved ontology is the foundation, not a closed vocabulary. A closed enum in a transport schema or validator is never the only way to express a concept (mandate 2026-10-25 §6): the transport stays strict and versioned, the semantics stay extensible.
  - Each scientifically relevant concept resolves to exactly one of: reuse an approved equivalent; alias or terminology variant; instance of an approved class; characteristic of an existing instance; justified subclass; genuinely new class; new relation with documented meaning; unresolved classification preserved with its evidence. They are not interchangeable: a new characteristic is not a new class, an unknown term is not a new definition, a similar term is not an equivalent.
  - Never discard a source-supported concept only because the registry lacks it; stage it.
  - Never force an unsupported hierarchy placement; keep parent candidates for Phase 2.
  - Never auto-publish an extension into the approved baseline.
- **Scientific roles are facets, not a growing label list** (mandate §5 decision 1, §10): statement type, epistemic role, modality (actual, proposed, intended, conditional, hypothetical), execution status, temporal/historical scope, subject, applicability, attribution and verification are separate dimensions. The legacy statement and quantity roles stay valid as profiles over these facets, and old records and receipts load unchanged. Plans, goals, design and test criteria (reuse `fs:DesignCriterion`, `fs:TestCriterion`), target and proposed conditions are representable; a planned value is never an executed run, a criterion need not belong to an executed test, a cited result stays historical. The source must support the chosen facets.
- **Separate states, never interchangeable:** extraction completeness, scientific evidence validation, structural contract validity, semantic extension approval, and publication authorization (plus scientific review in Phase 2). Staging never publishes. A complete, source-supported, independently validated extraction that uses a *staged* class or property may count as correct Phase 1 extraction under a versioned evaluation protocol; an `UNRESOLVED`, incomplete, misattributed or merely retained (`documentary_context`) record does not.

## Limits of the LLM

The LLM may interpret language, compare concepts, construct candidate relations, propose extensions, recover context, flag uncertainty and draft questions.

It may not:
- invent NASA findings, values or conditions;
- turn hypotheses into observations, or calculations into measurements;
- invent causality, or change the scope of a conclusion;
- erase superseded knowledge, or treat model confidence as truth.

Every statement stays traceable to NASA evidence.

**The scientist** decides genuine scientific ambiguity and authorizes versions. Do not ask them about routine extraction, parsing or RDF/SHACL.

## No overfitting

Metrics measure implementation quality; they are not the objective. The targets are precision ≥ 0.95, fully correct recall ≥ 0.80, and 0 known critical false attributions in the adjudicated set.
- **Forbidden:**
  - paper-specific mappings, identifiers or answer dictionaries;
  - vocabulary tuned to one source;
  - validators that recognize benchmark values;
  - scorer or frozen-target changes.
- **Every new rule** is classified as general science, document structure or semantic with evidence. Record the source that motivated it and its effect on the other development sources, and add metamorphic and negative tests.
- **Development sources** (PTFE, LUCI, ignition, regulator, textiles) are regression material, not evidence of generalization.
- **Reporting:** distinguish revalidated saved outputs (replay) from fresh inference (live runs), report every predetermined run, and never pick the best generation.
- **Phase 1 closes** only on frozen, independent, heterogeneous evaluation (`docs/PHASE1_MASTER_DIRECTIVE.md` §19; mandate §5 decision 10): at least two genuinely independent unexposed investigations and about 60+ adjudicated objectives, all predetermined runs reported with lineage-aware uncertainty. Two consecutive passes on a development paper prove nothing; look at the run distribution. Never tune on a holdout and still call it unseen.
- **Evaluation protocol is versioned.** Frozen v4 targets, historical scores, runner configurations and adjudications are never rewritten. A justified target correction goes into a separately versioned set with rationale. Target finders recognize scientific equivalence but never credit a different subject, condition or role; a genuine scientific disagreement goes to independent review, not to the agent.
- **General modules are not overfitting.** A general formula extractor, table reconstructor, layout recovery or OCR fallback is legitimate; a rule for one paper's formula is not.

## Research mechanisms adopted (mandate §7, §8, §12, §17)

Only these three areas; inspect the real code and its license before reusing any.
- **SCION** (`github.com/wandugu/paper_scion`, Apache-2.0): evidence-linked candidate mining, separation of candidate generation from consolidation, normalization and deduplication, conservative reconciliation with the existing schema, malformed-output fallback, merge-decision traces. Integrated through `SemanticRegistry` and the existing staging, not as a second pipeline.
- **ODKE+** (arXiv 2509.04696): ontology snippets built dynamically per candidate entity from the ontology and `SemanticRegistry` (definitions, parents and children, inherited properties, compatible relations, endpoint types, aliases), plus missing-fact detection against the existing candidate inventory. Never a static hardcoded prompt; a second LLM's agreement is never proof.
- **Docling** (`github.com/docling-project/docling`, MIT): an optional specialist for formula glyphs, broken tables, reading order and image-only regions, routed only when ordinary extraction demonstrably failed, and adopted only with evidence that it recovers the real missing structure. Not a mandatory dependency and not a second source of truth; extracted values still pass attribution validation.

No second KG, no competing ontology registry, no multi-agent framework.

## How to work

- **Inspect before implementing.** Read the real code, contracts, tests and commits; reuse and repair at the real boundary. Do not duplicate parsers, registries, extraction engines, graph stores or orchestration.
- **Development assistants are not runtime dependencies.** NASA FIRE AI calls its own configured scientific providers.
  - NVIDIA is the default provider and stays available, with its configuration preserved.
  - `SCIENCE_PROVIDER=anthropic` with `claude-sonnet-5-5` is the preferred research-branch candidate for completing Phase 1 (mandate §5 decision 8). It is not the global production default; do not change that silently.
  - Before any independent holdout, freeze ONE documented model/provider configuration (model id, prompts, decoding, contracts, runtime settings). Do not repeat the Sonnet-versus-Opus pilot without a new causal reason.
- **Runs cost time and credits: two-track policy** (mandate §15, replaces the 2026-10-22 replay-before-live rule).
  - **Track A, replay and tests:** validators, post-output subject reconciliation, numeric parsing, contract compatibility, scoring, staging and publication safety. Never spend API calls where replay answers the question.
  - **Track B, fresh inference:** needed when a change alters what the model sees or produces (ontology context, candidate discovery, request construction, role instructions, missing-term detection, document recovery, retrieval, provider handling). Before a campaign: the change is integrated, offline regressions pass, and the campaign has a predefined scientific question, run count and cost.
  - **Diego authorizes every live campaign in writing** (one authorization may cover a defined series of runs). No paid services or new billing. Report every predeclared run, including failures; never run until a favorable score appears.
  - The per-run `--max-total-tokens` ceiling is a spending brake: a call that would pass it is not sent and is recorded as deferred. It never truncates scientific content inside a request, and must not be set so low that legitimate processing is incomplete.
- **Branch and commits.** Work only on `diego/research`; never `main`, no PR without request.
  - Commits as Diegomed11, with no assistant trailers.
  - LF endings, no Windows-only fixes.
  - Secrets only in `.env`, never printed or committed (receipts are scanned for `nvapi-` and `sk-ant-`). `ClaudeDiego/` is never committed.
  - Never modify the evaluator, frozen targets, global ontology baseline or source PDFs.
- **Work in small packages.** One logical commit each, tests and ruff green, pushed, and the canonical record plus `CONTINUATION.md` updated. A cut session then loses at most one package.

## Authoritative documents

- `AGENTS.md`: immutable repository rules.
- `docs/PHASE1_MASTER_DIRECTIVE.md`: Phase 1 master directive and its addendum (October 2026).
- `docs/PHASE1_ARCHITECTURAL_CORRECTION_MANDATE_2026-10-25.md`: the architectural correction mandate. It resolves the ten decisions of `milestone13/package4/liam/PROPOSAL_FOR_LIAM.md` (do not ask them again) and defines packages A–E (§18). Where it updates a dated operational rule of this file or the directive, it prevails; `AGENTS.md` still prevails over it.
- `docs/NASA_FIRE_AI_MASTER_PLAN_2026-10-14.pdf`: six-phase master plan. Its commits, models and status are historical; verify the real HEAD.
- `docs/architecture.md` and `docs/PHASE1_GENERALIZABLE_SCIENTIFIC_INGESTION.md`: architecture and the Phase 1 report.
- `artifacts/phase1_generalizable_ingestion/v6/milestone13/phase1_plan.md`: **the single canonical record** of requirements, state, evidence and next action.
- `CONTINUATION.md`: where the last session stopped.

## Phase 1 state (2026-10-29)

DRAFT 1.4c, for review. Standing rules learned in phase 1; they add to the sections above and do not replace them.

- **B8 before every commit.** Run the four guard files (`tests/test_prompt_has_no_source_phrases.py`, `tests/test_new_prompt_text_b8.py`, `tests/test_redo_clause_b8.py`, `tests/test_redo_subject_b8.py`). No comment, docstring, test, receipt or prompt string may share a phrase with a frozen target quote or a development document beyond what existing receipts already quote; use invented values and words in tests. Never run them on a `known_fail` state.
- **Full suite before any push, in the main repo.** 0 failed, no allowance. A worktree lacks ignored local data, so judge the suite only in the main repo, from a saved pytest output (never pipe pytest into a push).
- **One function per concern.** A rule is one named function behind one flag, classified (general science, document structure or semantic) with its motivating source and its effect on the other sources; no second pipeline, no rule that mixes two concerns.
- **Flags.** A new behaviour is off by default. Track A flags (replay only) go on by default in their own commit with a receipt (the replay status changes against the previous replay, judged blind) after their gate; reason-only changes are listed in the receipt too. Track B flags (they change what the model sees) are measured in a campaign first. A flag found useless is pruned with its receipt kept; Family 2 stays OFF in code as an exception to "a flag ends ON or is pruned", allowed only because it is a requirement of the 3.2 freeze; before the freeze it either goes ON or is pruned. Suite rule: no xfail or skip is added to get green; open families are tested OFF, and their ON results live in their branch receipts. The single locator (one function, work on tmp-locator) covers all its users: the evidence validator, ORIGIN, family 1 and the caption check of S5. Before the 3.2 freeze everything not in the frozen configuration is removed. `campaign/PHASE2_CAMPAIGN_CONFIG.md` lists the flags by state; SCIENCE_VALUE_ORIGIN_MARK is on in the campaign and `tests/test_campaign_config_origin_mark.py` fails if it is off.
- **Role literals.** A module outside `scientific_facets.py` reads a role through a constant of that module (`PROVENANCE_ROLE`, `DOCUMENTARY_ROLE`), never a new quoted role name; the allowance in `tests/test_role_dictionary.py` is not raised.
- **Blind judging with the full sentence.** A judge of a changed record sees the full printed sentence and not the verdict, the rule or the expected answer; any record whose verdict conflicts with another is judged again blind before a default goes on.
- **No harness or criterion changes to get green.** Never change the scorer, the frozen targets, a stop criterion or an acceptance test to make a result pass; a failed criterion is reported and the rule stays off or is pruned.
- **Windows hold only.** A window designed to hold never feeds a veto that rejects or downgrades (the pruned family 2 window variant lost 42 credited textiles targets that way).
- **Cited values.** The gap of cited attribution blocks the 3.2 freeze; its conditions are in `campaign/PHASE2_CAMPAIGN_CONFIG.md` (F5). A surname of the reference list anchors a cited value (N1): as the subject of a finite verb, before et al., and colleagues, a year in parentheses, a bracketed number, or as a possessive; a surname also printed in lowercase needs an explicit signal at the sentence start.
- **Trim residual.** The slow trim invariant tolerates exactly 14 quantity trims that cross a printed line break (`phase1/trim_residual/QUANTITIES_TOLERATED.json`, listed case by case; entities and relations have no tolerance). This residual is a path by which a trimmed model quote can end up SUPPORTED; it is closed with the layout piece before the freeze.
- **Verdict versions.** Verdict files are versioned, never overwritten (`phase1/verdicts_v2/`); a metric reports the gate version and the earlier one alongside.
