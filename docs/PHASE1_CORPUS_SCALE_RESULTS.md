# Phase-1 corpus-scale execution results

Executed locally on 2026-10-03. This is a conservative scale-up, not a claim that all NASA fire-safety data has been downloaded.

## Executive summary

The verified PSI-25 BASS-II experimental table was processed by the generic structured CSV pipeline: 129 rows became validated candidates and 129 stable runs were eligible for publication. The existing B1 curated record overlaps that table; canonical assembly deduplicated it by stable ID and retained the existing curated record. PSI-98 S1/S2 were retained as regression gold. A held-out NTRS PDF was segmented deterministically. NVIDIA extraction was not configured, so no LLM candidate was created or published.

## Source inventory and corpus scale

The catalog has 5 records: 4 ingested official-source entries (BASS-II/PSI-25, Saffire-I/PSI-98, NTRS 20205007829, NASA-STD-6001) and one explicit discovery-pending family group (FLEX/FLEX-2, SoFIE variants, SAME, SPICE, SLICE, Confined Combustion). No IDs were invented for the pending group.

- Raw files: 15; raw disk footprint: 7.8 MiB.
- Registry source rows/documents: 6/8. The sixth source row is the developer-supplied local handle for the already-official held-out NTRS PDF, not a new scientific source.
- FTS passages: 252.
- Newly deterministic-segmented holdout passages: 19.
- Media/raw archives: not downloaded by default (`INCLUDE_MEDIA=false`, 50 MiB limit).

## Scientific coverage

Represented areas are solid-fuel/material combustion (BASS-II), large-scale spacecraft fire and forced flow (Saffire-I), oxygen/atmosphere values, suppression/detection documentary evidence, and normative material flammability/testing evidence. Liquid-droplet combustion, recent SoFIE work, smoke/detection experiments, and the discovery-pending families were not acquired in this execution and are not claimed as corpus coverage.

## Structured experimental ingestion

- BASS-II PSI-25: 129 real table rows processed with the schema-driven adapter.
- SAFFIRE-I PSI-98: existing S1/S2 retained, including oxygen range and approximation representations.
- Canonical experimental runs after stable-ID deduplication: 131 (129 BASS-II + 2 SAFFIRE-I).
- Canonical entities/RDF triples: 926 / 5,770.
- No unrecognized unit was converted: ppm values preserve reported values and units with null normalization.

## Document extraction, review, and evidence

The holdout NTRS source was deterministically segmented. LLM extraction is `PENDING_CONFIGURATION` because no complete NVIDIA configuration was present. Thus LLM documents/candidates were not fabricated or silently accepted.

- Candidate records: 129 structured candidates.
- Validated/published-eligible: 129.
- Review-required/rejected: 0/0 for the executed table.
- Review queue: 0 pending. Unknown terms and high-risk prose remain designed to enter review, not auto-publication.
- Published scientific records resolve through Evidence Registry evidence IDs; SHACL conforms.

## Incremental and holdout evaluation

`ingest_source.py --psi-id PSI-25 --publish` first reported `published_runs: 129`. Re-running the unchanged source reported `published_runs: 0`; canonical stable-ID assembly also prevented the pre-existing B1 duplicate. The development group is PSI-25/PSI-98/NASA-STD-6001. The NTRS 20205007829 document group was held out from table-parser work: its first pass yielded 19 deterministic passages and zero candidates, with no source-specific extraction rule added.

## Validation

- `uv run pytest -q`: **35 passed**.
- `uv run ruff check .`: **All checks passed**.
- `uv run python scripts/build_graph.py`: **SHACL conformant**.

## Limitations and Phase-2 readiness

The catalog intentionally records unverified family names as pending rather than asserting IDs. NTRS, standards, and Task Book adapters are interface boundaries; only the already verified PSI public interface was executed for new structured acquisition. The optional NVIDIA adapter is configuration-gated and does not yet send documents until a schema-constrained model identifier is verified. The pipeline is ready for reviewed adapters/mappings and additional official source artifacts, without retraining.
