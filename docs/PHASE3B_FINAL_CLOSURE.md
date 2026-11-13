# Phase 3B final closure

Phase 3B established a generic V2 query representation, persistent non-authoritative
semantic staging, a source-independent profiler/resolver, an isolated blind-holdout
evaluation path, and a parity-tested V2 compatibility retrieval adapter. The original
invalid FLEX/PSI-99 holdout selection is retained as historical invalidation; the
corrected holdouts were frozen before their first-pass content processing.

The principal success is safe extensibility: four unseen PSI-142 column semantics were
preserved with provenance as `UNKNOWN`, with zero false canonicalizations and zero
staging-to-DIRECT leaks. The V2 schema raises standalone contract coverage from 0.8298
to 1.0000, and its compatibility execution preserves V1 DIRECT, RELATED, and evidence
eligibility on the 39 scored cases.

The phase does **not** enable V2 by default. Existing PSI/FLEX semantic mappings remain
legacy source coupling, and V2 has not yet replaced them with an ontology-backed generic
KG/SPARQL execution layer. Accordingly the decisions are ADOPT for QueryIntentV2,
generic ingestion, and staging; REVISE for generic retrieval; KEEP_EXPERIMENTAL for the
default path; and `READY_FOR_PHASE_4 = NO`.

No Phase 4 work was started.
