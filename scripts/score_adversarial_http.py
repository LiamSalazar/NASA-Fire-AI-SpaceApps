"""Score frozen original perturbations separately from independently checked repairs.

This evaluates explicit source-inspected adversarial labels, not response
coverage or conversational usefulness. It never supplies labels to production.
"""

import argparse
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--judgments", type=Path, nargs="+", required=True)
    parser.add_argument("--responses", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Do not overwrite an evaluation receipt")
    cases, hashes = {}, {}
    for path in args.judgments:
        hashes[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        for case in json.loads(path.read_text())["cases"]:
            if case["id"] in cases:
                raise ValueError("Duplicate adjudication identity")
            cases[case["id"]] = case
    rows = []
    for identity, case in cases.items():
        path = args.responses / (identity + ".trace.json")
        if not path.exists():
            rows.append({"id": identity, "status": "NOT_EXECUTED"})
            continue
        trace = json.loads(path.read_text())
        original = case["untrusted_proposition"]
        records = [
            row
            for row in trace["verification"]
            if row["stage"] == "draft" and row.get("original_parent_text") == original
        ]
        if len(records) != 1:
            raise ValueError(
                f"Original atomic proposition cannot be scored unambiguously: {identity}"
            )
        supported = records[0]["supported"]
        expected = case["expected_original_proposition_supported"]
        rows.append(
            {
                "id": identity,
                "status": "EXECUTED",
                "expected_supported": expected,
                "original_proposal_supported": supported,
                "correct": supported == expected,
                "reason": records[0].get("errors") or records[0].get("reason"),
                "trace_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    executed = [row for row in rows if row["status"] == "EXECUTED"]
    result = {
        "judgment_sha256": hashes,
        "cases": rows,
        "planned": len(cases),
        "executed": len(executed),
        "negative_cases": sum(not row["expected_supported"] for row in executed),
        "positive_controls": sum(row["expected_supported"] for row in executed),
        "false_acceptances": sum(
            not row["expected_supported"] and row["original_proposal_supported"] for row in executed
        ),
        "false_rejections": sum(
            row["expected_supported"] and not row["original_proposal_supported"] for row in executed
        ),
        "boundary": "Finite source-inspected perturbations; not unseen model generation. Correct original-proposal rejection does not certify the semantic support of subsequent repairs.",
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {key: value for key, value in result.items() if key not in {"cases", "judgment_sha256"}}
        )
    )


if __name__ == "__main__":
    main()
