# Phase 3C corrective benchmark protocol

Versions: PRE_CORRECTION artifacts remain immutable. New outputs use corrective
v1/v2 names. `phase3c_corrective_native_freeze_v1.json` freezes implementation,
registry and SHACL before live prediction. Gold is never derived from predictions.

Separate evaluation layers:

1. Canonical coverage: all canonical run/condition links, original values, units,
   context, unresolved fields, evidence validity and idempotence.
2. Linguistic interpretation: reviewed standalone and conversational cases and
   frozen compositional fixtures, with exact and per-field scores separately.
3. Representability: validated actual V2 objects, not inferred schema expressivity.
4. Generic execution: dynamic properties/classes and prohibited legacy-call guards.
5. DIRECT/RELATED: structured canonical constraints, missing/conflicting/invalid values.
6. Structured retrieval: immutable canonical table evidence and known condition truth.
7. Documentary retrieval: frozen source-backed source-ID gold and BM25 regression.
8. Safety retrieval: existing reviewed epistemic evidence identities. Exact quotation
   probes test recoverability, not independently reviewed paraphrase relevance.
9. Open world: ambiguity, unknown terms and no-source fixtures; staging cannot confer authority.
10. Generalization: prior holdouts remain historical; exposed sources are not new blind holdouts.
11. Synthesis: citation/authority plus quotation gate; no claim of verified paraphrase fidelity.
12. End to end: interpretation, evidence retrieval, classification and useful response
    independently scored. Safe but irrelevant fallback is not product success.
13. Jev: optional advisory triage; same reviewed inputs for rules/Jev/combined priority,
    simulated first-K review yield, no hard filtering or scientific publishing authority.
14. Latency: component median/p95/max/N; API failures and missing cases remain explicit.

Rates carry numerator/denominator and Wilson intervals where implemented; N<10
is SMALL_N. Do not aggregate layers into one magic score. Subjective relevance,
paraphrase fidelity and scientist usefulness require independent review and must
be labeled NOT_MEASURED if no reviewed gold is available.

Calls are persisted after each receipt and case. Retry only failed service calls,
at most two attempts per case in the corrective campaign. No model/prompt tuning
loop after prediction begins. Generic repairs require preserved first-pass results,
a change log and a new freeze/pass.

## Final corrective campaign supplements

The novel composition gold contains 30 intent-first cases across ten template
families. Combination novelty is measured by operation, target, relation
multiset, property/operator pairs, requested information and comparison/source/
unknown/ambiguity presence, ignoring numeric literal substitutions. Against
historical gold, 27 cases contain unseen combinations and nine composition
signatures are new. Gold is deterministic language intent, not expert relevance.

The first attempt is preserved. At most one separate retry is allowed for failed
service calls, reusing compatible successful predictions transparently. No model,
prompt, executor or resolver changes are permitted during that campaign.

Final quality commands and scientific integrity are captured by
`scripts/phase3c_corrective_finish.py`. Closure is allowed to record failed
readiness gates; a closed evaluation is not a claim of Phase 4 readiness.
