# Requested-information and topic-aware retrieval repair

Native retrieval now treats the requested evidence class as a registry-driven
selection dimension, not as a topic keyword. A candidate must satisfy the
requested class, source/evidence eligibility, authority policy, and available
topic anchors. Entity constraints and comparison operands contribute topic
anchors; class candidates carry overlap, coverage, score, source, location,
eligibility reason, rank, and exclusion traces into the EvidenceBundle.

The prior defect included a target/information class conflation and class
selection that could surface unrelated evidence. A requester for a NASA
conclusion now selects conclusion-class records; observation, requirement,
guidance, explicit open question, intervention, measurement, and safety
implication are independently selectable. Documentary ranking remains the
existing FTS5/BM25 path. A failed class/topic match produces a typed no-direct
reason rather than a broad keyword substitute. A bare “NASA” is not interpreted
as a source ID. A material-only or measurement query does not acquire unrelated
safety guidance merely because it shares a corpus.

The frozen objective test recovered all 11 required evidence IDs in 11
positive cases; one explicit unavailable-source case returned no evidence.
Exact evidence-set agreement is 8/11 because three cases also contain extra
eligible passages. Median retrieval execution was 59.0 ms (N=12; p95/max 121.4
ms). The 20-case service regression recovered objective evidence in 11/12
cases; full combined success is 2/20. Eight other cases remain
`REVIEW_REQUIRED` and are not counted as correct or incorrect relevance labels.

These are source-backed identity checks, not independent topical relevance
ratings. A scientist review packet with evidence text, source title/location,
retrieval trace, and blank reviewer judgments is provided in
`artifacts/phase3c_final_repair_scientific_relevance_review_v2.json`. No human
review is claimed. Remaining action is independent relevance/authority review,
especially for the three extra-evidence results and the eight subjective cases.
