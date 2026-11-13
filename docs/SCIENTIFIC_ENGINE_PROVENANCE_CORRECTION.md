# Scientific engine provenance correction and release assessment

## A. Executive decision

**SCIENTIFIC ENGINE NOT YET ACCEPTED.** The backend now owns citation selection and
records claim decisions, but complete live answers still omit requested findings.
The 85% usefulness and essential coverage gates have not been met. This is an
engineering correction with an honest NO-GO, not a scientific release freeze.

## B. Original failure

The old explanation schema required every `segments[].support_ids`. The historical
SoFIE geometry turn generated MIST, RTDFS and GEL facts, then rejected MIST and
GEL dimensions against the selected spans and finally delivered only RTDFS.
Another failure path let `organize()` discard already verified prose. A source ID
appearing in the answer plan could also make a need appear covered without its
content being communicated. The saved case and its original trace are in
`artifacts/scientific_engine_release_v1/live-holdout-v1.json.gz`.

## C. Responsibilities

Nemotron writes English scientific text and may optionally provide source ID hints.
The backend segments independently checkable propositions, searches registered
passages, verifies subject, quantities, modality, provenance and semantic support,
and creates numbered citations. Invalid model IDs do not authorize citations.
Verified prose removed by the organizer is restored. The model still plans
information needs, but the plan no longer requires source IDs.

## D. Evidence Registry

The existing `EvidenceRegistry.resolve()` and `source_metadata()` remain the
authority for original passages, documents, locations and source links. No RDF,
ontology, source data or frozen evidence snapshot was modified. The new operational
ledger is separate because the read-only scientific snapshot is immutable.

## E. Claim–Evidence ledger

Each turn writes a private `claim-evidence-ledger-v1` JSON receipt under
`data/index/claim_ledger/` by default. The receipt links conversation, response,
question, snapshot, implementation hashes, provider model, retrieved and exposed
evidence IDs, search queries, need IDs, compact anchor-to-evidence mappings,
original and corrected claim text, matched and verified IDs, rejection
reason, repair identity, communicated state and cited evidence IDs. Rejections
remain as separate versions. Receipts are mode `0600`, have a content hash, and
are retained for 30 days. The file records backend decisions and minimal claim
text; it does not assert which evidence the model used cognitively. Source text
is untrusted data and is never executed as an instruction. Credentials and
authorization headers are not recorded.

## F. Provenance accuracy

The deterministic citation audit checks every emitted evidence ID against the
registered original document and source metadata. Its result is recorded in
`backend-provenance-citation-audit-final-v1.json`. This measures **resolvable provenance**.
Across the retained correction conversations, **70/70 emitted citations resolved**;
the final two post-fix questions contributed **8/8**. These counts include
DISCOVERY listings and repeated sources across turns.
It does not prove semantic support. The development runs exposed a real false
association: a package-wide absence statement borrowed passages about unrelated
flame events. A later run cited a NASA standard for a pronoun whose referent was
a different document. General package-absence and explicit-subject guards were
added, with adversarial tests. Neither case is silently scored as correct.

## G. Information preservation

The saved historical draft now yields six supported atomic propositions and one
rejected geometry dimension in backend replay. MIST's PMMA cylinders and 15 cm
rods, RTDFS's PMMA sheets and 30 cm × 5 cm samples, and GEL's PMMA spheres are
recoverable from original SoFIE pages 4 and 14. The complete comparison passes
the verifier against both pages in that replay. This replay is not a fresh final
conversation. Fresh Nemotron turns still omitted MIST or dimensions, so the
coverage defect is **not solved end to end**. Supported statements and final
communication are recorded separately.

## H. Scientific conversation example

A real Nemotron turn about NCA produced: “The Narrow Channel Apparatus (NCA) in
SoFIE aimed to use a 1-g narrow channel to control buoyancy so that microgravity
opposed-flow flame-spread rates and possibly extinction limits could be determined
on Earth.” The backend cited the original SoFIE presentation,
`ntrs-20200000361`, registered page 7, evidence ID
`E-hackathon-817485e7bad281c090241f84`. This statement preserves the objective's
intended status. The full turn is in `backend-provenance-unseen-live-v1.json`;
it later became development material after an unrelated absence defect was fixed.

## I. Evaluation

The historical old final answer communicated RTDFS alone. Replaying its saved
draft with the new backend recovered the six supported propositions described
above. The separate complete-context diagnostic generated four segments in each
condition; replay with the final verifier accepted zero automatic-context
paragraphs and one source-inspected paragraph. These are distinct drafts and
must not be represented as a controlled improvement in generation. The pinned
NLI threshold remained 0.92; false rejection of faithful paraphrases persists.

Final Candidate Recall@20 and independent scientist-graded usefulness and target
coverage were **not measured** in this correction. Prior frozen benchmark scores
remain in `SCIENTIFIC_ENGINE_RELEASE.md`. Verification acceptance counts are not
scientific precision. The final two new turns fell back to source excerpts (2/2);
additional candidates remained accessible in the response. No new scored
multi-turn continuity campaign was run after these edits. A release cannot be
accepted by the unit-test pass count.

## J. Generalization

New questions were fixed before each live batch and every result was kept.
Questions used to find the package-absence, citation and relevance failures are
development cases thereafter. The final post-fix questions and their outcomes
are stored in `backend-provenance-postfix-new-v1.json`; no source-specific rule
was added for them. Both of those turns used source excerpts instead of a useful
generated answer to the requested dimensions (0/2 useful turns by this review).
Two cases cannot establish population-level performance. The separate
`backend-provenance-release-evaluation-v1.json` set became development material
when it exposed the pronoun attribution defect.

## K. Stability

The snapshot verification and `uv sync --locked` pass. Tests run in 16 bounded
batches because a monolithic test run exhausted temporary storage in the earlier
release process. The completed shipping receipt reports **3,582 passed,
40 pre-existing skips and zero failures** in
`backend-provenance-regression-final-ship-v1.json`. The existing HTTP citation route
and `scientific-chat-v1` response schema remain available. A final no-key HTTP
chat returned 200 with original excerpts; its cited evidence route returned 200
for the same registered ID. NVIDIA credentials
loaded from the local `.env`; the pinned local NLI verifier was provisioned
outside the source corpus. No secret is in versioned receipts.

## L. Blocking limits and smallest next correction

The backend still lacks reliable semantic decomposition for compound comparison
statements and a general method to preserve all verified information needs
through live generation and repair. NLI can reject faithful source descriptions
and accept some unrelated source relationships. The final live answers are too
narrow, and fallback extracts can come from tangential passages of the same
source family. The next correction should improve proposition decomposition,
source identity binding and source-local relationship validation within the
existing registry, then run a
fresh, independently adjudicated acceptance set. Retrieval must remain broad.

## M. Git

All work is local on `NASA_hackathon` in `.worktrees/NASA_hackathon`. The source
snapshot and `data/raw/` were not edited. No push or merge was performed.
