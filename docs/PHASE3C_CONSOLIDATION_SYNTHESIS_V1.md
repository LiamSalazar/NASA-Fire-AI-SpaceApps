# Integrated architecture and synthesis

The public Phase3AssistantService still uses QueryIntentV2, SemanticRegistry,
project_legacy and the native executor. EvidenceBundle remains the common boundary.
No second graph, QueryIntentV3 or new scientific vocabulary was introduced.
The existing context layer verifies scoped source statements without rewriting run facts.
FTS5/BM25 remains enabled; existing vector components were evaluated separately.

`SCIENTIFIC_SYNTHESIS_ENABLED=true` enables bounded statement selection and compact rendering.
`SCIENTIFIC_CONTEXT_RESOLUTION_ENABLED=true` enables verified applicability.
`NEMOTRON_SCIENTIFIC_SELECTION_ENABLED=true` enables optional bounded model selection;
`NEMOTRON_SCIENTIFIC_SYNTHESIS_ENABLED=true` additionally requests proposed claim text.
All new model stages are experimental, default off, with deterministic fallback.
V1 and the previous native renderer remain available.

Core implementation: services/scientific_synthesis.py, services/phase3.py,
services/native.py, llm/scientific_selection.py, models/GroundedClaim.
Sources, exact support spans, effective conditions, scientific entities, epistemic
types, scope limits and membership paths stay inspectable in the complete bundle.

