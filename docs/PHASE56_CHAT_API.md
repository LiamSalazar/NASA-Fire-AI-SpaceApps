# Scientific chat and API v1

Latest stabilization: [release decision](SCIENTIFIC_ENGINE_RELEASE.md) and
[dashboard handoff](SCIENTIFIC_ENGINE_DASHBOARD_HANDOFF.md). The scientific engine
is **not yet accepted**; transport operation is distinct from scientific answer
coverage. Needs-aware context allocation is implemented; release blockers remain.

Current implementation: `NASA_hackathon`. The service reuses the immutable
snapshot, native RDF executor, semantic registry, EvidenceRegistry, FTS5,
comparison, scenario analysis, investigation loop and independent verification.
See [the refinement report](PHASE56_RECALL_REPORT.md) for measurements and limits.
The historical bilingual delivery is recorded in `PHASE56_REPORT.md`.

## Run

```bash
uv sync --locked
uv run python scripts/search_science.py verify
uv run python scripts/provision_semantic_verifier.py --output /operator/models/nasa-nli
export NASA_NLI_DIRECTORY=/operator/models/nasa-nli
export NASA_CORS_ORIGINS=http://localhost:5173
uv run uvicorn nasa_fire_ai.api:app --app-dir src --host 127.0.0.1 --port 8000 --limit-concurrency 32
```

Use backend environment configuration for `NVIDIA_API_KEY`, `NVIDIA_BASE_URL`
and `NVIDIA_PHASE3_MODEL`. Never send credentials from the browser.
`NASA_SNAPSHOT` defaults to `data/snapshots/hackathon-20261105-v9`.
Requests do not download models or modify source files, RDF or the snapshot.

The pinned float32 ONNX NLI model is retained for English scientific verification
at threshold 0.92. Its multilingual training does not require translation.
Provisioning downloads only its configuration, tokenizer and weights. There is
no language detector, Argos translator, back-translation, CTranslate2 or BPE
translation package. Old operator translation directories are unused and are
not deleted. No new local model was introduced.

All planning, query expansion, explanations, messages and suggestions use
English. Original NASA wording and units remain unchanged. No language-specific
retrieval branches exist.

Without an API key, local search, comparison, scenarios, evidence lookup and
candidate exploration remain usable. Chat can show exact documentary excerpts
with citations and `response_mode: source_excerpts`; it never attributes those
to Nemotron. Without an NLI verifier, freely generated paraphrases remain
unverified and cannot bypass the source checks. A missing or invalid snapshot
causes scientific operations to return 503.

## Chat contract

```http
POST /api/v1/chat
Content-Type: application/json

{
  "message": "Which instruments were used in those studies?",
  "conversation_id": "UUID from the preceding turn",
  "detail": "standard",
  "max_queries": 3,
  "evidence_limit": 12,
  "max_output_tokens": 4000
}
```

Omit `conversation_id` on the first turn. Optional `history` contains up to 12
`{role: user|assistant, content: string}` messages. `scientific_parameters`
retains the existing ScenarioInput contract; simulator results never become
NASA observations. The existing `scientific-chat-v1` fields remain available.

| Field | Meaning |
| --- | --- |
| `answer` | English explanation, exact excerpts or qualified exploratory source descriptions, with compact `[1]` citations |
| `conversation_id`, `message_id` | Session and turn identity |
| `citations` | Real source title/URL/DOI, evidence IDs, original passages, page/table location, conditions and limitations |
| `evidence_groups` | DIRECT, RELATED, DOCUMENTARY and DISCOVERY results |
| `comparison` | Native comparison matrix when applicable |
| `discovery_suggestions` | Model-proposed, unverified search directions; no invented citations |
| `additional_candidates` | A bounded preview of candidates beyond cited passage IDs |
| `retrieval` | Retained count, support inventory size, context omissions, summarized evidence count, query receipts and continuation URL |
| `provider_status` | Provider availability, verifier availability and response mode |
| `limitations`, `trace_id`, `snapshot_id` | Scope, operational trace and pinned corpus identity |

`retrieval.retrieved` counts the retained conversation pool, including accessible
prior candidates when research continues. It is not the number of paragraphs
summarized or the total NASA literature. A candidate is not a supported claim.
`examined_supports` counts context anchors offered for explanation, not scientific
adjudications. Query metrics separately record candidate routes, deduplication,
truncation, classification and returned-page counts.

```http
GET /api/v1/conversations/{conversation_id}/candidates?offset=12&limit=20
```

Returns `items`, `total`, `offset`, `limit`, `next_offset`. This reads retained
context without provider calls. Sessions expire after one hour; unknown sessions
return 404. A topic change clears the prior candidate scope. Continuations retain
prior candidates as DISCOVERY because old applicability cannot establish new
question constraints. History is bounded to 1,000 candidates by default; omissions
are disclosed. Evidence IDs remain available through evidence lookup.

## Retrieval and verification

Native graph selection keeps the original question's constraints. A separate
broad passage pool combines lexical searches, focused content terms, existing
approved aliases, controlled lexicon terminology and word forms actually present
in the corpus. These expansions propose search locations only. Reciprocal-rank
fusion avoids comparing incompatible scores; source round-robin and original
page deduplication prevent long or multiply registered documents monopolizing
results. Strict DIRECT/RELATED checks follow retrieval. Unverified relationships
remain DISCOVERY; documentary source content is not experimental equivalence.

The optional `semantic_candidates` service adapter can contribute existing
`LocalVectorIndex` results. No vector index is provisioned by default, and no
semantic recall improvement is claimed without one.

The existing investigation loop replans local searches and graph paths using
coverage receipts. Conversation planning can propose multiple meanings and
queries. When budget remains, a post-retrieval Nemotron review can propose
additional searches from retrieved context. A search yielding no new candidates
stops further proposals. Every expansion is bounded and recorded. Source focus
guides follow-ups while unrestricted queries remain possible.

| Setting | Default |
| --- | --- |
| `NASA_CANDIDATE_LIMIT` | 200 passage candidates, independent of display page size |
| `NASA_RESEARCH_ROUNDS` | 3 |
| `NASA_RESEARCH_ACTIONS` | 6 |
| `NASA_RESEARCH_CANDIDATES` | 32 per investigation action |
| `NASA_RESEARCH_SECONDS` | 15; checked between local actions |
| `NASA_PROVIDER_TIMEOUT_SECONDS` | 120 per provider call, zero SDK retries |

Search pages use a stable bounded pool: `POST /api/v1/search` still accepts
`query`, `limit`, `offset`, `research`. Additive `candidates` and `continuation`
fields expose retained candidates, category totals and next offsets. A pool cap
is not proof that no further literature exists.

Verification preserves exact evidence identity, original spans, values and units,
subject attribution, modality, comparison dimensions, causal restraint and
source applicability. Rejected statements can be repaired; accepted statements
survive. The NLI threshold was not lowered. Exact complete documentary statements
have a deterministic identity path; it cannot authorize a modified paraphrase,
DISCOVERY scientific claim or experimental applicability.

For exploratory bibliography, Nemotron selects actual candidate IDs through a
separate `exploratory_source_ids` channel. The server renders registry titles
with explicit unverified relevance and citations to the real retrieved source.
It does not accept model-written scientific relationships through that channel.
Exploratory titles are deduplicated and limited to three sources in the main
answer by default; additional candidates remain accessible. Exact documentary
excerpts can accompany these listings when no scientific prose is accepted.
Source authenticity and relevance remain separate.

## Other routes and deployment

Existing `/api/v1/comparisons`, `/scenarios`, `/catalog`, `/ontology`,
`/evidence/{id}`, `/sources/{id}`, `/health` and `/capabilities` are preserved.
The capabilities language list is now `["en"]`. OpenAPI is in
`PHASE56_OPENAPI.json` and served at `/openapi.json`.

One bounded worker owns RDF/SQLite. Concurrent scientific requests receive 429
with Retry-After. Health remains independent. Sessions are process-local; use
one worker or provide session affinity/shared storage before scaling. CORS is an
explicit allowlist. Scientific inputs are capped, paths are not exposed, and
source content must be displayed as untrusted text by the frontend. The dashboard
and its repository were not modified. Public claim streaming is not implemented.

## Reproduce checks

```bash
uv run python scripts/test_batches.py --output /tmp/nasa-tests-new
uv run python scripts/evaluate_recall.py --output /tmp/nasa-recall-new.json
uv run python scripts/evaluate_conversation.py --output /tmp/nasa-english-new.json
uv run python scripts/evaluate_semantic_adversaries.py --nli "$NASA_NLI_DIRECTORY" --output /tmp/nasa-adversaries-new.json
uv run python scripts/smoke_http_offline.py --output /tmp/nasa-http-new.json
uv run ruff check src scripts tests
```

Recall qrels are source-inspected provisional annotations, not independently
adjudicated scientific ground truth. Historical evaluations are retained. The
current default conversational evaluation is `questions_english_v2.json`.

## Conversational reliability checkpoint

The focused follow-up is documented in
[`PHASE56_CONVERSATIONAL_RELIABILITY.md`](PHASE56_CONVERSATIONAL_RELIABILITY.md).
It adds optional response objects without replacing existing chat fields:

- `generation_status`: draft outcome, explanation outcome and provider failures.
- `verification_status`: retained/rejected statements and bounded repair outcome.
- `answer_completeness`: model-declared needs and unresolved aspects; not an
  independently certified completeness score.
- `coverage_summary`: available/supplied anchors, reexamined evidence,
  communicated sources and accepted content omitted during composition.

`provider_status.availability` indicates CONFIGURED or UNAVAILABLE separately
from final response quality. Verified final prose can be AVAILABLE even when
an earlier draft contained rejected claims. Excerpt and exploratory-list
fallbacks retain their own response modes and do not count as generated prose.
Clients can continue rendering `answer` and the existing compact citations.

Operators can configure `NASA_REPAIR_ATTEMPTS` (default 1, supported 0–2),
`NASA_SOURCE_CHARACTERS` (default 60000), and `NASA_ALIGNMENT_CHECKS` (default
96). Repairs use existing provider credentials and independently verified real
source spans; zero disables model repair. The pinned verifier and fail-closed
no-key behavior are unchanged. Full structured traces stay outside normal prose.

Live evaluation commands, source-inspected targets and explicit remaining
acceptance failures are in the checkpoint report and artifact README. Do not
interpret the new status fields as proof that the whole question was answered.
