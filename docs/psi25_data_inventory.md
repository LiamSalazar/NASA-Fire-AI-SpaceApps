# PSI-25 (BASS-II) data inventory

The public metadata, file tree, version history, and experimental CSV were inspected through the PSI API. Current metadata reports Version 4. Its Version 4 history reports **694 added files**, **131 removed files**, and no modified files; the API’s compact top-level category response intentionally does not expand every raw-data item.

| Category | Publicly resolvable useful item | Use |
| --- | --- | --- |
| Experimental table | `PSI-25_Experimental table_BASS-II.csv` | Structured test rows and reported atmosphere/display values; source for the one clean B1 sample ingested. |
| Investigation Metadata Files | `PSI-25_metadata_PSI_metadata_PSI-101_BASS-II.zip` | Investigation-level package; candidate for richer provenance/metadata extraction. |
| Science Documents | `PSI-25_Science Documents_BASS-II_Test.Matrices.xlsx` | Candidate structured test planning/matrix information. |
| Science Documents | `PSI-25_Science Documents_BASS-II_ReadMe.docx` | Candidate field/data-file semantics. |
| Reports | `PSI-25_Reports_BASS-II Summary Report.pdf` | Candidate contextual documentation, not run data by itself. |
| Raw Data | `BASS_GMT50_SAMPLE_147_TEST_B1.mp4` (Version History) | Resolves to B1/sample 147 by official listing, but filename alone is not used for scientific values. |

## Small verified ingestion

The CSV includes structured B1. This MVP ingests only that row (`psi-25-B1`) because its fields are simple reported values. It preserves the original fuel-sample text, GMT, flow restrictor, fan/air displays, initial/final O2, and frame count. Complex BASS rows contain staged flow changes, annotations, inequalities, and nonnumeric values; they remain raw evidence and are not flattened into false single conditions.

## Remaining work

The top-level API listing returns category folders rather than an expanded 694-file current tree. A subsequent, separately scoped importer should use the metadata ZIP/ReadMe/Test Matrices to establish per-test field semantics and parse staged values as sequences, not scalar conditions. Video names are only linkage candidates until supported by a table/metadata row.
