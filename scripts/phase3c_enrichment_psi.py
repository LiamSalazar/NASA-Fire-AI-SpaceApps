"""Reconcile scoped official inventory with local files and runtime knowledge."""

import csv
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.psi import PSIClient


def main():
    out = ROOT / "artifacts/phase3c_enrichment_psi_v1.json"
    if out.exists():
        raise FileExistsError(out)
    registry = EvidenceRegistry(ROOT / "data/index/evidence.sqlite")
    inv = json.loads((ROOT / "artifacts/phase3c_knowledge_psi_inventory_v1.json").read_text())
    metadata = list(
        csv.DictReader((ROOT / "data/raw/upstream_nasa_space_apps/psi/psi_index.csv").open())
    )
    records = json.loads((ROOT / "data/canonical/records.json").read_text())

    def normalized(s):
        return re.sub(r"[^a-z0-9]", "", s.lower()).removesuffix("complete")

    rows = []
    for original in inv["rows"]:
        name = original["investigation_name"]
        matches = [
            m
            for m in metadata
            if normalized(name) in [normalized(m["title"]), normalized(m["acronym"])]
        ]
        if name in ["DAFT", "DAFT-2"]:
            matches = [m for m in metadata if name in m["acronym"].split(" / ")]
        if normalized(name) == "acmesflames":
            matches = [m for m in metadata if normalized(m["acronym"]) == "acmesflame"]
        paths = [
            p
            for m in matches
            for p in (ROOT / "data/raw").rglob(m["accession"] + "*")
            if p.is_file()
        ]
        csvs = [p for p in paths if p.suffix == ".csv" and "manifest" not in p.name]
        sids = {m["accession"].lower() for m in matches}
        canonical = [
            r for r in records if any(e["source_id"] in sids for e in r.get("evidence_refs", []))
        ]
        discovery_terms = [name] + [m["title"] for m in matches]
        doc = registry.search(" ".join(discovery_terms), limit=10)
        # Lexical documentary exposure is not investigation identity verification.
        documentary = [
            p["evidence_id"]
            for p in doc
            if any(normalized(t) in normalized(p["text"]) for t in discovery_terms)
        ]
        runs = [r for r in canonical if r["type"] == "ExperimentalRunRecord"]
        status = (
            "PARTIALLY_STRUCTURED"
            if runs
            else "STRUCTURED_DATA_AVAILABLE"
            if csvs
            else "DOCUMENTARY_ONLY"
            if documentary
            else "NOT_ACQUIRED"
        )
        rows.append(
            {
                "investigation": name,
                "official_inventory": inv["authority"],
                "psi_metadata_matches": matches,
                "identifier_status": "SOURCE_METADATA_MATCH" if matches else "UNRESOLVED",
                "local_files": [str(p.relative_to(ROOT)) for p in paths],
                "table_files": [str(p.relative_to(ROOT)) for p in csvs],
                "canonical_types": dict(Counter(r["type"] for r in canonical)),
                "canonical_runs": len(runs),
                "documentary_evidence": documentary,
                "state": status,
                "priority": 1 if csvs and not runs else 2 if not runs else 3,
                "next_action": "Validate table schemas and evidence row identities; stage scientific roles before publication"
                if csvs and not runs
                else "Resolve official dataset metadata and acquisition gaps; documentary mention is not dataset coverage",
                "coverage_complete": False,
            }
        )
    acquired = []
    client = PSIClient(ROOT / "data/raw/enrichment")
    for accession in ["PSI-68", "PSI-107"]:
        try:
            result = client.get_investigation(accession)
            acquired.append(
                {
                    "accession": accession,
                    "status": "ACQUIRED",
                    "path": str(result.cache_path.relative_to(ROOT)),
                    "url": result.source_url,
                    "sha256": hashlib.sha256(result.cache_path.read_bytes()).hexdigest(),
                    "prior_exposure": "PREVIOUSLY_LISTED_INVESTIGATION",
                    "publication_status": "REVIEW_REQUIRED",
                    "canonical_facts_added": 0,
                }
            )
        except Exception as exc:  # noqa: BLE001
            acquired.append(
                {
                    "accession": accession,
                    "status": "FAILED",
                    "error_type": type(exc).__name__,
                    "error": str(exc)[:500],
                }
            )
    out.write_text(
        json.dumps(
            {
                "universe": len(rows),
                "state_counts": dict(Counter(r["state"] for r in rows)),
                "rows": rows,
                "bounded_acquisition": acquired,
                "limit": "19 listed investigations; not all NASA knowledge. Local index download counts are historical remote-machine receipts, not proof files exist here.",
                "refresh": "Refresh official inventory and PSI versions monthly; compare source digests, acquire changed revisions append-only; isolate first-pass unseen sources.",
            },
            indent=2,
        )
    )
    print(
        json.dumps(
            {
                "investigations": len(rows),
                "states": dict(Counter(r["state"] for r in rows)),
                "acquisition": [a["status"] for a in acquired],
            }
        )
    )


if __name__ == "__main__":
    main()
