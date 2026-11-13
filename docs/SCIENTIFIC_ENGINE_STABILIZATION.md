# Scientific engine stabilization assessment — 2026-11-09

## A. Executive release decision

**SCIENTIFIC ENGINE NOT YET ACCEPTED.** The conversational verifier now audits
approved graph relations and retains documentary claims when no triple exists.
The four-question paired pilot still has substantial answer omissions and
fallbacks. The 85% coverage and usefulness gates, as well as independent
document-OOS evidence, are not met. Technical interface testing can proceed
with this status visible to operators; scientific dashboard release cannot.

## B. Root cause

The last provenance correction moved source selection to the backend, but claim
alignment still begins with text overlap and NLI. Source-local numeric, modality
and absence controls protect many false claims, while rejecting some faithful
paraphrases. One false rejection treated digits in a correctly cited report
identifier as an unsupported measurement. The final verifier now removes only
the exact backend-resolved source/document identifier before comparing numeric
values. Repair does not reliably recover other rejected propositions. An explicit
pronoun ban discarded potentially resolvable claims. The Saffire table pilot
exposed a separate retrieval/context gap: the full experimental table was not
in the response evidence package, so neither model answered sample-level
airflow and oxygen conditions. A citation to a related report cannot fill it.

## C. Ontology integration and inventory

The immutable snapshot contains 64 OWL classes, 11 OWL object-property
declarations and 36 subclass statements. The native `SemanticRegistry` has 16
approved relation definitions and 3,472 graph entities in this snapshot.

| Stage | Actual use and boundary |
| --- | --- |
| Retrieval | Query intent, native RDF execution, approved aliases, class ancestors and `ontology_navigation.navigate` constrain DIRECT/RELATED and expose typed paths. The optional graph enrichment flag is separate from these active capabilities. |
| Query interpretation | `SemanticRegistry`, query language and graph identities resolve recognized entities and properties; unknown words remain unresolved. |
| Context assembly | Source propositions, conditions and registry IDs are retained, but allocation remains lexical and has no ontology sufficiency proof. |
| Comparison | Native graph values and condition relationships drive comparison; unknown conditions remain unknown. |
| Claim alignment | Backend source selection now calls `audit_relation` after documentary verification. Explicit approved predicate aliases and two unambiguous resolved graph entities receive typed domain/range and evidence-linked triple review. |
| Claim verification | An ontology-incompatible explicit relation is rejected. An approved graph triple is only a sourced candidate; original passage verification still has to pass. A missing triple remains eligible for documentary verification. |
| Final composition | Existing verified-proposition restoration and registry-owned citations remain. There is no new ontology-based answer organizer. |

The audit records resolved entity IDs, ontology predicate URIs, graph assertion
IDs and evidence IDs when they genuinely exist. It cannot interpret every
natural-language relationship; unrecognized relations stay documentary. SHACL
still checks graph structure and provenance, not the truth of prose. No ontology,
graph snapshot or vocabulary was mutated.

## D. Overfitting review

The unconditional leading-pronoun rejection was narrowed. A singular `It` or
`Its` is resolved only from one verified graph entity in the same generated
segment, then the expanded proposition is verified again. Ambiguous referents
remain rejected. This is a defensible contextual normalization, not an
experiment-name map. Existing source-local table and reporting-absence guards
are retained as general document-structure safeguards. The `uses ..., described
as ...` split remains a narrow linguistic normalization that independently
verifies both clauses; it grants no relationship authority. These and other
legacy phrase checks still warrant further generalization. No benchmark source
title, experiment ID or expected value was added to production rules.
The source-ID numeric correction uses backend identity rather than a
source-specific punctuation rule.

## E. Evidence and provenance

`EvidenceRegistry` resolves original spans and source metadata. The graph audit
requires registered evidence for a relation receipt. The claim ledger now
records optional resolved entities, predicates, assertion and evidence IDs,
scientific status and verification mechanism alongside the previous proposal,
repair, acceptance, communication and citation stages. Model `support_ids`
remain hints. The backend alone emits citations. Graph compatibility is never
treated as proof of a particular observation.

## F. Verification and source-inspected pilot review

Four English questions were frozen in
[`pilot_questions.json`](../artifacts/scientific_engine_stabilization_v1/pilot_questions.json)
before paid calls (SHA-256 `762ec7c438458a916f15a9d8c01ec84751bc59d182902d624d8ce9be2e3804eb`).
Both providers received the same question and backend evidence-routing contract.
They did not always receive byte-identical packages because each provider's
planning queries influenced retrieval; this limits causal model comparison.

| Case | Sonnet final | Nemotron final | Source-inspected finding |
| --- | --- | --- | --- |
| MIST–RTDFS–GEL geometry | Source excerpts | Partial generated comparison | The excerpts expose rods, sheets and spheres with dimensions. Nemotron explains the three material/shape identities but omits dimensions. Neither is a complete natural comparison. |
| FLEX diameter method | Partial generated prose | Generated explanation | The original FLEX report/table distinguishes initial diameter and visible extinction diameter. Nemotron explains both definitions with source passages; Sonnet instead describes apparatus and general conditions. |
| Saffire I sample conditions | Candidate metadata | Source excerpts | Neither answer gives sample-level table airflow and oxygen conditions. Related sources and catalogue entries do not supply them. |
| Standard methods and scope | Partial generated prose | Narrow generated prose | Sonnet cites the standard's purpose and methods section for flammability, offgassing and compatibility. Nemotron states only the flammability purpose. Neither fully explains test scope. |

These are operator source inspections, not independent scientist adjudications.
Proposal acceptance counts are verifier decisions, not scientific precision:
Sonnet accepted 7 of 96 checked propositions in the four final turns; Nemotron
accepted 7 of 59. Rejected faithful paraphrases and remaining false acceptance
risk have not been exhaustively adjudicated. The generic ontology tests cover
a sourced triple, an absent triple, incompatible endpoints and safe pronoun
resolution. They do not establish universal scientific fidelity.
The source-ID correction was replayed against saved raw outputs after this live
pilot; no fresh final-version complete-turn acceptance percentage is claimed.
The pilot also exposed a transport label bug: successful Sonnet turns inherited
the old `generated_by: Nemotron` display value. Final code derives that field
from the selected provider. Historical response receipts retain the original
incorrect label and are analyzed by recorded model identity instead.

## G. Scientific context and retrieval

The unchanged historical provisional, source-inspected 24-question relevance
set reproduces macro Recall@20 **96.15%** (13 questions source inspected; no
independent scientist review). Its 32 anchor evidence judgments cover only a
bounded corpus and unjudged candidates are not negatives. The pilot Saffire
failure shows that stable retrieval recall on this set does not guarantee
question-specific context sufficiency. See
[`recall-recheck.json`](../artifacts/scientific_engine_stabilization_v1/recall-recheck.json).

## H. Final answer coverage

The pilot did not have independently adjudicated, pre-frozen essential-answer
targets, so it cannot certify the 85% gate. The response modes and source review
above demonstrate missing communicated information in three of four cases for
both providers. The ledger continues to distinguish retrieved, supplied,
generated, verified and communicated material. Excerpts make originals
accessible but do not count as a natural generated explanation.
A saved Nemotron follow-up supplied the preceding real droplet question and
answer as conversation history, then asked for original defining passages and
time zero. It returned long source excerpts after only three of seven checked
propositions passed. This is a multi-turn diagnostic, not a complete
multi-turn acceptance campaign, and reinforces the coverage NO-GO.

## I. OOS generalization

The pilot includes one known-document regression and three new questions about
known sources. It is **not** document-, investigation- or source-family-OOS.
Historical evaluation receipts expose several available investigations, and
the bounded snapshot does not provide a clean independent held-out family for
this round. No OOS success rate is claimed. Future independent sources must be
frozen before any evaluation-specific correction; a debugged case becomes
development material. The explicit empty OOS partitions and leakage rule are
recorded in
[`oos_partitions.json`](../artifacts/scientific_engine_stabilization_v1/oos_partitions.json).

## J. Nemotron versus Sonnet

Sonnet is a configurable alternative, not the default. Its standard response
was somewhat broader; Nemotron's droplet response was substantially more
responsive. Both failed the geometry completeness and Saffire table cases.

To isolate generation, four additional evidence packages were frozen from the
union of both retrieval traces, checked against the registry and allocated by
the same deterministic context algorithm. Within each case, both models saw
the **identical package hash** and explanation contract. Source-inspected raw
Sonnet drafts were more complete on geometry (rods, sheets, spheres and
dimensions) and the standard's scope; Nemotron was more directly responsive on
droplet diameter definitions. Neither received the Saffire experimental table.
Before the source-ID fix, backend replay accepted Sonnet/Nemotron propositions
as follows: geometry **1/0**, droplet **1/3**, Saffire **0/0**, standard **3/0**.
These are acceptance counts, not accuracy rates. The source-ID fix raised
Sonnet geometry to two accepted propositions in a zero-cost replay; all other
replays are retained in
[`fair-summary.json`](../artifacts/scientific_engine_stabilization_v1/fair-summary.json)
with package hashes and raw response filenames.

This establishes complementary raw generation behavior, but no demonstrated
final-answer advantage or release readiness. Backend false rejection and
context selection dominate. S2 was deferred because further paid generation
cannot decide deployment until these deterministic defects are corrected.
There is no basis for mandatory two-model review or an automatic router.

## K. API costs and provider behavior

The pilot used Claude Sonnet 5.5 via the official Messages API with JSON schema
output. [Anthropic's model page](https://platform.claude.com/docs/en/models/sonnet-5-5/overview)
lists `claude-sonnet-5-5` at USD 2 per million input and USD 10 per million
output tokens. [Structured-output documentation](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)
specifies `output_config.format`; the existing Anthropic SDK is reused with
zero retries. [Anthropic's rate-limit documentation](https://platform.claude.com/docs/en/api/rate-limits)
describes tier-specific request, input-token and output-token limits; the
evaluation brake stops subsequent calls after a recorded rate-limit or credit
failure. Four Sonnet turns plus four equal-package explanations made 18
paid attempts: 16 complete responses
and two `max_tokens` repair truncations. Provider-reported usage in the saved
turn traces totals **421,671 input** and **22,126 output** tokens, for an
estimated **USD 1.064602**. One preflight input-ceiling rejection made no paid
call; its planning response was reused from cache on the next attempt.
Mean summed provider-call latency per completed full turn was **36.04 s** for
Sonnet and **17.07 s** for Nemotron. In the equal-package explanation-only
comparison, means were **10.78 s** and **8.35 s**, respectively. These are four
observations per provider, with no network or load normalization; they are not
service-level latency guarantees.
The content-addressed cache includes provider, model, settings, prompt,
question/evidence payload and schema. The USD 15 and 40-call hard caps were not
approached. NVIDIA billing cost was not available from its receipts and is not
invented here.

## L. Stability

Snapshot verification passed with original source, RDF and evidence hashes
unchanged. The historical retrieval recheck passed. Focused ontology, ledger,
provider and conversation tests passed. The final complete regression ran in 11
controlled batches: **3,589 passed, 40 existing skips, zero failures**. Its
logs and manifest are in `artifacts/scientific_engine_stabilization_v1/regression-final/`.
The earlier `regression-batches/` receipt is transitional and is not added to
the final count.
All four required B8 guard files passed (50 tests). Locked `uv sync`, compile,
Ruff and Git whitespace checks passed. The HTTP conversation tests ran in the
regression; provider selection and credential-free startup were also checked.
All 37 emitted pilot and follow-up citation evidence references, including the
diagnostic attempt, resolve to registered passages and source metadata; this is a
structural provenance result, not semantic support certification. No credential
pattern appeared in the tracked pilot artifacts.

## M. Remaining limitations

**Critical:** verified answer coverage, source-scoped alignment, faithful
paraphrase retention, and complete Saffire table context remain below the
release target. Independent OOS and complete multi-turn acceptance are absent;
the one measured follow-up fell back to excerpts.
**Corpus:** the snapshot is bounded and missing relations are not evidence of
a NASA knowledge gap. **Optional:** broader linguistic normalization and a
larger provider comparison can follow once the backend passes its own gates.

## N. Dashboard integration

The unchanged `scientific-chat-v1` response, evidence detail, continuation,
comparison and discovery contracts are in
[the dashboard handoff](SCIENTIFIC_ENGINE_DASHBOARD_HANDOFF.md). NVIDIA remains
default. `NASA_SCIENTIFIC_LLM_PROVIDER=anthropic` selects Sonnet when its
server-side key is present; without a key, local search and excerpt mode remain
usable. `ANTHROPIC_SONNET_MODEL` is configurable. Scientific release status is
NO-GO regardless of provider configuration.

## O. Git

All implementation and receipts are local on `NASA_hackathon` in
`.worktrees/NASA_hackathon`. The initial architecture commit is `1ccb7d4` and
the first pilot/report commit is `ff205b7`. The final fair-evaluation and
source-ID correction commit is identified by `git log -1` at handoff. No push
or merge is authorized. The protected `main` and `diego/research` refs were
checked against their baseline values; worktree status is reported after the
final commit.
