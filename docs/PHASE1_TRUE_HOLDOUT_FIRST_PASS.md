# True holdout first pass: FLEX

Recorded on 2026-10-03 before adding any FLEX-specific semantic mapping.

## Qualification

FLEX was not used to design the MVP parser or the BASS/SAFFIRE structured mappings. It is a distinct liquid-droplet combustion family, represented by the official NTRS 20150023456 *FLEX Experiment Data Archive*. Its input is a 40.9 MiB NASA technical report/documentary archive rather than a PSI experimental CSV.

## First-pass execution

The generic official-URL adapter acquired the PDF and generic deterministic segmentation produced 317 FTS/evidence passages. No source-specific semantic parser, ontology change, or FLEX condition mapping was introduced.

| Item | First-pass result |
| --- | --- |
| Source format | PDF / documentary archive |
| Structured table parser | Not applied; no exported machine-readable table was used |
| Automatically mapped runs | 0 |
| Published scientific runs | 0 |
| Documentary publication | pending generic document-identity publication |
| Fields/concepts encountered | liquid-fuel droplet, droplet size, flame size, regression, cool flame, extinction, vapor cloud |
| Unknown/ambiguous mappings | intentionally not mapped on first pass |
| Source-specific semantic code additions | 0 |

## Interpretation

The architecture generalized for acquisition, immutable provenance, segmentation, Evidence Registry storage, and FTS indexing. It did not claim experimental rows from narrative/appendix material. Novel terms are candidates for review rather than ontology additions. Any later change is limited to generic candidate extraction/validation, not a FLEX-specific scientific rule.
