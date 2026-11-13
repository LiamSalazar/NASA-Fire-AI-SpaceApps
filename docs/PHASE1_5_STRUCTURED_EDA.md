# Structured-table EDA

Executed profile: 22 official PSI CSV tables, 2,870 rows. Profiles are in `data/eda/experimental_tables.json`.

| Family examples | Tables / rows | Finding |
|---|---:|---|
| FLEX/FLEX-2 | 2 / 282 | Liquid fuel, droplet diameter, pressure, mole fraction, burn time/end condition; FLEX-2 uses ranges/semicolon lists and is not row-ingested. |
| BASS/BASS-II | 2 / 251 | Material/sample and operational columns differ substantially. |
| SAFFIRE I–III | 3 / 21 | Shared material/geometry/flow patterns but differing oxygen and outcome representations. |
| SAME/SAME-R | 2 / 117 | Smoke material, aging and detector-related operational values. |
| SPICE | 1 / 469 | Gas-fuel/nozzle/rate fields; not conflated with solid-fuel flow. |

FLEX’s 274 row table was safely ingested using generic header aliases: fuel → Sample material; pressure/compositions/droplet diameters/burn time → explicit generic conditions. No novel ontology class was created.
