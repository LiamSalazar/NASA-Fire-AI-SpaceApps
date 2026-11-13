"""Export actual HTTP answers and original evidence for manual scientific review.

Resolution is mechanical. Semantic support, essential coverage and usefulness
require explicit source inspection; this script never infers those judgments.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.hackathon import verify_snapshot


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--campaigns", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Review packets are append-only")
    manifest = verify_snapshot(args.snapshot, ROOT)
    registry = EvidenceRegistry(
        args.snapshot / "evidence.sqlite", read_only=True, evidence_root=ROOT
    )
    cases = []
    for campaign in args.campaigns:
        for path in sorted(campaign.glob("*.json")):
            response = json.loads(path.read_text())
            if response.get("status") != 200 or "body" not in response:
                continue
            body = response["body"]
            ledger_path = campaign / (response["id"] + ".ledger.json")
            if not ledger_path.exists():
                ledger_path = ROOT / "data/index/claim_ledger" / (body["trace_id"] + ".json")
            ledger = json.loads(ledger_path.read_text())
            evidence_ids = {citation["evidence_id"] for citation in body["citations"]}
            evidence_ids.update(
                eid
                for claim in ledger["claims"]
                if claim.get("communicated")
                for eid in claim.get("cited_evidence_ids", [])
            )
            evidence = {}
            for eid in sorted(evidence_ids):
                original = registry.resolve(eid)
                evidence[eid] = original
            cases.append(
                {
                    "id": response["id"],
                    "response_path": str(path),
                    "response_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "ledger_sha256": hashlib.sha256(ledger_path.read_bytes()).hexdigest(),
                    "snapshot_id": body["snapshot_id"],
                    "question": response["request"]["message"],
                    "answer": body["answer"],
                    "claims": ledger["claims"],
                    "citations": body["citations"],
                    "registered_original_evidence": evidence,
                    "unresolved_emitted_evidence": [
                        eid for eid, value in evidence.items() if not value
                    ],
                    "information_needs": ledger["information_needs"],
                    "coverage_summary_machine_only": body.get("coverage_summary"),
                    "semantic_judgment": "PENDING_MANUAL_SOURCE_INSPECTION",
                }
            )
    registry.db.close()
    args.output.write_text(
        json.dumps(
            {
                "snapshot_id": manifest["snapshot_id"],
                "boundary": "Original evidence and mechanical resolution only; no automatic semantic-support, coverage or usefulness adjudication.",
                "cases": cases,
            },
            indent=2,
        )
        + "\n"
    )
    print(
        json.dumps(
            {
                "cases": len(cases),
                "unresolved_evidence": sum(len(c["unresolved_emitted_evidence"]) for c in cases),
            }
        )
    )


if __name__ == "__main__":
    main()
