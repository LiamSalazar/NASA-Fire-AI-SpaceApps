# Generic ingestion V2

V2 separates physical acquisition from semantic publication. A generic table profiler
retains headers, units, type/range form, nullability, and samples. The semantic resolver
uses canonical identity, approved alias, normalized identity, dimensional compatibility,
then staging; it never guesses a canonical identity. Unknown semantics do not prevent
source registration, documentary indexing, or citation. Holdout execution used an
isolated Evidence Registry, not the frozen baseline index.
