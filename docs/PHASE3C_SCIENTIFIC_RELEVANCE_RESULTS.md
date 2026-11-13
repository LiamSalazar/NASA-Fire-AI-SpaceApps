# Scientific relevance evaluation status

The exact-evidence regression is now 11/11 required IDs recovered across 11
positive source-backed probes (SMALL_N); exact result sets agree in 8/11. The
twelfth frozen probe is an explicit unavailable source and returned no
evidence. All 12 outputs retained valid source metadata. These checks establish
identity recovery against frozen source-backed records, not full scientific
relevance, authority appropriateness, or paraphrase retrieval.

The native service benchmark has 20 cases: 12 objectively scoreable evidence or
no-answer criteria and 8 `REVIEW_REQUIRED` cases. Objective recovery is 11/12;
interpretation exactness is 6/20; strict combined end-to-end success is 2/20.
No model-generated relevance label was used as gold. The eight review-required
cases remain explicitly unresolved. For the objectively scoreable set, extra
retrieved passages in three positive cases still need relevance/authority
review even though all expected identities were recovered.

The review packet in
`artifacts/phase3c_final_repair_scientific_relevance_review_v2.json` includes
queries, class requests, expected and actual evidence identities, text, NASA
source metadata, page/section, and ranking/eligibility diagnostics. Reviewer
fields are blank. `human_review_performed` is false. This packet is suitable
for independent scientific assessment; this report does not claim expert
validation.

The latest preserved 39-case parity second pass reports DIRECT 39/39, RELATED
39/39, and exact evidence IDs 9/39, with the native runtime guard and SHACL
passing. It is a compatibility comparison, not independent relevance truth,
and was not rerun after this final retrieval repair. No new full-corpus V1 parity
sweep was run because this corrective pass did not change the V1 executor. The
FTS5/BM25 baseline was rerun over 40 source-backed probes: Recall@1 25/40
(0.625), @3 34/40 (0.850), @5 34/40 (0.850), @10 36/40 (0.900), MRR 0.7267.
The new diagnostics use the existing FTS5/BM25 path, not global vector
retrieval.
