# Day-1 PSI ingestion results

Executed with the public NASA PSI API and local cache on 2026-09-29.

## Access and cache

The discovered mechanism is documented in [psi_ingestion.md](psi_ingestion.md). It retrieved public metadata, version history, a category file listing, and the PSI-selected experimental-table CSV without authentication. Raw, immutable response artifacts are under `data/raw/psi/`.

## Verified ingestion

- PSI-98 current metadata version: 4.
- PSI-98 Version 4 history: 74 files added, 85 removed, 1 updated.
- PSI-98 top-level file categories: Investigation Metadata Files, Engineering Documents, Raw Data, Science Documents, Experimental table.
- PSI-98 experimental rows ingested: 2 (`S1`, `S2`). The two non-sample pre-test camera rows are retained in raw CSV but intentionally not represented as sample runs.
- PSI-25 current metadata version: 4.
- PSI-25 Version 4 history: 694 files added, 131 removed, 0 updated.
- PSI-25 small verified sample ingested: 1 (`B1`) from the API-discovered experimental CSV. Its detailed inventory is in [psi25_data_inventory.md](psi25_data_inventory.md).

The PSI-98 records retain reported values and units: S1 has oxygen `21.5 - 21.7 %` represented as a range (0.215–0.217 fraction); S2 has `~ 21.5 %` represented as approximate (0.215 fraction). Geometry and flow units are retained and normalized: 0.37 cm/0.0037 m, 40.6 cm/0.406 m, 94 cm/0.94 m, and 20 cm/s/0.20 m/s.

## Build results

- Canonical entities: 39
- RDF triples: 303
- SHACL: conformant
- Tests: `13 passed`
- Ruff: clean

## Deterministic query demonstration

`scripts/demo_psi_queries.py` produced:

1. All SAFFIRE-I runs: `psi-98-S1`, `psi-98-S2`.
2. SIBAL Fabric runs: `psi-98-S1`, `psi-98-S2`.
3. Airflow <= 0.20 m/s: `psi-98-S1`, `psi-98-S2`.
4. S1/S2 comparison retains equal material, microgravity, and 0.20 m/s airflow.
5. Explicit differences include `Concurrent` vs `Opposed` flow direction, 420 s vs 70 s burn time, and differently reported oxygen forms (range versus approximate value).

This comparison states no cause or applicability conclusion.

## Unresolved limitations

The top-level PSI file endpoint does not expand every nested raw item. The 694 number is the official Version 4 added-file count, not a claim that this MVP downloaded them. BASS-II’s complex rows frequently contain sequences, inequalities, and free-text operational annotations; only B1 was ingested. Parsing those safely requires a separate sequence-aware model and metadata-file review.
