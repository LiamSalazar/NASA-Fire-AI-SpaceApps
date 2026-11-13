# Phase 3B post-holdout changes

The blind first-pass artifact is preserved unchanged. The following subsequent changes
were made and do not retroactively alter its zero-shot measurements.

| Classification | Change | Holdout-specific scientific rule? |
| --- | --- | --- |
| GENERIC_BUG_FIX | Normalize textual numeric operators such as `at most` in the shared offline parser. | No |
| GENERIC_SEMANTIC_ABSTRACTION | Add the generic V2 compatibility execution adapter and parity harness. | No |
| GENERIC_FORMAT_SUPPORT | None | No |
| HOLDOUT_SPECIFIC_SEMANTIC_RULE | None | No |

A second acquisition/profiling pass was not needed: the first pass acquired and profiled
both sources without a format or serialization failure. The later isolated index is a
query-probe evaluation, not a replacement first pass.
