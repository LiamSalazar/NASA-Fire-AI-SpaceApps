"""Validated source crosswalks; preserve original records, units and epistemic roles."""

import hashlib
import json

from nasa_fire_ai.query.v2 import GenericValue, PropertyDefinition


def project_source_corrections(store, evidence, root, records):
    path = root / "artifacts/phase3c_targeted_flex_corrections_v3.json"
    if not path.exists():
        return
    report = json.loads(path.read_text())
    pdf = root / "data/raw/ntrs-20150023456.pdf"
    if hashlib.sha256(pdf.read_bytes()).hexdigest() != report["pdf_checksum"]:
        raise ValueError("correction source version mismatch")
    run_index = {
        cid: run["id"]
        for run in records
        if run["type"] == "ExperimentalRunRecord"
        for cid in run["condition_ids"]
    }
    for correction in report["corrections"]:
        original = correction["original_record"]
        passage = evidence.resolve(original["evidence_refs"][0]["evidence_id"])
        source = root / passage["raw_file"]
        if hashlib.sha256(source.read_bytes()).hexdigest() != correction["csv_checksum"]:
            raise ValueError("correction CSV source version mismatch")
        refs = [ref["evidence_id"] for ref in original["evidence_refs"]] + [
            correction["pdf"]["evidence_id"],
            correction["dictionary_evidence_id"],
        ]
        if any(evidence.resolve(eid) is None for eid in refs):
            raise ValueError("correction evidence unresolved")
        unit = correction["corrected_source_unit"]
        selector = "source:" + correction["kind"]
        context = (
            "initial"
            if correction["scientific_role"].startswith("INITIAL_")
            else "SOURCE_FIELD_ACCESSOR"
        )
        store.registry.register(
            PropertyDefinition(
                selector,
                "fraction" if unit == "fraction" else "area_per_time",
                "fraction" if unit == "fraction" else "m2/s",
                aliases=[correction["kind"].replace("_", " ")],
                context=context,
            )
        )
        store.add_value(
            "source-correction:" + original["id"],
            run_index[original["id"]],
            selector,
            GenericValue(reported_value=original["reported_value"], reported_unit=unit),
            refs,
            {
                "origin": "validated_source_crosswalk_v1",
                "role": correction["scientific_role"],
                "context": context,
                "original_record": original,
                "observed_status": "NOT_ASSERTED",
                "source_method": correction["method"],
                "source_unit_correction": unit,
                "original_nasa_test": correction["original_nasa_test"],
                "engineering_identifier": correction["engineering_identifier"],
            },
            class_id="ExperimentalCondition",
        )
    corrected_ids = {c["record_id"] for c in report["corrections"]}
    staging = getattr(store, "projection_staging", [])
    if not hasattr(store, "source_correction_original_staging_count"):
        store.source_correction_original_staging_count = len(staging)
    store.source_correction_report = {
        "corrected_records": len(corrected_ids),
        "corrected_by_kind": report["corrected_counts"],
        "historical_staging_count": store.source_correction_original_staging_count,
        "scientific_authority": "source-contract corroboration; independent review pending",
    }
    store.projection_staging = [
        row for row in staging if row.get("provenance", {}).get("id") not in corrected_ids
    ]
    store.source_correction_report["remaining_staging_count"] = len(store.projection_staging)
