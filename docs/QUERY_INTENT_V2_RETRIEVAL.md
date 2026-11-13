# QueryIntent V2 retrieval

The V2 planner validates generic targets, entity constraints, property constraints,
information classes, and units through the semantic registry. The evaluator produces
`MATCH`, `DIFFER`, `UNKNOWN`, or `INVALID`. Generic DIRECT requires every required
canonical constraint to match; RELATED requires explicit partial overlap. The current
V2 execution path is additive and parity-tested against V1 through a legacy run-field
compatibility adapter, so it remains experimental rather than the default retrieval
path.
