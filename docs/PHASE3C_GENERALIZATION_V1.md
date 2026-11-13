# Phase 3C scientific curation generalization — executed campaign v1

The campaign demonstrates real-source incorporation with dynamic scientific choices, a successful fresh Nemotron correction, compatible new scientific classes and object relationships, native retrieval, and controlled rollback. It does **not** establish complete scientific-domain knowledge or independently validated unseen-investigation generalization. V2 remains experimental and Phase 4 has not begun.

All paths below are relative to the repository. Machine-readable receipts are under `artifacts/phase3c_generalization_v1/`; its artifact index records exact paths, sizes and SHA-256 digests, including isolated workspaces. The pre-existing dirty worktree was preserved. Changes attributed to this campaign are measured against `baseline.json`, not against Git HEAD, which includes earlier user work.

## A. Implementation and architecture

Modified runtime modules:

- `services/curation.py`: stable no-op saves, exclusion identity, correction replay, relation identity/provenance merging, answer plans, compatible quantity alternatives, multiple scope selections, decision reopening, compatible class/object-property proposals, reviewed contract activation and reload, generated SHACL, statement endpoints, epistemic protection, and reversible Windows-1252 CSV decoding.
- `llm/scientific_correction.py`: bounded whole-object context selection instead of cutting serialized JSON, fresh/cached clarification receipts, conservative model question wording over ontology-grounded alternatives, explicit clarification/notes separation, bounded provider syntax normalization, typed previews and narrower follow-up questions.
- `ingestion/scientific_proposals.py`: extraction cache identity includes class/property/relationship contracts, nonnumeric proposed quantity rejection, additional narrative outcome/interpretation phrases, and whitespace-tolerant phrase matching that retains the exact original span.
- `query/v2.py`: additive relationship domain, range, direction and alias contracts; QueryIntentV2 remains the query model.
- `query/native.py`: generic domain/range enforcement, subclass-compatible selection and approved relationship edges in scientific query records.
- `query/native_interpreter.py` and `query/evidence_selection.py`: approved new class vocabulary and class ancestry participate in the existing interpretation/selection path. Historical class wording was deliberately not remapped.
- `app/curation_view.py`: generated choices, an explanation fallback on every question, multiple group/run scope selection, optional explanation for listed choices, scientific class/relationship proposal controls, and guided class refinement. Draft-approved terms are available to controls before publication.

The existing EvidenceRegistry, scientific staging, SemanticRegistry, native RDF graph, SHACL, ScopeResolver, NVIDIA adapter, canonical version approval, SQLite/FTS, publication/rollback, and Phase3AssistantService were reused. There is no new graph, truth store, ontology engine, query executor, QueryIntentV3 or agent platform. Scientific additions reside in approved immutable RDF versions in isolated development workspaces. Operational source paths, checksums, IDs and editorial history remain in the existing registry.

Reproduction drivers are `phase3c_generalization.py`, `phase3c_generalization_e2e.py`, `phase3c_generalization_language.py`, and `phase3c_generalization_report.py`. Existing pilot/prose/revision drivers were reused; the pilot driver now tests a real version change rather than treating an unchanged save as a revision.

## B. Dynamic scientific clarification

Each question includes its stable identity, issue kind, affected scientific entities/records, original evidence, answer meanings, corrective operations, validation requirements and readiness implications. Scope selections produce typed `scope` operations; mapping, identity, context and table-role selections update their existing decision contract and regenerate affected scientific proposals. The final alternative always requests an explanation and produces a correction preview rather than applying prose directly.

Real generated examples and executable plans are in `pilot/clarifications_initial.json`, `pilot/clarification_receipts.json`, and `language_v2/questions.json`:

1. **Does this table report executed experimental runs or documentary/planned information?**
   - A: Executed experimental runs.
   - B: Retain documentary information.
   - C: Another interpretation; explain briefly.
   Original PSI-98 row evidence accompanies the question. The two pretest camera/flow rows are separately excluded; they do not become active runs.
2. **What does “Sample Thickness (cm)” represent?**
   - Before scientific extension approval: retain documentary information, propose a scientific definition, or explain another interpretation.
   - After approval: choose SampleThickness, retain documentary information, propose a different definition, or explain another interpretation.
   Original column units and values constrain choices. Pressure and oxygen concentration are not offered for a length column. The approved mapping resolves both eligible Saffire records.
3. **Which identified investigation or experimental scope do these source statements describe?**
   - A: The submitted depressurization investigation.
   - B: Retain documentary evidence without asserting current-study applicability.
   - C: Another interpretation; explain briefly.
   The actual question wording, source passages and plans are retained, including the model's original “identified runs” wording. In this prose package only an investigation identity was prepared; the options do not invent run identities. Individual exception controls remain necessary.

Fresh Nemotron wording accepted three questions in `language_v2/questions.json` using 4,178 reported tokens. The identical later request is explicitly `CACHE_REPLAY` in `language_v3/questions.json`. An earlier five-question attempt accepted five wordings; another output exhausted its limit and failed JSON parsing. Those attempts remain visible rather than being counted as final successes.

Alternatives are generated conservatively from existing scientific constraints and source context; Nemotron may improve wording but cannot invent choices or replace resolution operations. This prevents new model vocabulary from silently becoming scientific authority. Full inference of experimental identities and scientifically precise scope groups from general narratives remains partial. Grouping solely by epistemic role is useful for review but is not proof that every grouped statement has identical applicability.

## C. Human review reduction and idempotence

Fresh Saffire execution made **11 shared decisions covering 26 dependency-record memberships**, avoiding **15 potential repeated prompts**. This is prompt/workload accounting, not measured scientist time or independent usability evidence. See `pilot/validation.json` and `pilot/clarification_receipts.json`.

The recorded package went from **13 initial questions to zero remaining questions/validation blockers**; the shared decisions and the explicit preliminary-row exclusions account for the resolution. `clarification_metrics.json` records this distinction.

The active exclusion source of truth now uses subject identity, rather than accumulating replayed exclusions. Relationship identity is `(subject, relationship, object)`; evidence is merged deterministically. Reapplying an identical correction retains one active correction. A scientifically unchanged save reuses the exact existing digest/version. Editorial events remain append-only and separate.

`test_regeneration_exclusion_and_correction_idempotence` repeats regeneration, correction, publication, rollback and reactivation four times. `e2e_v3/regeneration.json` records five unchanged regeneration cycles and a stable digest. `test_narrative_whitespace_and_multiple_scope_reopen` demonstrates multiple scopes, removal of resolved questions and reopening without replaying a superseded scope decision.

Existing approved quantity aliases and definitions reload for compatible future imports. General reuse of all identity/scope/column decisions across unrelated packages is not implemented; approvals must not be broadened on title or lexical similarity alone.

## D. Natural-language fallback and model evaluation

The current fresh evaluation is `language_v3/corrections.json`:

| Scientist instruction | Executed result |
| --- | --- |
| Retain only the specifically identified tentative oxygen interpretation as documentary evidence | Validated exclusion preview; applied; revalidated; exact-version published; rolled back to the prior active version |
| Replace source wording with “Nomex extinguished in all four tests” | Rejected: the returned unrelated material relationship had an unknown endpoint; no change applied |
| Fix conclusion scope while the intended group remains unspecified | Ambiguous; a narrower question asks for the statement IDs and intended group/condition |

The negative result demonstrates backend containment, **not** correct model reasoning about the contradictory instruction. The model returned an irrelevant proposed relationship rather than a satisfactory scientific refusal. Arbitrary language correction remains partial.

The previous four failures were not reproduced as a single assumed model defect. Fresh attempts identified (1) truncated JSON context in the old implementation, (2) harmless completion notes being treated as blockers, and (3) alternate provider operation syntax such as `{exclude:{...}}`. Context is now bounded before serialization; notes and required clarification are distinct; bounded equivalent syntax is normalized before the same entity, ontology, unit, provenance, scope, epistemic and conflict validators.

`inference_accounting.json` accounts for **16 fresh calls and 138,679 reported tokens** across extraction, question generation, unsuccessful attempts and final corrections. Cached wording is not counted as new inference. Calls use finite output budgets and zero SDK retries. No simulated output is described as live. Existing credentials and the precedence-preserving environment loader were reused; `.env` was not overwritten or exported.

No-key operation remains available through closed choices and the deliberately narrow deterministic language grammar. An accepted model proposal is never independent scientific authority: preview review and exact-version authorization remain necessary.

## E. Generic ontology evolution and retrieval

The real-source compatible addition is **SustainedFlameObservation**, a subclass of ReportedObservation. It distinguishes reported flame persistence during an intervention from a phenomenon identity or a confirmed mechanism. It does not assert stable burning. Its proposal includes scientific definition, purpose, parent, source-backed instance, reviewed query terms, compatibility and constraints.

The new object relationship is **authorInterpretsObservation**, directed from NASAConclusion to ReportedObservation. Its definition records explicit source-author attribution; it is not causal, transitive or an independent confirmation. The real source's “This demonstrated…” sentence interprets the preceding documented persistence/reignition outcome.

`e2e_v3/ontology_and_evidence.json`, `scientific_preview.json`, `publication.json` and `queries.json` record the definitions, exact spans, evidence, approved relation and actual assistant queries. Runtime registration, RDF subclass/property definitions, reload, domain/range validation, query vocabulary, scientific bundle fields and generated native SHACL all derive from the approved contracts. Neither scientific name was added to a production switch statement.

The query **“Which sustained flame observations describe depressurization?”** retrieves the new observation through the actual Phase3AssistantService. The conclusion query includes the new approved relationship in `EvidenceBundle.semantic_records[].approved_relationships`. Native graph retrieval also resolves the edge. Arbitrary natural-language relation formulations and all ontology families are not comprehensively evaluated.

`test_generic_class_relation_and_actual_assistant` independently exercises a labeled synthetic subtype, unauthorized approval, reversed domain/range rejection, generated SHACL against deliberate RDF corruption, native service retrieval, epistemic preservation, rollback and reactivation. `test_reject_existing_concept_and_epistemic_upgrade` rejects recreating Extinction, which already exists in the ontology, and rejects upgrading a hypothesis to an observation.

Supported extensions are compatible additions under classes already exposed by the approved native registry, plus the existing numeric/categorical quantity path. Unsupported structural constraints, inverse/transitive relations and incompatible changes are rejected for separate modeling review. No incompatible migration or historical semantic rewrite was performed. Approved query terms and quantity aliases are supported; a comprehensive cross-package alias/identity contract workflow remains incomplete.

## F. Real NASA scientific preparation

The actual twelve-page NTRS 20260003546 PDF is retained unchanged at `data/raw/autonomous/ntrs-20260003546-b4b64e88992718a7598000ad85d181ac4d9c06ed58e0ae7df0fb4188a6662a18.pdf`.

The fresh source pilots preserve:

- PSI-98 Saffire S1/S2: SIBAL Fabric; source-backed microgravity; 20 cm/s airflow; original oxygen expressions; SampleThickness 0.37 cm for both records. Two preliminary documentary rows are absent from active scientific runs.
- A later source-backed BurnDuration contract: S1 **420 s**, S2 **70 s**, retrieved through the existing assistant. Revision, rollback and reactivation receipts are in `revision/`.
- Narrative observation: some samples sustained a flame at **4 psia**, with reignition when venting continued.
- Author conclusion: the described combination of depressurization blow-off and reduced oxygen partial pressure was insufficient to extinguish the fire in that reported context.
- Nomex outcome: extinguished in two of four tests, retained as the source states.
- Tentative oxygen interpretation: remains tentative; it is not a confirmed extinction mechanism.
- Future CFD work: remains an open question, not a completed result.

The last four original pilot statements are in `prose/prose_reviewed.json` and `prose/prose_query_after.json`. The observation/interpretation edge in `e2e_v3/` uses the explicit same-paragraph author reference, not document proximity. Gravity is unspecified for these narrative statements: an explicit microgravity request returns RELATED rather than silently assigning microgravity.

PDF parsing was reused. Source line breaks are accepted during phrase recognition while original wording and source spans remain intact. General narrative experiment/group identity, detailed condition/intervention structuring, referenced-study attribution and complete observation-to-conclusion coverage remain review requirements.

## G. Corpus reconciliation and coverage

The freshly retrieved [official NASA PSI combustion inventory](https://www.nasa.gov/physical-sciences-informatics-psi/psi-investigations-by-research-area/) contains **19 investigation names**. `inventory/coverage_ledger.json` independently reproduces **228 local domain candidates**, all acquired/hash-verified, **227 parsed/searchable**, and **six** referenced by historical structured records. These are separate coverage measures, not complete investigations.

`corpus_coverage_v2.json` reconciles all 290 registry sources. The 228 candidate titles require scientific relevance review; none is falsely labeled independently confirmed. Two exact-content duplicate source records are skipped: `ntrs-20110001653` duplicates `ntrs-20070010766`, and `ntrs-20205007829` duplicates `local-ntrs-20205007829`. One candidate has no indexed text. PSI-98's HTML overview remains an unsupported package input, although the experimental table was successfully used in the real pilot.

| Coverage | Executed result |
| --- | --- |
| Development/validation candidate packages prepared | 199 |
| Held-out candidate packages prepared after freeze | 25 |
| Total isolated reviewable corpus packages | 224 |
| Development proposed ExperimentalRun entities/table rows | 1,136 |
| Development proposed values | 32 |
| Development observation / conclusion / tentative / open-question proposals | 1,624 / 214 / 108 / 55 |
| Holdout observation / conclusion / hypothesis / tentative / open-question proposals | 336 / 46 / 1 / 26 / 20 |
| Development draft relations | 1,139 |
| Automatically approved corpus scientific packages | **0** |

These numbers are **proposals**, not verified scientific findings, approved measurements or completely structured sources. `scientific_coverage.json` records class/epistemic distributions separately. The batch records 1,256 bounded staged propositions through the existing scientific extraction path; the curation layer separately prepares document-level exact-span proposals. Their counts should not be added as distinct discoveries. Rejected proposals and unresolved scope/classification are retained in the existing registry and source receipts.

The first batch produced 198 packages and two failures. A checkpointed zero-inference retry recovered PSI-69's Windows-1252 FLEX CSV, retaining all source bytes and proposing 274 rows. The remaining HTML failure is explicitly checkpointed. Each source has an identity, original digest, draft digest, extraction/cache receipt, scientific proposals, questions, blockers and authorization state. Successful sources were replayed from checkpoints rather than spending new model tokens.

No corpus scientific ambiguity was automatically approved. Compatible source records remain staged for scientist review. Three source-backed incorporation scenarios were authorized only in the isolated development workflow; their documentary passages, graph records and citations are available through the current service. The 224 corpus drafts are not promoted into canonical knowledge by their existence.

Official PSI names and the local collection do not establish exhaustive public NTRS/PSI coverage. Full experimental-versus-review classification, publication-lineage/supersession reconciliation, metadata-only completeness and independent relevance remain partial. No unrelated NASA-wide acquisition was performed.

## H. Frozen final evaluation

`evaluation_split.json` was frozen before extraction changes, with 290 source memberships and 36 held-out source records. Title normalization groups exact-title lineages; 25 eligible domain candidates from that holdout were processed only after `contract_freeze.json` was written following successful final gates. `holdout_coverage.json` records 25 successful staged packages and zero new inference calls. `final_holdout_protocol.json` verifies that runtime/test/ontology contracts and membership digests remained unchanged.

The split is **not** claimed to prove genuinely unseen investigation generalization. Historical source/model exposure is not excluded, and different publications from the same investigation may have different titles. No hidden human answers or independent scientific relevance labels were available or invented. No holdout scientific package was automatically approved. This evaluates isolated preparation contracts, not independently established scientific precision or incorporation-to-answer generalization. The latter remains NOT_MEASURABLE.

## I. Executed end-to-end incorporation

The application service accepted original bytes; prepared isolated proposals; generated shared questions and concrete alternatives; applied reviewed choices/corrections; revalidated; authorized exact digests; published immutable RDF; synchronized evidence/FTS; retrieved source-grounded results; rolled back; and reactivated.

- `pilot/`: known-schema real PSI-98 import, exclusions, thickness, shared decisions, seven actual queries, stale-approval and injected failure recovery.
- `prose/`: real PDF, four selected epistemic statements, exact-source correction preview and publication.
- `e2e_v3/`: real new observation subtype, new author-attribution relationship, actual service queries, five unchanged regeneration cycles, rollback/reactivation.
- `language_v3/`: actual fresh natural-language modification, revalidation, exact approval/publication and rollback; negative and ambiguous controls.
- `revision/`: meaningful source-backed duration publication and retrieval, followed by rollback/reactivation.

Earlier `e2e/` and `e2e_v2/` stopped at source-span selection because line breaks defeated fixture matching or phrase extraction; they are not acceptance runs. Original inputs and unsuccessful question receipts were preserved. Development test approval is not NASA institutional authorization. Actual browser file-upload automation and independent scientist usability were not performed; backend uploads and real Streamlit widgets were exercised.

## J. Scientific answers and resolvable evidence

The actual service response in `e2e_v3/queries.json` states:

> Several test samples maintained a flame down to 4 psia and when the vent valve was opened to continue depressurization of the test chamber, the fire was re-ignited.

It cites **E-314ab314f123e9b1b937bdd0**, resolving to the unchanged source PDF, page 11, in the isolated EvidenceRegistry. Its interpretation query separately returns the author's insufficiency conclusion, with the same original paragraph evidence and the reviewed author-attribution edge. This does not recommend a spacecraft depressurization procedure.

`revision/measurement_query_final.json` returns **420 s for S1 and 70 s for S2**, under the imported Saffire context. `prose/prose_query_after.json` retains the explicitly tentative oxygen explanation and future CFD question. DIRECT/RELATED traces and original citations are included in each full response. A requested gravity condition is a restriction on DIRECT eligibility; an unspecified condition is not silently introduced.

## K. Integrity and executed gates

`quality_receipt_v2.json`: `uv run ruff format --check .`, `uv run ruff check .`, and `uv run pytest -q` all pass; **304 tests** passed. Fresh baseline execution was **298 tests**, rather than merely copying the earlier report. The first final gate caught a driver-formatting defect; its receipt was retained before the passing second run.

`scientific_integrity.json`: canonical and native/generated SHACL pass; **7,266** graph evidence references all resolve; SQLite reports `ok`; foreign-key violations and missing FTS rows are zero. This audit was executed after class/relationship incorporation and before the duration revision; that revision separately passed normal publication SHACL and rollback checks.

`preservation.json`: all **600** frozen raw/canonical/evaluation/historical-receipt/main-registry files are unchanged. `baseline.json` additionally freezes source/ontology/domain digests. `final_holdout_protocol.json` records zero runtime contract changes after final evaluation. `ui_receipt.json` records zero widget-rendering exceptions. `secret_exclusion.json` records no configured secret values or `.env` in the audited artifacts. No API key is necessary for the test suite or guided review.

Generated domain/range shapes reject isolated graph corruption; hypotheses cannot become observations; wrong endpoint directions and unauthorized approvals fail; unchanged drafts retain their digest; excluded preliminary rows remain inactive. Historical regressions and V1/V2 contracts pass. Experimental vectors remain disabled; enabled-vector publication/synchronization is not demonstrated. These integrity checks do not substitute for independent scientific judgments.

## L. Decisions and remaining requirements

Machine-readable decisions with evidence are in `decisions.json`.

```text
DYNAMIC_SCIENTIFIC_CLARIFICATION = PARTIAL
CLOSED_FORM_QUESTION_GENERATION = VALIDATED
NATURAL_LANGUAGE_FALLBACK = PARTIAL
CLARIFICATION_DEPENDENCY_GROUPING = VALIDATED
HUMAN_REVIEW_REDUCTION = DEMONSTRATED
SCIENTIFIC_CORRECTION_APPLICATION = VALIDATED
CURATION_IDEMPOTENCE = VALIDATED
GENERIC_NEW_CLASS_SUPPORT = VALIDATED
GENERIC_NEW_RELATION_SUPPORT = VALIDATED
ONTOLOGY_BACKWARD_COMPATIBILITY = VALIDATED
ONTOLOGY_QUERY_EXTENSIBILITY = PARTIAL
SCIENTIFIC_PROSE_EXTRACTION = PARTIAL
OBSERVATION_CONCLUSION_LINKING = VALIDATED
EPISTEMIC_FIDELITY = PARTIAL
SCIENTIFIC_REVIEW_UI = OPERATIONAL
CONTROLLED_KNOWLEDGE_PUBLICATION = VALIDATED
PUBLICATION_ROLLBACK = VALIDATED
DOMAIN_CORPUS_INVENTORY = PARTIAL
DOMAIN_CORPUS_PROCESSING = PARTIAL
DOMAIN_SCIENTIFIC_COVERAGE = PARTIAL
HOLDOUT_GENERALIZATION = NOT_MEASURABLE
NEMOTRON_CLARIFICATION_VALUE = DEMONSTRATED
END_TO_END_SCIENTIFIC_INCORPORATION = VALIDATED
INDEPENDENT_SCIENTIFIC_RELEVANCE = REVIEW_REQUIRED
V2_DEFAULT_PATH = KEEP_EXPERIMENTAL
READY_FOR_PHASE_4 = NO
```

Remaining requirements are scientist review of staged sources/attribution, richer general narrative experiment/group/condition structuring, scientifically justified scope grouping and reusable contracts beyond quantities, comprehensive natural-language relationship queries and fallback interpretation, supported modeling for ontology families not exposed by the native registry, HTML/special-source preparation, exhaustive relevant inventory reconciliation, enabled-vector synchronization validation and an independently reconciled genuinely unseen investigation evaluation. These are not NASA knowledge gaps. Normal preparation and review use application runtime APIs and widgets; Codex is not a normal processing component.
