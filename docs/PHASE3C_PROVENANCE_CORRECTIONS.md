# Phase 3C citation-location audit

The Evidence Registry currently stores an integer `page` and section, but legacy extracted text does not always preserve a verifiable physical PDF page map. The controlled audit in `artifacts/phase3c_controlled_provenance_audit_v1.json` deliberately does not rewrite stored values.

- `E-382165f1a4516fa8`, NASA ID 20040053586, has `page_as_stored=1`; the local source available to this repository is a `.txt` extraction and no local source PDF page map was available. Physical PDF page is therefore unverified.
- `E-safety-saffire-suppression-open-question`, NASA ID 20205007829, has stored page 16 and section “Fire Suppression Requirements”. The exact normalized excerpt was found on physical PDF page 16 of `data/raw/ntrs-20205007829.pdf`.

No page fields or raw NASA sources were modified. The native renderer now labels unverified integers as “recorded page N (physical PDF page unverified)” and only says “PDF page N” when a passage explicitly carries a verified-location flag. Citations retain title, source identifier, official URL, section/page metadata and evidence ID. Review packet v2 additionally carries passage text, offsets, raw-file path and checksum when available. This avoids turning printed page labels or extracted chunk positions into a fabricated physical citation.
