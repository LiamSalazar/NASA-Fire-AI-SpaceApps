# Phase 3C scientific incorporation — version 1

The guided incorporation path is operational for compatible text-backed research packages. It prepares an isolated draft, resolves shared decisions, previews corrections, authorizes an exact digest and activates approved RDF through the existing scientific query service. Full automatic scientific preparation and unrestricted natural-language correction are **partial**. Independent scientific correctness and institutional authorization are not established by this development campaign. V2 remains experimental; Phase 4 has not begun.

## Implementation and retained components

New runtime components are `services/curation.py`, `llm/scientific_correction.py`, `app/curation_view.py`, `domain/incorporation.yaml` and `scripts/curate_research.py`. The presentation file contains structural header hints and epistemic role labels, not an independent scientific ontology or frontend database schema. `ontology/incorporation_mappings.ttl` contains seven conservative alignment hints. The existing Material class is exposed in SemanticRegistry; its definition was already present in `ontology/fire_safety.ttl`.

Integration changes are in `ingestion/semantic.py`, `services/phase3.py`, `services/native.py`, `services/scientific_synthesis.py`, `models/__init__.py` and `app/streamlit_app.py`. Preparation reuses generic table profiling, registry alias/unit resolution, PyMuPDF and exact-span scientific proposal extraction. Shared gravity applicability uses the existing ScopeResolver. Projection uses SemanticGraph, QueryIntentV2, normal native retrieval, FTS5, existing claim selection and the mandatory emission verifier. NVIDIA uses the existing structured client and environment loader. Jev remains unchanged and optional. Existing maintenance, scientific proposal staging, historical canonical inputs, V1 and experimental vector retrieval remain available.

There is no second scientific graph, QueryIntentV3 or new runtime dependency. Draft/review JSON in the Evidence Registry records proposed meaning and editorial history. Approved scientific entities, values, relations and quantity contracts are immutable RDF versions under `data/canonical/research/<digest>.nt`. These versions augment the same native graph used for historical knowledge. Input paths, checksums, file/row locators, identities of approving principals and activation pointers remain operational registry data.

## Source-to-knowledge lifecycle

1. Submission accepts original PDF, CSV, TSV, text, Markdown and documentary JSON bytes. Content-addressed originals are retained under `data/submissions/`; `data/raw/` is untouched. Duplicate title/content packages reopen the previous draft, independent of filename order.
2. Parsing retains original row values, source units, PDF pages and input digests. Tables yield proposed runs, registered material identities, groups, conditions and source statements. Prose extraction yields exact-span propositions, never automatic scientific authority. Nested JSON is documentary input, not a fully generalized structured experiment parser.
3. Review templates derive classes, relations and quantity contracts from SemanticRegistry, existing ontology classes and SHACL constraints. Existing approved quantities, including quantities added through previous active packages, are reusable by a compatible new table without changing Python.
4. Dependencies group column mapping, ambiguous material identity, table execution role, campaign context and prose scope. A question carries its evidence and affected record count. Questions rank by affected structures, not model confidence or a forced maximum review count.
5. A guided choice or correction preview changes an isolated version. Typed correction operations can change group/material/gravity relations, statement scope, quantity semantics, source-supported values or labels, epistemic classification, and documentary exclusion. Source rows and wording remain immutable. Reopening an earlier decision makes a new version and retains its prior decision receipt.
6. Validation checks original submitted bytes, parsed rows, evidence identity, exact source expressions, numeric expression/value agreement, registered vocabulary, unit dimensions, relation endpoints and kinds, conflicting identities, epistemic classification and applicable scope. Unsupported structures remain blocked or are explicitly retained as documentary material.
7. Approval records creator/version, exact package digest, approving principal, timestamp and development authority. A later change invalidates the earlier approval for publication. Browser-entered names do not confer authority. The UI has no production authentication and keeps real public publication disabled.
8. After approval, the service prepares deterministic RDF, runs native SHACL and writes an immutable, checksum-protected RDF version. It then commits source/document/passages, evidence references, locators, FTS and the active digest in one SQLite transaction. A competing draft/quantity contract is rechecked under the activation lock. A failed commit leaves the last active version intact; an unreferenced prepared RDF file can remain as a recoverable artifact.
9. Normal Phase3AssistantService rebuilds its existing graph when active digests change, loads only checksum-verified selected RDF versions, restores their approved quantity contracts and recognizes reviewed investigation titles. Registry-resolvable citations pass through the existing final claim gate.
10. Rollback changes the active pointer without deleting historical approvals, RDF or original sources. Repeated activation is idempotent. Draft query preview runs the same service against a discarded registry copy and labels every response `DRAFT PREVIEW`.

## Scientist interface and operator setup

An operator configures one isolated development workspace:

```bash
uv run python scripts/curate_research.py --workspace /tmp/nasa-curation-demo initialize
NASA_CURATION_DEVELOPMENT=true NASA_CURATION_WORKSPACE=/tmp/nasa-curation-demo NATIVE_V2_QUERY_ENABLED=true uv run streamlit run app/streamlit_app.py
```

The scientist chooses **Incorporate research**, uploads materials, supplies the title and purpose, and selects **Prepare investigation**. The page shows proposed groups, runs/materials, quantities, observations/conclusions/open questions, original evidence, essential shared clarifications and approval readiness. It provides a scoped Graphviz graph with published references marked read-only. Forms add/remove relationships and restrict scope; no canvas framework migration or drag-and-drop graph editor was added.

The scientist can answer a shared question, explain a correction, preview/apply typed changes, revisit an earlier decision, propose/authorize a compatible quantity addition, regenerate, preview a draft question, download a portable package, and authorize the exact visible digest. The checkbox resets for a changed digest. **Approve and incorporate** performs publication automatically. The **Scientific questions** view uses the same configured development workspace.

`ui_final_receipt.json` records real widget rendering with zero exceptions. `test_scientific_ui_actual_widgets` operates the actual consent checkbox and incorporation button and verifies activation. Upload bytes enter the same submission service used by the page; browser file-upload automation and independent scientist usability evaluation were not performed. The displayed graph is an aid alongside guided forms, not a full graphical editor.

## Real-source acceptance receipts

The final runs are `pilot_v3/`, `prose_v2/` and `revision_v2/`. v1/v2 pilot directories retain intermediate behavior, failed audits and fresh model refusals; they are not final acceptance evidence.

### PSI-98 Saffire-I isolated re-import

Unmodified public experimental-table and metadata files were submitted through the application service. S1 and S2 became proposed runs. Two pretest visualization/camera rows were explicitly excluded from combustion-run publication and retained in original documentary evidence. No original Saffire canonical record was overwritten.

The source table and reviewed campaign context yield SIBAL Fabric, microgravity, airflow **20 cm/s**, Concurrent/Opposed direction and oxygen **21.5–21.7% / approximately 21.5%**. Original values and units remain present; canonical conversion of 20 cm/s is 0.2 m/s. Source evidence IDs are `E-101d939155b55113731b219d` and `E-e676d43a433ee76dd78cd97b`, with campaign context `E-91031fb6c0e6edcd7bcd74ed`. These are registry-resolvable references to original inputs.

A genuine missing quantity contract became an explicit `SampleThickness` proposal: definition, insufficiency of existing quantities, run domain, numeric range, original cm unit, evidence and compatible impact. After test-principal authorization, both source values **0.37 cm** were projected without editing ontology files manually for this study. Ordinary matching tables can subsequently reuse the approved quantity contract. Class/property equivalence is not inferred from a similar label.

The pilot made **11 shared decisions**, resolved **26 dependency-record memberships**, and avoided **15 potential repeated row prompts** by grouping. Two property mappings were already automatic. Two correction sets were approved. These are workload accounting measures, not elapsed-time targets or independently measured expert effort. Documentary choices explicitly withheld unsupported ancillary quantity semantics.

Seven fresh production-service queries verify conditions, material/gravity identity, new numerical-property retrieval and RELATED evidence. A normal-gravity request yields zero DIRECT and two RELATED imported runs. Observation/conclusion questions about this table alone appropriately abstain from unsupported outcomes.

### NTRS 20260003546

The second submission used the actual existing twelve-page PDF. The campaign prepared **23 epistemic prose propositions**; condition/intervention sentences detected by the shared extractor were not fully structured by this incorporation layer. Four independently selected current-source statements were authorized under an isolated test identity. Other cited-study/caption/attribution proposals remain documentary, not newly approved NASA findings.

Fresh final service outputs include the source-reported Nomex extinction outcome, the explicitly tentative oxygen interpretation, the author's Nomex conclusion and the stated future CFD work. The tentative interpretation remains `tentative_interpretation` after editorial approval; the future work remains `open_question`. The sentence beginning “At the point of extinguishment, it is not clear” is never upgraded to a demonstrated mechanism. No new observation-to-conclusion support relationship or individual-run attribution is inferred. Gravity remains unspecified for these statements.

The approved version digest is:

`cb68e02f44effbc0388db7c5c7fc6089fa6beab242969bc0ff1e824196f10426`

### Meaningful published-version correction

A later reviewed quantity addition represents the original Saffire **Burn Time (s)** column as source-reported `BurnDuration`, with **420 s** for S1 and **70 s** for S2. This changes the available scientific representation; it is not only a new version number. The earlier documentary decision is reopened with an explanation. The new Measurement records become available to the same Phase3AssistantService. Their authority is `RESEARCHER_CURATED`; development approval is not NASA institutional approval.

The final Saffire version digest is:

`ee60b4675c2b0d2c5fd95bc0c1fffb6118a26a26bea469f19cd261f6b82fc79d`

Rollback removes the newly represented measurements from active scientific retrieval and restores the previous approved version; reactivation restores them. Original durations remain in historical documentary evidence throughout. `meaningful_revision.json`, `meaningful_rollback.json`, `measurements_after_rollback.json` and `meaningful_reactivation.json` contain the exact receipts.

## Clarifications and corrections

Questions are generated from actual draft dependencies. Examples in `clarifications_initial.json` include:

- Whether the table describes executed runs or documentary/planned information, affecting all dependent rows.
- What `Sample Thickness (cm)` represents and whether it maps to an established quantity or needs a definition.
- What `Percent O2` represents; the reviewed mapping retains the original header and records `%` as its explicitly stated percent unit.
- Whether the source metadata's microgravity context applies to the submitted campaign, with local terrestrial exceptions preserved.
- Which source-supported investigation/runs apply to a grouped set of observations or tentative statements, with individual exceptions available.

The controlled tests also produce a single material-identity question for two `acrylic` rows and one `Wind (cm/s)` mapping question for two records. Incorrect mapping to pressure is rejected by unit validation; the approved airflow mapping resolves both records without duplicate questions. These fixtures are explicitly synthetic and are not NASA evidence.

Natural correction interpretation uses the existing NVIDIA adapter with a 35-second timeout, zero SDK retries, bounded output, an input window and typed validation. Four fresh calls consumed **36,399 reported tokens** across retained receipts. All four returned clarification/refusal rather than an accepted change set; no positive real-source Nemotron correction is claimed. They include redundant gravity assignments and a request to retain a tentative interpretation as documentary context. This is a product limitation even though refusal is safe.

The deterministic no-key grammar `Assign R1 and R2 to microgravity` produces a two-run preview and works through the same explicit approval and validation boundary. Guided controls perform broader scope/classification/value corrections. Incorrect provider endpoint output, conflicting context, fabricated numbers, wrong run attribution and stale previews are exercised by adversarial tests. Arbitrary natural-language semantic correctness is not established by JSON validity or endpoint checks.

## Ontology and standards boundaries

Compatible numeric/categorical quantity-property additions are operational, versioned and tested. New instances reuse existing classes. Previously approved quantities reload from selected RDF and participate in normal QueryIntentV2 property matching. General new class hierarchies, new object-property contracts and incompatible ontology migrations are not implemented by this minimal extension form. They remain explicit review/engineering blockers; unsupported relations are rejected rather than silently invented.

SHACL supplies structural validation and template constraints. PROV-O `wasDerivedFrom` links domain entities to source documents. SOSA/SSN and QUDT mappings are conservative `skos:relatedMatch` declarations, not scientific equivalence claims or imports of external ontologies. The downloadable research package includes original files, preparation metadata and RO-Crate 1.1 JSON-LD. Full RO-Crate profile validation and complete SSN/QUDT modeling are not claimed.

Primary specifications consulted: [SHACL](https://www.w3.org/TR/shacl/), [PROV-O](https://www.w3.org/TR/prov-o/), [SOSA/SSN](https://www.w3.org/TR/vocab-ssn/), [QUDT Velocity](https://qudt.org/vocab/quantitykind/Velocity), [RO-Crate](https://www.researchobject.org/ro-crate/1.1/).

## Domain coverage

The fresh official [NASA PSI combustion inventory](https://www.nasa.gov/physical-sciences-informatics-psi/psi-investigations-by-research-area/) yields **19 investigation names**. The independently reconciled local domain-candidate source ledger identifies **228 sources**: 228 acquired with verified digests, 227 parsed/searchable, and six referenced by at least one historical canonical record. Six structured sources does not mean six completely represented investigations. Per-source contextual completeness and independent scientific relevance are not measured.

The ledger preserves separate acquisition, parsing, searchability, structured representation, review and identity-reconciliation states. It records prioritized next actions for public PSI datasets, NTRS reports and source-specific scope/quantity attribution. Title candidates do not establish investigation identity. The official list plus the existing local collection is not a complete inventory of all public NASA combustion research. A broad NTRS/PSI semantic completeness audit remains partial. No unrelated NASA-wide ingestion was performed.

## Fresh quality and preservation

The untouched baseline passed **285 tests**. The final campaign adds thirteen tests covering grouped mappings/aliases, campaign-only context with a terrestrial control, unit incompatibility, wrong observation/run attribution, narrower conclusions, hypotheses/tentative/open statements, new quantity contracts, read-only published references, multiple-run corrections, incorrect provider output, conflicting correction, unauthorized publication, changed approval, duplicate upload, graph/index failure, idempotence, rollback, historical retrieval, draft isolation, real widgets and approved-RDF corruption.

The final full suite passed **298 tests**. Final receipts are `format_final_v4.txt`, `lint_final_v4.txt`, `pytest_final_v5.txt`, `final_integrity.json`, `final_queries.json`, `ui_final_receipt.json` and `secrets_exclusion.json`. Native and canonical SHACL pass. SQLite integrity is `ok`; foreign-key checks have no violations. All 7,254 graph evidence references resolve. The final graph has 22,058 triples. All **351 frozen raw/canonical/evaluation files** are unchanged; the main repository evidence database is unchanged. Publication demonstrations modified only isolated development workspaces. The secret scanner found no configured secret values and no `.env` in artifacts.

Foreign-key checks are integrity checks against the existing schema, not a claim that every legacy table has declared/enforced foreign keys. Experimental vectors remain disabled in the normal native path; enabled-vector synchronization is not demonstrated. Historical regression success is not an independent scientific accuracy label. Source-specific answers and their applicability are reported separately from historical behavior.

## Reproduction

Use new, exclusive artifact directories; preserve previous receipts:

```bash
uv run python scripts/phase3c_curation_pilot.py --directory /tmp/curation-replay/pilot
uv run python scripts/phase3c_curation_prose.py --directory /tmp/curation-replay/prose --workspace /tmp/curation-replay/pilot/workspace
uv run python scripts/phase3c_curation_revision.py --directory /tmp/curation-replay/revision --workspace /tmp/curation-replay/pilot/workspace
uv run ruff format --check .
uv run ruff check .
uv run pytest -q
```

The real-source scripts require the local public NASA corpus and historical registry. The standalone curation tests require no credentials. `--live` explicitly enables a bounded advisory call; fresh calls and fallback execution are distinguished in receipts. No runtime step depends on Codex.

## Final decisions

```text
SCIENTIFIC_PACKAGE_PREPARATION = PARTIAL
ONTOLOGY_DRIVEN_TEMPLATES = VALIDATED
MINIMAL_CLARIFICATION = VALIDATED
CLARIFICATION_RESOLUTION = VALIDATED
DUPLICATE_REVIEW_REDUCTION = DEMONSTRATED
NATURAL_LANGUAGE_CORRECTIONS = PARTIAL
SCIENTIFIC_REVIEW_UI = OPERATIONAL
SCOPED_GRAPH_EDITING = OPERATIONAL
EPISTEMIC_FIDELITY = PARTIAL
ONTOLOGY_EVOLUTION = PARTIAL
SCIENTIFIC_PROVENANCE = VALIDATED
APPROVAL_VERSION_INTEGRITY = VALIDATED
CONTROLLED_PUBLICATION = VALIDATED
PUBLICATION_ROLLBACK = VALIDATED
NEW_RESEARCH_QUERYABILITY = VALIDATED
HISTORICAL_KNOWLEDGE_COMPATIBILITY = VALIDATED
DOMAIN_CORPUS_INVENTORY = PARTIAL
DOMAIN_SEMANTIC_COVERAGE = PARTIAL
END_TO_END_INCORPORATION = PARTIAL
INDEPENDENT_SCIENTIFIC_RELEVANCE = REVIEW_REQUIRED
V2_DEFAULT_PATH = KEEP_EXPERIMENTAL
READY_FOR_PHASE_4 = NO
```

The remaining blockers are general prose-to-experiment identity/scope preparation, arbitrary natural-language correction interpretation, non-quantity ontology evolution, enabled-vector publication, production authentication/authority deployment, complete corpus reconciliation and independent scientific/usability review. A scientifically valid partial representation can be published without approving any blocked relation; this campaign does not equate engineering structural validity with scientific truth.
