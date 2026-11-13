# Phase 3C specimen normalization

405 specimens retain unchanged source descriptions and canonical geometry/condition payloads. A generic boundary-aware approved-alias resolver recognizes 70/405: PMMA 41, SIBAL Fabric 29. This count measures alias resolution, not all material identities; methanol/heptane literals remain preserved. Ambiguous multi-material labels are not merged. No production branch names a material.

Runs link to Sample through usesSample; samples link to actual material through madeOf. Approved identities also receive source-backed hasMaterial links. Unknown descriptions remain literal and recoverable. Geometry scalars remain source condition records, not newly approved geometric properties. Synthetic tests cover different geometries, different materials, ambiguity and unknown descriptions. Receipts: phase3c_knowledge_projection_final_v1.json.
