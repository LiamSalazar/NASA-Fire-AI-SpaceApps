# Phase 3C scientific extraction and staging

Nemotron extraction is opt-in and proposed only. Exact source/evidence identity, supporting substring and both mentions are checked deterministically. Validation cannot approve scientific interpretation, numeric context or taxonomy. Content-addressed staging is idempotent; conflicting reuse of an existing candidate ID raises an error rather than overwriting review state.

Initial extraction accepted three span-valid proposals and rejected one mention/span mismatch. Two first-pass calls on reacquired primary-PDF passages are preserved separately. All remain pending scientific review. No LLM-proposed relation was published. Existing canonical foreign keys can be projected through existing ontology relations; unknown property mappings and unsupported evidential/causal relations remain proposals.
