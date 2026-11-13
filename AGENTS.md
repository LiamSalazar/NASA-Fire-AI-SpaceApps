# NASA Fire Safety Evidence Assistant rules

This repository is an evidence assistant, not an autonomous scientist. These rules are immutable:

1. Never modify raw source data.
2. Never fabricate NASA data.
3. Preserve original values and units.
4. Every scientific assertion requires evidence.
5. Never silently create ontology vocabulary.
6. No direct evidence is not a NASA knowledge gap.
7. Related evidence is not equivalent evidence.
8. Never transform observation into recommendation unless NASA explicitly does so.
9. Never treat derived, simulated, or predicted data as a NASA observation.
10. LLM general knowledge may not fill scientific evidence gaps.
11. Scientists, not the assistant, make new scientific inferences.
12. Tests must pass before task completion.

Use `uv`; keep the system usable without an API key. Raw files under `data/raw/` are append-only immutable inputs. Domain entities belong in RDF; local paths, chunk ids, checksums, and vectors belong only in the evidence registry/index.
