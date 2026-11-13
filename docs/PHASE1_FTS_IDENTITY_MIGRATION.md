# FTS identity migration

The registry was backed up to `data/index/evidence.pre-phase1-fts-migration.sqlite` before migration. The replacement identity is source document + artifact checksum + `segment-v2` + page + offset. It distinguishes changed NASA artifacts while remaining stable for an unchanged artifact. Raw NASA files are untouched.

Final execution created an additional timestamped backup before cleanup. Migration removed 144 obsolete old/new passage identities across 109 logical-location groups, migrated zero candidate references (none pointed at removed IDs), and rebuilt FTS from the canonical passage table. Final integrity check: 569 passages, 569 FTS rows, zero logical duplicate locations, zero candidate/review/FTS orphans.

FLEX artifact checksum: `b4f6ca983e2792c33a0b92220a791a818f426bb635b94f7fd33dc8c9c471e79d`; segmentation version: `segment-v2`. FLEX Run 1/2/3 each produced 317 logical passages and ID-set digest `4866f01d45321494756493d3d530a82b194cf798e6bb6b6ab11360cf8a808b66`; runs 2 and 3 added zero passages, FTS rows, documents, or canonical records.
