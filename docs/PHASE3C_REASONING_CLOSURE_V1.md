# Phase 3C autonomous scientific reasoning closure — v1

The engineering campaign corrected the existing research and response paths, but
does **not** establish full scientific closure. V2 remains experimental and Phase
4 is not ready. Every positive engineering decision below has an execution
receipt; independent scientific relevance remains unreviewed.

The final execution directory is `artifacts/phase3c_closure_v5/`. Earlier v1–v4
receipts record intermediate failures and corrections. They are not overwritten.
The initial repository commit was `c186823b78da5019d3d90317625e9458af80c5a7`.
Historical reports of 266 tests, 38 questions, 22/38 and 24/38 DIRECT identities,
28/29 searches and 30 staged proposals are historical, not newly reproduced
measurements. This campaign freshly evaluated twelve questions.

## Actual implementation and runtime

Changes remain in `Phase3AssistantService`, the native V2 executor integration,
existing Investigation Engine, scientific synthesis, claim verifier, Nemotron
planner, scientific proposal staging and maintenance CLI. No QueryIntentV3,
replacement ontology, second graph, second scientific truth store or autonomous
code editing runtime was introduced. V1 rollback remains available.

`information_requirements` keeps the existing V2 query as its authority. Coverage
receipts now expose the requested information, entities, explicit conditions,
epistemic type, comparison operands, evidence, missing information and state.
Necessary phenomenon/material wording and validated material context prevent
some wrong-topic statements from satisfying a requirement. Source-backed
conditions projected from canonical values now participate in coverage.
Experiment identity alone is only partial support.

`next_actions` reconstructs alternatives after every retrieval. It uses unresolved
requirements, recovered entities and existing reified relation records. Identical
operation/query/start/path combinations are rejected. Forward paths whose edge
evidence is already supplied are skipped. Traversal retains its existing cycle
and relation authority checks. Failed native/document searches are recorded,
bounded by attempted actions, and retain the prior bundle.

The planner receives compact evidence, unresolved requirements, previous actions,
discovered entities, approved relations and budgets. The first implementation
included too many graph entities and reserved no completion budget; actual
execution exposed this and the input was reduced. Proposals never grant
scientific authority or relax the V2 constraints in native execution.

All corrected V2 flag combinations render the **final** bundle. Claim selection
precedes `verify_claim`; only SUPPORTED or SUPPORTED_WITH_LIMITATIONS candidates
are rendered. Full exact spans are checked against the registry, and structured
values against validated graph payloads. Conflicted scope blocks emission.
Rejected candidates remain in receipts. Arbitrary paraphrase entailment is not
implemented: safe extractive synthesis is the fallback. Conceptual and
bibliographic outputs separately verify exact documentary spans.

Receipts: `answers_b.json`, `answers_c.json`, `answers_e.json`,
`feature_flags.json`, and `quality_verified/pytest.txt`.

## Sufficiency findings and comparative limits

The original service was executed in an isolated interpreter from the frozen
commit against the same evidence registry. Its repository-relative lexicon and
graph resources initially prevented replay; the verified rerun provided those
resources without changing the checkout. See `answers_a_baseline_verified.json`;
the failed attempts are retained separately.

Both the original and corrected service count seven of twelve questions as
sufficient, but the covered questions differ. This is **not scientific accuracy**.
The original type-presence logic marked a seawater-corrosion bibliography as
supported and returned unrelated fire-safety papers. The corrected result is
MISSING with honest abstention. The original oxygen-reintroduction observation
case was supported by type presence; corrected coverage is RELATED_ONLY.
Saffire-I S1/S2 conditions were previously missing in coverage despite existing
typed source values; their corrected condition requirement is supported.
Author-stated open questions are recovered by additional typed search.

New adversarial tests cover wrong phenomenon, wrong publication topic, conflicted
scope, changed negation, changed number/unit, model self-approval, invalid paths,
retrieval timeout and automatic exact replay under a trusted approved-record
fixture. Existing numerical/metamorphic, context, V1 and registry suites remain
part of the full run. These guards do not cover arbitrary scientific entailment,
every material synonym, every temporal relation or every comparison group.
Therefore SEMANTIC_SUFFICIENCY remains PARTIAL.

## Three adaptive traces

`adaptive_recovery.json` records actual service requests over real NASA evidence.
Their initial information inventories/passages were deliberately suppressed to
simulate incomplete retrieval. Subsequent searches run the production native
executor; no NASA statement was fabricated and no follow-up query is hardcoded in
production for these questions.

1. PMMA observations and interventions: typed searches add 16, then 6, then 6
   evidence IDs. Coverage changes reduce or redirect unresolved requirements;
   a later validated reverse material route adds eight evidence IDs.
2. Saffire observations and conditions: the first typed search adds eight IDs.
   An entity recovered in that search, `saffire-iv-flow-off-20s`, becomes the
   start of an approved relation traversal, adding another evidence ID. This
   does not certify that Saffire-IV answers an explicit Saffire-I request; this
   scenario abstains from complete scientific support.
3. Spacecraft suppression observations and conclusions: typed searches add 12
   and six IDs; documentary searches selected from the updated discoveries add
   seven and three IDs. The remaining relationship requirement stays unresolved.

These demonstrate operational replanning and evidence change, not independently
reviewed useful scientific search in all three cases. EVIDENCE_DRIVEN_REPLANNING
is PARTIAL. Budgets are operational; no action count is a scientific necessity.

## Nemotron and hybrid retrieval

The campaign contains twelve fresh planner calls across the intermediate v2/v4
receipts, consuming 15,863 reported tokens. The final v5 comparison replays six
successful calls and incurs no fresh planning calls. Those replay receipts retain
original usage and inference latency; that latency is not replay execution time.
Fresh inference latency spans approximately 1.35–7.82 seconds in the v4 receipts.
Rejected/duplicate actions and recovered IDs are visible per query.

Some model searches recover different documentary IDs. No expert labels establish
that these are additional **useful** evidence, and no additional complete
depressurization-support answer is demonstrated. NEMOTRON_PLANNING_VALUE remains
INCONCLUSIVE; valid JSON rate is not the scientific metric.

`hybrid.json` compares FTS, vector, KG, lexical+KG, lexical+vector, all three and
contextual retrieval on a frozen 171-passage vector corpus, five queries and a
five-candidate output budget. The existing vector generation is finite and its
metadata hash is recorded. Five fresh query embeddings consume 72 reported
tokens in the final hybrid run; the corpus is not re-embedded or globally enabled.

All five KG candidate sets are nonempty after the harness projects information
and publication candidates as well as run IDs. This corrects an evaluation
projection assumption; it does not establish a production graph-edge repair or
scientific relevance. Contextual candidates are legitimately empty for one
conceptual case in that restricted corpus. Candidate identity differences are
reported; unique useful evidence and precision are NOT MEASURABLE. The H planning
comparison is recorded separately and is not claimed to be a matched reranking
experiment. HYBRID_RAG remains KEEP_EXPERIMENTAL.

## NTRS 20260003546 and publication

The final source is the previously acquired PDF, not the upstream text copy:

`data/raw/autonomous/ntrs-20260003546-b4b64e88992718a7598000ad85d181ac4d9c06ed58e0ae7df0fb4188a6662a18.pdf`

SHA-256:
`b4b64e88992718a7598000ad85d181ac4d9c06ed58e0ae7df0fb4188a6662a18`.

`source_integrity_receipt.json` verifies the digest and all twelve indexed pages
against original PDF page text. No redownload or raw-file edit occurred.

The final extraction stages 32 exact-span proposals: 32 pending, zero newly
rejected, zero new approved canonical scientific facts. Intermediate text-copy
extractions have different dispositions and are not conflated with this PDF run.
The PDF model attempt failed JSON parsing; deterministic proposal extraction
completed. Its token usage was not retained in that failure receipt and is
reported as unknown. The parser now saves provider usage before parsing for
future failures; no token count was invented retrospectively.

Proposed classes, original wording, page/offset, source digest, scope, eligibility
and failure reasons remain in the existing staging registry and noncanonical RDF
projection. Current-study versus cited-study attribution, experimental groups,
quantities and epistemic roles remain incomplete. White Sands/spacecraft subject
matter never grants microgravity. The staged class is a proposal, not scientific
approval. `source_extraction.json` includes independently retrievable proposals.

Publication eligibility now checks contracts instead of assigning a constant
False. Exact unchanged statements under an existing reviewed canonical contract
can replay automatically with their original identity and payload; the trusted
canonical file, not model-supplied APPROVED fields, grants authority. Its
idempotence is tested with an explicitly synthetic approved-record fixture.
The existing public-document publication and approved structured projection
contracts remain operative. No eligible nontrivial new scientific proposition
was approved from this PDF.

The missing authority is an approved new-prose-to-experiment/epistemic publication
contract. Observation-to-conclusion candidates preserve both spans but remain
REVIEW_REQUIRED: shared publication or proximity does not establish attribution.
The canonical SemanticRegistry also lacks an approved scientific support
relation. This campaign does not silently create one. There is no positive
validated NASA observation→conclusion demonstration for the new source.
AUTOMATIC_PUBLICATION_CONTRACTS remains PARTIAL.

## Actual answers and scientific applicability

Complete service outputs and citations are in `answers_e.json`.

- Acrylic/PMMA: the source says “Fuel: acrylic cylinders (PMMA)”
  `[E-751f8e0f5230aa68]`. This establishes that source's terminology, not universal
  acrylic↔PMMA equivalence. The conceptual requirement is partial.
- Depressurization bibliography: relevant source wording is returned for NTRS
  20260003546, 19930015566, 20000120278 and 19990063738. These are dated source
  statements, not a present-day literature consensus or recommendation.
- PMMA: original BASS passages describe radiative quenching below 2 cm/s and
  blowoff as flow crosses 40 cm/s. Without a gravity constraint, both source-backed
  microgravity and ground observations remain accessible. Explicit microgravity
  changes applicability of ground observations to RELATED rather than removing
  them. See `[E-context-90f697823c2ba1b2ea82]` and associated spans in the receipt.
- Saffire-I: S1 and S2 report airflow 20.0 cm/s, with Concurrent versus Opposed
  direction and oxygen 21.5–21.7% versus approximately 21.5%, respectively
  `[E-psi-98-table-S1, E-psi-98-table-S2]`. Source-field burn times are displayed as
  reported quantities rather than silently treated as initial conditions.
- Restored airflow: “The fire didn’t extinguish and began to grow when we turned
  the flow back on” is retained with its experimental/context references
  `[E-context-d1e50788b120206316a0, E-context-80d7fc00aae08504c315]`.
- Open questions: an author's explicit suppressant concentration/hold-time
  question is retrieved `[E-context-9df40cae8e6f693c2466]`; missing evidence elsewhere
  is not converted into a NASA knowledge gap.
- Depressurization conclusions and their supporting experiments: the service
  reports incomplete verified support. Staged document statements cannot certify
  the requested experimental chain. A fluent complete answer is not fabricated.

These examples reproduce source statements. Their independent scientific
relevance, extraction correctness and completeness have not been expert-scored.

## Operations, recovery and reproduction

`operations.json` contains successful application-owned CLI executions for ask,
review, status, validation-only and two offline maintenance cycles without an
API key. `maintenance.json` also contains two complete offline cycles with
model assistance allowed: both replay extraction and consume zero new calls.
The maintenance service example now permits bounded extraction, one model call,
two sources, bounded retries and elapsed limits. It is not installed or enabled.
README documents deliberate installation and inspection commands.

Recovery tests cover malformed PDF, invalid source span, source version rollback,
failed atomic publication integrity gate, interruption of vector publication,
invalid model paths, duplicate/circular actions and retrieval timeout. The failed
publication test restores consistent operation on retry. Not every requested
network/NVIDIA/SHACL/database interruption permutation has a dedicated new test;
OPERATIONAL_FAILURE_RECOVERY remains PARTIAL. Hard deadlines are checked between
operations and cannot forcibly interrupt every SQLite/native call.

Disk space was exhausted by duplicate working snapshots during the campaign.
Four disposable copies created here were removed, retaining their receipts and
the final snapshot. The principal database, historical receipts and NASA raw
sources were not removed. Those duplicate snapshots are reconstructible from the
principal/final registry and retained receipts.

`audit.zip` includes source/code/configuration hashes, lockfile, canonical
projection, scientific context indexes, evaluation inputs/traces, sanitized model
receipts, claim/publication dispositions, tests and a sanitized public evidence
registry. It includes this selected verified PDF while excluding the enormous
historical raw corpus, credentials, private caches and vector corpus.
The package supports deterministic CLI replay and this source's staged workflow.
Full historical/source-level regressions, vector replay and fresh model behavior
still require excluded inputs or credentials. Reproducibility is PARTIAL and is
explicit in `audit_manifest.json`. `artifact_index.json` gives exact paths,
archive paths, byte sizes, counts and SHA-256 digests.

`integrity.json` records conforming canonical/native/taxonomy SHACL, SQLite
integrity, foreign keys, complete and consistent FTS, immutable-source drift zero
and real PMMA→run→investigation paths. Those paths are associations, not causal or
observation-to-conclusion edges. Quality commands and final counts are in
`quality_verified/quality.json` and its logs. Existing rdflib deprecation warnings
are classified separately from scientific validation.

## Final decisions

```text
SEMANTIC_SUFFICIENCY = PARTIAL
ADAPTIVE_INVESTIGATION = OPERATIONAL
EVIDENCE_DRIVEN_REPLANNING = PARTIAL
NEMOTRON_PLANNING_VALUE = INCONCLUSIVE
FINAL_CLAIM_VERIFICATION = ENFORCED
FEATURE_FLAG_INTEGRATION = VALIDATED
CONCEPTUAL_QUERY_HANDLING = VALIDATED
BIBLIOGRAPHIC_QUERY_HANDLING = PARTIAL
SCIENTIFIC_EXTRACTION = PARTIAL
AUTOMATIC_PUBLICATION_CONTRACTS = PARTIAL
OBSERVATION_CONCLUSION_REASONING = REVIEW_REQUIRED
ONTOLOGY_GRAPH_REASONING = PARTIAL
HYBRID_RAG = KEEP_EXPERIMENTAL
AUTONOMOUS_MAINTENANCE = PARTIAL
OPERATIONAL_FAILURE_RECOVERY = PARTIAL
AUDIT_REPRODUCIBILITY = PARTIAL
END_TO_END_SCIENTIFIC_ANSWERS = PARTIAL
INDEPENDENT_SCIENTIFIC_RELEVANCE = REVIEW_REQUIRED
V2_DEFAULT_PATH = KEEP_EXPERIMENTAL
READY_FOR_PHASE_4 = NO
```

The remaining scientific dependencies are independent relevance judgments,
approved experimental/epistemic extraction contracts and reviewed conclusion
attribution. Remaining engineering work includes a broader semantic requirement
matcher, fuller failure-matrix validation and strictly enforced in-flight budgets.
They are not mislabeled as external scientific blockers. The primary success
condition is therefore only partially achieved; this report does not declare
technical or scientific closure.
