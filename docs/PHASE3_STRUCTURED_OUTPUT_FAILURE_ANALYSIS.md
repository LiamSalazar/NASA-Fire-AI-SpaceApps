# Phase 3 structured-output failure analysis

## Pre-repair live baseline

The provider authenticated and returned JSON. Failures were predominantly schema failures, not transport failures: interpreter 17/50 and synthesis 10/10 were rejected at Pydantic validation. The adapter previously collapsed these into `ProviderFailure`, losing actionable classification.

| Category | Interpreter | Synthesis | Root cause | Repair |
|---|---:|---:|---|---|
| TRANSPORT/HTTP/TIMEOUT/RATE_LIMIT | 0 observed | 0 observed | Not indicated by successful authenticated requests | Preserve distinct adapter errors. |
| NESTED_SCHEMA_MISMATCH | dominant | dominant | Model mixed strings/objects and generated nested fields incorrectly. | Minimal raw-mention and claim-plus-ID contracts. |
| WRONG_ENUM | observed | n/a | `keyword_search` was not a supported query mode. | Deterministic query-mode validation/fallback. |
| MISSING_REQUIRED_FIELD/WRONG_FIELD_TYPE | observed | observed | The prior contracts required redundant canonical/epistemic metadata. | Move canonical and epistemic reconstruction to deterministic code. |

Representative sanitized interpreter shape: a valid first mention followed by a second mention object containing unrelated top-level arrays. No credential, reasoning content, or private data is retained.

The repair does not relax evidence, provenance, DIRECT/RELATED, authority, normative, or open-question validation. It reduces the LLM contract to raw mention strings and claim text plus bundle evidence IDs.
