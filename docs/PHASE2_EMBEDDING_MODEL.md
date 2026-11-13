# Phase 2 embedding model

Official NVIDIA documentation was verified for `nvidia/nemotron-3-embed-1b`: `POST https://integrate.api.nvidia.com/v1/embeddings`, required `input_type` of `query` or `passage`, 2,048 dimensions, and a 4,096-token input limit. The provider uses `truncate=NONE`, bounded retries for transient failures, and separate query/passage cache keys.

Live execution used the verified model and returned 2,048-dimensional vectors. The API did not return cost/usage metadata. A 4,170-token passage response exposed the hard model limit; rather than truncating evidence, the indexer deterministically split long embedding inputs and averaged sub-vectors while retaining the complete original evidence passage for provenance/citation.
