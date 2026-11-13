# Phase 3C graph relation coverage

Objective fixture: 3,808 explicit foreign keys frozen in canonical records before development. Native association coverage changed from 0/3,808 to 3,808/3,808. This tests projection completeness for those records, not scientific extraction recall across NASA documents. Final graph and original first-pass projection have separate versioned receipts.

Native SemanticGraph.explore_route validates declared relation types, evidence resolution, traversal direction, depth/budget, cycles and review states. Property hierarchy may authorize a narrower predicate; the path records the actual predicate. Class inheritance uses approved subclass edges only; exact execution remains available. Example source-backed routes: psi-98 → hasRun → usesSample → madeOf; psi-98 → hasRun → hasCondition; Saffire-IV observation → reportedBy → source publication. None establishes causality or an observation-to-conclusion support relation. A synthetic evidential-looking relation remains an association unless stronger semantics are explicitly validated.

ONTOLOGY_GRAPH_ENRICHMENT_ENABLED=false by default. Unknown relationships raise a controlled error; exact retrieval survives optional model failures. Source ontology and canonical data are unchanged.

Final correction: source descriptions without approved alias resolution remain Sample payloads and do not receive new madeOf/Material assertions. First-pass graph v1 is superseded by phase3c_knowledge_final_graph_v2.ttl; its 4,769 relations and 54,767 triples are the final projection. Earlier graph files are retained for error analysis.
