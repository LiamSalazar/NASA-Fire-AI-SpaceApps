# Actual autonomous-service scientific answers

Source support and experimental attribution remain subject to the limits in the final report. These are actual final primary-registry service outputs; frozen comparisons remain in v7 receipts.

## A. What did NASA observe about PMMA combustion?

Observations (DIRECT): Sequence of top views showing radiative quenching when flow velocity goes below 2 cm/s. Flame nearing blow off extinction as the flow velocity crosses 40 cm/s. [E-context-90f697823c2ba1b2ea82, E-context-e6623c40985279bec3b2, E-context-5227141f2aaa7feb2e37]

Applicable hasMaterial: PMMA (MATCH).

Applicable hasGravityCondition: microgravity (VERIFIED_APPLICABLE_CONTEXT).

Observations (DIRECT): There is a downward trend in flame spread rate as sample diameter increases for both the 1g and μg (microgravity) tests. 1g tests have higher flame spread rates than μg. 1g Black Flame Spread Rate [cm/sec] Flame spread rate as a function of sample diameter for both 1g and μg tests. 1g tests are in natural convection at 21% oxygen environments. Values for μg tests are averaged over flow velocity and oxygen concentration. [E-context-d0e9f6c262d92e57e3bd, E-context-87d3a70a788ae398fe4a, E-context-5227141f2aaa7feb2e37]

Applicable hasMaterial: PMMA (MATCH).

Applicable hasGravityCondition: microgravity (VERIFIED_APPLICABLE_CONTEXT).

The same quoted statement also belongs to context:bass-ground-rod-observation (DIRECT); its applicable context follows.

Applicable hasMaterial: PMMA (MATCH).

Applicable hasGravityCondition: normal-gravity (VERIFIED_APPLICABLE_CONTEXT).

Observations (DIRECT): The fire didn’t extinguish and began to grow when we turned the flow back on [E-context-d1e50788b120206316a0, E-context-80d7fc00aae08504c315]

Applicable hasMaterial: PMMA (MATCH).

Microgravity is a presentation preference, not an experimental fact or an added mandatory condition.

Full records, source passages and applicability traces remain available in the EvidenceBundle and Evidence Registry.

```json
{
  "intent": {
    "schema_version": "query-intent-v2",
    "operation": "SEARCH",
    "targets": [
      "ExperimentalRun"
    ],
    "entity_constraints": [
      {
        "relation": "hasMaterial",
        "entity_id": "PMMA"
      }
    ],
    "property_constraints": [],
    "requested_information": [
      "ReportedObservation"
    ],
    "comparison": null,
    "source_constraints": [],
    "unresolved_mentions": [],
    "conversation_reference": null,
    "clarification_required": false,
    "ambiguities": []
  },
  "investigation": {
    "question": "What did NASA observe about PMMA combustion?",
    "intent": {
      "schema_version": "query-intent-v2",
      "operation": "SEARCH",
      "targets": [
        "ExperimentalRun"
      ],
      "entity_constraints": [
        {
          "relation": "hasMaterial",
          "entity_id": "PMMA"
        }
      ],
      "property_constraints": [],
      "requested_information": [
        "ReportedObservation"
      ],
      "comparison": null,
      "source_constraints": [],
      "unresolved_mentions": [],
      "conversation_reference": null,
      "clarification_required": false,
      "ambiguities": []
    },
    "requirements": [
      "ReportedObservation"
    ],
    "explicit_constraints": [
      {
        "relation": "hasMaterial",
        "entity_id": "PMMA"
      }
    ],
    "domain_preferences": [
      "microgravity"
    ],
    "budget": {
      "max_rounds": 3,
      "max_actions": 8,
      "max_candidates": 8,
      "timeout_seconds": 30.0,
      "max_model_calls": 2,
      "max_model_tokens": 8000
    },
    "completed_actions": [],
    "rejected_actions": [],
    "model_calls": [],
    "rounds": 1,
    "initial_coverage": {
      "items": [
        {
          "requirement": "ReportedObservation",
          "status": "SUPPORTED",
          "evidence_ids": [
            "E-context-5227141f2aaa7feb2e37",
            "E-context-80d7fc00aae08504c315",
            "E-context-87d3a70a788ae398fe4a",
            "E-context-90f697823c2ba1b2ea82",
            "E-context-d0e9f6c262d92e57e3bd",
            "E-context-d1e50788b120206316a0",
            "E-context-e6623c40985279bec3b2"
          ],
          "reason": "Exact source-backed requested items; scientific applicability SUPPORTED"
        }
      ],
      "sufficient": true,
      "independent_scientific_precision": "NOT_MEASURABLE"
    },
    "final_coverage": {
      "items": [
        {
          "requirement": "ReportedObservation",
          "status": "SUPPORTED",
          "evidence_ids": [
            "E-context-5227141f2aaa7feb2e37",
            "E-context-80d7fc00aae08504c315",
            "E-context-87d3a70a788ae398fe4a",
            "E-context-90f697823c2ba1b2ea82",
            "E-context-d0e9f6c262d92e57e3bd",
            "E-context-d1e50788b120206316a0",
            "E-context-e6623c40985279bec3b2"
          ],
          "reason": "Exact source-backed requested items; scientific applicability SUPPORTED"
        }
      ],
      "sufficient": true,
      "independent_scientific_precision": "NOT_MEASURABLE"
    },
    "missing_information": [],
    "final_decision": "ANSWER",
    "latency_ms": 0.7691229984629899,
    "remaining_budget": {
      "actions": 8,
      "rounds": 2,
      "seconds": 29.999230877001537
    },
    "receipt_id": "e833f3a06664b89c5e78"
  }
}
```

## B. What did NASA observe about PMMA combustion under microgravity?

Observations (DIRECT): Sequence of top views showing radiative quenching when flow velocity goes below 2 cm/s. Flame nearing blow off extinction as the flow velocity crosses 40 cm/s. [E-context-90f697823c2ba1b2ea82, E-context-e6623c40985279bec3b2, E-context-5227141f2aaa7feb2e37]

Applicable hasMaterial: PMMA (MATCH).

Applicable hasGravityCondition: microgravity (MATCH).

Observations (DIRECT): There is a downward trend in flame spread rate as sample diameter increases for both the 1g and μg (microgravity) tests. 1g tests have higher flame spread rates than μg. 1g Black Flame Spread Rate [cm/sec] Flame spread rate as a function of sample diameter for both 1g and μg tests. 1g tests are in natural convection at 21% oxygen environments. Values for μg tests are averaged over flow velocity and oxygen concentration. [E-context-d0e9f6c262d92e57e3bd, E-context-87d3a70a788ae398fe4a, E-context-5227141f2aaa7feb2e37]

Applicable hasMaterial: PMMA (MATCH).

Applicable hasGravityCondition: microgravity (MATCH).

The same quoted statement also belongs to context:bass-ground-rod-observation (RELATED); its applicable context follows.

Applicable hasMaterial: PMMA (MATCH).

Applicable hasGravityCondition: normal-gravity (DIFFER).

Observations (RELATED): The fire didn’t extinguish and began to grow when we turned the flow back on [E-context-d1e50788b120206316a0, E-context-80d7fc00aae08504c315]

Applicable hasMaterial: PMMA (MATCH).

Applicable hasGravityCondition: unknown (UNKNOWN).

Observations (RELATED): Results were convincing although rather anticlimactic as none of the silicone samples burned. When the igniter was powered off, a tiny gas phase flame remained but did not spread and quickly extinguished. The igniters all appeared to function normally and the materials were clearly damaged in the vicinities of the igniters. [E-context-d86d030e275ce04b8b82, E-context-ec300b3756c4bd69021b]

Applicable hasMaterial: context:silicone-material (DIFFER).

Applicable hasGravityCondition: microgravity (MATCH).

Observations (RELATED): In upward-burning, normal-gravity tests, these three thicknesses spanned the flammability limits from significant burn, to partial burn, to no burn. ‒ The 0.27-mm thick samples were almost always completely consumed ‒ The 0.61-mm thickness burned on average 7.6 cm of the available 30 cm before extinguishing ‒ The 1.03-mm thickness would not burn at all. Downward burning silicone sample (2-4) was 0.37 mm thick. In downward burning, normal gravity tests, this thickness was completely consumed. The next higher thickness tested (0.61 mm) would not burn. [E-context-a79df97c23d629116824]

Applicable hasMaterial: context:silicone-material (DIFFER).

Applicable hasGravityCondition: normal-gravity (DIFFER).

Related evidence: 4 additional records differ in requested conditions or address a related question; they are not equivalent experiments.

Pending scientific review (ReportedObservation, scope UNRESOLVED_CURRENT_OR_CITED_STUDY): “There is no record of the venting rate used in the evaluation or the pressure where extinguishment was achieved, however it was observed that there was a substantial difference between the slow flame spread under quiescent conditions and the rapid flame spread that was observed during depressurization venting.” [E-auto-6f9591242c3f9382d799df2f]. Experimental attribution and publication remain unapproved.

Full records, source passages and applicability traces remain available in the EvidenceBundle and Evidence Registry.

```json
{
  "intent": {
    "schema_version": "query-intent-v2",
    "operation": "SEARCH",
    "targets": [
      "ExperimentalRun"
    ],
    "entity_constraints": [
      {
        "relation": "hasMaterial",
        "entity_id": "PMMA"
      },
      {
        "relation": "hasGravityCondition",
        "entity_id": "microgravity"
      }
    ],
    "property_constraints": [],
    "requested_information": [
      "ReportedObservation"
    ],
    "comparison": null,
    "source_constraints": [],
    "unresolved_mentions": [],
    "conversation_reference": null,
    "clarification_required": false,
    "ambiguities": []
  },
  "investigation": {
    "question": "What did NASA observe about PMMA combustion under microgravity?",
    "intent": {
      "schema_version": "query-intent-v2",
      "operation": "SEARCH",
      "targets": [
        "ExperimentalRun"
      ],
      "entity_constraints": [
        {
          "relation": "hasMaterial",
          "entity_id": "PMMA"
        },
        {
          "relation": "hasGravityCondition",
          "entity_id": "microgravity"
        }
      ],
      "property_constraints": [],
      "requested_information": [
        "ReportedObservation"
      ],
      "comparison": null,
      "source_constraints": [],
      "unresolved_mentions": [],
      "conversation_reference": null,
      "clarification_required": false,
      "ambiguities": []
    },
    "requirements": [
      "ReportedObservation"
    ],
    "explicit_constraints": [
      {
        "relation": "hasMaterial",
        "entity_id": "PMMA"
      },
      {
        "relation": "hasGravityCondition",
        "entity_id": "microgravity"
      }
    ],
    "domain_preferences": [],
    "budget": {
      "max_rounds": 3,
      "max_actions": 8,
      "max_candidates": 8,
      "timeout_seconds": 30.0,
      "max_model_calls": 2,
      "max_model_tokens": 8000
    },
    "completed_actions": [],
    "rejected_actions": [],
    "model_calls": [],
    "rounds": 1,
    "initial_coverage": {
      "items": [
        {
          "requirement": "ReportedObservation",
          "status": "SUPPORTED",
          "evidence_ids": [
            "E-context-5227141f2aaa7feb2e37",
            "E-context-87d3a70a788ae398fe4a",
            "E-context-90f697823c2ba1b2ea82",
            "E-context-d0e9f6c262d92e57e3bd",
            "E-context-e6623c40985279bec3b2"
          ],
          "reason": "Exact source-backed requested items; scientific applicability SUPPORTED"
        }
      ],
      "sufficient": true,
      "independent_scientific_precision": "NOT_MEASURABLE"
    },
    "final_coverage": {
      "items": [
        {
          "requirement": "ReportedObservation",
          "status": "SUPPORTED",
          "evidence_ids": [
            "E-context-5227141f2aaa7feb2e37",
            "E-context-87d3a70a788ae398fe4a",
            "E-context-90f697823c2ba1b2ea82",
            "E-context-d0e9f6c262d92e57e3bd",
            "E-context-e6623c40985279bec3b2"
          ],
          "reason": "Exact source-backed requested items; scientific applicability SUPPORTED"
        }
      ],
      "sufficient": true,
      "independent_scientific_precision": "NOT_MEASURABLE"
    },
    "missing_information": [],
    "final_decision": "ANSWER",
    "latency_ms": 0.7034350128378719,
    "remaining_budget": {
      "actions": 8,
      "rounds": 2,
      "seconds": 29.999296564987162
    },
    "receipt_id": "bfd073bbd26daf8b9fdd"
  }
}
```

## C. Does acrylic mean PMMA?

The retrieved documentation does not establish that these terms are fully equivalent.

Approved registry terminology: PMMA (PMMA). This is a vocabulary lookup, not a scientific equivalence claim.

Source terminology: “Fuel: acrylic cylinders (PMMA)” [E-751f8e0f5230aa68].

Source terminology: “Acrylic cylinders (PMMA) and engineering materials (sheets)” [E-751f8e0f5230aa68].

Source terminology: “Thick acrylic (PMMA)” [E-751f8e0f5230aa68].

```json
{
  "intent": {
    "schema_version": "query-intent-v2",
    "operation": "EXPLAIN",
    "targets": [
      "Publication"
    ],
    "entity_constraints": [],
    "property_constraints": [],
    "requested_information": [],
    "comparison": null,
    "source_constraints": [],
    "unresolved_mentions": [],
    "conversation_reference": null,
    "clarification_required": false,
    "ambiguities": []
  },
  "investigation": {
    "question": "Does acrylic mean PMMA?",
    "intent": {
      "schema_version": "query-intent-v2",
      "operation": "EXPLAIN",
      "targets": [
        "Publication"
      ],
      "entity_constraints": [],
      "property_constraints": [],
      "requested_information": [],
      "comparison": null,
      "source_constraints": [],
      "unresolved_mentions": [],
      "conversation_reference": null,
      "clarification_required": false,
      "ambiguities": []
    },
    "requirements": [
      "ConceptualRelationship"
    ],
    "explicit_constraints": [],
    "domain_preferences": [
      "microgravity"
    ],
    "budget": {
      "max_rounds": 3,
      "max_actions": 8,
      "max_candidates": 8,
      "timeout_seconds": 30.0,
      "max_model_calls": 2,
      "max_model_tokens": 8000
    },
    "completed_actions": [
      {
        "operation": "document_search",
        "query": "acrylic pmma",
        "requirement": "ConceptualRelationship",
        "objective": "Recover original passages for unresolved information",
        "expected_evidence_type": "Publication",
        "scientific_constraints": [],
        "cost": {
          "candidate_limit": 8
        },
        "stopping_condition": "Supported requirements, exhausted alternatives or budget",
        "recovered_evidence_ids": [
          "E-751f8e0f5230aa68",
          "E-5cd2680edc32b966",
          "E-6c0e7e8d8cd6a684",
          "E-5212a18ab5fb37c1",
          "E-4cdaeb4fca2ed9bd",
          "E-0ff0dc022e415930",
          "E-9464f0ca8ca7ee4b",
          "E-b3d0c69c6415bc13"
        ],
        "coverage_before": {
          "items": [
            {
              "requirement": "ConceptualRelationship",
              "status": "PARTIALLY_SUPPORTED",
              "evidence_ids": [
                "E-0ff0dc022e415930",
                "E-2dd90ca4a289b23f",
                "E-4cdaeb4fca2ed9bd",
                "E-5212a18ab5fb37c1",
                "E-5cd2680edc32b966",
                "E-6c0e7e8d8cd6a684",
                "E-751f8e0f5230aa68",
                "E-9464f0ca8ca7ee4b",
                "E-b3d0c69c6415bc13"
              ],
              "reason": "Documentary terminology does not establish total material equivalence"
            }
          ],
          "sufficient": false,
          "independent_scientific_precision": "NOT_MEASURABLE"
        },
        "coverage_after": {
          "items": [
            {
              "requirement": "ConceptualRelationship",
              "status": "PARTIALLY_SUPPORTED",
              "evidence_ids": [
                "E-0ff0dc022e415930",
                "E-2dd90ca4a289b23f",
                "E-4cdaeb4fca2ed9bd",
                "E-5212a18ab5fb37c1",
                "E-5cd2680edc32b966",
                "E-6c0e7e8d8cd6a684",
                "E-751f8e0f5230aa68",
                "E-9464f0ca8ca7ee4b",
                "E-b3d0c69c6415bc13"
              ],
              "reason": "Documentary terminology does not establish total material equivalence"
            }
          ],
          "sufficient": false,
          "independent_scientific_precision": "NOT_MEASURABLE"
        },
        "latency_ms": 16.62360699265264
      }
    ],
    "rejected_actions": [],
    "model_calls": [],
    "rounds": 2,
    "initial_coverage": {
      "items": [
        {
          "requirement": "ConceptualRelationship",
          "status": "PARTIALLY_SUPPORTED",
          "evidence_ids": [
            "E-0ff0dc022e415930",
            "E-2dd90ca4a289b23f",
            "E-4cdaeb4fca2ed9bd",
            "E-5212a18ab5fb37c1",
            "E-5cd2680edc32b966",
            "E-6c0e7e8d8cd6a684",
            "E-751f8e0f5230aa68",
            "E-9464f0ca8ca7ee4b",
            "E-b3d0c69c6415bc13"
          ],
          "reason": "Documentary terminology does not establish total material equivalence"
        }
      ],
      "sufficient": false,
      "independent_scientific_precision": "NOT_MEASURABLE"
    },
    "final_coverage": {
      "items": [
        {
          "requirement": "ConceptualRelationship",
          "status": "PARTIALLY_SUPPORTED",
          "evidence_ids": [
            "E-0ff0dc022e415930",
            "E-2dd90ca4a289b23f",
            "E-4cdaeb4fca2ed9bd",
            "E-5212a18ab5fb37c1",
            "E-5cd2680edc32b966",
            "E-6c0e7e8d8cd6a684",
            "E-751f8e0f5230aa68",
            "E-9464f0ca8ca7ee4b",
            "E-b3d0c69c6415bc13"
          ],
          "reason": "Documentary terminology does not establish total material equivalence"
        }
      ],
      "sufficient": false,
      "independent_scientific_precision": "NOT_MEASURABLE"
    },
    "missing_information": [
      "ConceptualRelationship"
    ],
    "final_decision": "PARTIAL_ANSWER",
    "latency_ms": 18.15291098318994,
    "remaining_budget": {
      "actions": 7,
      "rounds": 1,
      "seconds": 29.98184708901681
    },
    "receipt_id": "e821ab9aef2831caf263"
  }
}
```

## D. Which NASA publications discuss depressurization as a fire suppression technique?

NASA publications recovered for this topic:

- The 3rd International Microgravity Combustion Workshop: NASA Lewis Research Center Introduction Venting, or depressurization, has been discussed as a possible technique for extinguishing fires on aircraft [1] and spacecraft [2,3]. [E-03904fe70d5640c8] https://ntrs.nasa.gov/citations/19960008386
- Risks of Depress as a Fire Suppression Technique in Spacecraft: 55th International Conference on Environmental Systems ICES-2026-18 12-16 July 2026, Rio Grande, Puerto Rico Risks of Depress as a Fire Suppression Technique in Spacecraft Toni Griego1 Amentum, Houston, TX 77058 Alfredo Juarez2 and Brent Woods3 Sierra Lobo, Las Cruces, NM 88012 Ilse Reyes4 and Susana Harper5 NASA White Sands Test Facility, Las Cruces, NM 88012 Alma Stephanie Tapia6 NASA Johnson Space Center, Houston, TX 77058 Morgan B. [E-auto-baa3c9655a747294059a349c] https://ntrs.nasa.gov/api/citations/20260003546/downloads/ICES%202026%20176%20Depress%20for%20Supress%20STRIVES_4-30.pdf
- Progress in Fire Detection and Suppression Technology for Future Space Missions: depressurization is to reach a limit of 6.9 kPa in 10 min. [E-32f96130ace46b48] https://ntrs.nasa.gov/citations/20000120278

```json
{
  "intent": {
    "schema_version": "query-intent-v2",
    "operation": "SEARCH",
    "targets": [
      "Publication"
    ],
    "entity_constraints": [],
    "property_constraints": [],
    "requested_information": [
      "Publication"
    ],
    "comparison": null,
    "source_constraints": [],
    "unresolved_mentions": [],
    "conversation_reference": null,
    "clarification_required": false,
    "ambiguities": []
  },
  "investigation": {
    "question": "Which NASA publications discuss depressurization as a fire suppression technique?",
    "intent": {
      "schema_version": "query-intent-v2",
      "operation": "SEARCH",
      "targets": [
        "Publication"
      ],
      "entity_constraints": [],
      "property_constraints": [],
      "requested_information": [
        "Publication"
      ],
      "comparison": null,
      "source_constraints": [],
      "unresolved_mentions": [],
      "conversation_reference": null,
      "clarification_required": false,
      "ambiguities": []
    },
    "requirements": [
      "Publication"
    ],
    "explicit_constraints": [],
    "domain_preferences": [
      "microgravity"
    ],
    "budget": {
      "max_rounds": 3,
      "max_actions": 8,
      "max_candidates": 8,
      "timeout_seconds": 30.0,
      "max_model_calls": 2,
      "max_model_tokens": 8000
    },
    "completed_actions": [],
    "rejected_actions": [],
    "model_calls": [],
    "rounds": 1,
    "initial_coverage": {
      "items": [
        {
          "requirement": "Publication",
          "status": "SUPPORTED",
          "evidence_ids": [
            "E-03904fe70d5640c8",
            "E-19b93c109b36ae2d",
            "E-32f96130ace46b48",
            "E-65774e32adc0c5aa",
            "E-786e80d119e742d6",
            "E-8378cb54e1efd123",
            "E-auto-6f9591242c3f9382d799df2f",
            "E-auto-baa3c9655a747294059a349c",
            "E-auto-c372fa199c3f7bd04c056c7d"
          ],
          "reason": "Publication identity and matching source passages; independent topical relevance remains reviewable"
        }
      ],
      "sufficient": true,
      "independent_scientific_precision": "NOT_MEASURABLE"
    },
    "final_coverage": {
      "items": [
        {
          "requirement": "Publication",
          "status": "SUPPORTED",
          "evidence_ids": [
            "E-03904fe70d5640c8",
            "E-19b93c109b36ae2d",
            "E-32f96130ace46b48",
            "E-65774e32adc0c5aa",
            "E-786e80d119e742d6",
            "E-8378cb54e1efd123",
            "E-auto-6f9591242c3f9382d799df2f",
            "E-auto-baa3c9655a747294059a349c",
            "E-auto-c372fa199c3f7bd04c056c7d"
          ],
          "reason": "Publication identity and matching source passages; independent topical relevance remains reviewable"
        }
      ],
      "sufficient": true,
      "independent_scientific_precision": "NOT_MEASURABLE"
    },
    "missing_information": [],
    "final_decision": "ANSWER",
    "latency_ms": 0.17447100253775716,
    "remaining_budget": {
      "actions": 8,
      "rounds": 2,
      "seconds": 29.999825528997462
    },
    "receipt_id": "48122dc06427edd8b19c"
  }
}
```

## E. Which experiments support NASA's conclusions about depressurization-based fire suppression, and under what conditions were the observations made?

Verified experimental support for the requested conclusions and conditions remains incomplete.

Related evidence: 1 additional records differ in requested conditions or address a related question; they are not equivalent experiments.

Microgravity is a presentation preference, not an experimental fact or an added mandatory condition.

Unresolved requested information: ReportedObservation, NASAConclusion, ExperimentalCondition, ObservationConclusionLink. Additional retrieval did not establish complete support.

Pending scientific review (ReportedObservation, scope UNRESOLVED_CURRENT_OR_CITED_STUDY): “The test showed that common cabin materials continue to burn down to 11% oxygen with a balance of nitrogen, meaning that achieving 11.7% O2 for Gateway would be at risk of not being an effective method of fire suppression even if implemented per the guidance provided.” [E-auto-c372fa199c3f7bd04c056c7d]. Experimental attribution and publication remain unapproved.

Pending scientific review (ReportedObservation, scope UNRESOLVED_CURRENT_OR_CITED_STUDY): “There is no record of the venting rate used in the evaluation or the pressure where extinguishment was achieved, however it was observed that there was a substantial difference between the slow flame spread under quiescent conditions and the rapid flame spread that was observed during depressurization venting.” [E-auto-6f9591242c3f9382d799df2f]. Experimental attribution and publication remain unapproved.

Full records, source passages and applicability traces remain available in the EvidenceBundle and Evidence Registry.

```json
{
  "intent": {
    "schema_version": "query-intent-v2",
    "operation": "SEARCH",
    "targets": [
      "ExperimentalRun"
    ],
    "entity_constraints": [],
    "property_constraints": [],
    "requested_information": [
      "ReportedObservation",
      "NASAConclusion"
    ],
    "comparison": null,
    "source_constraints": [],
    "unresolved_mentions": [],
    "conversation_reference": null,
    "clarification_required": false,
    "ambiguities": []
  },
  "investigation": {
    "question": "Which experiments support NASA's conclusions about depressurization-based fire suppression, and under what conditions were the observations made?",
    "intent": {
      "schema_version": "query-intent-v2",
      "operation": "SEARCH",
      "targets": [
        "ExperimentalRun"
      ],
      "entity_constraints": [],
      "property_constraints": [],
      "requested_information": [
        "ReportedObservation",
        "NASAConclusion"
      ],
      "comparison": null,
      "source_constraints": [],
      "unresolved_mentions": [],
      "conversation_reference": null,
      "clarification_required": false,
      "ambiguities": []
    },
    "requirements": [
      "ReportedObservation",
      "NASAConclusion",
      "ExperimentalCondition",
      "ObservationConclusionLink"
    ],
    "explicit_constraints": [],
    "domain_preferences": [
      "microgravity"
    ],
    "budget": {
      "max_rounds": 3,
      "max_actions": 8,
      "max_candidates": 8,
      "timeout_seconds": 30.0,
      "max_model_calls": 2,
      "max_model_tokens": 8000
    },
    "completed_actions": [
      {
        "operation": "native_search",
        "query": "depressurization-based fire suppression observation",
        "requirement": "ReportedObservation",
        "objective": "Recover missing typed evidence with original constraints",
        "expected_evidence_type": "ReportedObservation",
        "scientific_constraints": [],
        "cost": {
          "candidate_limit": 8
        },
        "stopping_condition": "Supported requirements, exhausted alternatives or budget",
        "recovered_evidence_ids": [
          "E-safety-saffire-observation",
          "E-context-80d7fc00aae08504c315",
          "E-context-d1e50788b120206316a0",
          "E-8ff460d980f636ec",
          "E-e0c3312020b853ea",
          "E-19b93c109b36ae2d",
          "E-32f96130ace46b48",
          "E-65774e32adc0c5aa",
          "E-auto-c372fa199c3f7bd04c056c7d",
          "E-8378cb54e1efd123",
          "E-ca3b8702cd899ddb",
          "E-context-3b27486ede2bf8151a2f"
        ],
        "coverage_before": {
          "items": [
            {
              "requirement": "ReportedObservation",
              "status": "MISSING",
              "evidence_ids": [],
              "reason": "No applicable source-backed item of the requested type"
            },
            {
              "requirement": "NASAConclusion",
              "status": "MISSING",
              "evidence_ids": [],
              "reason": "No applicable source-backed item of the requested type"
            },
            {
              "requirement": "ExperimentalCondition",
              "status": "MISSING",
              "evidence_ids": [],
              "reason": "No applicable source-backed item of the requested type"
            },
            {
              "requirement": "ObservationConclusionLink",
              "status": "MISSING",
              "evidence_ids": [],
              "reason": "Requires explicit reviewed attribution; co-occurrence in a publication is insufficient"
            }
          ],
          "sufficient": false,
          "independent_scientific_precision": "NOT_MEASURABLE"
        },
        "coverage_after": {
          "items": [
            {
              "requirement": "ReportedObservation",
              "status": "MISSING",
              "evidence_ids": [],
              "reason": "No applicable source-backed item of the requested type"
            },
            {
              "requirement": "NASAConclusion",
              "status": "MISSING",
              "evidence_ids": [],
              "reason": "No applicable source-backed item of the requested type"
            },
            {
              "requirement": "ExperimentalCondition",
              "status": "MISSING",
              "evidence_ids": [],
              "reason": "No applicable source-backed item of the requested type"
            },
            {
              "requirement": "ObservationConclusionLink",
              "status": "MISSING",
              "evidence_ids": [],
              "reason": "Requires explicit reviewed attribution; co-occurrence in a publication is insufficient"
            }
          ],
          "sufficient": false,
          "independent_scientific_precision": "NOT_MEASURABLE"
        },
        "latency_ms": 264.4617379992269
      },
      {
        "operation": "document_search",
        "query": "depressurization-based fire suppression",
        "requirement": "ReportedObservation",
        "objective": "Recover original passages for unresolved information",
        "expected_evidence_type": "Publication",
        "scientific_constraints": [],
        "cost": {
          "candidate_limit": 8
        },
        "stopping_condition": "Supported requirements, exhausted alternatives or budget",
        "recovered_evidence_ids": [
          "E-auto-6f9591242c3f9382d799df2f",
          "E-19b93c109b36ae2d",
          "E-32f96130ace46b48",
          "E-65774e32adc0c5aa",
          "E-auto-c372fa199c3f7bd04c056c7d",
          "E-8378cb54e1efd123",
          "E-8ff460d980f636ec",
          "E-ca3b8702cd899ddb"
        ],
        "coverage_before": {
          "items": [
            {
              "requirement": "ReportedObservation",
              "status": "MISSING",
              "evidence_ids": [],
              "reason": "No applicable source-backed item of the requested type"
            },
            {
              "requirement": "NASAConclusion",
              "status": "MISSING",
              "evidence_ids": [],
              "reason": "No applicable source-backed item of the requested type"
            },
            {
              "requirement": "ExperimentalCondition",
              "status": "MISSING",
              "evidence_ids": [],
              "reason": "No applicable source-backed item of the requested type"
            },
            {
              "requirement": "ObservationConclusionLink",
              "status": "MISSING",
              "evidence_ids": [],
              "reason": "Requires explicit reviewed attribution; co-occurrence in a publication is insufficient"
            }
          ],
          "sufficient": false,
          "independent_scientific_precision": "NOT_MEASURABLE"
        },
        "coverage_after": {
          "items": [
            {
              "requirement": "ReportedObservation",
              "status": "MISSING",
              "evidence_ids": [],
              "reason": "No applicable source-backed item of the requested type"
            },
            {
              "requirement": "NASAConclusion",
              "status": "MISSING",
              "evidence_ids": [],
              "reason": "No applicable source-backed item of the requested type"
            },
            {
              "requirement": "ExperimentalCondition",
              "status": "MISSING",
              "evidence_ids": [],
              "reason": "No applicable source-backed item of the requested type"
            },
            {
              "requirement": "ObservationConclusionLink",
              "status": "MISSING",
              "evidence_ids": [],
              "reason": "Requires explicit reviewed attribution; co-occurrence in a publication is insufficient"
            }
          ],
          "sufficient": false,
          "independent_scientific_precision": "NOT_MEASURABLE"
        },
        "latency_ms": 27.508221013704315
      }
    ],
    "rejected_actions": [],
    "model_calls": [],
    "rounds": 3,
    "initial_coverage": {
      "items": [
        {
          "requirement": "ReportedObservation",
          "status": "MISSING",
          "evidence_ids": [],
          "reason": "No applicable source-backed item of the requested type"
        },
        {
          "requirement": "NASAConclusion",
          "status": "MISSING",
          "evidence_ids": [],
          "reason": "No applicable source-backed item of the requested type"
        },
        {
          "requirement": "ExperimentalCondition",
          "status": "MISSING",
          "evidence_ids": [],
          "reason": "No applicable source-backed item of the requested type"
        },
        {
          "requirement": "ObservationConclusionLink",
          "status": "MISSING",
          "evidence_ids": [],
          "reason": "Requires explicit reviewed attribution; co-occurrence in a publication is insufficient"
        }
      ],
      "sufficient": false,
      "independent_scientific_precision": "NOT_MEASURABLE"
    },
    "final_coverage": {
      "items": [
        {
          "requirement": "ReportedObservation",
          "status": "MISSING",
          "evidence_ids": [],
          "reason": "No applicable source-backed item of the requested type"
        },
        {
          "requirement": "NASAConclusion",
          "status": "MISSING",
          "evidence_ids": [],
          "reason": "No applicable source-backed item of the requested type"
        },
        {
          "requirement": "ExperimentalCondition",
          "status": "MISSING",
          "evidence_ids": [],
          "reason": "No applicable source-backed item of the requested type"
        },
        {
          "requirement": "ObservationConclusionLink",
          "status": "MISSING",
          "evidence_ids": [],
          "reason": "Requires explicit reviewed attribution; co-occurrence in a publication is insufficient"
        }
      ],
      "sufficient": false,
      "independent_scientific_precision": "NOT_MEASURABLE"
    },
    "missing_information": [
      "ReportedObservation",
      "NASAConclusion",
      "ExperimentalCondition",
      "ObservationConclusionLink"
    ],
    "final_decision": "ABSTAIN",
    "latency_ms": 292.601172986906,
    "remaining_budget": {
      "actions": 6,
      "rounds": 0,
      "seconds": 29.707398827013094
    },
    "receipt_id": "ce026a0b56527e1c7701"
  }
}
```

## F. How do PMMA combustion observations differ between microgravity and normal gravity?

Observations (DIRECT): Sequence of top views showing radiative quenching when flow velocity goes below 2 cm/s. Flame nearing blow off extinction as the flow velocity crosses 40 cm/s. [E-context-90f697823c2ba1b2ea82, E-context-e6623c40985279bec3b2, E-context-5227141f2aaa7feb2e37]

Applicable hasMaterial: PMMA (MATCH).

Applicable hasGravityCondition: microgravity (MATCH).

Observations (DIRECT): There is a downward trend in flame spread rate as sample diameter increases for both the 1g and μg (microgravity) tests. 1g tests have higher flame spread rates than μg. 1g Black Flame Spread Rate [cm/sec] Flame spread rate as a function of sample diameter for both 1g and μg tests. 1g tests are in natural convection at 21% oxygen environments. Values for μg tests are averaged over flow velocity and oxygen concentration. [E-context-d0e9f6c262d92e57e3bd, E-context-87d3a70a788ae398fe4a, E-context-5227141f2aaa7feb2e37]

Applicable hasMaterial: PMMA (MATCH).

Applicable hasGravityCondition: microgravity (MATCH).

The same quoted statement also belongs to context:bass-ground-rod-observation (DIRECT); its applicable context follows.

Applicable hasMaterial: PMMA (MATCH).

Applicable hasGravityCondition: normal-gravity (DIFFER).

Observations (RELATED): The fire didn’t extinguish and began to grow when we turned the flow back on [E-context-d1e50788b120206316a0, E-context-80d7fc00aae08504c315]

Applicable hasMaterial: PMMA (MATCH).

Applicable hasGravityCondition: unknown (UNKNOWN).

Observations (RELATED): Results were convincing although rather anticlimactic as none of the silicone samples burned. When the igniter was powered off, a tiny gas phase flame remained but did not spread and quickly extinguished. The igniters all appeared to function normally and the materials were clearly damaged in the vicinities of the igniters. [E-context-d86d030e275ce04b8b82, E-context-ec300b3756c4bd69021b]

Applicable hasMaterial: context:silicone-material (DIFFER).

Applicable hasGravityCondition: microgravity (MATCH).

Observations (RELATED): In upward-burning, normal-gravity tests, these three thicknesses spanned the flammability limits from significant burn, to partial burn, to no burn. ‒ The 0.27-mm thick samples were almost always completely consumed ‒ The 0.61-mm thickness burned on average 7.6 cm of the available 30 cm before extinguishing ‒ The 1.03-mm thickness would not burn at all. Downward burning silicone sample (2-4) was 0.37 mm thick. In downward burning, normal gravity tests, this thickness was completely consumed. The next higher thickness tested (0.61 mm) would not burn. [E-context-a79df97c23d629116824]

Applicable hasMaterial: context:silicone-material (DIFFER).

Applicable hasGravityCondition: normal-gravity (DIFFER).

Related evidence: 6 additional records differ in requested conditions or address a related question; they are not equivalent experiments.

Pending scientific review (ReportedObservation, scope UNRESOLVED_CURRENT_OR_CITED_STUDY): “There is no record of the venting rate used in the evaluation or the pressure where extinguishment was achieved, however it was observed that there was a substantial difference between the slow flame spread under quiescent conditions and the rapid flame spread that was observed during depressurization venting.” [E-auto-6f9591242c3f9382d799df2f]. Experimental attribution and publication remain unapproved.

Full records, source passages and applicability traces remain available in the EvidenceBundle and Evidence Registry.

```json
{
  "intent": {
    "schema_version": "query-intent-v2",
    "operation": "SEARCH",
    "targets": [
      "ExperimentalRun"
    ],
    "entity_constraints": [
      {
        "relation": "hasMaterial",
        "entity_id": "PMMA"
      },
      {
        "relation": "hasGravityCondition",
        "entity_id": "microgravity"
      },
      {
        "relation": "hasGravityCondition",
        "entity_id": "normal-gravity"
      }
    ],
    "property_constraints": [],
    "requested_information": [
      "ReportedObservation"
    ],
    "comparison": null,
    "source_constraints": [],
    "unresolved_mentions": [],
    "conversation_reference": null,
    "clarification_required": false,
    "ambiguities": []
  },
  "investigation": {
    "question": "How do PMMA combustion observations differ between microgravity and normal gravity?",
    "intent": {
      "schema_version": "query-intent-v2",
      "operation": "SEARCH",
      "targets": [
        "ExperimentalRun"
      ],
      "entity_constraints": [
        {
          "relation": "hasMaterial",
          "entity_id": "PMMA"
        },
        {
          "relation": "hasGravityCondition",
          "entity_id": "microgravity"
        }
      ],
      "property_constraints": [],
      "requested_information": [
        "ReportedObservation"
      ],
      "comparison": null,
      "source_constraints": [],
      "unresolved_mentions": [],
      "conversation_reference": null,
      "clarification_required": false,
      "ambiguities": []
    },
    "requirements": [
      "ReportedObservation"
    ],
    "explicit_constraints": [
      {
        "relation": "hasMaterial",
        "entity_id": "PMMA"
      },
      {
        "relation": "hasGravityCondition",
        "entity_id": "microgravity"
      }
    ],
    "domain_preferences": [],
    "budget": {
      "max_rounds": 3,
      "max_actions": 8,
      "max_candidates": 8,
      "timeout_seconds": 30.0,
      "max_model_calls": 2,
      "max_model_tokens": 8000
    },
    "completed_actions": [],
    "rejected_actions": [],
    "model_calls": [],
    "rounds": 1,
    "initial_coverage": {
      "items": [
        {
          "requirement": "ReportedObservation",
          "status": "SUPPORTED",
          "evidence_ids": [
            "E-context-5227141f2aaa7feb2e37",
            "E-context-87d3a70a788ae398fe4a",
            "E-context-90f697823c2ba1b2ea82",
            "E-context-d0e9f6c262d92e57e3bd",
            "E-context-e6623c40985279bec3b2"
          ],
          "reason": "Exact source-backed requested items; scientific applicability SUPPORTED"
        }
      ],
      "sufficient": true,
      "independent_scientific_precision": "NOT_MEASURABLE"
    },
    "final_coverage": {
      "items": [
        {
          "requirement": "ReportedObservation",
          "status": "SUPPORTED",
          "evidence_ids": [
            "E-context-5227141f2aaa7feb2e37",
            "E-context-87d3a70a788ae398fe4a",
            "E-context-90f697823c2ba1b2ea82",
            "E-context-d0e9f6c262d92e57e3bd",
            "E-context-e6623c40985279bec3b2"
          ],
          "reason": "Exact source-backed requested items; scientific applicability SUPPORTED"
        }
      ],
      "sufficient": true,
      "independent_scientific_precision": "NOT_MEASURABLE"
    },
    "missing_information": [],
    "final_decision": "ANSWER",
    "latency_ms": 1.6572159947827458,
    "remaining_budget": {
      "actions": 8,
      "rounds": 2,
      "seconds": 29.998342784005217
    },
    "receipt_id": "24c48ef56411d7c11e53"
  }
}
```

## G. What happened when airflow was interrupted and later restored?

Observations (RELATED): Sequence of top views showing radiative quenching when flow velocity goes below 2 cm/s. Flame nearing blow off extinction as the flow velocity crosses 40 cm/s. [E-context-90f697823c2ba1b2ea82, E-context-e6623c40985279bec3b2, E-context-5227141f2aaa7feb2e37]

Applicable hasGravityCondition: microgravity (VERIFIED_APPLICABLE_CONTEXT).

Observations (RELATED): There is a downward trend in flame spread rate as sample diameter increases for both the 1g and μg (microgravity) tests. 1g tests have higher flame spread rates than μg. 1g Black Flame Spread Rate [cm/sec] Flame spread rate as a function of sample diameter for both 1g and μg tests. 1g tests are in natural convection at 21% oxygen environments. Values for μg tests are averaged over flow velocity and oxygen concentration. [E-context-d0e9f6c262d92e57e3bd, E-context-87d3a70a788ae398fe4a, E-context-5227141f2aaa7feb2e37]

Applicable hasGravityCondition: microgravity (VERIFIED_APPLICABLE_CONTEXT).

The same quoted statement also belongs to context:bass-ground-rod-observation (RELATED); its applicable context follows.

Applicable hasGravityCondition: normal-gravity (VERIFIED_APPLICABLE_CONTEXT).

Observations (DIRECT): The fire didn’t extinguish and began to grow when we turned the flow back on [E-context-d1e50788b120206316a0, E-context-80d7fc00aae08504c315]

Observations (RELATED): Results were convincing although rather anticlimactic as none of the silicone samples burned. When the igniter was powered off, a tiny gas phase flame remained but did not spread and quickly extinguished. The igniters all appeared to function normally and the materials were clearly damaged in the vicinities of the igniters. [E-context-d86d030e275ce04b8b82, E-context-ec300b3756c4bd69021b]

Applicable hasGravityCondition: microgravity (VERIFIED_APPLICABLE_CONTEXT).

Observations (DIRECT): The fire didn’t extinguish and began to grow when we turned the flow back on. [E-safety-saffire-observation]

Interventions (DIRECT): For the Saffire-IV PMMA sample, we turned off the flow for 20 seconds [E-context-3b27486ede2bf8151a2f, E-context-80d7fc00aae08504c315]

Related evidence: 4 additional records differ in requested conditions or address a related question; they are not equivalent experiments.

Microgravity is a presentation preference, not an experimental fact or an added mandatory condition.

Full records, source passages and applicability traces remain available in the EvidenceBundle and Evidence Registry.

```json
{
  "intent": {
    "schema_version": "query-intent-v2",
    "operation": "SEARCH",
    "targets": [
      "ExperimentalRun"
    ],
    "entity_constraints": [],
    "property_constraints": [],
    "requested_information": [
      "ReportedObservation",
      "Intervention"
    ],
    "comparison": null,
    "source_constraints": [],
    "unresolved_mentions": [],
    "conversation_reference": null,
    "clarification_required": false,
    "ambiguities": []
  },
  "investigation": {
    "question": "What happened when airflow was interrupted and later restored?",
    "intent": {
      "schema_version": "query-intent-v2",
      "operation": "SEARCH",
      "targets": [
        "ExperimentalRun"
      ],
      "entity_constraints": [],
      "property_constraints": [],
      "requested_information": [
        "ReportedObservation",
        "Intervention"
      ],
      "comparison": null,
      "source_constraints": [],
      "unresolved_mentions": [],
      "conversation_reference": null,
      "clarification_required": false,
      "ambiguities": []
    },
    "requirements": [
      "ReportedObservation",
      "Intervention"
    ],
    "explicit_constraints": [],
    "domain_preferences": [
      "microgravity"
    ],
    "budget": {
      "max_rounds": 3,
      "max_actions": 8,
      "max_candidates": 8,
      "timeout_seconds": 30.0,
      "max_model_calls": 2,
      "max_model_tokens": 8000
    },
    "completed_actions": [],
    "rejected_actions": [],
    "model_calls": [],
    "rounds": 1,
    "initial_coverage": {
      "items": [
        {
          "requirement": "ReportedObservation",
          "status": "SUPPORTED",
          "evidence_ids": [
            "E-context-80d7fc00aae08504c315",
            "E-context-d1e50788b120206316a0",
            "E-safety-saffire-observation"
          ],
          "reason": "Exact source-backed requested items; scientific applicability SUPPORTED"
        },
        {
          "requirement": "Intervention",
          "status": "SUPPORTED",
          "evidence_ids": [
            "E-context-3b27486ede2bf8151a2f",
            "E-context-80d7fc00aae08504c315"
          ],
          "reason": "Exact source-backed requested items; scientific applicability SUPPORTED"
        }
      ],
      "sufficient": true,
      "independent_scientific_precision": "NOT_MEASURABLE"
    },
    "final_coverage": {
      "items": [
        {
          "requirement": "ReportedObservation",
          "status": "SUPPORTED",
          "evidence_ids": [
            "E-context-80d7fc00aae08504c315",
            "E-context-d1e50788b120206316a0",
            "E-safety-saffire-observation"
          ],
          "reason": "Exact source-backed requested items; scientific applicability SUPPORTED"
        },
        {
          "requirement": "Intervention",
          "status": "SUPPORTED",
          "evidence_ids": [
            "E-context-3b27486ede2bf8151a2f",
            "E-context-80d7fc00aae08504c315"
          ],
          "reason": "Exact source-backed requested items; scientific applicability SUPPORTED"
        }
      ],
      "sufficient": true,
      "independent_scientific_precision": "NOT_MEASURABLE"
    },
    "missing_information": [],
    "final_decision": "ANSWER",
    "latency_ms": 0.9576639859005809,
    "remaining_budget": {
      "actions": 8,
      "rounds": 2,
      "seconds": 29.9990423360141
    },
    "receipt_id": "7d1820c1590a4829c602"
  }
}
```

## H. What questions about fire suppression remain unresolved in the NASA literature?

Explicit research questions (DIRECT): For a fixed fire suppression system in a compartment, what suppressant concentration must be reached and how long must it be held there? [E-context-9df40cae8e6f693c2466, E-context-80d7fc00aae08504c315]

Microgravity is a presentation preference, not an experimental fact or an added mandatory condition.

Pending scientific review (ReportedObservation, scope UNRESOLVED_CURRENT_OR_CITED_STUDY): “The test showed that common cabin materials continue to burn down to 11% oxygen with a balance of nitrogen, meaning that achieving 11.7% O2 for Gateway would be at risk of not being an effective method of fire suppression even if implemented per the guidance provided.” [E-auto-c372fa199c3f7bd04c056c7d]. Experimental attribution and publication remain unapproved.

Pending scientific review (NASAConclusion, scope current study): “Based on this data, depressurization as a method of fire suppression in spacecraft is highly discouraged.” [E-auto-133c1547dc205949f6a4f4c2]. Experimental attribution and publication remain unapproved.

Full records, source passages and applicability traces remain available in the EvidenceBundle and Evidence Registry.

```json
{
  "intent": {
    "schema_version": "query-intent-v2",
    "operation": "SEARCH",
    "targets": [
      "ExperimentalRun"
    ],
    "entity_constraints": [],
    "property_constraints": [],
    "requested_information": [],
    "comparison": null,
    "source_constraints": [],
    "unresolved_mentions": [],
    "conversation_reference": null,
    "clarification_required": false,
    "ambiguities": []
  },
  "investigation": {
    "question": "What questions about fire suppression remain unresolved in the NASA literature?",
    "intent": {
      "schema_version": "query-intent-v2",
      "operation": "SEARCH",
      "targets": [
        "ExperimentalRun"
      ],
      "entity_constraints": [],
      "property_constraints": [],
      "requested_information": [],
      "comparison": null,
      "source_constraints": [],
      "unresolved_mentions": [],
      "conversation_reference": null,
      "clarification_required": false,
      "ambiguities": []
    },
    "requirements": [
      "OpenQuestion"
    ],
    "explicit_constraints": [],
    "domain_preferences": [
      "microgravity"
    ],
    "budget": {
      "max_rounds": 3,
      "max_actions": 8,
      "max_candidates": 8,
      "timeout_seconds": 30.0,
      "max_model_calls": 2,
      "max_model_tokens": 8000
    },
    "completed_actions": [
      {
        "operation": "native_search",
        "query": "questions fire suppression remain unresolved literature open questions",
        "requirement": "OpenQuestion",
        "objective": "Recover missing typed evidence with original constraints",
        "expected_evidence_type": "OpenQuestion",
        "scientific_constraints": [],
        "cost": {
          "candidate_limit": 8
        },
        "stopping_condition": "Supported requirements, exhausted alternatives or budget",
        "recovered_evidence_ids": [
          "E-context-80d7fc00aae08504c315",
          "E-context-9df40cae8e6f693c2466",
          "E-72d8a9c524f0bd61",
          "E-733d1e5d0226dbe6",
          "E-d41a6b2ee0c8e9d3",
          "E-1dcaee47bb8f564b",
          "E-f9c9d6f3bd3183e2",
          "E-340c188ebb1369fb",
          "E-afcda2a09d83ed04",
          "E-ac77e9cbeb211127",
          "E-safety-saffire-suppression-open-question"
        ],
        "coverage_before": {
          "items": [
            {
              "requirement": "OpenQuestion",
              "status": "MISSING",
              "evidence_ids": [],
              "reason": "No applicable source-backed item of the requested type"
            }
          ],
          "sufficient": false,
          "independent_scientific_precision": "NOT_MEASURABLE"
        },
        "coverage_after": {
          "items": [
            {
              "requirement": "OpenQuestion",
              "status": "SUPPORTED",
              "evidence_ids": [
                "E-context-80d7fc00aae08504c315",
                "E-context-9df40cae8e6f693c2466"
              ],
              "reason": "Exact source-backed requested items; scientific applicability SUPPORTED"
            }
          ],
          "sufficient": true,
          "independent_scientific_precision": "NOT_MEASURABLE"
        },
        "latency_ms": 397.3002719867509
      }
    ],
    "rejected_actions": [],
    "model_calls": [],
    "rounds": 2,
    "initial_coverage": {
      "items": [
        {
          "requirement": "OpenQuestion",
          "status": "MISSING",
          "evidence_ids": [],
          "reason": "No applicable source-backed item of the requested type"
        }
      ],
      "sufficient": false,
      "independent_scientific_precision": "NOT_MEASURABLE"
    },
    "final_coverage": {
      "items": [
        {
          "requirement": "OpenQuestion",
          "status": "SUPPORTED",
          "evidence_ids": [
            "E-context-80d7fc00aae08504c315",
            "E-context-9df40cae8e6f693c2466"
          ],
          "reason": "Exact source-backed requested items; scientific applicability SUPPORTED"
        }
      ],
      "sufficient": true,
      "independent_scientific_precision": "NOT_MEASURABLE"
    },
    "missing_information": [],
    "final_decision": "ANSWER",
    "latency_ms": 397.4295319931116,
    "remaining_budget": {
      "actions": 7,
      "rounds": 1,
      "seconds": 29.60257046800689
    },
    "receipt_id": "adb9624589551ea51645"
  }
}
```
