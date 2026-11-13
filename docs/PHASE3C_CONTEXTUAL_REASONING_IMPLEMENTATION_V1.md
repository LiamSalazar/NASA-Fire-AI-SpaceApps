# Phase 3C contextual scientific reasoning — implementation v1

This increment extends the existing V2/native architecture. It does not create
QueryIntentV3, a parallel graph, new ontology vocabulary, or a Phase 4 path.

## Implemented boundaries

- `nasa_fire_ai.context` defines source-backed context statements, structure-preserving source units, explicit scope statuses, a deterministic scope resolver, and a retrieval-only context policy.
- `ContextQueryPolicy` prefers microgravity only when gravity is unspecified. It records the preference in retrieval metadata and never inserts a gravity fact into RDF or changes a run's stored value.
- Scope resolution accepts only linked entity IDs and evidence IDs. Local/execution scope outranks campaign scope; same-scope authoritative disagreement is `CONFLICTED`; exceptions produce `NOT_APPLICABLE`; candidate statements never become verified.
- `NvidiaContextInterpreter` reuses the existing NVIDIA adapter and returns untrusted proposals. Exact evidence IDs and verbatim supporting text are required before a proposal is marked `ACCEPTED_FOR_REVIEW`.
- `SemanticGraph.add_context_relation` publishes only an already canonical relation, reviewed endpoints, validated status, and resolvable evidence. It cannot invent predicates or publish model proposals.

## Evaluation fixture coverage

The new tests cover context persistence across linked runs, unrelated-run isolation,
local-versus-campaign precedence, explicit exceptions, candidate status, default
microgravity preference, and rejection of unsupported model evidence. Existing
Phase 3C tests continue to cover qualifiers, provenance, numerical fidelity,
dynamic relations, RAG, native execution, rollback, and Jev advisory isolation.

## Pilot and review state

The repository contains the previously frozen evidence identities and Phase 3C
review artifacts. This implementation does not rewrite them or claim that BASS-II
or Saffire-I execution-level gravity is newly verified. No independent scientific
relevance labels were available in this run; scientific precision and attribution
remain review-required. Fresh live model inference was not required for the
deterministic implementation and no secret or API key was emitted.

## Decisions

```text
MICROGRAVITY_DEFAULT_POLICY = ADOPT
CONTEXT_EXTRACTION = KEEP_EXPERIMENTAL
SCIENTIFIC_SCOPE_RESOLUTION = KEEP_EXPERIMENTAL
ONTOLOGY_CONTEXT_ALIGNMENT = PARTIAL
GRAPH_CONTEXTUAL_REASONING = KEEP_EXPERIMENTAL
NEMOTRON_CONTEXTUAL_VALUE = INCONCLUSIVE
JEV_ADVISORY_VALUE = INCONCLUSIVE
SCIENTIFIC_ATTRIBUTION = REVIEW_REQUIRED
V2_DEFAULT_PATH = KEEP_EXPERIMENTAL
READY_FOR_PHASE_4 = NO
```

The conservative experimental decisions reflect missing independent scientific
labels and the absence of a fresh, reviewed BASS/Saffire applicability gold set.
