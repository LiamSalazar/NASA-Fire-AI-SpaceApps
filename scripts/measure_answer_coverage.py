"""Replay communication probes per verified statement, within the NLI window.

Whole answers can exceed the NLI context window. That is not missing scientific
coverage. This protocol records per-statement and small joint-support checks;
original live receipts are never overwritten. Manual source review is separate.
"""

import argparse
import json
import re
import sys
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nasa_fire_ai.services.semantic_support import LocalEntailment


def communication_check(verifier, statements, proposition):
    terms = set(re.findall(r"[a-z]{4,}", proposition.lower()))
    ranked = sorted(
        set(statements), key=lambda text: -len(terms & set(re.findall(r"[a-z]{4,}", text.lower())))
    )
    checks = []
    for text in ranked:
        verdict = verifier.check(text, proposition)
        checks.append({"statement": text, "verdict": verdict})
        if verdict["supported"]:
            return {"supported": True, "checks": checks}
    for first, second in combinations(ranked[:4], 2):
        verdict = verifier.check(first + "\n" + second, proposition)
        checks.append({"statements": [first, second], "verdict": verdict})
        if verdict["supported"]:
            return {"supported": True, "checks": checks}
    return {"supported": False, "checks": checks}


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--targets", type=Path, required=True)
    parser.add_argument("--nli", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Preserve older receipts")
    verifier = LocalEntailment(args.nli)
    run = json.loads(args.run.read_text())
    targets = json.loads(args.targets.read_text())["targets"]
    rows = []
    for case in run["cases"]:
        response = case["response"]
        statements = {
            s["claim_text"]
            for c in response.get("citations", [])
            if c.get("category") != "DISCOVERY"
            for s in c.get("supports", [])
        }
        checks = []
        for target in (t for t in targets if case["id"] in t["case_ids"]):
            result = communication_check(verifier, statements, target["proposition"])
            checks.append(
                {"target_id": target["id"], "proposition": target["proposition"], **result}
            )
        rows.append(
            {
                "case_id": case["id"],
                "target_checks": checks,
                "response_mode": response.get("provider_status", {}).get("response_mode"),
                "explanatory_statements": len(statements),
            }
        )
        print(case["id"], sum(c["supported"] for c in checks), len(checks), flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(
            {
                "protocol": "per-supported-statement-NLI-v2",
                "input_run": args.run.name,
                "cases": rows,
                "boundary": "Automated independent NLI communication probe, not human scientific adjudication",
                "reason": "Whole-answer NLI may exceed 512 tokens; unexamined overflow is not a coverage miss",
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
