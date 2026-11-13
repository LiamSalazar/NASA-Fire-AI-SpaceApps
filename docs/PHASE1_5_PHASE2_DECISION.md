# Phase 2 decision gate

Corpus scale is sufficient for meaningful retrieval evaluation: 405 structured runs, 275 managed upstream NTRS documents, 6,054 FTS passages, 50 frozen retrieval questions, and fixed lexical/KG baseline measurements. The FTS baseline to beat is Recall@1/3/5/10 = 0.6250/0.8500/0.8500/0.9000 and MRR 0.7226. The deterministic KG baseline must preserve DIRECT 1.0000 and RELATED 1.0000 correctness on its supported cases; Phase 2 must not improve a metric by weakening canonical constraints.

The ontology covers generic materials, conditions, measurements, and runs sufficiently for semantic-retrieval evaluation, but FLEX-2 ranges, smoke/soot measures, and burning-rate units remain deliberately unresolved. The 15-case semantic-resolution seed is frozen; later embeddings must measure Top-1/Top-k on unambiguous terms and preserve marked ambiguity/confusable separations.

Nemotron remains the candidate-only open-text extractor. Deterministic validation, evidence IDs, ranges/units, DIRECT/RELATED semantics, FTS, and review routing remain deterministic. Live Jev `jev-1.13.0` is **ADOPT_FOR_SPECIFIC_TASKS**: optional advisory rhetorical triage/review prioritization only. Its triage F1 was 0.8889 with FPR 0.0476, but it had a false negative and its epistemic macro F1 (0.5733) was below the rule baseline (0.6576). It must not discard evidence, determine truth/DIRECT, calculate, mutate ontology, or write the KG.

`READY_FOR_PHASE_2 = YES`. The mandatory live Jev benchmark executed; an evidence-based narrow decision exists; corpus integrity, frozen gold, retrieval baselines, SHACL, tests, and Ruff remain valid.
