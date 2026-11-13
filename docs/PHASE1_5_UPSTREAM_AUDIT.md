# Phase 1.5 upstream audit

Audited `Krypton-N/NASA-SPACE-APPS` at a pinned local shallow clone. It contains 24 PSI investigation inventories, 20 CSV experimental tables, 276 NTRS text files/catalog records, 138 Task Book rows, standards, and a dashboard/mechanism layer.

Safe reuse: PSI CSV tables and `files_manifest.csv` (SAFE_RAW_SOURCE/SAFE_MANIFEST), PSI index/NTRS catalog/Task Book CSV (SAFE_METADATA). The legacy ZIP range reader is a reusable acquisition strategy only after PSI endpoint verification; it was not executed here. Dashboard JSON and Cantera mechanisms are DERIVED_NOT_CANONICAL/OUT_OF_SCOPE. No frontend, simulation, or dashboard-derived values were imported.

Eleven selected upstream artifacts were copied into our immutable managed raw area with SHA256 provenance: eight PSI tables/manifests plus PSI/NTRS/Task Book catalogs. The managed import is self-contained.
