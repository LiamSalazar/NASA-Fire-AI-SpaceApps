#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry

p = argparse.ArgumentParser()
sub = p.add_subparsers(dest="action", required=True)
sub.add_parser("list")
show = sub.add_parser("show")
show.add_argument("review_id")
for action in ("approve", "reject", "needs-mapping", "ambiguous", "change-type"):
    q = sub.add_parser(action)
    q.add_argument("review_id")
    q.add_argument("--reason", default="")
    q.add_argument("type", nargs="?")
a = p.parse_args()
r = EvidenceRegistry(Settings().registry_path)
if a.action == "list":
    print(
        json.dumps(
            [
                dict(x)
                for x in r.db.execute(
                    "select * from review_queue where status='PENDING' order by created_at"
                )
            ],
            indent=2,
        )
    )
elif a.action == "show":
    print(
        json.dumps(
            dict(
                r.db.execute(
                    "select * from review_queue where review_id=?", (a.review_id,)
                ).fetchone()
            ),
            indent=2,
        )
    )
else:
    status = {
        "approve": "APPROVED",
        "reject": "REJECTED",
        "needs-mapping": "NEEDS_MAPPING",
        "ambiguous": "AMBIGUOUS",
        "change-type": "APPROVED",
    }[a.action]
    r.decide_review(a.review_id, status, a.reason, a.type)
    print(json.dumps({"review_id": a.review_id, "status": status}))
