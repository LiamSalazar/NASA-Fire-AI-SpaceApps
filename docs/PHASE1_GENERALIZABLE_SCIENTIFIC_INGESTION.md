# Phase 1 scientific ingestion: v6 milestones 9–13, pilot, orchestration and point A on `diego/research`

**PHASE1_COMPLETE = NO.**
- The §13 gate is not met: recall ≥ 0.80 is reached only on PTFE.
- The registered holdout (NTRS 20170004702) has not been acquired.
- Code at point A: `377e013`, plus 2.1b (`c0acb35`), which changes only the model request. Package 4 live rounds: `dc6f342` and `a6d967b` (schema fix).

**Canonical record:** `artifacts/phase1_generalizable_ingestion/v6/milestone13/phase1_plan.md`.
**Receipts:**
- `v6/milestone9`–`milestone12/README.md`;
- `milestone13/README.md`, `point_a.md`, `point_a/phase1_metrics.json` (built by `milestone13/tools/phase1_metrics.py`);
- `pilot_anthropic/`, `evaluation_b.json`, `adjudication.json`, `target_miss_diagnosis.md`, `rejected_classification.md`, `capabilities.md`, `scorer_review.md`.

## What changed since milestone 8

- **Milestones 9–12** (NVIDIA live rounds and their corrections):
  - evaluation B on the four development investigations;
  - provider fallback and quantity validation;
  - the two critical paths found in evaluation B, closed;
  - printed structure settles a specimen line, a series' class and an unknown study.
  Each milestone README lists its rules and receipts.
- **Milestone 13, block 0–1:**
  - the directive and master plan saved in the repo, plus `CLAUDE.md`;
  - the capability table;
  - the 69 rejected target-run pairs classified (A must stay rejected 19, B contract too rigid 20, C incomplete association 30);
  - the scorer review: no publication requirement.
- **Block 2 (adaptive semantics):**
  - one proposal state per record;
  - staged class, statement-class and relation proposals with isolated structural validation, reuse analysis (cases A–C) and placement;
  - proposed-extension items kept in the package;
  - review and publication states derived from curation.
  - 2.1b: the model request may now propose a term the vocabulary lacks, with an approved parent; it is staged and never approved.
- **Block 3 (validation rigidity and precision by structure):**
  - quantity names from the printed setting verb;
  - a slide's own title is its section;
  - "prior to" a step orders a procedure;
  - units printed apart from values (inch marks, multirow table headers, percent glued to the quantity symbol);
  - running page headers cut off whole sentences;
  - materials only mentioned outside the study's own research are held;
  - a supported group the passage does not belong to scopes it to the study, never a run;
  - set-up and planned steps are not observations.
  Each rule is classified, has its motivating source and its effect on the other sources, and has metamorphic and negative tests.
- **Model pilot and orchestration:**
  - `claude-sonnet-5-5` is the development model (`pilot_anthropic/README.md`); Opus gave +1 target at 2.4–3× the cost.
  - Per-document memo, window prefetch, validation reuse, per-call timing.
  - A token ceiling that defers calls and never truncates.
  - Local validation time per source fell to 6–42 s.
  - NVIDIA stays the default provider; changing the primary model waits for Liam.

## The nine §11 metrics at point A

All of these are evaluation A: saved outputs revalidated with 0 model calls. They are development sources, so the figures measure regressions, not generalization (§12, §19).
- PTFE is scored by the official scorer.
- The other sources use the round B adjudication plus the point A judgments (`point_a.md`).
- 95 % Wilson intervals. UNRESOLVED never counts as recovered.

| source | recall | precision | evidence retention | unresolved | correctly unresolved | omissions | critical |
|---|---|---|---|---|---|---|---|
| ptfe | 28/34 = 0.82 [0.67, 0.92] | 134/136 = 0.98 [0.95, 1.00] | 32/34 = 0.94 [0.81, 0.98] | 4/34 = 0.12 [0.05, 0.27] | 1/34 = 0.03 [0.01, 0.15] | 2/34 = 0.06 [0.02, 0.19] | 0 |
| ignition | 16/29 = 0.55 [0.38, 0.72] | 86/114 = 0.75 [0.67, 0.82] | 22/29 = 0.76 [0.58, 0.88] | 6/29 = 0.21 [0.10, 0.38] | — | 2/29 = 0.07 [0.02, 0.22] | 0 |
| regulator | 11/32 = 0.34 [0.20, 0.52] | 21/30 = 0.70 [0.52, 0.83] | 20/32 = 0.62 [0.45, 0.77] | 9/32 = 0.28 [0.16, 0.45] | — | 2/32 = 0.06 [0.02, 0.20] | 0 |
| textiles | 8/29 = 0.28 [0.15, 0.46] | 19/23 = 0.83 [0.63, 0.93] | 13/29 = 0.45 [0.28, 0.62] | 5/29 = 0.17 [0.08, 0.34] | — | 4/29 = 0.14 [0.06, 0.31] | 0 |
| pooled | 63/124 = 0.51 [0.42, 0.59] | 260/303 = 0.86 [0.81, 0.89] | 87/124 = 0.70 [0.62, 0.78] | | | 10/124 = 0.08 [0.04, 0.14] | 0 |

Correctly unresolved (a hold judged the right outcome) is assessed only in the PTFE review.

**Recall by scientific category** (all four sources, accessible targets):

| category | recall |
|---|---|
| entities | 19/22 = 0.86 [0.67, 0.95] |
| quantities | 18/46 = 0.39 [0.26, 0.54] |
| statements | 20/44 = 0.46 [0.32, 0.60] |
| relations | 6/12 = 0.50 [0.25, 0.75] |

**Run-to-run variability** (milestone 12 live rounds, same code, two runs per source):

| source | r1 | r2 |
|---|---|---|
| ignition | 11/29 | 14/29 |
| regulator | 14/32 | 17/32 |
| textiles | 10/29 | 10/29 |
| ptfe | 27/34 | 28/34 |

Round B, on later code (`b4be17d`), gave regulator 10/32 and textiles 7/29. Across live rounds a source has therefore varied by up to 7 targets, part of it from code changes and part from the model, so one run is not a measurement of stability.

## Reading

- Precision rose on every source in block 3: pooled 0.86. Recall is the bottleneck: pooled 0.51 [0.42, 0.59].
- Quantities and statements are the weakest categories.
- Of the target-run misses in milestone 12 (`target_miss_diagnosis.md`):
  - 66 % were rejected by a rule; block 3 addressed the class B and C ones that are general;
  - 21 % were accepted but graded wrong;
  - 12 % were never proposed.
- The narrative values the model omits are already offered by the targeted recovery call. They lack an eligible experimental subject (historical missions, assessment targets), and only a staged class can supply one (2.1b).
- The §13 gate, then leave-one-source-out and the frozen holdout (§19) remain.

## Package 4: live Sonnet rounds (evaluation B)

Fresh live inference with `claude-sonnet-5-5` on the four sources (`milestone13/package4/README.md`). Each round is reported apart, none is selected, and none is comparable to the point A replay as a gain or loss of rules.

- **Round 1 at `dc6f342` exposed a defect.** The 2.1b schema referenced `ProposedTerm` without defining it, so Anthropic refused every identity request. The refusals' token reservations then deferred windows unsent. Fixed in `a6d967b`.

| source | `dc6f342` r1 | `a6d967b` r1 | `a6d967b` r2 |
|---|---|---|---|
| PTFE (official scorer) | 25/34, 90/92 | 28/34, 100/101 | 28/34, 117/119 |
| ignition | 10/29, 32/42 | 13/29, 71/85 | 12/29, 63/76 |
| regulator | 9/32, 32/33 | 9/32, 31/34 | 8/32, 29/36 |
| textiles | 10/29, 17/24 | 10/29, 20/22 | 10/29, 20/27 |
| pooled recall | 0.435 [0.35, 0.52] | 0.48 [0.40, 0.57] | 0.47 [0.38, 0.56] |
| pooled precision | 0.90 [0.84, 0.93] | 0.92 [0.88, 0.95] | 0.89 [0.84, 0.92] |
| critical | 0 | 0 | 0 |
| cost | 1.66 USD | 2.28 USD | 2.17 USD |

- **2.1b:** in 12 live runs the model never used the new-term sentinels, so nothing was staged through it.
- **The gate is still not met.** Only PTFE reaches recall ≥ 0.80.
- **Remaining variation on the same code** comes from the model and the network:
  - an ignition window deferred under the token brake after two network failures;
  - regulator's wet series merged into one group;
  - more textiles slide bullets typed as documentary context.
- The nine metrics per round, with every interval, are in `package4/phase1_metrics_*.json` (`phase1_metrics.py --round`).

# Phase 1 scientific ingestion — v6 milestone 8 on `diego/research` (candidates from document structure, under the generalization addendum)

**PHASE1_COMPLETE = NO.** Receipts: `artifacts/phase1_generalizable_ingestion/v6/milestone8/`. Code `d7c4732`.

Three document-structure mechanisms, each classified per Liam's generalization addendum (§2) and checked on the four development sources by offline revalidation of the saved live outputs (evaluation A; no fresh inference in this milestone):
- a condition printed as a setting ("exposed to …", "to achieve …", "at …") inside a group's own subsection is that group's condition, unless the sentence names another group;
- a configuration value printed in a method section outside every group's subsection configures the document's investigation;
- "<thing> tested at <settings>" proposes the thing as a specimen with its settings.

| Source | Accepted records `2f343b8` → `d7c4732` | Frozen targets provisionally reached (author's adjudication pending) |
| --- | --- | --- |
| Lunar ignition | 105 → 109, none removed | q-05, rel-26, rel-27 |
| Oxygen regulator | 74 → 75, none removed | q-08 |
| Textiles | 23 → 27, none removed | ent-04, q-14, q-15 |
| PTFE, 12 reviewed runs | +2 model-proposed method values in runs 1, 4, 5, 6; none removed | no target change |

Metamorphic (rewrapped lines) and negative (other specimen, other group, other gravity condition, incidental mention) tests exercise the production readers. The rejection audit (`rejection_audit_d7c4732.json`) separates what the model proposed from what printed-structure candidates added; the next mechanism must start from that audit, giving the model each entity's class and subsection scope, rather than from new readers.

The development gate is still not met, and the registered holdout (NTRS 20170004702) was not acquired.

# Phase 1 scientific ingestion — v6 milestone 7 on `diego/research` (several development investigations)

**PHASE1_COMPLETE = NO.** Receipts: `artifacts/phase1_generalizable_ingestion/v6/milestone7/`.

Live runs with frozen code on the lunar ignition, oxygen regulator and textiles investigations, scored against their frozen v4 targets.

| Source | Frozen code | Milestone-7 code (`031f5ab`) |
| --- | --- | --- |
| Lunar ignition | 6/29 | 10/29 |
| Oxygen regulator | 11/32 | 18/32 |
| Textiles | 5/29 | 8/29 |
| PTFE | — | 27–28/34 at 0.98–1.00 precision |

What changed, all checked on every source:
- the structure reader handles unnumbered major headings, slide titles, section-heading group names and acronym forms;
- more units, name syntaxes and unit-named pressure settings;
- three critical attribution errors fixed (relative clauses, printed differences, slide lines);
- more criteria, definitions, plot keys, fragments, apparatus and section titles held;
- group materials and the tested specimen recovered as relations.

The development gate is not met, and the registered holdout (NTRS 20170004702) was not acquired.

# Phase 1 scientific ingestion — v6 milestone 6 on `diego/research` (material composition, staged)

**PHASE1_COMPLETE = NO.** Receipts: `artifacts/phase1_generalizable_ingestion/v6/milestone6/`.

- The approved ontology has no material-to-constituent relation. `madeOf` relates samples and runs to their material, and the model can only propose registered relations.
- A generic reader of composition wording (`ingestion/composition.py`) stages one component assertion per constituent:
  - a candidate `hasComponent` relation;
  - the component's documented role as a characteristic of that assertion;
  - its documented share, with the basis only when stated;
  - the context of nested components;
  - the literal evidence.
- The missing relation is proposed as vocabulary for ontology review, never activated, and preparation stages everything as pending candidates.
- Explanations are rendered from the structured assertions.
- On PTFE, the same seven assertions (Salox-M® with 40% Bronze as filler and 60% PTFE; the Bronze of Salox-M® as 90/8/2% Copper/Tin/Zinc; Brass-filled PTFE with Brass as filler, share not known) come out of every reviewed run. The other sources produce none.
- The evaluator is unchanged, so targets 18 and 33 stay uncredited until the vocabulary and the reviewed representation are approved.

# Phase 1 scientific ingestion — v6 milestone 5 on `diego/research` (precision rules; frozen-code confirmations)

**PHASE1_COMPLETE = NO.** Receipts: `artifacts/phase1_generalizable_ingestion/v6/milestone5/`.

What changed:
- The errors that recurred in the reviewed runs are now held:
  - test media typed as materials;
  - cited work continued by "the same …";
  - procedures, criteria and data sources typed as interpretations or conclusions;
  - generic specimen descriptions;
  - conditions named only in cited work;
  - instrument readouts typed as observations;
  - statements that carry a running page header.
- A value binds to a subject only within its own contrast clause. This fixed a critical attribution.
- The printed structure now proposes, for the same validator:
  - the batch groups;
  - their relations;
  - a tested material's own table cells.
- Statements held only for their role or scope are revalidated with the role their wording states.

Results:
- **Twelve reviewed PTFE runs at `77828b9`:** recall 25–28/34, precision 0.978–1.000, 0 critical.
- **The two live runs made with frozen code** did not reach the bar: 24/34 at 0.934 and 18/34 at 0.900.

Consecutive PTFE runs are a stability check, not the closure criterion. Closure still requires stable recovery on several development investigations, then a prospective independent evaluation on an unexposed NASA lineage with frozen code.

# Phase 1 scientific ingestion — v6 milestone 4 on `diego/research` (recall from the printed structure)

**PHASE1_COMPLETE = NO.** Receipts: `artifacts/phase1_generalizable_ingestion/v6/milestone4/`.

- **Starting point.** A per-target table across the reviewed PTFE runs showed that the most often missed targets are printed deterministically by the document.
- **What the pipeline now takes from the print.** These are proposed as printed-structure candidates and validated like model proposals:
  - the specimen collection;
  - the conditions printed in its rows;
  - a value applied in a test step that the subject's own table prints under a column;
  - a standard-deviation column;
  - a sample "discussed in this paper".
- **Recovery rules.**
  - A statement held only for a role the validator detects otherwise is revalidated with that role.
  - A setting-versus-result conflict on a cell is settled by its column's state word.
  - A printed group of a material proposed as a material is revalidated as its specimen group.
  - Relations now run after the targeted recovery.
- **New holds.** Recovery never moves a value onto a condition or onto a table cell without row binding, and a reported cell of a column the document applies is a setting.
- **Two live runs with this pipeline.** 28/34 (0.82) at precision 0.97 and 27/34 (0.79) at precision 0.91, 0 critical.
- **The six earlier runs replayed.** 24–28/34, precision 0.96–0.99.
- **What remains.** Precision in every run, stability of the statement targets, and an approved material-component relation for the Salox-M® composition and filler. The §14 holdout comes only after that.

# Phase 1 scientific ingestion — v6 milestone 1 on `diego/research` (quantities and subjects)

**PHASE1_COMPLETE = NO.** This section adds milestone 1 of the consolidated mandate (work packages A and B) on top of the v5 closure below, which is unchanged. Receipts: `artifacts/phase1_generalizable_ingestion/v6/milestone1/` (README, CHECKPOINT, replays, reviews, metrics, exposed-source comparison, historical negatives).

## What the validation path does now (`ingestion/document_extraction.py`, `normalization/units.py`)

- **Units and dimensions.** `units.interpret` reports the dimension, canonical unit and, for pressure, the reference (`psia` absolute, `psig` gauge and never absolute, `psi` unspecified); °C and °F convert with their offset; J, ft-lbf, cal/g and inches are linear. A unit never implies a property.
- **Approved properties.** A label made of an approved alias plus state modifiers (`initial`, `final`, `test`, `system`, `chamber`, …) reuses that property with status `CANONICAL_STATE_QUALIFIED`; any other modifier leaves it unknown.
- **Unknown properties.** A bound source value whose property is not approved stays `SOURCE_SUPPORTED` with `mapping.kind = staged_property_proposal` (term, dimension, units, subject class, evidence, same-dimension approved properties as leads, `activation: NONE`). Curation projects only approved properties, so a staged one never enters the isolated store as a value. Staging needs printed name–value syntax; otherwise the value is held as before.
- **Subjects.** `validate_quantity` revalidates a rejected subject (`QUANTITY_SUBJECT_NOT_IN_APPLICABLE_SOURCE`, `QUANTITY_LOCAL_SUBJECT_BINDING_UNRESOLVED`) with the full validator against every other source-supported experimental subject, never the Investigation; one survivor is adopted with `subject_recovery`, otherwise the value is kept `UNRESOLVED` with `subject = None` and the alternatives. A current-study table row (no cited lineage) that names a material scopes its value to the material as tested in this investigation (`general_material_property: False`).
- **Roles.** The configuration/derived cue of a prose value is read in the value's own sentence; standard deviations are dispersion statistics; one printed value accepted under two roles is held; exact duplicates are consolidated.

## Measured (offline replay, 0 model calls, 36 frozen PTFE targets, 34 accessible)

| Run | v5 (`0ade8f1`) | v6 M1 (`b5cc4d8`) | Approved-property only | Precision | Critical |
| --- | --- | --- | --- | --- | --- |
| First live run | 17/34 | 21/34 = 0.62 | 19/34 | 87/88 | 0 |
| Second live run | 18/34 | 22/34 = 0.65 | 20/34 | 70/71 | 0 |
| Fourth live run | 14/34 | 18/34 = 0.53 | 16/34 | 65/66 | 0 |

Targets 9 (1332 cal/gram), 11 (AIT `>425` °C as a bound), 12 and 13 (1500 / 2268 psia) are newly correct in every run. LUCI gains 9 correct staged quantities; ignition, regulator, textiles and the v4 PTFE package have no new supported quantity; the 29 historical negatives show 0 critical regressions. Recall stays below 0.80: the narrative values (targets 14–18), the omitted specimen entity and relations, and several held statements are milestone 2.

## Milestone 2, part 1 (`v6/milestone2/`)

The fifth live run (`29aead3`, 17 calls, 1,208 s, `PARTIAL_MODEL_COVERAGE`, 0 approvals) scores 17/34 = 0.50 with precision 69/77 as produced. It typed Algoflon® E2/F7 and Salox-M® as cited, although their Table 3 rows are MSFC tests, and Kel-F® 81 as current, although it is printed only in cited rows. A material whose printed rows contradict its study label is now held in both directions (`8bc0d04`), and a validity caveat typed as a configuration is held (`2a64310`). At `2a64310` the run scores 17/34 with precision 69/72 = 0.96 and 0 critical. The remaining gap is the model's repeated omission of the same targets in every run (entity 02, values 14–18, statement 19, relations 31–33).

## Milestone 2, part 2: targeted recovery of prose values (`v6/milestone2/`)

- **Why recovery returned empty.** In every earlier run the focused quantity recovery was asked about table cells the deterministic binding already covers, and it was offered no material as a subject.
- **Recovery fix (`b8db2a5`).** The recovery now asks only for prose values. As subjects it offers the batches and the materials that this document's own tables establish as tested here.
- **Validator fixes (`0294286`, `17b88c2`).**
  - A prose value is named by its subject's own table column.
  - A sentence-opening pronoun binds to the one subject of the preceding sentence.
  - A value following an applied test step is a configuration.
  - A printed relative difference ("12% lower") is a derived value.
  - A page-cut sentence is read joined.
  - A material's row group wins over the material.
  - A number with a unit is not an entity name.
- **Sixth live run (`b8db2a5`).** 19/34 at `17b88c2` with precision 66/69, 0 critical.
- **All reviewed runs at `17b88c2`.** Recall 0.68, 0.65, 0.53, 0.50 and 0.56, precision 0.96–0.99, 0 critical. The other exposed sources are unchanged and the 29 historical negatives show no critical regression.
- **Still blocking.** Relations and the specimen entity omitted by the model, batch-scoped prose percentages, and holds that strict recall does not count. The next actions are in `v6/milestone2/CHECKPOINT.md`.

## Milestone 3: relations from the printed structure and correct holds (`v6/milestone3/`)

- **Relations from the printed structure (`05e689e`).** The validator now receives relation candidates taken from the printed table structure. A group printed as "<material> (qualifier)" is `madeOf` that material. A group gets `hasCondition` when its own rows, with no cited lineage, print that condition, and only for a condition of the same study.
- **Correct holds in the scorer (`a798003`).** The scorer lists reviewer-assessed correct holds (`correctly_held_targets`, never recall) apart from strict recall.
- **Type holds (`aff5039`, `2adc6e8`).** Instruments and test methods typed as interventions are held, as are labels that are only a value.
- **Seventh live run (`a798003`, 12 calls).** For the first time it gets the p4 specimen entity and batch #1 under LOX/GOX right. Its recall is 18/34 at precision 64/67, 0 critical.
- **All reviewed runs at `2adc6e8`.** Recall 0.68, 0.71, 0.56, 0.50, 0.62 and 0.53; precision 0.96–0.99; 0 critical; the other exposed sources are unchanged and the 29 historical negatives show no critical regression.
- **Still blocking.** Every accessible target except 18, 31 and 33 is correct in some run; recall per run is held back by run-to-run variance and by the 1,800 s deadline cutting the recovery stages. The next actions are in `v6/milestone3/CHECKPOINT.md`.

# Phase 1 scientific ingestion — v5 closure on `diego/research` (M1, M2 and the §18 matrix)

**PHASE1_COMPLETE = NO.** This section describes what the code on `diego/research` actually does after the v5 closure work, how to run it, what was measured on the exposed sources, and what still blocks acceptance. Receipts are under `artifacts/phase1_generalizable_ingestion/v5/` (`numeric_expression_grammar/` for the numeric grammar, `phase1_closure/` for tables, scope, lineage, coverage, eligibility and the §18 matrix). The v4 record below this section is unchanged.

## A. Working production implementation

All changes are in the ordinary ingestion path (`CurationService.submit_ntrs/submit/save → prepare_scientific → validate → export_package`); no evaluation-only pipeline was added.

| Module | What it does now |
| --- | --- |
| `ingestion/numeric_expressions.py` (new) | Syntax-only grammar: signed values, grouping and decimal conventions (ambiguous `1,500` keeps both readings), scientific and flattened exponents, approximations, inequalities and bounds (`>425` is never 425), ranges, `between`/`from … to`, ±, ratios (`4/80` is never a scalar), footnote-annotated values, header-inherited units, author-equivalent units (`72 ft-lbs (98J)`), and lists of separate values (`~.9 and 4.3` is a `LIST`, never one quantity). `CurationService.parse_value` (CSV and export) uses the same grammar. |
| `ingestion/table_continuity.py` (new) | Source-grounded table layout: a data-first table after a headed table with the same columns continues it and inherits the header; row groups carry down, also across the continuation; a leading letter is a footnote marker only when the text printed with that table has its legend; legends are read per table; rows carry the caption and a cited/external lineage from the caption citation, a legend naming an author of the document's own reference list or "obtained from"; `table_row_binding` binds a model quantity to its row group (`UNIQUE`, `GROUP_CONSTANT`, `AMBIGUOUS`), `table_cell_spans` locates the exact printed cell, `row_group_identity`/`printed_label_forms` recognise a group label with or without its marker. |
| `ingestion/study_attribution.py` (new) | Authors of the document's own reference list; cited attribution in a passage or the sentence before it (named author, "their data", bracket citation); tables whose caption cites a reference. |
| `ingestion/statement_integrity.py` (new) | Fragments (abbreviation, page break, mid-sentence start, glued caption line, front matter), source count conflicts, procedure/purpose wording and test steps that report no outcome, criteria, rules and caveats (a validity caveat typed as an interpretation or conclusion is held as well), documentary pointers, incompatible roles on one span. |
| `ingestion/source_eligibility.py` (new, §8) | Official identity, NASA involvement, domain relevance and accessibility judged separately from NTRS metadata and, when needed, the document's first pages; uncertain relevance is acquired for review, research outside the domain is not acquired. |
| `ingestion/document_extraction.py` | Uses the modules above in `validate_output`: footnote-marker identity in both directions (label normalised, marker and legend recorded, entity id independent of the marker), table-row binding with the column header as the quantity name and the exact cell as its span, `madeOf` by printed name (`Alpha (Lot 1)`, `Alpha samples`), document-investigation scope for research-section statements with material subjects, cited-attribution and cited-table guards, comparator lineage, the integrity holds, a caption (`Table 3—…`, `Figure – 1 …`) never accepted as an experiment-family identity, and the `LIST` rejection. `grounded_entities` matches printed label forms and never sends an identity without its anchor. Omission recovery (`recover_stage`) retries once on the window's halves when a recovery request did not fit the provider context, was partial or was cut short; a finished empty answer is kept as a reported gap. |
| `ingestion/document_structure.py` | `structure()` links continuation tables. |
| `ingestion/scientific_scope.py` | `logical_section` keeps the first word of a section title ("Results and Discussion" was read as "and Discussion") and treats a major heading followed by a subsection line as major. |
| `ingestion/pdf_quantities.py` | Header-unit binding; PDF cell proposals carry their row group, marker, legend and lineage as review context. |
| `services/curation.py` | Only `SOURCE_SUPPORTED` records are included as established statements, values and relations; unresolved ones stay in the package with `review_status` and `review_reasons` and never enter the isolated store as approved knowledge. `submit_ntrs` uses the §8 assessment and stores it in `source_provenance`; `validate()` keeps a review requirement for anything not established. |
| `scripts/` | `phase1_offline_replay.py` (full replay of a saved package, 0 model calls), `phase1_numeric_replay.py`, `phase1_exposed_live_run.py` (live run through the ordinary services, refuses receipts with credentials, re-judges the citation on file), `phase1_table_structure_receipt.py`, `score_scientific_review.py` (now also precision and critical counts per category). |

Entry points: `uv run python scripts/curate_research.py --workspace W submit --ntrs-id ID`, `… prepare PACKAGE --model`, `… prepare PACKAGE --model --recover`; the exposed-source runner above; the replay script for any saved `prepared.json.gz`.

## B–D. Table repairs, numeric handling and experimental context (original examples)

- NTRS 20090043050 Table 3 (pages 12–13): the page-13 table has a data row first; it now inherits the six-column header, its first row belongs to `Brass-filled PTFE (Batch #4)` from page 12, and `Salox-M®`, `Algoflon® F7` and `Algoflon® E2` start new groups on page 13. The printed `aBrass-filled PTFE (Batch #1)` is the group `Brass-filled PTFE (Batch #1)` with marker `a` → legend "NASA-STD 6001 MSFC". Tables 4–6 (pages 15–17): continuations on 16 and 17, legends "Determined by ABMA", "MSFC and WSTF mechanical impact test results", "Obtained from MAPTIS", captions citing `[4]`: 69 of 96 data rows are cited or external by the printed caption or legend. `phase1_closure/table_structure_receipt.json` counts the same on the five exposed sources (only PTFE prints continuation tables).
- Quantities: `0/20` for `Brass-filled PTFE (Batch #1)` binds to row 1 of Table 3 (`LOX/-297°F`, `10,000` psia, `0.06802` in) with the unit from "System Pressure (psia)" and the value located in its printed cell; `10,000` psia for `Salox-M®` is `AMBIGUOUS` (rows 2–4) and held; `72` ft-lbs for `Algoflon® E2` is `GROUP_CONSTANT`. All of them end `UNRESOLVED` with `QUANTITY_SEMANTICS_OR_UNIT_UNRESOLVED`: the semantic registry has four properties (`AirflowVelocity`, `FlowDirection`, `OxygenConcentration`, `Pressure`) and no accessor for heat of combustion, AIT, impact energy, test pressure or reaction counts, and `normalization/units.py` has no psi/psia, °C, J, ft-lbf or cal/g. Approving that vocabulary is the owner's decision.
- Context, before/after on the first live PTFE run (`ptfe_live_2b7d1d6` raw proposals replayed): `madeOf(Brass-filled PTFE (Batch #1) → Brass-filled PTFE)` from `UNRESOLVED` to supported by the printed name; the Experimental-section configurations (calorimeter, purges, mineral oil spike) from `UNRESOLVED` to supported at document-investigation scope; `Viton® A`, `Viton® A-500` and `Fluorel®` from current to `CURRENT_STUDY_LINEAGE_NOT_ESTABLISHED` (cited rows only); the page-12 Table 3 dump from an accepted observation scoped to four batches to `TABLE_REGION_IS_NOT_A_STATEMENT`; "Their data indicates that only TFE-Teflon® …" stays out of current scope by the named cited authors; "The reactivity of the same material increases by 20% …" stays out because it reads Table 6, whose caption cites `[4]`.

## E–F. Coverage and correctness on the exposed sources

Scored with `scripts/score_scientific_review.py` against the 36 frozen PTFE targets (34 accessible); precision covers every non-duplicate `SOURCE_SUPPORTED` record, judged by the branch author from full records (22 reused judgments are byte-identical to the earlier two-lens review). These are exposed development measurements, not acceptance.

| PTFE raw output replayed at the closure commit | Correct | Retained | Precision (by kind) | Critical |
| --- | --- | --- | --- | --- |
| First live run (`2b7d1d6` proposals), at `118ec71` | 15/34 | 25/34 | 57/59 | 0 |
| First live run, closure code | 17/34 = 0.50 | 25/34 = 0.74 | 64/65 (entities 15/15, statements 45/46, relations 4/4) | 0 |
| Second live run (`e19b7c0` proposals), closure code | 18/34 = 0.53 (17/34 if the p9-anchored specimen is not credited for the p4 target) | 26/34 = 0.76 | 61/62 (entities 18/18, statements 41/42, relations 2/2) | 0 |
| Fourth live run (`63e9bb9` proposals), as produced | 14/34 = 0.41 | 24/34 = 0.71 | 61/66 = 0.92 (entities 16/18, statements 45/48) | 0 |
| Fourth live run, closure code (`0ade8f1`) | 14/34 = 0.41 | 24/34 = 0.71 | 61/62 (entities 16/16, statements 45/46) | 0 |

`phase1_closure/exposed_sources_replay/comparison.json` replays the five exposed v4 receipts under `118ec71` and the closure code: no previously supported record on LUCI, textiles or ignition becomes supported for a wrong reason; what the closure holds there are 18 LUCI pairs of incompatible roles on one span, two slide tables, two cut sentences and one procedure; 41 PTFE-v4 and 9 regulator records become supported and were read one by one (role errors found that way, none critical, are held by the rules added at `adeada4`). `historical_negatives_receipt.json`: the 21 critical false attributions of v4 (ignition 6, regulator 9, textiles 6) and the 5 critical ones of the first live PTFE review are all rejected or held; the remaining known incorrect records are two non-critical role errors. `curation_projection_receipt.json`: on the PTFE package 46 statements are included and 137 unresolved ones (41 cited) are held; before the closure all 196 were included.

Third live run at `6ba33aa` (`phase1_closure/ptfe_live_6ba33aa/`): 39 calls in 2,078 s, `PARTIAL_MODEL_COVERAGE`; the pages 9–18 window (69,500 estimated tokens) was split for the first time, but the recovery loop spent 22 calls chasing empty answers on pages 1–8 and the deadline deferred the halves and the relationships stage. That defect is what `63e9bb9` bounds. Fourth live run at `63e9bb9` (`phase1_closure/ptfe_live_63e9bb9/`): 16 calls in 1,954 s, within the deadline, still `PARTIAL_MODEL_COVERAGE` (one propositions window needed a context split; five recovery windows, its halves among them, were deferred by the remaining budget). Reviewed as produced: 61/66 precision, 0 critical, 14/34 correct; the five incorrect records are the known framing sentence, two `Table n—…` captions typed as experiment families, a test step typed as an observation and a validity caveat typed as an interpretation. The last three patterns are held by `0ade8f1` with synthetic tests; the same raw output replayed there measures 61/62. The lower recall is run-to-run variance of the model: no `madeOf` and no p4 specimen entity were proposed, statements 26 and 28 were typed as conclusions or without subjects (held), and all 58 quantities name the Investigation as their subject, which the existing subject-applicability rule rejects.

## G–J. Model integration, evaluation, quality and reproducibility

- The live runs go through `submit → save → prepare_scientific` with `nvidia/nemotron-3.5-super-vl-120b-a12b` and the authorized fallback, from the local `.env`; receipts carry no credentials, approvals or publications; SQLite integrity `ok`; the original PDF hash `c9de8948…` is verified before each run.
- §8: `phase1_closure/source_eligibility_receipt.json` applies the repaired screening to the five official citations on file: the two the old keyword gate rejected (NTRS 20090043050 and 20170003941) are established by their own metadata (oxygen systems, EMU/PLSS; NASA centers MSFC and JSC); the other three still pass. Synthetic positives, negatives and metamorphic cases are in `tests/test_source_eligibility.py` and the NTRS screening test.
- Quality at the closure commit: `uv run ruff format --check .` and `uv run ruff check .` pass; `uv run pytest -q` passes 643 tests (572 before the closure; the new ones are synthetic positives, critical negatives and metamorphic twins for every rule above, including the end-to-end recovery split and the curation gate).
- §12 readiness is not demonstrated: table structure, numeric families, scope regressions, historical negatives and the normal workflow hold on the exposed corpus, but recall stays at 0.50–0.53 on PTFE against the 0.80 target, so no new holdout was consumed (§12: continue on exposed sources). `PHASE1_COMPLETE` stays `NO`.

## K. Remaining limitations (evidence-backed)

1. No quantity of any source can be `SOURCE_SUPPORTED` until the property vocabulary and units exist (owner's governance); every PTFE quantity target is `UNRESOLVED` with its row, cell, unit and lineage already bound.
2. Targets whose correct handling is `UNRESOLVED` (a source count conflict, a cited result, a recording rule) can never count as recovered under the frozen scorer; a "correctly held" outcome would need a new protocol.
3. The model omits or mistypes relations (`hasIntervention`/`hasCondition` on a Material; no `madeOf` at all in the fourth run), batch and specimen entities exist in one run and not the next, and runs of the same paper differ by up to 159 quantity proposals; in the fourth run every quantity names the Investigation as its subject and is rejected by the existing subject-applicability rule, so the narrative values are not retained. Prompt and stage design, and whether that rejection should become a hold, are outside this branch.
4. One non-critical role error remains accepted per run on PTFE (a narrative framing sentence typed as a conclusion; an instrument readout typed as an observation). Each live run has exposed one to three new role patterns that are then held by a rule with tests; a fresh run can still accept a pattern not yet seen (the fourth measured 0.92 as produced).
5. Live runs that recover omissions can exceed the 1,800 s deadline; `63e9bb9` bounds the retries and the fourth run finished within the deadline in 16 calls, but coverage of the split halves is still deferred when the remaining budget is short.

---

# Phase 1 scientific ingestion — v4 implementation and acceptance

**PHASE1_COMPLETE = NO. Independent scientific acceptance failed.** The production NVIDIA integration and general extraction repairs are implemented. Scientific approval and shared-baseline publication remain disabled by this campaign. The scientific implementation is frozen at `cdb17f252a0eb000f5afdf2a2bc5b647b903db1c`, from initial HEAD `2aca475`; `artifacts/phase1_generalizable_ingestion/v4/changed_source_files.json` identifies all 22 changed implementation/test files. Final reporting commits may add documentation and receipts without changing that freeze.

## Production model configuration and actual comparison

Scientific extraction uses `NVIDIA_EXTRACTION_MODEL=nvidia/nemotron-3.5-super-vl-120b-a12b`, with the already-authorized `NVIDIA_SCIENCE_FALLBACK_MODELS=nvidia/nemotron-3-super-120b-a12b`. Existing `NVIDIA_MODEL` query/Lightning configuration remains compatible. The local ignored `.env` preserves the existing authorized key. Endpoint: `https://integrate.api.nvidia.com/v1`. No subscription, purchase, account changes or credentials enter Git or receipts.

Matched original LUCI strict-schema tasks with 2,048 reasoning tokens completed for both candidates. On three page-37 author conclusions, VL recovered correct source scope/role **3/3**, Super **0/3**. On one complete page-29 quantity assignment both raw models scored **0/1**; validators and recovery remain necessary. Strict-task durations were **13.58/40.57 seconds for VL**, **67.05/80.27 for Super**. These are small developer source comparisons, not whole-paper precision or an independent scientific ranking. The historical Lightning v3 baseline is preserved. Ultra was subsequently justified by concrete primary-model failures, but its one matched development probe returned no completion before the 180-second diagnostic deadline; it is not selected.

The real VL endpoint accepted a text-plus-PNG `image_url` data URL for original LUCI page 36. It misclassified fitted rates as reported measurements, so multimodal routing is optional through `NVIDIA_SCIENCE_VISION_MODEL` and disabled by default. Original PDF checksum, physical page, rendered-page hash and table bounds remain operational provenance. Image-only assertions cannot become unquestioned NASA facts. Requested/served model aliases are recorded; exact hosted weight versions are unavailable. See `v4/model_selection_final.json` and original comparison receipts.

## General extraction changes

- Provider-aware scientific selection, observable finite retries, compatible transport fallback with the original task/evidence, persisted validated partial output and same-source continuation. There is no model voting or fallback triggered by scientific disagreement.
- Atomic bullet propositions, exact original offsets, abbreviation-safe spans, non-assertive identity context, true major-section scope, source-local exact figure/caption group references and review-only tested-article acronym resolution. Historical/cited work, planned tests, derived/model results, tentative interpretations and normative criteria retain separate roles.
- Original dimensional wording reuses existing sample-width/length accessors only after source binding. Unknown scientific labels retain expressions, units and experimental scope as unresolved proposals; no global class/property/alias is invented.
- Original PDF numeric cells retain row/column headings, original unit candidates, page/bbox/checksum and uncertainty. They remain unresolved until scientific subject/role/unit assignment is established; the software does not convert table presence into observation.
- Independently validated identical inference variants preserve their full audit history with one active native assertion. Recovery revalidates the same original source and produces no duplicate native IDs.
- Reserved-evaluation inference fails closed without a prospectively committed original-source reference, matching membership/source hash and unchanged code/model/ontology contracts. Production ingestion itself requires no gold answers.

No LUCI/PMMA/SIBAL/Saffire/BASS answer branches or new ontology vocabulary were added. `v4/ontology_reuse_final.json` records the unchanged approved vocabulary and unresolved approach.

## LUCI development results and honest denominators

LUCI NTRS **20250010653** remains development/regression evidence. Full original 43-page source processing and successive real recovery runs use the normal service; original outputs, failures and controlled interruptions are preserved. The final `v4/luci_delivery` package has **667/667 exact source spans**, original-PDF export equality, **2,725 isolated RDF triples**, conforming SHACL, zero native-ID duplicates and two zero-call replays with identical digest. There are no approvals/publications.

The expanded retrospective source sample has **31 targets**: four groups, nineteen quantities, six statements and two relations. Final results: **17 correct, 11 accurately unresolved, 3 omitted, 0 incorrect target recoveries**. Semantic recall is **17/31 (54.8%)**; original evidence retention is **28/31 (90.3%)**. Unresolved targets are not confirmed science. A selected 30-proposal regression precision audit scores **29/30**, with **zero critical false assignments in that sample**. One accepted tentative-versus-reported role error remains on page 20. This selected sample is neither random nor an exhaustive bound on the other 102 supported proposals. See `v4/luci_delivery_source_review_02.json` and `v4/luci_delivery_scientific_metrics.json`.

The four experimental groups, original **5 cm / 30 cm** specimen dimensions, seven oxygen values and main author conclusions are recovered with source grounding. Approximately **3.95 mm/s** remains correctly scoped but unresolved; approximately **.6 mm/s** retains a derived role; original fitted comparison cells remain pending rather than becoming measured observations. Missing structured targets include the **4-mm** rod diameter (preserved in the sample label), **greater than 25 seconds** duration (preserved in the author conclusion), and one SIBAL material relationship. All example numbers and judgments trace to original source spans in the review/package receipts. No new scientific inference is asserted here.

## Independent evaluation history

Every cycle retains its original frozen membership, source and outcome. Repaired exposed cases never become unseen passes. The v3 wire-break investigation remains exposed.

| Cycle / NASA investigation | Prospective result |
| --- | --- |
| 1 / 20250005133 battery calorimeter | Metadata domain-gate rejection before source body or inference; implementation acquisition false negative. |
| 2 / 20250002114 lunar ignition | Valid frozen science failure: 4/29 correct, 5/29 pending, 19 omitted, 1 incorrect; one inaccessible target; precision 23/30, six critical false assignments. |
| 3 / 20260003508 fire barriers | Structural audit failed after body acquisition, before model calls; no scientific pass. |
| 4 / 20260005493 textile slides | Valid frozen science failure: 1/29 correct, 1/29 pending, 22 omitted, 5 incorrect; one inaccessible target; precision 6/15, six critical false assignments. |
| 5 / 20190027097 laptop fires | Reference-registration protocol failed before a finalized gold file; no scientific pass or recall claim. |
| 6 / 20170003941 oxygen regulator | Valid frozen science failure: 7/32 correct, 6/32 pending, 13 omitted, 6 incorrect; two inaccessible targets; precision 19/30, nine critical false assignments. Existing upload service recovered metadata-gate rejection with official NASA bytes. |
| 7 / 20090043050 brass-filled PTFE | Valid frozen science failure: 7/34 correct, 15/34 pending, 12 omitted; two inaccessible targets; all-supported precision 28/29 (meaningful subset 26/27), zero critical false assignments. |

The final cycle prospectively froze all 224 scientific code/script/domain/ontology files, effective model configuration and a 36-target source reference before its first inference. Fourteen primary attempts completed or failed within an 1,800-second session; one subsequent ordinary recovery request was explicitly operator-interrupted after no visible content and deterministic validation defects were identified. This interruption is recorded as an operator action, not an NVIDIA outage. A real 600-second VL deadline switched to Super with a byte-identical scientific task/evidence request; partial valid proposals survived. None of the source-reference answers were passed to inference. The frozen evaluation is a failure and is now exposed development evidence.

The final source retains 125 original numeric table fields for review, but no source-supported quantities or target relations. Printed footnote prefixes adjoining wrapped batch labels fail literal identity checks; original thousands-separated numbers and reaction-count ratios exceed the numeric-expression grammar; current methods/results are frequently left unresolved. These are implementation and semantic-coverage limitations, not solely an external restriction. High proposal precision does not compensate for **7/34 (20.6%) semantic recall** and **22/34 (64.7%) target retention**. No post-evaluation code changes relabel this source as unseen.

The later generic repairs reject the known six ignition, six textile and nine regulator critical errors in exposed development replay. Those replays are regression evidence, not independent acceptance. The latest regulator recovery/export also preserves 255/255 exact spans, original PDF, conforming SHACL and two identical zero-call replays. Independent references are developer original-source reviews prepared before inference, not independent expert gold; model pretraining exposure is unknown. Source-character coverage, graph size and model completion never substitute for scientific recall.

## Normal application operation and validation

Use the existing incorporation view or supported CLI; no Codex process or manual generated-JSON repair is required:

```bash
uv run python scripts/curate_research.py --workspace /tmp/nasa-ingestion initialize
uv run python scripts/curate_research.py --workspace /tmp/nasa-ingestion submit --ntrs-id 20250010653
uv run python scripts/curate_research.py --workspace /tmp/nasa-ingestion prepare PACKAGE_ID --model
uv run python scripts/curate_research.py --workspace /tmp/nasa-ingestion prepare PACKAGE_ID --model --recover
```

`CurationService.submit_ntrs/submit/save → prepare_scientific → validate → export_package` preserves original retrieval, entity/relation proposals, approved ontology reuse, unresolved review issues and an isolated package. Export is available in the existing application/service; this campaign invokes neither approval nor publication. `v4/without_api_key` demonstrates usable offline preparation/export with no model calls and explicitly unestablished scientific completion. Some valid sources require the existing upload path because the metadata-only domain keyword gate is too narrow.

At the frozen source commit: **509 tests pass**, `uv run ruff format --check .` reports 477 files formatted (478 on the final reporting recheck) and `uv run ruff check .` passes. Regressions include G2/G3 attribution negatives, original quantitative expressions/units, EvidenceRegistry, SemanticRegistry, original PDF/table traceability, SHACL, partial replay, recovery/idempotence, provider failures/fallback and unauthorized publication. Existing rdflib deprecation warnings are recorded. Both canonical SHACL sets conform on **24,014 unchanged triples**. All **1,501 protected original raw/canonical/domain/ontology/historical v1-v3 files** remain byte-identical.

See `v4/README.md`, final checkpoint, acceptance decisions, preservation/quality receipts and verified compressed large JSON archives. Test counts and technical export success do not establish Phase 1 scientific completion. Phase 2 and shared-baseline publication have not begun.

---

# Historical v3 campaign — implemented, acceptance incomplete

The normal submission-to-curation runtime is implemented and regression verified. **PHASE1_COMPLETE = NO.** Real Nemotron outputs now recover meaningful source-grounded LUCI proposals, but scientific coverage and attribution remain incomplete. The reserved evaluation produced material identities and an incomplete scientific execution; it did not demonstrate independent scientific acceptance. No package was approved or published.

The v3 campaign used the existing user-authorized NVIDIA free development endpoint. The latest code passes **463 tests**, Ruff and source/SHACL/idempotence checks. A separate minimal provider check received no completion and was closed at its real deadline; NASA acquisition and internet access succeeded. The latest authorization supersedes the historical v2 budget boundary; no paid upgrade or publication is authorized. Original v1/v2 failures and evaluation membership remain preserved below.

## v3 continuation — adaptive production extraction and real-model validation

The initial independent-evaluation implementation was frozen by SHA-256 in `artifacts/phase1_generalizable_ingestion/v3/final_contract_freeze.json`. The initial Git HEAD was `32336287ee4bfc0725879ee5ba95949a7001e306`; the uncommitted v1/v2 implementation was present and preserved before edits in `workspace_before.json`, `git_before.patch` and `code_before.zip`. No Codex service or developer-prepared scientific mapping is required at runtime. Ordinary processing uses `CurationService.submit_ntrs/submit → prepare_scientific → validate → export_package`, the supported CLI and the existing incorporation UI. Approval and publication remain separate operations and were never invoked.

### Production changes and demonstrated mechanisms

| Exact source module | v3 functional change |
| --- | --- |
| `src/nasa_fire_ai/llm/scientific_provider.py` | Production SSE/nonstream adapter, usage/finish/latency receipts, persisted response prefixes, safe provider metadata, explicit network/rate/timeout/server/access/interruption classes; SDK retries disabled so retries are observable. |
| `src/nasa_fire_ai/llm/interfaces.py` | Configured NVIDIA client advertises supported streaming to the extractor. |
| `src/nasa_fire_ai/ingestion/extraction_resources.py` | Source/stage density selects context, visible output, reasoning and request timeout. Larger coherent sections are retained where the estimated provider context permits them. No fixed four-item ceiling or default document-call cutoff. |
| `src/nasa_fire_ai/ingestion/document_structure.py` | Exact original partitions, layout-derived PDF headings and table/cell localizers, cross-section source context, explicit inaccessible figures. |
| `src/nasa_fire_ai/ingestion/document_extraction.py` | Staged identities, propositions/quantities/concepts and relationships; compact original A/K/Q references; service-owned stable IDs; strict schemas and endpoint resolution; independent per-item validation and quarantine; finite splitting, repair and targeted source-quantity recovery; durable attempts and same-source partial replay. |
| `src/nasa_fire_ai/ingestion/scientific_coverage.py` | Separate read content, literal scientific/quantity cues, validated structure, unresolved/rejected proposals and inaccessible content. Original PDF numeric cells retain headers/notes/coordinates without becoming executed runs or measurements. |
| `src/nasa_fire_ai/services/curation.py` | Native proposal staging, source-reconstructed attribution validation, documentary-row roles, exact specimen/accessor reuse, late-invalid endpoint propagation, replay consolidation and existing correction lifecycle. |
| `scripts/curate_research.py`, `app/curation_view.py` | Normal configurable adaptive extraction and continuation using existing services. The UI continues unresolved work; optional operator resource ceilings remain available. |
| `scripts/run_phase1_scientific_validation.py` | Thin normal-service execution driver, versioned source snapshots/attempts/exports, resumability and final-contract hash enforcement. No scientific answer mappings or model JSON corrections. |
| `scripts/repair_generalizable_ingestion.py` | Offline replay/production integration receipts with explicit incomplete scientific status; mocks never count as live scientific acceptance. |
| `tests/test_document_extraction.py`, `tests/test_adaptive_extraction.py` | Real saved failure replay plus positive/negative source attribution, resource/retry/partial recovery, unresolved endpoints, original units/qualifiers, heading scope and idempotence regressions. |
| `tests/fixtures/scientific_extraction/` | One deliberate public NASA LUCI source fixture, its original package and the six historical failed parsed payloads. Original v1 responses were not all saved raw; that absence is explicit. |
| `README.md`, `.gitignore` | Independently usable adaptive CLI examples; local compressed historical SQLite archives remain excluded from Git. |

The preserved v1/v2 modules `document_context.py`, `narrative_candidates.py`, `generic.py`, `scientific_proposals.py` and prior evaluation scripts remain part of the implementation checkpoint. `changed_files_02.json` distinguishes v3 changes from the initial uncommitted continuation; the final changed-file receipt also records the Git-baseline boundary.

Independent validation still rejects unsupported/missing source anchors, unknown endpoints, material concepts used as experimental subjects, invented execution, source/value/unit swaps, derived-to-observed upgrades, cited-to-current upgrades, unjustified group/conclusion distribution and local exceptions. Exact original headings can resolve source scope with an explicit certificate; they cannot replace an unknown endpoint with a similar entity. Dimensional adjective/value binding and ordered “respectively” values use original local syntax. These mechanisms are general; there are no LUCI/PSI/BASS scientific answer branches.

### Actual NVIDIA behavior and adaptive resources

`provider_behavior.json` records official provider references and four actual production-adapter probes. The configured route is `https://integrate.api.nvidia.com/v1`, model `nvidia/nemotron-3.5-lightning-30b-a3b`, using existing authorized free development access. No credentials, `.env`, plan, paid endpoint or billing configuration changed. Accessible development access does not establish unrestricted production licensing or unlimited service. Account-specific credit/pricing information is unavailable, so a USD cost cannot be verified.

The hosted endpoint accepted a **32,768** `max_tokens` request; this establishes request acceptance, not reliable generation of that many meaningful scientific tokens. Its advertised million-token model context was not verified on this hosted route. The default usable envelope is conservatively **65,536** context tokens, configurable in `ProviderEnvelope`. Scheduling estimates original request UTF-8 bytes/2 plus output/reserve; unknown billing reserves full request bytes plus output instead of calling failed requests free.

Reasoning and visible text share the completion budget. The service allocates reasoning by source density and stage; focused quantity recovery receives additional reasoning. SSE with usage is accepted, but observed buffering often delays first visible content until near completion. Strict `json_schema` is accepted. A real `json_object` diagnostic emitted a small prefix and whitespace to `finish_reason=length` after 16,384 completion tokens; it is retained as a failed response, not adopted as a protocol shortcut.

Output capacity grows on length termination and then the original source is partitioned without loss. Whole-source primary stages precede deferred recovery so an early difficult section does not consume all processing before later results. Request timeout defaults to `max(120,45+output_tokens/35)` capped at **600 seconds**, with an operator override; there is no default whole-document deadline. Two transient retries and two semantic repair rounds, finite source splits and no-progress checks prevent endless loops. Long/date `Retry-After` values defer explicitly rather than induce unbounded sleeps. Scientific rejection changes the task or stays unresolved; it is not blindly retried as a network fault.

Development execution receipts have **233 unique attempt keys**, of which 223 report **1,665,333 actual total tokens** and ten lack complete usage. Across development, the reserved execution and six provider diagnostics, `reliability_usage_final.json` records 242 attempts: 228 report a measured subtotal of 1,716,008 tokens and 14 lack complete usage. This is not a zero-cost or complete billing total. Three recorded `length` finishes and all errors/interruption/partial-source outcomes remain failures or incomplete results. `development_provider_attempts_01.jsonl.gz` preserves original requests and responses without duplicate prepared-snapshot accounting; its companion JSON reports the exact boundary. Four provider probes are separate. `attempts_5_interrupted_scope_correction.json` distinguishes the twelve new invocation-five attempts from 75 older attempts exported together after a disk incident.

### Live LUCI recovery, original evidence and remaining omissions

LUCI **NTRS 20250010653 remains DEVELOPMENT_REGRESSION**. Its six v1 failures and all post-exposure runs remain immutable. `luci_live_01` through `_07` preserve distinct executions; newer validation never relabels a failed model run as successful. Current `luci_live_07/prepared_10.json` and `prepared_11.json` have identical digest `35040ab8dc36e19874ea861f6832ad8f7731014f8d4bc6957e1552d0750a5b90` and zero new model calls. The original prefreeze digest and evaluations remain preserved separately.

| Scientific structure in the final LUCI proposal set | Source-supported / unresolved |
| --- | --- |
| Entities | 40 / 12 |
| Statements | 53 / 154 |
| Quantities | 8 / 15 |
| Relations | 4 / 10 |
| Concept definitions/extensions | 0 / 3 |

These are independently checked extraction statuses, **not final scientific approval or comprehensive precision**. The full curation validator still identifies author-role and other review dependencies, so the package is not ready for scientific approval. Historical rejected proposals remain in attempt receipts; their absence from the final consolidated valid set does not mean no rejection occurred.

Concrete original-source results are in `scientific_quality_development_01.json` and the source-bearing prepared package:

- Page 5: Fabric **5 cm wide × 30 cm long** enters the existing specimen width/length accessor contracts as source characteristics, not new observed measurements.
- Page 19: flame-base **.92 mm/s** and flame-tip **1.1 mm/s** are recovered at the original **LUCI: SIBAL** group scope. Their quantity semantics remain staged/unresolved rather than inventing a global property.
- Page 22: oxygen **20%, 14.3%, 15.8%** belongs to **LUCI: PMMA**. The numerical sequence is separate from the author's tentative explanation.
- Page 27: roughly constant **20%** oxygen is scoped to **1-G Results: SIBAL**. Page 31 **21%/14.5%** oxygen is scoped to the original **Results: PMMA** heading without invented run membership.
- Pages 24, 26, 27 and 30: original typed headings/local passages support SIBAL-material and normal-gravity relations. Two supports describe one documentary group, not two executed experiments.

The complete review of the eight supported quantity proposals found **8/8** source/value/unit/scope correct; the four supported relation proposals were **4/4** correct within that narrow boundary. The prospective development sample has **19 items**: four groups recovered **4/4**, selected quantities **1/7 fully mapped plus 5/7 grounded pending semantics**, selected observations/conclusions **5/6**, selected relations **2/2**. Combining grounded-pending quantities gives **17/19 recovered**, but that must not be represented as whole-document recall. Entity/statement precision and review-request precision were not comprehensively adjudicated.

The source inventory separately records **12,915/12,915 characters read**, 39 candidate scientific units, 57 literal quantity occurrences and nine original numeric PDF table cells. Correct character coverage is not scientific recall. The approximate **3.95 mm/s** page-29 rate and page-37 applications conclusion remain omitted from the selected source sample. Method quantities, complex table roles, some cross-section attribution and figure interpretation remain incomplete. Canonical material/gravity entities cannot absorb unscoped results merely to improve the metric.

### Semantic reuse, human decisions and normal operation

Approved PMMA, SIBAL Fabric and normal-gravity aliases are reused. Original specimen dimensions reuse approved `sample_width`/`sample_length` source accessors. Unknown flame-base/tip quantities and new definitions remain source-bearing semantic proposals; global concepts are never activated automatically. New investigation/group/sample instances use the existing RDF classes and source-derived identities.

Source uncertainty, incomplete support and scientific semantic decisions remain distinct from transport errors. The package groups dependencies by cause/term/source, with original spans and resolution attempts. LUCI has ten grouped quantity-semantic issues plus scope, execution, author-role and other dependencies. Some requests remain unnecessarily broad or duplicate ordinary interpretation, so human-review quality is incomplete; scientists were not asked to approve every routine extraction. Native curation and semantic staging continue to enforce independent authority.

The normal CLI was exercised on the actual live-output package with `--model --recover --max-model-calls 0`; it reproduced the exact digest and made **zero** calls. `application_cli_luci_stdout_01.json` records a third-party PyMuPDF informational stdout preamble; the artifact reader strips only that banner, never changes scientific JSON. The normal service response is already structured. `application_luci_verified_02.json` proves **454/454** exact original source spans, unchanged original PDF SHA-256, original bytes inside the export, SQLite integrity, **1,689** isolated RDF triples conforming to the existing semantic SHACL, and **zero approvals/publications**. Curation readiness remains false because unresolved science remains.

### Reproducible checks, preservation and storage cleanup

`quality_checks_09.json` records unchanged hashes throughout the latest final checks (the original 449-test prefreeze boundary remains in `quality_checks_06.json`):

```bash
uv run ruff format --check .  # 465 files formatted
uv run ruff check .           # pass
uv run pytest -q              # 463 passed in 104.88s
uv run python scripts/repair_generalizable_ingestion.py \
  --directory artifacts/phase1_generalizable_ingestion/v3/offline_final_08
```

All four real original-source offline preparations (PSI-98, BASS, Depressurization, LUCI) pass integrity, idempotence and isolated SHACL on the frozen code, with zero live calls. Controlled adapters prove the production protocol and malformed/truncated/missing-support/unresolved-endpoint negatives; they do not establish live scientific acceptance. Historical G2/G3 correction negatives, QueryIntentV2, SemanticRegistry, quantity/unit and unauthorized-publication regressions remain in the 463-test suite. Canonical **24,014 triples** pass both existing shape files in `canonical_shacl_01.json`. Earlier checks and the disk-full failed execution are retained rather than overwritten.

During development the local filesystem filled while large test workspaces coexisted. One receiving journal could not finish and one QA recorder failed with `ENOSPC`; this was an infrastructure failure, not an invented provider outage. The registry recovered with `PRAGMA integrity_check=ok`; same-source cached proposals were independently revalidated through production recovery with zero new inference. `infrastructure_incident_01.json` preserves the boundary.

The user subsequently authorized obsolete artifact cleanup. Eight cold historical workspace databases were losslessly gzip archived and decompressed-byte SHA-256 verified before removing the uncompressed duplicates. This freed **947,515,404 bytes (903.62 MiB)**; original sources, historical scientific receipts, correction negatives, current test/runtime databases and Phase 1 workspaces were retained. `artifacts/storage_cleanup_20261015/manifest.jsonl` and `README.md` give exact paths and restoration. `preservation_04_final.json` verifies **2,611/2,611 original byte contents**: 2,603 at their original path and eight in the explicit lossless archives; no missing/changed originals. The canonical KG, ontology, domain, main registry and original evaluation files retain their content.

### Frozen independent evaluation

NTRS **20240006315**, *Wire-break Ignition Testing of Materials for Spacesuit Fire Hazard Control*, retains the v2 lineage freeze and excludes related 20240008688/20070006358 and other spacesuit wire-break/arc-ignition lineage documents. The final code/evaluation contract was frozen before acquiring the full PDF. It records 267 source/test/domain/ontology/contract file hashes, the actual QA boundary and development limitations. Metadata/abstract exposure and unknown pretraining exposure remain explicit.

The normal `submit_ntrs` service acquired the 14-page original PDF (SHA-256 `48390bbce022b7a9dbdf7b4e6fd505d1d9bbce020040df67abdf64b2c3de3710`, 38,173 extracted characters). `holdout_source_reference_02.json` records a 24-item source-only stratified reference after implementation freeze and before inspecting model responses. It distinguishes historical/current/planned tests, table values/footnotes, reported versus derived power, qualified bounds and author conclusions. This is developer source verification, not independent expert gold. The final answers cannot tune the frozen implementation, prompts, schemas, aliases or resource contracts. The actual incomplete result is recorded below; this execution remains incomplete and cannot be relabeled as acceptance.


### Expanded development audit and final execution boundaries

A further LUCI-only source audit found four invalid `SOURCE_SUPPORTED` classifications in the original prefreeze statement set: page29 diagram symbols treated as an observation; page29 inferential approximation; page25 an approximate fitted relationship; and page43 a rate explicitly derived from a neighboring fitted-position equation. All four are now blocked by production revalidation (three rejected, one source-bearing unresolved proposition); no valid quantity or relation from the reviewed positive set was lost. `scientific_quality_development_02.json` preserves the exact original proposals/anchors and **4/4** corrected negative cases. This targeted sample is not a comprehensive precision estimate. Current total statement precision remains unestablished.

General corrections reject nonpropositional diagram-label blocks including mathematical Unicode, distinguish inferred approximations from direct measurements, and attach the nearest original derivation passage only when it shares the variable phrase. A measured pressure beside a derived spread rate remains eligible: page-wide derivation keywords do not invalidate unrelated observations. Source values/text are never normalized in storage to make the test pass. These fixes and regressions were based on LUCI while the reserved responses remained sealed; they were not tuned on the final answers.

A separate source-independent provider diagnostic found that SSE comment heartbeats could keep resetting HTTP inactivity timeouts without yielding SDK events. The old 120-second minimal-ID request required interruption at **189.03 seconds**. Production now uses a response-socket deadline watchdog and preserves sanitized streamed `APIError` diagnostics. The repaired real minimal-ID request closed at **120.001 seconds** with `deadline`, no response content and unknown usage (`provider_health_06.json`). This verifies failure control, not scientific acceptance or a universal provider outage. `provider_behavior_02.json` records the corrected transport and uncertainty.

The old frozen evaluation runtime was interrupted because its total deadline could remain unenforced, as independently demonstrated by that development diagnostic. Its immutable `final_holdout_01` package records **three calls**, one completed identity response (**24,014 actual tokens**, 265.64 seconds), an earlier API error and an interrupted relationship request with unknown usage. Processing records **190,089 consumed-or-conservatively-reserved tokens**. Proposition work required context splitting and did not complete. This is an incomplete technical execution, not a finding that the model cannot recover the science within sufficient resources.

The reserved package retained **19/19 checked original material names**, **143 numeric PDF cells**, **47 literal quantity occurrences**, and all **38,173 source characters**. It recovered **zero supported scientific quantities, statements or relationships** and **0/24 fully supported source-reference requirements** in the delivered partial package. The 24-item count is a coverage denominator for that incomplete artifact, not whole-document model recall or precision. Entity checks establish material-label/column identity only, not complete current/cited attribution. Source integrity is exact **50/50 spans**, original PDF bytes remain in the export, SQLite and existing SHACL pass, and approvals/publications are zero. See `scientific_quality_holdout_01.json`, `holdout_provider_attempts_01.json` and `holdout_originals_verified_01.json`.

The subsequent LUCI-only repairs therefore have **no independently demonstrated generalization**. The original frozen contract and results remain immutable; the already exposed reserved investigation cannot be presented as a pristine evaluation of later code. No further code, prompt, schema or alias change was made using its answers. Any later independent acceptance requires a prospectively established new evaluation cycle after development and provider behavior stabilize. `live_validation_plan.json` records the executable existing-service recovery command, finite request/retry policy, proposed minimal provider check and token/cost uncertainty. Routine authorized free access does not need renewed per-call permission; paid changes remain unauthorized.

The final acceptance matrix is `artifacts/phase1_generalizable_ingestion/v3/acceptance_decisions.json`. Technical ingestion, source traceability, semantic reuse/staging and regression preservation have positive execution evidence. Scientific coverage, identity/attribution completeness, review precision and independent generalization remain partial or unaccepted. **PHASE1_COMPLETE=NO.**

## Historical v1 and v2 record

Receipts are under `artifacts/phase1_generalizable_ingestion/v1/`. Initial HEAD was `3233628`; the working tree was clean. The reproduced baseline was **331 passing tests**. No commit was created. Protected raw, canonical, ontology, domain, frozen evaluation, historical receipt and main-index files remain unchanged: **2,267/2,267** in `preservation_final.json`.

## Production implementation and ordinary entry points

| Module | Delivered behavior |
| --- | --- |
| `ingestion/document_structure.py` | Exact character partitions, section transitions across pages, literal methods/context retrieval, original PDF tables/cell coordinates, Markdown table spans, structured table records, explicit unread-image limitations, consecutive units packed into bounded model windows. |
| `ingestion/document_extraction.py` | Strict typed entity/statement/relation/quantity/concept contracts; deterministic and optional Nemotron interpretation; independent source-span, identity, expression/unit, role and applicability validation; ontology/alias/source-accessor inspection; typed table attributes; grouped review dependencies; successful and partial checkpoints; failure isolation; bounded calls, tokens, retries and elapsed time. |
| `ingestion/document_context.py` | Explicit group membership plus universal methods context, resolved through the existing `ScopeResolver`; original local gravity evidence overrides broader context and rejects contradictory assignments. Context remains unapproved. |
| `ingestion/narrative_candidates.py` | General literal investigation/group/run/sample anchors and approved concept mentions. No investigation-specific extraction branches or scientific answer tables. Named scientific quantities can enter semantic review without invented definitions. |
| `services/curation.py` | `submit_ntrs` uses the existing NTRS adapter/public-download policy, domain screening, bounded acquisition and immutable submissions. `prepare_scientific` attaches results to existing versioned packages, correction/export structures and SemanticRegistry staging. Revalidation reconstructs source support. Superseded operational candidates retain history. Draft-local reuse of already declared RDF classes adds no global definition. Numeric parsing reuses the existing native `NUMBER` grammar. |
| `ingestion/scientific_proposals.py` | Procedural modal guard distinguishes “must be recorded” from scientific reasoning such as “must be fairly constant.” Existing attribution safeguards remain operative. |
| `app/curation_view.py` | Existing incorporation form supports official NTRS IDs, optional bounded Nemotron preparation, processing receipts, semantic issues and original table attributes. |
| `scripts/curate_research.py` | Submission prepares a scientific package; `prepare` resumes an existing package. No API key is required. |
| `tests/test_document_extraction.py` | Synthetic, explicitly labeled positive, negative and metamorphic tests for batching, caching, partial replay, source identity, quantities, scientific notation, role upgrades, ontology reuse, local exceptions and no publication. |

Existing `QueryIntentV2`, native KG, curation lifecycle, EvidenceRegistry, FTS, Nemotron adapter and approved schemas are reused. There is no second scientific truth store, agent framework or ontology platform. JSON packages/caches are the established operational proposal lifecycle. Isolated RDF exports use the existing `SemanticGraph`, with canonical flags false and `STAGED_CANDIDATE` review state. Original paths, hashes and physical localizers remain operational evidence metadata.

Examples using the supported runtime:

```bash
uv run python scripts/curate_research.py --workspace /tmp/nasa-phase1 initialize
uv run python scripts/curate_research.py --workspace /tmp/nasa-phase1 submit \
  --title "NASA research package" --purpose "Scientific preparation" original.csv original.pdf
uv run python scripts/curate_research.py --workspace /tmp/nasa-phase1 submit \
  --ntrs-id 20150008961 --model --max-model-calls 3 --max-total-tokens 100000
uv run python scripts/curate_research.py --workspace /tmp/nasa-phase1 prepare \
  PACKAGE_ID --model --max-model-calls 1 --max-total-tokens 40000
```

Acquisition and preparation never call approval/publication. Model unavailability produces deterministic proposals and an explicit incomplete-model status. Successful windows replay without inference; partial valid items survive zero-call replay and remain retryable. Original source integrity precedes preparation and export. Uploaded sources whose NASA association is not established receive a source-eligibility blocker.

## Actual NASA executions and scientific fidelity

Development membership was frozen before extraction work in `evaluation_freeze.json`:

- **A: PSI-98 Saffire experimental CSV**, unchanged `data/raw/psi/PSI-98_experimental_table.csv`, with preserved official PSI metadata.
- **B: NTRS 20150008961**, [Microgravity Flammability of PMMA Rods in Concurrent Flow](https://ntrs.nasa.gov/citations/20150008961), official ten-page PDF.
- **C: NTRS 20260003546**, [Risks of Depress as a Fire Suppression Technique in Spacecraft](https://ntrs.nasa.gov/citations/20260003546), official twelve-page prose/table report.

`development_run1/` preserves the initial baseline and eight-call live attempt. `final_development_receipts/` contains final service-prepared packages, source-bearing ZIP exports, isolated RDF, SHACL and validation receipts. Preparation uses production APIs, not handcrafted scientific packages.

| Source | Actual final deterministic result |
| --- | --- |
| PSI-98 | Four original rows retained; S1/S2, SIBAL Fabric, 20 cm/s and Concurrent/Opposed native proposals; **16** typed original numeric attributes across the two scientific sample rows. Percent-header convention, ranges, approximate expressions, specimen dimensions, ignition parameters and unspecified burn-duration role retained. Two pre-test visualization rows remain unreviewed run-shaped proposals; this is an unresolved identity limitation. |
| BASS paper | Investigation/group/material candidates, source-backed gravity relations, five author-conclusion proposals with documentary conclusion scope, and named quantity definition proposals. Cited comparisons, uncertain scopes and unsupported entity correspondences remain unresolved. |
| Depressurization report | **25** physically located detected table records plus original prose, including observations, configurations, tentative interpretations, author conclusion and explicit future-work proposals. Complex merged headers are preserved; they are not automatically asserted to be executed rows or measurements. |

The PSI source rows report S1/S2 thickness **0.37 cm**, airflow **20 cm/s**, and burn-time expressions **420 s / 70 s**. The package keeps exact cell expressions, header units, row identity and the original CSV. Burn duration is not silently classified as an observed measurement. Its approved source-accessor role remains `REPORTED_DURATION_UNSPECIFIED`.

BASS page 1 explicitly documents concurrent-flow tests and complementary drop tests. The corresponding group/gravity proposals retain original passages and source IDs. Methods identity on earlier pages supports conclusion proposals on later pages at investigation scope; it does not make every conclusion apply to every historical run. Scientific uses of “must” are separated from procedural instructions. Source-based correction is independent of initial model classifications.

Negative controls reject moving a quantity to another run, replacing an original local gravity condition, upgrading hypotheses/tentative interpretations or simulations to observations, converting procedural requirements to measurements, changing units and promoting cited results to current experiments. `tests/test_curation_attribution.py` preserves the six historical G2 attribution negatives and supported correction/lifecycle positives. Shared methods/local terrestrial exceptions are additionally tested through the production preparer with a mocked adapter; **that exception demonstration is synthetic**, not claimed to be a new NASA scientific gold case.

Every proposition carries original source evidence, exact recovered spans/offsets, page/row localizers and hashes. Rejected proposals and provider/schema failures are preserved as operational review/diagnostic records. Model validity never grants approval.

## Generalization boundary and failed final evaluation

**LUCI, NTRS 20250010653**, [Lunar Combustion Investigation: Flammability Results from a Rotating Sounding Rocket](https://ntrs.nasa.gov/citations/20250010653), was absent by identifier/investigation name from repository raw inputs, canonical data, source, domain, reports, artifacts and frozen evaluations before selection. NASA acquisition/authorship and domain relevance are in the official citation receipt. Citation metadata and abstract were viewed at selection; the document body was first acquired after `contract_freeze.json`. Other LUCI/FM2 lineages were excluded from development. Pretraining exposure is unknown. Historical FLEX/Saffire exposure and title-only split limitations were inspected before selection.

The official **44-page** PDF entered via `submit_ntrs` and `prepare_scientific`. All **12,915 extracted characters** were structurally covered, with image-only/inaccessible figure content explicitly identified. PMMA, SIBAL fabric and LUCI candidates were prepared without investigation-specific Python or aliases. Source integrity, export, SQLite and isolated native SHACL passed; approved packages remained zero.

**First scientific acceptance failed.** Three calls yielded one truncated JSON response and two timeouts; the conservative token reservation deferred further calls. No model window completed. Quantitative experimental/group/conclusion structuring was insufficient.

General engineering repairs packed short pages into three bounded windows and reduced repeated entity context. Native numeric grammar and explicit derived-data guards were reused. `contract_freeze_v2.json` documents the changes and exposure boundary. Three remaining calls were used in `post_exposure_repair.json`: two partial-schema responses and one truncated response. Entity support fields were missing; proposed statement/relation endpoints or source spans failed validation. **No window completed, and no scientific relation was accepted from this model run.** This is a post-exposure repair run, not an untouched holdout. No source-specific scientific vocabulary, quantities, conditions, expected answers or extraction branches were added.

The failed original and repair receipts remain separate. Later deterministic validation receipts do not replace or relabel the live failure. Final generalization is **not accepted**.

## Semantic reuse and scientific review

Approved PMMA/SIBAL/gravity aliases, existing classes/properties/object and datatype declarations, hierarchies and source-field accessor contracts are inspected. Original specimen dimensions reuse existing attribute contracts and condition/value representation. Thickness does not create a material subclass. Extinction reuse is explicitly tested against an unnecessary new-class proposal.

BASS named terms including Peclet/Damkohler quantities enter typed definition-review proposals with original source passages and the examined approved vocabulary. These are unresolved semantic definitions, not activated ontology extensions or invented scientific definitions. Actual staged candidate terms and mappings are in package `scientific_extraction.semantic_mappings` and the existing semantic staging registry.

Review requirements group dependent propositions by source, cause and semantic term. They retain concise questions, candidate subjects, alternatives, focused supporting spans and source/contract-resolution attempts. Source uncertainty is retained as uncertainty. An explicit scientific open question is not evidence of an ingestion-created NASA research gap. Full genuine-versus-unnecessary review precision is **not measured**; some current/cited and narrative subject questions remain broader than desired.

## Quality, coverage and resource use

`scientific_quality.json` labels all adjudication as **developer source checks**, not independent expert gold.

| Measured boundary | Result and denominator |
| --- | --- |
| PSI-98 numeric attribute expression recovery | **16/16** produced correct; precision **16/16**, recall **16/16** within the two scientific rows/eight fields. Initial native numeric representation was **2/16**; final native mapped numeric representation remains two, with other typed source attributes staged. This is representational recovery, not measurement-role accuracy. |
| Proposed executed-combustion row identity | **2/4** correct scientific run labels; two documentary/pre-test rows also proposed. Baseline has the same limitation; zero such false proposals were approved. |
| BASS scoped gravity edge sample | **3/3** checked source-supported edges; precision **3/3** in this small source-support sample. These are repeated documentary supports, not three independent experiments. Publication-wide relation recall was not adjudicated. |
| Final deterministic original span/localizer/hash checks | **215/215** across four sources; these are mechanical source checks, not semantic entailment gold. |
| Historical critical attribution negatives | **0/6** scientifically false assignments accepted in preserved regression cases. |
| Unmodeled LUCI complete model windows | **0** on first pass and repair; scientific acceptance failed. |
| Parsed text coverage | PSI **1,353/1,353**, BASS **31,520/31,520**, report **39,015/39,015**, LUCI **12,915/12,915** characters. This does not imply recovered scientific-content coverage or interpretation of figures. |

Full scientific entity omission, group assignment, epistemic role and relationship precision/recall; observation/conclusion scope; and genuine/unnecessary review issue rates are **not broadly measurable** from this adjudicated sample. Abstention/unresolved proposals are not scored as scientific correctness. The zero-complete-window holdout cannot support a high-precision or generalization claim.

Explicit run limits were recorded before inference: four calls per development paper, six total holdout calls, 3,000 output tokens/call, zero retries, 40-second provider timeouts, 100,000 consumed-or-conservatively-reserved tokens/run and 180/300-second elapsed bounds. **14 fresh calls** were made. Received usage totals **56,244 tokens**; timed-out and initial schema-failed calls have incomplete usage, so actual billed cost is unknown. Processing durations, reservation accounting, finish reasons, failures and cache replays are in receipts. No further paid inference was performed. Environment precedence was preserved and `.env` was not modified.

## Regression, preservation and reproducibility

Final quality receipts record:

- `uv run ruff format --check .` — passed.
- `uv run ruff check .` — passed.
- `uv run pytest -q` — **355 passed** after production changes and the added scientific ingestion cases.
- Existing canonical SHACL and all four isolated native package SHACL validations — passed.
- Original-source reconstruction and repeated preparation digest checks — passed for four sources.
- SQLite integrity — `ok`; isolated approval/publication counts — zero.
- Protected file preservation — **2,267 unchanged**, zero missing/changed.

The development/holdout drivers and final validator are reproducible using new output destinations; they refuse to replace campaign outputs. Existing frozen scientific evaluations were not altered. Tests use no API key. Actual browser upload automation was not performed; the supported backend submission/preparation/export path was exercised. Vectors remain unchanged and no Phase 2–6 implementation was started.

```bash
uv run python scripts/evaluate_generalizable_ingestion.py development \
  --directory /tmp/nasa-phase1-development-new
uv run python scripts/validate_generalizable_ingestion.py \
  --run /tmp/nasa-phase1-development-new --output /tmp/nasa-phase1-validation-new
```

A live run additionally requires configured NVIDIA credentials and explicit `--model`/call limits. Successful model-cache tests and partial-cache replay tests use controlled adapters; live successful scientific cache coverage is not claimed.

## Acceptance decision and concrete blocker

| Required capability | Decision | Evidence/boundary |
| --- | --- | --- |
| DOCUMENT_PROCESSING | VALIDATED_BOUNDED | Four actual sources, reversible windows, tables/localizers, original integrity; unread figures explicitly limited. |
| CONTEXTUAL_SCIENTIFIC_EXTRACTION | PARTIAL | BASS deterministic scoped conclusions; live unmodeled extraction failed. |
| EXPERIMENT_IDENTITY | PARTIAL | Source-grounded candidates; non-run rows and complex narrative/group identity remain unresolved. |
| TABLE_AND_NARRATIVE_INTEGRATION | PARTIAL | Typed CSV attributes and physically located PDF rows; complex merged-table scientific mapping incomplete. |
| EVIDENCE_ATTRIBUTION | VALIDATED_BOUNDED | Source spans, protected G2/G3 tests and local-context negatives; not general semantic entailment validation. |
| EPISTEMIC_FIDELITY | PARTIAL | Procedural/uncertain/derived negative guards pass; complete real-source role coverage is unmeasured. |
| SEMANTIC_REUSE | VALIDATED_BOUNDED | Approved aliases, ontology/source accessors and existing RDF class instance staging. |
| ONTOLOGY_EXTENSION_STAGING | VALIDATED_BOUNDED | Source-backed named-quantity proposals and synthetic concept controls; zero activation. |
| REVIEW_REQUIREMENT_PREPARATION | PARTIAL | Grouped dependencies and evidence-bearing questions; minimal/genuine issue quality unmeasured. |
| GENERALIZATION_TO_UNMODELED_RESEARCH | FAILED_SCIENTIFIC_ACCEPTANCE | LUCI source preparation works; model experimental/quantity/conclusion recovery insufficient. |
| END_TO_END_INGESTION | VALIDATED_ISOLATED_PREPARATION | Normal application service/CLI submission → original source → structure → proposals → validation → package/export. Scientific completeness remains partial. |
| REGRESSION_AND_PRESERVATION | PASS | Required gates, SHACL, integrity, idempotence and protected-file receipts. |
| PHASE1_COMPLETE | **NO** | Functional scientific acceptance has not been met. |

The external execution blocker is unreliable configured Nemotron completion under the reserved paid-inference limits: timeouts, truncation and missing source-support fields prevented the final scientific demonstration. All reserved calls have been used. The cached partial outputs and exact failures are preserved; they need a corrected entity-reference/source-support protocol and a further explicitly bounded live validation run. The exposed LUCI document cannot be relabeled as an untouched final holdout. Complete group/run and complex-table scientific attribution must be demonstrated against original evidence before the Phase 1 decision can become positive.

`CHECKPOINT.md` records the final state and next concrete executable task. These are implementation/evaluation limitations, not NASA scientific knowledge gaps.

## Continuation correction v2 — offline repair validated, live acceptance pending

The sections above describe the immutable **v1 execution**. The current continuation is recorded under `artifacts/phase1_generalizable_ingestion/v2/`; v1 packages, failures, evaluation freezes and receipts were preserved. **PHASE1_COMPLETE remains NO.** No further paid inference, scientific publication or ontology activation occurred.

The offline correction changes `ingestion/document_extraction.py`, `ingestion/narrative_candidates.py`, `ingestion/generic.py`, `services/curation.py`, `tests/test_document_extraction.py`, and adds `scripts/repair_generalizable_ingestion.py` and `scripts/validate_scientific_extraction_live.py`. The final file hashes, report/checkpoint hashes and validation results are in the v2 receipts. The continuation retains the existing submission/curation lifecycle, QueryIntentV2, SemanticRegistry, EvidenceRegistry, RDF/SHACL and source IDs.

### Failure diagnosis and production correction

All six historical LUCI failure payloads were inspected read-only. Their source-of-failure boundary is narrower than the earlier report suggested: **none retains the raw provider response string**. Two retain normalized partial proposals and schema diagnostics; the remaining four retain JSON failure/timeout outcomes. Raw missing-support entity objects and the truncated JSON bytes cannot be reconstructed. The v2 `offline_run3/historical_failure_replay.json` preserves what actually survives and independently validates it, without manufacturing missing responses.

| Failure class | Actual surviving evidence | Correction |
| --- | --- | --- |
| Provider/elapsed limits | Two `APITimeoutError` outcomes at the original 40-second limit; timing/usage for failed calls remains incomplete. | Keep bounded per-call/aggregate limits and zero SDK retries; timeout handling records an attempt without borrowing another attempt's response or usage. Offline work does not establish improved provider reliability. |
| Oversized output / truncation | Two JSON-decode failures consumed 3,000 completion tokens; the repair run explicitly records `finish_reason=length`. | Three bounded tasks per source window: identity, propositions/quantities/concepts, relationships. Responses have enforced item limits, source-anchor IDs and smaller default 2,500-character windows. Only fully closed items in an actual JSON prefix may survive a length stop; the stage stays incomplete. No item or missing JSON tail is invented. |
| Support-contract mismatch | Eight missing entity-support diagnostics across the two partial-schema responses, invalid quantity roles and empty concept support. | Dynamic stage schemas require original source-anchor references. Code resolves these to independently recovered original spans, offsets and evidence IDs. Missing, invented or model-written replacement support is rejected. Strict Pydantic validation remains. |
| Reference failure / contaminated context | Surviving relationships use labels/approved IDs such as `PMMA`, `1-G`, `psi-98` and `psi-25` as undeclared endpoints. | Source-derived entity keys, merged independently located supports, and same-source validated identities supplied to later stages. Existing material/gravity aliases remain semantic vocabulary; unrelated investigation identifiers are excluded from the prompt. Labels are never silently substituted for missing endpoints. |
| Parseable but scientifically invalid output | Replayed partial proposals include wrong class/epistemic combinations, altered/unrecoverable spans, ungrounded endpoints and a nonnumeric quantity. | Production validation checks source spans, roles, numeric expressions, units, quantity names and applicability independently of JSON parsing. Rejected items are isolated; a source-rejected response is `PARTIAL_SOURCE`, never a successful cache entry. Unresolved semantic meaning stays review-required. |
| Lost attempt diagnostics | Historical raw responses are absent; an earlier failure path depended on usage being present before saving response text. | Each new checkpoint retains request, raw response even with missing usage, finish reason, schema/source diagnostics, and the accumulated attempt history. Failure-to-success resume carries its prior attempt receipts forward. |

Stage schemas allow at most four identities, four statements, six quantities, two concepts or six relationships as appropriate. Earlier identity evidence is bounded to 3,000 characters, shared methods retrieval to 1,000, and identities to sixteen per request. Source anchor identifiers derive from the original evidence ID and recovered offsets. They are operational evidence references, not new ontology vocabulary. Independently rejected identities, conflicting keys and cross-document identities cannot authorize dependent attribution. Valid grounded items survive partial replay; unresolved quantity semantics never create a property definition.

Additional scientific safeguards reject promoting explicit planned/documentary entries to performed runs, inventing a quantity name from its unit, discarding approximation or inequality markers, changing scientific notation/unit case, and silently scoping a multi-run comparison to only one run. Run execution requires source role evidence rather than a run-shaped label. Literal `Run`/`Sample` prefix recognition now handles source capitalization while retaining the original labels.

The general documentary-row mechanism reads explicit original cell labels. PSI's two pre-test flow visualization rows remain in the immutable CSV and package table, but no longer generate automatic run proposals. S1/S2 remain unapproved candidates; the repair does not convert their unspecified burn-duration attributes into observed measurements. Existing curation decisions and corrections remain available. Explicit row-role proposals are revalidated against original cells. NASA spacesuit fire investigations are now recognized by the existing metadata eligibility screen; a synthetic acquisition regression also rejects unrelated laboratory combustion metadata. This eligibility change adds no scientific vocabulary or source-specific extraction rule.

### Offline scientific and integration results

`offline_run3/validation.json` records all four original submissions prepared through `CurationService` in a new isolated workspace. Its outputs include original-source ZIP exports and the existing native RDF export, with canonical flags false and staged review state. Earlier corrective `offline_run1` and `offline_run2` remain available; the final run is explicitly run3.

- **380 tests passed**, including the original curation/correction integration, scientific attribution negatives, shared-context/local-exception safeguards and the new protocol/science regressions. Ruff format and lint passed.
- Four isolated native SHACL checks and both existing canonical SHACL shape sets passed. SQLite integrity is `ok`, with no foreign-key violations, approvals or publications.
- Original-source integrity and repeated preparation digests passed for four sources. **166/166** recovered support span/localizer/hash checks passed. Entity support merging changes this mechanical denominator; it is not scientific recall or an improvement in NASA science.
- PSI retains **16** original typed numeric attributes across S1/S2 and all four original source rows. Two documentary exceptions generate **zero** automatic run proposals. Performed-measurement role accuracy is not asserted.
- The real saved LUCI partial proposals were replayed through independent production validation; **zero relationships were source-supported**. Missing raw bytes remain an explicit limitation.
- A controlled source regression reuses an exact configuration sentence from the saved failed LUCI output and the original page-12 evidence `E-6a062578a8bc9b381a5d6bf0`. It reads the number/unit from the original source and passes the staged production pipeline. The rotation quantity stays unresolved for semantic review; no property/unit mapping or observed-measurement role is invented. This is a controlled source fixture, not a successful live extraction.
- A labeled synthetic production regression verifies investigation/group/run identities, original configuration quantity, observation/run attribution, shared gravity, cross-section author conclusion scope and successful zero-call replay. Existing local exception negatives remain operative.
- **21 empty controlled responses** complete seven LUCI windows' three stages and replay all 21 without calls, preserving the digest. Maximum request size in this controlled replay is **18,890 UTF-8 bytes**. Empty responses measure the protocol and cache only; they recover no model science.
- **2,468/2,468 protected files unchanged**, including the original v1 protected corpus/evaluations/history and the continuation-start raw/canonical/index/domain/ontology/evaluation/v1-snapshot manifests. No `.env` change or commit was made.

Full real-model scientific entity/relationship precision and recall, scope/role coverage, complex merged-table interpretation, unread figure content and genuine-versus-unnecessary review issue rates remain unvalidated. The offline fixtures do not close those acceptance criteria or create a NASA research gap. The exact external boundary is renewed inference authorization followed by successful source-adjudicated live extraction and generalization.

### Frozen evaluation and executable live boundary

LUCI is **development/regression**, including every post-exposure repair. `v2/evaluation_freeze.json` reserves [Wire-break Ignition Testing of Materials for Spacesuit Fire Hazard Control, NTRS 20240006315](https://ntrs.nasa.gov/citations/20240006315) as the different final investigation. The whole spacesuit wire-break/electrical-arc ignition lineage is excluded from further development, including the related 20240008688 presentation and 20070006358 earlier work. The official NASA metadata documents NASA authors and a public experimental fire-hazard paper. Only metadata/abstract was inspected; PDF/fulltext and final responses have not been acquired. Exact identifiers and named lineage had no matches in the audited science corpus/receipts. Generic historical spacesuit/wire queries and unknown pretraining exposure are explicitly disclosed. Metadata eligibility does not guarantee sufficient body coverage or acceptance.

`v2/contract_freeze.json` fixes the production code, prompt/parser, ontology/domain contracts and live driver before final evaluation. The driver checks these hashes, defaults to dry-run, refuses to replace output directories, requires an explicit authorization reference to execute, and writes versioned receipts. Final holdout responses must never tune prompts, contracts or ontology. A failure stays a failed/incomplete evaluation.

The proposed upper limits in `v2/live_validation_plan.json` are:

| Execution | Maximum calls | Timeout per call | Output tokens per call | Aggregate consumed/reserved tokens | Elapsed bound |
| --- | ---: | ---: | ---: | ---: | ---: |
| LUCI identity smoke | 1 | 55 s | 1,200 | 30,000 | 60 s |
| LUCI development scientific evaluation | 21 | 55 s | 1,800 | 400,000 | 900 s |
| Frozen unseen scientific evaluation | 15 | 55 s | 1,800 | 200,000 | 900 s |

This is **37 calls / 630,000 consumed-or-conservatively-reserved tokens maximum**, with zero retries and at most 66,000 completion tokens. The smoke must pass source-support checks before proceeding. LUCI requires seven complete staged windows under the currently prepared text; the final source permits at most five fully staged windows under its cap. If the final document is larger, the execution records incomplete coverage and cannot claim acceptance; no unapproved call extension or tuning follows. Actual usage/cost is uncertain because account pricing/credits and failed-call billing are unavailable. These are proposed caps, not authorization or a USD estimate.

The next executable action now is a zero-call verification:

```bash
uv run python scripts/validate_scientific_extraction_live.py smoke
```

**Only after renewed explicit user authorization**, the first paid action would be:

```bash
uv run python scripts/validate_scientific_extraction_live.py smoke --execute \
  --authorization-ref USER_AUTHORIZATION_REFERENCE --directory /tmp/nasa-phase1-smoke-new
```

Then source-adjudicate the smoke before authorizing/running `luci` and `holdout` with the same driver and fresh destinations. Scientific review must report recovered/omitted entities, groups, runs, quantities, conditions, conclusions and scope, with original evidence, explicit denominators and critical negative cases. Protocol completeness, cache success and parseable JSON alone cannot satisfy Phase 1. The original exhausted budget has not been extended.
