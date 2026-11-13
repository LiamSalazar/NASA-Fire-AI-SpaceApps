"""Publish source-explicit sample identities separately from experimental runs."""

import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nasa_fire_ai.evidence import EvidenceRegistry


def main():
    reports = json.loads((ROOT / "artifacts/phase3c_targeted_psi_publication_v1.json").read_text())
    records = []
    for report in reports:
        report["published_samples"] = 0
        if report["investigation"] not in {"SAFFIRE-II", "SAFFIRE-III", "SAME"}:
            continue
        with (ROOT / report["raw_file"]).open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        identity_column = next(h for h in rows[0] if h.strip() in {"Sample Number", "Sample #"})
        ids = Counter(row[identity_column] for row in rows)
        for row, staged in zip(rows, report["rows"], strict=True):
            sample = row[identity_column]
            # Numeric sample identifiers distinguish actual samples from camera
            # file names and footnotes in the Saffire-II source schema.
            if (
                ids[sample] != 1
                or not any(c.isdigit() for c in sample)
                or sample.startswith(("F", "Note"))
            ):
                continue
            material_column = next(h for h in row if h.strip() in {"Material", "Sample Material"})
            eid = staged["evidence_id"]
            record = {
                "type": "SampleRecord",
                "id": f"{report['source_id']}-reported-sample-{sample}",
                "source_id": report["source_id"],
                "reported_sample_id": sample,
                "reported_material_description": row[material_column],
                "evidence_refs": [{"evidence_id": eid, "source_id": report["source_id"]}],
                "scientific_scope": "source sample identity and original label only; no derived measurements, run equivalence or canonical material mapping",
            }
            records.append(record)
            report["published_samples"] += 1
            staged["sample_publication"] = record["id"]
            staged["scientific_values_status"] = "REVIEW_REQUIRED"
    path = ROOT / "data/canonical/phase3c_targeted_psi_samples_v1.json"
    assert not path.exists()
    path.write_text(json.dumps(records, indent=2))
    output = ROOT / "artifacts/phase3c_targeted_psi_publication_v2.json"
    assert not output.exists()
    output.write_text(json.dumps(reports, indent=2))
    registry = EvidenceRegistry(ROOT / "data/index/evidence.sqlite")
    assert all(registry.resolve(r["evidence_refs"][0]["evidence_id"]) for r in records)
    print({"published_samples": len(records)})


if __name__ == "__main__":
    main()
