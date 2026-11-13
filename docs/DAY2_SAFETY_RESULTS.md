# Day-2 safety knowledge results

## Official evidence ingested

- NTRS 20205007829, *Spacecraft Fire Safety Needs for Exploration* (pages 7 and 16).
- NTRS 20150020937, *Flammability Configuration Analysis for Spacecraft Applications* (pages 1 and 2).
- NASA-STD-6001B w/CHANGE 3, *Flammability, Offgassing, and Compatibility Requirements and Test Procedures* (current official PDF, pages 8 and 17).

Every curated statement has a dedicated Evidence Registry passage containing its exact selected source text, source document ID, page, section, checksum/raw reference where applicable, and evidence ID.

## Curated semantic records

| Type | Count | Explicitly modeled example |
| --- | ---: | --- |
| Experimental intervention | 1 | Saffire-IV PMMA: flow turned off for 20 seconds |
| Experimental observation | 1 | Fire did not extinguish and grew after flow resumed |
| NASA conclusion | 1 | Suppressant may not have been held at desired concentration long enough for surface cooling |
| Safety implication | 1 | Active suppression may need activation if fire propagates despite detection/initial response |
| Requirement | 1 | NASA-STD-6001 applicability requirement |
| Guidance | 1 | Payload flammability-assessment guidance |
| Design criterion | 1 | Control quantity/configuration to eliminate propagation paths |
| Test criterion | 1 | Required testing at worst-case exposure and representative form |
| NASA-identified open question | 1 | Additional focused testing may be required to develop suppression guidance |

The Saffire evidence is connected at the investigation/documented-experiment-context level (`psi-98`), not to a fabricated Saffire-IV run. The observation is linked as support for the NASA conclusion. The observed non-extinction was not transformed into guidance.

## Verification

- Canonical entities: 48
- RDF triples: 349
- Evidence coverage for Day-2 curated records: 9/9
- SHACL: conformant
- Pytest: `18 passed`
- Ruff: clean

## Deterministic query demonstration

`scripts/demo_safety_queries.py` returns requirements, guidance, suppression-related information, PMMA/investigation-context information, explicit open questions, and the observation linked to the safety conclusion. It also explicitly demonstrates both:

1. direct experimental evidence plus the distinct NASA-identified suppression open question; and
2. `NO_DIRECT_EVIDENCE` with no open question created.

## Intentionally unmodeled ambiguity

The presentation does not identify a PSI-98/Saffire-I table run for the Saffire-IV PMMA demonstration, so no run ID is asserted. The phrase that a suppressant *could* have been used is represented as NASA conclusion text with its scope, not as a universal requirement or recommendation. No general-purpose automatic statement classifier was added.

## Next highest-value step

Add an expert-reviewed source-annotation workflow that records selected passage offsets and links requirements to their applicability/tailoring context, before expanding the curated statement set.
