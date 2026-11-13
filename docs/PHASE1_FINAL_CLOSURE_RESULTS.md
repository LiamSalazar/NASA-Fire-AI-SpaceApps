# Phase-1 final-closure execution

## Before

The audited live extraction contained 23 exact-span candidates, including invalid rhetorical classifications: infrastructure as observations, titles/topics as conclusions/open questions, and duplicate safety implications. FLEX had duplicate FTS/evidence identities from two segmentation paths.

## After implemented controls

- Candidate records retain exact span, source type, local heading, scope, uncertainty, modality, and negation fields.
- The rhetorical prompt explicitly permits NONE and rejects titles, themes, approach, relevance/impact, infrastructure, and noun phrases as scientific claims.
- All LLM reported observations now require review; all conclusions, safety, normative, and open-question candidates require review.
- Human review workflow and reviewed-candidate publication were executed. Two audited, explicitly qualified safety implications were approved and published with their evidence spans; 20 incorrect rhetorical candidates were rejected.
- Registry backup and a FLEX FTS identity migration were initiated. The intended v2 ID is document/checksum/segmentation/page/offset.

## Verification and remaining result

The graph rebuilt with 930 canonical records, 5,784 triples, and 131 runs; SHACL conformed on the last completed build. The review queue had no pending audited candidates. Existing evidence links were retained.

## FTS closure

The v2 identity contract is document ID + artifact checksum + `segment-v2` + page + deterministic offset. A timestamped registry backup was created before migration. 144 obsolete duplicate IDs in 109 logical-location groups were removed after reference checks; FTS was rebuilt from 569 canonical passages. Candidate, review, and FTS orphan counts are all zero.

FLEX Run 1/2/3 each had 317 passages, total/FTS counts of 713 during the three-run check, and identical digest `4866f01d45321494756493d3d530a82b194cf798e6bb6b6ab11360cf8a808b66`. Runs 2 and 3 added zero documents, passages, FTS rows, or canonical records. The final global dedupe reduced the registry to 569 canonical passages/FTS rows without removing a referenced claim.

`READY_FOR_PHASE_2 = YES`.

All Phase-1 closure conditions now hold: versioned evidence identities, repeated unchanged FLEX idempotence, preserved evidence references, review history, SHACL conformance, and passing automated checks. No Phase-2 capability was implemented.
