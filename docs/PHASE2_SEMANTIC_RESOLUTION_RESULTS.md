# Phase 2 semantic-resolution results

Implemented hierarchy: controlled canonical label/safe alias first; controlled ambiguity second; embedding-ranked `SEMANTIC_CANDIDATE` last. Embeddings cannot establish canonical identity or DIRECT evidence. The frozen 15-case seed and a separate local concept index are ready for Top-1/3/5 and confusable-margin evaluation.

Live evaluation used the frozen seed unchanged. Twelve unambiguous cases were evaluable against the deliberately limited 10-concept controlled index: end-to-end Top-1/3/5 = 0.3333/0.3333/0.3333. Closure decomposition found that only 4/12 expected canonical IDs (33.33%) exist in that index. On the coverage-conditioned subset, Top-1/3/5 is 1.0000/1.0000/1.0000, driven by controlled canonical/safe-alias resolution rather than an embedding identity decision.

The eight non-indexed expectations are airflow/forced-flow category IDs, flame-spread velocity, intervention-form suppression, blowoff, droplet diameter, oxygen concentration, and pressure. They are ontology/model coverage work or intentionally ambiguous terminology, not failures that Phase 2 may silently cure. The flame-spread query's top vector candidate was airflow velocity, an explicit confusable-property warning. Candidate aliases may be proposed for human review only; no semantic result becomes canonical identity automatically.

No CandidateAlias proposal was emitted in this closure (`data/eda/phase2_candidate_alias_proposals.json`): none of the unreviewed phrases had both a represented expected concept and an adequate non-confusable semantic margin. Exact safe aliases do not need a proposal, and absent concepts must not be manufactured to improve a benchmark.
