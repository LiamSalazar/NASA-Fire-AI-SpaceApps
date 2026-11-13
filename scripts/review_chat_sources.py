"""Read-only physical PDF/CSV provenance checks for recorded chat references.

This checks source locations and quotes, not whether an answer is relevant or
scientifically correct. Semantic review must remain a separate assessment.
"""

import argparse
import json
import sys
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nasa_fire_ai.evidence import EvidenceRegistry


def normalize(text):
    return " ".join(text.split())


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output must be new")
    registry = EvidenceRegistry(
        ROOT / "data/snapshots/hackathon-20261105-v9/evidence.sqlite",
        read_only=True,
        evidence_root=ROOT,
    )
    report = {"input": str(args.input), "scientific_validation": False, "checks": []}
    try:
        for case in json.loads(args.input.read_text())["cases"]:
            for citation in case["response"].get("citations", []):
                supports = citation.get("supports") or [
                    {
                        "evidence_id": citation["evidence_id"],
                        "passage": citation["supporting_passage"],
                    }
                ]
                for support in supports:
                    evidence = registry.resolve(support["evidence_id"])
                    original = Path(evidence["raw_file"])
                    if original.suffix.lower() == ".pdf":
                        with pymupdf.open(original) as pdf:
                            text = pdf[evidence["page"] - 1].get_text()
                    else:
                        text = original.read_text(encoding="utf-8-sig")
                    report["checks"].append(
                        {
                            "case_id": case["id"],
                            "evidence_id": support["evidence_id"],
                            "page": evidence["page"],
                            "quote": support["passage"],
                            "registry_quote_matches": normalize(support["passage"])
                            in normalize(evidence["text"]),
                            "original_file_quote_matches": normalize(support["passage"])
                            in normalize(text),
                            "claim_text": support.get("claim_text"),
                        }
                    )
    finally:
        registry.db.close()
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(
        json.dumps(
            {
                "checks": len(report["checks"]),
                "registry_matches": sum(c["registry_quote_matches"] for c in report["checks"]),
                "physical_source_matches": sum(
                    c["original_file_quote_matches"] for c in report["checks"]
                ),
            }
        )
    )


if __name__ == "__main__":
    main()
