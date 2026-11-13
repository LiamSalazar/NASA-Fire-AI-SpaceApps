# Phase 1.5 retrieval error analysis

Observed lexical misses were predominantly `WRONG_RANKING` (four title/source cases not recovered in the top ten) rather than empty-index failures. The indexed corpus returned a result for every lexical gold query.

Structured misses were `STRUCTURED_DATA_MISSING`/current-parser-coverage issues: PSI-69 FLEX is canonical RDF but is not yet represented in the legacy `runs.json` query matcher; PMMA/suppression wording activates existing documentary safety context; and the deterministic parser has limited numeric/property coverage. These are fixed-baseline findings, not permission to weaken DIRECT or infer a mapping. The semantic seed explicitly retains airflow versus flame-spread velocity and extinction versus suppression as confusable distinctions.
