# Scientific engine dashboard handoff

## Current RC14 assets and API (2026-11-12)

The API/CLI default is `data/snapshots/hackathon-20261112-scientific-rc14`; snapshot ID `dc3b092ab7a455286f63d3d26c781b040106d2a2027f043609b1a15420888241`. Actual source files, RDF, evidence registry and 1,371 persistent documentary vectors are supplied in the ordered RC14 archive parts. Follow [the asset restoration commands](../artifacts/releases/README.md) and use the matching checkout. The package SHA-256 is `9435b556717046de7f1f66a2e6b0803515de6428b7dee88fa83db0f52a84b17c`. Local credentials and the separately provisioned NLI model are excluded.

All nineteen original tables are mapped. The nine formerly documentary tables contribute 678 source rows with their scientifically defensible record/session/configuration scopes; source records are not automatically unique physical runs. RDF contains 400,177 triples and 23,636 entities, with 3,074 resolvable graph evidence identifiers. Original-cell validation covers 17,774 field/value links, and documentary validation covers 464 original JSON pointers. Curated quotations and term definitions retain exact original evidence; publication metadata remains distinct from inspected publication content.

Isolated restoration and real HTTP checks are recorded in `artifacts/scientific_engine_execution_20261109/restored_http_rc14.json` and `auxiliary_restored_http_rc14.json`. They include original record fields, graph navigation, instrument attributes, original Tad field → printed NASA nomenclature, explicit documentary investigation scope, and missing/incompatible asset responses. The keyless restoration test intentionally reports partial scientific mode. Vector file integrity was verified separately; live conversational acceptance must be assessed with configured generation and local verification.

Use `/api/v1/readiness` to display channel availability and `scientific_mode`; `/api/v1/health` establishes process liveness only. Preserve DIRECT, RELATED, DOCUMENTARY and DISCOVERY distinctions. The conversational acceptance evaluation is still running; a deployable asset package does not establish the 85% answer coverage/usefulness gates. The sections below retain earlier checkpoint history and the API contract.

## Historical expanded PSI checkpoint (2026-11-09)

At this historical checkpoint, the API defaulted to `data/snapshots/hackathon-20261109-v15`. The former build command was
`uv run python scripts/search_science.py build --snapshot data/snapshots/hackathon-20261109-v15`
before starting the server, then run `verify` with the same `--snapshot` path.
The snapshot has 19 original PSI tables and indexes the team's processed family
rows as provisional DISCOVERY evidence. An original table row remains source
evidence; a team-processed row is never a verified NASA measurement. Distinguish
them by `depth` (`A`, `B`, `C`, `P`) and source type. `P` means provisional
team-processed discovery. Render its QC flags and source-line claim, and avoid
displaying it as an experimental result. See
`SCIENTIFIC_ENGINE_INTEGRATION_20261109.md` and its coverage receipt for the
complete campaign matrix and current NO-GO status. The existing source and
evidence routes continue to resolve original records. The vector channel is
not provisioned for v15.

## Stabilization pilot (2026-11-09)

`NASA_SCIENTIFIC_LLM_PROVIDER=nvidia` remains the default. Set it to
`anthropic` with `ANTHROPIC_API_KEY` and optional
`ANTHROPIC_SONNET_MODEL=claude-sonnet-5-5` to use Sonnet for the same planning,
explanation and organization contract. The backend still selects citations and
verifies claims. The selected provider requires its own server-side key; the
credential-free excerpt/search path remains available. Never put either key in
dashboard requests. The four-question paired pilot did not establish a reason
to change the default; see [the stabilization assessment](SCIENTIFIC_ENGINE_STABILIZATION.md).

For controlled Sonnet evaluations only, set `NASA_SONNET_EVAL_ENABLED=1`.
`NASA_SONNET_EVAL_USD_CAP` and `NASA_SONNET_EVAL_CALL_CAP` are independently
capped at USD 15 and 40 paid attempts. The defaults for
`NASA_SONNET_EVAL_MAX_INPUT_TOKENS` and `NASA_SONNET_EVAL_MAX_OUTPUT_TOKENS`
are 50,000 and 10,000; the pilot used a 150,000 input ceiling to accommodate
the existing evidence package. The preflight input estimate conservatively
uses serialized UTF-8 bytes plus protocol overhead as a token upper bound.
Content-addressed responses are private under
`data/index/sonnet_evaluation/` and are reused for identical contracts.

Release decision and measured limits: [release report](SCIENTIFIC_ENGINE_RELEASE.md).
Use the existing `scientific-chat-v1` API; no dashboard changes are included.

## Provenance correction (2026-11-08)

Nemotron's explanation contract now accepts segments with only `text`; optional
`support_ids` are untrusted locator hints. The server checks propositions against
registered evidence and constructs citation numbers from resolved evidence records.
An organizer can reorder verified prose but cannot remove it without the backend
restoring it. The transport schema and citation endpoint are unchanged.

The backend writes a private, 30-day operational claim ledger under
`data/index/claim_ledger/` (override with `NASA_CLAIM_LEDGER_DIR`). Each receipt
links the turn and response to retrieved, exposed, matched, verified and cited
evidence IDs, including rejected proposals and repairs. The receipts contain
conversation text and are for operators, not browser clients. Restrict filesystem
access accordingly. The ledger is separate from immutable RDF and evidence
snapshot data. `trace_id` identifies the receipt. A citation's resolvable identity
is distinct from scientific support of its `claim_text`.

The scientific engine remains **NOT YET ACCEPTED** for dashboard release; see the
latest release assessment for observed omissions and false rejections. The API is
available for interface integration tests with that status visible to operators.

## Start and provision

Run from the `NASA_hackathon` worktree:

```bash
uv sync --locked
uv run python scripts/search_science.py verify
uv run python scripts/provision_semantic_verifier.py --output /operator/models/nasa-nli
export NASA_NLI_DIRECTORY=/operator/models/nasa-nli
export NASA_SNAPSHOT=data/snapshots/hackathon-20261112-scientific-rc14
export NASA_VECTOR_DIRECTORY=data/index/hackathon-20261112-scientific-rc14-vectors
export NASA_VECTOR_REQUIRED=1
export NASA_CORS_ORIGINS=http://localhost:5173
uv run uvicorn nasa_fire_ai.api:app --app-dir src --host 127.0.0.1 --port 8000 --workers 1
```

Restore the pinned RC14 archive parts and original inputs using the asset instructions linked above. `verify` checks both source and snapshot
hashes. To reproduce an absent snapshot from the preserved bounded inputs, run
`uv run python scripts/search_science.py build`. Existing different snapshots
must not be overwritten; build in a new directory and set `NASA_SNAPSHOT`.
The acquisition manifest and bounded acquisition instructions are in
[HACKATHON_ENGINE.md](HACKATHON_ENGINE.md). Do not run a bulk corpus acquisition
for dashboard installation. The backend does not download models during requests.

Set `NVIDIA_API_KEY` on the server for natural-language Nemotron explanations.
Optional `NVIDIA_BASE_URL` and `NVIDIA_PHASE3_MODEL` retain the configured NVIDIA
endpoint/model. No provider secrets belong in browser requests. The verifier
provisioner pins its repository revision; the verifier threshold remains 0.92.
`uv.lock` pins dependencies. No new model or dependency was added for this round.

Without credentials, retrieval, comparisons, scenarios, citations and exploration
operate locally; chat uses labelled exact excerpts or source listings. Without
the verifier, free paraphrases cannot pass verification. `NASA_SNAPSHOT` can point
to the operator's verified snapshot. Invalid or missing evidence returns 503 on
scientific operations. Health reports process operation, not provider health.

## Chat and sessions

```http
POST /api/v1/chat
Content-Type: application/json

{"message":"What does the FLEX report say its cameras measure?","detail":"standard","max_queries":3,"evidence_limit":12,"max_output_tokens":4000}
```

The response includes `schema_version`, `conversation_id`, `message_id`, `answer`,
`citations`, `evidence_groups`, `comparison`, `additional_candidates`,
`discovery_suggestions`, `retrieval`, `limitations`, `provider_status`,
`generation_status`, `verification_status`, `answer_completeness`,
`coverage_summary`, `trace_id`, and `snapshot_id`. Render `answer` with its `[1]`
markers and resolve those numbers against `citations[].number`.
A reproducible actual English request/response pair is included in
`artifacts/scientific_engine_release_v1/dashboard-example.json`.

Omit `conversation_id` initially; send the returned UUID for each follow-up.
Optional `history` takes at most twelve `{role, content}` messages; history is
referent context, never scientific evidence. Sessions last one hour and are
process-local. Restart loses sessions; unknown/expired UUIDs return 404. Use one
worker or session affinity before scaling. A topic change releases the earlier
source focus. Follow-ups can search beyond prior citations. The retained research
focus includes planned and unanswered needs even after a degraded turn.

`detail` is `concise`, `standard`, or `technical`. `max_queries` is 1–6,
`evidence_limit` 1–40, and `max_output_tokens` 256–10000. Display limits are not
retrieval recall limits. Optional `scientific_parameters` uses the existing
scenario contract; supplied simulator results remain predictions, not NASA data.

## Evidence, comparisons and continuation

| Endpoint | Contract |
| --- | --- |
| `GET /api/v1/evidence/{evidence_id}` | Original registered text, source metadata and page/table/structured location; 404 for unknown IDs |
| `GET /api/v1/sources/{source_id}` | Registered source record; external NASA link and original identity |
| `POST /api/v1/search` | `{query, limit, offset, research}`; categorized evidence, retained candidates and continuation |
| `POST /api/v1/comparisons` | `{subjects: [IDs], dimensions: [optional dimensions]}`; existing native matrix with original values, units, qualifiers and unknowns |
| `POST /api/v1/scenarios` | Existing `ScenarioInput` (`schema_version: scientific-scenario-v1`, `scenario_id`, `question`, `provenance`, constraints, optional simulator results); evidence and applicability limitations |
| `GET /api/v1/conversations/{UUID}/candidates?offset=12&limit=20` | Retained candidate `items`, `total`, `offset`, `limit`, `next_offset`; no provider call |
| `GET /api/v1/catalog`, `/api/v1/ontology` | Existing paginated catalogue/approved vocabulary views |
| `GET /api/v1/health`, `/api/v1/capabilities`, `/openapi.json` | Process state, supported capabilities and exact transport schemas |

Citations contain real source metadata, original `text`, `evidence_ids`,
`supporting_passage`, per-statement `supports` with `claim_text` and `passage`,
`conditions`, `limitations`, category, and page/structured location when available.
No server filesystem paths are exposed. Show source content as untrusted text.
A valid citation is provenance; it does not establish applicability by itself.
DIRECT, RELATED, DOCUMENTARY and DISCOVERY retain their scientific meanings.
A DISCOVERY listing or search idea carries unverified relevance.

`retrieval.continuation_url` opens the retained candidate pool. Search also exposes
its own offset continuation. Candidate caps and paging do not establish literature
exhaustiveness. No evidence detail is lost merely because it is not cited in prose.

## Status and operation

`provider_status.availability: CONFIGURED` means credentials exist, not a health
check of NVIDIA. Its `status` may be AVAILABLE, DEGRADED or UNAVAILABLE.
`response_mode` distinguishes `generated`, `source_excerpts`, `candidate_metadata`
and `unavailable`. Count only useful, source-faithful generated prose as an
explanation. `verification_status` reports rejected and repaired statements;
`answer_completeness` is model-declared, not independent scientific certification.
Coverage exposes routed needs and communicated support; terminology matches are
never reported as proof that a need is satisfied. Full selection/omission decisions
remain in server traces, outside the normal response text.

One scientific worker owns SQLite/RDF. Concurrent requests return 429 with
`Retry-After: 2`; validation errors return 422. The CORS allowlist must match the
dashboard origin. Provider timeout defaults to 120 seconds per call, zero SDK
retries; multiple calls and local verification can exceed that total time.
Public claim streaming is not implemented. Clients should allow a research turn
to complete and display provider/fallback limitations.

Operators may set `NASA_SOURCE_CHARACTERS` (60000), `NASA_REPAIR_ATTEMPTS` (1,
range 0–2), `NASA_ALIGNMENT_CHECKS` (96), `NASA_CANDIDATE_LIMIT` (200), and the
existing bounded `NASA_RESEARCH_*` settings documented in
[PHASE56_CHAT_API.md](PHASE56_CHAT_API.md). Context accounting covers serialized
evidence, not the entire model request. Changing these settings changes the
evaluated configuration and should be measured again.

## Vector provisioning correction — 2026-11-09

The current v15 runtime can now load the snapshot-bound documentary vector index.
See [the completion attempt](SCIENTIFIC_ENGINE_COMPLETION_20261109.md) for build,
transfer, integrity verification and `NASA_VECTOR_REQUIRED=1` startup commands.
Earlier statements above that v15 has no vector generation are historical.
The scientific release decision remains **NOT YET ACCEPTED**: the new live
Nemotron receipt still omits the requested diagnostic details.
