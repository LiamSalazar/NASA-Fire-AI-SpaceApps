"""Complete deterministic value/unit/role checks, leaving scientific review explicit."""

import json
import os
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.semantic import project_legacy
from nasa_fire_ai.normalization.units import normalize


def main():
    registry = EvidenceRegistry(ROOT / "data/index/evidence.sqlite")
    os.environ["ONTOLOGY_GRAPH_ENRICHMENT_ENABLED"] = "true"
    os.environ["SOURCE_KNOWLEDGE_ENRICHMENT_ENABLED"] = "true"
    os.environ["PSI_STRUCTURED_PUBLICATION_ENABLED"] = "true"
    os.environ["FLEX_SOURCE_CORRECTIONS_ENABLED"] = "true"
    store = project_legacy(ROOT, registry)
    checks = []
    for mapped in store.source_enrichment_report["mapped"]:
        original = mapped["original"]
        payload = store.payload(original["id"])
        expected = normalize(original["reported_value"], original["reported_unit"])
        cells = [
            cell
            for ref in original["evidence_refs"]
            for cell in registry.resolve(ref["evidence_id"]).get("source_cells", [])
        ]
        matches = []
        for cell in cells:
            try:
                if float(cell["original_value"]) == original["reported_value"]:
                    matches.append(
                        {
                            "column": cell["column_ordinal"],
                            "header": cell["original_header"],
                            "value": cell["original_value"],
                        }
                    )
            except ValueError:
                continue
        checks.append(
            {
                "record_id": original["id"],
                "kind": original["kind"],
                "role": mapped["qualifiers"]["role"],
                "original_value_and_unit_preserved": payload["qualifiers"]["original_record"]
                == original,
                "canonical_conversion_verified": payload["value"]["canonical_value"] == expected[0]
                and payload["value"]["canonical_unit"] == expected[1],
                "observed_status": payload["qualifiers"]["observed_status"],
                "exact_source_row_available": bool(cells),
                "numeric_matching_cells": matches,
                "semantic_caveat": "Numeric equality alone is not field identity or independent scientific validation.",
            }
        )
    report = {
        "fields": checks,
        "conversion_numerator": sum(c["canonical_conversion_verified"] for c in checks),
        "denominator": len(checks),
        "preservation_numerator": sum(c["original_value_and_unit_preserved"] for c in checks),
        "strata": dict(Counter((c["kind"] + ":" + c["role"]) for c in checks)),
        "source_correction_report": store.source_correction_report,
        "scientific_role_review": "Source-contract engineering review only; no independent expert precision measured",
        "additional_caveats": [
            "NASA FLEX dictionary defines ignition-time initial diameter; it is not a final diameter.",
            "NASA FLEX dictionary permits extrapolated extinction diameter in some cases; generic accessor never asserts all are directly measured.",
            "Initial/final gas quantities remain separately qualified; no condition-to-observation promotion.",
        ],
        "remaining_staging": store.projection_staging,
    }
    out = ROOT / "artifacts/phase3c_targeted_field_correctness_v2.json"
    assert not out.exists()
    out.write_text(json.dumps(report, indent=2))
    print(
        {
            "verified_conversions": report["conversion_numerator"],
            "fields": len(checks),
            "remaining_staging": len(store.projection_staging),
        }
    )


if __name__ == "__main__":
    main()
