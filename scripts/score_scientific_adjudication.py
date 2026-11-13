"""Aggregate explicit source-inspected judgments; never infer semantic quality.

Each essential need, usefulness decision and communicated claim judgment must be
entered by the reviewer. Response and rubric hashes bind that review to the
actual outputs; citation resolution is reported independently of citation support.
"""

import argparse
import hashlib
import json
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--rubric", type=Path, required=True)
    parser.add_argument("--judgments", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Evaluation receipts are append-only")
    rubric = json.loads(args.rubric.read_text())
    judgments = json.loads(args.judgments.read_text())
    if judgments["rubric_sha256"] != digest(args.rubric):
        raise ValueError("Rubric changed after adjudication")
    questions = {row["id"]: row for row in rubric["questions"]}
    seen, cases = set(), []
    for row in judgments["cases"]:
        identity = row["id"]
        if identity in seen or identity not in questions:
            raise ValueError("Duplicate or unknown scientific case")
        seen.add(identity)
        response_path = Path(row["response_path"])
        if digest(response_path) != row["response_sha256"]:
            raise ValueError("Reviewed response changed")
        response = json.loads(response_path.read_text())
        if response["id"] != identity:
            raise ValueError("Judgment does not describe this HTTP case")
        if response["status"] != 200 and (
            row.get("execution_failure", {}).get("http_status") != response["status"]
            or row.get("useful") is not False
            or any(need.get("met") for need in row.get("needs", []))
        ):
            raise ValueError(
                "A failed HTTP turn requires an explicit failure judgment and zero answer credit"
            )
        needs = questions[identity]["essential_needs"]
        if len(row["needs"]) != len(needs):
            raise ValueError("Every frozen essential need requires a judgment")
        for expected, actual in zip(needs, row["needs"], strict=True):
            if (
                actual["need"] != expected
                or type(actual["met"]) is not bool
                or not actual["reason"]
            ):
                raise ValueError("Incomplete essential-information judgment")
        if type(row["useful"]) is not bool or not row["source_inspection"]:
            raise ValueError("Usefulness requires explicit source inspection")
        if not row["citation_support_review"] or not row["claim_fidelity_review"]:
            raise ValueError("Citation support and scientific correctness require separate review")
        cases.append(
            {
                "id": identity,
                "http_status": response["status"],
                "essential_needs": len(needs),
                "essential_needs_met": sum(need["met"] for need in row["needs"]),
                "useful": row["useful"],
                "critically_unsupported_claims": len(row["critically_unsupported_claims"]),
                "semantically_unsupported_citations": len(
                    row["semantically_unsupported_citations"]
                ),
                "response_sha256": row["response_sha256"],
            }
        )
    total = sum(row["essential_needs"] for row in cases)
    result = {
        "rubric_sha256": digest(args.rubric),
        "judgments_sha256": digest(args.judgments),
        "reviewer_boundary": judgments["reviewer_boundary"],
        "planned_questions": len(questions),
        "adjudicated_questions": len(cases),
        "failed_http_questions": sum(row["http_status"] != 200 for row in cases),
        "essential_needs": total,
        "essential_needs_met": sum(row["essential_needs_met"] for row in cases),
        "essential_answer_coverage": sum(row["essential_needs_met"] for row in cases) / total
        if total
        else None,
        "conversational_usefulness": sum(row["useful"] for row in cases) / len(cases)
        if cases
        else None,
        "critically_unsupported_claims": sum(row["critically_unsupported_claims"] for row in cases),
        "semantically_unsupported_citations": sum(
            row["semantically_unsupported_citations"] for row in cases
        ),
        "citation_resolution": "Reported separately by registered-original-evidence review packets",
        "cases": cases,
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key != "cases"}))


if __name__ == "__main__":
    main()
