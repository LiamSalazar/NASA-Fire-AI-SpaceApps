# Phase 3C autonomous research engineering — final executed results

A bounded research runtime and repeatable maintenance jobs are implemented and executed. Scientific readiness remains partial. No independent scientific precision is claimed. Phase 4 was not started.

## A. Architectural implementation

`Phase3AssistantService` retains the native QueryIntentV2 interpreter/executor and existing graph. Optional execution follows interpretation → initial native retrieval → typed sufficiency → justified native/document/ontology actions → source-backed claim verification → concise synthesis. Investigation receipts stay in EvidenceBundle metadata. Staged scientific entities project into the existing RDF graph with canonical=false and STAGED_CANDIDATE, and never enter canonical candidate enumeration.

Modules changed or added: services/phase3.py, services/investigation.py, services/intent_answers.py, services/claim_verification.py, services/maintenance.py, services/scientific_synthesis.py, query/native_interpreter.py, query/conceptual.py, llm/research.py, ingestion/scientific_proposals.py, ingestion/semantic.py, retrieval/semantic.py. Operational interfaces: scripts/research.py, scripts/maintain_knowledge.py; evaluation and integrity scripts use versioned receipts.

Defaults: three total retrieval rounds, eight follow-up action ceiling, eight candidates/action, 30-second between-action research deadline, at most two planning calls, conservative input/completion token reserve. The implemented planner currently makes at most one optional call/query. Initial retrieval remains native; additional actions retain explicit entity, numeric and source constraints. Simple sufficient queries stop immediately. V2/research, Nemotron planning and vectors remain experimental flags; CLI explicitly enables the validated research path.

## B. Actual autonomous recovery

**What did NASA observe about PMMA combustion?**

Injected fault: Initial requested-information inventories and passages deliberately removed at service retrieval boundary. Final decision: ANSWER.

- `native_search`: `observe pmma combustion observation`; missing `ReportedObservation`; 16 recovered references. Constraints retained in the full trace.

**What happened when airflow was interrupted and later restored?**

Injected fault: Initial requested-information inventories and passages deliberately removed at service retrieval boundary. Final decision: PARTIAL_ANSWER.

- `native_search`: `happened airflow interrupted later restored observation`; missing `ReportedObservation`; 16 recovered references. Constraints retained in the full trace.
- `document_search`: `happened airflow interrupted later restored`; missing `ReportedObservation`; 8 recovered references. Constraints retained in the full trace.

**What conclusions did NASA report for Saffire-I fire suppression?**

Injected fault: Initial requested-information inventories and passages deliberately removed at service retrieval boundary. Final decision: PARTIAL_ANSWER.

- `native_search`: `report saffire-i fire suppression conclusion`; missing `NASAConclusion`; 9 recovered references. Constraints retained in the full trace.
- `ontology_path`: `What conclusions did NASA report for Saffire-I fire suppression?`; missing `NASAConclusion`; 2 recovered references. Constraints retained in the full trace.

Full before/after coverage, constraints, rejected actions, returned IDs and timings: artifacts/phase3c_autonomy_recovery_v5.json. These are real service executions with an intentionally incomplete first retrieval, not production benchmark branches.

## C. Scientific interpretation and corrections

Conceptual retrieval now shows actual source terminology such as acrylic/PMMA specimen wording and distinguishes documentary usage from total material equivalence. Bibliographic retrieval returns publication titles and matching passages, deduplicated by NASA identity, without ExperimentalRun requirements. The regression suite caught and corrected a report/source linguistic guard that had erased explicit gravity and guidance requests. An explicit technical topic modifier absent from a statement cannot establish sufficient support for that topic.

The complex depressurization answer now retains unresolved conclusion support, experiment conditions and attribution. Pending exact source quotations are visible as proposed science, with unapproved scope. This is a useful partial result, not a validated observation-to-conclusion explanation.

## D. Source-to-knowledge execution

NTRS 20260003546 reused its immutable content-addressed PDF; original SHA256 `b4b64e88992718a7598000ad85d181ac4d9c06ed58e0ae7df0fb4188a6662a18`. Twelve physical page texts were verified. Structure-selected original pages went through bounded Nemotron proposals, exact-span/quantity checks, existing-class mapping and isolated staging. One provider timeout fell back to deterministic sentence proposals. The successful validated extraction yielded 32 candidates: 30 pending and 2 rejected. No new canonical scientific fact was published.

Published contract: document identity, source provenance and original page text. Pending candidates retain exact original wording, evidence ID, physical page, offsets, digest, proposed class, group/scope, original quantities when proposed, limitations, validation reasons and scientific-review=null. Model-proposed classes and scope are not approved science. A subsequent deterministic maintenance cycle added remaining bounded sentence proposals without duplicate identities. Unknown gravity remains unresolved; a full-page proposal falsely assigning microgravity was rejected despite historical microgravity discussion in that same source.

- `science-9e0bc74b4a90a6dd8f5d6d96` / ReportedObservation / PENDING; `E-auto-c372fa199c3f7bd04c056c7d`, page 3; reasons: EXPERIMENT_GROUP_AND_EPISTEMIC_CLASSIFICATION_REQUIRE_SCIENTIFIC_REVIEW.
- `science-41ece6a401d92e6e1e4e8200` / ReportedObservation / REJECTED; `E-auto-133c1547dc205949f6a4f4c2`, page 12; reasons: SOURCE_SPAN_NOT_FOUND.
- `science-2a30844a551bfe192b78f8e1` / ReportedObservation / PENDING; `E-auto-6f9591242c3f9382d799df2f`, page 2; reasons: EXPERIMENT_GROUP_AND_EPISTEMIC_CLASSIFICATION_REQUIRE_SCIENTIFIC_REVIEW.
- `science-4ca9a28530560000cccb3cbe` / ReportedObservation / PENDING; `E-auto-6f9591242c3f9382d799df2f`, page 2; reasons: EXPERIMENT_GROUP_AND_EPISTEMIC_CLASSIFICATION_REQUIRE_SCIENTIFIC_REVIEW.
- `science-b88c21e08a1c92c9f89f08d3` / NASAConclusion / PENDING; `E-auto-133c1547dc205949f6a4f4c2`, page 12; reasons: EXPERIMENT_GROUP_AND_EPISTEMIC_CLASSIFICATION_REQUIRE_SCIENTIFIC_REVIEW.
- `science-af4398e05132ae8c77616ee4` / Guidance / PENDING; `E-auto-6f9591242c3f9382d799df2f`, page 2; reasons: EXPERIMENT_GROUP_AND_EPISTEMIC_CLASSIFICATION_REQUIRE_SCIENTIFIC_REVIEW.
- `science-c2172851d14d378418fbdd3a` / ReportedObservation / PENDING; `E-auto-c372fa199c3f7bd04c056c7d`, page 3; reasons: EXPERIMENT_GROUP_AND_EPISTEMIC_CLASSIFICATION_REQUIRE_SCIENTIFIC_REVIEW.
- `science-1984d30e0cee5fb8a943af6d` / ReportedObservation / REJECTED; `E-auto-baa3c9655a747294059a349c`, page 1; reasons: SOURCE_SPAN_NOT_FOUND.

Complete propositions and model traces: artifacts/phase3c_autonomy_maintenance_validated_v1.json. Natural-language retrieval of explicitly pending knowledge occurs through the real service and `research.py review`.

## E. Ontology and KG

- `PMMA`: 41 valid paths through hasMaterial REVERSE, belongsToInvestigation FORWARD. Every edge carries resolvable provenance; paths express association.
- `psi-98`: 2 valid paths through belongsToInvestigation REVERSE, hasMaterial FORWARD. Every edge carries resolvable provenance; paths express association.

Observation/conclusion pair candidates retain both exact statements and source IDs. Approved support links: zero. No causal/support vocabulary or scientific equivalence was silently added. The graph benchmark was repaired to execute actual native queries, retain publication/information candidate identities, and exclude lexical-only passages from KG eligibility. Valid empty graph sets remain empty.

## F. Hybrid RAG

Expanded frozen corpus: 171 original units; 38 queries, including twelve developer-authored holdout probes. Configurations A lexical, B vector, C native KG eligibility, D lexical+KG, E lexical+vector, F all three, G context candidates were executed at k=5. KG ranks use BM25 only inside graph eligibility; they are not a new semantic graph scorer. 8 KG rankings are empty. H attempted bounded model organization on two fixed candidate lists; the full receipt distinguishes fresh inference from no validated inventory.

Precision@5, recall, nDCG and usefulness are unmeasurable without independent labels. Different candidates do not prove improved relevance. Vectors remain local and disabled in normal native execution. Actual 171-unit vector data was migrated to an atomic generation; interrupted manifest publication is regression-tested to retain the old searchable generation. Previous generations remain available for recovery.

## G. Claim verification

- actual supplied service claim: **SUPPORTED**; exact supplied statement with preserved entities, context and provenance.
- actual supplied service claim: **SUPPORTED**; exact supplied statement with preserved entities, context and provenance.
- actual supplied service claim: **SUPPORTED_WITH_LIMITATIONS**; exact supplied statement with preserved entities, context and provenance.
- actual supplied service claim: **SUPPORTED_WITH_LIMITATIONS**; exact supplied statement with preserved entities, context and provenance.
- changed_value: **UNSUPPORTED**; Claim is not an exact, complete supplied statement of the stated epistemic type.
- wrong_epistemic_type: **UNSUPPORTED**; Claim is not an exact, complete supplied statement of the stated epistemic type.
- wrong_investigation: **UNSUPPORTED**; Scientific statement identity changed, Statement support references changed.

Numeric changes, wrong epistemic type and wrong investigation identity were rejected while original grounded statements remained available. Two actual source claims were qualified because applicability was RELATED. This verifier deliberately rejects arbitrary paraphrases and cannot independently establish full scientific accuracy or causal entailment.

## H. Autonomous operation

Runnable commands:

```bash
uv run python scripts/research.py ask 'What did NASA observe about PMMA combustion?'
uv run python scripts/research.py ask 'Which experiments support the reported conclusions?' --planner --json
uv run python scripts/research.py review 'depressurization extinguishment'
uv run python scripts/research.py status
uv run python scripts/maintain_knowledge.py cycle --query 'depressurization fire suppression' --max-sources 1
uv run python scripts/maintain_knowledge.py cycle --execute --query 'depressurization fire suppression' --max-sources 1
uv run python scripts/maintain_knowledge.py cycle --execute --offline --nasa-id 20260003546 --extract
uv run python scripts/maintain_knowledge.py validation-only
uv run python scripts/maintain_knowledge.py rollback --source-id SOURCE_VERSION_ID
```

An actual discovery-led cycle found seven metadata records and selected an eligible official source without developer source selection. It correctly returned UNCHANGED for 20260003546. Offline controlled extraction and a repeated unchanged execution were also run; repeat inference count was zero. Per-cycle source/reference/FTS checks and autonomous-maintenance regressions passed. Persistent job leases prevent overlap, expired leases recover abandoned work, retry/backoff is bounded, and one failed extraction cannot stop later valid sources. Existing document publication/rollback tests retain raw input and citations.

`ops/nasa-knowledge-maintenance.service.example` and `.timer.example` passed systemd-analyze verify in temporary deployment copies. They are not installed or enabled. The configured recurring cycle can discover and process bounded sources. API key absence still supports queries, scientific review listing, validation and deterministic extraction. Strict whole-operation preemption and scientific-quality drift monitoring remain incomplete.

## I. Nemotron and Jev

New Nemotron requests: 9; provider failures: 1; reported tokens across successful recorded calls: 16070; usage unavailable for 1 calls. Counts exclude cache replay. Embedding calls and usage are recorded separately per request in hybrid_v1; hybrid_v2 reuses the cache. Billing cost is unavailable.

Nemotron supplied valid bounded actions and exact-span scientific proposals, but no independently demonstrated scientific precision gain. Its altered wording was rejected. Jev availability and one advisory classification were executed; its confidence/label did not approve science or change canonical knowledge. Both incremental scientific values remain INCONCLUSIVE.

## J. Scientific answer quality and comparisons

The unmodified historical A renderer is cited from its frozen receipt, not mislabeled as a fresh run. Fresh B uses repaired routing/verification; C adds deterministic iteration; D adds selective model planning. E/F scientific hybrid adoption is not justified by unlabelled candidate rankings. The best shipping configuration remains conservative with optional components off by default.

| Configuration | Cases | DIRECT identities present | Citation resolution | Mean words | Additional actions | Initially/finally sufficient |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| B | 38 | 22 | 38/38 | 242.9 | 0 | None/None |
| C | 38 | 24 | 38/38 | 245.2 | 28 | 21/22 |
| D | 38 | 24 | 38/38 | 245.2 | 29 | 21/22 |

B sufficiency counts are not measured with iteration disabled (None); C/D coverage is measured by the implemented engineering contracts. All are engineering coverage/formatting counts, not independent precision. Bibliographic and conceptual success is not measured by ExperimentalRun DIRECT counts. All scientific-review fields remain blank. Previously exposed and developer-authored holdouts are identified separately; the holdout is not independently adjudicated scientific gold.

## K. Engineering integrity

`uv run ruff format --check .`, `uv run ruff check .`, and the full `uv run pytest -q` passed (265 tests). Canonical, native and taxonomy SHACL conform; SQLite, reference anti-joins, FTS completeness and exact text consistency pass. All 1,050 historical digests remain unchanged; 159 original evidence units and twelve report pages match original cells/spans. Staged propositions are excluded from canonical enumeration. Dynamic checks: 230/230; post-freeze: 125/125; classes: 5/5. Historical 39-case parity remains DIRECT 31/39, RELATED 37/39 and exact evidence identities 6/39, so V2 parity is incomplete. V1/no-key rollback was actually executed.

72,960 rdflib warnings are classified as Dataset.default_context deprecation in installed rdflib (233 native-semantic; 72,727 scientific-enrichment), and were not suppressed. Earlier failed regression/renderer/lint receipts are retained; the final quality receipt resolves the corrected gates. No original data, frozen gold or historical benchmark receipt was overwritten. Credentials are excluded from the indexed campaign artifacts.

## L. Readiness

```text
AUTONOMOUS_RESEARCH_LOOP = OPERATIONAL
INTENT_AWARE_ROUTING = PARTIAL
EVIDENCE_SUFFICIENCY = PARTIAL
SCIENTIFIC_CLAIM_VERIFICATION = PARTIAL
OBSERVATION_CONCLUSION_LINKING = REVIEW_REQUIRED
AUTONOMOUS_SCIENTIFIC_EXTRACTION = PARTIAL
SOURCE_TO_KNOWLEDGE_PUBLICATION = CONTROLLED
ONTOLOGY_GRAPH_REASONING = PARTIAL
HYBRID_RAG = KEEP_EXPERIMENTAL
VECTOR_RETRIEVAL = INCONCLUSIVE
AUTONOMOUS_MAINTENANCE = PARTIAL
OPERATIONAL_FAILURE_RECOVERY = PARTIAL
NEMOTRON_INCREMENTAL_VALUE = INCONCLUSIVE
JEV_INCREMENTAL_VALUE = INCONCLUSIVE
SCIENTIFIC_RELEVANCE = REVIEW_REQUIRED
END_TO_END_SCIENTIFIC_RESEARCH = PARTIAL
V2_DEFAULT_PATH = KEEP_EXPERIMENTAL
READY_FOR_PHASE_4 = NO
```

Remaining blockers:

- Independent scientific relevance, answer completeness and claim labels are unavailable; precision cannot be independently measured.
- Current-study experiment identities, groups, table quantities and gravity scopes need approved extraction contracts and adjudication.
- Observation-to-conclusion candidates have no approved attribution or support predicate; shared publication does not establish support.
- Claim verification is exact supplied statement verification; unrestricted paraphrase entailment and contradiction reasoning remain unimplemented.
- Intent-specific methodology, comparison completeness and general conceptual authority remain partial.
- The recurring timer is verified but not installed or enabled, as required; unattended deployment remains a deployment step.
- Maintenance has bounded retries, leases, isolation and regression checks, but full scientific quality drift monitoring and strict whole-operation deadline preemption remain incomplete.
- Vector and selective model components lack independently demonstrated scientific benefit; they remain disabled by default.
