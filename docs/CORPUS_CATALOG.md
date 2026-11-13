# NASA fire-safety corpus catalog

The machine-readable authority is `data/catalog/nasa_fire_corpus.yaml`. The catalog records only verified identifiers. Family names without a verified public identifier are explicitly pending rather than guessed.

| Family/source | Official system | Phase-1 status | Included material |
| --- | --- | --- | --- |
| BASS-II / PSI-25 | NASA PSI | Structured ingestion executed | Official experimental-table CSV; large/raw/media items inventoried only |
| Saffire-I / PSI-98 | NASA PSI | Existing structured regression corpus retained | Official experimental-table CSV |
| Spacecraft Fire Safety Needs for Exploration | NTRS 20205007829 | Document segmented | Official PDF |
| NASA-STD-6001 | NASA Technical Standards | Existing curated documentary evidence retained | Official PDF/page evidence |
| FLEX / NTRS 20150023456 | NTRS | True holdout first pass | Official liquid-droplet technical-report archive; 317 first-pass passages |
| SoFIE / NTRS 20200000361 | NTRS | Documents ingested | Official recent ISS solid-fuel report; NVIDIA audit source |
| FLEX, FLEX-2, SoFIE variants, SAME, SPICE, SLICE, Confined Combustion | Official NASA discovery required | Not ingested | No IDs or metadata are asserted in this repository yet |

`INCLUDE_MEDIA=false` and `MAX_SINGLE_DOWNLOAD_MB=50` are the defaults. Large files are cataloged rather than downloaded.
