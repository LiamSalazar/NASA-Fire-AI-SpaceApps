# PSI structured dataset publication

| Dataset | Rows | Published runs | Published samples | Identity rows staged / quantities pending |
|---|---:|---:|---:|---|
| BASS (psi-26) | 122 | 111 | 0 | 11; unsupported scientific quantities remain pending |
| FLEX-2 (psi-68) | 8 | 0 | 0 | 8; unsupported scientific quantities remain pending |
| SAFFIRE-II (psi-99) | 15 | 0 | 9 | 15; unsupported scientific quantities remain pending |
| SAFFIRE-III (psi-100) | 2 | 0 | 2 | 2; unsupported scientific quantities remain pending |
| SAME (psi-102) | 8 | 0 | 8 | 8; unsupported scientific quantities remain pending |
| SAME-R (psi-101) | 109 | 0 | 0 | 109; unsupported scientific quantities remain pending |
| SPICE (psi-107) | 469 | 0 | 0 | 469; unsupported scientific quantities remain pending |

All 733 source rows were inspected with original headers, checksums, duplicate counts and complete staged source values. Exact file paths come from the prior PSI reconciliation artifact. New canonical artifacts are additive and opt-in. Engineering source-contract approval is not independent scientist review.

BASS: unique explicit As Run Test # plus source date/sample permits 111 run identities; 11 missing/repeated identities remain staged. Original material descriptions are preserved without guessing PMMA from an unlabeled sphere or inheriting gravity. FLEX-2's eight rows list configuration alternatives/ranges, not identified individual runs. Saffire-II publishes nine explicit sample identities, including blank material labels; camera/footnote rows remain separate. Mixed gravity columns, approximate values and derived O2 footnotes prevent blanket observation publication. Saffire-III publishes two samples, without claiming samples are runs. SAME publishes eight sample identities; same-conditions-as references are not silently expanded. SAME-R and SPICE require stable trial/run identity and scientific role review; SPICE duplicate acquisition rows are not new experiments.

Supported sample labels remain raw source labels, with no canonical material merge or unsupported numeric mapping. Native projection idempotence and explicit identity queries are tested. Detailed staged rows and blockers: `phase3c_targeted_psi_publication_v2.json`. Current canonical totals add 111 runs and 19 samples; the old 405 runs remain unchanged.
