# Semantic staging

`EvidenceRegistry.semantic_staging` persists candidate ID, raw label, candidate type,
source/evidence location, status, review state, and provenance. Supported noncanonical
states include `UNKNOWN`, `KNOWN_AMBIGUOUS`, `CANDIDATE_NEW_CONCEPT`,
`CANDIDATE_ALIAS`, and `CANDIDATE_RELATION`. The storage API rejects `CANONICAL`;
staging cannot mutate the ontology, become a controlled alias, acquire NASA-backed
authority, or establish DIRECT evidence.
