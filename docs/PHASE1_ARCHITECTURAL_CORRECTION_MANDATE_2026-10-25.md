# NASA FIRE AI — PHASE 1 ARCHITECTURAL CORRECTION AND SCIENTIFIC COMPLETION
## Final consolidated engineering mandate — 25 October 2026

### ROLE AND MISSION

Act as the principal scientific AI systems engineer, knowledge representation engineer, scientific information extraction specialist and implementation lead for NASA FIRE AI.

Continue development in the existing repository and the `diego/research` branch.

**Your objective is to finish Phase 1 by correcting the underlying scientific representation, semantic adaptation, retrieval and evaluation mechanisms—not by repeatedly optimizing known benchmark investigations.**

You have authority to investigate, select, implement and improve general engineering solutions that respect the approved product philosophy.

Do not deliver another implementation plan as the main outcome.

Deliver functioning, integrated production software.

The work must preserve what Codex and Claude Code have already implemented correctly.

This instruction explicitly resolves the ten questions recorded in:

`artifacts/phase1_generalizable_ingestion/v6/milestone13/package4/liam/PROPOSAL_FOR_LIAM.md`

It also incorporates the architectural conclusions of the October 2026 scientific-ingestion audit.

---

# 1. ESTABLISH THE ACTUAL REPOSITORY STATE

Verify the current repository location, branch, HEAD, uncommitted changes and implementation status before modifying anything.

The latest supplied research ZIP contained:

- `diego/research` at `030917f`.
- Earlier implementation commit `10692ba`.
- `main` at `54445d0`.
- 954 reported passing tests in Diego's environment.
- Phase 1 incomplete.

These are historical references, not assumptions about the present HEAD.

Read, in order:

1. `AGENTS.md`.
2. `CLAUDE.md`.
3. `CONTINUATION.md`.
4. `artifacts/phase1_generalizable_ingestion/v6/milestone13/phase1_plan.md`.
5. `docs/PHASE1_MASTER_DIRECTIVE.md`.
6. `docs/PHASE1_GENERALIZABLE_SCIENTIFIC_INGESTION.md`.
7. `docs/architecture.md`.
8. The six-phase master plan.
9. The Phase 1 Package 4/5 feasibility reports, adjudications, negative tests and scientific receipts.
10. The actual production modules, ontology, SemanticRegistry, scientific validators and existing staging services.

The immutable scientific rules of `AGENTS.md` remain authoritative.

However, distinguish immutable scientific rules from dated operational decisions that this mandate explicitly updates.

Do not reset, duplicate or discard existing work.

Do not modify `main`, create a PR or publish scientific knowledge to the canonical baseline.

---

# 2. PERSIST THE VISION WITHOUT REWRITING COMPLETED WORK

The current `CLAUDE.md` already documents:

- NASA FIRE AI's purpose.
- Its two major subsystems.
- The six product phases.
- Scientific fidelity.
- Adaptable knowledge structures.
- The boundary between Phases 1 and 2.
- Anti-overfitting policies.

Preserve that work.

Update only the sections made obsolete by this mandate, especially:

- The unconditional replay-before-live requirement.
- The treatment of semantic contracts as potentially closed vocabularies.
- The distinction between scientifically complete staging and globally approved knowledge.
- The decisions on scientific roles and new vocabulary.
- The evaluation and model-selection policy.
- The relevant research references and reusable implementation principles.

Keep one canonical operational plan and concise continuation checkpoints.

Do not generate competing architecture documents or duplicate the master specification.

A future development agent must understand the project through `CLAUDE.md`, but the actual production code must implement these rules independently of any development agent.

---

# 3. THE NON-NEGOTIABLE PRODUCT VISION

NASA FIRE AI is an end-to-end scientific knowledge and research platform for relevant official NASA and verifiably NASA-associated research in microgravity combustion, flame behavior, materials, spacecraft fire safety and related experiments.

It consists of two major subsystems.

## Knowledge creation

Original scientific documents and data become evidence-grounded entities, measurements, observations, conclusions, experimental relations and compatible semantic structures.

New knowledge must be integrated without requiring a programmer to design every new scientific concept.

## Knowledge consultation

Researchers query, compare, navigate and inspect original NASA knowledge through the KG, ontology, evidence registry and documentary retrieval.

Scientific claims remain source-grounded, condition-aware, historically preserved and distinguishable from generated analysis.

### Scientific integrity is strict

Never:

- Fabricate NASA observations or conclusions.
- Modify original values or units.
- Infer undocumented experimental conditions.
- Attribute cited studies to current experiments.
- Transform hypotheses into measurements.
- Convert procedures or future plans into completed observations.
- Invent scientific causality.
- Silently approve ontology modifications.
- Delete historically refuted or superseded knowledge.
- Treat model confidence or agreement as scientific proof.

### Knowledge representation is adaptable

Classes, relations, properties, attributes, instance characteristics, experimental configurations, hierarchies and semantic definitions must be extensible.

The approved ontology is the foundation of knowledge, not an exhaustive list of everything the system may ever discover.

**Strict scientific constraints and adaptable scientific vocabulary must coexist.**

---

# 4. PHASE 1 AND PHASE 2 — THE CORRECT BOUNDARY

Phase 1 must autonomously:

- Read heterogeneous NASA scientific sources.
- Identify evidence-grounded scientific candidates.
- Understand subjects, conditions, scope and epistemic meaning.
- Reuse existing entities and ontology definitions.
- Recognize partially represented concepts.
- Discover genuinely new concepts, properties and relationships.
- Prepare minimal compatible semantic extensions.
- Validate candidates independently.
- Preserve unresolved genuine scientific ambiguity.
- Produce complete isolated curation packages.

Phase 2 implements:

- Scientist-facing clarification questions.
- Interactive correction of scientific relationships.
- Review of proposed semantic extensions.
- Human-readable semantic change previews.
- Authorized local ontology evolution.
- Final scientific confirmation of the workspace version.

Phase 3 implements Git-like version history, isolated researcher workspaces and authorized baseline promotion.

Do not implement the complete Phase 2 UI or Phase 3 workflow now.

**But Phase 1 must provide all the information those phases need without requiring a reconstruction of the scientific extraction model.**

A proposed new ontology concept that remains unapproved does not constitute a Phase 1 failure when it has been correctly discovered, represented, evidenced and staged.

Failure to discover or represent it when the original evidence permits doing so is an ingestion deficiency.

---

# 5. EXPLICIT RESOLUTION OF THE TEN PENDING DECISIONS

These are approved architectural decisions. Do not request the same authorization again.

## Decision 1 — Plans, goals, criteria and staging

AUTHORIZE the generalizable representation of:

- Planned experimental activities.
- Scientific goals and intentions.
- Design requirements.
- Test criteria.
- Acceptance thresholds.
- Target conditions.
- Proposed experimental environments.
- Completed experimental configurations.
- Actual observations and results.

Do not model all of these as observations, conclusions or documentary context.

The ontology already contains concepts such as `DesignCriterion` and `TestCriterion`. Inspect and reuse them.

Do not merely add a growing collection of isolated role labels.

Prefer a backward-compatible representation that separates independent scientific dimensions such as:

- Scientific statement type.
- Epistemic role.
- Modality: actual, proposed, intended, conditional, hypothetical.
- Execution status.
- Time or historical scope.
- Scientific subject.
- Experimental applicability.
- Source attribution.
- Verification state.

Retain existing role definitions as compatible profiles where appropriate.

### Does staging count toward Phase 1 recall?

**YES, conditionally.**

A fully structured, scientifically source-supported, independently validated extraction may count as correct Phase 1 extraction even if its semantic class/property is still awaiting global ontology approval.

It must satisfy the predeclared evaluation target semantically.

It must not depend on an unsupported invented definition.

A valid staged ontology extension is not a published ontology extension.

An `UNRESOLVED`, incomplete, incorrectly attributed or merely source-retained statement does NOT count as fully recovered.

Separate:

- Extraction completeness.
- Scientific evidence validation.
- Structural contract validity.
- Semantic extension approval.
- Knowledge publication authorization.

Introduce a versioned evaluation protocol if the current protocol cannot express this distinction.

Never rewrite historical frozen scores.

## Decision 2 — POR and regulator identity

AUTHORIZE contextual acronym and alias resolution, not universal string substitution.

"POR" may identify a particular Primary Oxygen Regulator test article only where the original source establishes that identity and the local statement refers to that article.

Investigate the source-defined full name, acronym, specimen identity and serial number.

Use contextual entity linking, not a special case for the literal letters POR.

A sentence describing measurements made before reconnecting a regulator does not automatically mean those measurements belong to the regulator.

Subject applicability must still be verified for every relationship and quantity.

Reject unsupported transfers of experimental results.

## Decision 3 — Documentary context versus complete extraction

A literal sentence preserved as `documentary_context` is evidence retention, not automatically a complete extraction of a goal, plan, criterion or experimental configuration.

Do not award full semantic recall solely because the source sentence was copied correctly.

If the relevant scientific role can be justified, represent it explicitly and verify its scope.

If the information is preserved but not interpreted, record retention separately.

## Decision 4 — Frozen textiles targets versus existing contracts

DO NOT weaken scientific attribution contracts merely to satisfy the targets.

Resolve the underlying representation problem.

For the reported conflicting targets:

**statements-18:** distinguish a qualified state-of-the-art or historical-background assertion from an original finding of the current investigation.

**statements-19:** represent a normative test criterion only when the applicable original source actually supports that normative interpretation. If the presentation does not establish it, retrieve an admissible authoritative NASA standard when appropriate or retain the ambiguity. Do not import external scientific meaning silently.

**quantities-05 through -07:** permit values associated with proposed environments, intended configurations and mission-design conditions without assigning them falsely to an executed experimental run.

If a frozen target requires an assertion unsupported by its original sources, mark it for independent adjudication.

Preserve the original gold set and historical result.

Any justified correction must appear in a separately versioned evaluation set with explicit rationale.

Do not silently change a target or the scorer to improve results.

## Decision 5 — The 29 ambiguous target finders

AUTHORIZE a reproducible adjudication and evaluation-standardization workflow.

Do not request 29 independent software-engineering decisions from Liam.

Group cases by general matching ambiguity:

- Same value in multiple passages.
- Equivalent source wording.
- Subject or relation ambiguity.
- Different experimental scope.
- Missing endpoints.
- Source evidence split across sections.

Define consistent matching rules before subsequent frozen evaluations.

The finder must recognize scientific equivalence, not just literal string similarity.

It must not credit different subjects, conditions or epistemic roles as equivalent.

Use original NASA evidence and independent review where a scientific judgment is required.

A development agent may implement the finder and create a review packet, but must not silently adjudicate a genuine scientific disagreement in its own favor.

Freeze and version the finalized protocol.

Preserve the previous evaluator and receipts for historical reproducibility.

## Decision 6 — Material composition / `hasComponent`

AUTHORIZE a generic material-composition capability and its use in isolated scientific staging.

Before adding any predicate, check for equivalent existing ontology relationships.

A valid composition representation must support, when documented:

- Material or formulation.
- Constituent material.
- Constituent scientific role.
- Fraction or percentage.
- Basis of composition: mass, volume, molar or unresolved.
- Relevant specimen or experimental context.
- Original NASA evidence.

Prefer one generic component relationship with contextual role information over redundant relations when that is semantically adequate.

Do not automatically create both `hasComponent` and `hasFiller`.

Do not hardcode Salox-M, Bronze or PTFE.

A new relation may be proposed, validated and staged.

This authorization DOES NOT approve publishing it globally in the canonical ontology.

## Decision 7 — "was set to"

AUTHORIZE recognition of "was set to" and semantically equivalent configuration expressions.

However, it is a contextual indication, not sufficient evidence of an observed measurement.

Resolve whether the source describes:

- An executed setpoint.
- A planned setpoint.
- A recommended criterion.
- A simulated configuration.
- A conditional or hypothetical value.

The quantity's scientific property must come from the source or an independently justified equivalent definition.

Never use the word "set" itself as the quantity name merely to satisfy a validator.

Preserve original text, subject, unit and scientific scope.

## Decision 8 — Scientific inference provider

AUTHORIZE Claude Sonnet 5.5 as the preferred research-branch candidate for completing and validating Phase 1, given the existing pilot results and practical latency improvements.

Preserve the NVIDIA provider and its configuration.

Do not treat the Claude Code development model as a runtime dependency.

The actual scientific application must call its own configurable API provider.

You may implement and verify the approved Sonnet development configuration and use it in controlled development runs.

Do not silently change the globally approved production default.

Before any independent holdout, select and freeze ONE documented model/provider configuration, including prompts, decoding parameters, model identifier, available revision metadata, validation contracts and relevant runtime settings.

Select based on demonstrated scientific correctness, completion reliability, stability, time and cost.

Do not repeat the completed broad Sonnet-versus-Opus pilot without a new causal reason.

Diego manages credentials and live-execution authorization.

## Decision 9 — New-term proposal mechanism

DO NOT remove the existing proposal infrastructure.

DO NOT leave it permanently dependent on the model spontaneously choosing `PROPOSE_NEW_CLASS` or `PROPOSE_NEW_RELATION`.

Redesign the missing discovery and reconciliation mechanism as a production capability.

Determine why no new-term proposals were generated in twelve runs:

- No genuine novel concepts?
- The model did not identify them?
- The model recognized them but forced existing vocabulary?
- The request or output schema suppressed alternatives?
- The semantic matcher failed?
- Candidates were discarded later?
- The proposal pipeline was never invoked?

Preserve existing functioning staging and proposal states.

Implement active detection of representational gaps and evidence-grounded resolution against the existing ontology.

Do not generate unnecessary new classes merely because the capability exists.

## Decision 10 — Thresholds, stability and holdout

KEEP the previously established engineering targets:

- Scientific precision at least 0.95.
- Fully correct scientific recall at least 0.80.
- Zero observed critical false accepted attributions in the adjudicated acceptance set.

Do not change the target definitions to manufacture success.

However, two consecutive passing runs on one development paper are NOT sufficient proof of generalization or statistical reliability.

Retain repeat-run stability testing, but assess the distribution of results instead of relying on consecutive lucky passes.

After development readiness, use a prospectively frozen independent evaluation involving multiple unexposed NASA scientific lineages.

An initial acceptance package should contain at least two genuinely independent investigations and approximately 60 or more adjudicated scientific objectives when available. Prefer greater heterogeneity and additional independent lineages when feasible.

Two documents or 60 objectives are a minimum engineering check, not proof of universal domain reliability.

Report individual studies, scientific categories, all predetermined runs and uncertainty.

Never tune against a holdout and subsequently relabel it unseen.

---

# 6. ARCHITECTURAL CHANGE: SCIENTIFIC REPRESENTATION MUST BE EXTENSIBLE

The current system has a disconnect between:

- Scientific concepts already available in the ontology.
- The SemanticRegistry.
- The model output schemas.
- The validators.
- The curation service.
- The staged ontology proposal system.
- The hierarchy-aware knowledge interfaces.

Correct this disconnect.

## Separate stable transport from extensible scientific semantics

The extraction transport may remain structurally strict and versioned.

It should not use a closed semantic enum as the only way to represent every possible future NASA scientific concept.

Create or extend the existing evidence-grounded intermediate proposal representation so it can preserve:

- Original claim or literal value.
- Source identity and anchor.
- Scientific subject and candidate subjects.
- Predicate or relation definition.
- Scientific object or quantitative value.
- Unit and dimension.
- Modality and epistemic facets.
- Experimental context.
- Relevant parent/child concept relationships.
- Current semantic mapping status.
- Candidate extension definition.
- Validation findings.
- Review dependencies.

Do not build another database or KG.

Reuse existing proposal structures and extend only where necessary.

Compatibility with existing records, source hashes, SemanticRegistry and CurationService is mandatory.

## Required semantic resolution outcomes

For every scientifically relevant concept, select among:

1. Reuse an approved equivalent concept.
2. Recognize an alias or terminology variant.
3. Instantiate an approved class.
4. Use or extend characteristics of an existing instance.
5. Propose a justified subclass or specialization.
6. Propose a genuinely new class.
7. Propose a new relation/property with documented meaning.
8. Preserve an unresolved scientific classification.

These are not interchangeable.

A new characteristic does not automatically require a new class.

An unknown term does not automatically justify a new ontology definition.

A similar term does not establish semantic equivalence.

---

# 7. IMPLEMENT EVIDENCE-CONSTRAINED SCHEMA DISCOVERY — SCION

### Research references

Paper:

https://proceedings.mlr.press/v306/hu26t.html

Official implementation:

https://github.com/wandugu/paper_scion

Relevant implementation:

- `src/utils/scion_candidates.py`
- `src/ontology_generate.py`
- `src/ontology_process.py`
- Schema graph evaluation and candidate validation code.

SCION is an auditable schema-induction and fusion pipeline. It is not a complete replacement for NASA FIRE AI's scientific extraction architecture.

## What to adopt

Study and adapt the working mechanisms for:

- Candidate mining from documentary evidence.
- Evidence-linked candidate definitions.
- Separation of candidate generation from schema consolidation.
- Normalization and deduplication.
- Candidate-constrained naming and merging.
- Conservative reconciliation with an existing schema.
- Validation and fallback for malformed model output.
- Provenance and merge-decision traces.

Implement these capabilities through the existing SemanticRegistry and scientific staging services.

## Required integration

Source evidence
→ candidate scientific concepts/relations
→ contextual definitions
→ comparison with approved ontology
→ reuse or minimal extension
→ isolated semantic validation
→ staged scientific proposal.

The candidate inventory may include multiple hypotheses, but a hypothesis is not an approved fact.

Do not use source-specific answer dictionaries.

Do not force every novel candidate into a known superclass if its scientifically correct location is still unknown.

Preserve unresolved hierarchy-placement questions for Phase 2.

## Required proof

Demonstrate that the system can:

- Detect equivalent terminology and reuse an approved concept.
- Identify a characteristic that does not require a new class.
- Propose a valid subclass when justified.
- Propose an unfamiliar relationship when source-supported.
- Avoid duplicating an existing relationship.
- Reject a scientifically unsupported extension.
- Preserve unresolved placement without losing the scientific evidence.

These cases must work through real production components.

Synthetic fixtures are useful for regressions, but demonstrate the full flow with source-grounded NASA evidence as well.

Do not install SCION's entire benchmark and training architecture unless a directly required component cannot reasonably be integrated otherwise.

Review licensing and dependencies before reusing implementation code.

---

# 8. IMPLEMENT ONTOLOGY-GUIDED EXTRACTION — ODKE+

### Research reference

Apple Research:

https://machinelearning.apple.com/research/odke

Paper:

https://arxiv.org/abs/2509.04696

ODKE+ combines missing-fact detection, evidence retrieval, ontology-guided extraction, fact validation and candidate normalization.

Its reported production results are not evidence of equivalent scientific accuracy on NASA papers.

## What to adopt

Use its practical approach of generating **contextual ontology snippets for the entities being interpreted**.

Instead of exposing only a global list of allowed types, construct the relevant semantic context from:

- Candidate entity type.
- Approved definitions.
- Parent and child classes.
- Inherited properties.
- Compatible relations.
- Applicable subject and object types.
- Known aliases and equivalences.
- Relevant provenance and experimental conditions.

This context must be generated dynamically from the ontology and SemanticRegistry.

Do not hardcode it into a static LLM prompt.

## Missing-fact and evidence retrieval

Reuse the existing candidate inventory and source retrieval infrastructure.

Detect when documentary evidence contains a potentially relevant entity, condition, quantity or statement that the structured output has not represented.

Recover the corresponding context before attempting additional inference.

Do not ask the LLM to invent missing science.

## Grounding and corroboration

Reuse NASA FIRE AI's existing deterministic evidence checks and scientific validators.

You may use contextual model assistance when it adds measurable value, but do not make a second LLM's agreement sufficient scientific proof.

The original source remains authoritative.

## Required integration

Ontology-aware extraction must remain compatible with newly proposed semantic extensions.

If no approved schema element can express a valid scientific source statement, the system must be able to stage a proposal, not drop the statement or force a false match.

## Required proof

Demonstrate improvements in:

- Scientific type selection.
- Correct subject and relation attribution.
- Reuse of inherited semantic properties.
- Distinguishing background from executed research.
- Representing proposed versus completed experimental conditions.
- Handling unfamiliar scientific properties.

Compare against the previous extraction path on identical exposed development sources.

If an already implemented equivalent mechanism exists, extend it instead of rebuilding it.

---

# 9. SCIENTIFIC HIERARCHIES MUST BE USED DURING INGESTION

Hierarchical knowledge is a central product feature, not an optional future visualization.

Reuse existing RDF, RDFS, SKOS, ontology definitions and hierarchy-aware query components.

Determine why concept hierarchies are not consistently available to the extraction and mapping pipeline.

Correct the interfaces between ingestion, SemanticRegistry and hierarchy resolution.

The system must distinguish:

- `rdf:type`: an instance belongs to a class.
- `rdfs:subClassOf`: a class specializes another class.
- `skos:broader` and related conceptual hierarchy definitions.
- Equivalent concepts and aliases.
- Properties versus class membership.
- Relationships between experimental instances.

Do not model material states, material families or compositions solely through a rigid single-parent tree.

Support legitimate multiple classifications and contextual attributes without introducing redundant classes.

When proposing a new class, preserve potential parent candidates and supporting evidence.

Do not force an unsupported hierarchy assignment.

Validate proposed extensions on isolated graphs using the appropriate approved and candidate shapes.

The canonical ontology remains unchanged until authorized review.

---

# 10. SCIENTIFIC ROLE MODEL — PRESERVE MEANING, REMOVE ARTIFICIAL LIMITATIONS

Review current closed `Statement` and `Quantity` epistemic role schemas.

Do not assume the existing enums are all bad.

Classify each restriction as:

- Essential scientific distinction.
- Existing legitimate ontology concept.
- Implementation-specific constraint.
- Legacy deterministic limitation.
- Redundant or conflicting contract.

Preserve essential scientific distinctions.

Extend the representation through compatible scientific facets instead of repeatedly adding special-case labels.

Support the distinctions between:

- Observed and reported facts.
- Experimental setpoints.
- Derived quantities.
- Simulated or predicted values.
- Planned actions.
- Stated scientific goals.
- Design criteria.
- Normative requirements.
- Historical/background claims.
- Tentative author interpretation.
- Author conclusions.
- Hypotheses and open questions.

The scientific source must support the selected role.

Do not infer a real executed experiment merely because a planned experiment has specific numerical settings.

Do not force every criterion to belong to a test that was actually executed.

Validate both the semantic type and the applicability of the statement.

Preserve backward compatibility for existing accepted scientific data and frozen historical receipts.

---

# 11. SCIENTIFIC RELATION VALIDATION MUST SUPPORT NEW PREDICATES

Review existing hardcoded predicate validators and relation endpoint contracts.

Some restrictions are necessary to reject scientifically invalid assignments.

Others may prevent legitimate novel relations from being represented.

Do not remove all deterministic validation.

Instead, generalize relation validation where possible using:

- Source evidence.
- The proposed relation's meaning.
- Approved domain and range definitions.
- Candidate source and target entity types.
- Applicable scientific scope.
- Original relation wording.
- Contextual entailment verification.
- Explicit uncertainty and rejection reasons.

A new predicate requires a traceable definition and validation.

It must not automatically become valid because the model named it.

An unsupported relation must remain rejected.

A source-supported relationship whose predicate is not yet approved may be represented as a validated staged extension, with the correct publication state.

Preserve original negative G2/G3 attribution tests.

---

# 12. SPECIALIZED DOCUMENT TOOLS — DOCLING

### Reference

https://github.com/docling-project/docling

https://docling.ai/

Docling provides document layout, reading order, table structure, formula and OCR capabilities.

## Approved engineering philosophy

A module that solves a general class of documentary problems is not overfitting.

Examples:

- A general mathematical formula extractor.
- A scientific table reconstruction module.
- A page-layout recovery tool.
- An OCR fallback for inaccessible source regions.

A rule recognizing one exact formula from one benchmark paper is overfitting.

## Required implementation approach

Inspect existing table, formula, PDF and multimodal extraction components first.

Create or reuse a specialized document-recovery interface.

When source evidence indicates that ordinary extraction failed, route the affected page or region to a suitable specialist.

Possible triggers:

- Formula glyph corruption.
- Missing mathematical symbols.
- Unrecoverable merged table headers.
- Broken table row/column identity.
- Incorrect reading order.
- Image-only scientific content.
- Significant mismatch between source visuals and extracted text.

Docling is an approved candidate for this specialist role.

Evaluate it on the actual missing source evidence.

If it recovers scientifically relevant structure significantly better than the existing implementation, integrate it into production with regression tests.

If another existing module already solves the same problem adequately, reuse it.

Do not introduce Docling as a mandatory heavyweight dependency for every document without demonstrated value.

Do not replace the entire ingestion pipeline or create a competing source of truth.

Preserve original page coordinates, source identity and scientific evidence relationships.

A visually extracted scientific value must still undergo scientific attribution validation.

---

# 13. CORRECT REJECTION LOSSES WITHOUT WEAKENING SCIENCE

The current evaluation reports many targets that the model proposed but the downstream pipeline did not accept.

For each significant rejection family, distinguish:

A. Scientifically unsupported proposal — rejection is correct.

B. Scientifically valid candidate blocked by a representation limitation.

C. Source-supported information with an incorrect proposed subject.

D. Valid information with incomplete scientific context.

E. Parser/transport/evaluator defect.

Treat these differently.

Do not loosen category A.

For B–E, correct the general underlying mechanism.

A valid original expression should not disappear because a model initially chose the wrong subject or the ontology lacks the appropriate property.

Preserve independently verified components and recover missing associations.

However, incomplete evidence does not become a complete scientific fact through persistence alone.

Avoid repeated whole-document inference when the failure is local and the original evidence is accessible.

---

# 14. SCIENTIFIC EVALUATION — REPAIR THE PROTOCOL, NOT THE SCORE

Current evaluation infrastructure is inconsistent across scientific sources.

PTFE has a more formal scorer; ignition, regulator and textiles depend partly on manually adjudicated target finders.

Resolve the evaluation contract before using final scores for Phase 1 acceptance.

## Maintain historical integrity

Keep:

- Frozen v4 targets.
- Original historical scores.
- Original source evidence.
- Previous runner configurations.
- Prior adjudication results.

Do not silently overwrite any of them.

## Implement a versioned scientific evaluation protocol

Distinguish:

- Completely correct structured extraction.
- Complete extraction using a validated staged semantic extension.
- Scientifically incomplete or `UNRESOLVED`.
- Correctly retained evidence.
- Justified rejection.
- True omission.
- Scientific role mismatch.
- Unsupported subject or relation.
- Critical false accepted attribution.

A staged but scientifically complete proposal may be evaluated as a correct Phase 1 extraction when its meaning is independently supported and the target is satisfied.

This does not mean the underlying ontology extension is globally approved.

A raw sentence retained as context does not count as completed structured extraction.

## Statistical and operational evaluation

Report:

- Strict precision and recall.
- Evidence retention.
- Correctly unresolved content.
- Omissions.
- False accepted critical attributions.
- Category-level results.
- Per-investigation results.
- Run-to-run variation.
- Model/provider completion and failure rates.
- Appropriate uncertainty intervals.

Scientific assertions within the same paper are dependent observations. Do not report naive per-target intervals as proof of domain-wide reliability.

Use investigation/lineage-aware analysis where sufficient independent sources exist.

Preserve denominators and negative results.

---

# 15. CHANGE THE LIVE-EVALUATION EXECUTION RULE

The previous operational policy forbidding all live inference until saved-output replay passes is replaced by a scientifically appropriate two-track policy.

## Track A — Offline/replay validation

Use saved proposals, tests and replays to evaluate changes involving:

- Deterministic validators.
- Subject reconciliation after model output.
- Numeric parsing.
- Scientific contract compatibility.
- Scoring implementation.
- Existing proposal staging and publication safety.

Do not spend live API calls where replay answers the actual engineering question.

## Track B — Fresh inference validation

Replay cannot measure improvements that change what the model sees or generates.

Use fresh inference when modifying:

- Dynamic ontology context.
- Source candidate discovery.
- Model request construction.
- Scientific role instructions.
- Missing-term detection.
- Specialized document recovery.
- Retrieval and context preparation.
- Provider-specific handling.

Before a live campaign, confirm the change is integrated, offline regressions pass and the campaign has a predefined scientific question.

Diego controls API configuration and authorizes the bounded live campaign.

A single authorization may cover a defined series of necessary development runs rather than requiring a new decision for every routine request.

Do not purchase paid services or activate new billing.

Respect provider rate limits, actual credit availability and system resources.

Do not use arbitrary old token ceilings that make legitimate scientific processing incomplete.

Maintain finite retries, no-progress checks, caching, concurrency safeguards and resumability.

Report every predeclared run, including failures.

Do not continue running until a favorable score happens to appear.

---

# 16. GENERALIZATION AND ANTI-OVERFITTING

The following documents are exposed development investigations:

- PTFE.
- LUCI.
- Ignition.
- Regulator.
- Textiles.
- Other investigations previously used to guide implementation.

They are not independent generalization evidence.

For every meaningful engineering change:

1. Identify the general scientific or document-processing failure.
2. Implement a general solution.
3. Explain why the mechanism transfers beyond the motivating source.
4. Test positive and negative cases.
5. Add metamorphic variations.
6. Test relevant distinct exposed source formats.
7. Measure regressions.
8. Preserve known limitations.

Do not introduce production rules based on:

- Specific NASA paper identifiers.
- Frozen target numbers.
- Exact expected benchmark values.
- Literal source quotations copied into prompts.
- Material names used solely to improve evaluation.
- Handwritten mappings for individual papers.

Legitimate scientific constants, standards, dimensional rules and defined ontology concepts are allowed when independently justified.

## Required metamorphic tests

Examples:

- Reordered table columns preserve scientific meaning.
- Wrapped identifiers retain identity.
- A legitimate equivalent unit is normalized without changing the original.
- A proposed experiment is not represented as executed.
- A cited result remains historical.
- A scientific criterion remains a criterion.
- A relation with changed subject is not treated as equivalent.
- An unfamiliar concept can be staged without source-specific code.
- A valid ontology concept can be reused through inherited properties.

Tests should exercise production functionality.

---

# 17. STATE-OF-THE-ART ADOPTION POLICY

Do not conduct open-ended technology research.

The three approved areas are:

**SCION:** evidence-linked schema candidates and conservative semantic reconciliation.

**ODKE+:** dynamically retrieved ontology definitions and context-specific extraction.

**Docling:** specialized document structure and formula recovery.

Inspect real implementation code where available.

Select useful working mechanisms, integrate them into the existing architecture and demonstrate their effect.

You may choose a better established implementation when it meets the same general requirement with less complexity.

Do not build a platform merely because a paper reports strong results.

Do not copy its evaluation metrics as NASA FIRE AI performance.

Do not install an unnecessary multiagent framework.

Do not create a second KG.

Do not add competing ontology registries or redundant truth databases.

The criterion is substantial scientific functionality, not technological novelty.

---

# 18. IMPLEMENTATION CAMPAIGN — COMPLETE WORK, NOT ANOTHER PLAN

Carry out the following integrated work packages.

## Package A — Contract and scientific representation correction

- Reconcile all existing contracts.
- Preserve immutable integrity rules.
- Separate scientific roles and modal facets.
- Represent goals, plans, criteria and proposed conditions.
- Correct staging-versus-publication semantics.
- Preserve compatibility with existing data.
- Implement actual production integration.

Deliver tested code.

## Package B — Adaptive semantic discovery and hierarchy

- Integrate evidence-linked candidate discovery.
- Implement ontology-context retrieval.
- Compare candidate meaning with existing definitions.
- Reuse, instantiate, specialize or propose extensions.
- Preserve unresolved hierarchy placement.
- Validate candidate structures in isolation.
- Connect existing RDF/SKOS hierarchies to ingestion and staging.

Deliver a functioning end-to-end semantic extension path.

## Package C — Scientific attribution and recovery

- Repair source-supported subject resolution.
- Correct predicate applicability where unnecessarily restrictive.
- Maintain scientific negative safeguards.
- Improve coverage of plans, criteria and novel structures.
- Recover useful evidence that was rejected or omitted.
- Integrate specialized PDF recovery when justified.

Deliver improvements across heterogeneous development sources.

## Package D — Evaluation integrity and reliability

- Resolve the ambiguous target finders under a versioned protocol.
- Preserve historical gold and scores.
- Validate the new extraction states correctly.
- Compare fresh and replayed inference.
- Measure stability and category-level scientific performance.
- Correct regressions rather than hiding them.

Deliver reproducible evaluations.

## Package E — Independent scientific acceptance

After development readiness:

- Freeze implementation and dependencies.
- Freeze prompts and model configuration.
- Freeze semantic contracts and evaluation criteria.
- Select unexposed NASA scientific lineages.
- Establish independent source-grounded reference answers.
- Execute ordinary NASA FIRE AI ingestion without development-agent intervention.
- Record all results and failures.
- Report precision, recall, critical errors, stability and limitations.

Do not use a known development paper as a fresh holdout.

Do not modify code after inspecting a holdout and still describe that same test as independent.

---

# 19. ENGINEERING AUTONOMY

You are authorized to make reasonable implementation decisions that preserve:

- Scientific fidelity.
- Source traceability.
- Semantic adaptivity.
- Backward compatibility.
- Controlled staging.
- Independent validation.
- Historical preservation.
- Reproducibility.
- Generalization.
- No paper-specific overfitting.

You may:

- Refactor defective production modules.
- Extend versioned data contracts compatibly.
- Add general scientific facets.
- Implement ontology snippet retrieval.
- Improve candidate discovery and reconciliation.
- Introduce specialized document-processing components when justified.
- Improve source-subject recovery.
- Add appropriate automated tests.
- Consolidate duplicated code.
- Improve existing inference orchestration.
- Create versioned evaluation tooling and receipts.
- Commit coherent production changes to the research branch.

You must not:

- Change the approved scientific baseline.
- Auto-publish ontology extensions.
- Delete original scientific data.
- Falsify NASA findings.
- Rewrite frozen historical evaluation outcomes.
- Weaken critical attribution protections.
- Merge into `main`.
- Make Codex or Claude Code part of the product runtime.
- Activate paid API accounts without authorization.
- Commit API credentials.
- Claim Phase 1 success without reproducible scientific evidence.

Escalate genuine scientific judgments or baseline publication authorization.

Do not escalate ordinary engineering decisions already resolved by this mandate.

Do not ask the user to manually design ontology classes that the system should be capable of proposing automatically.

---

# 20. REQUIRED PROOF OF ADAPTIVE KNOWLEDGE HANDLING

Before requesting Phase 1 acceptance, demonstrate at least these cases through the real application and its existing scientific services.

### Case A — Existing concept

A new NASA source uses a term already represented.

The system recognizes equivalence, reuses the approved definition and avoids duplication.

### Case B — New instance

A previously unseen experiment or specimen belongs to an existing class.

The system creates a properly sourced instance proposal without adding a needless class.

### Case C — New characteristic

A known entity has a newly documented property or configuration.

The system models it as a supported characteristic when appropriate.

It does not automatically invent a subclass.

### Case D — Valid specialization

A source establishes a meaningful new subcategory.

The system identifies its distinguishing scientific characteristics and proposes a compatible hierarchical relationship.

### Case E — New relation

A source introduces a relationship not represented by approved predicates.

The system discovers and defines a candidate relation with appropriate endpoints, scientific meaning and source evidence.

### Case F — Genuine ambiguity

The source does not sufficiently establish a concept's meaning or location in the hierarchy.

The system retains the evidence, records the unresolved alternatives and prepares a scientific clarification request.

It does not fabricate the missing information.

### Case G — Unsupported scientific assertion

A model proposes a value, relationship or scientific role that the original NASA source does not support.

The system rejects the unsupported assertion.

### Case H — Heterogeneous original source

A different document type or format reaches the same scientific representation pipeline.

Where ordinary document processing is insufficient, a justified specialized recovery mechanism may be used without paper-specific programming.

These are architectural acceptance cases, not answers to memorize in model prompts.

---

# 21. QUALITY GATES AND RELEASE DISCIPLINE

Run:

`uv run ruff format --check .`

`uv run ruff check .`

`uv run pytest -q`

Also execute relevant:

- RDF/SHACL checks.
- Source and evidence integrity.
- Scientific attribution negatives.
- Quantity and unit validation.
- Contextual entity linking.
- SemanticRegistry compatibility.
- Hierarchy reconciliation.
- Staging and ontology-extension compatibility.
- Curation package integrity.
- Idempotence and resume.
- Provider request and fallback tests.
- Publication safety.
- Metamorphic regression checks.

Use full tests before committing/pushing according to repository policy.

If required ignored local files are missing, explain and distinguish environment failures from source-code failures.

Do not claim 954 tests are reproduced if they are not executed in the current environment.

Preserve all historical scientific receipts.

Create new versioned artifacts for the resulting campaign.

Avoid redundant reports and unnecessary large generated files.

---

# 22. FINAL DELIVERABLES

The final handoff must contain:

1. Exact Git branch and commits.
2. Existing capabilities reused without rewriting.
3. Defective components repaired.
4. New generalizable scientific capabilities implemented.
5. Adaptive semantic discovery results.
6. Existing versus proposed ontology mapping examples.
7. Correct scientific role representation.
8. Hierarchy and relationship integration.
9. Source-grounded accepted and rejected examples.
10. Before/after results across exposed investigations.
11. Fresh versus replayed inference comparison.
12. Stability and provider reliability.
13. Independent generalization evidence, if readiness allowed it.
14. Complete software and scientific validation results.
15. Source, ontology and baseline preservation evidence.
16. Concise unresolved scientific decisions, if any.
17. Updated `CLAUDE.md`, canonical plan and continuation checkpoint.
18. Final `PHASE1_COMPLETE` decision with supporting receipts.

The report must be shorter than the implementation effort it documents.

Do not stop after producing the report.

---

# 23. FINAL DEFINITION OF PHASE 1 SUCCESS

Phase 1 is not complete merely because:

- PTFE passes.
- A set of known papers reaches favorable scores.
- Automated tests are green.
- Model output conforms to a JSON schema.
- New properties are manually inserted.
- Staged facts are counted without verifying them.
- An unapproved ontology extension is treated as official knowledge.
- The model returns a large number of triples.
- Replayed outputs score better.
- Two favorable runs happen consecutively.

Phase 1 is complete when NASA FIRE AI has demonstrated:

- A generalizable scientific ingestion workflow.
- Faithful scientific representation.
- Dynamic reuse and proposed extension of semantic structures.
- Functional hierarchy-aware ingestion.
- Correct representation of diverse scientific roles.
- Strong evidence provenance.
- Independent attribution validation.
- Recovery of accessible scientific information.
- Controlled handling of genuine ambiguity.
- Isolated scientific staging compatible with Phase 2.
- Reliable operation without development agents.
- Defensible quality and reproducibility on genuinely independent investigations.

The quality targets remain 95% precision, 80% fully correct recall and zero observed critical false accepted attributions in the adjudicated set.

They measure how well the architecture works.

They do not define which scientific facts the architecture is permitted to invent or which validation standards it may weaken.

A finite evaluation cannot guarantee equal performance on all future NASA research. Report the demonstrated generalization scope and its uncertainty accurately.

**If these requirements are satisfied, mark `PHASE1_COMPLETE=YES` with reproducible evidence.**

Otherwise, deliver actual completed implementations and exact remaining defects. Do not claim success artificially.

---

# 24. EXECUTION MANDATE

START IMPLEMENTATION.

Do not restart NASA FIRE AI.

Do not repeat solved Codex or Claude Code work.

Do not create another large proposal before working on the code.

Do not optimize exclusively for the known benchmark investigations.

Do not weaken scientific contracts to increase recall.

Do not preserve artificial closed vocabularies merely because earlier deterministic implementations used them.

Implement the missing semantic adaptation mechanisms using the existing ontology, KG, staging, evidence and curation infrastructure.

Use the verified research mechanisms of SCION and ODKE+ where they solve the demonstrated architectural deficiencies.

Integrate specialized document recovery only where it resolves a real scientific extraction problem.

Take engineering decisions autonomously within the authorized boundaries.

Test, correct, integrate and continue.

Maintain reproducible checkpoints and commits so work survives session interruption.

**The goal is to finish Phase 1 as the scientific foundation of NASA FIRE AI: an adaptive system able to receive new NASA research, understand its scientific representation, reuse existing knowledge, propose compatible extensions and preserve source fidelity without programmers implementing exceptions for every paper.**

Do not begin the complete Phase 2 user interface or merge into `main`.

Deliver functioning architecture, measurable scientific progress and a scientifically defensible acceptance decision.
