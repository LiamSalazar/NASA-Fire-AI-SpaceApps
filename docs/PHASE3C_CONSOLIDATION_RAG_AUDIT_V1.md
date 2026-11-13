# Actual retrieval and hybrid pilot

Existing capabilities: SQLite FTS5 with BM25, registry metadata eligibility,
ontology entity resolution, native graph constraints and traversals, verified
context scope, passage support and existing NVIDIA embedding/vector cache components.
No replacement of lexical retrieval or the native executor was made.

The bounded pilot compares A lexical, B vector, C graph, D lexical/vector,
E lexical/graph, F lexical/vector/graph and G verified-context hybrid at final k=5.
45 stratified source units, 12 questions and two representations (text; section/title)
share a frozen corpus. Two paraphrase graph cases were NOT_RUN, explicitly recorded.
G uses contextual graph results, not a newly evaluated model reranker.
Independent Precision@5, Recall and nDCG are null: no judged relevance universe exists.
Vector result changes and cosine scores are not evidence of scientific improvement.

