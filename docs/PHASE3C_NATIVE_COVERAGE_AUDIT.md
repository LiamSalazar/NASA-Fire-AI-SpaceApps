# Native coverage audit

POST_CORRECTION coverage v2: 405 total canonical runs; 405 source-evidence-eligible
runs; 405 projected run entities; 408 valid generic reported conditions; 812
relations; zero facts newly asserted as observed measurements. Two runs have no
validated generic numeric/categorical value. All 405 have at least one unresolved
condition field. The source corpus remains unchanged.

2,588 unresolved fields retain original ConditionRecord provenance. Of these,
274 pressure conditions use mmHg, for which the conservative conversion table
does not currently supply an approved conversion. Other unresolved fields have
no approved registry property mapping. They are not silently registered.
Missing original values: 0; broken evidence references detected during projection: 0.
424 unique original record evidence references are retained in the input/provenance
boundary; this count is not the total number of graph evidence edges.

Idempotence is tested by repeating unchanged projection into the same graph and
comparing its triple set. Context (initial/final/reported condition), approximation,
ranges and exact source record values survive. A reported range is not treated as
a point observation; inconsistent multiple values do not establish DIRECT.

Artifacts: `phase3c_corrective_coverage_v1.json` preserves the first corrective
pass (406 conditions, 2,590 candidates). `phase3c_corrective_coverage_v2.json`
records generic source-expression support (408 conditions, 2,588 candidates).
The difference is a numeric-source-expression parsing repair, not altered gold.

Limitation: run type authority is inherited from existing canonical records;
this projection does not independently prove every upstream row was an executed
experiment. No new table is classified using that inherited assumption.
