# Corrective post-freeze changes

The v1 native freeze and first corrective retrieval results are preserved.
Two generic defects discovered during code-path inspection justified a separate
v2 freeze before the next native end-to-end pass:

- GENERIC_BUG_FIX: comparison operands now restrict candidate entities. A comparison
  must not enumerate every unrelated run when it has no additional constraints.
- GENERIC_BUG_FIX / AUTHORITY_BOUNDARY: the one-time legacy projection publishes
  epistemic classifications only from existing reviewed record types. Three old
  automatically classified bare records lack that authority and are quarantined
  as review candidates, rather than silently inheriting NASAConclusion/OpenQuestion
  status. Raw data and historical canonical records are unchanged.

There are no holdout-specific scientific rules. Interpretation prompt/resolution
is unchanged between v1 and v2; native query/bundle selection is not. Therefore
old live linguistic calls remain compatible, but native results are versioned.

`phase3c_corrective_native_freeze_v2.json` records the repaired architecture.
The existing original Phase 3C holdouts are already exposed, not new blind sources.

Subsequent freezes and separately reported passes:

- v3 GENERIC_INTEGRATION: actual native natural-language service and bounded
  interpreter adapter. No compatibility execution was introduced.
- v4 GENERIC_BUG_FIX: reconcile contradictory minimal slots using only approved
  aliases, validated expressions, registered source IDs and administrative words.
  Unknown scientific terms remain unresolved. Replayed predictions are explicitly
  POST_HOLDOUT_REPAIR; they are not new blind model results.
- v5/v6 AUTHORITY_BOUNDARY: documentary source quotations no longer inherit the
  model's default observed-result label. Canonical design/test criterion status is
  preserved. The complete quotation gate is unchanged. Final rendering clarifies
  that no DIRECT structured match does not mean no documentary support.
- v6 final formatting and compatibility checks do not modify NASA facts or gold.

The final metadata audit reuses persisted synthesis responses offline. Its v1
empty-query reconstruction omitted a requirement; v2 uses the original query and
preserves both artifacts. This is an audit-harness repair, not a live model repair.
The v1 integrity aggregate incorrectly included the deliberately mutable progress
checkpoint; v2 excludes only that checkpoint. Every raw, canonical, original gold
and historical benchmark digest remains unchanged.

No source-specific scientific rule, approved scientific alias, or gold expectation
was added to fit any holdout. New composition templates were frozen after v6,
before their predictions, and cause no executor/resolver change.
