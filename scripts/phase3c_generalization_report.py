"""Read-only scientific coverage and inference accounting for the executed campaign."""

import hashlib
import json
import sqlite3
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / "artifacts/phase3c_generalization_v1"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, value):
    with (DIRECTORY / name).open("x") as handle:
        json.dump(value, handle, indent=2)


def summarize():
    packages = {}
    stages = {}
    for label, workspace in (("development", "corpus_workspace"), ("holdout", "holdout_workspace")):
        db = sqlite3.connect(
            f"file:{DIRECTORY / workspace / 'data/index/evidence.sqlite'}?mode=ro", uri=True
        )
        payloads = [
            json.loads(r[0])
            for r in db.execute(
                "SELECT p.payload FROM research_packages p JOIN (SELECT package_id,MAX(version) version FROM research_packages GROUP BY package_id) latest USING(package_id,version)"
            )
        ]
        packages[label] = {
            "packages": len(payloads),
            "entity_classes_proposed": Counter(
                e["class_id"] for p in payloads for e in p["entities"]
            ),
            "statement_roles_proposed": Counter(
                s["epistemic"] for p in payloads for s in p["statements"]
            ),
            "table_rows_parsed": sum(len(t["rows"]) for p in payloads for t in p["tables"]),
            "values_proposed": sum(len(p["values"]) for p in payloads),
            "draft_relations_proposed": sum(len(p["relations"]) for p in payloads),
            "active_scientific_packages": db.execute(
                "SELECT count(*) FROM research_active"
            ).fetchone()[0],
        }
        stages[label] = Counter(
            r[0] for r in db.execute("SELECT review_status FROM semantic_staging")
        )
        db.close()
    calls = []
    for path in (DIRECTORY / "corpus_sources").glob("*.json"):
        receipt = json.loads(path.read_text()).get("extraction", {}).get("model", {})
        if receipt.get("execution") == "FRESH_INFERENCE":
            calls.append(
                {
                    "path": str(path.relative_to(ROOT)),
                    "usage": receipt.get("usage"),
                    "kind": "extraction",
                }
            )
    for relative in (
        "pilot/natural_correction.json",
        "e2e/generated_questions.json",
        "e2e_v3/generated_questions.json",
        "language_v2/questions.json",
    ):
        receipt = json.loads((DIRECTORY / relative).read_text())["receipt"]
        if receipt.get("execution") == "FRESH_INFERENCE":
            calls.append(
                {
                    "path": relative,
                    "usage": receipt.get("usage"),
                    "kind": "clarification_or_correction",
                }
            )
    for relative in (
        "e2e_v3/natural_language_results.json",
        "language_v2/corrections.json",
        "language_v3/corrections.json",
    ):
        for result in json.loads((DIRECTORY / relative).read_text()):
            receipt = result["receipt"]
            if receipt.get("execution") == "FRESH_INFERENCE":
                calls.append(
                    {
                        "path": relative,
                        "usage": receipt.get("usage"),
                        "kind": "correction",
                        "outcome": receipt.get("outcome"),
                    }
                )
    frozen = json.loads((DIRECTORY / "contract_freeze.json").read_text())
    changed = [p for p, value in frozen["files"].items() if sha(ROOT / p) != value]
    write(
        "scientific_coverage.json",
        {
            "draft_coverage": packages,
            "registry_staging_status_including_historical_candidates": stages,
            "counts_are_proposed_not_scientifically_approved": True,
        },
    )
    write(
        "inference_accounting.json",
        {
            "fresh_calls": len(calls),
            "reported_tokens": sum((c["usage"] or {}).get("total_tokens", 0) for c in calls),
            "calls": calls,
            "cache_replay_counted_as_new": False,
        },
    )
    write(
        "final_holdout_protocol.json",
        {
            "membership_sha256": sha(DIRECTORY / "evaluation_split.json"),
            "contracts_sha256": sha(DIRECTORY / "contract_freeze.json"),
            "contracts_changed_after_final_evaluation": changed,
            "holdout_processing": "25 independent source packages staged after runtime freeze; no new model inference or automatic scientific approval",
            "scientific_generalization": "NOT_MEASURABLE",
            "limitations": [
                "Historical exposure cannot be excluded",
                "Title-lineage grouping is not a scientist-reconciled investigation split",
                "No independent relevance or attribution gold labels",
                "No new holdout scientific knowledge was approved; preparation is not incorporation-to-answer generalization",
            ],
        },
    )
    print(
        json.dumps(
            {"draft_coverage": packages, "fresh_calls": len(calls), "contracts_changed": changed}
        )
    )


if __name__ == "__main__":
    summarize()
