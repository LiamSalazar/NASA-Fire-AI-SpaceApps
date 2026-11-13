# Phase 3C query expansion implementation and measurement

Nemotron expansion is an opt-in, bounded documentary-candidate generator. It receives the original question, validated QueryIntentV2, and approved registry aliases. It proposes no more than three short alternate formulations. Every original query is retained. Numeric expressions and units, negation, explicit sources, known entity/property identities, and explicitly requested information classes are checked before an expansion can contribute candidates. Expansions do not update aliases or ontology terms.

On the 20-case exposed end-to-end regression, the live model proposed 54 formulations among 19 completed expansion responses; **7/54 were accepted** across four queries and **47/54 were rejected**. Rejection prefixes were: added registered entity 35, added information class 4, added registered property 3, numeric constraint changed/dropped 3, and missing hard anchor 2. One expansion request timed out. The prompts used `nvidia/nemotron-3.5-lightning-30b-a3b`, temperature 0, non-streaming JSON and a 500-token output bound.

The pool grew from 18.7 mean candidates in a deterministic original-query top-20 FTS budget control to 19.4 under expansion; 14 candidate IDs were additional to that budget-matched lexical pool. However, objective expected-ID recall stayed **7/8** at @1, @3, @5 and @10 for both controls. This exposed set is small and is not a relevance gold. Expansion produced no demonstrated recall gain; more candidate IDs alone are not an improvement.

**Decision:** `NEMOTRON_QUERY_EXPANSION_DECISION = KEEP_EXPERIMENTAL`. Continue to preserve validated constraints and the A-path fallback. Do not enable by default based on this result.
