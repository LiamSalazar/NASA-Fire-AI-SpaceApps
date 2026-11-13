"""Backend-owned wording for exact, source-validated structured fields.

This verifies a graph quantity and its original cell, then renders only that fact.
It never certifies arbitrary model wording or infers experimental applicability.
"""


def structured_fact(record_id, store, registry):
    record = store.payload(record_id)
    subject, pid = record.get("subject"), record.get("property_id")
    qualifiers = record.get("qualifiers", {})
    if not subject or pid not in store.registry.properties or not qualifiers.get("source_header"):
        return None
    if not any(
        record_id in store.relations(subject, relation)
        for relation in ("hasCondition", "hasMeasurement", "hasRecordedField")
    ):
        return None
    raw = qualifiers.get("original_value")
    refs = store.evidence(record_id)
    verified = []
    for eid in refs:
        source = registry.resolve(eid)
        if source and any(
            cell.get("original_header", "").strip() == qualifiers["source_header"]
            and cell.get("original_value") == raw
            for cell in source.get("source_cells", [])
        ):
            verified.append(eid)
    if not verified:
        return None
    definitions = []
    if qualifiers.get("scientific_role") == "instrument_capacity_nitrogen_basis":
        from rdflib import RDF

        from nasa_fire_ai.query.native import identity, node

        for candidate in store.graph.subjects(RDF.type, node("SourceFieldDefinition")):
            definition_id = identity(candidate)
            if not (set(store.sources(record_id)) & set(store.sources(definition_id))):
                continue
            definition = store.payload(definition_id)
            original = definition.get("qualifiers", {}).get("original_value")
            if not original:
                continue
            for eid in store.evidence(definition_id):
                source = registry.resolve(eid)
                if source and original in source["text"]:
                    definitions.append(
                        {"evidence_id": eid, "text": original, "scope": "table_field_definition"}
                    )
    from nasa_fire_ai.services.source_definitions import registered_quotation_fragments

    for definition_id in store.relations(record_id, "hasTermDefinition"):
        if "ScientificTermDefinition" not in store.classes(definition_id):
            continue
        definition = store.payload(definition_id)
        if pid not in definition.get("defined_properties", []):
            continue
        fragments = registered_quotation_fragments(
            definition.get("text", ""),
            store.evidence(definition_id),
            registry,
            context_id=definition_id,
        )
        definitions.extend(
            {**fragment, "scope": "table_field_definition"} for fragment in fragments
        )
    # Follow explicit source annotations only from this record. An annotation
    # mentioning another specimen cannot establish a condition for this one.
    for annotation in store.relations(subject, "hasSourceAnnotation"):
        for field in store.relations(annotation, "hasRecordedField"):
            payload = store.payload(field)
            original = payload.get("qualifiers", {}).get("original_value")
            if not original:
                continue
            for eid in store.evidence(field):
                source = registry.resolve(eid)
                if source and any(
                    cell.get("original_value") == original
                    for cell in source.get("source_cells", [])
                ):
                    definitions.append(
                        {"evidence_id": eid, "text": original, "scope": "source_record_annotation"}
                    )
    investigations = sorted(store.relations(subject, "belongsToInvestigation"))
    titles = [store.payload(identity).get("title", identity) for identity in investigations]
    if not titles:
        return None
    label = store.payload(subject).get("reported_identifier")
    if label:
        record_label = f"record {label}"
    else:
        original = registry.resolve(verified[0]) or {}
        ordinal = original.get("structured_location", {}).get("row_ordinal")
        record_label = (
            f"record at table row {ordinal}" if ordinal is not None else f"record {subject}"
        )
    name = qualifiers.get("scientific_label") or qualifiers["source_header"]
    basic_record_label = record_label
    description = store.payload(subject).get("reported_material_description")
    if (
        description
        and pid != "source:material_description"
        and any(
            cell.get("original_value") == description
            for eid in verified
            for cell in (registry.resolve(eid) or {}).get("source_cells", [])
        )
    ):
        record_label += f" (recorded material description: {description})"
    # Figure/reference values need their own original record description,
    # not just an opaque numeric row label or a detached publication URL.
    if pid != "source:data_description" and "source:data_description" in store.registry.properties:
        descriptions = set()
        for descriptor in store.value_records(subject, "source:data_description"):
            original = descriptor["qualifiers"].get("original_value")
            header = descriptor["qualifiers"].get("source_header")
            if original and any(
                cell.get("original_header", "").strip() == header
                and cell.get("original_value") == original
                for eid in set(verified) & set(descriptor["evidence_ids"])
                for cell in (registry.resolve(eid) or {}).get("source_cells", [])
            ):
                descriptions.add(original)
        if len(descriptions) == 1:
            record_label += f" (data description: {next(iter(descriptions))})"
    context = qualifiers.get("context")
    if context and context not in {"reported", "initial", "final"}:
        name += f" ({context.replace('_', ' ')})"
    unit = "" if pid == "source:unparsed_quantity" else qualifiers.get("original_unit") or ""
    display = str(raw).strip()
    if qualifiers.get("source_quantity_expression"):
        expression = qualifiers["source_quantity_expression"]
        if expression not in raw:
            return None
        display = expression
    if unit and not display.lower().endswith(unit.lower()):
        display += " " + unit
    text = f"The {'; '.join(titles)} source {record_label} lists {name} as {display}."
    core_text = f"The {'; '.join(titles)} source {basic_record_label} lists {name} as {display}."
    if qualifiers.get("scientific_role") == "source_field_definition":
        text = f"The {'; '.join(titles)} table defines its fields as follows: {display}"
        core_text = text
    return {
        "text": text,
        "core_text": core_text,
        "field_text": f"The record lists {name} as {str(raw).strip() if unit == 'count' else display}.",
        "property_id": qualifiers.get("intended_property") or pid,
        "primary_evidence_ids": verified,
        "record_id": record_id,
        "subject": subject,
        "evidence_ids": list(dict.fromkeys([*verified, *[s["evidence_id"] for s in definitions]])),
        "definition_spans": definitions,
        "primary_span": {"evidence_id": verified[0], "text": raw, "scope": "table_field_definition"}
        if qualifiers.get("scientific_role") == "source_field_definition"
        else None,
        "role": qualifiers.get("scientific_role"),
        "verification_mechanism": "typed_original_cell_projection",
    }


def record_scope_fact(subject, store, registry):
    """Explain the curated representation boundary, not a new NASA finding."""
    classes = store.classes(subject)
    boundaries = {
        "SourceAnnotation": "an original source annotation, applicable only within its recorded reference scope",
        "DataProductReference": "a data product reference, without a measured value or an identified physical instrument",
        "MaintenanceRecord": "a maintenance entry, without asserting an experimental combustion run",
        "PublicationFigureReference": "a publication-figure reference; figure identifiers are not treated as measured experimental quantities",
        "ConfigurationSummary": "a configuration summary; alternatives are not expanded into individual experimental runs",
        "ExperimentalSession": "a session summary; individual physical run identities are not reconciled from this row",
        "SourceRecord": "a source acquisition record; repeated labels are not reconciled into distinct physical experiments",
    }
    kind = next((key for key in boundaries if key in classes), None)
    investigations = store.relations(subject, "belongsToInvestigation")
    if not kind or not investigations:
        return None
    refs = [
        eid for eid in store.evidence(subject) if (registry.resolve(eid) or {}).get("source_cells")
    ]
    if not refs:
        return None
    row = registry.resolve(refs[0])["structured_location"]["row_ordinal"]
    title = "; ".join(store.payload(sid).get("title", sid) for sid in sorted(investigations))
    return {
        "text": f"The engine retains {title} table row {row} as {boundaries[kind]}.",
        "record_id": subject,
        "subject": subject,
        "evidence_ids": refs,
        "verification_mechanism": "curated_source_record_scope",
    }


def projection_fact(anchor, search):
    """Recompute an exact backend projection; model-provided flags are insufficient."""
    if not getattr(search, "store", None) or not anchor.get("structured_record_id"):
        return None
    renderer = (
        record_scope_fact if anchor.get("projection_kind") == "record_scope" else structured_fact
    )
    fact = renderer(anchor["structured_record_id"], search.store, search.registry)
    return fact if fact and fact["text"] == anchor.get("deterministic_text") else None
