# Phase 3 grounded synthesis

The NVIDIA-compatible synthesizer is separated from query interpretation and accepts an `EvidenceBundle` only. Its prompt states that pretrained knowledge is not evidence and delimitates evidence as data. It emits `GroundedAnswerDraft` before rendering.

Every scientific draft claim requires evidence IDs. The deterministic validator requires IDs to be in the bundle and checks direct/related, open-question, authority, and requirement/guidance metadata. A rejected, unavailable, malformed, or unconfigured synthesis request falls back to the extractive renderer. The renderer adds no scientific content.
