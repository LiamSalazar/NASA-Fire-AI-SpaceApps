# Phase 3 repair results

## Before repair

- Query schema valid: 33/50; invalid/fallback: 17/50 (.3400); median/max 4171.9/15833.8 ms.
- Synthesis valid: 0/10; fallback: 10/10.
- Unsafe visible scientific prose: 0.

## Repair implemented

The query adapter now requests `text|type` raw mentions rather than nested entity objects, canonical IDs, statuses, and values. Deterministic validation resolves canonical entities and rejects unsupported semantics. The synthesis adapter requests only text and evidence IDs; `GroundingValidator` reconstructs metadata from the current EvidenceBundle before enforcing its whitelist and epistemic rules.

A minimal live smoke request after repair produced a valid deterministic interpretation for `PMMA in microgravity`: PMMA material and microgravity were resolved through the existing lexicon. This is a smoke result, not a replacement for the full rerun.

## Closure status

An unreviewed deterministic candidate-gold and review queue now exist. Human/domain promotion to reviewed/frozen labels and the final live benchmark remain required before Phase-3 closure. `READY_FOR_PHASE_4 = NO`.
