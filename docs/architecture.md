# Architecture

Natural language is converted to a validated `QueryIntent`; application code deterministically builds SPARQL. Runs are context containers, preventing values from separate experiments from being combined. Graph filtering determines Direct, Related, or No Direct Evidence, then evidence IDs restrict SQLite FTS retrieval. Claims are structured and evidence-validated before rendering. OpenAI is an optional adapter only; no-key mode is fully retrieval-capable.

Phase 1 adds an independent operational ingestion layer: source adapter → append-only raw artifact manifest → deterministic structured ETL or document segmentation → candidate record → validation/review → incremental canonical publication. Operational batch IDs, checksums, caches, and review states remain in SQLite rather than RDF. Only accepted, evidence-resolvable canonical records enter the graph.
