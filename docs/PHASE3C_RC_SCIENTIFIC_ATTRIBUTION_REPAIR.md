# Phase 3C G2/G3 scientific attribution repair

The six known scientifically false, structurally valid corrections are now rejected for source-attribution or source-role reasons. Source-supported corrections to deliberately wrong initial extraction succeed, including repeated application, regeneration, exact-version publication, rollback and reactivation. The bounded technical release candidate is eligible for the existing isolated scientist-reviewed configuration. Phase 4 has not begun.

G1 passes integrity; G2 passes the bounded source-attribution cases; G3 passes correction validation and mocked-provider parity; G4 preserves supported compatibility; G5 remains unchanged review readiness; G6 passes the supported lifecycle and bounded release eligibility. This is not an independently adjudicated scientific-accuracy or unseen-investigation generalization claim. Public deployment/authentication and enabled vectors remain outside the RC profile.

## Repository and preserved evidence

Before modification, `AGENTS.md` was read and Git inspected. HEAD before and after is `b55b717fd7efc4d998cdf75cc73cc79fc07f1367`. No commit was created: the implemented repair is in the working tree, identified by exact changed paths and SHA-256 hashes in `artifacts/phase3c_rc_scientific_repair/implementation_receipt.json`. The baseline report was already an untracked file at the start and was preserved.

Implementation changes:

- `src/nasa_fire_ai/services/curation.py`: immutable evidence identity validation, reconstructed table applicability, quantity/unit/role invariants, contextual author-role review in existing package decisions.
- `src/nasa_fire_ai/ingestion/scientific_proposals.py`: narrow procedural-modal guard in deterministic proposals and proposal validation, using existing Requirement vocabulary.
- `tests/test_curation.py`: wrong-observation attribution now rejects; stale-preview protection uses a legitimate documentary exclusion. The offline assignment fixture now explicitly supplies source gravity rather than accepting an unsupported scientific assignment.
- `tests/test_curation_attribution.py`: exact ten-case baseline replay, valid-ID mocked adapter parity, alternative mutation/approval blockers, positive repairs and lifecycle/metamorphic coverage.

The baseline document, `artifacts/phase3c_rc_baseline/`, historical generalization receipts, raw/canonical inputs, main evidence database and all frozen evaluation material remain unchanged. No G5 packages were reprocessed or published. The verification driver imports the historical audit driver unchanged and redirects its output variable to a new repair-only directory; it does not run historical drivers against their original receipt destinations. All original artifact digests are checked against the repair's pre-change preservation snapshot. The baseline document also matches its original artifact manifest.

## Missing invariants and implementation

Previously, correction validation checked that evidence existed, values reconstructed from their expressions, source text remained unchanged, endpoints were valid and simultaneous identities did not conflict. It did not independently bind the proposed subject or scope to the source row. Removing a correct relationship also removed its only competing identity. Registered class/epistemic pairs did not establish that the author made that claim.

`validate_attribution` now reconstructs temporary applicability anchors directly from checksum-verified submitted CSV/TSV bytes. It uses existing source identities, row evidence IDs, table profiling, semantic identities and approved review decisions. These temporary Python maps are discarded after validation; they are not a persisted scientific truth store or another graph. It does not use corrected relations or initial model classifications as its authority.

Original evidence validation now also compares document identity, page/row ordinal and locator to the original parsed units, in addition to source ID, text and checksum. Table entities retain their original run label and row evidence. Relationships for gravity, material, experiment family and investigation must agree with the original row and its evidence. This comparison survives removal of the original relationship. Unknown applicability produces an actionable scientific review requirement rather than a guessed condition. Original table identity/role checks also apply when a statement ID or mutable column metadata is changed to try to evade attribution validation.

Quantities retain their original table-cell identity, experimental subject, exact expression, reported unit and evidence row. Existing numeric reconstruction and semantic/unit validation remain in place. The reviewed percent-header convention remains supported. Thus 20 cm/s cannot be moved to the row reporting 10 cm/s, nor silently relabeled 20 m/s. Correcting an initially wrong subject back to the original cell's run is allowed.

Table statements retain original text, evidence, supported row applicability and source role. Identical statements explicitly repeated with the same role in multiple original rows can still be scoped to those supported rows. Compatible observation subclasses remain permitted through registry ancestry. Class and epistemic role must agree. Uncertainty is checked against original source-role evidence rather than treating an initially wrong extraction label as authoritative.

Broader documentary gravity context remains supported through the existing explicit campaign-applicability decision. Original local row conditions take precedence, including terrestrial exceptions. Narrative scope requires an existing review decision with evidence, an explanation and the selected applicable scope; ambiguous typed or model-proposed scope alone does not make the package ready.

Author-conclusion attribution requires original author-role wording or an explicit authorized source-context adjudication. `review_statement_role` records that adjudication in the existing package `decisions` and append-only editorial events. It requires a configured authorized scientist, an explanation and exact supporting spans from the statement's original source. Context can be in a separate sentence, paragraph or PDF page. A model cannot grant itself this review decision through correction operations. The decision does not waive contradictory table membership, uncertainty or normative safeguards. No relation connectivity is interpreted as causality.

The shared validator is used by draft validation, correction preview, application revalidation, exact-version approval and publication. Regeneration replays typed corrections, and the resulting package is again subject to the same approval/publication checks. Existing exact-digest authorization, stale-preview checks, immutable RDF hashes and transactional activation remain unchanged. Directly saving an invalid mutated draft is still permitted as editorial staging, but it is not ready and cannot be approved or published.

## Exact negative cases

`before_after_cases.json` contains the original baseline operations and before/after outcomes. Fixtures are explicitly synthetic; they are not invented NASA data. All original operation IDs and schemas remain valid. Unknown endpoints, parser errors and schema failures are not counted as scientific rejection.

| Case | Current scientific safeguard |
| --- | --- |
| `gravity_replace_contradiction` | Proposed gravity contradicts original row condition, even after removal of the correct relation. |
| `group_replace_wrong_row` | Proposed family/group contradicts original source-row membership. |
| `measurement_wrong_run` | Quantity subject contradicts original table-cell/run identity. |
| `conclusion_scope_wrong_run` | Conclusion applicability contradicts original row scope. |
| `observation_scope_wrong_run` | Observation applicability contradicts original row scope. |
| `observation_to_conclusion` | Author-conclusion role differs from original observation-column role. |
| `gravity_add_conflict` | Existing equal-scope identity-conflict rejection preserved. |
| `measurement_numeric_fabrication` | Reported number differs from original expression; prior numeric safeguard preserved. |
| `hypothesis_to_observation` | Original source hypothesis role cannot become a confirmed observation. |
| `nomex_two_to_all_four_direct_text_mutation` | Replacement remains absent from the original source span; prior safeguard preserved. |

The first six baseline cases were ready previews before repair; they were never published in the baseline. New lifecycle tests publish only the unchanged or source-corrected synthetic positive package under configured test authority. No invalid negative correction is described as an observed unauthorized publication.

All nine operation cases also run through a mocked Nemotron adapter returning exactly the valid-ID operations. The backend returns the same scientifically relevant reason as direct typed preview. No live provider request is required. The direct Nomex wording mutation is separately validated because there is no supported statement-text replacement operation.

## Positive and metamorphic verification

Six positive axes deliberately corrupt the initial draft's gravity, group, quantity subject, observation scope, conclusion scope or epistemic classification. The original bytes remain correct. Corrections restore their original supported attribution and become ready; this demonstrates that the initial extraction is not treated as scientific authority.

Each axis repeats preview/apply/regeneration and authorized publication/rollback/reactivation three times. Further positives restore an incorrectly extracted material, adjudicate contextual author attribution using a separate source sentence, and correct a procedural table statement to the existing normative Requirement role. Unauthorized role review is rejected. Changed reported units, document identities, row locators and column-role tampering are negative controls.

The old wrong-observation test now expects scientific rejection. Its stale-preview check uses a source-supported preview followed by documentary exclusion, making the earlier preview stale without first applying an invalid attribution. Existing broader-context/local-exception, ontology extension, quantity contract, no-key, authorization, graph corruption, service retrieval and rollback tests continue to run.

## Normative safeguard

The documented NASA-STD-6001 example remains in the preserved baseline provenance receipt. This repair does not reclassify or republish that historical corpus draft. New deterministic preparation treats procedural `shall` and narrowly selected imperative `must` phrases as existing Requirement proposals, not measured observations. Model-supplied observation/measurement proposals with this procedural language receive `NORMATIVE_INSTRUCTION_NOT_EXPERIMENTAL_OBSERVATION`.

Publication validation independently blocks procedural instructions labeled as measured observations. A procedural statement under an Observation column can be corrected to `Requirement` / `normative_requirement` using the original wording. Unresolved applicability or documentary exclusion remains available. This is a small procedural guard, not a general scientific language classifier.

## Executed quality and release gates

Reproduction:

```bash
uv run ruff format --check .
uv run ruff check .
uv run pytest -q
PYTHONPATH=src uv run python artifacts/phase3c_rc_scientific_repair/verify.py
```

The verification command executes and records the three required quality commands, then runs the additional attribution tests verbosely and checks its own script format/lint. `checks/execution_receipt.json` retains commands, timestamps, exit codes, environment versions and exact output digests. Provider-key environment variables are explicitly empty for quality subprocesses; adapter tests use mocks. No credential values are printed or exported, and no live inference is invoked.

The final suite passes **331 tests**, compared with 304 in the baseline: 27 additional regression cases, zero failures. Existing rdflib deprecation warnings remain documented. The final receipts supersede exploratory repair checks made while the implementation was still being edited; historical baseline receipts are untouched.

Canonical SHACL, main/pilot native and generated SHACL, four read-only SQLite integrity checks, explicit FTS/document/pointer checks, evidence resolution, six publication RDF digests and original package-input/span digests pass. The current pilot has 7,266 resolvable graph evidence IDs; the main graph has 7,237. Publication/rollback/reactivation are freshly exercised by the regression suite in discarded isolated workspaces. Foreign-key pragmas remain supplemented by explicit joins because legacy tables declare no foreign keys.

The historical runtime contract freeze naturally identifies the intentionally repaired runtime/test files as changed; it is not relabeled unchanged. Its 600 historical immutable inputs and frozen membership/evaluation material remain unchanged. Source preservation is separately checked against the repair-start snapshot, and the final verification run makes no changes to protected inputs.

| Gate | Decision | Scope |
| --- | --- | --- |
| G1 | PASS | Quality, SHACL, evidence/registry/publication identity and source preservation. |
| G2 | PASS bounded | Original table attribution, contextual review requirements and source-supported positive repairs. |
| G3 | PASS known critical cases | All six false previews blocked, three existing rejections and Nomex span safeguard preserved; mocked-provider parity. |
| G4 | PASS supported compatibility | Existing QueryIntentV2, registry, ontology extension and native assistant regressions pass. |
| G5 | UNCHANGED, review readiness only | No corpus processing, proposal publication, holdout or gold changes. |
| G6 | PASS, bounded RC eligible | Valid reviewed lifecycle and failure/authority/stale protections; isolated configuration only. |

Remaining limitations are explicit scientist adjudication for ambiguous narrative scope/roles, incomplete general procedural-language recognition, no independently unseen-investigation scientific validation, no enabled-vector or public-authentication release, and no retrospective reclassification of historical published RDF. These do not reinstate the repaired critical cases or imply complete scientific-domain accuracy. No new ontology vocabulary, truth database, agent framework, graph or frontend was introduced. Work stops after this bounded repair and verification.
