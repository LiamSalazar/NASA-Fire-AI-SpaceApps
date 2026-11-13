"""Conservative enrichment of existing canonical source fields and specimens."""

import csv
import json
import re
from pathlib import Path

import yaml
from rdflib import RDF, Literal

from nasa_fire_ai.normalization.units import normalize
from nasa_fire_ai.query.native import NS, node
from nasa_fire_ai.query.v2 import GenericValue, PropertyDefinition


def source_rows(evidence, root):
    path = Path(evidence["raw_file"])
    if not path.is_absolute():
        path = root / path
    if not path.exists():
        path = root / "data/raw" / evidence["raw_file"]
    if not path.exists() or path.suffix.lower() != ".csv":
        return None, None
    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        # Legacy NASA CSVs contain Windows punctuation; never replace invalid bytes.
        text = path.read_text(encoding="cp1252")
    import io

    with io.StringIO(text, newline="") as handle:
        reader = csv.reader(handle)
        headers = next(reader)
        target = next(csv.reader([evidence["text"]]))
        matches = [row for row in reader if row == target]
    if len(matches) != 1 or len(headers) != len(target):
        return None, None
    return headers, target


def specimen_dimensions(label):
    """Explicit dimension/unit/attribute expressions only; unlabelled sizes remain unknown."""
    rows = []
    for match in re.finditer(
        r"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>cm|mm|micron|µm|μm)\s*(?P<axis>wide|thick|long)\b",
        label,
        re.IGNORECASE,
    ):
        original_unit = match["unit"]
        unit = "um" if original_unit.lower() in {"micron", "µm", "μm"} else original_unit
        value, canonical = normalize(float(match["value"]), unit)
        rows.append(
            {
                "attribute": {"wide": "width", "thick": "thickness", "long": "length"}[
                    match["axis"].lower()
                ],
                "reported_value": match["value"],
                "reported_unit": original_unit,
                "canonical_value": value,
                "canonical_unit": canonical,
                "source_span": match.group(),
                "start": match.start(),
                "end": match.end(),
                "role": "SPECIMEN_CHARACTERISTIC",
                "publication_status": "REVIEW_REQUIRED",
            }
        )
    return rows


def enrich_source_fields(store, records, evidence_registry, root, approved_mentions):
    """New source-field accessors use existing fs:conditionType/fs:value semantics.

    No ontology measurement classes, taxonomy relations, or inferred units are introduced.
    """
    config = yaml.safe_load((root / "domain/source_field_accessors.yaml").read_text())
    report = {"mapped": [], "staged": [], "specimens": [], "additional_materials": []}
    newly_executable = 0
    runs = {
        cid: run["id"]
        for run in records
        if run["type"] == "ExperimentalRunRecord"
        for cid in run["condition_ids"]
    }
    for record in records:
        if record["type"] != "ConditionRecord":
            continue
        kind = record["kind"]
        meta = config["fields"].get(kind)
        if not meta:
            continue
        refs = [e["evidence_id"] for e in record["evidence_refs"]]
        if not refs or any(evidence_registry.resolve(e) is None for e in refs):
            report["staged"].append({"record": record, "reason": "missing evidence"})
            continue
        value = record.get("reported_value")
        try:
            if not isinstance(value, (int, float)):
                raise TypeError("non-numeric or insufficient source value")
            normalized, unit = normalize(value, record["reported_unit"])
            if unit != meta["unit"]:
                raise ValueError("dimension differs from source-field contract")
            selector = "source:" + kind
            store.registry.register(
                PropertyDefinition(
                    selector,
                    meta["dimension"],
                    meta["unit"],
                    aliases=[kind, kind.replace("_", " ")],
                    context=meta.get("context", "SOURCE_FIELD_ACCESSOR"),
                )
            )
            qualifiers = {
                "role": meta["role"],
                "context": meta.get("context", "SOURCE_FIELD_ACCESSOR"),
                "source_field": kind,
                "observed_status": "NOT_ASSERTED",
                "original_record": record,
                "mapping_version": config["version"],
            }
            was_executable = (node(record["id"]), RDF.type, NS.SemanticValue) in store.graph
            store.add_value(
                record["id"],
                runs[record["id"]],
                selector,
                GenericValue(
                    reported_value=value,
                    reported_unit=record["reported_unit"],
                    canonical_value=normalized,
                    canonical_unit=unit,
                ),
                refs,
                qualifiers,
                class_id="ExperimentalCondition",
            )
            newly_executable += not was_executable
            # A single deterministic payload; original record is retained in qualifiers.
            payload = {
                "id": record["id"],
                "subject": runs[record["id"]],
                "property_id": selector,
                "value": {
                    "reported_value": value,
                    "reported_unit": record["reported_unit"],
                    "canonical_value": normalized,
                    "canonical_unit": unit,
                },
                "qualifiers": qualifiers,
                "evidence_ids": refs,
            }
            store.graph.remove((node(record["id"]), NS.payload, None))
            store.graph.add(
                (node(record["id"]), NS.payload, Literal(json.dumps(payload, sort_keys=True)))
            )
            report["mapped"].append(
                {
                    "record_id": record["id"],
                    "property_id": selector,
                    "original": record,
                    "qualifiers": qualifiers,
                    "normalization": payload["value"],
                }
            )
        except (ValueError, TypeError, LookupError, KeyError) as exc:
            report["staged"].append({"record": record, "reason": str(exc)})
    from nasa_fire_ai.ingestion.knowledge import normalize_mention

    for record in records:
        if record["type"] != "SampleRecord":
            continue
        label = record["material"]
        resolved = normalize_mention(label, approved_mentions)
        refs = [e["evidence_id"] for e in record["evidence_refs"]]
        disposition = (
            "NORMALIZABLE_WITH_APPROVED_VOCABULARY"
            if resolved["identity"]
            else "INSUFFICIENT_SOURCE_CONTEXT"
        )
        # Source column Fuel + exact atomic material name: identity literal already canonical,
        # not a new alias, family membership, or external chemical assertion.
        source_identity = False
        if not resolved["identity"] and re.fullmatch(r"[A-Za-z]+", label):
            for ref in refs:
                passage = evidence_registry.resolve(ref)
                if not passage:
                    continue
                headers, row = source_rows(passage, root)
                if headers and "Fuel" in headers and row[headers.index("Fuel")] == label:
                    source_identity = True
                    break
        if source_identity:
            resolved["identity"] = label
            disposition = "NORMALIZABLE_WITH_APPROVED_VOCABULARY"
            store.add_entity(
                label,
                "Material",
                refs,
                [e["source_id"] for e in record["evidence_refs"]],
                {"id": label},
            )
            store.add_relation(record["id"], "madeOf", label, refs)
            for run in records:
                if run["type"] == "ExperimentalRunRecord" and run["sample_id"] == record["id"]:
                    store.add_relation(run["id"], "hasMaterial", label, refs)
            report["additional_materials"].append(
                {
                    "sample_id": record["id"],
                    "identity": label,
                    "authority": "Exact canonical material and immutable Fuel cell",
                    "evidence_ids": refs,
                }
            )
        elif not resolved["identity"]:
            if not re.search(r"[0-9]", label) and re.search(r"[A-Za-z]", label):
                disposition = "REQUIRES_NEW_ALIAS"
            elif not re.search(r"[A-Za-z]", label):
                disposition = "NOT_A_MATERIAL_DESCRIPTION"
        report["specimens"].append(
            {
                "sample_id": record["id"],
                "original_description": label,
                "identity": resolved["identity"],
                "disposition": disposition,
                "dimensions": specimen_dimensions(label),
                "evidence_ids": refs,
                "specimen_identity_preserved": True,
            }
        )
    store.registry.entity_mentions = {
        **getattr(store.registry, "entity_mentions", {}),
        **{
            row["identity"]: {
                "relation": "hasMaterial",
                "aliases": list(
                    dict.fromkeys(
                        [
                            *getattr(store.registry, "entity_mentions", {})
                            .get(row["identity"], {})
                            .get("aliases", []),
                            row["identity"],
                        ]
                    )
                ),
                "authority": "Canonical identity and exact immutable Fuel cell",
            }
            for row in report["additional_materials"]
        },
    }
    resolved_fields = {row["record_id"] for row in report["mapped"]}
    store.projection_staging = [
        row
        for row in store.projection_staging
        if row.get("provenance", {}).get("id") not in resolved_fields
    ]
    store.projection_report = {
        **store.projection_report,
        "conditions": store.projection_report["conditions"] + newly_executable,
        "unknown_fields_staged": len(store.projection_staging),
        "source_field_accessor_version": config["version"],
    }
    store.source_enrichment_report = report
    return report
