"""Frozen architecture holdout campaign; structural selection and isolated ingestion.

Selection uses no column labels or scientific claims. All candidate outcomes are
persisted before selection. Previously acquired contents exclude a source.
"""

import argparse
import csv
import hashlib
import json
import re
import sys
import urllib.request
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from phase3c_native_benchmarks import check_freeze, native_guard

from nasa_fire_ai.evaluation.phase3c import append_result, digest, freeze_json, proportion
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.generic import profile_table
from nasa_fire_ai.ingestion.psi import PSIClient, parse_experimental_table
from nasa_fire_ai.ingestion.semantic import ingest_generic_table, load_semantic_registry
from nasa_fire_ai.query.native import SemanticGraph, execute_native
from nasa_fire_ai.query.v2 import QueryIntentV2

ART = ROOT / "artifacts"
CACHE = ART / "phase3c_holdout_acquisition"
# Full bounded official search result pool, frozen before structural preflight.
NTRS_POOL = [
    "19870006579",
    "20205000063",
    "20240002981",
    "20230004106",
    "20240007488",
    "19900003329",
    "20240008602",
    "20040161216",
    "20240015018",
    "20240014247",
    "19880010969",
    "20230018172",
    "19940022933",
    "20240014551",
    "20240006980",
    "20260000342",
]


def acquire(url, path):
    if not path.exists():
        request = urllib.request.Request(url, headers={"User-Agent": "NASA-evidence-phase3c/1.0"})
        with urllib.request.urlopen(request, timeout=35) as response:
            content = response.read()
        with path.open("xb") as stream:
            stream.write(content)
    return path.read_bytes()


def historical_exposure():
    exposed = {}
    for folder in ("docs", "evals", "domain", "artifacts", "data"):
        for path in (ROOT / folder).rglob("*"):
            if not path.is_file() or "phase3c" in str(path).lower() or path.name == "psi_index.csv":
                continue
            text = str(path.relative_to(ROOT))
            if (
                path.suffix in {".json", ".yaml", ".md", ".ttl", ".csv", ".txt"}
                and path.stat().st_size < 10_000_000
            ):
                text += "\n" + path.read_text(errors="replace")
            for value in re.findall(r"PSI-\d+|(?<!\d)(?:19|20)\d{9}(?!\d)", text, re.IGNORECASE):
                exposed.setdefault(value.upper(), set()).add(str(path.relative_to(ROOT)))
    registry = EvidenceRegistry(ROOT / "data/index/evidence.sqlite")
    for row in registry.db.execute("SELECT source_id,nasa_id FROM sources"):
        for value in re.findall(
            r"psi-\d+|(?:19|20)\d{9}", " ".join(str(x) for x in row), re.IGNORECASE
        ):
            exposed.setdefault(value.upper(), set()).add("EvidenceRegistry.sources")
    return exposed


def select():
    check_freeze()
    CACHE.mkdir(parents=True, exist_ok=True)
    exposed = historical_exposure()
    psi = list(
        csv.DictReader((ROOT / "data/raw/upstream_nasa_space_apps/psi/psi_index.csv").open())
    )
    pool = [{"source_id": r["accession"], "kind": "structured", "url": r["url"]} for r in psi]
    pool += [
        {"source_id": sid, "kind": "documentary", "url": f"https://ntrs.nasa.gov/citations/{sid}"}
        for sid in NTRS_POOL
    ]
    pool.sort(key=lambda r: (r["kind"], r["source_id"]))
    receipts_path = ART / "phase3c_holdout_preflight.jsonl"
    prior = (
        {r["source_id"]: r for r in map(json.loads, receipts_path.read_text().splitlines())}
        if receipts_path.exists()
        else {}
    )
    rows = []
    client = PSIClient(CACHE)
    for position, candidate in enumerate(pool):
        sid = candidate["source_id"]
        row = {
            **candidate,
            "ordering_position": position,
            "eligible": sid.upper() not in exposed,
            "exclusion_reasons": sorted(exposed.get(sid.upper(), [])),
            "selected": False,
        }
        if not row["eligible"]:
            rows.append(row)
            continue
        if sid in prior:
            rows.append(prior[sid])
            continue
        try:
            if row["kind"] == "structured":
                response = client.get_experimental_table(sid)
                table = parse_experimental_table(response.value)
                profiles = profile_table(table)
                # Do not persist labels/samples in the selection record.
                row["structure"] = {
                    "bytes": response.cache_path.stat().st_size,
                    "rows": len(table),
                    "columns": len(profiles),
                    "numeric_columns": sum(p.datatype == "numeric" for p in profiles),
                    "nonconstant_columns": sum(
                        len({str(r.get(p.label)) for r in table}) > 1 for p in profiles
                    ),
                }
                row["cache_path"] = str(response.cache_path.relative_to(ROOT))
            else:
                metadata = json.loads(
                    acquire(
                        f"https://ntrs.nasa.gov/api/citations/{sid}", CACHE / f"{sid}-metadata.json"
                    )
                )
                downloads = sorted(
                    [
                        r
                        for r in metadata.get("downloads", [])
                        if r.get("mimetype") == "application/pdf"
                        or r.get("name", "").lower().endswith(".pdf")
                    ],
                    key=lambda r: r.get("name", ""),
                )
                if not downloads:
                    raise LookupError("no PDF download")
                link = downloads[0].get("links", {}).get("pdf") or downloads[0].get(
                    "links", {}
                ).get("original")
                url = link if link.startswith("https://") else "https://ntrs.nasa.gov" + link
                content = acquire(url, CACHE / f"{sid}.pdf")
                with pymupdf.open(stream=content, filetype="pdf") as doc:
                    row["structure"] = {"bytes": len(content), "pages": len(doc)}
                row["cache_path"] = str((CACHE / f"{sid}.pdf").relative_to(ROOT))
                row["download_url"] = url
            row["preflight"] = "SUCCESS"
        except (OSError, ValueError, LookupError, TypeError) as exc:
            row["preflight"] = "FAILURE"
            row["error_type"] = type(exc).__name__
        append_result(receipts_path, row)
        rows.append(row)
        print(
            json.dumps(
                {"source_id": sid, "preflight": row["preflight"], "structure": row.get("structure")}
            ),
            flush=True,
        )
    selected = []
    for kind in ("structured", "documentary"):
        choices = [r for r in rows if r["kind"] == kind and r.get("preflight") == "SUCCESS"]

        def preferred(r, kind=kind):
            s = r["structure"]
            return (
                (s["rows"] >= 20 and s["columns"] >= 5 and s["nonconstant_columns"] >= 2)
                if kind == "structured"
                else s["pages"] >= 5
            )

        choices.sort(key=lambda r: (not preferred(r), r["source_id"]))
        for row in choices[:2]:
            row["selected"] = True
            selected.append(row)
    freeze_json(
        ART / "phase3c_holdout_candidates.json",
        {
            "pool": rows,
            "selection_rule": "prefer structural thresholds, then stable source-ID order; first two per kind",
            "catalog_metadata_exception": "PSI metadata-only index is the candidate pool, not acquired source contents",
            "architecture_freeze_digest": digest(ART / "phase3c_native_freeze_second_pass.json"),
        },
    )
    freeze_json(
        ART / "phase3c_holdout_manifest.json",
        {
            "selected": selected,
            "candidate_pool_digest": digest(ART / "phase3c_holdout_candidates.json"),
        },
    )


def ingest():
    check_freeze()
    manifest = json.loads((ART / "phase3c_holdout_manifest.json").read_text())
    evidence = EvidenceRegistry(ART / "phase3c_holdout_evidence.sqlite")
    store = SemanticGraph(load_semantic_registry(ROOT / "domain/semantic_registry.yaml"))
    results = []
    for row in manifest["selected"]:
        sid = row["source_id"]
        path = ROOT / row["cache_path"]
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        evidence.add_source(
            {
                "source_id": sid,
                "source_type": row["kind"],
                "title": sid,
                "url": row["url"],
                "sha256": sha,
            }
        )
        evidence.add_document(sid, sid, sid)
        passages = []
        if row["kind"] == "structured":
            table = parse_experimental_table(path.read_text(encoding="utf-8-sig"))
            passages = [
                (f"E-{sid}-row-{i}", None, json.dumps(value, sort_keys=True))
                for i, value in enumerate(table)
            ]
        else:
            with pymupdf.open(path) as doc:
                for i, page in enumerate(doc):
                    text = page.get_text()
                    for j in range(0, len(text), 1600):
                        passages.append((f"E-{sid}-page-{i + 1}-{j}", i + 1, text[j : j + 1600]))
        for eid, page, text in passages:
            evidence.add_passage(
                {
                    "evidence_id": eid,
                    "document_id": sid,
                    "page": page,
                    "section": None,
                    "text": text,
                    "start_offset": None,
                    "end_offset": None,
                    "raw_file": str(path.relative_to(ROOT)),
                    "checksum": sha,
                }
            )
        info = {
            "source_id": sid,
            "kind": row["kind"],
            "acquisition": "SUCCESS",
            "passages": len(passages),
            "structure": row["structure"],
        }
        if row["kind"] == "structured":
            info.update(ingest_generic_table(table, sid, [p[0] for p in passages], store, evidence))
        else:
            store.add_entity(sid, "Document", [p[0] for p in passages], [sid])
            store.add_entity(sid, "Publication", [p[0] for p in passages], [sid])
        results.append(info)
        append_result(ART / "phase3c_holdout_ingestion_receipts.jsonl", info)
    store.graph.serialize(destination=str(ART / "phase3c_holdout_graph.ttl"), format="turtle")
    staging = evidence.staged_semantic_candidates()
    freeze_json(
        ART / "phase3c_holdout_first_pass.json",
        {
            "holdouts": results,
            "manifest_digest": digest(ART / "phase3c_holdout_manifest.json"),
            "architecture_freeze_digest": digest(ART / "phase3c_native_freeze_second_pass.json"),
            "metrics": {
                "source_ingestion": proportion(len(results), len(manifest["selected"])),
                "structured_profiling": proportion(
                    sum(r["kind"] == "structured" for r in results),
                    sum(r["kind"] == "structured" for r in manifest["selected"]),
                ),
                "staging_provenance": proportion(
                    sum(
                        bool(r.get("source_id") and r.get("evidence_id") and r.get("provenance"))
                        for r in staging
                    ),
                    len(staging),
                ),
                "false_canonicalization": "NOT_INDEPENDENTLY_REVIEWED; automatic authority is frozen-registry exact labels/aliases only",
            },
            "source_specific_semantic_code_additions": 0,
        },
    )


def probes():
    check_freeze()
    manifest = json.loads((ART / "phase3c_holdout_manifest.json").read_text())
    evidence = EvidenceRegistry(ART / "phase3c_holdout_evidence.sqlite")
    store = SemanticGraph(load_semantic_registry(ROOT / "domain/semantic_registry.yaml"))
    store.graph.parse(ART / "phase3c_holdout_graph.ttl")
    store.registry.entities.update(store.entities())
    rows = []
    for source in manifest["selected"]:
        sid = source["source_id"]
        candidates = evidence.db.execute(
            "SELECT evidence_id,text FROM passages WHERE document_id=? ORDER BY evidence_id", (sid,)
        ).fetchall()
        for eid, text in candidates[:5]:
            tokens = re.findall(r"[A-Za-z]{4,}", text)
            query = " ".join(dict.fromkeys(tokens[:8]))
            target = "Document" if source["kind"] == "documentary" else "ExperimentalRun"
            with native_guard():
                result = execute_native(
                    QueryIntentV2(targets=[target], source_constraints=[sid]),
                    query,
                    store,
                    evidence,
                    limit=10,
                )
            returned = [p["evidence_id"] for p in result.bundle.evidence_passages]
            rank = returned.index(eid) + 1 if eid in returned else None
            rows.append(
                {
                    "source_id": sid,
                    "kind": source["kind"],
                    "query": query,
                    "expected_evidence_id": eid,
                    "rank": rank,
                    "returned": returned,
                }
            )
    documentary = [r for r in rows if r["kind"] == "documentary"]
    n = len(documentary)
    freeze_json(
        ART / "phase3c_document_retrieval_results.json",
        {
            "probes": rows,
            "documentary_metrics": {
                f"Recall@{k}": proportion(
                    sum(r["rank"] is not None and r["rank"] <= k for r in documentary), n
                )
                for k in (1, 3, 5, 10)
            },
            "MRR": {
                "numerator": sum(1 / r["rank"] for r in documentary if r["rank"]),
                "denominator": n,
                "estimate": sum(1 / r["rank"] for r in documentary if r["rank"]) / n if n else None,
            },
            "limitation": "Literal passage probes; no reviewed scientific claim-classification accuracy or broad language-generalization claim",
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["select", "ingest", "probes"])
    args = parser.parse_args()
    {"select": select, "ingest": ingest, "probes": probes}[args.stage]()
