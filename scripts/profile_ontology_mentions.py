"""Check entity-lookup equivalence and timing against the previous complete scan."""

import argparse
import hashlib
import json
import sys
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nasa_fire_ai.services.ontology_support import (
    _mention_pattern,
    _mentions,
    scientific_mention_view,
)
from nasa_fire_ai.services.search import ScientificSearchService


def complete_scan(text, store):
    text = scientific_mention_view(text, store)
    matches = {}
    for entity in store.registry.entities:
        labels = [entity, *store.registry.entity_mentions.get(entity, {}).get("aliases", [])]
        if any(label and _mention_pattern(label).search(text) for label in labels):
            matches[entity] = sorted(store.classes(entity, include_ancestors=True))
    return matches


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Receipts are append-only")
    service = ScientificSearchService(args.snapshot, ROOT)
    timings = {"complete_scan": 0.0, "prefilter": 0.0}
    cases = []
    try:
        for filename, key in [
            ("psi_open_questions_v1.json", "questions"),
            ("psi_post_freeze_holdout_v1.json", "questions"),
        ]:
            for case in json.loads((ROOT / "evaluation" / filename).read_text())[key]:
                text = case["question"]
                start = perf_counter()
                baseline = complete_scan(text, service.store)
                timings["complete_scan"] += perf_counter() - start
                start = perf_counter()
                actual = _mentions(text, service.store)
                timings["prefilter"] += perf_counter() - start
                if actual != baseline:
                    raise AssertionError(f"Entity interpretation changed: {case['id']}")
                cases.append({"id": case["id"], "identical": True, "matches": len(actual)})
        result = {
            "snapshot_id": service.manifest["snapshot_id"],
            "ontology_support_sha256": hashlib.sha256(
                (ROOT / "src/nasa_fire_ai/services/ontology_support.py").read_bytes()
            ).hexdigest(),
            "cases": cases,
            "seconds": timings,
            "speedup": timings["complete_scan"] / timings["prefilter"],
            "boundary": "Entity lookup equivalence/performance only; no factual certification or new question acceptance measurement.",
        }
        args.output.write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps({"cases": len(cases), "seconds": timings, "speedup": result["speedup"]}))
    finally:
        service.close()


if __name__ == "__main__":
    main()
