# Phase 1.5 final closure status

## Executed scale and integrity

Before this completion work the registry held 11 documents and 848 FTS passages. After: 286 documents, including 275 managed verified upstream NTRS texts; 6,054 canonical passages; 6,054 FTS rows; 282 sources; and 275 artifact/document-metadata records. The upstream catalog had 277 records, 275 verified/imported and two missing text files. Re-indexing unchanged cache added zero artifacts or passages. All logical-passage duplicate, FTS-orphan, evidence-ref-orphan, candidate-orphan, and review-orphan checks are zero.

Structured science remains unchanged: 24 PSI investigations discovered, 22 tables profiled, eight managed table groups, and 405 canonical experimental runs. The 3,831 canonical entities and 24,014 RDF triples remain evidence-backed; SHACL conforms. No new ontology vocabulary was added. FLEX-2 ranges, smoke/soot measures, and ambiguous burning-rate units remain review items.

## Fixed evaluation baseline

The gold sets are 30 epistemic cases, 50 retrieval questions, and 15 semantic-resolution cases. FTS/BM25 source retrieval (40 source-backed questions) is Recall@1/3/5/10 = 0.6250/0.8500/0.8500/0.9000, MRR 0.7226. Current structured status correctness is 0.8000 overall, DIRECT 1.0000, RELATED 1.0000, and abstention 0.6667 over its 10 relevant cases. These are pre-vector baseline measurements, not Phase-2 functionality.

## Jev decision

The live official TypeSafe benchmark executed after successful model discovery. The requested stable alias `jev-latest` returned actual model `jev-1.13.0`; 31 API calls evaluated all 30 frozen cases using bounded `noul` triage and closed-set `choice` classification. Triage accuracy/precision/recall/F1 was 0.9333/0.8889/0.8889/0.8889 with one FP and one FN. Epistemic accuracy was 0.7333, macro precision/recall/F1 0.5083/0.7714/0.5733, below the deterministic rule macro F1 of 0.6576. NONE precision/recall was 1.0000/0.7143; OpenQuestion FPR 0.0000; reported-observation FPR 0.5000; SafetyImplication precision 0.5000. Median latency was 0.309 s; API returned 19,666 input and 4,343 output tokens, but no cost field.

`JEV_DECISION = ADOPT_FOR_SPECIFIC_TASKS`: optional advisory rhetorical triage/review prioritization behind `SEMANTIC_CLASSIFIER_BACKEND=jev`, with no automatic discard threshold. The 30-case threshold experiment showed a 0.50 threshold still misses one claim and a 0.80 threshold misses four, so it is not productionized. Jev has no authority over claims, DIRECT, ontology, calculations, or KG writes. Nemotron remains the candidate-only evidence-span extractor; the historical shared-negative audit favors Jev on background rejection (14/20 NONE versus Nemotron proposing candidates for all 20) but is not a full equal-denominator replacement benchmark.

## Quality and decision

The review queue remains 0 pending (2 approved safety implications, 20 preserved rejections). A graph rebuild produced 24,014 triples and SHACL conformance. Final automated validation: `uv run pytest -q` passed 39 tests; `uv run ruff format --check .` and `uv run ruff check .` passed.

`READY_FOR_PHASE_2 = YES`. The prior sole blocker—the required live Jev benchmark—is now complete, with a bounded evidence-based adoption decision. No Phase-2 functionality was implemented.
