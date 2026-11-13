"""Measure known-source coverage against source-inspected, provisional judgments.

Unjudged candidates are not negatives. These metrics do not estimate complete
NASA literature recall or scientific precision. Baseline and revised use the
same immutable corpus and question set; qrels never enter production retrieval.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nasa_fire_ai.services.search import ScientificSearchService


def document_id(sid):
    return sid.removeprefix("local-")


def score(rows, judgments):
    known = {document_id(j["source_id"]) for j in judgments}
    docs = [document_id(r["source_id"]) for r in rows]
    evidence = {j["evidence_id"] for j in judgments}
    # Catalogue records for one PSI accession identify one investigation; a
    # report covering several investigations is not counted as a new experiment.
    investigations = {s.removeprefix("catalog-") for s in known if s.startswith("catalog-psi-")}
    found_investigations = {
        s.removeprefix("catalog-") for s in docs if s.startswith(("psi-", "catalog-psi-"))
    }
    return {
        "known_documents": len(known),
        "recall_at": {str(k): len(known & set(docs[:k])) / len(known) for k in (10, 20, 50, 100)}
        if known
        else None,
        "known_documents_missed": sorted(known - set(docs)),
        "known_document_hits": len(known & set(docs)),
        "known_investigations": len(investigations),
        "known_investigations_found": len(investigations & found_investigations),
        "anchor_evidence_found": len(evidence & {r["evidence_id"] for r in rows}),
        "anchor_evidence_total": len(evidence),
        "unjudged_documents": sorted(set(docs) - known),
    }


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--baseline", type=Path, default=ROOT / "artifacts/hackathon_recall_v1/baseline.json"
    )
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Preserve earlier receipts: output must be new")
    questions_path = ROOT / "evals/phase56/recall_questions.json"
    qrels_path = ROOT / "evals/phase56/recall_qrels_v1.json"
    questions = json.loads(questions_path.read_text())
    qrels = json.loads(qrels_path.read_text())
    baseline = {r["id"]: r for r in json.loads(args.baseline.read_text())["cases"]}
    service = ScientificSearchService(ROOT / "data/snapshots/hackathon-20261105-v9", ROOT)
    report = {
        "qrels_status": qrels["status"],
        "independent_scientist_review": False,
        "question_sha256": hashlib.sha256(questions_path.read_bytes()).hexdigest(),
        "qrels_sha256": hashlib.sha256(qrels_path.read_bytes()).hexdigest(),
        "snapshot": service.manifest["snapshot_id"],
        "cases": [],
    }
    try:
        for case in questions:
            result = service.search(case["question"], research=True, limit=100)
            passages = sorted(
                result.documentary + result.discovery, key=lambda r: r.get("candidate_rank", 100000)
            )
            ranked = [
                {
                    "evidence_id": r["evidence_id"],
                    "source_id": r["source"]["source_id"],
                    "category": r["category"],
                    "strategies": [x["strategy"] for x in r.get("retrieval_routes", [])],
                }
                for r in passages
            ]
            judgments = [j for j in qrels["judgments"] if j["question_id"] == case["id"]]
            row = {
                **case,
                "baseline": score(baseline[case["id"]]["ranked_passages"], judgments),
                "revised": score(ranked, judgments),
                "ranked_passages": ranked,
                "metrics": result.metrics,
                "continuation": result.continuation,
                "direct_count": len(result.direct),
            }
            row["new_known_sources"] = sorted(
                set(row["baseline"]["known_documents_missed"])
                - set(row["revised"]["known_documents_missed"])
            )
            report["cases"].append(row)
            print(
                json.dumps({"id": case["id"], "new_known_sources": row["new_known_sources"]}),
                flush=True,
            )
    finally:
        service.close()
    judged = [r for r in report["cases"] if r["baseline"]["known_documents"]]
    report["summary"] = {"questions": len(questions), "source_inspected_questions": len(judged)}
    for version in ("baseline", "revised"):
        report["summary"][version] = {
            "macro_recall_at": {
                str(k): sum(r[version]["recall_at"][str(k)] for r in judged) / len(judged)
                for k in (10, 20, 50, 100)
            },
            "known_documents_missed": sum(
                len(r[version]["known_documents_missed"]) for r in judged
            ),
            "known_investigations_found": sum(
                r[version]["known_investigations_found"] for r in judged
            ),
            "known_investigation_question_pairs": sum(
                r[version]["known_investigations"] for r in judged
            ),
            "anchor_evidence_found": sum(r[version]["anchor_evidence_found"] for r in judged),
            "anchor_evidence_total": sum(r[version]["anchor_evidence_total"] for r in judged),
        }
    report["limitations"] = [
        "Source inspection was performed by the implementation agent, not independent scientific adjudicators.",
        "Relevance sets are incomplete; unknown candidates cannot be called irrelevant.",
        "Document recall is not evidence fidelity, applicability, or response quality.",
        "Baseline rank combines exposed documentary/discovery passages by BM25; revised uses rank fusion and source diversity.",
        "Investigation counts use explicit PSI identities only; report titles are not extra investigations.",
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    main()
