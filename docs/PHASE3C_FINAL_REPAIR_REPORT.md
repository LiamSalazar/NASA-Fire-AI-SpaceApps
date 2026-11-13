# Phase 3C final corrective repair

This versioned corrective pass repaired class-scoped retrieval, deterministic
intent resolution, generic condition context matching, and the conventional
mmHg-to-Pa conversion. It preserves every earlier Phase 3C benchmark. The
current architecture is frozen in
`artifacts/phase3c_final_repair_native_freeze_v4.json`; per-case outputs and
digests are listed in `artifacts/phase3c_final_repair_results.json`.

The native projection evaluates all 405 canonical run records. It projects 405
run entities, 682 supported reported/design conditions, 812 relations, and 424
unique evidence references; it creates no new observed measurements. The 274
pressure entries labeled mmHg now convert to Pa under the existing approved
Pressure mapping. 2,314 unsupported field interpretations remain staged with
provenance. Two runs have no validated values, all 405 retain at least one
unresolved field, and there are no invalid conversions or broken evidence
references.

The frozen 12-case retrieval regression recovered all 11 required source-backed
evidence identities (11/11); the no-answer case remains empty. Exact evidence
sets match in 8/11 positive cases because additional eligible candidates remain
in three results. This is evidence-identity recovery, not an independent
scientific-relevance score. The separate 20-case service regression recovered
required evidence in 11/12 objective cases; only 2/20 meet the strict combined
interpretation, retrieval, and provenance criterion. Eight cases remain
`REVIEW_REQUIRED`.

The repaired interpreter is semantically exact on 28/30 newly compositional
cases and 11/41 standalone cases. Across its 101 frozen/reviewed supported
interpretations, requested-information precision is 1.00 and recall is 0.68;
numeric comparison is 6/6 (SMALL_N), explicit approximation is 13/13, and range
fields are 15/26. The historical composition set is 10/30 exact. The gold is
unchanged; raw extraction, previous resolution, repaired resolution, and field
metrics are preserved per case.

The 230-case dynamic-property regression remains 230/230, and the existing
post-freeze registry stress test remains 125/125. These support the generic
executor. They do not establish successful generalization to a new structured
NASA combustion source. The previous bounded PSI/NTRS candidate searches did
not provide an eligible, unexposed structured experimental dataset. The
reproducible candidate pool is retained; no candidate was silently replaced.
The preserved 39-case parity second pass measured DIRECT 39/39, RELATED 39/39,
and exact evidence IDs 9/39; it was not rerun after this final repair. FTS5/BM25
was rerun on 40 cases: Recall@1/3/5/10 = 25/40, 34/40, 34/40, 36/40 and MRR
0.7267. The machine-readable extensionality summary is
`artifacts/phase3c_final_repair_extensibility_v1.json`.

Jev remains optional. The prior live evaluation (30 reviewed rhetorical
triage cases) measured F1 0.8889 versus 0.7500 for deterministic rules, but did
not establish sufficient evidence-preserving workload reduction for mandatory
use. Grounded paraphrase generation remains disabled: no independent fidelity
gold exists, and the quotation-oriented validator remains in force.

Final gates: Ruff format/check pass; pytest 91 passed; canonical and generic
SHACL conform; SQLite and foreign-key integrity pass; evidence, FTS and native
references are intact. Historical result artifacts remain unchanged. The
engineering iteration is closed, but Phase 4 readiness is **NO**: standalone
language performance, independent relevance review, new-source structured
generalization, and useful validated paraphrase response remain open.
