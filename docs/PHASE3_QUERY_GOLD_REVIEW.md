# Phase 3 query-gold review packet

The frozen source file remains unchanged. `phase3_query_interpreter_gold_candidate.json` is an **unreviewed** candidate derived only from the deterministic parser, controlled lexicon, ambiguity policy, and unit parser; it must not be used as final scoring gold.

## A. Auto-high-confidence cases (26)

These are direct canonical labels, safe aliases, or explicit query syntax with no unknown/ambiguous term detected: qi01–qi18 excluding qi12–qi13, qi24–qi27, qi31–qi36, qi43, qi49–qi50 where not listed below. Each candidate retains `DETERMINISTIC_PARSER`, `SAFE_CONTROLLED_ALIAS`, and `UNIT_PARSER` provenance.

## B. Review-required cases (24)

The machine-readable queue identifies each field and deterministic result. Review is needed for known ambiguity (`acrylic`, `flow`, `velocity`), unknown material terms, numeric ranges/approximations beyond the current parser, unsupported follow-up context, documentary/requested-information scope, or comparison targets not deterministically resolvable.

Key decisions include whether bare S1/S2 is context-resolvable, whether observation/conclusion/publication wording maps to current `requested_information`, and whether range/approximation language is in the current query contract.

## C. Exclude candidates (0)

No query text was changed or removed. Reviewers may mark individual cases excluded if current domain semantics cannot support a defensible expected intent.

The final live benchmark must wait for human/domain review to promote candidate labels to a separately frozen reviewed file.
