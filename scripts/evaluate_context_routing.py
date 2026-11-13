"""Replay fixed historical query jobs to isolate examination/context routing losses.

No provider, new relevance judgments or generated answers. This complements the
live conversation evaluator; it cannot establish answer quality.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--implementation-root", type=Path, default=ROOT)
    parser.add_argument(
        "--run", type=Path, default=ROOT / "artifacts/conversation_reliability_v1/live-frozen.json"
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output must be new")
    sys.path.insert(0, str(args.implementation_root / "src"))
    from nasa_fire_ai.services.conversation import ConversationService
    from nasa_fire_ai.services.search import ScientificSearchService

    run = json.loads(args.run.read_text())
    targets = json.loads((ROOT / "evals/phase56/answer_targets_v1.json").read_text())["targets"]
    report = {
        "mode": "offline fixed saved query replay; no generation or scientific adjudication",
        "input_sha256": hashlib.sha256(args.run.read_bytes()).hexdigest(),
        "implementation_hashes": {
            name: hashlib.sha256((args.implementation_root / name).read_bytes()).hexdigest()
            for name in [
                "src/nasa_fire_ai/services/conversation.py",
                "src/nasa_fire_ai/services/context_assembly.py",
            ]
            if (args.implementation_root / name).is_file()
        },
        "cases": [],
    }
    with_service = ScientificSearchService(ROOT / "data/snapshots/hackathon-20261105-v9", ROOT)
    service = ConversationService(with_service)
    try:
        for case in run["cases"]:
            trace = case["trace"]
            results = []
            for query in trace["queries"]:
                intent = None
                if query.get("source_scope"):
                    intent = with_service.interpret(query["query"])
                    intent.source_constraints = query["source_scope"]
                results.append(
                    with_service.search(
                        query["query"],
                        intent=intent,
                        assist=True,
                        research=True,
                        limit=12,
                        complete_claims=True,
                    )
                )
            service._inventory(
                results, primary_result=results[0], question=trace["resolved_question"]
            )
            receipt = service.inventory_receipt
            target_stages = [
                {
                    "target_id": t["id"],
                    "evidence_id": t["evidence_id"],
                    "retrieved": t["evidence_id"] in receipt["retrieved_evidence_ids"],
                    "examined_for_routing": t["evidence_id"] in receipt["available_evidence_ids"],
                    "supplied_page": t["evidence_id"] in receipt["supplied_evidence_ids"],
                }
                for t in targets
                if case["id"] in t["case_ids"]
            ]
            # Full per-anchor decisions are retained in live traces. Keep this
            # routing comparison compact and auditable by page/need.
            public = {k: v for k, v in receipt.items() if k != "selection_decisions"}
            report["cases"].append(
                {
                    "id": case["id"],
                    "resolved_question": trace["resolved_question"],
                    "receipt": public,
                    "targets": target_stages,
                }
            )
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(report, indent=2) + "\n")
            print(json.dumps({"id": case["id"], "targets": target_stages}), flush=True)
    finally:
        with_service.close()
    all_targets = [t for c in report["cases"] for t in c["targets"]]
    report["summary"] = {
        k: sum(t[k] for t in all_targets)
        for k in ("retrieved", "examined_for_routing", "supplied_page")
    }
    report["summary"]["target_page_associations"] = len(all_targets)
    report["complete"] = True
    args.output.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
