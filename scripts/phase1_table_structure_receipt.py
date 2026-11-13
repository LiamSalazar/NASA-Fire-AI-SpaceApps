"""Table-structure receipt over saved packages: what the deterministic layer recovers.

For every prepared package given, the saved document structure is re-linked
with the current continuation/row-group/legend logic (no model calls) and the
receipt counts what it finds: detected tables, continuation tables with an
inherited header, row groups carried down, legend-backed footnote markers and
rows whose lineage is cited or external by the printed caption or legend. The
counts describe layout recovery only; they are not scientific recall.

    uv run python scripts/phase1_table_structure_receipt.py PACKAGE.json.gz ... --output receipt.json
"""

import argparse
import gzip
import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def describe(path):
    from nasa_fire_ai.ingestion.study_attribution import reference_authors
    from nasa_fire_ai.ingestion.table_continuity import (
        link_continuation_tables,
        row_lineage,
        table_rows,
    )

    with gzip.open(path, "rt", encoding="utf-8") as handle:
        package = json.load(handle)["package"]
    document = package["scientific_extraction"]["document"]
    tables = link_continuation_tables(document["detected_tables"])
    document["detected_tables"] = tables
    structured = [t for t in tables if t.get("cells")]
    rows = table_rows(document)
    authors = reference_authors(document)
    groups = Counter()
    for row in rows:
        if row["group_label"]:
            groups[(row["table_index"], row["group_label"])] += 1
    continuations = [t for t in structured if t.get("continuation_of")]
    # The tables in which each group prints its own labelled row; a group spans a
    # continuation when a continuation table only inherits it from above.
    labelled = {}
    for row in rows:
        if row["group_label"] and (row["cells"][0]["original_value"] or "").strip():
            labelled.setdefault(row["group_label"], set()).add(row["table_index"])
    return {
        "package": path.as_posix(),
        "package_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "source_sha256": [i["sha256"] for i in package["inputs"]],
        "detected_tables": len(structured),
        "text_tables": len(tables) - len(structured),
        "continuation_tables_with_inherited_header": [
            {
                "page": t["physical_pdf_page"],
                "continues_page": t["continuation_of"]["physical_pdf_page"],
                "columns": len(t["header"]),
            }
            for t in continuations
        ],
        "data_rows": len(rows),
        "row_groups": len(groups),
        "rows_inheriting_a_group_from_above": sum(
            1
            for r in rows
            if r["group_label"] and not (r["cells"][0]["original_value"] or "").strip()
        ),
        "groups_spanning_a_continuation": sorted(
            {
                " ".join(r["group_label"].split())
                for r in rows
                if r["group_label"]
                and r["continuation_of"]
                and not (r["cells"][0]["original_value"] or "").strip()
                and r["table_index"] not in labelled.get(r["group_label"], set())
            }
        ),
        "rows_with_legend_backed_marker": sum(1 for r in rows if r["footnote_marker"]),
        "distinct_legends": sorted(
            {m for r in rows if r["footnote_legend"] for m in r["footnote_legend"]}
        ),
        "rows_cited_or_external_by_caption_or_legend": sum(
            1 for r in rows if row_lineage(r, authors)
        ),
        "reference_list_authors_found": len(authors),
        "table_captions": sorted(
            {r["table_caption"].replace("\n", " ") for r in rows if r["table_caption"]}
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("packages", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=False
    ).stdout.strip()
    receipt = {
        "kind": "PHASE1_TABLE_STRUCTURE_RECEIPT",
        "git_head": head,
        "model_calls": 0,
        "scientific_acceptance": "LAYOUT_RECOVERY_ONLY_NOT_SCIENTIFIC_RECALL",
        "packages": [describe(p) for p in args.packages],
    }
    with args.output.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(receipt, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    for entry in receipt["packages"]:
        print(
            Path(entry["package"]).parent.name,
            "tables",
            entry["detected_tables"],
            "continuations",
            len(entry["continuation_tables_with_inherited_header"]),
            "groups",
            entry["row_groups"],
            "marked rows",
            entry["rows_with_legend_backed_marker"],
            "cited/external rows",
            entry["rows_cited_or_external_by_caption_or_legend"],
        )


if __name__ == "__main__":
    main()
