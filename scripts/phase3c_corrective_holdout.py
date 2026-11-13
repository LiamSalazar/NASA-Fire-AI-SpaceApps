"""Metadata-only expanded NASA search; deterministic isolated documentary holdout."""

import hashlib
import json
import re
import sys
from pathlib import Path

import httpx
import pymupdf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from phase3c_corrective_live import check_freeze
from phase3c_native_benchmarks import native_guard

from nasa_fire_ai.evaluation.phase3c import append_result, digest, freeze_json, proportion
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.semantic import load_semantic_registry
from nasa_fire_ai.query.native import SemanticGraph, execute_native
from nasa_fire_ai.query.v2 import QueryIntentV2

ART = ROOT / "artifacts"
VERSION = "v2" if "--expanded" in sys.argv else "v1"
CACHE = ART / f"phase3c_corrective_holdout_acquisition_{VERSION}"


def acquire(url, path):
    if not path.exists():
        response = httpx.get(url, timeout=35, follow_redirects=True)
        response.raise_for_status()
        with path.open("xb") as stream:
            stream.write(response.content)
    return path.read_bytes()


def main():
    check_freeze()
    CACHE.mkdir(exist_ok=True)
    candidates_path = ART / f"phase3c_corrective_holdout_candidates_{VERSION}.json"
    manifest_path = ART / f"phase3c_corrective_holdout_manifest_{VERSION}.json"
    # Search snippets exposed scientific text for these IDs; do not call them blind.
    snippet_ids = {
        "20250001364",
        "20020090250",
        "19970001589",
        "20250002347",
        "19970020606",
        "20160000593",
        "20260000641",
        "20205008449",
        "20050199458",
        "19930011022",
        "79490066403600",
        "19970020548",
        "19930013417",
        "19990062669",
        "20130004397",
        "20190032395",
        "19900003329",
    }
    if not candidates_path.exists():
        historical_texts = []
        for folder in ("docs", "evals", "domain", "artifacts", "data"):
            for p in (ROOT / folder).rglob("*"):
                if (
                    p.is_file()
                    and "phase3c_corrective_holdout" not in str(p)
                    and p.suffix.lower()
                    in {".json", ".jsonl", ".yaml", ".csv", ".md", ".txt", ".ttl"}
                    and p.stat().st_size < 20_000_000
                ):
                    historical_texts.append(
                        (str(p.relative_to(ROOT)), p.read_text(errors="replace"))
                    )
        search_url = (
            "https://ntrs.nasa.gov/api/citations/search?keyword="
            + ("combustion" if VERSION == "v2" else "microgravity%20combustion")
            + "&page.size=20"
        )
        metadata = json.loads(acquire(search_url, CACHE / "search-metadata.json"))
        pool = []
        for position, record in enumerate(sorted(metadata["results"], key=lambda r: str(r["id"]))):
            sid = str(record["id"])
            reasons = [
                name
                for name, text in historical_texts
                if re.search(rf"(?<!\d){re.escape(sid)}(?!\d)", text)
            ]
            if sid in snippet_ids:
                reasons.append("PRE_SELECTION_SEARCH_SNIPPET_EXPOSURE")
            row = {
                "source_id": sid,
                "ordering_position": position,
                "eligible": not reasons,
                "exclusion_reasons": reasons,
                "selected": False,
            }
            if not reasons:
                try:
                    details = json.loads(
                        acquire(
                            f"https://ntrs.nasa.gov/api/citations/{sid}",
                            CACHE / f"{sid}-metadata.json",
                        )
                    )
                    downloads = sorted(
                        [
                            d
                            for d in details.get("downloads", [])
                            if d.get("mimetype") == "application/pdf"
                            or d.get("name", "").lower().endswith(".pdf")
                        ],
                        key=lambda d: d.get("name", ""),
                    )
                    if not downloads:
                        raise LookupError("No PDF")
                    link = downloads[0].get("links", {}).get("pdf") or downloads[0].get(
                        "links", {}
                    ).get("original")
                    url = link if link.startswith("https://") else "https://ntrs.nasa.gov" + link
                    content = acquire(url, CACHE / f"{sid}.pdf")
                    with pymupdf.open(stream=content, filetype="pdf") as document:
                        row["structure"] = {"pages": len(document), "bytes": len(content)}
                    row["download_url"] = url
                    row["preflight"] = "SUCCESS"
                except (httpx.HTTPError, ValueError, LookupError, TypeError) as error:
                    row["preflight"] = "FAILURE"
                    row["error"] = {
                        "type": type(error).__name__,
                        "status": getattr(getattr(error, "response", None), "status_code", None),
                    }
            pool.append(row)
            append_result(ART / f"phase3c_corrective_holdout_preflight_{VERSION}.jsonl", row)
            print(
                json.dumps(
                    {"source": sid, "eligible": row["eligible"], "structure": row.get("structure")}
                ),
                flush=True,
            )
        successful = [r for r in pool if r.get("preflight") == "SUCCESS"]
        successful.sort(key=lambda r: (r["structure"]["pages"] < 5, r["source_id"]))
        selected = successful[:1]
        for r in selected:
            r["selected"] = True
        freeze_json(
            candidates_path,
            {
                "pool": pool,
                "search": search_url,
                "authority": "Metadata and PDF structural preflight only; no abstract/text used for selection",
            },
        )
        freeze_json(
            manifest_path,
            {
                "selected": selected,
                "candidates_digest": digest(candidates_path),
                "architecture_digest": digest(ART / "phase3c_corrective_native_freeze_v2.json"),
                "structured_status": "NO_NEW_ELIGIBLE_STRUCTURED_ARTIFACT in earlier bounded PSI pool; not a claim none exists anywhere",
            },
        )
    manifest = json.loads(manifest_path.read_text())
    result_path = ART / f"phase3c_corrective_holdout_first_pass_{VERSION}.json"
    if result_path.exists():
        print("Blind first pass already persisted; unchanged")
        return
    registry = EvidenceRegistry(ART / f"phase3c_corrective_holdout_evidence_{VERSION}.sqlite")
    store = SemanticGraph(load_semantic_registry(ROOT / "domain/semantic_registry.yaml"))
    results = []
    for selected in manifest["selected"]:
        sid = selected["source_id"]
        metadata = json.loads((CACHE / f"{sid}-metadata.json").read_text())
        title = metadata.get("title", sid)
        registry.add_source(
            {
                "source_id": sid,
                "source_type": "NTRS",
                "title": title,
                "url": f"https://ntrs.nasa.gov/citations/{sid}",
            }
        )
        registry.add_document(sid, sid, title)
        ids, probes = [], []
        with pymupdf.open(CACHE / f"{sid}.pdf") as document:
            for page_index, page in enumerate(document):
                for paragraph_index, paragraph in enumerate(re.split(r"\n\s*\n", page.get_text())):
                    if len(paragraph.split()) < 5:
                        continue
                    eid = f"E-corrective-{sid}-{page_index + 1}-{paragraph_index}"
                    registry.add_passage(
                        {
                            "evidence_id": eid,
                            "document_id": sid,
                            "page": page_index + 1,
                            "section": None,
                            "text": paragraph,
                            "start_offset": None,
                            "end_offset": None,
                            "raw_file": str(CACHE / f"{sid}.pdf"),
                            "checksum": hashlib.sha256(paragraph.encode()).hexdigest(),
                        }
                    )
                    ids.append(eid)
                    if len(probes) < 10:
                        probes.append({"id": eid, "query": " ".join(paragraph.split()[:10])})
        store.add_entity(sid, "Document", ids, [sid], {"id": sid, "title": title})
        freeze_json(
            ART / f"phase3c_corrective_holdout_query_gold_{VERSION}.json",
            {
                "probes": probes,
                "policy": "Literal source-backed passage identity, not scientific relevance or interpretation gold",
            },
        )
        ranks = []
        for probe in probes:
            with native_guard():
                execution = execute_native(
                    QueryIntentV2(targets=["Document"], source_constraints=[sid]),
                    probe["query"],
                    store,
                    registry,
                    limit=10,
                )
            ranked = [p["evidence_id"] for p in execution.bundle.evidence_passages]
            ranks.append(next((i for i, eid in enumerate(ranked, 1) if eid == probe["id"]), None))
        results.append(
            {
                "source_id": sid,
                "title": title,
                "structure": selected["structure"],
                "passages": len(ids),
                "probes": len(ranks),
                "ranks": ranks,
                "recall": {
                    f"Recall@{k}": proportion(
                        sum(r is not None and r <= k for r in ranks), len(ranks)
                    )
                    for k in (1, 3, 5, 10)
                },
            }
        )
    freeze_json(
        result_path,
        {
            "holdouts": results,
            "manifest_digest": digest(manifest_path),
            "zero_code_acquisition": proportion(len(results), len(manifest["selected"])),
            "scientific_facts_published": 0,
            "source_specific_scientific_code_additions": 0,
            "limitation": "One documentary source, literal lexical probes; no new structured scientific mapping benchmark",
        },
    )


if __name__ == "__main__":
    main()
