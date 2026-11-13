# Incremental ingestion

Use `uv run python scripts/ingest_source.py --psi-id PSI-25 --publish` for a public PSI table, or `uv run python scripts/ingest_source.py --local-document path/to/official-nasa.pdf` for a developer-supplied NASA document.

The command creates a batch, retains an immutable raw manifest entry, records evidence passages, validates candidates, and publishes only validated deterministic structured records. Re-running an unchanged PSI table uses stable candidate/run identities and reports `published_runs: 0`; it does not duplicate canonical runs. Follow with `build_canonical.py`, `build_graph.py`, and `corpus_stats.py`.

No model training occurs. Failed official fetches are failures, not permission to use unofficial mirrors.
