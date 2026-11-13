"""Official PSI combustion scope inventory and reproducible acquisition backlog."""

import hashlib
import html
import json
import re
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
url = "https://www.nasa.gov/physical-sciences-informatics-psi/psi-investigations-by-research-area/"
response = httpx.get(url, follow_redirects=True, timeout=30)
response.raise_for_status()
source = response.text
start = source.find('id="combustion-science"')
end = source.find("<h2", start)
if start < 0 or end < 0:
    raise ValueError("Official page structure changed; review scope extraction")
block = source[start:end]
names = [
    html.unescape(re.sub("<[^>]+>", "", label)).strip()
    for label in re.findall(r"<strong>(.*?)</strong>", block, re.DOTALL)
]
names = [name for name in names if "|" not in name]
inventory = json.loads((ROOT / "artifacts/phase3c_knowledge_source_inventory_v1.json").read_text())
records = json.loads((ROOT / "data/canonical/records.json").read_text())
normalize = lambda text: re.sub(r"[^a-z0-9]+", "", text.lower())
rows = []
for name in names:
    matches = [
        r["source_id"] for r in inventory if normalize(r.get("title") or "") == normalize(name)
    ]
    structured = [
        r.get("id")
        for r in records
        if r["type"] == "InvestigationRecord" and normalize(r.get("title", "")) == normalize(name)
    ]
    rows.append(
        {
            "investigation_name": name,
            "authoritative_inventory_url": url,
            "scope": "IN_SCOPE",
            "acquisition_state": "DISCOVERED",
            "runtime_exact_title_matches": matches,
            "canonical_investigations": structured,
            "publication_state": "STRUCTURED" if structured else "REVIEW_REQUIRED",
            "priority": 1
            if not structured
            and (
                "suppression" in name.lower() or "saffire" in name.lower() or "bass" in name.lower()
            )
            else 2,
            "next_action": "Resolve official PSI identifier/downloads; check runtime metadata IDs and source digests before acquisition",
            "matching_limit": "Exact normalized titles only; absent match is not proof source missing",
        }
    )
out = ROOT / "artifacts/phase3c_knowledge_psi_inventory_v1.json"
if out.exists():
    raise FileExistsError(out)
out.write_text(
    json.dumps(
        {
            "authority": url,
            "html_sha256": hashlib.sha256(response.content).hexdigest(),
            "discovered_universe": len(rows),
            "canonical_exact_title_representation": {
                "numerator": sum(bool(r["canonical_investigations"]) for r in rows),
                "denominator": len(rows),
            },
            "rows": rows,
            "scope_completeness": "Official page snapshot only, not all NASA knowledge",
        },
        indent=2,
    )
)
print(
    json.dumps(
        {
            "official_scope_investigations": len(rows),
            "canonical_exact_title_matches": sum(bool(r["canonical_investigations"]) for r in rows),
        }
    )
)
