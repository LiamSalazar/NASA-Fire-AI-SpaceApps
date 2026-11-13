"""Current official PSI scope snapshot plus independent local coverage levels."""

import argparse
import hashlib
import html
import json
import re
import sqlite3
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
URL = "https://www.nasa.gov/physical-sciences-informatics-psi/psi-investigations-by-research-area/"


def audit(directory):
    response = httpx.get(URL, follow_redirects=True, timeout=30)
    response.raise_for_status()
    source = response.text
    start = source.find('id="combustion-science"')
    end = source.find("<h2", start)
    if start < 0 or end < 0:
        raise ValueError("Official inventory layout changed; scope extraction needs review")
    block = source[start:end]
    names = [
        html.unescape(re.sub("<[^>]+>", "", name)).strip()
        for name in re.findall(r"<strong>(.*?)</strong>", block, re.DOTALL)
    ]
    names = [name for name in names if "|" not in name]
    (directory / "official_psi_inventory.html").write_bytes(response.content)
    db = sqlite3.connect(f"file:{ROOT / 'data/index/evidence.sqlite'}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    sources = [dict(r) for r in db.execute("SELECT * FROM sources")]
    records = json.loads((ROOT / "data/canonical/records.json").read_text())
    structured_ids = {ref["source_id"] for r in records for ref in r.get("evidence_refs", [])}
    levels = []
    # Registry identity and source-backed domain text determine this local ledger's
    # scope candidates; it is not an exhaustive NTRS relevance adjudication.
    relevance = re.compile(
        r"microgravity|combustion|flame|spacecraft.{0,30}fire|fire.{0,30}(spacecraft|suppress)|saffire|burning and suppression",
        re.IGNORECASE,
    )
    for item in sources:
        if (
            not relevance.search(item.get("title") or "")
            and not str(item.get("source_id", "")).startswith("psi-")
            and "6001" not in str(item.get("nasa_id", ""))
        ):
            continue
        sid = item["source_id"]
        passage_ids = {
            r[0]
            for r in db.execute(
                "SELECT p.evidence_id FROM passages p JOIN documents d USING(document_id) WHERE d.source_id=?",
                (sid,),
            )
        }
        fts_ids = {r[0] for r in db.execute("SELECT evidence_id FROM passages_fts")}
        filename = item.get("filename")
        path = ROOT / filename if filename else None
        if path and not path.is_file():
            alternatives = list((ROOT / "data/raw").rglob(Path(filename).name))
            path = alternatives[0] if len(alternatives) == 1 else None
        acquired = bool(path and path.is_file())
        actual = hashlib.sha256(path.read_bytes()).hexdigest() if acquired else None
        verified = bool(actual and actual == item.get("sha256"))
        structured = sid in structured_ids
        levels.append(
            {
                "source_id": sid,
                "title": item["title"],
                "url": item.get("url"),
                "identified": True,
                "acquired": acquired,
                "digest_verified": verified,
                "parsed": bool(passage_ids),
                "searchable": bool(passage_ids) and passage_ids <= fts_ids,
                "scientifically_structured": structured,
                "contextually_linked": "NOT_MEASURED_PER_SOURCE",
                "reviewed": "PARTIAL" if structured else "PENDING",
                "blocked": not acquired,
                "priority": 1 if not structured else 2,
                "next_action": "Verify missing original/acquisition locator"
                if not acquired
                else "Review quantity, identity, scope and source attribution contracts",
                "matching_limit": "Local title-based domain candidate; independent scientific relevance review remains required",
            }
        )
    inventory = []
    metadata = []
    for path in (ROOT / "data/raw").rglob("PSI-*_metadata.json"):
        document = json.loads(path.read_text())
        for study in document.get("studies", []):
            metadata.append(
                {
                    "source_id": study["identifier"],
                    "title": study.get("title", ""),
                    "path": str(path.relative_to(ROOT)),
                }
            )
    normalize = lambda x: re.sub(r"[^a-z0-9]+", "", x.lower())
    for name in names:
        exact = [m for m in metadata if normalize(m["title"]) == normalize(name)]
        candidates = [m for m in metadata if normalize(name) in normalize(m["title"])]
        inventory.append(
            {
                "investigation": name,
                "identified": True,
                "authority": URL,
                "exact_metadata_matches": exact,
                "possible_title_matches": candidates,
                "acquired": "VERIFIED_METADATA_ONLY"
                if exact
                else "IDENTITY_RECONCILIATION_REQUIRED",
                "scientific_completeness": "NOT_ESTABLISHED",
                "priority": 1 if any(t in name.lower() for t in ["bass", "saffire", "flex"]) else 2,
                "next_action": "Reconcile official PSI IDs, dataset inventories, public NTRS and experiment reports; do not treat metadata as complete experimental coverage",
            }
        )
    result = {
        "official_inventory_url": URL,
        "retrieved_at": response.headers.get("date"),
        "inventory_sha256": hashlib.sha256(response.content).hexdigest(),
        "official_combustion_investigations": inventory,
        "local_domain_sources": levels,
        "counts": {
            level: sum(bool(row[level]) for row in levels)
            for level in (
                "identified",
                "acquired",
                "digest_verified",
                "parsed",
                "searchable",
                "scientifically_structured",
                "blocked",
            )
        },
        "ontology_scope": "Flame in Freefall combustion and spacecraft fire safety; no unrestricted NASA ingestion",
        "limitations": [
            "Official PSI combustion list is one verified inventory, not universal public NASA completeness.",
            "Source-level downloaded/searchable/structured/reviewed coverage is independent.",
            "NTRS relevance reconciliation and structured dataset completeness still require source-specific review.",
            "Context coverage per source is unmeasured; no semantic completeness claim.",
        ],
    }
    (directory / "coverage_ledger.json").write_text(json.dumps(result, indent=2))
    print(json.dumps({"official_investigations": len(inventory), "local_counts": result["counts"]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args()
    args.directory.mkdir(parents=True, exist_ok=True)
    audit(args.directory)
