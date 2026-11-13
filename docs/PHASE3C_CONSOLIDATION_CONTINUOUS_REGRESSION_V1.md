# Fresh engineering gates

```json
{
  "commands": [
    {
      "command": [
        "uv",
        "run",
        "ruff",
        "format",
        "--check",
        "."
      ],
      "exit_code": 0,
      "execution": "FRESH_LOCAL_EXECUTION",
      "log": "artifacts/phase3c_consolidation_format_v2.txt",
      "sha256": "c08cb44deef3bd5e6aceb013d76f19020ed4f70d4eea0e35334c33d2a0dc94ff"
    },
    {
      "command": [
        "uv",
        "run",
        "ruff",
        "check",
        "."
      ],
      "exit_code": 0,
      "execution": "FRESH_LOCAL_EXECUTION",
      "log": "artifacts/phase3c_consolidation_lint_v2.txt",
      "sha256": "82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18"
    },
    {
      "command": [
        "uv",
        "run",
        "pytest",
        "-q"
      ],
      "exit_code": 0,
      "execution": "FRESH_LOCAL_EXECUTION",
      "log": "artifacts/phase3c_consolidation_pytest_v2.txt",
      "sha256": "3096307398516ef1201a72511386b4672b582e3826e4be97be1c586984cf6e32"
    }
  ],
  "shacl": {
    "canonical": {
      "conforms": true,
      "report": "Validation Report\nConforms: True\n",
      "execution": "FRESH_SHACL"
    },
    "native": {
      "conforms": true,
      "report": "Validation Report\nConforms: True\n",
      "execution": "FRESH_SHACL"
    },
    "taxonomy": {
      "conforms": true,
      "report": "Validation Report\nConforms: True\n",
      "execution": "FRESH_SHACL"
    }
  },
  "registry": {
    "sqlite_integrity": "ok",
    "foreign_keys": [],
    "missing_documents": 0,
    "missing_sources": 0,
    "missing_fts": 0,
    "duplicate_fts": 0,
    "fts_mismatches": 0
  },
  "frozen_files": 1050,
  "historical_changes": [],
  "graph_missing_evidence": [],
  "independent_review": null
}
```

The full quality gate is a runnable separate evaluation command, not yet an atomic gate for every unattended discovery cycle. Publication currently gates registry integrity, not all answer regressions. All 1,050 frozen historical digests are checked. Historical parity and dynamic suites were freshly executed in native_checks_v1; they are not promoted to independent scientific accuracy. The approximately 72,960 warnings originate in rdflib Dataset.default_context deprecation, not 72,960 scientific failures; no blanket warning suppression was introduced.
