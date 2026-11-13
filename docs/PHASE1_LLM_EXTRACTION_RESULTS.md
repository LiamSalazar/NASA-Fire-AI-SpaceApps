# NVIDIA extraction execution

Model: `nvidia/nemotron-3.5-lightning-30b-a3b`, through NVIDIA's OpenAI-compatible endpoint, temperature 0, non-streaming, thinking disabled. The credential was supplied only in the execution environment and is not stored here.

Six real NASA passages were processed and cached: curated NTRS 20205007829 pages 7/16 and newly acquired SoFIE NTRS 20200000361 passages. The cache key includes checksum, passage fingerprint, model, extractor version, and prompt version.

| Source | Candidates | Validated | Review | Rejected |
|---|---:|---:|---:|---:|
| Curated NTRS 20205007829 | 11 | 1 intervention | 10 | 0 |
| New SoFIE NTRS 20200000361 | 12 | 2 reported observations | 10 | 0 |

All 23 candidates had a contiguous exact span verified against their registry passage. Type distribution: 1 intervention, 2 reported experimental observations, 8 proposed NASA conclusions, 6 proposed safety implications, and 6 proposed open questions. The 20 high-risk classifications were routed to review; no LLM candidate directly entered RDF. This is intentionally not a claim of scientific classification accuracy. The curated regression recovered the known intervention but missed/overproduced safety categories, so precision/recall are not claimed as gold metrics beyond span presence (23/23).
