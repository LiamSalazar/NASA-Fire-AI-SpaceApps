# Embedding decision

The existing `nvidia/nemotron-3-embed-1b` provider was used, not the generative model.
Fresh inference processed 12 query, 45 text and 45 section inputs in seven bounded
requests. Only the last batch usage per embedding operation was exposed: 3,407
tokens is an available lower bound, not a complete bill. No price or recurring cost
is asserted. The v2 comparison is historical embedding replay, not fresh inference.
Vectors and checksums remain in local indexes/registry, not domain RDF.
Repeated sync changed zero vectors and did not rewrite unchanged files.
Table-header and fully context-augmented representation evaluation remains incomplete.
Global vector adoption is INCONCLUSIVE; no new recurring embedding job was installed.

Provider documentation: https://docs.api.nvidia.com/nim/reference/nvidia-nemotron-3-embed-1b-infer

