"""Reverify saved actual model drafts without rerunning generation or organizing.

This measures statement recovery, not a replay of complete conversational quality.
Original raw live receipts are immutable inputs. No draft text is changed beyond
verified inline locator syntax handled by the production acceptance service.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nasa_fire_ai.services.conversation import ConversationService
from nasa_fire_ai.services.search import ScientificSearchService
from nasa_fire_ai.services.semantic_support import LocalEntailment


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--nli", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output must be new")
    original = json.loads(args.run.read_text())
    engine = ScientificSearchService(ROOT / "data/snapshots/hackathon-20261105-v9", ROOT)
    service = ConversationService(engine, entailment=LocalEntailment(args.nli))
    report = {
        "mode": "saved-draft-verification-replay",
        "cases": [],
        "limitations": [
            "No fresh generation or relevance review; statement preservation is not full conversational acceptance."
        ],
    }
    try:
        for case in original["cases"]:
            old = case.get("trace", {})
            anchors = old.get("supplied_supports") or {
                a["support_id"]: a for a in old.get("support_inventory", [])
            }
            trace = {"verification": [], "verification_stage": "draft"}
            citations, numbers = [], {}
            service._alignment_checks = 0
            accepted, rejected = service._accept_segments(
                old.get("draft", {}).get("segments", []), anchors, trace, citations, numbers
            )
            for attempt in old.get("repairs", []):
                trace["verification_stage"] = "repair-" + str(attempt["attempt"])
                trace["repair_targets"] = attempt["requested_statements"]
                permitted = {
                    i: anchors[i] for i in attempt["permitted_support_ids"] if i in anchors
                }
                repaired, failed = service._accept_segments(
                    attempt.get("draft", {}).get("segments", []),
                    permitted,
                    trace,
                    citations,
                    numbers,
                )
                accepted.extend(repaired)
                rejected.extend(failed)
            checks = []
            for citation in citations:
                for support in citation["supports"]:
                    raw = engine.registry.resolve(support["evidence_id"])
                    checks.append(
                        " ".join(support["passage"].split()) in " ".join(raw["text"].split())
                    )
            row = {
                "id": case["id"],
                "accepted_paragraphs": accepted,
                "rejected": rejected,
                "trace": trace,
                "citations": citations,
                "source_checks": checks,
            }
            report["cases"].append(row)
            print(case["id"], len(accepted), len(rejected), flush=True)
    finally:
        engine.close()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
