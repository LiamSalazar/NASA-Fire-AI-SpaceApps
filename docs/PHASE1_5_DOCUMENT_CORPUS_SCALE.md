# Phase 1.5 managed documentary corpus scale

The upstream catalog contained 277 NTRS records. Of these, 275 had nonempty cached text and passed deterministic catalog verification: numeric NTRS ID, HTTPS `ntrs.nasa.gov/citations/<id>` URL, and a checksum-recorded text file. Two records lacked usable text; none failed the URL/identifier check.

The 275 verified cached texts were copied once into the immutable managed raw area, registered as `UPSTREAM_NTRS_TEXT_VERIFIED`, and indexed as documentary evidence only. They produced 275 versioned registry documents, 275 artifact records, 275 documentary-metadata records, and 5,206 newly managed passages. The registry now has 286 documents, 6,054 passages, and 6,054 FTS rows.

The import does not create canonical scientific records or RDF claims. Text provenance records the upstream path, canonical NASA citation URL, checksum, and the limited verification claim: catalog NTRS ID/URL verified and upstream text checksum recorded. It is not represented as a substituted official PDF byte stream.

Repeated import of the unchanged cache imported zero artifacts and added zero passages in 4.794 seconds. Integrity after import: zero versioned logical-passage duplicates, FTS orphans, evidence-reference orphans, candidate orphans, and review orphans.
