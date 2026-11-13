# Phase 3 query interpreter

`ProposedQueryIntent` is untrusted linguistic output. `ValidatedQueryIntent` wraps the existing `QueryIntent` and is the only contract supplied to retrieval. Validation gives exact canonical labels and approved aliases precedence over an LLM candidate, preserves unknown terms, and treats lexicon-marked `acrylic`, bare `flow`, and unqualified `velocity` as ambiguity rather than canonical identity.

Numeric text retains reported values and units in the query contract. Deterministic code validates units and normalizes only for matching. The interpreter has bounded provider failure handling and a deterministic parser/proposal fallback. Conversation context contains only validated referents, never generated answers.
