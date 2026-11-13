# NASA PSI ingestion

## Public access mechanism

The active public repository is the Angular application at `https://psi.nasa.gov/physci/repo/`. Its JavaScript uses the unauthenticated Geode service at `https://psi.nasa.gov/geode-py/ws`.

| Purpose | Method and endpoint | Response |
| --- | --- | --- |
| Investigation metadata | `GET /studies/{PSI-ID}/metadata` | JSON with `studies`, metadata comments, and current `version` |
| Version history | `GET /repo/investigations/{PSI-ID}/versions` | JSON `versions[]`, each with `added`, `removed`, and `modified` file entries |
| File/category tree | `POST /files/v2` | JSON `{files: [...]}`; request body is `folder`, `fileType: "study"`, `studyId`, `version`, `obfuscationcode` |
| Download exposed file | `GET /studies/{PSI-ID}/download?file={basename}&version={file-version}&redirect=false` | public short-lived S3 URL in text; a GET of that URL returns the file |

The endpoints used for PSI-98 and PSI-25 require no authentication. `list_files` preserves the category tree; `get_versions` exposes historical version-file arrays, including nested raw-data names that are not expanded by the top-level file tree.

## Client behavior

`nasa_fire_ai.ingestion.PSIClient` is cache-first and writes each response only when absent under `data/raw/psi/`. It has a 0.5-second minimum interval between live requests. Cached metadata, version history, file listing, and experimental CSV are the immutable raw inputs to canonical conversion.

`get_experimental_table` finds a CSV only from the API-returned `Experimental table` category; no filename or experimental value is hardcoded. If the CSV is not exposed, it raises `LookupError`. If the download endpoint cannot return a public URL, it raises an error and creates no replacement data.

## Fallback

The fallback is to retain the cached metadata/listing and report that no structured table was available. It does not scrape search-engine text, infer values from names, or download bulk raw data. Re-running `scripts/ingest_psi.py` is sufficient to populate a fresh cache when public access is restored.
