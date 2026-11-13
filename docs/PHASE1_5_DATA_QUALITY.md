# Data quality

Observed source-data issues: non-UTF-8 CSV bytes (profiled with replacement and retained raw), semicolon-delimited multi-value design ranges in FLEX-2, approximate/inequality strings in SAFFIRE, malformed/legacy headers, missing values, and duplicate-looking SPICE rows. Parser policy: preserve reported strings/units; do not manufacture a central value. FLEX ingestion accepted only parseable per-test values. These are source-format issues, not evidence gaps.
