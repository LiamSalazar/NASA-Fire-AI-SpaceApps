# Phase 3C consolidation — operational handoff

This is a **partial scientific capability**, with completed engineering integrations
and explicit remaining scientific dependencies. Phase 4 was not started.

## Measured results

| Configuration | Questions with DIRECT | Mean answer words | Valid citation answers |
| --- | ---: | ---: | ---: |
| A: previous V2 renderer, context off | 4/18 | 3,306.94 | 18/18 |
| B: conservative synthesis, context off | 4/18 | 86.61 | 18/18 |
| C: B plus validated applicability | 14/18 | 167.39 | 18/18 |
| D: C plus selective fresh model selection | 14/18 | 159.94 | 18/18 |

These are technical coverage and presentation counts, not independent scientific
precision. Comparisons share corpus and candidate budgets. Vector retrieval was
tested separately, not silently incorporated into these DIRECT counts.

Full questions, QueryIntentV2, sources, classifications, support spans, membership
paths and final answers: [scientist-facing examples](PHASE3C_CONSOLIDATION_ANSWERS_V1.md).
There are ten real-question demonstrations and eighteen machine-readable cases.

## Newly available NASA knowledge

NTRS public discovery returned twelve metadata records. NASA 20260003546 was
acquired as an immutable content-addressed PDF, parsed into twelve cited pages and
projected into the **existing** native graph as Document/Publication. Its actual
public-service query recovered the new source. A repeat update performed no
download, parsing or index rebuild.

No new experimental facts or normative conclusions were automatically published.
Existing 86 verified contexts, eight scopes and two terrestrial exclusions are
reused; the 68 BASS-II and two Saffire-I recoveries are not new autonomous discoveries.
335 other historical executions still have unresolved gravity.

ACME 20210015913 remains blocked by an image-only PDF, not by the restored network.
OCR is not implemented. New-source execution identity and observation/conclusion
membership are not independently certified.

## Models and retrieval

Seventeen fresh Nemotron attempts: twelve selections, three contextual attempts
(two timeouts) and two constrained synthesis calls. The successful context attempt
took 24.24 seconds and reported 3,744 tokens. It proposed four relations: three
were rejected after source/value validation, including unsupported microgravity;
one Nomex mention remains staged with unresolved experimental scope. No additional
DIRECT coverage or newly verified contextual relation was demonstrated.
Both synthesis calls accepted two exact supplied claims, in 6.88 and 3.00 seconds;
that does not validate unrestricted scientific paraphrasing. Jev was not called.

The existing embedding provider processed 102 fresh inputs over 45 frozen units;
the follow-up ranking comparison used cache replay. Seven retrieval configurations
were recorded at k=5, with two graph paraphrase cases explicitly unexecuted. Without
independent relevance judgments, Precision@5, Recall and nDCG remain blank.
Vectors remain local and disabled in the default native query path.

Resource inspection: eight logical CPUs, approximately 15.4 GiB RAM, approximately
4.8 GiB available RAM and 2.7 GiB free repository filesystem space. `nvidia-smi`
was not available; this does not prove the machine has no GPU. Existing hosted
embeddings were reused rather than downloading a new model into limited disk space.
Complete billing/cost estimates are unavailable; recorded embedding token usage is
a last-batch lower bound, not total billable usage.

## Integrity and operation

Fresh full suite: 253 passing tests. Ruff format/lint and canonical, native and
taxonomy SHACL conform. All 1,050 frozen historical file digests are unchanged.
159 original units are checked against exact text spans or original CSV cells;
twelve new PDF locators match physical page text. SQLite integrity, reference
anti-joins and FTS identity/completeness pass. This schema has no declared foreign
keys, so the anti-join results—not an empty PRAGMA result alone—establish integrity.

The 72,960 warnings are rdflib's Dataset.default_context deprecation: 233 from
native-semantic tests and 72,727 from scientific-enrichment tests. No blanket
suppression was added. Historical parity was freshly rerun: DIRECT 31/39,
RELATED 37/39, exact evidence sets 6/39. Dynamic 230/230, post-freeze 125/125 and
class 5/5 checks were freshly run, not replayed receipts.

Rollback archives publication while retaining raw files, all historical evidence
records and resolvable citations. Retrieval omits superseded/rolled-back sources;
the public service invalidates its graph cache when source status changes. FTS
validation now materializes its virtual-table scan to avoid repeated full scans;
the read-only CLI validation was rerun successfully after this optimization.

Latest receipts: quality_v3, source_integrity_v3, cli_validation_v1 and
artifact_index_v4 under artifacts/phase3c_consolidation_*.json. The index includes
code, reports, receipts, scheduling examples and the new raw PDF, with exact hashes.
Secrets and rebuildable vector caches are excluded. No commit or push was performed
for this campaign. Scheduling examples are verified but not installed.

```bash
uv run python scripts/maintain_knowledge.py discover --query 'microgravity combustion'
uv run python scripts/maintain_knowledge.py dry-run --nasa-id 20260003546
uv run python scripts/maintain_knowledge.py controlled-update --nasa-id 20260003546
uv run python scripts/maintain_knowledge.py review-pending
uv run python scripts/maintain_knowledge.py validation-only
```

## Decisions

```text
SCIENTIFIC_SYNTHESIS = KEEP_EXPERIMENTAL
CLAIM_GROUNDING = PARTIAL
EVIDENCE_SELECTION = KEEP_EXPERIMENTAL
CONDITION_AGNOSTIC_RETRIEVAL = VALIDATED
HYBRID_RAG = KEEP_EXPERIMENTAL
VECTOR_RETRIEVAL = INCONCLUSIVE
ONTOLOGY_GRAPH_INTEGRATION = PARTIAL
AUTOMATED_SOURCE_DISCOVERY = PARTIAL
INCREMENTAL_INGESTION = PARTIAL
AUTOMATED_KNOWLEDGE_PUBLICATION = CONTROLLED
CONTINUOUS_EVALUATION = PARTIAL
NEMOTRON_INCREMENTAL_VALUE = INCONCLUSIVE
JEV_INCREMENTAL_VALUE = INCONCLUSIVE
END_TO_END_SCIENTIFIC_ANSWERS = PARTIAL
INDEPENDENT_SCIENTIFIC_RELEVANCE = REVIEW_REQUIRED
V2_DEFAULT_PATH = KEEP_EXPERIMENTAL
READY_FOR_PHASE_4 = NO
```

Remaining dependencies: independently reviewed claim relevance/usefulness; approved
new-source experiment/extraction contracts; OCR; conceptual acrylic/PMMA identity;
open-question scope; observation-to-conclusion links; geometry reconciliation;
full per-cycle scientific regressions and adjudicated vector comparison. Discovery
is not yet autonomous bulk scientific selection/publication. The review packet
keeps independent reviewer fields blank rather than fabricating approval.
