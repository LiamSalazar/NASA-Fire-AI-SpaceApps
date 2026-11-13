# Incremental ingestion and operation

Content-addressed append-only raw files, metadata/content/contract digests and version
records make updates repeatable. Unchanged metadata under the same extraction contract
skips download, parsing and index rebuild; `refresh` can inspect remote content explicitly.
Content changes preserve both versions; superseded sources leave active retrieval.
Publication of document, page, locator, citation and FTS records is transactional.
Malformed PDFs are quarantined before persistent source publication.
Rollback archives active publication, preserves historical citation resolution/raw files,
and restores the previous eligible version. Tests cover changed content at identical metadata.
Scientific facts are not automatically published by this document acquisition contract.

Runnable commands from the repository:

```bash
uv run python scripts/maintain_knowledge.py discover --query 'microgravity combustion'
uv run python scripts/maintain_knowledge.py dry-run --nasa-id 20260003546
uv run python scripts/maintain_knowledge.py controlled-update --nasa-id 20260003546
uv run python scripts/maintain_knowledge.py review-pending
uv run python scripts/maintain_knowledge.py validation-only
```

`--interpret` optionally proposes context with one bounded Nemotron request and staging.
Scheduling examples in ops/ are verified examples, not installed services.
Discovery does not yet automatically select scientific eligibility for bulk ingestion.

