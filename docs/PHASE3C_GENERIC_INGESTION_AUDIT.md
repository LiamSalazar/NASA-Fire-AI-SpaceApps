# Generic ingestion corrective audit

Unreviewed table rows no longer become ExperimentalRun entities automatically.
`propose_table_role()` produces advisory structural hints for publications,
inventories, designs, runs, or unresolved tables. A run-ID header is not evidence
that an experiment was executed. Without approved role authority, rows remain
provenance-backed registry/staging records and produce zero canonical runs.

The native ingestion boundary can accept an explicitly reviewed role, but the
authority argument is not itself an independently authenticated review workflow.
That integration requires further validation before default adoption.

Four source-independent fixtures cover a catalog, planned design, run-shaped
table, and unknown table. All four retain unreviewed status; safe role handling
4/4, SMALL_N, with zero automatic canonical scientific roles. Tests additionally
verify that generic ingestion preserves row evidence and creates no unreviewed
run entities. See `phase3c_corrective_table_role_audit_v1.json` and
`tests/test_phase3c_corrective.py`. Fixture success is not a new NASA dataset
generalization result.

The complete canonical projection preserves 2,588 unresolved condition candidates,
including 274 unsupported-unit fields. These candidates retain their original
ConditionRecord provenance and are not published as new property identities.
Canonical source files, approved aliases and the baseline staging database were
not rewritten. The native projection stages candidates in an isolated derived
representation, not as reviewed scientific facts.

No eligible new structured experimental NASA artifact was acquired in the bounded
campaign. Therefore new-source structured profiling/mapping precision/recall,
false-canonicalization rate and staging completeness have no scientific holdout
denominator: NOT_EVALUATED, not 1.0000. There are zero holdout-specific scientific
code additions. Decision: REVISE, with conservative unreviewed-row staging retained.
