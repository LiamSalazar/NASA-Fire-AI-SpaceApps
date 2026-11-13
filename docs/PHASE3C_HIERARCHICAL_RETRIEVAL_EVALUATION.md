# Hierarchical Retrieval Evaluation

This is an additive Phase 3C engineering iteration. NASA raw/canonical inputs, historical gold and historical benchmark artifacts are preserved. No independent scientific adjudication is claimed. Experimental features remain default-off. QueryIntentV2 is retained; no Phase 4 work is started.

Evaluation uses neutral synthetic development fixtures, the exposed 20-case regression, historical compatible model replay and the exposed 40-case documentary source-identity set. There is no new independent scientific relevance gold. The original 11-case/224-candidate review packet is retained intact inside the expanded packet; independent reviewer fields remain blank.

| Configuration | Expected identity recovery | False DIRECT on no-direct cases | Total returned candidates |
|---|---:|---:|---:|
| A | 8/8 | 0/4 | 76 |
| A_budget_matched | 8/8 | 0/4 | 760 |
| B | 8/8 | 0/4 | 72 |
| C | 8/8 | 0/4 | 577 |
| D | 8/8 | 0/4 | 577 |
| E | 8/8 | 0/4 | 577 |

A is repaired exact/native execution. B adds reviewed hierarchy and relational eligibility. C adds controlled historical search replay with revised validation. D adds selective compatible reranker replay. E records available historical Jev advisory judgments without treating rhetorical class as scientific relevance. A_budget_matched supplies up to 40 lexical candidates per case, equal to the discovery cap. Candidate-count increases are not semantic-reasoning gains.

Historical objective recovery was 7/8. The fresh 8/8 result comes from preserving selected statement citations before BM25; the approved domain taxonomy has zero edges, so this does not demonstrate a NASA hierarchy gain. Identity recovery Wilson 95% CI is approximately 0.676–1.000 (small N). Zero false DIRECT in four designated negative cases has a broad 95% upper bound of approximately 0.490; it is not a universal safety claim.

Native median latency: A 77.6 ms; B 98.5 ms. Offline harness median 447.9 ms includes several configurations and is not live model latency. Fresh synchronous endpoint timings are recorded separately in the examples. Historical reranker latency near 14 seconds is historical only. Selective policy skips 9/20 cases; 8/20 have compatible replay and 3/20 have incompatible inputs. Utility and live cost/latency improvement remain unestablished.

Fresh documentary Recall@1/3/5/10 = 25/40/34/40/34/40/36/40; MRR 0.7267. These score expected source identities, not independent scientific relevance.

Scientifically reviewed Precision@1/3/5, RELATED precision/recall, nDCG, answer usefulness, scientific citation precision and unsupported-claim rate are NOT SCOREABLE: expert-label denominator is zero. The Precision@5 ≥ 0.90 target is not established. Technical numeric contract cases are 9/9; the full test suite also covers unsupported-unit changes. See machine-readable benchmark, numeric, review and documentary receipts.

Final quality: Ruff format/check PASS; pytest 128 passed. Canonical/native/taxonomy SHACL and Evidence Registry/FTS integrity PASS. Original raw/canonical, frozen-gold and historical-artifact digest changes: 0. Final receipts: `artifacts/phase3c_related_integrity_v2.json` and `phase3c_related_quality_v1.json`.
