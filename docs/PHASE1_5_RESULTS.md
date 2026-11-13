# Phase 1.5 results

Phase 1.5 now has representative documentary retrieval scale: the upstream 277-record NTRS catalog yielded 275 verified cached texts, 275 managed versioned documents, and 5,206 additional passages. The managed registry is 286 documents, 6,054 passages/FTS rows, and 282 sources; deterministic re-import added zero rows. This import is documentary indexing only, never automatic KG publication.

Structured scale remains 24 PSI investigations discovered, 22 tables/2,870 rows profiled, eight table groups managed, and 405 canonical runs (including 274 verified PSI-69 FLEX runs). The canonical graph remains 3,831 entities and 24,014 triples with SHACL conformance. No ontology concepts were added; FLEX-2 ranges, smoke/soot measures, and burning-rate units remain unresolved rather than guessed.

Evaluation is now frozen at 30 epistemic cases, 50 retrieval questions, and 15 semantic-resolution cases. Current FTS/BM25 source Recall@1/3/5/10 is 0.6250/0.8500/0.8500/0.9000 with MRR 0.7226; current structured status correctness is 0.8000 on 10 relevant deterministic cases. No vector retrieval or DIRECT semantics changed.

The live TypeSafe benchmark executed with `jev-latest`, returned actual model `jev-1.13.0`, and made 31 calls across 30 frozen epistemic cases. Jev triage F1 was 0.8889 (FPR 0.0476), while epistemic macro F1 was 0.5733 versus the deterministic rule baseline 0.6576. `JEV_DECISION = ADOPT_FOR_SPECIFIC_TASKS`: optional advisory rhetorical triage/review prioritization only, never claim publication or deterministic retrieval. Nemotron remains candidate-only span extractor. Review burden is unchanged at 0 pending (2 approved, 20 rejected historical audit records).
