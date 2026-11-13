# Phase 3C release-candidate baseline and finite exit gates

The current implementation passes its technical regression and storage-integrity checks. The release decision is **HOLD for source-attribution and correction validation (G2/G3)**: six deliberately false, structurally valid corrections receive `ready=true`. This is a demonstrated backend defect, not a demand to complete every previous PARTIAL feature. Lifecycle checks pass, but G6 cannot authorize release while those critical defects remain. Phase 4 is not started or authorized.

The proposed technical RC is bounded to the existing no-key evidence assistant, experimental native V2 and isolated scientist-reviewed curation. It excludes public deployment, enabled vectors, comprehensive scientific-domain accuracy and claims of independently unseen investigation generalization. Expert approval remains necessary for scientific incorporation; configured development approval is not NASA institutional authority.

## Repository and audit boundary

Repository: `/home/liam/NASA`. Inspected HEAD: `b55b717fd7efc4d998cdf75cc73cc79fc07f1367`. There are no commits or tracked changes since `b55b717`; the initial worktree was clean. This was established by fresh Git execution, not assumed from the campaign. The campaign report describes changes relative to its own earlier `baseline.json`, which is a different comparison from changes since the present Git commit.

This audit read `AGENTS.md`, `docs/PHASE3C_GENERALIZATION_V1.md`, the current curation contract and implementation, scientific extraction and context contracts, QueryIntentV2/SemanticRegistry, native query interpretation/selection, Phase3AssistantService and EvidenceRegistry. Relevant paths are:

- `docs/PHASE3C_CURATION_V1.md`; `src/nasa_fire_ai/services/curation.py`; `app/curation_view.py`.
- `src/nasa_fire_ai/llm/scientific_correction.py`; `src/nasa_fire_ai/llm/interfaces.py`; `src/nasa_fire_ai/ingestion/scientific_proposals.py`; `src/nasa_fire_ai/context.py`.
- `src/nasa_fire_ai/query/{v2,native,native_interpreter,evidence_selection}.py`; `src/nasa_fire_ai/ingestion/semantic.py`; `src/nasa_fire_ai/services/phase3.py`; `src/nasa_fire_ai/evidence/registry.py`.
- `domain/{semantic_registry,incorporation,query_language_v2,legacy_semantic_projection}.yaml`; `ontology/{fire_safety,shapes,semantic_shapes}.ttl`; generated `extension_shapes`; `tests/test_curation.py`.

The entire `artifacts/phase3c_generalization_v1/` tree was inventoried and hashed; every JSON artifact was parsed. Both artifact indexes were checked: 621 original artifact entries and 624 v2 artifact entries match their recorded sizes/digests. The older index omits later clarification/model receipts and indexes, and its separate report entry describes an earlier document digest/size. The v2 report entry matches the current document; the complete RC inventory includes the later files. These version differences are nonblocking and explicitly recorded in `final_validation_receipt.json`. There are 338 parseable JSON files, including per-source quality, coverage, holdout, scientific, clarification, publication and rollback receipts. This is forensic inspection of all artifact identities and structured receipts, with scientific content checks described below; it is not expert adjudication of every proposed passage.

Fresh checks preserved all 1,260 protected files in data, evaluation, runtime, application, contracts, tests, scripts and campaign artifacts. The historical campaign preservation claim was separately reproduced for all 600 frozen immutable files. All 125 frozen runtime/test/domain/ontology contracts and the evaluation membership digest still match. Production code, original NASA sources, main registry, historical receipts and frozen evaluation material were not changed. Only this document and audit artifacts were created. No corpus proposal was approved or published. No live paid inference was invoked.

## Reproduction and claim verification

Fresh execution receipts, complete command output, timestamps and environment versions are in `artifacts/phase3c_rc_baseline/`. Commands:

```bash
uv run ruff format --check .
uv run ruff check .
uv run pytest -q
PYTHONPATH=src uv run python artifacts/phase3c_rc_baseline/reproduce.py
uv run ruff format --check artifacts/phase3c_rc_baseline/reproduce.py artifacts/phase3c_rc_baseline/build_assessment.py
uv run ruff check artifacts/phase3c_rc_baseline/reproduce.py artifacts/phase3c_rc_baseline/build_assessment.py
uv run python artifacts/phase3c_rc_baseline/build_assessment.py
```

The reproducer uses SQLite read-only connections for historical databases, performs canonical/native/generated SHACL, checks publication RDF/approval/package identity, and exercises unapproved synthetic negative fixtures only in discarded temporary workspaces. It writes new audit receipts. Quality subprocesses receive explicitly empty provider-key variables. `uv.lock`, `uv pip freeze`, Python/platform and `uv --version` are recorded. The original campaign drivers were inspected but not run into their historical output directories; several create exclusive receipts or can mutate development workspaces. The isolated publication/rollback paths are freshly exercised by the existing full test suite.

The audit driver initially needed its import path/lint corrected and later failed on an incorrectly named group predicate in its own synthetic fixture. The predicate was corrected to the existing `belongsToExperimentFamily`; the complete audit was repeated successfully. These were audit-driver failures, not product regressions. `audit_execution_notes.json` retains that distinction. Original extraction, review and provider calls were not relabeled fresh.

| Claim | Classification | Fresh result and boundary |
| --- | --- | --- |
| 304 passing tests | REPRODUCED | 304 pass; 72,960 rdflib deprecation warnings retained. |
| Ruff format/lint pass | REPRODUCED | Both repository commands pass; new audit scripts separately checked. |
| 224 prepared review packages | REPRODUCED | Current read-only recount: 199 development + 25 holdout latest packages. Full extraction/review events were not repeated. |
| 11 grouped review decisions | REPRODUCED | Retained pre-duration-revision package has 11 decisions. The clarification receipt list has only ten; initial table-role decision is in the package. |
| 26 affected dependencies | REPRODUCED, narrowly | 26 summed affected-record memberships; not 26 unique records or dependency nodes. Ten listed receipts sum to 22; table-role decision contributes four. |
| 7,266 resolvable evidence references | REPRODUCED | Pilot native graph has 7,266 unique resolvable evidence IDs. Main graph has 7,237. These include documentary references, not 7,266 independent scientific findings. |
| Scientific integrity/publication identity | REPRODUCED | Canonical/native/generated SHACL pass; four databases report `ok`; FTS missing/duplicate/orphan and missing-document counts are zero; six retained RDF publication checksums match approvals/packages. |
| Corpus acquisition/structure | REPRODUCED | 228 candidate originals rehashed; 227 searchable; six candidate source IDs referenced by historical canonical records. |
| Fresh Nemotron behavior and human workload | REPORTED_ONLY | Historical outputs and token receipts inspected; no new provider execution or independent scientist-time measurement. |
| General semantic rejection of valid-looking false corrections | FAILED | Six false corrections accepted as ready previews. |
| Independent unseen-investigation scientific accuracy | NOT_REPRODUCIBLE | No independent expert gold or exposure control; campaign correctly calls it NOT_MEASURABLE. |
| Enabled-vector publication synchronization | NOT_REPRODUCIBLE | Disabled configuration, no enabled-path receipt; excluded from RC. |

`claim_verification.json` defines the classifications and records each claim's receipt and scope. REPRODUCED includes fresh recounts of persisted state, explicitly distinguished from rerunning the historical events that produced it.

The pilot graph is now 22,141 triples and includes the subsequent duration revision. Its evidence count still reproduces the earlier 7,266 claim. Main native graph is 21,674 triples. `foreign_key_check` has no violations, but audited tables declare zero foreign keys; explicit document, pointer and publication joins provide additional checks. Neither SHACL nor checksum/provenance integrity proves scientific entailment.

## Scientific correction audit

Nemotron is advisory. `interpret_correction` bounds complete context objects, requests typed operations with a finite output/timeout budget and zero SDK retries, normalizes limited provider syntax and sends proposals to `preview_correction`. Application independently checks editable IDs, registered vocabulary, relationship kinds/domain/range, evidence membership, numeric reconstruction, units, original inputs/spans, uncertainty upgrades and simultaneous identity conflicts. `apply_correction` re-previews against the current digest. None of these steps is a general source-entailment verifier.

The actual original NTRS 20260003546 PDF states the Nomex outcome as two of four tests on page 8. Its SHA-256 is `b4b64e88992718a7598000ad85d181ac4d9c06ed58e0ae7df0fb4188a6662a18`; exact extracted wording/page/offsets are retained in `provenance_receipt.json`. In `language_v3/corrections.json`, Nemotron's notes explicitly recognize that “all four” contradicts the original. However, its operation proposes an unrelated material relationship to the unregistered `Nomex` endpoint. The backend rejects **Unknown relationship endpoint**. The note shows contradiction-aware model commentary, but it is not an independent validator and did not supply the operative rejection reason. Counting this as backend scientific refusal would be incorrect.

There is no supported statement-text replacement operation. Directly changing the synthetic two-of-four statement to all-four fails exact-source-span validation. This is a source-fidelity safeguard; the historical model operation did not actually request that mutation. It does not show that valid endpoint/scope/classification operations with false meanings are rejected.

Fresh negative diagnostics in `correction_negative_cases.json` use explicitly synthetic rows A1/B/microgravity/20 cm/s and A2/C/normal-gravity/10 cm/s. These are not fabricated NASA observations and were never applied or published.

| Negative case | Backend result | Rationale assessment |
| --- | --- | --- |
| Add normal gravity while microgravity remains | Rejected | Genuine equal-scope identity conflict. |
| Remove microgravity, replace with normal gravity using A1 evidence | Accepted, ready | Contradicts original row; evidence existence is insufficient. |
| Replace B group with C while retaining A1 evidence | Accepted, ready | Wrong source-row membership. |
| Reassign A1's 20 cm/s value to A2 | Accepted, ready | Number/span unchanged, measured subject wrong. |
| Change reported 20 to 999 while retaining expression 20 | Rejected | Scientific numeric reconstruction detects mismatch. |
| Attribute A1-only author conclusion to A2 | Accepted, ready | Existing target identity is checked; original scope is not. |
| Attribute A1 observation to A2 | Accepted, ready | Same attribution defect; existing test accepts then repairs this case. |
| Hypothesis to observation | Rejected | Explicit uncertainty upgrade safeguard. |
| Observation to author conclusion | Accepted, ready | Registered epistemic pair passes without author-conclusion evidence. |
| Replace two-of-four wording with all-four directly in draft | Validation error | Exact original span absent; direct mutation boundary, not model semantic refusal. |

These six ready previews are independently sufficient to justify the G2/G3 hold. This audit did not approve them to demonstrate publication; the ordinary publication contract accepts ready packages after exact-version human authorization, so the defect concerns approval eligibility rather than an observed unauthorized publication.

ScopeResolver prioritizes local context and preserves conflicts among supplied authoritative contexts. In curation, an edited gravity relationship is itself wrapped as `EXPLICIT_LOCAL`. Removing the original relationship removes the competing identity; there is no independent comparison to the unchanged source row at that point. Similarly, validators ensure quantities and statement text occur somewhere in supplied evidence, but do not enforce their original run/group membership. The corrective scope should be those concrete bindings, not a new scientific inference engine.

## Coverage, relevance and frozen holdout

Current inventory has 290 registry sources and 295 documents, with 7,237 indexed passages. There are 228 heuristic domain candidates. The reconciliation is **228 = 224 prepared drafts + two skipped exact-content duplicates + one candidate without indexed text + one failed HTML preparation**. Development contributes 199 drafts and holdout 25. A Windows-1252 retry recovered PSI-69 without changing source bytes; PSI-98's overview HTML remains unsupported. Its experimental CSV was separately demonstrated in the pilot.

Historical canonical `records.json` contains 3,831 records: 405 runs, 405 samples, 3,002 conditions and the remaining documentary/scientific record types listed in `provenance_receipt.json`. Six candidate sources appear in historical canonical evidence references; that does not establish six complete investigations. Isolated pilot state has five latest packages, three active packages and six publication versions; the main database has no curation publication tables. The two corpus workspaces have zero approvals/publications/active packages.

| Proposed scientific content | Development | Holdout |
| --- | --- | --- |
| Run entities/table rows | 1,136 | 0 |
| Values | 32 | 0 |
| Observations | 1,624 | 336 |
| Author conclusions | 214 | 46 |
| Hypotheses | 0 | 1 |
| Tentative interpretations | 108 | 26 |
| Open questions | 55 | 20 |
| Draft relations | 1,139 | 0 |

These distributions were freshly recounted from latest package payloads. The separate bounded extraction ledger reports 1,256 development and 245 holdout propositions; they overlap document-level proposals and must not be added as independent discoveries. Registry staging also contains historical candidates and rejected proposals, so its raw row count is a different denominator. All 270 stored package versions across development, holdout and pilot have matching payload digests, original input digests/sizes and statement spans.

Title selection is not scientific relevance. A concrete example is the NASA-STD-6001 draft: procedural text such as “shall be observed and recorded” is proposed as `measured_observation`. The source and exact span are real; the proposed epistemic role describes an instruction as an observation. Examples are retained with IDs/evidence in the provenance receipt. They are unapproved corpus proposals, not published scientific findings. This warrants a narrow extraction/classification safeguard and scientist review; no independent precision score is available.

The retained NASA inventory snapshot lists 19 combustion investigations. Its bytes/digest were inspected; this audit does not claim a newly fetched official inventory or exhaustive public NTRS/PSI coverage. Publication versus review identity, scientific relevance, supersession and dataset-version overlap remain unadjudicated. PSI version metadata and separate publications exist, but neither title proximity nor filenames justify merging them into an investigation or treating multiple versions as independent experiments.

Frozen membership remains 223 development, 31 validation and 36 holdout sources. Exact-title lineage keys and NASA IDs have no cross-partition identity groups. **Content hashes do**: `local-ntrs-20205007829` in validation and `ntrs-20205007829` in holdout share digest `769f062bb966340ee568170f39c311dee12a6a774a680137c3994a21e66c7b78`. The holdout duplicate was skipped, so it is not one of the 25 prepared holdout packages. Nevertheless, the membership is not a content-disjoint evaluation.

Lexical Saffire titles appear in eleven development sources and one holdout source; FLEX titles span development and validation. These are lineage risk indicators, not scientifically adjudicated identities. Moreover, both isolated corpus databases contain the historical 290-source/7,237-passage registry and caches, so package separation does not exclude documentary or historical model exposure. Different-title publications and version overlap are not reconciled by exact-title grouping. Zero new holdout inference is reported by its receipts; it does not establish absence of prior exposure. Frozen gold and memberships were preserved. The current holdout supports preparation-contract accounting, not independently validated scientific accuracy, recall or incorporation-to-answer generalization.

## Six finite exit gates

`exit_gates.json` supplies implementation/evidence, verified defects, exact acceptance tests, numerical thresholds, critical/noncritical failures, external scientific dependencies, blocking decisions and the smallest correction for each gate. Thresholds are proposed software release criteria, not NASA-endorsed scientific standards.

| Gate | Current assessment | RC blocking boundary and finite acceptance |
| --- | --- | --- |
| G1 Technical integrity/reproducibility | PASS | Zero failures in 304 existing tests, Ruff, canonical/native/generated SHACL, SQLite, explicit orphan/FTS checks, publication digests and preservation. Deprecation warnings and absence of FK migrations are noncritical. No scientific dependency. |
| G2 Narrative/contextual attribution | HOLD | Zero known source-row contradictions may be ready. Require exact original values/units/spans, original row/run/group binding, explicit local exceptions and source-backed author roles. Unresolved prose remains documentary/review-required. General narrative recall and full condition extraction are noncritical; ambiguous attribution requires scientists. |
| G3 Clarification/correction correctness | HOLD | All six accepted negatives must become evidence-grounded rejections or unresolved previews, never ready. Valid-ID mocked provider cases must agree with direct typed validation; zero incidental rejections counted scientifically. Positive source-backed changes, ambiguity, no-key choices, idempotence and stale-preview tests must still pass. Arbitrary-language coverage and general cross-package reuse are noncritical. |
| G4 Ontology/NL retrieval | PASS within supported contracts | Existing compatible class/relation/quantity tests must pass 100%; zero silent terms, reversed contracts or unsupported migrations. Fixed queries below preserve original IDs/citations and epistemic roles. Unsupported ontology families or unresolved paraphrases do not block this RC. New scientific definitions/aliases require expert approval. |
| G5 Corpus/review readiness | PASS for review only | Account for all 228 candidates, hash 100% of originals, retain 224 drafts with evidence/blockers and zero automatic approvals. Preserve frozen gold; make zero unadjudicated scientific-generalization claims. HTML support, exhaustive coverage and independent precision are noncritical for this technical RC; external experts supply relevance/lineage labels. |
| G6 Incorporation/rollback/release | Lifecycle PASS; release HOLD | Zero unauthorized/stale activations, partial visible failure states, rollback/reactivation mismatches, checksum failures or unreviewed corpus activations. Re-run after G2/G3 fixes; zero unresolved critical gates. Development authority and disabled vectors remain explicit; public deployment and usability study are outside scope. |

The fixed G4/G6 source checks are the actual existing service scenarios: sustained-flame observations about depressurization; the author's linked insufficiency conclusion; original Nomex two-of-four outcome; explicitly tentative oxygen interpretation; future CFD open question; Saffire S1/S2 thickness 0.37 cm; BurnDuration S1 420 s/S2 70 s; and a microgravity restriction on gravity-unspecified prose yielding RELATED rather than invented DIRECT applicability. Compare exact source-backed records/citations and statuses, not free-text stylistic equality. Existing `test_generic_class_relation_and_actual_assistant`, `test_reject_existing_concept_and_epistemic_upgrade`, `test_measurement_retrieval_and_approved_rdf_integrity`, repeated regeneration/publication/rollback and authority/failure-recovery tests provide the executable foundation. Historical real-source answers are receipts; fresh synthetic/service regression tests do not establish independent expert validation of their scientific classifications.

Release can proceed only when the bounded critical source-binding/role defects are corrected and the same checks pass. It does not require a new graph, truth database, ontology platform, agent framework, frontend, live model campaign, wholesale ontology expansion or completion of every earlier PARTIAL label.

## Prioritized corrective backlog — not implemented

1. **P0:** Enforce original table row/run/group bindings for gravity, group membership, quantities and statement scope in the existing preview/apply validators. Reject explicit contradictions with source-specific rationale; keep unresolved prose applicability under review.
2. **P0:** Require explicit original author-role support for observation-to-conclusion changes; do not let registered class/epistemic pairs alone authorize a scientific role change.
3. **P1:** Add valid-endpoint negative expectations and mocked Nemotron parity cases to the existing curation tests. Update the test that currently accepts wrong attribution, preserve supported correction positives, and rerun G1/G6. No paid call is required.
4. **P1:** Add a narrow normative-language extraction guard for the demonstrated `shall be observed` cases, using existing ontology roles or unresolved documentary status. Expert review resolves ambiguous passages.
5. **P2:** Complete future clarification receipts with the initial table-role event; retain content-hash and exposure annotations alongside the frozen split. Any future independent evaluation needs separately versioned expert lineage/relevance adjudication, without rewriting historical gold.

`risk_register.json` links each work item to independently observed evidence and its release impact. Broad acquisition, speculative query features, enabled-vector rollout and production authentication are excluded from this corrective backlog. Work stops at this baseline and exit-gate assessment.
