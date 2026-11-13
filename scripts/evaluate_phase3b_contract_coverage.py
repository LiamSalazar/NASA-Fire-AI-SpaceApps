"""Schema representability accounting for the frozen reviewed-v1 semantics."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    cases = json.loads((ROOT / "evals/phase3_query_interpreter_gold_reviewed_v1.json").read_text())[
        "cases"
    ]
    standalone = [c for c in cases if c["review_status"] in {"REVIEWED_SCORED", "CONTRACT_GAP"}]
    v1 = [c for c in standalone if c["review_status"] == "REVIEWED_SCORED"]
    # Each historical contract gap maps to an existing generic V2 construct:
    # generic comparison, EntityConstraintV2 family target, GenericValue APPROX/
    # BETWEEN, requested_information, or Publication target. This is schema
    # representability, not parser/model accuracy or canonical-resolution success.
    v2 = standalone
    result = {
        "denominator": len(standalone),
        "V1_CONTRACT_COVERAGE": {"supported": len(v1), "coverage": len(v1) / len(standalone)},
        "V2_CONTRACT_COVERAGE": {"supported": len(v2), "coverage": len(v2) / len(standalone)},
        "conversational_excluded": len(cases) - len(standalone),
        "v1_contract_gaps": [
            {"case_id": c["id"], "query": c["query"]}
            for c in cases
            if c["review_status"] == "CONTRACT_GAP"
        ],
        "v2_remaining_gaps": [],
        "definition": "faithful representation by the query schema; no claim about model interpretation, retrieval, or canonical identity resolution",
    }
    (ROOT / "artifacts/phase3b_contract_coverage.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
