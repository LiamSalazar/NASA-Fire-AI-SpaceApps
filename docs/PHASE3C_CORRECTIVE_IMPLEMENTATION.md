# Phase 3C corrective implementation — evaluated closure

Historical results are preserved. `artifacts/phase3c_corrective_baseline_v1.json`
freezes raw/canonical and pre-correction evaluation digests. No Phase 4 work started.

Implemented and tested:

- Project condition links for all 405 canonical run records instead of using the
  two-row legacy execution view. Original values, units, source references and
  initial/final context survive in generic records.
- Represent reported conditions as ExperimentalCondition, not observed Measurement.
- Preserve missing, conflicting, approximate and invalid values as non-matches;
  no implicit approximation percentage. Missing relation values are open-world unknowns.
- Filter eligible evidence inside SQL before BM25 truncation. Source metadata can
  be recovered from passage/document/source linkage even if the redundant ref row is absent.
- Combine documentary ranking with the structured KG. Requested epistemic classes
  are selected independently of run matches and only with lexical evidence overlap.
- Preserve child condition evidence and context in the EvidenceBundle.
- Resolve compound linguistic mentions against approved aliases, default implicit
  run targets, preserve bare velocity/acrylic/Saffire ambiguity, and parse inclusive
  inequalities, ranges and explicit approximation expressions.
- Unreviewed table roles produce operational, provenance-backed ROW candidates;
  no automatic ExperimentalRun publication.
- Deterministic readable native rendering separates direct/related evidence,
  requirements/guidance, coverage, sources and expandable technical JSON.
  The quotation-only generative gate is retained.

Final tests: 84 passed; Ruff and SHACL pass. Corrective live interpretation and
Jev triage receipts are resumable and separate from original Phase 3C predictions.
The actual natural-language service is now exercised, not only a preconstructed
V2 bundle. An offline path remains usable without API credentials.

The live historical set has 71 cases; the novel composition set adds 30 surfaces,
27 with previously unseen capability combinations and nine new composition
signatures, ignoring numeric literals. Jev has 30 completed live cases. The native
service has 20 cases in two separately preserved passes. Generic fixture execution
is 230/230 with 125/125 post-freeze stress cases; usefulness still fails.

Final metadata distinguishes unclassified documentary quotation from a reported
observation and retains reviewed design/test criterion authority. It does not
relax the scientific paraphrase boundary.

These are implementation results, not adoption or expert-readiness claims.
See `PHASE3C_FINAL_CLOSURE.md`: READY_FOR_PHASE_4=NO, V2 remains experimental.
