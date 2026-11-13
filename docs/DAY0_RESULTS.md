# Day-0 execution results

Executed on 2026-09-29 using Python 3.12 and `uv 0.12.20`.

## Implemented and verified

- Typed Pydantic canonical records and `QueryIntent`; deterministic SPARQL builder.
- RDF/OWL v0.1 ontology and SHACL evidence/run constraints.
- SQLite evidence registry with FTS5 lexical retrieval and optional NumPy cosine utility.
- PDF extraction via PyMuPDF, provenance manifest, immutable raw-file policy, canonical chunking, and graph build.
- Direct/Related/No Direct matching with run context isolation and claim evidence validation.
- Retrieval-only Streamlit UI and a 15-question lightweight evaluation harness.

## Seed source ingestion

All five requested official NASA endpoints fetched successfully:

- NTRS 20205007829, *Spacecraft Fire Safety Needs for Exploration* (PDF).
- NTRS 20150020937, *Flammability Configuration Analysis for Spacecraft Applications* (PDF).
- NASA PSI-25, BASS-II, DOI `10.60555/4qc4-de67` (HTML application shell).
- NASA PSI-98, Saffire-I, DOI `10.60555/0t15-1z43` (HTML application shell).
- NASA-STD-6001 current standards entry (HTML application shell).

No fetches failed. The two PSI endpoints exposed no extractable experiment table in their fetched HTML shells, so no Saffire-I structured run rows were created. Their investigation identities are represented only with traceable source metadata; no conditions, results, or other scientific details were filled in.

## Counts and checks

- Sources/documents indexed: 5 / 5
- Passages: 72
- Canonical entities: 6 (two investigation identity records, one standard identity, one explicit NASA-identified question, one NASA conclusion, one guidance statement)
- RDF triples: 85
- SHACL: conformant
- Tests: `12 passed`
- Ruff: `All checks passed!`
- Evaluation: 15 questions; FTS non-empty for 14; expected source covered for 4; unsupported claims: 0.
- Optional vector indexing: skipped because `OPENAI_API_KEY` was not configured. SQLite FTS5 was built and used.

The conclusion and guidance records retain the exact extracted official-source passage plus an evidence ID. The open-question record is only present because the NASA presentation explicitly says designers may not realize the fire-safety question they need answered until a solution is needed; it is not inferred from an empty retrieval.

## Working example queries

1. `spacecraft fire safety exploration`
2. `flammability configuration`
3. `NASA STD 6001`
4. `fire safety needs`
5. `material configuration`

Use the Streamlit filter panel to exercise a structured query such as material `PMMA`, gravity `microgravity`, oxygen `< 18%`. With the current verified corpus it correctly reports **No Direct Evidence**, not an open question.

## Limitations and next step

The PSI application pages need an official data/API export or downloadable table before this slice can represent BASS-II conditions and Saffire-I rows. The OpenAI embedding adapter is intentionally not run without credentials, and synthesis remains disabled in no-key mode. The next highest-value step is to acquire official PSI experiment exports, preserve them as raw artifacts, then map each source row to an `ExperimentalRun` with page/table evidence references.
