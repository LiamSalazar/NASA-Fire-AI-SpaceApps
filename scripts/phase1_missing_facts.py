"""Missing-fact report over saved readings: the printed terms of the body that no record covers.

    uv run python scripts/phase1_missing_facts.py PREPARED.json.gz [...] [--output report.json]

Reads each saved reading (prepared.json.gz), runs ``missing_fact_report`` on its records and
candidates, and prints the counts per source. It changes nothing: no record, no request.
"""

import argparse
import gzip
import json
from pathlib import Path

from nasa_fire_ai.ingestion.scientific_coverage import missing_fact_report


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("prepared", nargs="+", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    reports = {}
    for path in args.prepared:
        package = json.loads(gzip.decompress(path.read_bytes()))["package"]
        extraction = package["scientific_extraction"]
        reports[str(path)] = missing_fact_report(
            extraction["records"],
            extraction["semantic_candidates"],
            extraction["document"],
            {e["evidence_id"]: e["source_id"] for e in package["evidence"]},
        )
        print(path, reports[str(path)]["count"], reports[str(path)]["per_source"])
    if args.output:
        args.output.write_text(json.dumps(reports, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
