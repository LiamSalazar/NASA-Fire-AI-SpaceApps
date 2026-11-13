"""Compare an expanded snapshot with the frozen provisional source judgments."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from evaluate_recall import score

from nasa_fire_ai.services.search import ScientificSearchService


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Do not overwrite an evaluation receipt")
    questions = json.loads((ROOT / "evals/phase56/recall_questions.json").read_text())
    judgments = json.loads((ROOT / "evals/phase56/recall_qrels_v1.json").read_text())["judgments"]
    engine = ScientificSearchService(args.snapshot, ROOT)
    cases = []
    try:
        for item in questions:
            result = engine.search(item["question"], research=True, limit=100)
            candidates = sorted(
                result.documentary + result.discovery,
                key=lambda row: row.get("candidate_rank", 100000),
            )
            ranked = [
                {"source_id": row["source"]["source_id"], "evidence_id": row["evidence_id"]}
                for row in candidates
            ]
            case_judgments = [j for j in judgments if j["question_id"] == item["id"]]
            cases.append(
                {
                    "id": item["id"],
                    "judged_sources": len(case_judgments),
                    "score": score(ranked, case_judgments),
                    "candidate_count": len(ranked),
                }
            )
            print(item["id"], flush=True)
    finally:
        engine.close()
    judged = [case for case in cases if case["score"]["known_documents"]]
    summary = {
        "questions": len(cases),
        "source_inspected_questions": len(judged),
        "anchor_evidence_total": sum(c["score"]["anchor_evidence_total"] for c in judged),
        "anchor_evidence_found": sum(c["score"]["anchor_evidence_found"] for c in judged),
        "macro_document_recall_at": {
            str(k): sum(c["score"]["recall_at"][str(k)] for c in judged) / len(judged)
            for k in (10, 20, 50, 100)
        },
    }
    receipt = {
        "snapshot_id": engine.manifest["snapshot_id"],
        "metric_scope": "Frozen provisional judgments on known sources; unjudged candidates are not negatives",
        "vector_enabled": False,
        "summary": summary,
        "cases": cases,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
