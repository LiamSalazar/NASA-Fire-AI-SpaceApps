# Phase 3C semantic enrichment implementation

Reuses QueryIntentV2, SemanticRegistry, native projection/executor, Evidence Registry, NVIDIA client and Jev adapter. `SOURCE_KNOWLEDGE_ENRICHMENT_ENABLED=false` independently gates additions inside existing ontology enrichment; both flags must be true. Default exact V2 and V1 remain available. No embeddings or second retrieval engine.

Typed source accessors resolve original canonical kinds, validate units and preserve original records plus evidence. They do not establish observed measurements. Numeric failures remain staged. Exact atomic Fuel-cell matches resolve existing source-backed material identities. Original specimen IDs and descriptions remain distinct. Idempotence covers graph triples, executable counts and staging. Alias lookup recognizes source labels with spaces. Source-span validation preserves source offsets through whitespace/NFC only. PDF table cells retain bounding boxes and physical indexes; scientific roles remain unapproved.

Changes: `ingestion/enrichment.py`, `knowledge.py`, `source_spans.py`, `semantic.py`, `pdf.py`, `normalization/units.py`, `query/native_interpreter.py`, `evidence_selection.py`, `native.py`, `controlled_reasoning.py`, registry/configuration and ontology shapes. Existing adapters and shared dotenv loader are reused unchanged. API failure never publishes a fact.

Artifact index: all `artifacts/phase3c_enrichment_*_v1.json/jsonl`, fresh native suites in `phase3c_enrichment_native_checks_v1/v2`. Final measured receipts: summary, benchmark_summary, live_summary, parity_reconciliation, review_packet, integrity and decisions. Historical files remain inputs.

Representative real source/query examples: `artifacts/phase3c_enrichment_scientific_examples_v1.json`. Component failures: `artifacts/phase3c_enrichment_errors_v1.json`. Final expanded artifact index: `artifacts/phase3c_enrichment_artifact_index_v2.json`.
