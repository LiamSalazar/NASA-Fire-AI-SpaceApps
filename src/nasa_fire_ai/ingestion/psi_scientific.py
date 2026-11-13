"""Curated PSI table semantics, with source-record identity and exact cell lineage.

Interpretation authority is domain/psi_table_mappings.yaml, never a user query.
Session summaries and configuration alternatives do not assert individual runs.
"""

import json
import re
from functools import lru_cache

import yaml

from nasa_fire_ai.normalization.units import interpret
from nasa_fire_ai.query.v2 import GenericValue, PropertyDefinition


@lru_cache(maxsize=8)
def mappings(root):
    return yaml.safe_load((root / "domain/psi_table_mappings.yaml").read_text())["tables"]


def register_properties(store, root):
    auxiliary = yaml.safe_load((root / "domain/psi_auxiliary_rows.yaml").read_text())
    profiles = [
        *mappings(root).items(),
        *(
            (investigation, profile)
            for investigation, records in auxiliary.items()
            for profile in records.values()
        ),
    ]
    for investigation, profile in profiles:
        if profile.get("aliases"):
            existing = store.registry.entity_mentions.get(investigation.lower(), {})
            store.registry.entity_mentions[investigation.lower()] = {
                "relation": "belongsToInvestigation",
                "aliases": sorted(set(existing.get("aliases", [])) | set(profile["aliases"])),
            }
        for header, field in profile["fields"].items():
            pid = field["property"]
            if pid in store.registry.properties:
                definition = store.registry.properties[pid]
                aliases = list(
                    dict.fromkeys([*definition.aliases, header, *field.get("aliases", [])])
                )
                if aliases != definition.aliases:
                    from dataclasses import replace

                    store.registry.properties[pid] = replace(definition, aliases=aliases)
                continue
            unit = field.get("unit")
            info = interpret(unit)
            store.registry.register(
                PropertyDefinition(
                    pid,
                    info["dimension"] if info else "none",
                    info["canonical_unit"] if info else None,
                    datatype=field.get("datatype", "numeric"),
                    aliases=[
                        field.get("label", header),
                        header,
                        pid.removeprefix("source:").replace("_", " "),
                        *field.get("aliases", []),
                    ],
                )
            )
    for pid in ("material_description", "unparsed_quantity"):
        store.registry.register(
            PropertyDefinition(
                "source:" + pid,
                "none",
                None,
                datatype="categorical",
                aliases=[
                    pid.replace("_", " "),
                    *sorted(
                        {
                            p["material_header"]
                            for p in mappings(root).values()
                            if p.get("material_header")
                        }
                    ),
                ]
                if pid == "material_description"
                else [pid.replace("_", " ")],
            )
        )


def cell_value(raw, field):
    """Parse only explicit scalar/range/alternative syntax; never mine prose digits."""
    if field.get("datatype") == "categorical":
        return GenericValue(reported_value=raw, raw_expression=raw)
    number = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
    unit = field["unit"]
    # A printed unit overrides the header only if dimensionally compatible.
    body = raw.strip()
    printed = re.search(
        r"\s*(mg/min|mg/s|cm/s|mm/s|slpm|sccm|mmHg|atm|bar|ppm|mm|cm|°C|K|W|s|%)\s*$",
        body,
        re.IGNORECASE,
    )
    if field.get("require_printed_unit") and not printed:
        raise ValueError("Original cell supplies no quantitative unit")
    if printed:
        candidate = printed.group(1)
        if interpret(candidate) != interpret(unit):
            a, b = interpret(candidate), interpret(unit)
            if not a or not b or a["dimension"] != b["dimension"]:
                raise ValueError("Incompatible printed unit")
        unit = candidate
        body = body[: printed.start()].strip()
    body = re.sub(r"(?<=\d)%", "", body)
    approximate = body.startswith(("~", "≈"))
    body = body.lstrip("~≈ ").strip()
    interval = re.fullmatch(rf"({number})\s*[-–]\s*({number})", body)
    if interval:
        return GenericValue(
            lower=float(interval[1]),
            upper=float(interval[2]),
            reported_unit=unit,
            raw_expression=raw,
            approximate=approximate,
        )
    if re.fullmatch(number, body):
        return GenericValue(
            reported_value=float(body),
            reported_unit=unit,
            raw_expression=raw,
            approximate=approximate,
        )
    alternatives = re.split(r"\s*;\s*(?:or\s+)?", body)
    if len(alternatives) > 1 and all(re.fullmatch(number, x.strip()) for x in alternatives):
        # Separate values keep their common summary scope; no Cartesian run expansion.
        return [
            GenericValue(
                reported_value=float(x),
                reported_unit=unit,
                raw_expression=raw,
                approximate=approximate,
            )
            for x in alternatives
        ]
    raise ValueError("Not an unambiguous quantitative expression")


def import_fields(
    store, evidence, root, accession, subject, row, headers, eid, counts, *, profile=None
):
    profile = mappings(root).get(accession, {}) if profile is None else profile
    fields = dict(profile.get("fields", {}))
    material_header = profile.get("material_header")
    if material_header:
        fields[material_header] = {
            "property": "source:material_description",
            "datatype": "categorical",
            "role": "reported_material_description",
        }
    for header, field in fields.items():
        raw = row.get(header, "")
        if not raw.strip():
            continue
        column = headers.index(header) + 1
        try:
            expression = field.get("quantity_expression")
            if expression and expression not in raw:
                raise ValueError("Reviewed quantity is absent from the original annotation")
            values = cell_value(expression.replace(" to ", "–") if expression else raw, field)
            pid = field["property"]
        except ValueError:
            # Preserve ambiguous or nonnumeric original content as unresolved, not a measurement.
            values = GenericValue(reported_value=raw, raw_expression=raw)
            pid = "source:unparsed_quantity"
            counts["unresolved_quantities"] += 1
        if not isinstance(values, list):
            values = [values]
        for i, value in enumerate(values):
            rid = f"{subject}-field-{column}-{i}"
            role = field["role"]
            cls = (
                "Measurement"
                if role == "reported_measurement"
                else "ExperimentalCondition"
                if role == "reported_condition"
                else "ReportedField"
            )
            if role == "source_field_definition":
                cls = "SourceFieldDefinition"
            qualifiers = {
                "scientific_role": role,
                "modality": role,
                "original_value": raw,
                "original_unit": value.reported_unit or "",
                "context": field.get("context", "reported"),
                "verification_status": "SOURCE_CELL_VERIFIED",
                "record_scope": profile.get("record_class", "existing"),
                "source_header": header,
                "scientific_label": field.get("label"),
                "limitations": "Summary alternatives do not establish simultaneous conditions or distinct physical runs.",
            }
            if field.get("quantity_expression") and pid != "source:unparsed_quantity":
                qualifiers["source_quantity_expression"] = field["quantity_expression"]
                value.raw_expression = raw
            if pid == "source:unparsed_quantity":
                cls = "ReportedField"
                qualifiers["verification_status"] = "EXACT_CELL_SEMANTICS_UNRESOLVED"
                qualifiers["intended_property"] = field["property"]
            store.add_value(rid, subject, pid, value, [eid], qualifiers, class_id=cls)
            store.add_relation(
                subject,
                "hasMeasurement"
                if cls == "Measurement"
                else "hasCondition"
                if cls == "ExperimentalCondition"
                else "hasRecordedField",
                rid,
                [eid],
            )
            evidence.db.execute(
                "CREATE TABLE IF NOT EXISTS value_cells (value_id TEXT PRIMARY KEY, evidence_id TEXT, column_ordinal INTEGER)"
            )
            evidence.db.execute("INSERT INTO value_cells VALUES (?,?,?)", (rid, eid, column))
            counts["curated_values"] += 1
    evidence.db.commit()


def import_auxiliary_record(store, evidence, root, accession, row, headers, eid, ordinal, counts):
    """Apply reviewed original-row mappings without asserting an executed trial."""
    profiles = yaml.safe_load((root / "domain/psi_auxiliary_rows.yaml").read_text())
    profile = profiles.get(accession, {}).get(ordinal)
    if profile is None:
        return False
    sid = accession.lower()
    subject = f"{sid}-annotation-{ordinal}"
    # A changed source layout must not silently attach a reviewed interpretation
    # to another record. The file checksum is independently checked by the build.
    if any(row.get(header) != raw for header, raw in profile["expected"].items()):
        raise ValueError(f"Auxiliary source identity mismatch: {accession} row {ordinal}")
    store.add_entity(
        subject,
        profile["class"],
        [eid],
        [sid],
        {
            "id": subject,
            "reported_identifier": profile["identifier"],
            "text": json.dumps(row, ensure_ascii=False),
            "identity_scope": "original auxiliary source record; not an executed trial",
            "annotation_kind": profile["kind"],
            "reference_scope": profile.get("references", []),
        },
    )
    store.add_relation(subject, "belongsToInvestigation", sid, [eid])
    store.add_relation(sid, "hasSourceRecord", subject, [eid])
    import_fields(
        store,
        evidence,
        root,
        accession,
        subject,
        row,
        headers,
        eid,
        counts,
        profile={"record_class": profile["class"], "fields": profile["fields"]},
    )
    counts[profile["class"]] += 1
    for target in profile.get("references", []):
        record = f"{sid}-{target['record']}"
        if not store.evidence(record):
            raise ValueError(f"Auxiliary target does not exist: {record}")
        cells = [
            cell
            for ref in store.evidence(record)
            for cell in evidence.resolve(ref).get("source_cells", [])
        ]
        if not any(
            cell["original_header"].strip() == target["column"]
            and target["marker"] in cell["original_value"]
            for cell in cells
        ):
            raise ValueError(f"Original source lacks annotation marker: {record}")
        refs = [eid, *store.evidence(record)]
        store.add_relation(record, "hasSourceAnnotation", subject, refs)
        store.add_relation(subject, "referencesSourceRecord", record, refs)
        for relation in ("hasCondition", "hasMeasurement", "hasRecordedField"):
            for field in store.relations(record, relation):
                if (
                    store.payload(field).get("qualifiers", {}).get("source_header")
                    == target["column"]
                ):
                    store.add_relation(field, "hasSourceAnnotation", subject, refs)
    return True


def material_description(store, subject, raw, header, eid, source_id):
    """Represent a reported description without inferring chemical identity."""
    if not raw.strip():
        return
    identity = subject + "-material-description"
    store.add_entity(
        identity,
        "ReportedMaterialDescription",
        [eid],
        [source_id],
        {
            "id": identity,
            "text": raw,
            "source_header": header,
            "identity_scope": "source_record_description; no purity or cross-record equivalence asserted",
        },
    )
    store.add_relation(subject, "hasMaterialDescription", identity, [eid])


def import_record(store, evidence, root, accession, row, headers, eid, ordinal, counts):
    profile = mappings(root)[accession]
    sid = accession.lower()
    # Source row is the identity when no explicit run identity exists. Repeated times
    # and dates are labels; neither merging nor distinct physical trials is asserted.
    subject = f"{sid}-record-{ordinal}"
    label = row.get(profile.get("identifier"), "")
    cls = profile["record_class"]
    store.add_entity(
        subject,
        cls,
        [eid],
        [sid],
        {
            "id": subject,
            "reported_identifier": label,
            "reported_material_description": row.get(profile["material_header"], ""),
            "identity_scope": "source_record; no physical identity reconciliation",
            "modality": "reported_table_record",
            "text": json.dumps(row, ensure_ascii=False),
        },
    )
    store.add_relation(subject, "belongsToInvestigation", sid, [eid])
    store.add_relation(
        sid, "hasRun" if cls == "ExperimentalRun" else "hasSourceRecord", subject, [eid]
    )
    material_description(
        store,
        subject,
        row.get(profile["material_header"], ""),
        profile["material_header"],
        eid,
        sid,
    )
    import_fields(store, evidence, root, accession, subject, row, headers, eid, counts)
    counts[cls] += 1


def import_documentation(store, evidence, path, passage, register_source):
    """Expose original official PSI narrative fields with explicit epistemic roles."""
    data = json.loads(path.read_text())
    result = []
    for study_index, study in enumerate(data.get("studies", [])):
        accession = study["identifier"]
        sid = "documentation-" + accession.lower()
        title = study.get("title", accession)
        checksum = register_source(
            evidence,
            sid,
            path,
            title,
            f"https://psi.nasa.gov/physci/repo/data/investigations/{accession}",
            "NASA PSI investigation documentation",
        )
        comments = study.get("comments", [])
        for index, item in enumerate(comments):
            name, text = item.get("name", ""), item.get("value", "")
            if not text.strip() or name not in {
                "Approach",
                "Objective",
                "Hypothesis",
                "Experiment Hardware",
                "Significance",
                "Results",
                "Summary",
                "Description",
                "Flight Platform",
            }:
                continue
            eid = passage(
                evidence,
                sid,
                path,
                checksum,
                {
                    "kind": "investigation_documentation",
                    "field": name,
                    "json_pointer": f"/studies/{study_index}/comments/{index}/value",
                },
                text,
            )
            investigation = accession.lower()
            if "Investigation" not in store.classes(investigation):
                store.add_entity(
                    investigation,
                    "Investigation",
                    [eid],
                    [sid],
                    {"id": investigation, "title": title},
                )
            cls, relation = {
                "Objective": ("ResearchObjective", "hasObjective"),
                "Hypothesis": ("ResearchHypothesis", "hasHypothesis"),
                "Approach": ("DocumentaryMethod", "hasDocumentedMethod"),
                "Experiment Hardware": ("Apparatus", "usesApparatus"),
            }.get(name, ("Document", "hasDocumentation"))
            subject = f"{sid}-{index}"
            store.add_entity(
                subject,
                cls,
                [eid],
                [sid],
                {
                    "id": subject,
                    "text": text,
                    "title": name,
                    "scientific_role": name,
                    "modality": "source_reported_documentation",
                    "limitations": "Investigation-level narrative; no run-level conditions inherited. Hypotheses and objectives are not observations.",
                },
            )
            store.add_relation(investigation, relation, subject, [eid])
        result.append({"source_id": sid, "depth": "B", "scope": "investigation_documentation"})
        if study.get("publications"):
            bibliographic_source = "catalog-publications-" + accession.lower()
            checksum = register_source(
                evidence,
                bibliographic_source,
                path,
                title + " publication references",
                f"https://psi.nasa.gov/physci/repo/data/investigations/{accession}",
                "NASA PSI publication catalogue metadata",
            )
            for index, publication in enumerate(study["publications"]):
                eid = passage(
                    evidence,
                    bibliographic_source,
                    path,
                    checksum,
                    {
                        "kind": "publication_metadata",
                        "json_pointer": f"/studies/{study_index}/publications/{index}",
                    },
                    json.dumps(publication, ensure_ascii=False),
                )
                identity = f"{bibliographic_source}-{index}"
                store.add_entity(
                    identity,
                    "Publication",
                    [eid],
                    [bibliographic_source],
                    {
                        "id": identity,
                        "title": publication.get("title"),
                        "doi": publication.get("doi"),
                        "authors": publication.get("authorList"),
                        "metadata_only": True,
                        "identity_scope": "source_metadata_record; duplicate DOI records are not asserted to be distinct papers",
                        "limitations": "Bibliographic metadata, not inspected full-text scientific findings",
                    },
                )
                store.add_relation(accession.lower(), "hasPublicationReference", identity, [eid])
            result.append(
                {
                    "source_id": bibliographic_source,
                    "depth": "C",
                    "scope": "publication_metadata",
                    "records": len(study["publications"]),
                }
            )
    return result


def import_report_assertions(store, evidence, root):
    """Load reviewed quotations, validating every fragment against registered pages."""
    path = root / "domain/psi_report_assertions.yaml"
    curated = yaml.safe_load(path.read_text())
    evidence.db.execute("""CREATE TABLE IF NOT EXISTS curated_quotation_parts (
        context_id TEXT NOT NULL, part_ordinal INTEGER NOT NULL,
        evidence_id TEXT NOT NULL REFERENCES passages(evidence_id),
        part_text TEXT NOT NULL, passage_start INTEGER NOT NULL,
        passage_end INTEGER NOT NULL, source_checksum TEXT NOT NULL,
        PRIMARY KEY(context_id, part_ordinal))""")

    def original(source_id, page):
        rows = evidence.db.execute(
            "SELECT p.* FROM passages p JOIN documents d USING(document_id) WHERE d.source_id=? AND p.page=?",
            (source_id, page),
        ).fetchall()
        if len(rows) != 1:
            raise ValueError("Curated statement requires one registered source page")
        return dict(rows[0])

    for statement in curated["statements"]:
        fragments, refs = [], []
        for part_ordinal, part in enumerate(statement["parts"]):
            source = original(statement["source_id"], part["physical_page"])
            if part["text"] not in source["text"]:
                raise ValueError("Curated quotation is not an exact original source fragment")
            fragments.append(part["text"])
            refs.append(source["evidence_id"])
            start = source["text"].index(part["text"])
            evidence.db.execute(
                "INSERT INTO curated_quotation_parts VALUES (?,?,?,?,?,?,?)",
                (
                    statement["id"],
                    part_ordinal,
                    source["evidence_id"],
                    part["text"],
                    start,
                    start + len(part["text"]),
                    source["checksum"],
                ),
            )
        attributes = statement.get("instrument_attributes", {})
        if attributes and statement["class"] != "Instrument":
            raise ValueError("Instrument facets require an explicitly typed instrument description")
        store.add_entity(
            statement["id"],
            statement["class"],
            refs,
            [statement["source_id"]],
            {
                "id": statement["id"],
                "title": statement.get("title"),
                "identity_scope": statement.get("identity_scope"),
                "text": "\n".join(fragments),
                **({"instrument_attributes": attributes} if attributes else {}),
                "attribution": "verbatim inspected NASA source",
                "scope": statement.get(
                    "scope", "investigation-level source statement; no run conditions inherited"
                ),
                **(
                    {"defined_properties": statement["defined_properties"]}
                    if statement.get("defined_properties")
                    else {}
                ),
            },
        )
        from rdflib import OWL, RDF, Literal

        from nasa_fire_ai.query.native import node

        for property_id, value in attributes.items():
            if (node(property_id), RDF.type, OWL.DatatypeProperty) not in store.graph:
                raise ValueError("Instrument attribute is not approved in the ontology")
            if not isinstance(value, str) or not re.search(
                r"(?<!\w)" + re.escape(value) + r"(?!\w)", "\n".join(fragments)
            ):
                raise ValueError("Instrument attribute is not an exact original source expression")
            store.graph.add((node(statement["id"]), node(property_id), Literal(value)))

        for extra_class in statement.get("also_classes", []):
            if (node(extra_class), RDF.type, OWL.Class) not in store.graph:
                raise ValueError("Curated additional class is not approved in the ontology")
            store.graph.add((node(statement["id"]), RDF.type, node(extra_class)))
        if statement.get("apparatus"):
            parent = statement["apparatus"]
            if "Apparatus" not in store.classes(parent):
                raise ValueError("Instrument requires an already documented apparatus")
            store.add_relation(
                parent, "hasInstrument", statement["id"], [*refs, *store.evidence(parent)]
            )
        if statement.get("defined_properties"):
            if statement["class"] != "ScientificTermDefinition":
                raise ValueError("Nomenclature mappings require a ScientificTermDefinition")
            from nasa_fire_ai.query.native import NS, identity

            for property_id in statement["defined_properties"]:
                if property_id not in store.registry.properties:
                    raise ValueError("Definition refers to an unapproved scientific property")
                for value in list(store.graph.subjects(NS.measuredProperty, node(property_id))):
                    store.add_relation(
                        identity(value),
                        "hasTermDefinition",
                        statement["id"],
                        list(dict.fromkeys([*store.evidence(identity(value)), *refs])),
                    )
        for investigation in statement["investigations"]:
            if "Investigation" not in store.classes(investigation):
                raise ValueError("Unknown investigation in curated report mapping")
            store.add_relation(investigation, statement["relation"], statement["id"], refs)
            for relation in statement.get("additional_relations", []):
                if relation not in store.registry.relations:
                    raise ValueError("Curated additional relation is not approved in the ontology")
                store.add_relation(investigation, relation, statement["id"], refs)
        if statement.get("context_statement"):
            context = statement["context_statement"]
            store.add_relation(
                statement["id"],
                "hasFindingContext",
                context,
                list(dict.fromkeys(refs + store.evidence(context))),
            )
    for campaign in curated.get("campaigns", []):
        refs = [
            original(campaign["source_id"], page)["evidence_id"]
            for page in campaign["evidence_pages"]
        ]
        store.add_entity(
            campaign["id"],
            "Campaign",
            refs,
            [campaign["source_id"]],
            {
                "id": campaign["id"],
                "title": campaign["title"],
                "scope": "source-reported group of investigations; not equivalent experimental regimes",
            },
        )
        for investigation in campaign["investigations"]:
            store.add_relation(campaign["id"], "hasInvestigation", investigation, refs)
    evidence.db.commit()
