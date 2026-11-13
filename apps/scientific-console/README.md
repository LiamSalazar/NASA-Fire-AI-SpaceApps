# Flame in Freefall — Scientific Intelligence

Standalone Vite scientific research console. Run the backend from the repository root:

```bash
uv run python scripts/serve_scientific_console.py
```

Then, in this directory:

```bash
npm ci
npm run dev
```

Open http://127.0.0.1:5173. Use backend `--offline` for source consultation without credentials. `npm run build` creates the standalone build; `npm run preview` serves it locally on 4173. Tested with Node 22.22.3.

See [the complete handoff](../../docs/SCIENTIFIC_CONSOLE_HANDOFF.md) for API contracts, tests, launch options and later dashboard integration. Scientific answer acceptance remains conditional; read [the scientific checkpoint](../../docs/SCIENTIFIC_ENGINE_VALIDATION_CHECKPOINT.md).

Questions use a bounded server queue with progress, cancellation and independent source browsing. New conversation remains available during a request. Exact identifiers in Evidence resolve against the registry before conceptual search. See the handoff for the runtime ZIP restore command; do not rebuild ingestion.
