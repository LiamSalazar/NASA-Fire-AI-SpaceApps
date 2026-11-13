# Actual scientist-facing V2 results

Same frozen source snapshot; candidate budget 8, documentary pool 32.

```json
{
  "configurations": {
    "A": {
      "questions": 18,
      "with_direct": 4,
      "selected_claims": 0,
      "citation_valid_answers": 18,
      "mean_words": 3306.9444444444443,
      "scientific_precision": null,
      "independent_judgments": 0
    },
    "B": {
      "questions": 18,
      "with_direct": 4,
      "selected_claims": 59,
      "citation_valid_answers": 18,
      "mean_words": 86.61111111111111,
      "scientific_precision": null,
      "independent_judgments": 0
    },
    "C": {
      "questions": 18,
      "with_direct": 14,
      "selected_claims": 91,
      "citation_valid_answers": 18,
      "mean_words": 167.38888888888889,
      "scientific_precision": null,
      "independent_judgments": 0
    },
    "D": {
      "questions": 18,
      "with_direct": 14,
      "selected_claims": 88,
      "citation_valid_answers": 18,
      "mean_words": 159.94444444444446,
      "scientific_precision": null,
      "independent_judgments": 0
    }
  },
  "E": "Vector retrieval evaluated separately; not adopted into native classification",
  "F": "Not enabled; incremental scientific benefit unreviewed"
}
```

These counts measure technical DIRECT coverage, not independently reviewed answer correctness. Current final rollback/source-filter fixes are separately regression-tested; the v4 benchmark receipt records the synthesis implementation at execution time.

## What did NASA observe about PMMA combustion?

Baseline: 48 words; integrated: 198 words.

QueryIntentV2: `{"schema_version":"query-intent-v2","operation":"SEARCH","targets":["ExperimentalRun"],"entity_constraints":[{"relation":"hasMaterial","entity_id":"PMMA"}],"property_constraints":[],"requested_information":["ReportedObservation"],"comparison":null,"source_constraints":[],"unresolved_mentions":[],"conversation_reference":null,"clarification_required":false,"ambiguities":[]}`.

Classification: 4 DIRECT and 0 RELATED identities. Sources: E-context-5227141f2aaa7feb2e37, E-context-80d7fc00aae08504c315, E-context-3b27486ede2bf8151a2f, E-context-e6623c40985279bec3b2, E-context-87d3a70a788ae398fe4a, E-13fb7f02cdca2f8a, E-1f129c9ecb7f6b59, E-4084124e9dc2a202, E-08c3327bddbeb4ae, E-4ee1d5c251e70899, E-69974633ab0fed54, E-a01be685f4e205f1, E-cf90bf6996c63f80, E-context-90f697823c2ba1b2ea82, E-context-d0e9f6c262d92e57e3bd, E-context-d1e50788b120206316a0.

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

Support and applicable path (full exact spans remain in the case receipt):

```json
{
  "claim_id": "claim-e92a6bedbd1b7d4b",
  "evidence_ids": [
    "E-context-90f697823c2ba1b2ea82",
    "E-context-e6623c40985279bec3b2",
    "E-context-5227141f2aaa7feb2e37"
  ],
  "graph_paths": [
    {
      "statement_id": "material-context:bass-film-observation",
      "membership_paths": {
        "context:bass-film-observation": [
          {
            "from": "context:bass-film-observation",
            "to": "context:bass-film-series",
            "relation": "concerns",
            "basis": "EXPLICIT_SOURCE_IDENTITY",
            "support_spans": [
              {
                "evidence_id": "E-context-90f697823c2ba1b2ea82",
                "text": "Sequence of top views showing radiative quenching when\nflow velocity goes below 2 cm/s.\n\nFlame nearing blow off extinction as the flow\nvelocity crosses 40 cm/s.",
                "role": "caption",
                "source_id": "ntrs-20160000593",
                "section": "Residence Time Driven Flame Spread"
              },
              {
                "evidence_id": "E-context-e6623c40985279bec3b2",
                "text": "Residence Time Driven Flame Spread\nSubrata Bhattacharjee, San Diego State University\nObjective\n\nExamine how thermal and species fields can diverge and lead to microgravity flame\nextinguishment by varying fuel thickness.\nStatus\n\u2015 22 test points obtained with BASS-II experiments.\n\u2015 The wealth of data has been catalogued at http://flame.sdsu.edu.\n\u2015 Samples were 1-cm and 2-cm wide sheets of plastic (PMMA; polymethyl methacrylate).\n\n\u2015 Thicknesses were between 0.1 and 0.4 mm.",
                "role": "paragraph",
                "source_id": "ntrs-20160000593",
                "section": "Residence Time Driven Flame Spread"
              },
              {
                "evidence_id": "E-context-5227141f2aaa7feb2e37",
                "text": "Approach\n\u2015 Microgravity combustion tests were performed aboard the International Space Station.\nActive crew support for real-time \u201clab partner\u201d operations.\n\n\u2015 The wind tunnel was installed in the Microgravity Science Glovebox which supplied power,\nimaging, and a level of containment.\n\u2015 Fuel samples were mounted inside a small wind tunnel which could impose airflow speeds\nup to 40 cm/s.\n\n\u2015 Main variables are airflow speed and oxygen concentration (oxygen varied below 21% by\nadding nitrogen).\n\u2015 Flame appearance, flame growth, and spread rates were determined in both the opposed\nand concurrent flow.",
                "role": "paragraph",
                "source_id": "ntrs-20160000593",
                "section": "Approach"
              }
            ]
          }
        ]
      },
      "provenance_path": []
    }
  ]
}
```
Support and applicable path (full exact spans remain in the case receipt):

```json
{
  "claim_id": "claim-440b0e46f6062e83",
  "evidence_ids": [
    "E-context-d0e9f6c262d92e57e3bd",
    "E-context-87d3a70a788ae398fe4a",
    "E-context-5227141f2aaa7feb2e37"
  ],
  "graph_paths": [
    {
      "statement_id": "material-context:bass-flight-rod-observation",
      "membership_paths": {
        "context:bass-flight-rod-observation": [
          {
            "from": "context:bass-flight-rod-observation",
            "to": "context:bass-flight-rods",
            "relation": "concerns",
            "basis": "EXPLICIT_SOURCE_IDENTITY",
            "support_spans": [
              {
                "evidence_id": "E-context-d0e9f6c262d92e57e3bd",
                "text": "There is a downward trend in flame\nspread rate as sample diameter increases\nfor both the 1g and \u03bcg (microgravity)\ntests. 1g tests have higher flame spread\nrates than \u03bcg.\n\n1g Black\n\nFlame Spread Rate [cm/sec]\n\nFlame spread rate as a function of\nsample diameter for both 1g and \u03bcg\ntests. 1g tests are in natural convection\nat 21% oxygen environments. Values for\n\u03bcg tests are averaged over flow velocity\nand oxygen concentration.",
                "role": "caption",
                "source_id": "ntrs-20160000593",
                "section": "PMMA rod comparison"
              },
              {
                "evidence_id": "E-context-87d3a70a788ae398fe4a",
                "text": "Material Ignition and Suppression Test\nCarlos Fernandez-Pello, University of California, Berkeley\nObjective\n\nUnderstand the effect of space exploration atmospheres (SEA) on the piloted ignition under an\nexternal radiant flux of a representative combustible material, as well as on its fire suppression\ncharacteristics.\nStatus\n\u2015 Three different diameters (0.25\u201d, 0.375\u201d, 0.5\u201d) of black and clear PMMA rods were tested.\n\u2015 Oxygen concentrations between 16% to 21% and flow velocity between 0.4 cm/sec to 4\ncm/sec were tested. The total set of experiments yielded 54 unique flame spread rates.",
                "role": "paragraph",
                "source_id": "ntrs-20160000593",
                "section": "Material Ignition and Suppression Test"
              },
              {
                "evidence_id": "E-context-5227141f2aaa7feb2e37",
                "text": "Approach\n\u2015 Microgravity combustion tests were performed aboard the International Space Station.\nActive crew support for real-time \u201clab partner\u201d operations.\n\n\u2015 The wind tunnel was installed in the Microgravity Science Glovebox which supplied power,\nimaging, and a level of containment.\n\u2015 Fuel samples were mounted inside a small wind tunnel which could impose airflow speeds\nup to 40 cm/s.\n\n\u2015 Main variables are airflow speed and oxygen concentration (oxygen varied below 21% by\nadding nitrogen).\n\u2015 Flame appearance, flame growth, and spread rates were determined in both the opposed\nand concurrent flow.",
                "role": "paragraph",
                "source_id": "ntrs-20160000593",
                "section": "Approach"
              }
            ]
          }
        ]
      },
      "provenance_path": []
    }
  ]
}
```

## What did NASA observe about PMMA combustion under microgravity?

Baseline: 37 words; integrated: 207 words.

QueryIntentV2: `{"schema_version":"query-intent-v2","operation":"SEARCH","targets":["ExperimentalRun"],"entity_constraints":[{"relation":"hasMaterial","entity_id":"PMMA"},{"relation":"hasGravityCondition","entity_id":"microgravity"}],"property_constraints":[],"requested_information":["ReportedObservation"],"comparison":null,"source_constraints":[],"unresolved_mentions":[],"conversation_reference":null,"clarification_required":false,"ambiguities":[]}`.

Classification: 2 DIRECT and 2 RELATED identities. Sources: E-context-5227141f2aaa7feb2e37, E-context-a79df97c23d629116824, E-context-d86d030e275ce04b8b82, E-context-80d7fc00aae08504c315, E-context-87d3a70a788ae398fe4a, E-context-e6623c40985279bec3b2, E-context-3b27486ede2bf8151a2f, E-context-d0e9f6c262d92e57e3bd, E-13fb7f02cdca2f8a, E-dc10a634dcb57b01, E-a01be685f4e205f1, E-1f129c9ecb7f6b59, E-4084124e9dc2a202, E-08c3327bddbeb4ae, E-5411d05d2ffb4e6a, E-9dc66a6421d1ebc7, E-context-90f697823c2ba1b2ea82, E-context-d1e50788b120206316a0.

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

Related evidence: 2 additional records differ in requested conditions or address a related question; they are not equivalent experiments.

Full records, source passages and applicability traces remain available in the EvidenceBundle and Evidence Registry.

Support and applicable path (full exact spans remain in the case receipt):

```json
{
  "claim_id": "claim-e92a6bedbd1b7d4b",
  "evidence_ids": [
    "E-context-90f697823c2ba1b2ea82",
    "E-context-e6623c40985279bec3b2",
    "E-context-5227141f2aaa7feb2e37"
  ],
  "graph_paths": [
    {
      "statement_id": "material-context:bass-film-observation",
      "membership_paths": {
        "context:bass-film-observation": [
          {
            "from": "context:bass-film-observation",
            "to": "context:bass-film-series",
            "relation": "concerns",
            "basis": "EXPLICIT_SOURCE_IDENTITY",
            "support_spans": [
              {
                "evidence_id": "E-context-90f697823c2ba1b2ea82",
                "text": "Sequence of top views showing radiative quenching when\nflow velocity goes below 2 cm/s.\n\nFlame nearing blow off extinction as the flow\nvelocity crosses 40 cm/s.",
                "role": "caption",
                "source_id": "ntrs-20160000593",
                "section": "Residence Time Driven Flame Spread"
              },
              {
                "evidence_id": "E-context-e6623c40985279bec3b2",
                "text": "Residence Time Driven Flame Spread\nSubrata Bhattacharjee, San Diego State University\nObjective\n\nExamine how thermal and species fields can diverge and lead to microgravity flame\nextinguishment by varying fuel thickness.\nStatus\n\u2015 22 test points obtained with BASS-II experiments.\n\u2015 The wealth of data has been catalogued at http://flame.sdsu.edu.\n\u2015 Samples were 1-cm and 2-cm wide sheets of plastic (PMMA; polymethyl methacrylate).\n\n\u2015 Thicknesses were between 0.1 and 0.4 mm.",
                "role": "paragraph",
                "source_id": "ntrs-20160000593",
                "section": "Residence Time Driven Flame Spread"
              },
              {
                "evidence_id": "E-context-5227141f2aaa7feb2e37",
                "text": "Approach\n\u2015 Microgravity combustion tests were performed aboard the International Space Station.\nActive crew support for real-time \u201clab partner\u201d operations.\n\n\u2015 The wind tunnel was installed in the Microgravity Science Glovebox which supplied power,\nimaging, and a level of containment.\n\u2015 Fuel samples were mounted inside a small wind tunnel which could impose airflow speeds\nup to 40 cm/s.\n\n\u2015 Main variables are airflow speed and oxygen concentration (oxygen varied below 21% by\nadding nitrogen).\n\u2015 Flame appearance, flame growth, and spread rates were determined in both the opposed\nand concurrent flow.",
                "role": "paragraph",
                "source_id": "ntrs-20160000593",
                "section": "Approach"
              }
            ]
          }
        ]
      },
      "provenance_path": []
    },
    {
      "statement_id": "gravity-context:bass-film-observation",
      "membership_paths": {
        "context:bass-film-observation": [
          {
            "from": "context:bass-film-observation",
            "to": "context:bass-film-series",
            "relation": "concerns",
            "basis": "EXPLICIT_SOURCE_IDENTITY",
            "support_spans": [
              {
                "evidence_id": "E-context-90f697823c2ba1b2ea82",
                "text": "Sequence of top views showing radiative quenching when\nflow velocity goes below 2 cm/s.\n\nFlame nearing blow off extinction as the flow\nvelocity crosses 40 cm/s.",
                "role": "caption",
                "source_id": "ntrs-20160000593",
                "section": "Residence Time Driven Flame Spread"
              },
              {
                "evidence_id": "E-context-e6623c40985279bec3b2",
                "text": "Residence Time Driven Flame Spread\nSubrata Bhattacharjee, San Diego State University\nObjective\n\nExamine how thermal and species fields can diverge and lead to microgravity flame\nextinguishment by varying fuel thickness.\nStatus\n\u2015 22 test points obtained with BASS-II experiments.\n\u2015 The wealth of data has been catalogued at http://flame.sdsu.edu.\n\u2015 Samples were 1-cm and 2-cm wide sheets of plastic (PMMA; polymethyl methacrylate).\n\n\u2015 Thicknesses were between 0.1 and 0.4 mm.",
                "role": "paragraph",
                "source_id": "ntrs-20160000593",
                "section": "Residence Time Driven Flame Spread"
              },
              {
                "evidence_id": "E-context-5227141f2aaa7feb2e37",
                "text": "Approach\n\u2015 Microgravity combustion tests were performed aboard the International Space Station.\nActive crew support for real-time \u201clab partner\u201d operations.\n\n\u2015 The wind tunnel was installed in the Microgravity Science Glovebox which supplied power,\nimaging, and a level of containment.\n\u2015 Fuel samples were mounted inside a small wind tunnel which could impose airflow speeds\nup to 40 cm/s.\n\n\u2015 Main variables are airflow speed and oxygen concentration (oxygen varied below 21% by\nadding nitrogen).\n\u2015 Flame appearance, flame growth, and spread rates were determined in both the opposed\nand concurrent flow.",
                "role": "paragraph",
                "source_id": "ntrs-20160000593",
                "section": "Approach"
              }
            ]
          }
        ]
      },
      "provenance_path": []
    }
  ]
}
```
Support and applicable path (full exact spans remain in the case receipt):

```json
{
  "claim_id": "claim-440b0e46f6062e83",
  "evidence_ids": [
    "E-context-d0e9f6c262d92e57e3bd",
    "E-context-87d3a70a788ae398fe4a",
    "E-context-5227141f2aaa7feb2e37"
  ],
  "graph_paths": [
    {
      "statement_id": "material-context:bass-flight-rod-observation",
      "membership_paths": {
        "context:bass-flight-rod-observation": [
          {
            "from": "context:bass-flight-rod-observation",
            "to": "context:bass-flight-rods",
            "relation": "concerns",
            "basis": "EXPLICIT_SOURCE_IDENTITY",
            "support_spans": [
              {
                "evidence_id": "E-context-d0e9f6c262d92e57e3bd",
                "text": "There is a downward trend in flame\nspread rate as sample diameter increases\nfor both the 1g and \u03bcg (microgravity)\ntests. 1g tests have higher flame spread\nrates than \u03bcg.\n\n1g Black\n\nFlame Spread Rate [cm/sec]\n\nFlame spread rate as a function of\nsample diameter for both 1g and \u03bcg\ntests. 1g tests are in natural convection\nat 21% oxygen environments. Values for\n\u03bcg tests are averaged over flow velocity\nand oxygen concentration.",
                "role": "caption",
                "source_id": "ntrs-20160000593",
                "section": "PMMA rod comparison"
              },
              {
                "evidence_id": "E-context-87d3a70a788ae398fe4a",
                "text": "Material Ignition and Suppression Test\nCarlos Fernandez-Pello, University of California, Berkeley\nObjective\n\nUnderstand the effect of space exploration atmospheres (SEA) on the piloted ignition under an\nexternal radiant flux of a representative combustible material, as well as on its fire suppression\ncharacteristics.\nStatus\n\u2015 Three different diameters (0.25\u201d, 0.375\u201d, 0.5\u201d) of black and clear PMMA rods were tested.\n\u2015 Oxygen concentrations between 16% to 21% and flow velocity between 0.4 cm/sec to 4\ncm/sec were tested. The total set of experiments yielded 54 unique flame spread rates.",
                "role": "paragraph",
                "source_id": "ntrs-20160000593",
                "section": "Material Ignition and Suppression Test"
              },
              {
                "evidence_id": "E-context-5227141f2aaa7feb2e37",
                "text": "Approach\n\u2015 Microgravity combustion tests were performed aboard the International Space Station.\nActive crew support for real-time \u201clab partner\u201d operations.\n\n\u2015 The wind tunnel was installed in the Microgravity Science Glovebox which supplied power,\nimaging, and a level of containment.\n\u2015 Fuel samples were mounted inside a small wind tunnel which could impose airflow speeds\nup to 40 cm/s.\n\n\u2015 Main variables are airflow speed and oxygen concentration (oxygen varied below 21% by\nadding nitrogen).\n\u2015 Flame appearance, flame growth, and spread rates were determined in both the opposed\nand concurrent flow.",
                "role": "paragraph",
                "source_id": "ntrs-20160000593",
                "section": "Approach"
              }
            ]
          }
        ]
      },
      "provenance_path": []
    },
    {
      "statement_id": "gravity-context:bass-flight-rod-observation",
      "membership_paths": {
        "context:bass-flight-rod-observation": [
          {
            "from": "context:bass-flight-rod-observation",
            "to": "context:bass-flight-rods",
            "relation": "concerns",
            "basis": "EXPLICIT_SOURCE_IDENTITY",
            "support_spans": [
              {
                "evidence_id": "E-context-d0e9f6c262d92e57e3bd",
                "text": "There is a downward trend in flame\nspread rate as sample diameter increases\nfor both the 1g and \u03bcg (microgravity)\ntests. 1g tests have higher flame spread\nrates than \u03bcg.\n\n1g Black\n\nFlame Spread Rate [cm/sec]\n\nFlame spread rate as a function of\nsample diameter for both 1g and \u03bcg\ntests. 1g tests are in natural convection\nat 21% oxygen environments. Values for\n\u03bcg tests are averaged over flow velocity\nand oxygen concentration.",
                "role": "caption",
                "source_id": "ntrs-20160000593",
                "section": "PMMA rod comparison"
              },
              {
                "evidence_id": "E-context-87d3a70a788ae398fe4a",
                "text": "Material Ignition and Suppression Test\nCarlos Fernandez-Pello, University of California, Berkeley\nObjective\n\nUnderstand the effect of space exploration atmospheres (SEA) on the piloted ignition under an\nexternal radiant flux of a representative combustible material, as well as on its fire suppression\ncharacteristics.\nStatus\n\u2015 Three different diameters (0.25\u201d, 0.375\u201d, 0.5\u201d) of black and clear PMMA rods were tested.\n\u2015 Oxygen concentrations between 16% to 21% and flow velocity between 0.4 cm/sec to 4\ncm/sec were tested. The total set of experiments yielded 54 unique flame spread rates.",
                "role": "paragraph",
                "source_id": "ntrs-20160000593",
                "section": "Material Ignition and Suppression Test"
              },
              {
                "evidence_id": "E-context-5227141f2aaa7feb2e37",
                "text": "Approach\n\u2015 Microgravity combustion tests were performed aboard the International Space Station.\nActive crew support for real-time \u201clab partner\u201d operations.\n\n\u2015 The wind tunnel was installed in the Microgravity Science Glovebox which supplied power,\nimaging, and a level of containment.\n\u2015 Fuel samples were mounted inside a small wind tunnel which could impose airflow speeds\nup to 40 cm/s.\n\n\u2015 Main variables are airflow speed and oxygen concentration (oxygen varied below 21% by\nadding nitrogen).\n\u2015 Flame appearance, flame growth, and spread rates were determined in both the opposed\nand concurrent flow.",
                "role": "paragraph",
                "source_id": "ntrs-20160000593",
                "section": "Approach"
              }
            ]
          }
        ]
      },
      "provenance_path": []
    }
  ]
}
```

## What do the available investigations report under normal gravity?

Baseline: 37 words; integrated: 189 words.

QueryIntentV2: `{"schema_version":"query-intent-v2","operation":"SEARCH","targets":["Investigation"],"entity_constraints":[{"relation":"hasGravityCondition","entity_id":"normal-gravity"}],"property_constraints":[],"requested_information":["ReportedObservation","Intervention","NASAConclusion"],"comparison":null,"source_constraints":[],"unresolved_mentions":[],"conversation_reference":null,"clarification_required":false,"ambiguities":[]}`.

Classification: 2 DIRECT and 0 RELATED identities. Sources: E-context-5227141f2aaa7feb2e37, E-context-a79df97c23d629116824, E-context-320a94a6feadb020fea3, E-context-87d3a70a788ae398fe4a, E-context-d0e9f6c262d92e57e3bd, E-f9c9d6f3bd3183e2, E-fce4222c581f0db3, E-cf52002d9d2fe8f4, E-c8f8ed9b6bd9012e, E-626767f8cbac8cd0, E-0736c640fe2b2d83, E-129ba4f7d3063d67, E-21e20799b88feef6.

Observations (DIRECT): There is a downward trend in flame spread rate as sample diameter increases for both the 1g and μg (microgravity) tests. 1g tests have higher flame spread rates than μg. 1g Black Flame Spread Rate [cm/sec] Flame spread rate as a function of sample diameter for both 1g and μg tests. 1g tests are in natural convection at 21% oxygen environments. Values for μg tests are averaged over flow velocity and oxygen concentration. [E-context-d0e9f6c262d92e57e3bd, E-context-87d3a70a788ae398fe4a, E-context-5227141f2aaa7feb2e37]

Applicable hasGravityCondition: normal-gravity (MATCH).

Observations (DIRECT): In upward-burning, normal-gravity tests, these three thicknesses spanned the flammability limits from significant burn, to partial burn, to no burn. ‒ The 0.27-mm thick samples were almost always completely consumed ‒ The 0.61-mm thickness burned on average 7.6 cm of the available 30 cm before extinguishing ‒ The 1.03-mm thickness would not burn at all. Downward burning silicone sample (2-4) was 0.37 mm thick. In downward burning, normal gravity tests, this thickness was completely consumed. The next higher thickness tested (0.61 mm) would not burn. [E-context-a79df97c23d629116824]

Applicable hasGravityCondition: normal-gravity (MATCH).

Full records, source passages and applicability traces remain available in the EvidenceBundle and Evidence Registry.

Support and applicable path (full exact spans remain in the case receipt):

```json
{
  "claim_id": "claim-17cdaeb7ff53225e",
  "evidence_ids": [
    "E-context-d0e9f6c262d92e57e3bd",
    "E-context-87d3a70a788ae398fe4a",
    "E-context-5227141f2aaa7feb2e37"
  ],
  "graph_paths": [
    {
      "statement_id": "gravity-context:bass-ground-rod-observation",
      "membership_paths": {
        "context:bass-ground-rod-observation": [
          {
            "from": "context:bass-ground-rod-observation",
            "to": "context:bass-ground-rods",
            "relation": "concerns",
            "basis": "EXPLICIT_SOURCE_IDENTITY",
            "support_spans": [
              {
                "evidence_id": "E-context-d0e9f6c262d92e57e3bd",
                "text": "There is a downward trend in flame\nspread rate as sample diameter increases\nfor both the 1g and \u03bcg (microgravity)\ntests. 1g tests have higher flame spread\nrates than \u03bcg.\n\n1g Black\n\nFlame Spread Rate [cm/sec]\n\nFlame spread rate as a function of\nsample diameter for both 1g and \u03bcg\ntests. 1g tests are in natural convection\nat 21% oxygen environments. Values for\n\u03bcg tests are averaged over flow velocity\nand oxygen concentration.",
                "role": "caption",
                "source_id": "ntrs-20160000593",
                "section": "PMMA rod comparison"
              },
              {
                "evidence_id": "E-context-87d3a70a788ae398fe4a",
                "text": "Material Ignition and Suppression Test\nCarlos Fernandez-Pello, University of California, Berkeley\nObjective\n\nUnderstand the effect of space exploration atmospheres (SEA) on the piloted ignition under an\nexternal radiant flux of a representative combustible material, as well as on its fire suppression\ncharacteristics.\nStatus\n\u2015 Three different diameters (0.25\u201d, 0.375\u201d, 0.5\u201d) of black and clear PMMA rods were tested.\n\u2015 Oxygen concentrations between 16% to 21% and flow velocity between 0.4 cm/sec to 4\ncm/sec were tested. The total set of experiments yielded 54 unique flame spread rates.",
                "role": "paragraph",
                "source_id": "ntrs-20160000593",
                "section": "Material Ignition and Suppression Test"
              },
              {
                "evidence_id": "E-context-5227141f2aaa7feb2e37",
                "text": "Approach\n\u2015 Microgravity combustion tests were performed aboard the International Space Station.\nActive crew support for real-time \u201clab partner\u201d operations.\n\n\u2015 The wind tunnel was installed in the Microgravity Science Glovebox which supplied power,\nimaging, and a level of containment.\n\u2015 Fuel samples were mounted inside a small wind tunnel which could impose airflow speeds\nup to 40 cm/s.\n\n\u2015 Main variables are airflow speed and oxygen concentration (oxygen varied below 21% by\nadding nitrogen).\n\u2015 Flame appearance, flame growth, and spread rates were determined in both the opposed\nand concurrent flow.",
                "role": "paragraph",
                "source_id": "ntrs-20160000593",
                "section": "Approach"
              }
            ]
          }
        ]
      },
      "provenance_path": []
    }
  ]
}
```
Support and applicable path (full exact spans remain in the case receipt):

```json
{
  "claim_id": "claim-e4b06d7998f9fe89",
  "evidence_ids": [
    "E-context-a79df97c23d629116824"
  ],
  "graph_paths": [
    {
      "statement_id": "gravity-context:silicone-ground-observation",
      "membership_paths": {
        "context:silicone-ground-observation": [
          {
            "from": "context:silicone-ground-observation",
            "to": "context:silicone-ground",
            "relation": "concerns",
            "basis": "EXPLICIT_SOURCE_IDENTITY",
            "support_spans": [
              {
                "evidence_id": "E-context-a79df97c23d629116824",
                "text": "In upward-burning, normal-gravity tests, these three thicknesses spanned the flammability limits from\nsignificant burn, to partial burn, to no burn.\n\u2012 The 0.27-mm thick samples were almost always completely consumed\n\u2012 The 0.61-mm thickness burned on average 7.6 cm of the available 30 cm before extinguishing\n\u2012 The 1.03-mm thickness would not burn at all.\nDownward burning silicone sample (2-4) was 0.37 mm thick.\n\nIn downward burning, normal gravity tests, this thickness was completely consumed. The next higher\nthickness tested (0.61 mm) would not burn.",
                "role": "paragraph",
                "source_id": "ntrs-20170008805",
                "section": "Saffire-II terrestrial reference tests"
              }
            ]
          }
        ]
      },
      "provenance_path": []
    }
  ]
}
```

## How do combustion observations differ between microgravity and normal gravity?

Baseline: 56 words; integrated: 300 words.

QueryIntentV2: `{"schema_version":"query-intent-v2","operation":"SEARCH","targets":["ExperimentalRun"],"entity_constraints":[{"relation":"hasGravityCondition","entity_id":"microgravity"},{"relation":"hasGravityCondition","entity_id":"normal-gravity"}],"property_constraints":[],"requested_information":["ReportedObservation"],"comparison":null,"source_constraints":[],"unresolved_mentions":[],"conversation_reference":null,"clarification_required":false,"ambiguities":[]}`.

Classification: 5 DIRECT and 0 RELATED identities. Sources: E-context-5227141f2aaa7feb2e37, E-context-a79df97c23d629116824, E-context-d86d030e275ce04b8b82, E-context-ec300b3756c4bd69021b, E-context-e6623c40985279bec3b2, E-context-87d3a70a788ae398fe4a, E-context-d0e9f6c262d92e57e3bd, E-648078dc1b9b887f, E-2e0c8358dffad031, E-010b45a4b4af736c, E-b1fe8e127108822e, E-27bcb4445e8fa047, E-0e211dd9cae7c63e, E-ea5c733358dfb67c, E-f8e5ad23867113ad, E-context-90f697823c2ba1b2ea82.

Observations (DIRECT): Sequence of top views showing radiative quenching when flow velocity goes below 2 cm/s. Flame nearing blow off extinction as the flow velocity crosses 40 cm/s. [E-context-90f697823c2ba1b2ea82, E-context-e6623c40985279bec3b2, E-context-5227141f2aaa7feb2e37]

Applicable hasGravityCondition: microgravity (MATCH).

Observations (DIRECT): There is a downward trend in flame spread rate as sample diameter increases for both the 1g and μg (microgravity) tests. 1g tests have higher flame spread rates than μg. 1g Black Flame Spread Rate [cm/sec] Flame spread rate as a function of sample diameter for both 1g and μg tests. 1g tests are in natural convection at 21% oxygen environments. Values for μg tests are averaged over flow velocity and oxygen concentration. [E-context-d0e9f6c262d92e57e3bd, E-context-87d3a70a788ae398fe4a, E-context-5227141f2aaa7feb2e37]

Applicable hasGravityCondition: microgravity (MATCH).

Observations (DIRECT): Results were convincing although rather anticlimactic as none of the silicone samples burned. When the igniter was powered off, a tiny gas phase flame remained but did not spread and quickly extinguished. The igniters all appeared to function normally and the materials were clearly damaged in the vicinities of the igniters. [E-context-d86d030e275ce04b8b82, E-context-ec300b3756c4bd69021b]

Applicable hasGravityCondition: microgravity (MATCH).

The same quoted statement also belongs to context:bass-ground-rod-observation (DIRECT); its applicable context follows.

Applicable hasGravityCondition: normal-gravity (MATCH).

Observations (DIRECT): In upward-burning, normal-gravity tests, these three thicknesses spanned the flammability limits from significant burn, to partial burn, to no burn. ‒ The 0.27-mm thick samples were almost always completely consumed ‒ The 0.61-mm thickness burned on average 7.6 cm of the available 30 cm before extinguishing ‒ The 1.03-mm thickness would not burn at all. Downward burning silicone sample (2-4) was 0.37 mm thick. In downward burning, normal gravity tests, this thickness was completely consumed. The next higher thickness tested (0.61 mm) would not burn. [E-context-a79df97c23d629116824]

Applicable hasGravityCondition: normal-gravity (MATCH).

Full records, source passages and applicability traces remain available in the EvidenceBundle and Evidence Registry.

Support and applicable path (full exact spans remain in the case receipt):

```json
{
  "claim_id": "claim-e92a6bedbd1b7d4b",
  "evidence_ids": [
    "E-context-90f697823c2ba1b2ea82",
    "E-context-e6623c40985279bec3b2",
    "E-context-5227141f2aaa7feb2e37"
  ],
  "graph_paths": [
    {
      "statement_id": "gravity-context:bass-film-observation",
      "membership_paths": {
        "context:bass-film-observation": [
          {
            "from": "context:bass-film-observation",
            "to": "context:bass-film-series",
            "relation": "concerns",
            "basis": "EXPLICIT_SOURCE_IDENTITY",
            "support_spans": [
              {
                "evidence_id": "E-context-90f697823c2ba1b2ea82",
                "text": "Sequence of top views showing radiative quenching when\nflow velocity goes below 2 cm/s.\n\nFlame nearing blow off extinction as the flow\nvelocity crosses 40 cm/s.",
                "role": "caption",
                "source_id": "ntrs-20160000593",
                "section": "Residence Time Driven Flame Spread"
              },
              {
                "evidence_id": "E-context-e6623c40985279bec3b2",
                "text": "Residence Time Driven Flame Spread\nSubrata Bhattacharjee, San Diego State University\nObjective\n\nExamine how thermal and species fields can diverge and lead to microgravity flame\nextinguishment by varying fuel thickness.\nStatus\n\u2015 22 test points obtained with BASS-II experiments.\n\u2015 The wealth of data has been catalogued at http://flame.sdsu.edu.\n\u2015 Samples were 1-cm and 2-cm wide sheets of plastic (PMMA; polymethyl methacrylate).\n\n\u2015 Thicknesses were between 0.1 and 0.4 mm.",
                "role": "paragraph",
                "source_id": "ntrs-20160000593",
                "section": "Residence Time Driven Flame Spread"
              },
              {
                "evidence_id": "E-context-5227141f2aaa7feb2e37",
                "text": "Approach\n\u2015 Microgravity combustion tests were performed aboard the International Space Station.\nActive crew support for real-time \u201clab partner\u201d operations.\n\n\u2015 The wind tunnel was installed in the Microgravity Science Glovebox which supplied power,\nimaging, and a level of containment.\n\u2015 Fuel samples were mounted inside a small wind tunnel which could impose airflow speeds\nup to 40 cm/s.\n\n\u2015 Main variables are airflow speed and oxygen concentration (oxygen varied below 21% by\nadding nitrogen).\n\u2015 Flame appearance, flame growth, and spread rates were determined in both the opposed\nand concurrent flow.",
                "role": "paragraph",
                "source_id": "ntrs-20160000593",
                "section": "Approach"
              }
            ]
          }
        ]
      },
      "provenance_path": []
    }
  ]
}
```
Support and applicable path (full exact spans remain in the case receipt):

```json
{
  "claim_id": "claim-440b0e46f6062e83",
  "evidence_ids": [
    "E-context-d0e9f6c262d92e57e3bd",
    "E-context-87d3a70a788ae398fe4a",
    "E-context-5227141f2aaa7feb2e37"
  ],
  "graph_paths": [
    {
      "statement_id": "gravity-context:bass-flight-rod-observation",
      "membership_paths": {
        "context:bass-flight-rod-observation": [
          {
            "from": "context:bass-flight-rod-observation",
            "to": "context:bass-flight-rods",
            "relation": "concerns",
            "basis": "EXPLICIT_SOURCE_IDENTITY",
            "support_spans": [
              {
                "evidence_id": "E-context-d0e9f6c262d92e57e3bd",
                "text": "There is a downward trend in flame\nspread rate as sample diameter increases\nfor both the 1g and \u03bcg (microgravity)\ntests. 1g tests have higher flame spread\nrates than \u03bcg.\n\n1g Black\n\nFlame Spread Rate [cm/sec]\n\nFlame spread rate as a function of\nsample diameter for both 1g and \u03bcg\ntests. 1g tests are in natural convection\nat 21% oxygen environments. Values for\n\u03bcg tests are averaged over flow velocity\nand oxygen concentration.",
                "role": "caption",
                "source_id": "ntrs-20160000593",
                "section": "PMMA rod comparison"
              },
              {
                "evidence_id": "E-context-87d3a70a788ae398fe4a",
                "text": "Material Ignition and Suppression Test\nCarlos Fernandez-Pello, University of California, Berkeley\nObjective\n\nUnderstand the effect of space exploration atmospheres (SEA) on the piloted ignition under an\nexternal radiant flux of a representative combustible material, as well as on its fire suppression\ncharacteristics.\nStatus\n\u2015 Three different diameters (0.25\u201d, 0.375\u201d, 0.5\u201d) of black and clear PMMA rods were tested.\n\u2015 Oxygen concentrations between 16% to 21% and flow velocity between 0.4 cm/sec to 4\ncm/sec were tested. The total set of experiments yielded 54 unique flame spread rates.",
                "role": "paragraph",
                "source_id": "ntrs-20160000593",
                "section": "Material Ignition and Suppression Test"
              },
              {
                "evidence_id": "E-context-5227141f2aaa7feb2e37",
                "text": "Approach\n\u2015 Microgravity combustion tests were performed aboard the International Space Station.\nActive crew support for real-time \u201clab partner\u201d operations.\n\n\u2015 The wind tunnel was installed in the Microgravity Science Glovebox which supplied power,\nimaging, and a level of containment.\n\u2015 Fuel samples were mounted inside a small wind tunnel which could impose airflow speeds\nup to 40 cm/s.\n\n\u2015 Main variables are airflow speed and oxygen concentration (oxygen varied below 21% by\nadding nitrogen).\n\u2015 Flame appearance, flame growth, and spread rates were determined in both the opposed\nand concurrent flow.",
                "role": "paragraph",
                "source_id": "ntrs-20160000593",
                "section": "Approach"
              }
            ]
          }
        ]
      },
      "provenance_path": []
    }
  ]
}
```

## What was investigated in BASS-II?

Baseline: 9507 words; integrated: 165 words.

QueryIntentV2: `{"schema_version":"query-intent-v2","operation":"SEARCH","targets":["ExperimentalRun"],"entity_constraints":[{"relation":"belongsToInvestigation","entity_id":"psi-25"}],"property_constraints":[],"requested_information":[],"comparison":null,"source_constraints":[],"unresolved_mentions":[],"conversation_reference":null,"clarification_required":false,"ambiguities":[]}`.

Classification: 129 DIRECT and 0 RELATED identities. Sources: E-context-0a49239e2fb97b47c967, E-context-d3dbd30b9225c3cf1bda, E-context-5227141f2aaa7feb2e37, E-7991f8bb07cfdf8c, E-context-f754593ea530edb87a0f, E-context-f797918013e400f45ee5, E-2dd90ca4a289b23f, E-b1eb0fcba70607d6, E-62706d15470b4dcf, E-ee5894ea3735b715, E-ecb4090800f37a74, E-24cbcbd1e598da3b, E-95bda32d30578f33, E-5212a18ab5fb37c1, E-context-2db49f0e1faad030aa8d, E-b32552ad0b0d12dd, E-context-eda9b16ad569a67b6818, E-4bbab85c8573ee28, E-context-772d71ea121a16a790fc, E-8af8deaa46974f9b, E-context-aed4c3edfaa6ec55b499, E-ef7902febe570d66, E-context-4eefc8331334df09dca5, E-f9051a6418603bba, E-context-07a0d7ae7e886ccdc3f5, E-eb869a77d71ba202, E-context-cc747944551cbbf183a8, E-b53e490dad1232a6, E-context-139fde6af07d97030c2b, E-28a3e91e3a5011ce, E-context-94893088b09e16a5fea6, E-e276a3a838e36bc7, E-context-ca6ed42b06f27e7a971c, E-bf6d5dc168d0cf28, E-32ae64e048a52899, E-context-b37e00fdb4bd65166a63, E-598d942ef88e00eb, E-context-23399514e05ca62cccb6, E-a9f2f65681b89318, E-context-60b394de3131e782dedc, E-31c96f6478e82314, E-context-d760281aafddd141d301, E-81298068664f27ad, E-context-2a09f4f8aaac0b85820d, E-48dae6500050528e, E-context-e3bfd560d34627343406, E-587857081c3df440, E-context-3ce0574fa6ffd12ff048, E-fe426453924435cd, E-context-2b6e5de5e4415a146795, E-9e03283b228334c4, E-34f4ce31abe5b8f3, E-context-fe1f2712d97ee7635aa3, E-9b3d9a6a2270535c, E-context-30f38f4b4cf7d223aa9d, E-6dd2cd0a4d048240, E-context-d4ba437bbc53df6404bc, E-f49dc4006364f9f7, E-context-eb8dc61f4cffacfdcb4d, E-6c35967ec020bf2c, E-context-2997b06f59a6b65580e2, E-f0e70d0094fff10e, E-context-9d562f3222fdbf05a4e4, E-8b9d08b75afd5be7, E-context-5742bbb42473a59fadfa, E-390686b2881ab650, E-context-7ea5c5232e3497124abc, E-d965211a57bd3a89, E-context-2de71d38c317717f3361, E-psi-25-table-B1, E-context-6ab483e6ad43615a01f1, E-28dbe4099f836799, E-context-0ddcb4bc32ac0e90449d, E-6f3dfc00b1ae921d, E-context-837729674e67241449f2, E-2b6dc02112f69c62, E-context-eeb5f4b119bb82ad2449, E-f048ab84d414e80c, E-context-633ef72921b67362ae3e, E-3f94c1f197bb369e, E-context-3741fd96cea02f392117, E-2e17cd58df509234, E-context-c0c2efac8d28c5274b86, E-85c990c665b4eab4, E-context-b32e7f7d9e87bec8a671, E-d4af5e696ef3cb3d, E-context-8316aff942e67c04805f, E-4eeddcd22086d51f, E-context-d077a4d55e9633e8d98e, E-05432e0197f0dc90, E-context-21091b83717224604612, E-fc47dcf2c3a28aa5, E-context-30b53f4e39699ae09fca, E-df975be73db3e312, E-context-1b2ecca3847616de3ed3, E-3cc01537e774aef5, E-context-2d0b7695c9eece411212, E-2014fc5b3d6baecf, E-context-d37a9415d6106177e204, E-29ccc4e2bf89fb0e, E-context-03b317e2ad99004c83ab, E-31f5ad33f7deebba, E-context-8115fbfc0b386ac448c3, E-4a56dcd4a534464e, E-context-e2f1ffd20ad50f76bdbf, E-48bbe68140eb6e4d, E-context-5a644b8097f8855560a4, E-40ffeae5cf8d32f0, E-context-cbfe4b07ba5959632dde, E-ad30ba0adef4fbcd, E-context-a93eaf9c327e3079402a, E-78fcea63a3e5b5e1, E-context-97af436463bbf9e0a5ed, E-53a9d15f7bab9b19, E-context-e86a80953b13c0074366, E-1f687be9bbc8ed02, E-context-9a53620a1295afac5bf9, E-5c090d705c043d1f, E-context-8b1f0d0a89d769d3ddc6, E-8ce6cbeb2818a73b, E-context-a11086892fe760af64fe, E-23b2d2d28846f6f7, E-context-2468a2e29f4bbba421bd, E-df9eb6681a1dcc94, E-context-9b7865f1a0ed1cd992ba, E-d0ce61110c69a466, E-context-bb114264c991d6f1518b, E-04cea895f0cb6795, E-context-beb9a2847d82a28e9ead, E-5f55cf9b7061d75a, E-context-b5372f452d0fa8c229ba, E-0664b84bf7462152, E-context-3197bea6986875886380, E-01ee0ccab9c9c12f, E-context-f64e79533a5f4f18d0cd, E-7c3a1adbd0401f1b, E-context-169472910097c63b01b1, E-2f33f40880c4fa52, E-context-2dcaeab319a0235cd00f, E-457cab5e59d8c2c4, E-context-d13390f0b4235ae89b82, E-4f5fca4fc5e3c86b, E-context-b52087fe0203c24fbd84, E-100a0cfefb97d303, E-context-09fb47a7d1880c41b705, E-82b9b60fb9f0decd.

Recorded source quantities (not observations):

| Source field | psi-25-B1 | psi-25-B10 | psi-25-B11 | psi-25-B12 | psi-25-B13 | psi-25-B15 | psi-25-B16 |

| --- | --- | --- | --- | --- | --- | --- | --- |

| OxygenConcentration | 22.2 % (DIRECT) [E-psi-25-table-B1] | 20.8 % (DIRECT) [E-f49dc4006364f9f7] | 20.7 % (DIRECT) [E-05432e0197f0dc90] | 22.1 % (DIRECT) [E-f1ce28190ffc8aad] | 20.5 % (DIRECT) [E-9f8c07a08bc46118] | 20.8 % (DIRECT) [E-4eeddcd22086d51f] | 17.2 % (DIRECT) [E-40ffeae5cf8d32f0] |

psi-25-B1: gravity microgravity; VERIFIED_APPLICABLE_CONTEXT [E-context-0a49239e2fb97b47c967, E-context-2de71d38c317717f3361, E-context-5227141f2aaa7feb2e37, E-psi-25-table-B1].

psi-25-B10: gravity microgravity; VERIFIED_APPLICABLE_CONTEXT [E-context-0a49239e2fb97b47c967, E-context-5227141f2aaa7feb2e37, E-context-d4ba437bbc53df6404bc, E-f49dc4006364f9f7].

psi-25-B11: gravity microgravity; VERIFIED_APPLICABLE_CONTEXT [E-05432e0197f0dc90, E-context-0a49239e2fb97b47c967, E-context-5227141f2aaa7feb2e37, E-context-d077a4d55e9633e8d98e].

psi-25-B15: gravity microgravity; VERIFIED_APPLICABLE_CONTEXT [E-4eeddcd22086d51f, E-context-0a49239e2fb97b47c967, E-context-5227141f2aaa7feb2e37, E-context-8316aff942e67c04805f].

psi-25-B16: gravity microgravity; VERIFIED_APPLICABLE_CONTEXT [E-40ffeae5cf8d32f0, E-context-0a49239e2fb97b47c967, E-context-5227141f2aaa7feb2e37, E-context-5a644b8097f8855560a4].

Values and field labels reproduce selected source records; documentary geometry and unclassified quantity roles are not silently reconciled.

Microgravity is a presentation preference, not an experimental fact or an added mandatory condition.

Full records, source passages and applicability traces remain available in the EvidenceBundle and Evidence Registry.

Support and applicable path (full exact spans remain in the case receipt):

```json
{
  "claim_id": "claim-23bb20338d2e1054",
  "evidence_ids": [
    "E-psi-25-table-B1"
  ],
  "graph_paths": []
}
```
Support and applicable path (full exact spans remain in the case receipt):

```json
{
  "claim_id": "claim-bc3c8dc1597366a8",
  "evidence_ids": [
    "E-psi-25-table-B1"
  ],
  "graph_paths": []
}
```

## Which conditions applied to the Saffire-I experiments?

Baseline: 5519 words; integrated: 134 words.

QueryIntentV2: `{"schema_version":"query-intent-v2","operation":"SEARCH","targets":["ExperimentalRun"],"entity_constraints":[{"relation":"belongsToInvestigation","entity_id":"psi-98"}],"property_constraints":[],"requested_information":[],"comparison":null,"source_constraints":[],"unresolved_mentions":[],"conversation_reference":null,"clarification_required":false,"ambiguities":[]}`.

Classification: 2 DIRECT and 0 RELATED identities. Sources: E-context-0bacb5f04c6c34659dcc, E-context-7973df3a5b7f8b12b64d, E-1ac66b2fe73347e1, E-18c496f0304c63ce, E-81123adcd59c0ce9, E-ad149b6a9ce7f2f8, E-5d4bb0be10b6a4a3, E-49fde889c36ce643, E-20d4518a07dc9870, E-772994a1417846a7, E-psi-98-table-S1, E-psi-98-table-S2.

Recorded source quantities (not observations):

| Source field | psi-98-S1 | psi-98-S2 |

| --- | --- | --- |

| AirflowVelocity | 20.0 cm/s (DIRECT) [E-psi-98-table-S1] | 20.0 cm/s (DIRECT) [E-psi-98-table-S2] |

| FlowDirection | Concurrent (DIRECT) [E-psi-98-table-S1] | Opposed (DIRECT) [E-psi-98-table-S2] |

| OxygenConcentration | 21.5 - 21.7 % (DIRECT) [E-psi-98-table-S1] | ~ 21.5 % (DIRECT) [E-psi-98-table-S2] |

| source:burn_time | 420.0 s (DIRECT) [E-psi-98-table-S1] | 70.0 s (DIRECT) [E-psi-98-table-S2] |

psi-98-S1: gravity microgravity; VERIFIED_APPLICABLE_CONTEXT [E-context-0bacb5f04c6c34659dcc, E-context-7973df3a5b7f8b12b64d, E-psi-98-table-S1].

psi-98-S2: gravity microgravity; VERIFIED_APPLICABLE_CONTEXT [E-context-0bacb5f04c6c34659dcc, E-context-7973df3a5b7f8b12b64d, E-psi-98-table-S2].

Values and field labels reproduce selected source records; documentary geometry and unclassified quantity roles are not silently reconciled.

Microgravity is a presentation preference, not an experimental fact or an added mandatory condition.

Full records, source passages and applicability traces remain available in the EvidenceBundle and Evidence Registry.

Support and applicable path (full exact spans remain in the case receipt):

```json
{
  "claim_id": "claim-e7fba1f04628427d",
  "evidence_ids": [
    "E-psi-98-table-S1"
  ],
  "graph_paths": []
}
```
Support and applicable path (full exact spans remain in the case receipt):

```json
{
  "claim_id": "claim-d174c34a3cfe9b36",
  "evidence_ids": [
    "E-psi-98-table-S2"
  ],
  "graph_paths": []
}
```

## Which experimental runs used PMMA, and how were their conditions different?

Baseline: 7099 words; integrated: 111 words.

QueryIntentV2: `{"schema_version":"query-intent-v2","operation":"SEARCH","targets":["ExperimentalRun"],"entity_constraints":[{"relation":"hasMaterial","entity_id":"PMMA"}],"property_constraints":[],"requested_information":[],"comparison":null,"source_constraints":[],"unresolved_mentions":[],"conversation_reference":null,"clarification_required":false,"ambiguities":[]}`.

Classification: 41 DIRECT and 0 RELATED identities. Sources: E-context-8115fbfc0b386ac448c3, E-f048ab84d414e80c, E-6dd2cd0a4d048240, E-psi-25-table-B1, E-04cea895f0cb6795, E-df9eb6681a1dcc94, E-100a0cfefb97d303, E-23b2d2d28846f6f7, E-b22d0e33bb275c68, E-f5888bf9b56a8b55, E-48e3b77356dfe707, E-273e62bebaaac6d5, E-ec0bd3175b39dd2e, E-527e58842c2599c5, E-502c430761d3a97d, E-3958fb378c75c4fb, E-context-5227141f2aaa7feb2e37, E-context-0a49239e2fb97b47c967, E-context-5a644b8097f8855560a4, E-40ffeae5cf8d32f0, E-context-cbfe4b07ba5959632dde, E-ad30ba0adef4fbcd, E-context-60b394de3131e782dedc, E-31c96f6478e82314, E-context-837729674e67241449f2, E-2b6dc02112f69c62, E-context-d760281aafddd141d301, E-81298068664f27ad, E-context-eeb5f4b119bb82ad2449, E-context-a93eaf9c327e3079402a, E-78fcea63a3e5b5e1, E-context-aed4c3edfaa6ec55b499, E-ef7902febe570d66, E-context-3741fd96cea02f392117, E-2e17cd58df509234, E-context-c0c2efac8d28c5274b86, E-85c990c665b4eab4, E-context-3ce0574fa6ffd12ff048, E-fe426453924435cd, E-context-4eefc8331334df09dca5, E-f9051a6418603bba, E-context-2b6e5de5e4415a146795, E-9e03283b228334c4, E-context-d3dbd30b9225c3cf1bda, E-34f4ce31abe5b8f3, E-context-fe1f2712d97ee7635aa3, E-9b3d9a6a2270535c, E-context-9a53620a1295afac5bf9, E-5c090d705c043d1f, E-context-8b1f0d0a89d769d3ddc6, E-8ce6cbeb2818a73b, E-context-b32e7f7d9e87bec8a671, E-d4af5e696ef3cb3d, E-context-a11086892fe760af64fe, E-context-8316aff942e67c04805f, E-4eeddcd22086d51f, E-context-2468a2e29f4bbba421bd, E-context-d077a4d55e9633e8d98e, E-05432e0197f0dc90, E-context-9b7865f1a0ed1cd992ba, E-d0ce61110c69a466, E-context-bb114264c991d6f1518b, E-context-30f38f4b4cf7d223aa9d, E-context-d4ba437bbc53df6404bc, E-f49dc4006364f9f7, E-context-2997b06f59a6b65580e2, E-f0e70d0094fff10e, E-context-30b53f4e39699ae09fca, E-df975be73db3e312, E-context-1b2ecca3847616de3ed3, E-3cc01537e774aef5, E-context-9d562f3222fdbf05a4e4, E-8b9d08b75afd5be7, E-context-139fde6af07d97030c2b, E-28a3e91e3a5011ce, E-context-2d0b7695c9eece411212, E-2014fc5b3d6baecf, E-context-5742bbb42473a59fadfa, E-390686b2881ab650, E-context-3197bea6986875886380, E-01ee0ccab9c9c12f, E-context-2de71d38c317717f3361, E-context-f754593ea530edb87a0f, E-7991f8bb07cfdf8c, E-context-169472910097c63b01b1, E-2f33f40880c4fa52, E-context-2dcaeab319a0235cd00f, E-457cab5e59d8c2c4, E-context-ca6ed42b06f27e7a971c, E-bf6d5dc168d0cf28, E-context-b52087fe0203c24fbd84, E-4a56dcd4a534464e.

Recorded source quantities (not observations):

| Source field | psi-25-B1 | psi-25-B10 | psi-25-B11 | psi-25-B15 | psi-25-B16 | psi-25-B17 | psi-25-B18 |

| --- | --- | --- | --- | --- | --- | --- | --- |

| OxygenConcentration | 22.2 % (DIRECT) [E-psi-25-table-B1] | 20.8 % (DIRECT) [E-f49dc4006364f9f7] | 20.7 % (DIRECT) [E-05432e0197f0dc90] | 20.8 % (DIRECT) [E-4eeddcd22086d51f] | 17.2 % (DIRECT) [E-40ffeae5cf8d32f0] | 17.4 % (DIRECT) [E-fe426453924435cd] | 17.4 % (DIRECT) [E-9b3d9a6a2270535c] |

Values and field labels reproduce selected source records; documentary geometry and unclassified quantity roles are not silently reconciled.

Full records, source passages and applicability traces remain available in the EvidenceBundle and Evidence Registry.

Support and applicable path (full exact spans remain in the case receipt):

```json
{
  "claim_id": "claim-23bb20338d2e1054",
  "evidence_ids": [
    "E-psi-25-table-B1"
  ],
  "graph_paths": []
}
```
Support and applicable path (full exact spans remain in the case receipt):

```json
{
  "claim_id": "claim-bc3c8dc1597366a8",
  "evidence_ids": [
    "E-psi-25-table-B1"
  ],
  "graph_paths": []
}
```

## What happened after airflow was interrupted and restored?

Baseline: 48 words; integrated: 218 words.

QueryIntentV2: `{"schema_version":"query-intent-v2","operation":"SEARCH","targets":["ExperimentalRun"],"entity_constraints":[],"property_constraints":[],"requested_information":["ReportedObservation","Intervention"],"comparison":null,"source_constraints":[],"unresolved_mentions":[],"conversation_reference":null,"clarification_required":false,"ambiguities":[]}`.

Classification: 2 DIRECT and 3 RELATED identities. Sources: E-context-5227141f2aaa7feb2e37, E-context-3b27486ede2bf8151a2f, E-context-80d7fc00aae08504c315, E-context-e6623c40985279bec3b2, E-context-d0e9f6c262d92e57e3bd, E-context-87d3a70a788ae398fe4a, E-context-d1e50788b120206316a0, E-1bc76d1f2a957fd8, E-1a048dade39a6ea2, E-1b77a0f62becebf7, E-6821163b1b183a5d, E-667fe69b6ea2e598, E-ca4ca79d1757f8e5, E-46e240439315046d, E-5212a18ab5fb37c1, E-context-90f697823c2ba1b2ea82.

Observations (RELATED): Sequence of top views showing radiative quenching when flow velocity goes below 2 cm/s. Flame nearing blow off extinction as the flow velocity crosses 40 cm/s. [E-context-90f697823c2ba1b2ea82, E-context-e6623c40985279bec3b2, E-context-5227141f2aaa7feb2e37]

Applicable hasGravityCondition: microgravity (VERIFIED_APPLICABLE_CONTEXT).

Observations (RELATED): There is a downward trend in flame spread rate as sample diameter increases for both the 1g and μg (microgravity) tests. 1g tests have higher flame spread rates than μg. 1g Black Flame Spread Rate [cm/sec] Flame spread rate as a function of sample diameter for both 1g and μg tests. 1g tests are in natural convection at 21% oxygen environments. Values for μg tests are averaged over flow velocity and oxygen concentration. [E-context-d0e9f6c262d92e57e3bd, E-context-87d3a70a788ae398fe4a, E-context-5227141f2aaa7feb2e37]

Applicable hasGravityCondition: microgravity (VERIFIED_APPLICABLE_CONTEXT).

The same quoted statement also belongs to context:bass-ground-rod-observation (RELATED); its applicable context follows.

Applicable hasGravityCondition: normal-gravity (VERIFIED_APPLICABLE_CONTEXT).

Observations (DIRECT): The fire didn’t extinguish and began to grow when we turned the flow back on [E-context-d1e50788b120206316a0, E-context-80d7fc00aae08504c315]

Interventions (DIRECT): For the Saffire-IV PMMA sample, we turned off the flow for 20 seconds [E-context-3b27486ede2bf8151a2f, E-context-80d7fc00aae08504c315]

Related evidence: 3 additional records differ in requested conditions or address a related question; they are not equivalent experiments.

Microgravity is a presentation preference, not an experimental fact or an added mandatory condition.

Full records, source passages and applicability traces remain available in the EvidenceBundle and Evidence Registry.

Support and applicable path (full exact spans remain in the case receipt):

```json
{
  "claim_id": "claim-e92a6bedbd1b7d4b",
  "evidence_ids": [
    "E-context-90f697823c2ba1b2ea82",
    "E-context-e6623c40985279bec3b2",
    "E-context-5227141f2aaa7feb2e37"
  ],
  "graph_paths": []
}
```
Support and applicable path (full exact spans remain in the case receipt):

```json
{
  "claim_id": "claim-440b0e46f6062e83",
  "evidence_ids": [
    "E-context-d0e9f6c262d92e57e3bd",
    "E-context-87d3a70a788ae398fe4a",
    "E-context-5227141f2aaa7feb2e37"
  ],
  "graph_paths": []
}
```

## Does acrylic mean PMMA?

Baseline: 4960 words; integrated: 80 words.

QueryIntentV2: `{"schema_version":"query-intent-v2","operation":"EXPLAIN","targets":["Publication"],"entity_constraints":[],"property_constraints":[],"requested_information":[],"comparison":null,"source_constraints":[],"unresolved_mentions":[],"conversation_reference":null,"clarification_required":false,"ambiguities":[]}`.

Classification: 0 DIRECT and 0 RELATED identities. Sources: E-751f8e0f5230aa68, E-5cd2680edc32b966, E-6c0e7e8d8cd6a684, E-2dd90ca4a289b23f, E-5212a18ab5fb37c1, E-b3d0c69c6415bc13, E-4cdaeb4fca2ed9bd, E-0ff0dc022e415930, E-9464f0ca8ca7ee4b.

The available records identify experiments, but do not establish a selected scientific observation answering this question.

Terminology: experiment matches do not establish material equivalence. Only approved ontology identity relationships can establish an exact equivalence.

No DIRECT match was established. Missing evidence in this corpus is not an identified NASA knowledge gap.

Microgravity is a presentation preference, not an experimental fact or an added mandatory condition.

Full records, source passages and applicability traces remain available in the EvidenceBundle and Evidence Registry.


## What unresolved questions did NASA identify about microgravity fire safety?

Baseline: 230 words; integrated: 62 words.

QueryIntentV2: `{"schema_version":"query-intent-v2","operation":"SEARCH","targets":["ExperimentalRun"],"entity_constraints":[{"relation":"hasGravityCondition","entity_id":"microgravity"}],"property_constraints":[],"requested_information":["OpenQuestion"],"comparison":null,"source_constraints":[],"unresolved_mentions":[],"conversation_reference":null,"clarification_required":false,"ambiguities":[]}`.

Classification: 0 DIRECT and 0 RELATED identities. Sources: E-context-80d7fc00aae08504c315, E-733d1e5d0226dbe6, E-f17d53d89a4e59b4, E-afcda2a09d83ed04, E-129ba4f7d3063d67, E-5d5764b9e2e15685, E-f7f48f13118ee722, E-5ede966d10692ff5, E-72d8a9c524f0bd61, E-safety-saffire-suppression-open-question.

Documentary context (not verified experimental support) (DOCUMENTARY): Additional focused tests may be required to develop guidance on these questions. [E-safety-saffire-suppression-open-question]

Limits: Documentary quotation; experimental identity and requested conditions remain unverified

No DIRECT match was established. Missing evidence in this corpus is not an identified NASA knowledge gap.

Full records, source passages and applicability traces remain available in the EvidenceBundle and Evidence Registry.

Support and applicable path (full exact spans remain in the case receipt):

```json
{
  "claim_id": "claim-b7ef6f8f7065df4c",
  "evidence_ids": [
    "E-safety-saffire-suppression-open-question"
  ],
  "graph_paths": []
}
```

