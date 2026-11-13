"""Optional original PDF page input; image interpretation never grants approval."""

import base64
import hashlib
from pathlib import Path

import pymupdf


def table_page_images(package, root, tables):
    """Render whole original table pages with independently checkable identities.

    No image data or paths enter RDF. Images exist only in the outbound request;
    receipts retain PDF checksums, page indexes, pixel hashes and full-page bounds.
    """
    images, receipts = [], []
    requested = {(t["input_sha256"], t["physical_pdf_page"]) for t in tables}
    for manifest in package["inputs"]:
        pages = sorted(p for sha, p in requested if sha == manifest["sha256"])
        if not pages:
            continue
        path = Path(root) / manifest["stored_input"]
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != manifest["sha256"]:
            raise ValueError("Original PDF changed before multimodal inference")
        with pymupdf.open(stream=data, filetype="pdf") as pdf:
            for page_number in pages:
                page = pdf[page_number - 1]
                scale = min(2, 1600 / max(page.rect.width, page.rect.height))
                png = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False).tobytes(
                    "png"
                )
                evidence = next(
                    e
                    for e in package["evidence"]
                    if e["checksum"] == manifest["sha256"] and e["page"] == page_number
                )
                receipts.append(
                    {
                        "source_id": evidence["source_id"],
                        "evidence_id": evidence["evidence_id"],
                        "pdf_sha256": manifest["sha256"],
                        "physical_pdf_page": page_number,
                        "page_bbox": list(page.rect),
                        "png_sha256": hashlib.sha256(png).hexdigest(),
                        "scientific_status": "UNAPPROVED_VISUAL_CONTEXT_REQUIRES_ORIGINAL_SOURCE_VALIDATION",
                    }
                )
                images.append("data:image/png;base64," + base64.b64encode(png).decode())
    return images, receipts
