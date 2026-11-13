# Scientific engine integration assessment — 2026-11-09

## 1. Executive GO/NO-GO decision

**SCIENTIFIC ENGINE NOT YET ACCEPTED.** Corpus access and provenance improved, and the small historical retrieval benchmark did not regress. A corpus-wide vector index, independent source-inspected answer evaluation, and scientifically validated document-OOS extraction are still absent. The 85% information coverage and usefulness gates cannot be claimed.

## 2. Baseline architecture and failures

The previous `hackathon-20261105-v9` snapshot had 39 sources, 8 deeply mapped PSI tables, 646 reported run records, 472 measurement records, and 44,490 RDF triples. Lexical retrieval, native graph queries, registry citations, Nemotron/Sonnet generation, and claim verification were present. The prior four-case pilot missed useful source facts and falsely rejected some faithful paraphrases; see `SCIENTIFIC_ENGINE_STABILIZATION.md`. Its 24-question provisional Recall@20 was 96.15% on 13 source-inspected questions; the [final v9 baseline replay](../artifacts/scientific_engine_integration_20261109/baseline-recheck-v9-final.json) reproduces that score with the current retrieval code.

## 3. NASA PSI source inventory

The [coverage receipt](../artifacts/scientific_engine_integration_20261109/coverage-v15.json) classifies all **24/24** team campaigns. The five family tables contain **1,972** rows, including 100 session rows; `experiments_all.csv` separately contains **1,872** summary rows and is not an additional set of unique runs. Publication metadata contains **360** rows, without demonstrated full text for those publications. The current snapshot contains **19** original PSI tables: 10 with source-explicit structured mappings and 9 indexed as documentary original rows. Five campaigns remain catalogue-only.

## 4. Corpus coverage before and after

| Measure | v9 baseline | v15 expanded |
| --- | ---: | ---: |
| Original PSI tables | 9 | 19 |
| Structured PSI table sources | 8 | 10 |
| Registered sources including documents and catalogue | 39 | 54 |
| RDF run records | 646 | 1,032 |
| RDF measurement records | 472 | 647 |
| RDF triples | 44,490 | 76,690 |
| Team processed family rows separately searchable as provisional discovery | 0 | 1,972 |

Of **1,964** non-excluded processed family rows, **1,964** have an explicit disposition and a provisional row locator. This is **100% traceability/disposition**, not 100% NASA-verified experimental representation. Original and team processed row counts differ in granularity and are never equated.

## 5. Remaining source-quality limitations

The team QC report records SIBAL thickness unit conflict, inferred BASS material identities, unspecified SPICE diluent, duplicate identifiers, and incomplete metadata. The new processed-row tier is labelled `PROVISIONAL_PROCESSED`, stays outside the canonical graph, and is offered only as DISCOVERY. The five catalogue-only campaigns have no original experimental rows in this snapshot. Original PSI rows for nine additional tables still need run/session interpretation and scientific QC. No publication full-text claim is made from bibliographic metadata.

## 6. Ontology and graph changes

No ontology term was added. The existing `Investigation`, `ExperimentalRun`, `Sample`, `ExperimentalCondition`, and `Measurement` classes and approved relations represent two additional ACME source tables. Original oxygen, pressure, and burn-duration cells retain their printed values and units; `atm` and `bar` now normalize through explicit general unit conversions. The `approx p (bar)` header retains an approximate qualifier. Derived adiabatic temperatures and ramped cells were not promoted as observations.

## 7. Scientific relationship validation

The [graph receipt](../artifacts/scientific_engine_integration_20261109/graph-oos-v15.json) checked **1,631** distinct RDF evidence references with **0** unresolved references; SHACL structural validation conformed. All **19/19** registered original PSI investigation landing URLs returned HTTP 200 in the [link check](../artifacts/scientific_engine_integration_20261109/psi-links-v15.json). This establishes structural integrity and source linkage, not scientific truth of every statement. No new graph relation was inferred from team-processed similarity. The existing claim relation audit remains in place; no fresh source-inspected false-acceptance rate was measured in this assignment.

## 8. Hybrid retrieval architecture

The production search continues to combine native structured/KG eligibility with lexical FTS and reciprocal-rank fusion. Retrieval now allocates separate candidate pools to original evidence, catalogue metadata, and provisional processed records. Original and catalogue evidence receive first-page consideration; provisional rows remain searchable after those tiers and cannot grant DIRECT status. Source identity, evidence ID, row and cell locator, and original file checksum remain in the registry. Registered PSI landing links now use the official `/data/investigations/{accession}` route instead of the older team catalogue `/data/studies/` path. The repository's `LocalVectorIndex` abstraction exists, but no corpus-wide vectors for this snapshot were provisioned or enabled.

## 9. Retrieval ablation metrics

The [paired receipt](../artifacts/scientific_engine_integration_20261109/channel-ablation-v15.json) uses the same 24 questions and 32 provisional source judgments (13 questions judged). Macro source-document recall is:

| Channel | R@5 | R@10 | R@20 |
| --- | ---: | ---: | ---: |
| Lexical only | 66.03% | 73.97% | 75.51% |
| Available fused retrieval | 69.36% | 85.26% | **96.15%** |

Measured mean local latency was 6.4 ms for one lexical query and 879.0 ms for full search; the latter includes interpretation and structured work and was measured under concurrent regression load. Vector-only and lexical+vector results are **not available**. KG-only source-document recall is **not comparable** to these document qrels. No general scientific precision claim follows from this small pool.

## 10. Evidence and context coverage

The expanded graph contains source-scoped run conditions and durations for two more ACME investigations, and original rows from CFI, DAFT, SPICE, ACME sessions, SLICE, and FLEX-2 can be inspected through registry evidence. A source table row now includes header–value pairs in search text so that original numbers retain their meaning. The [retrieval receipt](../artifacts/scientific_engine_integration_20261109/recall-v15.json) found **26/32** judged anchor evidence IDs at any returned rank. These are retrieval hits, not communicated findings. There is no new adjudicated receipt counting essential propositions available, supplied, generated, verified, and communicated in final answers; the 85% information gate remains unmeasured and failed by prior conversational evidence.

## 11. Verification and repair improvements

This integration did not change claim acceptance, targeted repair, or final composition rules. The earlier source-ID numeric correction and ontology audit remain active. The new provisional tier is excluded from scientific graph assertion and normal documentary generation, preventing team-normalized values from becoming NASA-confirmed claims. Remaining false rejection and false acceptance rates require source-level adjudication.

## 12. Final conversational quality

The previous four-case paired pilot remained incomplete and is not re-labelled as a pass. The [HTTP smoke receipt](../artifacts/scientific_engine_integration_20261109/http-smoke-v15.json) demonstrates a real TCP, credential-free scientific chat response on v15; it is not a graded English research conversation. No new complete conversational quality percentage is claimed.

## 13. Document-OOS and investigation-OOS results

The [prospective holdout declaration](../evals/scientific_engine_holdout_20261109.json) preceded new original-table mapping. The same generic acquisition/importer indexed **87** CFI, **2** DAFT, and **469** SPICE original rows. All **5,101** checked cells round-tripped to the original PSI files. These rows remain documentary, with **0** new factual RDF row mappings. Their team-processed summaries were already in the repository, so this is a limited original-document ingestion check, not an independently unseen scientific extraction or answer success rate. These sources are now exposed and cannot serve as a fresh final holdout.

## 14. Nemotron and Sonnet status

Nemotron remains the default provider, Sonnet remains configurable. The previous equal-package pilot found complementary generation behavior but no final-answer advantage. No new paid generation comparison was made because the deterministic corpus and retrieval work had to be checked first.

## 15. API usage and cost

This assignment made **0** paid Sonnet calls and **0** paid NVIDIA generation or embedding calls; incremental model cost is **USD 0**. Official PSI table acquisition used public source endpoints. Previous Sonnet usage and its estimated cost remain in `artifacts/scientific_engine_stabilization_v1/sonnet-cost.json` and are not charged to this run.

## 16. Technical regression

The v15 snapshot ID is `9bd8f3e896c6ed00c6271b8c17946456c0335af0889fb0d5fb7926a011a4c7c3`. Snapshot input and artifact verification, graph provenance, SHACL, Ruff, and a real TCP offline HTTP smoke passed. The [final controlled regression receipt](../artifacts/scientific_engine_integration_20261109/test-batches-v15/results.json) records **3,591 passed, 40 existing skips, zero failures** in 11 batches; its historical SQLite checksum is unchanged. Six focused source-header and unit tests passed on v15. `uv sync --locked --offline` resolved 81 packages and checked 77 installed packages. Earlier interrupted batch receipts are retained as development diagnostics and are not counted as the final regression.

Reproduce with:

```bash
uv run python scripts/search_science.py build --snapshot data/snapshots/hackathon-20261109-v15
uv run python scripts/search_science.py verify --snapshot data/snapshots/hackathon-20261109-v15
uv run python scripts/report_psi_coverage.py --snapshot data/snapshots/hackathon-20261109-v15 --output /tmp/psi-coverage-new.json
uv run python scripts/verify_expanded_snapshot.py --snapshot data/snapshots/hackathon-20261109-v15 --output /tmp/psi-graph-new.json
uv run python scripts/evaluate_retrieval_channels.py --snapshot data/snapshots/hackathon-20261109-v15 --output /tmp/psi-channels-new.json
uv run python scripts/test_batches.py --output /tmp/psi-tests-new
uv run ruff check src scripts tests
```

## 17. Dashboard integration readiness

The existing `/api/v1/search`, `/api/v1/chat`, source and evidence endpoints remain. The default API snapshot is v15. Search results distinguish DIRECT/RELATED, original documentary evidence, catalogue discovery, and provisional processed discovery by source depth and explicit text. The dashboard must present provisional rows as exploratory material. Citation endpoints continue to resolve registry IDs; source URLs for team-processed rows are absent because those rows are not NASA originals.

## 18. Remaining blockers and exact causes

1. No snapshot-wide vector index or vector ablation: the older index metadata has no local vector files, so the full hybrid gate is unproven.
2. Nine original tables are searchable but lack validated experimental/session RDF mapping; five campaigns have catalogue-only coverage.
3. No independent, source-inspected final-answer or proposition-communication acceptance campaign on v15; the 85% quality gates remain open.
4. The held-out importer check established source provenance, not OOS scientific relationship extraction or explanation.
5. The earlier verifier's faithful-paraphrase rejection and possible source-alignment false acceptance remain unquantified after this expansion.
6. Exact reported run labels in the newly mapped ACME tables are present in RDF but are not yet resolved as query identity constraints by the conversational interpreter; sample-level DIRECT queryability needs a general source-local identifier resolver.

## 19. Git commits and worktree status

Implementation, original-source additions, tests, and receipts were committed locally as `37ce0cb` on `NASA_hackathon`. The final 11-batch regression passed before commit. This report amendment records the commit in a separate local documentation commit. No push or merge occurred; the final worktree status is checked in the handoff response.
