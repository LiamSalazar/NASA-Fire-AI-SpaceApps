# Native context, units, and unresolved-field audit

The additive projection now processes every canonical run record. Results:
405/405 eligible runs projected; 682 supported conditions; 812 semantic
relations; 424 unique evidence references; zero broken references; zero
invalid conversions; zero missing original values; and zero new observed
measurements. The representation distinguishes reported/design conditions from
measurements and retains qualifiers and evidence context.

The 274 `mmHg` values are converted to Pa using the conventional factor
133.322387415 Pa/mmHg only where the pre-existing declarative projection and
registry identify the field as Pressure. This validates unit conversion, not a
new scientific property identity. No converted values are asserted as newly
observed NASA measurements.

The 2,314 fields without sufficient approved property mapping remain staged;
all 2,314 retain provenance. Their root cause in this projection is “no
approved property mapping”; this is not evidence that each represents a new
scientific concept. A staged field cannot support DIRECT. Two run records
contain no validated values; all runs retain one or more unresolved fields.

Constraint execution now filters reported values by requested context. A
context-specific value known to differ yields DIFFER; no value for that context
yields UNKNOWN, not DIFFER. The generic evaluator does not aggregate multiple
measurements implicitly. APPROX without explicit tolerance/interval does not
invent a percentage tolerance. The new unit/context tests cover initial versus
final records, missing-context UNKNOWN, and the standard mmHg conversion.

The table-role profiler remains advisory: a run-like header proposes a
`UNREVIEWED_STRUCTURAL_HINT`, never a canonical ExperimentalRun publication.
Unknown rows remain data/staging until meaning is supported. No unseen
structured NASA combustion dataset was newly acquired in this cycle; the
candidate audit is documented separately.
