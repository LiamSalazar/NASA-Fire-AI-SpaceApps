# Day-4 semantic coverage results

- Controlled concepts: 9; explicit aliases/abbreviations: 22.
- NASA terminology sources: PSI-98/PSI-25 metadata and experimental tables, NTRS 20205007829, NTRS 20150020937, NASA-STD-6001.
- Deliberately ambiguous: `acrylic`; unmapped unknown example: `unobtainium`.
- Gold questions: 25, covering entities, aliases, numeric constraints, comparison, safety, abstention, related evidence, ambiguity, and documentary search. The executable harness returned 24 non-empty FTS results.
- QueryIntent exact/field accuracy: 6/6 explicitly field-scored gold cases pass through parser/unit tests (alias, numeric, mode, ambiguity, unknown); remaining questions are retrieval-only gold coverage.
- DIRECT/RELATED: 3/3 exercised end-to-end cases pass (SAFFIRE direct rows, constrained SIBAL related rows, unknown-material abstention). Gold evidence Recall@k for the Saffire comparison is 2/2; citation coverage is 100% for rendered canonical/safety records; unsupported rendered claims are 0.
- Coverage: PMMA has ontology/run/documentary/safety coverage; SIBAL has ontology/run/documentary coverage; suppression has documentary/safety coverage; smoke detection has documentary mentions but no canonical run in this MVP.
- QueryIntent field behavior, direct/related handling, evidence coverage, abstention, and extractive rendering are covered by tests. No LLM judging is used.
- Current graph: 48 entities, 349 triples; SHACL conforms.
- Highest-value next step: expert review of additional aliases and gold expectations before enlarging the corpus.
