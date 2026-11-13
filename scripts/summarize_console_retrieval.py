"""Summarize frozen required-source judgments without claiming exhaustive precision."""

import argparse
import json
import math
from pathlib import Path


def summarize(receipt):
    channels = {}
    for name in receipt["cases"][0]["channels"]:
        rows = []
        for case in receipt["cases"]:
            relevant = set(case["expected_sources"])
            ranked = list(dict.fromkeys(case["channels"][name]["source_ids_at_20"]))
            ranked = [s for s in ranked if s]
            gains = [int(s in relevant) for s in ranked]
            ideal = sum(1 / math.log2(i + 2) for i in range(min(10, len(relevant))))
            rows.append(
                {
                    "id": case["id"],
                    "recall": {
                        str(k): len(relevant & set(ranked[:k])) / len(relevant) for k in (5, 10, 20)
                    },
                    "required_source_precision_lower_bound": {
                        str(k): sum(gains[:k]) / k for k in (5, 10)
                    },
                    "reciprocal_rank": next((1 / (i + 1) for i, g in enumerate(gains) if g), 0),
                    "ndcg10": sum(g / math.log2(i + 2) for i, g in enumerate(gains[:10])) / ideal,
                }
            )
        channels[name] = {
            "questions": len(rows),
            "recall": {
                str(k): sum(r["recall"][str(k)] for r in rows) / len(rows) for k in (5, 10, 20)
            },
            "required_source_precision_lower_bound": {
                str(k): sum(r["required_source_precision_lower_bound"][str(k)] for r in rows)
                / len(rows)
                for k in (5, 10)
            },
            "mrr_at_observed_pool": sum(r["reciprocal_rank"] for r in rows) / len(rows),
            "ndcg10": sum(r["ndcg10"] for r in rows) / len(rows),
            "cases": rows,
        }
    return {
        "unit": "unique original source, deduplicated within first 20 retrieved evidence entries",
        "boundary": "Required-source pool is incomplete. Precision is a lower-bound pool hit rate, not exhaustive scientific precision. No passage coverage, measurement recall or scientific relationship accuracy follows from these source ranks.",
        "channels": channels,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Do not overwrite a receipt")
    args.output.write_text(
        json.dumps(summarize(json.loads(args.input.read_text())), indent=2) + "\n"
    )
