# Scientific console integration handoff — 13 November 2026

**Flame in Freefall — Scientific Intelligence** is a standalone Vite console on `NASA_hackathon`. Its five views use the existing scientific API, evidence registry and canonical RDF graph. This release changes application orchestration and presentation; it does not rebuild ingestion, change the ontology or change scientific verification.

Scientific conversational acceptance remains **conditional**. Frozen observed results remain Recall@20 **100% on 30 required-source questions**, essential coverage **78/91 (85.71%)**, usefulness **16/21 (76.19%)**, and sampled factual precision **56/57 (98.25%)**. These finite, agent-reviewed results do not guarantee universal correctness. The unchanged [scientific checkpoint](SCIENTIFIC_ENGINE_VALIDATION_CHECKPOINT.md) preserves failures, denominators and evaluation receipts. No new scientific acceptance campaign or provider generation was run for this product finalization.

## Install and restore

Prerequisites: Git, Python 3.12+, [uv](https://docs.astral.sh/uv/), Node 22.22.3 and npm. Obtain `NASA_FIRE_AI_RUNTIME_ASSETS.zip` and its SHA-256 privately from the release owner. The archive's `RELEASE_METADATA.json` identifies the exact release commit. From a shell with those files available:

```bash
git clone --branch NASA_hackathon https://github.com/LiamSalazar/NASA.git NASA_FIRE_AI
cd NASA_FIRE_AI
RELEASE_COMMIT=$(python3 -c 'import json,zipfile; print(json.loads(zipfile.ZipFile("/path/NASA_FIRE_AI_RUNTIME_ASSETS.zip").read("RELEASE_METADATA.json"))["git_commit"])')
git checkout "$RELEASE_COMMIT"
uv sync --frozen
uv run python scripts/runtime_assets.py restore \
  --archive /path/NASA_FIRE_AI_RUNTIME_ASSETS.zip --sha256 THE_DELIVERED_ZIP_SHA256
uv run python scripts/serve_scientific_console.py --offline
```

In a second terminal, from the same checkout:

```bash
cd apps/scientific-console
npm ci
npm run dev
```

Open **http://127.0.0.1:5173**. API: **http://127.0.0.1:8765/api/v1**. The Vite dev and preview servers proxy `/api` to loopback 8765. `npm run build` produces `dist`; `npm run preview` serves it on 4173. To select a different API, pass `{apiBase}` to the mount function or configure the public `VITE_API_BASE` URL; never put credentials in a Vite variable.

The ZIP contains the exact RC14 `evidence.sqlite`, `graph.ttl` and manifest, compatible vector generation and pinned full-precision local NLI model. All required original scientific sources and auxiliary inputs currently exist in Git; their relative paths, sizes and hashes are recorded as `required_git_files` rather than duplicated in the ZIP. Restoration verifies the Git commit, all archive checksums, original inputs, database integrity, snapshot and vector/corpus compatibility and model checksums. It refuses different existing files and never overwrites raw data. No ontology reconstruction or ingestion is required.

Snapshot: `data/snapshots/hackathon-20261112-scientific-rc14`, version `hackathon-corpus-v22`, ID `dc3b092ab7a455286f63d3d26c781b040106d2a2027f043609b1a15420888241`. Vectors: `data/index/hackathon-20261112-scientific-rc14-vectors`, generation `78bd27e9dddb43ca97957f0c8a556d22`. NLI: `onnx-community/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7-ONNX`, revision `cdc8277b4682665e2f2e87cd83da7da07b153d75`. [Model declaration and license notices](model_licenses/nli-model-card.md) are included. Independent provisioning remains available:

```bash
uv run python scripts/provision_semantic_verifier.py --output data/index/models/nasa-nli
```

For full configured operation, stop the offline server, create a private backend `.env` containing `NVIDIA_API_KEY`, and run:

```bash
NASA_SCIENTIFIC_LLM_PROVIDER=nvidia uv run python scripts/serve_scientific_console.py
```

The launcher loads the installed local verifier automatically. Optional server variables are `NASA_SNAPSHOT`, `NASA_VECTOR_DIRECTORY`, `NASA_NLI_DIRECTORY`, `NASA_PROVIDER_TIMEOUT_SECONDS` and the existing provider settings. The existing NVIDIA default and Sonnet spending brake remain intact. `--offline` disables remote generation, embeddings and NLI while preserving actual lexical search, records, comparisons, graph navigation and extractive answers. Provider service availability requires private credentials and is not certified by asset restoration. Optional `--diagnostics NEW_DIRECTORY` writes private receipts; never publish that directory.

## Concurrency and cancellation

Two independently owned, single-thread lanes load their own read-only RDF/SQLite/search resources. The read lane serves inventories, filters, evidence, exact identity lookup, graph routes and structured comparisons. The conversation lane owns mutable sessions, provider state and the single local NLI resource. One conversation executes at a time; up to **eight active plus queued questions** are accepted. Excess conversation submissions return a clear 503 capacity response. Up to 16 read requests are admitted; read overload returns 503 rather than an unbounded executor queue. An offline warm-route probe during active chat measured catalog 42 ms, material filtering 39 ms, records 289 ms, evidence 2.5 ms, exact lookup 264 ms, graph navigation 231 ms and comparison 32 ms. Queued cancellation took 1 ms; active cancellation released its slot in 103 ms in that probe. These are finite local orchestration measurements, not provider/NLI latency guarantees. Cold lane initialization loads the immutable assets once; subsequent operations reuse them. Do not launch multiple Uvicorn processes: sessions and operations are process-local.

Use `POST /chat/operations` with the existing `ChatRequest`. The 202 response supplies an operation UUID. Poll `GET /chat/operations/{uuid}` for status, stage, queue position, queue seconds, execution seconds and the completed result. Lifecycle: pending → queued → running → completed/failed; cancellation may enter cancellation_requested before canceled. Results and operation history are bounded to 64 entries and expire after one hour on subsequent submission. Conversation sessions also retain their existing bounded one-hour lifetime.

`POST /chat/operations/{uuid}/cancel` is idempotent. Queued work cancels immediately. Active work checks cancellation before/after retrieval, each provider call, verifier calls, verification statements, context assembly and session publication. The current synchronous HTTP/provider or native inference call is **not force-killed**; it retains its worker until it returns or times out. During that interval status remains cancellation_requested. Cancellation bypasses scientific fallback and does not commit an unfinished turn. Provider timeout remains configurable (default 120 seconds). New questions can queue and source browsing remains available during cancellation. The compatibility `POST /chat` also uses the bounded conversation scheduler and requests cancellation on detected disconnect. There is no streaming.

The frontend issues independent requests, cancels obsolete view/subview requests and checks response versions. Conversation turns remain ordered. Cancel and New conversation detach abandoned responses, so an old result cannot overwrite the current session. New conversation stays available during a running question. Ordinary view navigation preserves the current chat. Previous completed context remains available after cancellation in the same conversation; New conversation intentionally clears it. Browser session storage retains up to ten messages. The server must receive the cancel request for cancellation to take effect.

## API and scientific navigation

All routes below are relative to `/api/v1`. See `/docs` on the local API for the current OpenAPI contract.

| Endpoint | Purpose |
| --- | --- |
| `GET /research/overview` | Actual facets, registered relations and property inventory |
| `GET /research/investigations` | Combined filters, query, offset and bounded limit |
| `GET /research/investigations/{id}` | Source-backed descriptions, feature inventory and shared-entity candidates |
| `GET /research/entities/{id}` / `…/neighbors` | Exact entity details and bounded directed RDF relationships; optional registered relation filter |
| `GET /resolve?query=…` | Exact source/NASA ID, evidence ID, graph ID or printed record identifier; preserves all matches; unknown identifier gets no semantic substitute |
| `GET /records?investigation=…&identifier=…` | Source-scoped original records, original headers, values, units, roles and evidence; paginated |
| `POST /comparisons` | Actual source-record subjects and approved dimensions; MATCH, DIFFER, UNKNOWN, CONFLICT and NOT_COMPARABLE |
| `POST /research/investigation-comparison` | Shared registered entities and source inventories; does not infer experimental equivalence |
| `GET /ontology` / `POST /ontology/navigate` | Approved vocabulary and bounded typed routes |
| `POST /search` | Real hybrid conceptual retrieval, preserving DIRECT, RELATED, DOCUMENTARY and DISCOVERY |
| `GET /catalog`, `/sources/{id}`, `/evidence/{id}` | Registered originals, passages, source cells and locations |
| `POST /chat/operations`, `GET /chat/operations/{id}`, `POST …/cancel` | Bounded question lifecycle |
| `POST /chat`, `GET /conversations/{id}/candidates` | Compatibility conversation and bounded candidate continuation |
| `GET /health`, `/capabilities`, `/readiness` | Operational diagnostics; readiness is not scientific acceptance |

Methods in Investigations use the actual registered description with investigation disambiguation, not invented categories. Original descriptions remain in detail records. Measurement counts cover indexed measurements only; source fields, configuration alternatives and documentary findings are separate. Compare describes records using available original identifiers, materials and fields, with source row and entity identity retained separately. A property arriving from Discover can select the corresponding comparison dimension. Related candidates come from shared registered entities, not inferred equivalence. Discover can filter real edges, find investigations with a registered property, trace findings and open source evidence or Compare.

DIRECT describes evidence matching requested constraints; RELATED retains differences; DOCUMENTARY contains original descriptions, methods, objectives and attributed findings; DISCOVERY is a candidate requiring relevance assessment. Exact identity is not a claim-support classification. Citation resolution is not proof of support. Values and original units stay intact. Source roles retain the distinction between NASA measurements, conditions, alternatives, derived fields, simulations and predictions. Graph connectivity is not causality. No direct evidence is not a NASA knowledge gap. Scientists make new scientific inferences.

## Reuse from the team's Vite application

The standalone build can be mounted in an iframe or a dedicated same-origin route backed by an `/api/v1` proxy. Direct source integration exports:

```javascript
import { mountScientificConsole } from './scientific-console/src/main.js';
const unmount = mountScientificConsole(document.querySelector('#research-console'), {
  apiBase: '/api/v1',
});
// Call unmount() when leaving the host route.
```

Install the console's package dependencies and copy its source and bundled font imports. Its CSS and hash router currently own the page: scope CSS and adapt routing before mounting beside another hash router. Keep credentials, authentication and provider access on the backend. No integration into the team's repository is performed here.

## Verify and recover

```bash
uv run pytest -q tests/test_product_operations.py tests/test_research_console_api.py tests/test_conversation_http.py
uv run python scripts/measure_console_operations.py --output /tmp/console-operations.json
cd apps/scientific-console
npm run test:unit
PLAYWRIGHT_BROWSERS_PATH=/tmp/nasa-console-browsers npx playwright install chromium
PLAYWRIGHT_BROWSERS_PATH=/tmp/nasa-console-browsers npm run test:e2e
npm run build
```

The timing probe requires an offline server. Deterministic browser tests use actual backend data; lifecycle timing tests delay real responses. They make no provider calls. Do not run `tests/live-workflows.mjs` as a regression retry; it invokes generation. Final checks passed: 85 focused backend/B8 tests, 29 additional conversation/vector/provider tests, seven final operation tests (overlapping the focused run), eight frontend unit tests, seven browser workflows, production build and Ruff. Initial startup-status and mobile-width failures were corrected; their failed engineering receipts are retained separately. No scientific scores were recomputed. New validation receipts live in `artifacts/product_finalize_20261113`; historical 3,782-pass scientific results and the original evaluation remain in `artifacts/scientific_console_release_20261112`.

For startup failure, check `/health` then `/readiness`, use server logs, confirm the exact commit and rerun the restore command. A 503 initialization error must not be treated as scientific absence. Check that ports 8765/5173 are free and Vite's proxy matches the backend. A missing provider credential permits offline consultation; missing RC14 inputs or incompatible vectors require verified restoration, not ingestion. Process restart loses in-memory operation/session IDs; start a new conversation if an ID expires. Keep at least 2 GB disk space for restoring runtime assets plus the checkout and software dependencies; do not delete historical scientific material to free space.

Remaining scientific limitations include incomplete answers, valid paraphrase false refusals, repetition and conditional conversational acceptance. Synchronous stages can delay cancellation, and long scientific answers retain the established verification latency. Historical live timings and limitations remain documented in the unchanged scientific checkpoint. Public hosting, team integration and scientific certification are outside this delivery.
