# Phase 3B holdout selection

## Historical selection invalidated

The original v1 manifest selected structured `PSI-99_SAFFIRE-II` and documentary
`ntrs-20150023456` / FLEX. It is retained in the manifest history, but it is **not a
valid blind-holdout freeze**.

- `ntrs-20150023456` is invalidated as `PREVIOUSLY_EXPOSED_SOURCE`: it was acquired,
  segmented, indexed, and used in earlier retrieval/idempotence work.
- `PSI-99_SAFFIRE-II` is independently invalidated as `PREVIOUSLY_EXPOSED_SOURCE`:
  its experimental table was included in the prior `experimental_tables.json` profile
  inventory and selected by `phase15_import_profile.py`.

The corrected selector must exclude a source whenever it occurs in the Evidence
Registry, canonical corpus, raw/cache acquisition, prior holdout processing, reports,
gold/evaluation material, or semantic-design artifacts. Noncanonical status alone is
not eligibility.

## Corrected v2 metadata-only freeze

`artifacts/phase3b_holdout_manifest.json` now freezes:

- structured: `PSI-142_Quantitative_Studies_of_Cool_Flame_Trans` (`PSI-142`);
- documentary: `ntrs-20250001364`.

The v2 selection digest is
`799d9b377ceae900a362577ced1a44d9b4f90ccc72dd2cf8978de29fd97edbb5`.
The selector records only official catalog/citation metadata and the eligibility
exclusions. It does not open selected tables or document bodies. The selection rule is
stable identifier ordering after excluding sources present in the local corpus or prior
semantic/evaluation history. **Detailed holdout scientific content was not used to
select or design the V2 semantic architecture.**
