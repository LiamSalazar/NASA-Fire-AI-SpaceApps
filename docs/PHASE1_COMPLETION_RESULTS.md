# Phase-1 completion assessment

## Executive assessment

The corpus now includes BASS-II, SAFFIRE-I, FLEX, SoFIE, spacecraft-fire-safety evidence, and NASA-STD-6001. FLEX and SoFIE were acquired from official NTRS PDFs; FLEX was processed as a genuine unseen family first pass without a FLEX semantic rule. NVIDIA Nemotron executed candidate-only extraction on real NASA text. The extraction audit showed meaningful safety-classification ambiguity, which was preserved in the review queue rather than published as science.

## Executed additions

- FLEX / NTRS 20150023456: official 40.9 MiB PDF, 317 first-pass passages; liquid-droplet documentary coverage.
- SoFIE / NTRS 20200000361: official 2.8 MiB PDF, documentary coverage for recent ISS solid-fuel work.
- Two evidence-backed publication identities were incrementally added; no documentary prose was promoted to a scientific conclusion.
- NVIDIA model executed: `nvidia/nemotron-3.5-lightning-30b-a3b`.

## Extraction and holdout

Six cached live extraction calls yielded 23 exact-span candidates: 3 low-risk candidates validated and 20 high-risk candidates were routed to review. No candidate bypassed validation or mutated ontology vocabulary. FLEX first pass found liquid-droplet terminology but published no unstructured experimental run; this is correct because no structured table was used and narrative values were not inferred. See the dedicated holdout and extraction reports.

## Final measured state

- Canonical entities/RDF triples: 928 / 5,776.
- Runs: 131; structured BASS-II rows: 129.
- Evidence Registry sources/documents: 8 / 10.
- Indexed passages: 923 before final FTS duplicate remediation; FTS identity remediation is documented as an implementation limitation and must be rerun before declaring operational index counts final.
- Candidate records: 152 total; 132 validated, 20 review-required, 0 rejected.
- Review queue: 20 pending.
- SHACL: conformant at the last graph build.

## Incremental behavior

FLEX was re-ingested unchanged after its first pass and did not create a second publication identity (`published_documents: 0`). The run exposed a duplicate FTS passage identity issue caused by non-deterministic PDF text extraction; the stable evidence-ID rule was changed from text-derived to document/page/offset-derived. Raw source files were not changed.

## Ready decision

`READY_FOR_PHASE_2 = NO`.

The architecture is now demonstrated across distinct families and live LLM extraction, but Phase 1 cannot honestly be closed until the FTS duplicate remediation is executed and verified after the stable-ID change, and the 20 live high-risk candidates receive human review. The result is intentionally conservative: it does not turn an extractor's safety labels into NASA knowledge.
