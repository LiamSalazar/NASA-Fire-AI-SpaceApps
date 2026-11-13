# Controlled NASA fire-safety vocabulary

The lexicon in `domain/lexicon.yaml` is an alias layer, not ontology expansion. It maps only explicit NASA-source labels to existing concepts.

| Concept | aliases | category | source / mapping |
| --- | --- | --- | --- |
| PMMA | polymethyl methacrylate | material | PSI-25/NTRS; `Material` |
| SIBAL Fabric | Sibal | material | PSI-98 table; `Material` |
| SAFFIRE-I | Saffire I, Saffire | investigation | PSI-98; `Investigation` |
| BASS-II | BASS II, BASS | investigation | PSI-25; `Investigation` |
| airflow velocity | airflow, air flow, forced flow | flow | PSI-98; `FlowCondition` |
| microgravity | low-g | gravity | PSI-98/NTRS; `GravityCondition` |
| suppression | fire suppression, suppressant | safety | NTRS 20205007829; `SafetyImplication` |
| requirement / guidance | shall / guidelines | normative | NASA-STD-6001 / NTRS 20150020937 |
| extinction | extinguish | phenomenon | NTRS 20205007829; `Extinction` |

Intentionally not collapsed: airflow velocity and flame-spread velocity; extinction and suppression; quenching and blowoff; flame spread and burning rate; guidance and requirement; observation and conclusion. `acrylic` is deliberately ambiguous/restricted and is not mapped by the parser.
