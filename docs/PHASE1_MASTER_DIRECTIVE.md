# NASA FIRE AI — PHASE 1 COMPLETION AND ADAPTIVE KNOWLEDGE ARCHITECTURE
## Master Engineering Directive for Claude Code — Sonnet 5.5

### ROLE AND OBJECTIVE

Act as the principal scientific AI engineer, knowledge-architecture engineer and autonomous implementation lead for NASA FIRE AI.

Repository: `/home/liam/NASA` (verify the actual location).

Continue on the existing `diego/research` development branch, preserving all valid work previously completed by Codex and Claude Code.

**Your mission is to complete Phase 1 as a genuinely adaptive, scientifically faithful, reproducible ingestion system capable of processing previously unknown NASA investigations without source-specific programming or manually extending a rigid ontology for every new document.**

The purpose is NOT to optimize the current benchmark papers until their scores pass.

The purpose is to build a generalizable scientific processing architecture whose correct behavior naturally produces good precision, recall, traceability and stability.

This directive supplements and consolidates previous approved engineering requirements. It must inform implementation, persistent project documentation and subsequent development phases.

Do not stop after preparing reports or rewriting instructions. Implement the required capabilities in working production code.

---

# 1. PERSIST THE PROJECT VISION IN THE REPOSITORY

A critical requirement is that the architectural decisions must survive future Claude Code sessions, context resets and changes of development agent.

Before implementing new functionality:

1. Read the existing `CLAUDE.md`, if present.
2. Read `AGENTS.md`.
3. Read the current product specification, approved execution plan, Phase 1 report, architecture contracts and recent research-branch checkpoints.
4. Reconstruct what is already implemented and identify the actual remaining gaps.
5. Preserve existing instructions and repository policies.

Update the root `CLAUDE.md` so it permanently explains:

- What NASA FIRE AI is.
- Its two major subsystems.
- Its scientific domain and approved sources.
- Its six implementation phases.
- The boundary and relationship between Phases 1 and 2.
- The distinction between immutable scientific safeguards and adaptable knowledge structures.
- The rules for autonomous ontology evolution.
- The limits of LLM scientific authority.
- The scientist's role.
- The requirement to avoid source-specific overfitting.
- The quality and generalization acceptance principles.
- The need to inspect existing code before implementing anything.
- The rule that development assistants are not runtime dependencies.
- Links to the authoritative architecture and execution documents.

Keep `CLAUDE.md` operational, concise and readable rather than duplicating hundreds of pages.

If a complete architecture document already exists, update and reference it. Otherwise create one canonical architectural reference covering the following requirements.

Do not create several competing documents that describe different product architectures.

**Writing these instructions is necessary but insufficient. The architecture must actually behave according to them.**

---

# 2. COMPLETE PRODUCT VISION

NASA FIRE AI is an end-to-end scientific research and knowledge-evolution platform.

Its scientific scope covers official NASA research and verifiably NASA-associated investigations relevant to microgravity combustion, flame behavior, fire safety, materials, experimental conditions, combustion phenomena, suppression and the related scientific domain of *Flame in Freefall*.

It is not a generic document chatbot.

The platform has two major subsystems.

## A. Scientific knowledge creation

NASA FIRE AI must:

- Acquire scientific documents and datasets.
- Preserve original sources.
- Understand scientific document structure.
- Interpret experiments, observations, measurements and conclusions.
- Identify scientific entities and relationships.
- Reuse existing knowledge and ontology definitions.
- Discover genuinely new semantic structures.
- Extend knowledge representations compatibly.
- Preserve uncertainty and source provenance.
- Perform independent scientific validation.
- Request scientist clarification only where genuinely necessary.
- Prepare and maintain versioned scientific knowledge.

## B. Scientific knowledge consultation

NASA FIRE AI must:

- Answer natural-language scientific questions.
- Retrieve relevant evidence from the KG and original documents.
- Use documentary and semantic retrieval together.
- Explain experimental conditions and scientific applicability.
- Compare findings without erasing important differences.
- Preserve historical, corrected and refuted knowledge.
- Distinguish direct evidence, related evidence and interpretation.
- Expose original NASA documents.
- Support scientific investigation and visualization.
- Never present model-generated conclusions as NASA findings.

The ingestion system must prepare scientific representations suitable for these future consultation capabilities.

---

# 3. THE SIX PRODUCT PHASES

Preserve the approved six-phase implementation program.

## Phase 1 — Generalizable Scientific Ingestion

Receive heterogeneous NASA scientific sources, interpret their scientific meaning, recover evidence-grounded entities and relations, resolve existing semantic structures, prepare justified extensions and produce isolated scientific curation packages.

This phase must deliver working software, not merely extraction scripts or schemas.

**Phase 1 is the current implementation priority.**

## Phase 2 — Autonomous Scientific Curation and Ontology Evolution

Develop the complete mechanisms for:

- Reuse of existing ontology definitions.
- Autonomous detection of new semantic concepts.
- Compatible ontology extension.
- Resolution of conflicting or ambiguous classifications.
- Minimal scientist clarification questions.
- Closed-form answer alternatives when appropriate.
- Concise natural-language clarification fallback.
- Understandable previews of proposed entities, relations and changes.
- Correction of individual associations.
- Final authorized confirmation of a scientific workspace version.

The scientist should primarily use scientific-domain knowledge, not RDF, SHACL or software-engineering concepts.

The model must not request approval for every straightforward extraction.

## Phase 3 — Scientific Workspaces, History and Versioning

Implement Git-like scientific knowledge workspaces with:

- Shared approved baseline.
- Isolated researcher workspaces.
- Incremental knowledge changes.
- Semantic differences and history.
- Scientific source preservation.
- Attribution of modifications.
- Review and authorization.
- Reversible changes and rollback.
- Authorized promotion.

For the initial independent product, only authorized developers may promote a reviewed workspace to the shared baseline.

NASA institutional authorization is a later deployment concern.

## Phase 4 — NASA Scientific Library

Build a broad, traceable, relevant NASA scientific corpus with the agreed 2026 cutoff.

Inventory, acquire, deduplicate and process eligible NASA research.

Measure coverage and identify scientifically relevant gaps.

Leave suitable independent sources reserved for evaluation.

Do not indiscriminately ingest unrelated NASA information.

## Phase 5 — Scientific Research and Consultation

Complete evidence-grounded natural-language investigation, native KG and document retrieval, contextual reasoning, comparison, scientific status, original-source access and interactive research dashboards.

No unsupported safety rankings or invented scientific conclusions.

## Phase 6 — Integrated Product Release

Complete the scientist-facing product, demonstration environments, access control, usability, performance, reliability, recovery, deployment and end-to-end acceptance.

The first release must work independently of NASA institutional infrastructure.

Future NASA deployment and authorization are separate.

---

# 4. CRITICAL ARCHITECTURAL PRINCIPLE: STRICT SCIENCE, ADAPTIVE KNOWLEDGE

Previous engineering efforts may have become too focused on forcing scientific information into a small set of existing contracts.

This is incompatible with the intended product.

**Scientific integrity constraints must remain strict. Scientific vocabulary and knowledge-representation contracts must be extensible.**

Distinguish these layers.

## Immutable integrity contracts

These protect:

- Source identity and provenance.
- Original source bytes and expressions.
- Experiment identity and applicability.
- Original measurements, units and qualifiers.
- Scientific epistemic roles.
- Valid source attribution.
- Uncertainty.
- Historical scientific status.
- Authorization boundaries.
- Transactional integrity.
- Version compatibility.

Never weaken these merely to increase recall.

## Adaptive semantic contracts

These represent:

- Scientific classes and subclasses.
- Properties and quantities.
- Entity types.
- Object relationships.
- Material composition.
- Experimental configurations.
- New scientific concepts.
- New hierarchies.
- Semantic definitions and compatibility rules.

These cannot be treated as a permanently closed vocabulary.

The system must be able to propose, validate and stage extensions when a NASA source legitimately introduces previously unmodeled information.

An unknown concept must not be discarded solely because it does not match an existing YAML definition.

Do not solve this by adding an ever-growing number of manually coded source-specific properties.

---

# 5. AUTONOMOUS KNOWLEDGE ADAPTATION

The target behavior for previously unseen NASA research is:

### Case A — Knowledge already represented

Detect matching concepts, definitions, properties and relationships.

Reuse the existing approved semantic structures when scientifically equivalent.

Create new instances and source-grounded assertions using existing contracts.

Do not duplicate ontology classes because a publication uses different terminology.

### Case B — Knowledge partially represented

Reuse all compatible existing structures.

Identify what genuinely cannot be represented.

Propose minimal compatible additions, such as a new property, relation, subclass or contextual attribute.

Preserve all existing scientific meanings.

Do not force an inaccurate mapping to avoid extending the ontology.

### Case C — Genuinely new semantic knowledge

Discover the concept from its original documentary evidence.

Investigate its definition, scientific role and possible place in the existing ontology.

Generate a compatible semantic-extension proposal.

Validate its structure and evidence independently.

Stage the proposal within the isolated scientific workflow.

Do not invent a source definition that NASA did not establish.

Do not automatically publish the extension into the canonical ontology.

### Case D — Genuine ambiguity

Investigate the original source and existing definitions before requesting human clarification.

If uncertainty remains, preserve it explicitly.

Prepare a precise scientific question describing the real decision required.

Do not ask the scientist to solve ordinary parsing errors, configure RDF or write ontology contracts.

---

# 6. DYNAMIC CONTRACT EVOLUTION MUST EXIST IN PRODUCTION CODE

This requirement must not remain only in prompts or documentation.

Inspect the existing:

- SemanticRegistry.
- Scientific proposal structures.
- Ontology-extension staging.
- RDF/SHACL contracts.
- Entity and relationship resolvers.
- Quantity and unit representations.
- Source-evidence validators.
- CurationService.
- Document-context and scientific-coverage modules.

Reuse existing capabilities before adding anything.

Implement the missing production functionality so scientific knowledge can be represented even when it introduces unfamiliar concepts or relations.

A correct design may use an evidence-grounded intermediate proposal representation, but this must not become a competing scientific truth store.

The adaptation mechanism must distinguish:

- Class versus instance.
- Subclass versus contextual attribute.
- Equivalent concept versus similar concept.
- Material versus specimen.
- Material component versus formulation.
- Experimental configuration versus observation.
- Measurement versus derived quantity.
- Scientific property versus physical unit.
- New ontology relation versus existing relation with additional qualifiers.

### Example: material composition

A previously unseen material formulation may contain multiple components with documented proportions and scientific roles.

The system must be capable of identifying:

- The formulation or material.
- Its components.
- Their documented proportions.
- The basis of those proportions when known.
- The scientific role of each component.
- The experimental source and context.

Reuse existing compatible relations first.

If no suitable relation exists, propose a minimal generic extension.

Do not hardcode Salox-M, bronze or PTFE.

Do not create a new global property merely to make one evaluation objective pass.

### Structural validation

New proposal-level contracts must be versioned, inspectable and validated for compatibility.

If a genuinely new structure requires an extended SHACL shape or semantic rule, stage the proposed extension and validate it in isolation without modifying the approved baseline.

Separate:

1. A structurally well-formed proposal.
2. A source-supported scientific proposal.
3. A proposed ontology extension.
4. A scientifically reviewed change.
5. An authorized published baseline change.

These are not interchangeable states.

Do not require final global ontology approval merely to preserve and prepare scientifically valid new knowledge.

---

# 7. RELATIONSHIP BETWEEN PHASES 1 AND 2

Phase 1 must not stop functioning every time it encounters a concept that Phase 2 will eventually review.

The architectural boundary is:

**Phase 1 autonomously discovers, interprets, maps, validates and stages knowledge and necessary semantic extensions.**

**Phase 2 provides complete scientist-facing clarification, correction, semantic evolution and approval workflows.**

Therefore Phase 1 must already produce:

- Scientific entities and source-supported assertions.
- Reused ontology mappings.
- New-instance proposals.
- Proposed property and relation extensions.
- Relevant scientific definitions.
- Semantic alternatives when genuinely ambiguous.
- Dependencies between proposed changes.
- Source-backed explanations of relationships.
- Unresolved issues requiring scientific authority.

Do not build the complete Phase 2 UI now.

But do not design Phase 1 outputs that will have to be discarded or completely remodeled to implement Phase 2.

The same adaptive semantic mechanisms should remain useful in both phases.

---

# 8. REVIEW CURRENT IMPLEMENTATION BEFORE WRITING CODE

The current repository contains substantial work from both Codex and Claude Code.

Do not assume a capability is missing merely because an earlier report described it as incomplete.

Inspect actual source files, active contracts, current Git commits and tests.

For each required behavior, establish whether it is:

- Already implemented and verified.
- Implemented but defective.
- Partially implemented.
- Missing.
- Dependent on genuine scientific authority.

Reuse existing valid components.

Correct defects at their real architectural boundary.

Do not create duplicate numeric parsers, ontology registries, extraction engines, graph stores or model orchestration frameworks.

Do not regress earlier correct scientific attributions.

Preserve working table-continuity, evidence preservation, partial-output recovery, scientific scoring and curation capabilities.

The purpose is not to rebuild Phase 1.

**Complete the existing architecture and remove unnecessary rigidity.**

---

# 9. SCIENTIFIC EXTRACTION MUST BE SOURCE-DRIVEN

The model must not be the only mechanism deciding what scientific information exists in a paper.

Use original document structure to identify candidates for scientific interpretation:

- Investigations.
- Experimental runs and groups.
- Materials and specimens.
- Tables and rows.
- Quantitative expressions.
- Experimental conditions.
- Results.
- Observations.
- Author conclusions.
- Relevant scientific relationships.

Reconcile this inventory with model output.

When important source-backed information is omitted, perform targeted contextual recovery.

When a proposed entity or relation is incorrect, preserve independently valid evidence and recover its proper meaning where possible.

Do not accept fabricated assignments to increase coverage.

Do not count raw extracted characters or unprocessed table cells as fully structured scientific knowledge.

Avoid a pipeline in which the LLM can only propose entities that fit a rigid pre-existing list.

It must have a mechanism for representing genuinely new concepts without compromising scientific validation.

---

# 10. THE LLM MAY INTERPRET BUT MUST NOT CREATE SCIENTIFIC FINDINGS

This is a central product rule.

The LLM may:

- Interpret source language.
- Compare existing concepts.
- Recognize semantic equivalence.
- Identify experimental context.
- Construct candidate relationships.
- Propose structural extensions.
- Recover missing source context.
- Identify uncertainty.
- Prepare scientist clarification questions.

It may not:

- Invent NASA findings.
- Alter numerical values.
- Invent experimental conditions.
- Convert hypotheses into observations.
- Present calculated results as reported measurements.
- Invent causal relationships.
- Change the scope of author conclusions.
- Erase superseded knowledge.
- Declare scientific truth based on model confidence alone.

Every scientific statement must remain traceable to the original NASA evidence.

An LLM-generated explanation must never be confused with a NASA-authored conclusion.

---

# 11. SCIENTIFIC METRICS ARE CONSEQUENCES, NOT THE PRODUCT OBJECTIVE

The existing engineering acceptance targets remain:

- Scientific precision ≥95%.
- Fully correct scientific recall ≥80%.
- Zero known critical false accepted attributions in the adjudicated acceptance set.

However:

**Do not design, modify or optimize the architecture primarily to make these numbers pass on PTFE or other development investigations.**

These metrics measure implementation quality. They are not instructions to memorize the evaluation set.

Do not introduce:

- Paper-specific mappings.
- Hardcoded experimental identifiers.
- Expected answer dictionaries.
- Manually tuned vocabulary for individual holdouts.
- Document-specific postprocessing.
- Special-case validators that recognize benchmark values.
- Scorer adjustments intended to inflate outcomes.

A valid new semantic property must be justified by scientific meaning and general reuse, not benchmark performance.

Measure separately:

- Scientific recall.
- Scientific precision.
- Retention of original evidence.
- Correctly unresolved information.
- Omissions.
- Critical attribution errors.
- Per-document performance.
- Per-scientific-category performance.
- Run-to-run variability.

Do not count `UNRESOLVED` as fully recovered.

Do not achieve high precision merely by discarding most relevant knowledge.

---

# 12. GENERALIZATION AND REPRODUCIBILITY

NASA FIRE AI must process future eligible NASA research using the same general implementation, even when it encounters scientific concepts not present in the initial corpus.

No finite test set can prove universal accuracy on every future paper.

Therefore, demonstrate credible generalization rather than claiming an impossible guarantee.

## Development investigations

Use previously exposed papers such as PTFE, LUCI, ignition, regulators and textiles as development/regression material.

Their results are useful for correcting general engineering mechanisms.

They are not independent evidence of future-domain performance after being used to guide implementation.

## Structural and semantic generalization

Test whether general mechanisms work with:

- New scientific materials.
- New experimental configurations.
- Unfamiliar quantitative properties.
- Different document formats.
- Mixed tables and narrative.
- Alternative table layouts.
- Unknown scientific entities.
- Legitimate new ontology relations.

Use metamorphic tests that preserve meaning under formatting changes.

Use negative tests where a change in scientific meaning must change the representation.

Do not rely exclusively on synthetic tests.

## Fresh versus replayed inference

Distinguish:

- Revalidating saved model output.
- Running the complete ingestion process again with real inference.

These measure different properties.

Report all predetermined runs.

Do not cherry-pick the best output.

## Final independent validation

When development readiness is demonstrated, freeze the actual implementation, prompts, semantic contracts, models and evaluation rules.

Evaluate genuinely unexposed NASA scientific lineages without introducing source-specific code.

Prefer a heterogeneous independent evaluation over relying on one conveniently simple paper.

Preserve failures.

Report uncertainty and document-level variability.

A good result on PTFE alone does not close Phase 1.

---

# 13. MODEL AND ORCHESTRATION POLICY

Claude Code Sonnet 5.5 is the DEVELOPMENT agent.

It must not become a runtime dependency of NASA FIRE AI.

NASA FIRE AI uses independently configured scientific model APIs through its own provider abstraction.

The current working NVIDIA integration must remain available.

Any API comparison or adoption of Anthropic, Gemini or another model must follow separately authorized provider decisions.

Diego is responsible for providing/configuring additional credentials.

Do not silently change the production scientific model simply because the development agent is Sonnet.

## Orchestration

Inspect the real inference pipeline before changing it.

Previous runs have involved many sequential model calls and long provider delays.

Measure:

- Time to first output.
- Generation throughput.
- Repeated prompts/context.
- Independent versus dependent tasks.
- Avoidable repeated inference.
- Cache behavior.
- Recovery overhead.
- Actual scientific coverage per operation.

Implement justified improvements such as bounded parallelism, context reuse, task consolidation and targeted recovery while preserving scientific correctness.

Do not substitute one enormous model request for a coherent scientific extraction process.

Do not impose arbitrary token ceilings that truncate legitimate scientific content.

Preserve finite operational safeguards and resumable execution.

---

# 14. HUMAN INTERVENTION SHOULD BE EXCEPTIONAL AND USEFUL

The scientist must not be asked to validate every entity, every row or every routine ontology mapping.

Prioritize:

1. Source-based automatic resolution.
2. Existing ontology and semantic definition retrieval.
3. Contextual scientific analysis.
4. Independent validation.
5. Targeted additional recovery.

Only then escalate genuine unresolved scientific decisions.

Future questions should be concise, preferably closed-form, and explain the actual scientific decision in accessible language.

The scientist should be able to inspect proposed relations, correct associations and understand the scientific effect before confirming a workspace version.

Global baseline promotion remains authorized and separate.

Do not expose technical RDF/SHACL contracts as the scientist's ordinary interface.

---

# 15. IMPLEMENTATION CAMPAIGN — CONTINUE TO COMPLETION

Execute one continuous Phase 1 engineering campaign using the existing research branch.

## Internal Milestone A — Architectural consolidation

Verify existing functionality.

Update persistent Claude/project instructions.

Identify exact architectural rigidity that prevents new scientific knowledge from being represented.

Preserve existing working code.

Implement missing adaptive semantic staging and compatibility mechanisms.

## Internal Milestone B — Generalizable scientific ingestion

Complete source-driven coverage, quantity semantics, entity and subject resolution, scientific relationships, context recovery and semantic extension proposals.

Correct current defects across exposed investigations.

Integrate every correction into the normal production ingestion workflow.

## Internal Milestone C — Stability and scientific validation

Verify scientific fidelity and generalization across heterogeneous development investigations.

Repair demonstrated architectural defects.

Optimize actual inference orchestration where justified.

Run the established software, SHACL, integrity and publication-safety suites.

Perform independent evaluation only after readiness is demonstrated.

## Internal Milestone D — Reproducible Phase 1 delivery

Produce a usable end-to-end ingestion subsystem and exact scientific acceptance decision.

Create coherent commits on the research branch.

Preserve a concise continuation checkpoint.

Do not stop after writing the architecture documentation.

Do not create a separate planning campaign for every milestone.

---

# 16. NORMAL PRODUCT WORKFLOW REQUIRED

The implementation must support:

NASA research document  
→ immutable original-source preservation  
→ document and table understanding  
→ identification of scientific candidates  
→ contextual scientific interpretation  
→ reuse of existing ontology definitions  
→ discovery of missing semantic structures  
→ compatible semantic extension proposals  
→ scientific entity and relationship construction  
→ independent evidence and attribution validation  
→ targeted recovery of omissions  
→ preparation of genuinely unresolved scientific questions  
→ isolated knowledge-curation package  
→ access to the original source

This must operate through the existing NASA FIRE AI runtime and service interfaces.

No manual JSON repair by developers.

No Codex runtime.

No Claude Code runtime.

No unreviewed shared-baseline publication.

The output must be compatible with the future scientist review and workspace workflows.

---

# 17. PRESERVATION AND REGRESSION

Preserve:

- Original NASA source documents.
- Approved ontology and scientific baseline.
- Historical scientific knowledge.
- Frozen gold/reference evaluations.
- Source hashes and provenance.
- Existing KG and source registry.
- Earlier implementation checkpoints.
- Correct scientific attribution safeguards.
- Existing QueryIntentV2 and retrieval contracts.

Run the established Ruff, pytest, SHACL, semantic, source-integrity, idempotence and curation integration checks.

Add scientifically meaningful positive, negative and metamorphic tests.

Do not remove tests to obtain green results.

Do not modify historical evaluations to improve metrics.

Do not merge `diego/research` into `main` without authorization.

Do not commit credentials or expose environment secrets.

Avoid unnecessary storage duplication.

---

# 18. REQUIRED DELIVERABLES

At the end of this campaign, deliver:

### A. Persistent project instructions

Updated `CLAUDE.md` containing the complete persistent engineering principles and links to the six-phase architecture and authoritative specifications.

### B. Verified reuse of prior implementation

Identify significant existing capabilities preserved, incomplete capabilities repaired and genuinely new production functions implemented.

### C. Adaptive knowledge representation

Demonstrate existing-concept reuse, partial semantic extension and handling of a genuinely new scientific concept without paper-specific code.

### D. Working scientific ingestion

Demonstrate source-grounded extraction, entity resolution, scientific quantities, experimental scope, relations, coverage recovery and isolated staging.

### E. Scientific fidelity

Provide original NASA evidence for representative assertions, including rejected unsupported claims and correctly retained scientific uncertainty.

### F. Generalization evidence

Show cross-investigation development improvements, stability checks, metamorphic tests and valid independent evaluation when ready.

### G. Measured scientific quality

Report precision, recall, retention, omissions, critical errors and variability with explicit denominators.

### H. Performance and reproducibility

Report actual inference duration, call behavior, significant orchestration improvements, provider failures and successful resumability.

### I. Software quality

Provide passing and failing checks, exact commands, source-integrity status and publication-safety verification.

### J. Reproducible development state

Provide branch, commits, affected production modules, checkpoint and any precise remaining blocker.

---

# 19. DEFINITION OF PHASE 1 COMPLETION

Phase 1 is NOT complete merely because:

- PTFE exceeds 80% recall.
- Two favorable generations occur consecutively.
- Automated tests pass.
- Nemotron or another LLM returns valid JSON.
- The current ontology can represent all known benchmark values.
- An architecture document describes adaptation.
- New properties were manually added for test papers.
- Every original source character has been processed.

Phase 1 is complete when NASA FIRE AI demonstrates a reusable, independent scientific ingestion architecture that:

1. Handles heterogeneous eligible NASA research.
2. Recovers scientifically meaningful information with defensible fidelity and coverage.
3. Reuses approved knowledge structures where appropriate.
4. Can propose compatible extensions for genuinely new concepts, properties and relations.
5. Does not depend on document-specific engineering.
6. Preserves source provenance and epistemic meaning.
7. Prevents unsupported scientific attribution.
8. Retains genuine uncertainty.
9. Produces complete isolated scientific proposals suitable for Phase 2.
10. Demonstrates credible generalization and reproducibility using frozen independent evaluation.

No system can guarantee identical performance for every future NASA study. Do not claim such a guarantee.

The acceptance decision must reflect measured evidence and remaining limitations.

---

# 20. FINAL EXECUTION DIRECTIVE

**CONTINUE THE EXISTING PHASE 1 IMPLEMENTATION NOW.**

Do not restart the project.

Do not rebuild what Codex or Claude already implemented correctly.

Do not treat existing ontology contracts as an exhaustive description of every scientific concept NASA FIRE AI may ever encounter.

Do not weaken scientific integrity to increase benchmark scores.

Do not optimize only for the papers already used during development.

Do not produce a longer prompt or report as a substitute for working architecture.

Persist the project vision in `CLAUDE.md` and the authoritative architecture documentation.

Then ensure that the actual runtime implements this vision.

Build reusable scientific interpretation, semantic reuse, compatible contract evolution, source-grounded validation and controlled staging.

Continue correcting real defects, executing the application and improving scientifically correct recovery across different NASA investigations.

**The target is a genuinely adaptable scientific knowledge-ingestion product that remains useful when NASA publishes new experiments and previously unknown scientific concepts.**

If verified acceptance is reached, mark `PHASE1_COMPLETE=YES` with reproducible evidence.

If it is not reached, report the actual result, preserve completed engineering and identify only concrete remaining blockers.

Do not begin Phase 2's full UI or Phase 3's workspace product.

Do not modify the approved shared baseline.

**Deliver working, scientifically defensible architecture and implementations—not benchmark-specific fixes or another implementation plan.**



# NASA FIRE AI — ADDENDUM TO PHASE 1 MASTER DIRECTIVE
## Engineering Priorities from the Latest Scientific Failure Analysis

This supplements the existing Phase 1 master instruction. Do not restart implementation or create a new planning campaign.

Read and reconcile the existing `milestone13/phase1_plan.md`, the current repository state, implementation receipts and all subsequent commits before changing anything.

The existing milestones, tests, provider pilot and validated improvements must be reused.

## 1. Prioritize actual failure mechanisms

The latest analysis of 104 failed target-run cases reports:

- 69 proposed by the model but rejected downstream.
- 22 accepted but not credited correctly by the current evaluation.
- 13 not proposed by the model.
- No missed windows in that analyzed sample.

Use these findings to prioritize the actual production defects.

For rejected proposals, distinguish:

A. Scientifically unsupported assertions that must remain rejected.

B. Source-supported facts rejected because their existing representation, subject, property or relationship contract is unnecessarily restrictive.

C. Incomplete assertions whose valid evidence must be preserved while the unresolved semantic association is recovered.

Do not relax category A to increase recall.

Correct category B through generalizable semantic resolution and compatible contract evolution.

Recover category C through the existing evidence-grounded proposal workflow.

A valid new scientific property must not be discarded simply because the approved SemanticRegistry does not yet contain it.

## 2. Implement real adaptive semantic contracts

The current ontology is the approved scientific foundation, not an exhaustive vocabulary for future NASA research.

NASA FIRE AI must determine whether incoming knowledge:

- Is already represented and requires reuse.
- Is partially represented and requires a compatible extension.
- Introduces a genuinely new concept, property or relation that must be proposed and validated.

Implement this behavior in production, not only in extraction prompts.

The system may generate and validate isolated extension proposals, including compatible proposed semantic and SHACL contracts.

It must not activate these extensions in the shared approved baseline without authorization.

Never create source-specific mappings merely to improve an evaluation.

The result must support future NASA investigations introducing unfamiliar materials, experimental structures, quantities and relationships without requiring programmers to define each one manually.

## 3. Clarify Phase 1 scientific staging versus publication

Phase 1 is responsible for producing complete, scientifically supported, isolated knowledge proposals suitable for Phase 2 curation.

A source-supported, fully structured staged proposal is not equivalent to an incomplete `UNRESOLVED` proposal.

Likewise, a scientifically validated proposal does not become globally approved knowledge merely because its representation is complete.

Inspect whether the current scorer accurately distinguishes:

- Complete source-grounded scientific extraction.
- Structurally valid proposed ontology extension.
- Genuine scientific ambiguity.
- Evidence retained without complete interpretation.
- Authorized publication into the canonical baseline.

Do not automatically credit staged proposals.

Do not change the scorer or historical gold evaluation without approval. If the current criterion incorrectly requires global ontology publication to recognize complete Phase 1 extraction, prepare a precise, evidence-backed correction for Liam's authorization.

Keep the original frozen scores intact.

## 4. Do not overfit to the four development investigations

The current development results on PTFE, ignition, regulators and textiles are important, but they cannot prove future-domain generalization.

Do not build a loop whose only objective is to keep changing rules until those four papers pass repeatedly.

Each correction must correspond to a reusable scientific or documentary mechanism.

Document what problem it solves, why it is scientifically valid and whether it transfers across relevant investigation structures.

Preserve existing metamorphic and negative tests.

Use leave-one-source-out as a development robustness check, not as proof of a genuinely unseen evaluation if the rule design was already influenced by that source.

Once development readiness is demonstrated, freeze implementation and evaluate unexposed scientific lineages without adapting to their answers.

## 5. Continue implementation rather than only optimizing replay metrics

Reuse the existing replay-first testing strategy, the saved inputs and the 29 critical negative cases.

However, replay does not measure improvements that change the model request, source-context assembly or candidate discovery.

For such changes, perform controlled fresh inference when justified rather than rejecting a potentially valid improvement solely because old saved outputs do not change.

Do not select favorable generations or continue executing until a convenient score appears.

Measure the actual normal end-to-end behavior and preserve every predetermined run.

## 6. Review the reported remaining defects

Inspect the existing implementation before making further changes.

Address demonstrated failures involving:

- Printed quantity names and original scientific clauses.
- Experimental scope and missing subjects.
- Units disconnected from their source quantities.
- Relationships rejected because applicable source context was not reconstructed.
- Table headers contaminating scientific statements.
- Incorrect classification of materials, experiment counts and planned procedures.
- Duplicate entities or groups.
- Source-supported content omitted from initial model proposals.

Preserve strict experimental attribution.

Do not introduce rigid linguistic rules.

For example, expressions such as "was set to" can describe an actual documented experimental setpoint, but not necessarily an observed measurement. Resolve their scientific role from source context instead of accepting or rejecting every occurrence based solely on its wording.

Do not replace a correct source-grounded interpretation with an inference designed to pass a test.

## 7. Preserve the existing provider work

The Sonnet and Opus pilot has already been completed.

Do not repeat that model-selection campaign.

Sonnet demonstrated a better balance of speed, cost and scientific results in the reported pilot, but this does not independently demonstrate that it solves the current semantic coverage failures.

Use the already authorized provider configuration for ongoing development.

Do not silently change the permanent production model, purchase another API or modify provider policy without authorization.

Continue implementing provider-independent scientific extraction and semantic validation.

## 8. Preserve all prior findings and improve execution continuity

The latest report identifies previously planned work that was not completed.

Review those pending items against the actual current code.

Implement only those that remain relevant, especially targeted recovery from tables and narrative, semantic representation, generalization checks and evaluation integrity.

Retire or consolidate redundant readers only when production regressions demonstrate that doing so preserves scientific coverage.

Update the main Phase 1 report with milestones previously documented only in individual README files.

Update root `CLAUDE.md` with the long-term project vision, the six-phase program, adaptive ontology principles, scientific authority constraints and rules for avoiding overfitting.

Maintain concise versioned checkpoints and logical commits so interruptions do not cause lost work.

Do not fill repository documentation with duplicated competing plans.

## 9. Completion criteria

Do not declare Phase 1 complete solely because:

- PTFE passes.
- Four exposed development investigations eventually pass.
- Two successive model runs exceed a threshold.
- The replay scorer improves.
- All unit tests pass.
- More ontology properties have been manually added.

The system must demonstrate adaptive representation, source-grounded scientific correctness, meaningful coverage, operational stability and credible independent generalization.

Keep the established 95% precision and 80% recall engineering targets, with zero critical accepted attributions in the adjudicated set.

Report results by investigation and scientific category, with explicit denominators and uncertainty.

Do not claim that any finite test set guarantees identical performance for every future NASA paper.

**Continue the current Phase 1 implementation. Reuse what already exists, solve the structural problems, preserve scientific fidelity and deliver a generalizable product rather than a benchmark-specific extractor.**

Do not merge into main or publish unreviewed knowledge.

The final deliverable is working production software with reproducible scientific evidence, not another plan.


Claude, adjunto también el **Plan maestro de ejecución de NASA Fire AI**, que debes incorporar como referencia del propósito completo del proyecto y de sus seis fases.

Lee el documento junto con el prompt maestro y su complemento. Actualiza `CLAUDE.md` para conservar esta visión, las decisiones científicas y las reglas de continuidad entre sesiones.

**Consideraciones importantes:**

1. El PDF define la arquitectura objetivo y el alcance de las fases, pero fue elaborado el 14 de octubre. Sus referencias a commits, modelos y estado de implementación son históricas. Verifica el HEAD real y conserva los avances posteriores de Codex y Claude.
2. Las fases son hitos funcionales, no límites rígidos. La Fase 1 debe preparar propuestas ontológicas adaptables y compatibles para que la Fase 2 pueda revisarlas, corregirlas y aprobarlas sin reconstruir la ingesta.
3. La ontología aprobada es la base del conocimiento, no un vocabulario cerrado. Implementa reutilización, adaptación y generación de extensiones propuestas cuando el conocimiento entrante lo requiera, sin modificar automáticamente el baseline oficial.
4. Las reglas de fidelidad científica, procedencia y autorización son obligatorias. La estructura semántica debe poder evolucionar sin debilitarlas.
5. Reutiliza lo que ya funciona. Prioriza implementaciones completas sobre informes, experimentos repetitivos o modificaciones destinadas únicamente a mejorar los resultados de las investigaciones conocidas.

**El objetivo sigue siendo terminar una Fase 1 generalizable y reproducible**, que procese investigaciones NASA nuevas sin intervención de programadores por cada documento.

Utiliza el PDF como referencia de producto y las decisiones posteriores aprobadas como actualización de sus aspectos operativos. Continúa implementando, probando y corrigiendo sin reiniciar el proyecto.