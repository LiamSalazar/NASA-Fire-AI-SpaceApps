# Phase-1 ingestion pipeline

`SourceAdapter → immutable raw artifact/manifest → deterministic segmentation or structured ETL → CandidateRecord → validation → review queue or publication → RDF/SHACL + Evidence Registry + FTS5`.

Structured files take precedence. The generic CSV adapter maps recognized measurement headers and preserves source values/units; unsupported unit conversions remain unnormalized. Ranges and approximations continue to use the existing PSI canonical path. `MeasurementObservationRecord` is numeric reported measurement; `ReportedExperimentalObservationRecord` is a qualitative NASA-reported outcome. Neither is a NASA conclusion.

Candidates need a resolvable evidence span. Unknown terminology produces `CandidateOntologyConcept`; ambiguous `acrylic` produces review-required status. Ontology Turtle is never modified by ingestion. High-risk prose types require source context and remain review-only in this Phase-1 implementation.

NVIDIA extraction is optional and configuration-gated (`LLM_EXTRACTION_ENABLED`, `NVIDIA_API_KEY`, `NVIDIA_BASE_URL`, `NVIDIA_EXTRACTION_MODEL`). No key is read into logs or committed. Without all settings, extraction is explicitly pending and deterministic ingestion proceeds.
