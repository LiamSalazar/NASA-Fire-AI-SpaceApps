# Phase 3C — corrective evaluation closure

**READY_FOR_PHASE_4 = NO.** The corrective implementation and evaluation cycle
is closed with failed readiness gates, not with a claim of product completion.
V2 remains experimental. Phase 4 was not begun. Phase 3B history, original Phase
3C predictions, first-pass holdouts and benchmark expectations are preserved.

Primary machine-readable results:
`artifacts/phase3c_corrective_benchmark_summary_v3.json`, final quality v1,
final integrity v2, and the separately versioned case-level JSONL files.
Protocol: [corrective benchmark protocol](PHASE3C_CORRECTIVE_BENCHMARK_PROTOCOL.md).

## System baseline and limitation addressed

The unchanged baseline contains 282 sources, 286 managed documents, 6,055
passages/FTS entries, 405 canonical run records, 3,002 condition records,
24,014 canonical RDF triples and four historical staging candidates. Raw and
canonical digests, approved vocabulary and original evaluation gold are unchanged.

The old native execution view projected scientific values from two legacy run
rows. It also lost documentary evidence, poorly resolved minimal model output,
over-classified generic table rows, and failed end-to-end usefulness. The repair
is additive; V1 remains available. No QueryIntentV3 or architecture replacement
was introduced.

## Native semantic model, projection and coverage

Registered property identities are data. Generic value/relation records carry
subject, property/relation identity, original value/unit, normalized value when
valid, qualifiers/context, source and evidence. Declarative legacy mapping is a
one-time projection boundary, not the native query executor.

Coverage: 405/405 eligible canonical run entities projected; 408 validated generic
reported conditions; 812 relations; zero newly asserted observed measurements.
Two runs have no validated generic value. All 405 have unresolved fields;
2,588 candidates retain original ConditionRecord provenance, including 274
unsupported mmHg-unit fields. Missing original values: zero. Broken native evidence
IDs: zero. 424 unique original-record references retained; this is not the number
of graph evidence edges. Repeated projection is idempotent in tests.

The projected values are reported conditions, not proven observed measurements.
Upstream run type is inherited from canonical records; this does not independently
prove every row represents an executed experiment. Initial/final qualifiers are
preserved, but full context-selective querying is not yet complete. Unsupported
properties/units are staged rather than fabricated or silently canonicalized.
See [coverage audit](PHASE3C_NATIVE_COVERAGE_AUDIT.md).

## Native execution and extensibility proof

Runtime guards prohibit legacy V1 match/bundle builders and V1-as-V2 execution
after constructing V2. Dynamic native benchmark: 230/230 cases across 25 numeric
and ten categorical properties plus five class registrations. Post-freeze stress:
125/125 cases across 13 additional numeric and seven categorical properties plus
five classes. Fixture identities are absent from production executors. These
benchmarks validate generic compilation, constraints and DIRECT/RELATED behavior;
they do not validate arbitrary new scientific unit systems or NASA source semantics.

Scientific fields in QueryIntentV2: zero. Named legacy-property conditional
branches in the audited native planner/evaluator: zero. Native source-ID/evaluation
case conditional audit is persisted with its exact file scope in final quality.
Legacy source-specific mappings remain only at the projection boundary. This
is a bounded static audit plus dynamic execution evidence, not a formal proof
that all conceivable code paths are source-independent.

MATCH/DIFFER/UNKNOWN/INVALID remain distinct. Missing values are UNKNOWN;
conflicting reported outcomes cannot establish DIRECT. Approximation without
explicit tolerance remains non-exact; no implicit universal ±5% is used.

## Query contract and language understanding

The corrective live benchmark covers only the 39 supported standalone reviewed
V2 objects, two conversational objects and 30 original compositions. It does
not establish the old conceptual 47/47 contract-coverage claim. Unsupported
reviewed gap cases need explicit validated gold, not model-generated labels.

Nemotron minimal extraction: 71 completed historical cases. First corrective
standalone exact intent 6/39; post-benchmark deterministic resolution repair
10/39. Targets F1 1.0000, entities 0.9706, properties 0.9091, requested information
0.5128. Numeric/operator/unit each 5/6, comparison 2/3, ambiguity 37/39,
unknown handling 23/39, clarification 36/39. Conversational exact 0/2; original
composition exact 1/30. Small relevant subgroups are SMALL_N, not strong evidence.
The final error matrix identifies field-level failures rather than equating every
inexact intent with every field being wrong.

The new composition campaign freezes 30 intent-first surfaces across ten template
families BEFORE prediction. Exact outcomes, field metrics and novelty relative to
original gold are in `phase3c_corrective_compositional_summary_v1/v2.json` and
`phase3c_corrective_compositional_novelty_v1.json`. These labels derive from
deterministic intended semantics, not expert scientific relevance review. Executor
code was not changed after this campaign began. Do not pool its denominator with
historical compositions. See [interpreter results](PHASE3C_QUERY_INTERPRETER_CORRECTIVE_RESULTS.md).

There are 27 cases with previously unseen capability combinations and nine new
composition signatures. First attempt yielded 27/30 valid responses and three
timeouts; after one bounded retry, 30/30 valid, 3/30 exact. Target/entity/property/
information F1 are 0.8333/1.0000/0.8750/0.9130. Numeric/unit 24/24, operator 21/24,
range 6/6, approximation preservation 0/3, comparison 0/3. Small subgroups are
SMALL_N. API attempts total 33; no executor changes or gold adjustments occurred.

## KG, documentary and safety retrieval

Native KG results cooperate with the existing BM25 registry. Eligibility filters
are applied before SQL ranking/truncation; source metadata is recovered through
document relationships. Reviewed epistemic classes and documentary targets are
first-class, without turning publications into run searches. Measurement-only
queries do not append unrelated safety statements.

Independent objective identity probes: 11/11 positive evidence recovery,
Recall@1/3/5/10 all 11/11; MRR 1.0000. Nine reviewed statement identities recover
9/9; unavailable-source no-answer 1/1. These near-exact lexical probes are not
exhaustive independent scientific relevance gold. Precision@k is unmeasured.

Old V1/native parity: DIRECT 37/39, RELATED 39/39, exact evidence IDs 5/39.
The two DIRECT differences reflect expanded BASS projection versus V1's two-run
view; the remaining documentary disagreements require independent review.
V1 does not define scientific relevance. A complete disagreement review packet
is persisted without pretending that subjective labels are expert-reviewed.

BM25 regression N=40: Recall@1 25/40, @3/@5 34/40, @10 36/40. MRR 0.7267361
versus historical 0.7225694 due to deterministic evidence-ID tie ordering.
No global vector retrieval was enabled. See [retrieval repair](PHASE3C_EVIDENCE_RETRIEVAL_REPAIR.md).

## Holdout selection, first pass and generalization

Corrected architecture freezes preceded metadata-only selection. Prior exposed
sources were excluded using historical corpus/acquisition/evaluation history.
Both bounded candidate pools, stable ordering, exclusions and preflight results
are preserved in corrective v1/v2 candidate/manifest files. No selected source
was replaced because of its scientific content or poor utility.

The selected new official NTRS document is 20140011119, six pages, 306,201 bytes:
*Radiative Forcing Due to Major Aerosol Emitting Sectors in China and India*.
Its unrelated aerosol scope was learned after metadata-based selection. It
supports generic document ingestion, NOT microgravity-combustion expertise.
An isolated registry/index contains six passages. Source acquisition 1/1;
six literal passage probes yield Recall@1 5/6, @3/@5/@10 6/6 and MRR 5.5/6=0.9167,
all SMALL_N. No scientific claim classifications were published.

No eligible new structured experimental artifact was acquired in this bounded
campaign. This is not a claim that NASA has no such dataset. New-source known
mapping precision/recall, scientific unknown-concept handling and staging
completeness lack denominators: NOT_EVALUATED. Zero holdout-specific scientific
code additions and zero published new scientific facts are counts, not proof
of complete semantic mapping. Earlier small holdouts are preserved, not relabeled
new. Generalization evidence is LIMITED.

First-pass artifacts remain immutable. Generic repairs are separately logged
in [post-freeze changes](PHASE3C_CORRECTIVE_POST_FREEZE_CHANGES.md); no second pass
is called zero-shot. Generic table-role protection is tested with four fixtures,
all unreviewed, zero automatic canonical runs. See [ingestion audit](PHASE3C_GENERIC_INGESTION_AUDIT.md).

## Jev additional value

Existing adapter, discovered `jev-latest`, actual response model `jev-1.13.0`;
30 live reviewed binary cases, nine positive and 21 negative. Rules precision/
recall/F1 0.8571/0.6667/0.7500; Jev 0.8889/0.8889/0.8889. False positives one
for both; false negatives three versus one. Combined priority finds nine relevant
items in the first ten review positions versus seven for rules on this sample.
This is suggestive simulated prioritization, not measured human review savings.
No hard filtering or scientific authority is delegated. Keep optional, disabled
by default. See [Jev evaluation](PHASE3C_JEV_EVALUATION.md).

## Grounding and actual end-to-end usefulness

The quotation-only boundary remains because independently reviewed paraphrase
fidelity gold is absent. Deterministic presentation is more readable; authority,
DIRECT/RELATED, negation and units are not transformed. Unclassified documentary
quotes are not observations. Final metadata audit revalidates stored quotes offline.

Twenty integrated native cases: planning 20/20; repaired exact intent 5/20;
required evidence/no-answer recovery 8/12; strict full objective success 2/20;
useful safe fallback 2/20. Eight cases remain relevance REVIEW_REQUIRED.
First corrective pass was 1/20 full success and 7/12 recovery. This improvement
is a disclosed repair result, not readiness.

Repaired bounded synthesis: six attempts, four valid drafts, five accepted
complete-source quotes, zero rejected valid-draft claims. Citation validity 5/5,
SMALL_N; zero visible unsupported generated claims in that accepted set. Invalid
draft/API attempts remain failures. Accepted irrelevant quotations do not count
as useful scientific answers. Separate paraphrase/causal/scope fidelity accuracy
is NOT_EVALUATED. See [synthesis](PHASE3C_GROUNDED_SYNTHESIS_RESULTS.md) and
[end-to-end results](PHASE3C_END_TO_END_CORRECTIVE_RESULTS.md).

## Latency

Standalone interpretation N=39: median/p95/max 3,064.95/17,708.14/20,310.66 ms.
Objective native retrieval N=12: planning median 9.08 ms, KG 66.70, BM25 21.69,
bundle 0.11, total 100.50; total p95/max 134.07 ms. Jev N=30:
185.94/302.80/305.95 ms. Repaired synthesis N=6:
14,943.69/40,219.47/40,219.47 ms. Integrated execution N=20:
82.67/40,345.90/42,662.12 ms, excluding reused language-call wall time.
No assembled timing is presented as a freshly measured serial end-to-end latency.
Novel composition latest-success language latency N=30 is
5,305.76/28,684.30/29,233.23 ms; the three earlier timeouts remain separately logged.

## Quality and scientific integrity

Final quality artifact records actual outputs: Ruff format/check PASS;
pytest 84 passed, with 197 existing rdflib deprecation warnings. Canonical and
native SHACL conform. DB integrity is `ok`, baseline counts preserved, FTS
integrity checked, native evidence references resolve, no duplicate passage IDs.
Raw/canonical/original-gold/historical-artifact digest comparisons all pass.
The mutable checkpoint alone is intentionally excluded from historical immutability.
Baseline staging provenance is checked independently and remains unreviewed.
No credentials are stored in source, tests, docs or artifacts.

## Decisions and smallest justified remaining work

| Gate | Decision |
| --- | --- |
| NATIVE_V2_EXECUTOR_DECISION | REVISE |
| QUERYINTERPRETER_V2_DECISION | REVISE |
| GENERIC_INGESTION_DECISION | REVISE |
| GROUNDED_SYNTHESIS_DECISION | REVISE |
| JEV_TRIAGE_DECISION | KEEP_OPTIONAL |
| GENERALIZATION_DECISION | LIMITED |
| V2_DEFAULT_PATH_DECISION | KEEP_EXPERIMENTAL |
| READY_FOR_PHASE_4 | NO |

Remaining blockers, evidence and smallest corrective scope:

1. Genre/topic retrieval misses reviewed observation/guidance/conclusion evidence:
   service recovery 8/12. Repair generic requested-class/topic cooperation, not
   blanket safety inclusion; rerun frozen cases in a new pass.
2. Requested information and qualified operands are unreliable: F1 0.5128,
   standalone exact 10/39, composition failures. Improve generic minimal extraction/
   resolution; retain ambiguity/unknown abstention and frozen gold.
3. Native context/unit coverage remains partial: 2,588 candidates and 274 mmHg
   fields. Independently approve the required mappings/conversions and add context
   selection; do not auto-promote scientific vocabulary or design ranges.
4. Scientific relevance and paraphrase fidelity lack adequate independent labels.
   Review the persisted disagreement packet and source-backed adversarial examples
   before permitting paraphrases or claiming expert-level relevance accuracy.
5. Meaningful new structured combustion generalization is not demonstrated.
   Acquire a genuinely unseen eligible experimental artifact after a new freeze,
   evaluate in isolation, and preserve failed/first-pass results.

These are bounded repairs and evaluation obligations, not an instruction to
redesign the architecture or start another phase. Verification commands remain
`uv run ruff format --check .`, `uv run ruff check .`, `uv run pytest -q`.
The progress checkpoint records the exact failed gates and next dependency-ready
work. A negative evaluation is the defensible result; expert time should not yet
be spent discovering these known engineering failures.
