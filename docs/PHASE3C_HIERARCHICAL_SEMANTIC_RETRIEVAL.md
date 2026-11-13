# Hierarchical Semantic Retrieval

This is an additive Phase 3C engineering iteration. NASA raw/canonical inputs, historical gold and historical benchmark artifacts are preserved. No independent scientific adjudication is claimed. Experimental features remain default-off. QueryIntentV2 is retained; no Phase 4 work is started.

The native RDF executor now consults provenance-bearing taxonomy records in the existing SemanticGraph. `domain/semantic_taxonomy.yaml` is declarative; its approved edge list is currently empty. The acrylic mapping remains a source-backed-review proposal, with no proposed canonical material identity.

`query/hierarchy.py` reifies standard RDF statements and records subject, predicate, object, endpoint modeling, authority, review state, provenance, applicable relation scope, version and evidence IDs. Runtime validation checks the RDF statement against its metadata and resolves each taxonomy evidence ID. Invalid records cause expansion fallback; exact execution remains available. `ontology/semantic_taxonomy_shapes.ttl` supplies additive technical SHACL shapes. No new scientific predicate is introduced.

Traversal follows descendants, ancestors, or an ancestor followed by descendants. It prevents repeated nodes, limits depth to four and path/visit budget to 128, records oriented steps, reports exhausted budgets, and chooses one supported path per concept. It excludes unrelated predicates and wrong scopes. Experimental material relations are never created by traversal. Source-scoped selection restrictions remain exact.

Only reviewed class subsumption, individual-to-class membership and individual identity can satisfy a category/identity constraint. SKOS broader/exactMatch/related support discovery; they cannot establish material identity. Ancestor and sibling results remain RELATED for specific requests. Broad category DIRECT still identifies the actual member and does not imply common behavior across a family.

Neutral synthetic fixtures use FamilyA → SubfamilyA → MaterialA1/MaterialA2 and separate FamilyB. They demonstrate subtype eligibility, sibling discovery, staged-edge rejection, dynamic concepts, cycles, duplicates and two-level paths. These are development fixtures, not NASA observations or independent relevance gold.

See `artifacts/phase3c_related_taxonomy_v1.json`, `phase3c_related_traversal_paths_v1.json`, and `phase3c_related_synthetic_fixtures_v1.json`. Enable `HIERARCHICAL_SEMANTIC_RETRIEVAL_ENABLED` only for the experimental path. Implementation readiness is supported by tests; NASA material-family coverage remains unestablished.
