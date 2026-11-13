"""Bounded official NTRS discovery with isolated append-only acquisition."""

import hashlib
import json
from pathlib import Path

import httpx
import pymupdf

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts"
OUT = ART / "phase3c_knowledge_discovery_v1.json"


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    rows, failures = {}, []
    client = httpx.Client(timeout=40, follow_redirects=True)
    for keyword in ["microgravity combustion", "spacecraft fire suppression"]:
        try:
            response = client.get(
                "https://ntrs.nasa.gov/api/citations/search",
                params={"keyword": keyword, "page.size": 20},
            )
            response.raise_for_status()
            for result in response.json().get("results", []):
                rid = str(result.get("id"))
                rows[rid] = {
                    "nasa_id": rid,
                    "title": result.get("title"),
                    "metadata": result,
                    "state": "DISCOVERED",
                    "query": keyword,
                }
        except Exception as exc:  # noqa: BLE001 - bounded external service boundary
            failures.append({"query": keyword, "error": type(exc).__name__})
    # Deliberate coverage-gap sources exposed by the official source audit; not blind holdouts.
    for rid in ["20210017780", "20220012861"]:
        try:
            response = client.get(f"https://ntrs.nasa.gov/api/citations/{rid}")
            response.raise_for_status()
            metadata = response.json()
            rows[rid] = {
                "nasa_id": rid,
                "title": metadata.get("title"),
                "metadata": metadata,
                "state": "IN_SCOPE",
                "selection": "fire-safety coverage audit",
                "evaluation_role": "EXPOSED_DEVELOPMENT_SOURCE",
            }
            downloads = metadata.get("downloads", [])
            pdf = next(
                (d for d in downloads if str(d.get("name", "")).lower().endswith(".pdf")), None
            )
            if not pdf:
                raise ValueError("no authoritative PDF download")
            link = pdf.get("links", {}).get("pdf") or pdf.get("links", {}).get("original")
            if not link:
                raise ValueError("download link missing")
            url = link if link.startswith("https://") else "https://ntrs.nasa.gov" + link
            path = ROOT / f"data/raw/phase3c-knowledge-ntrs-{rid}.pdf"
            if not path.exists():
                download = client.get(url)
                download.raise_for_status()
                if len(download.content) > 50 * 1024 * 1024 or not download.content.startswith(
                    b"%PDF"
                ):
                    raise ValueError("invalid or oversized PDF")
                with path.open("xb") as handle:
                    handle.write(download.content)
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            doc = pymupdf.open(path)
            pages = [
                {"physical_pdf_page": i + 1, "text": page.get_text()} for i, page in enumerate(doc)
            ]
            parsed = ART / f"phase3c_knowledge_ntrs_{rid}_parsed_v1.json"
            if not parsed.exists():
                parsed.write_text(
                    json.dumps({"nasa_id": rid, "sha256": digest, "pages": pages}, indent=2)
                )
            rows[rid].update(
                {
                    "state": "PARSED",
                    "acquired": True,
                    "url": url,
                    "sha256": digest,
                    "physical_pages": len(pages),
                    "characters": sum(len(p["text"]) for p in pages),
                    "publication_status": "REVIEW_REQUIRED",
                    "isolated_from_runtime_registry": True,
                }
            )
        except Exception as exc:  # noqa: BLE001 - bounded external service boundary
            failures.append({"nasa_id": rid, "error": type(exc).__name__, "detail": str(exc)[:300]})
    OUT.write_text(
        json.dumps(
            {
                "scope": "Bounded NTRS microgravity combustion and spacecraft fire suppression metadata queries; selected fire-safety gaps",
                "complete_nasa_universe": False,
                "metadata_limit_per_query": 20,
                "sources": list(rows.values()),
                "failures": failures,
            },
            indent=2,
        )
    )
    print(
        json.dumps(
            {
                "discovered": len(rows),
                "acquired_parsed": sum(bool(r.get("acquired")) for r in rows.values()),
                "failures": failures,
            }
        )
    )


if __name__ == "__main__":
    main()
