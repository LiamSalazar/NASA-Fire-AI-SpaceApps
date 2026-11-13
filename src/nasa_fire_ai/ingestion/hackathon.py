"""Bounded source adapters into the existing registry and native RDF model.

No legacy projection, inferred campaign conditions, or model extraction is used.
"""

import csv
import hashlib
import json
import re
import shutil
import tempfile
from collections import Counter
from pathlib import Path

import pymupdf
import yaml

from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.knowledge import enrich_native, normalize_mention
from nasa_fire_ai.ingestion.semantic import load_semantic_registry
from nasa_fire_ai.ingestion.structured_provenance import register_cells, table_cells
from nasa_fire_ai.query.native import SemanticGraph
from nasa_fire_ai.query.native_interpreter import parse_expression
from nasa_fire_ai.query.v2 import GenericValue, PropertyDefinition

VERSION = "hackathon-corpus-v22"

# Existing approved condition subclasses, selected by explicit source-column meaning.
CONDITION_CLASSES = {
    "Pressure": "PressureCondition",
    "OxygenConcentration": "AtmosphereCondition",
    "AirflowVelocity": "FlowCondition",
    "FlowDirection": "FlowCondition",
}

# Source-header adapters, not query/answer rules. Only existing property meanings.
TABLES = {
    "PSI-10": (
        "Test",
        "Fuel",
        {
            "XO2 (init)": ("OxygenConcentration", "fraction", "initial"),
            "XO2 (final)": ("OxygenConcentration", "fraction", "final"),
            "pinit (atm)": ("Pressure", "atm", "initial"),
            "pfinal (atm)": ("Pressure", "atm", "final"),
        },
    ),
    "PSI-159": (
        "Test",
        "Fuel",
        {
            "XO2 before test": ("OxygenConcentration", "fraction", "initial"),
            "XO2  after test": ("OxygenConcentration", "fraction", "final"),
            "approx p (bar)": ("Pressure", "bar", "approximate"),
            "burn time (sec)": ("source:burn_time", "s", None),
        },
    ),
    "PSI-98": (
        "Sample Number",
        "Material",
        {
            "Air Flow (cm/s)": ("AirflowVelocity", "cm/s", None),
            "Percent O2": ("OxygenConcentration", "%", None),
            "Flow Direction": ("FlowDirection", None, None),
            "Burn Time (s)": ("source:burn_time", "s", None),
        },
    ),
    "PSI-100": (
        "Sample Number",
        "Material",
        {
            "Air Flow": ("AirflowVelocity", "cm/s", None),
            "Direction": ("FlowDirection", None, None),
        },
    ),
    "PSI-99": (
        "Sample Number",
        "Material",
        {
            "Air Flow (cm/s)": ("AirflowVelocity", "cm/s", None),
            "Percent O2 (Note 1)": ("OxygenConcentration", "%", None),
            "Flow Direction": ("FlowDirection", None, None),
            "Burn Time (s)": ("source:burn_time", "s", None),
        },
    ),
    "PSI-25": (
        "Test #",
        "Fuel Sample Material",
        {
            "Calibrated  initial O2 % by vol": ("OxygenConcentration", "%", "initial"),
            "Calibrated final O2 % by vol": ("OxygenConcentration", "%", "final"),
        },
    ),
    "PSI-26": ("As Run Test #", "Fuel Sample Material", {}),
    "PSI-69": (
        "FLEX Identifier",
        "Fuel",
        {
            "Ambient pressure; mmHg": ("Pressure", "mmHg", None),
            "O initial ambient composition; mole fraction": (
                "OxygenConcentration",
                "fraction",
                "initial",
            ),
            "Burn time; s": ("source:burn_time", "s", None),
            "Droplet initial diameter; mm": ("source:initial_droplet_diameter", "mm", "initial"),
            "Visible flame extinction diameter; mm": (
                "source:visible_flame_extinction_diameter",
                "mm",
                None,
            ),
        },
    ),
    "PSI-101": ("SAME Test #", "Sample Type", {}),
    # SAME is a specimen table; references to other rows are not expanded.
    "PSI-102": (
        "Sample #",
        "Sample Material",
        {
            "Air Flow (cm/s)": ("AirflowVelocity", "cm/s", None),
        },
    ),
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def psi_landing_url(accession):
    """Current public PSI investigation landing page for a registered accession."""
    if not re.fullmatch(r"PSI-\d+", accession):
        raise ValueError("Invalid PSI accession")
    return f"https://psi.nasa.gov/physci/repo/data/investigations/{accession}"


def make_store(root):
    store = SemanticGraph(load_semantic_registry(root / "domain/semantic_registry.yaml"))
    # Reuse the ontology loader; empty records avoid projecting unverified legacy facts.
    enrich_native(store, [], None, root / "ontology/fire_safety.ttl", {})
    enrich_native(store, [], None, root / "ontology/psi_science.ttl", {})
    from nasa_fire_ai.ingestion.psi_scientific import register_properties

    register_properties(store, root)
    fields = yaml.safe_load((root / "domain/source_field_accessors.yaml").read_text())
    for key, meta in fields["fields"].items():
        store.registry.register(
            PropertyDefinition(
                "source:" + key,
                meta["dimension"],
                meta["unit"],
                aliases=list(
                    dict.fromkeys(
                        [
                            key.replace("_", " "),
                            *getattr(store.registry.properties.get("source:" + key), "aliases", []),
                        ]
                    )
                ),
                context=meta.get("context"),
            )
        )
    from rdflib import RDF, RDFS, Literal, Namespace

    from nasa_fire_ai.query.native import node

    fs = Namespace("https://example.org/nasa-fire-safety#")
    for pid, definition in store.registry.properties.items():
        store.graph.add((node(pid), RDF.type, node("ScientificProperty")))
        store.graph.add((node(pid), RDFS.label, Literal((definition.aliases or [pid])[0])))
        store.graph.add((node(pid), fs.dimension, Literal(definition.dimension)))
        if definition.canonical_unit:
            store.graph.add((node(pid), fs.canonicalUnit, Literal(definition.canonical_unit)))
    return store


def register_source(registry, sid, path, title, url, kind, doi=None):
    checksum = digest(path)
    registry.add_source(
        {
            "source_id": sid,
            "source_type": kind,
            "nasa_id": sid,
            "title": title,
            "doi": doi,
            "url": url,
            "filename": str(path.resolve().relative_to(registry.evidence_root)),
            "sha256": checksum,
            "mime_type": "application/pdf"
            if path.suffix == ".pdf"
            else "application/json"
            if path.suffix == ".json"
            else "text/csv",
            "status": "fetched",
        }
    )
    registry.add_document(sid, sid, title)
    return checksum


def passage(registry, sid, path, checksum, locator, text, page=None):
    key = hashlib.sha256(
        (sid + checksum + json.dumps(locator, sort_keys=True)).encode()
    ).hexdigest()[:24]
    eid = "E-hackathon-" + key
    registry.add_passage(
        {
            "evidence_id": eid,
            "document_id": sid,
            "page": page,
            "section": locator.get("kind"),
            "text": text,
            "start_offset": None,
            "end_offset": None,
            "raw_file": str(path.resolve().relative_to(registry.evidence_root)),
            "checksum": checksum,
        }
    )
    registry.add_evidence_location(eid, locator)
    return eid


def import_table(store, evidence, root, path, meta):
    from nasa_fire_ai.ingestion.psi_scientific import import_fields, import_record, mappings

    accession = meta["accession"]
    sid = accession.lower()
    original_headers, rows, cell_metadata = table_cells(path, root)
    headers = [x.strip() for x in original_headers]
    checksum = register_source(
        evidence,
        sid,
        path,
        meta["title"],
        psi_landing_url(accession),
        "NASA PSI publication figure catalogue"
        if mappings(root).get(accession, {}).get("record_class") == "PublicationFigureReference"
        else "NASA PSI",
        meta["doi"],
    )
    counts = Counter()
    seen = Counter()
    for ordinal, cells in enumerate(rows, 2):
        if not any(cells):
            continue
        row = dict(zip(headers, cells, strict=False))
        eid = passage(
            evidence,
            sid,
            path,
            checksum,
            {
                "kind": "table_row",
                "row_ordinal": ordinal,
                "encoding": cell_metadata["encoding"],
            },
            " | ".join(
                f"{header}: {cell}"
                for header, cell in zip(original_headers, cells, strict=False)
                if cell.strip()
            ),
        )
        if len(cells) != len(headers):
            counts["malformed_rows"] += 1
            continue
        register_cells(evidence, eid, cell_metadata, ordinal, original_headers, cells)
        if "Investigation" not in store.classes(sid):
            store.add_entity(
                sid, "Investigation", [eid], [sid], {"id": sid, "title": meta["title"]}
            )
        if accession not in TABLES:
            if accession in mappings(root):
                import_record(store, evidence, root, accession, row, headers, eid, ordinal, counts)
            else:
                counts["documentary_rows"] += 1
            continue
        id_header, material_header, mapping = TABLES[accession]
        label = row.get(id_header, "").strip()
        # Camera/calibration descriptions are not samples or runs.
        if (
            not label
            or (accession in {"PSI-98", "PSI-100"} and not re.fullmatch(r"S\d+", label))
            or (accession == "PSI-99" and not re.fullmatch(r"\d+-\d+", label))
        ):
            counts["non_experimental_rows"] += 1
            from nasa_fire_ai.ingestion.psi_scientific import import_auxiliary_record

            if not import_auxiliary_record(
                store, evidence, root, accession, row, headers, eid, ordinal, counts
            ):
                raise ValueError(f"Unmapped auxiliary record: {accession} row {ordinal}")
            continue
        seen[label] += 1
        subject = sid + "-" + label + (f"-occurrence-{seen[label]}" if seen[label] > 1 else "")
        cls = "Sample" if accession == "PSI-102" else "ExperimentalRun"
        store.add_entity(
            subject,
            cls,
            [eid],
            [sid],
            {
                "id": subject,
                "reported_identifier": label,
                "reported_material_description": row.get(material_header),
                "modality": "reported_table_record",
                "identity_scope": "source_row; repeated run labels are not reconciled",
            },
        )
        store.add_relation(subject, "belongsToInvestigation", sid, [eid])
        from nasa_fire_ai.ingestion.psi_scientific import material_description

        material_description(
            store, subject, row.get(material_header, ""), material_header, eid, sid
        )
        if cls == "ExperimentalRun":
            store.add_relation(sid, "hasRun", subject, [eid])
            sample = subject + "-sample"
            store.add_entity(
                sample,
                "Sample",
                [eid],
                [sid],
                {
                    "id": sample,
                    "reported_material_description": row.get(material_header),
                    "reported_sample_identifier": row.get("Sample #"),
                    "identity_scope": "run_local_description; physical identity not reconciled",
                },
            )
            store.add_relation(subject, "usesSample", sample, [eid])
        else:
            sample = subject
        materials = {
            key: value["aliases"]
            for key, value in store.registry.entity_mentions.items()
            if value["relation"] == "hasMaterial"
        }
        material = normalize_mention(row.get(material_header, ""), materials)["identity"]
        if re.search(r"[&+]|\b(?:and|or)\b", row.get(material_header, ""), re.IGNORECASE):
            # A component mention does not establish a pure-material identity.
            material = None
        if material:
            store.add_entity(material, "Material", [eid], [sid])
            store.add_relation(subject, "hasMaterial", material, [eid])
            store.add_relation(sample, "madeOf", material, [eid])
        for header, (pid, unit, context) in mapping.items():
            raw = row.get(header, "")
            if not raw.strip():
                counts["missing_values"] += 1
                continue
            try:
                if pid == "FlowDirection":
                    value = GenericValue(reported_value=raw.strip(), raw_expression=raw)
                else:
                    # Accept a scalar, explicit range or approximation only; prose stays documentary.
                    if not re.fullmatch(r"[~\s\d.+eE–\-]+(?:cm/s|mmhg|mm|s|%)?", raw):
                        raise ValueError("non scalar source cell")
                    expression = (
                        raw if re.search(r"(?:cm/s|mmhg|mm|s|%)$", raw) else raw + " " + unit
                    )
                    _, value = parse_expression(expression, "numeric", {})
                    value.raw_expression = raw
                    value.reported_unit = unit
                    if context == "approximate":
                        value.approximate = True
                qualifiers = {
                    "modality": "reported_measurement"
                    if pid in {"source:burn_time", "source:visible_flame_extinction_diameter"}
                    else "reported_condition",
                    "scientific_role": "reported_duration"
                    if pid == "source:burn_time"
                    else "reported_extinction_diameter"
                    if pid == "source:visible_flame_extinction_diameter"
                    else "initial_specimen_characteristic"
                    if pid == "source:initial_droplet_diameter"
                    else "reported_condition",
                    "source_header": header,
                    "limitations": "A reported duration or diameter does not establish flame spread or a safety recommendation",
                    "context": context or "reported",
                    "original_value": raw,
                    "original_unit": unit or "",
                    "qc_flags": None,
                    "qc_status": "Original cell verified; team QC not applied",
                }
                if accession == "PSI-99" and "(Note 1)" in header:
                    # The source explicitly labels this column as derived from CO2.
                    qualifiers["modality"] = "derived"
                    qualifiers["source_note"] = "Note 1"
                rid = subject + "-value-" + str(headers.index(header))
                store.add_value(
                    rid,
                    subject,
                    pid,
                    value,
                    [eid],
                    qualifiers,
                    class_id="Measurement"
                    if qualifiers["modality"] == "reported_measurement"
                    else CONDITION_CLASSES.get(pid, "ExperimentalCondition"),
                )
                store.add_relation(
                    subject,
                    "hasMeasurement"
                    if qualifiers["modality"] == "reported_measurement"
                    else "hasCondition",
                    rid,
                    [eid],
                )
                evidence.db.execute(
                    "CREATE TABLE IF NOT EXISTS value_cells (value_id TEXT PRIMARY KEY, evidence_id TEXT, column_ordinal INTEGER)"
                )
                evidence.db.execute(
                    "INSERT INTO value_cells VALUES (?,?,?)", (rid, eid, headers.index(header) + 1)
                )
                counts["values"] += 1
            except (ValueError, TypeError):
                # Preserve qualitative/ambiguous entries from prior numeric adapters
                # without asserting a numeric quantity or measurement role.
                counts["unparsed_values"] += 1
                rid = subject + "-literal-" + str(headers.index(header))
                store.add_value(
                    rid,
                    subject,
                    "source:unparsed_quantity",
                    GenericValue(reported_value=raw, raw_expression=raw),
                    [eid],
                    {
                        "source_header": header,
                        "original_value": raw,
                        "original_unit": unit or "",
                        "intended_property": pid,
                        "modality": "unresolved_source_value",
                        "scientific_role": "original_literal_not_numeric_measurement",
                        "verification_status": "EXACT_CELL_SEMANTICS_UNRESOLVED",
                    },
                    class_id="ReportedField",
                )
                store.add_relation(subject, "hasRecordedField", rid, [eid])
                evidence.db.execute(
                    "CREATE TABLE IF NOT EXISTS value_cells (value_id TEXT PRIMARY KEY, evidence_id TEXT, column_ordinal INTEGER)"
                )
                evidence.db.execute(
                    "INSERT INTO value_cells VALUES (?,?,?)", (rid, eid, headers.index(header) + 1)
                )
        import_fields(store, evidence, root, accession, subject, row, headers, eid, counts)
        counts[cls] += 1
    return dict(counts)


def import_processed_records(evidence, root, team):
    """Index team-normalized rows as discovery only; do not assert RDF facts.

    Original PSI cells can disagree with normalized values or their units. The
    family tables retain source-line and QC lineage, but are never a substitute
    for original cells in the native scientific graph.
    """
    sources = []
    for family in ("solids", "droplets", "gas_flames", "aerosols", "sessions"):
        path = team / "clean" / f"{family}.csv"
        sid = f"team-processed-{family}"
        checksum = digest(path)
        evidence.add_source(
            {
                "source_id": sid,
                "source_type": "team processed PSI table; provisional",
                "nasa_id": None,
                "title": f"Team processed {family} records",
                "doi": None,
                "url": None,
                "filename": str(path.relative_to(root)),
                "sha256": checksum,
                "mime_type": "text/csv",
                "status": "PROVISIONAL_PROCESSED",
            }
        )
        evidence.add_document(sid, sid, f"Team processed {family} records")
        counts = Counter()
        with path.open(newline="") as stream:
            for ordinal, row in enumerate(csv.DictReader(stream), 2):
                accession = row.get("accession") or ""
                qc = row.get("qc_flags") or ""
                excluded = (row.get("excluded") or "").lower() in {"1", "true", "yes"}
                status = "excluded" if excluded else "qc_flagged" if qc else "traceable_processed"
                text = (
                    "PROVISIONAL TEAM-PROCESSED RECORD; not a NASA-verified measurement. "
                    + json.dumps(row, ensure_ascii=False, sort_keys=True)
                )
                passage(
                    evidence,
                    sid,
                    path,
                    checksum,
                    {
                        "kind": "processed_table_row",
                        "row_ordinal": ordinal,
                        "accession": accession,
                        "source_file_claim": row.get("source_file"),
                        "source_line_claim": row.get("source_line"),
                        "qc_status": status,
                        "qc_flags": qc,
                    },
                    text,
                )
                counts[status] += 1
        sources.append(
            {
                "source_id": sid,
                "depth": "P",
                "scope": "processed_record_discovery_only",
                "counts": dict(counts),
            }
        )
    return sources


def build_snapshot(root: Path, output: Path):
    """Build a content addressed, reproducible snapshot; reject changed existing bytes."""
    root = root.resolve()
    output = output.resolve()
    team = root / "data/raw/hackathon-team/data"
    campaigns = {r["accession"]: r for r in csv.DictReader((team / "clean/campaigns.csv").open())}
    # Use official cached bytes, not the team's normalized numeric values.
    table_receipt = root / "artifacts/hackathon/official_tables.json"
    verified_tables = json.loads(table_receipt.read_text())
    expansion_receipt = root / "artifacts/hackathon/official_tables_expansion_20261109.json"
    if expansion_receipt.exists():
        verified_tables.extend(json.loads(expansion_receipt.read_text()))
    supplementary = root / "artifacts/hackathon/supplementary_tables_20261109.json"
    if supplementary.exists():
        verified_tables.extend(json.loads(supplementary.read_text()))
    tables = []
    for row in verified_tables:
        path = root / row["path"]
        if digest(path) != row["sha256"]:
            raise ValueError("Official table checksum mismatch: " + row["source_id"])
        tables.append(path)
    if not tables:
        raise ValueError("No official experimental tables; acquire the bounded corpus first")
    documents = []
    for row in json.loads((root / "data/raw/manifest.json").read_text()):
        path = root / "data/raw" / (row.get("filename") or "")
        if path.is_file() and path.suffix == ".pdf" and digest(path) == row.get("sha256"):
            documents.append((path, row))
    standard_receipt = root / "artifacts/hackathon/standard.json"
    standard = json.loads(standard_receipt.read_text())
    standard_path = root / standard["path"]
    if digest(standard_path) != standard["sha256"]:
        raise ValueError("Standard checksum mismatch")
    documents.append((standard_path, {**standard, "canonical_url": standard["url"]}))
    documentary_receipt = root / "artifacts/hackathon/documentary_expansion_20261109.json"
    completion_receipt = root / "artifacts/hackathon/documentary_completion_20261110.json"
    semantic_receipt = root / "artifacts/hackathon/documentary_semantic_completion_20261112.json"
    for receipt in (documentary_receipt, completion_receipt, semantic_receipt):
        if not receipt.exists():
            continue
        for entry in json.loads(receipt.read_text()):
            path = root / entry["path"]
            if digest(path) != entry["sha256"]:
                raise ValueError("Documentary source checksum mismatch")
            documents.append((path, entry))
    metadata_paths = sorted((root / "data/raw/hackathon-psi").glob("PSI-*_metadata.json"))
    inputs = {
        str(p.relative_to(root)): digest(p)
        for p in tables
        + [x[0] for x in documents]
        + metadata_paths
        + [
            table_receipt,
            *([supplementary] if supplementary.exists() else []),
            *([documentary_receipt] if documentary_receipt.exists() else []),
            *([completion_receipt] if completion_receipt.exists() else []),
            *([semantic_receipt] if semantic_receipt.exists() else []),
            *([expansion_receipt] if expansion_receipt.exists() else []),
            standard_receipt,
            team / "clean/campaigns.csv",
            *[
                team / "clean" / f"{family}.csv"
                for family in ("solids", "droplets", "gas_flames", "aerosols", "sessions")
            ],
            root / "domain/semantic_registry.yaml",
            root / "domain/query_language_v2.yaml",
            root / "ontology/fire_safety.ttl",
            root / "domain/source_field_accessors.yaml",
            root / "domain/psi_table_mappings.yaml",
            root / "domain/psi_auxiliary_rows.yaml",
            root / "domain/psi_report_assertions.yaml",
            root / "ontology/psi_science.ttl",
            root / "ontology/psi_shapes.ttl",
            root / "src/nasa_fire_ai/ingestion/psi_scientific.py",
            root / "src/nasa_fire_ai/normalization/units.py",
            root / "src/nasa_fire_ai/query/v2.py",
            root / "src/nasa_fire_ai/query/native.py",
            root / "src/nasa_fire_ai/evidence/registry.py",
            root / "src/nasa_fire_ai/query/native_interpreter.py",
            root / "src/nasa_fire_ai/query/numeric_mentions.py",
            root / "src/nasa_fire_ai/ingestion/knowledge.py",
            root / "src/nasa_fire_ai/ingestion/semantic.py",
            root / "src/nasa_fire_ai/ingestion/structured_provenance.py",
            root / "src/nasa_fire_ai/ingestion/hackathon.py",
        ]
    }
    snapshot_id = hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest()
    if output.exists():
        manifest = json.loads((output / "manifest.json").read_text())
        if manifest["snapshot_id"] != snapshot_id:
            raise ValueError("Snapshot exists with different inputs; select a new directory")
        verify_snapshot(output, root)
        return manifest
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".snapshot-", dir=output.parent))
    evidence = EvidenceRegistry(temporary / "evidence.sqlite", evidence_root=root)
    store = make_store(root)
    sources = []
    try:
        for path in tables:
            accession = path.name.split("_")[0]
            meta = campaigns[accession]
            counts = import_table(store, evidence, root, path, meta)
            sources.append(
                {
                    "source_id": accession.lower(),
                    "depth": "B" if accession == "PSI-142" else "A",
                    "scope": "specimen"
                    if accession == "PSI-102"
                    else "run"
                    if accession in TABLES
                    else "source_record",
                    "counts": counts,
                }
            )
        for path, row in documents:
            sid = row["source_id"]
            checksum = register_source(
                evidence,
                sid,
                path,
                row.get("title", sid),
                row["canonical_url"],
                row["source_type"],
                row.get("doi"),
            )
            with pymupdf.open(path) as document:
                for index, page in enumerate(document, 1):
                    text = page.get_text()
                    if not text.strip():
                        continue
                    eid = passage(
                        evidence,
                        sid,
                        path,
                        checksum,
                        {"kind": "document", "physical_pdf_page": index},
                        text,
                        page=index,
                    )
                    store.add_entity(
                        sid + "-page-" + str(index),
                        "Document",
                        [eid],
                        [sid],
                        {"id": sid + "-page-" + str(index), "title": row.get("title", sid)},
                    )
            sources.append({"source_id": sid, "depth": "B", "scope": "document"})
        from nasa_fire_ai.ingestion.psi_scientific import import_documentation

        for path in metadata_paths:
            sources.extend(import_documentation(store, evidence, path, passage, register_source))
        from nasa_fire_ai.ingestion.psi_scientific import import_report_assertions

        import_report_assertions(store, evidence, root)
        sources.extend(import_processed_records(evidence, root, team))
        # Catalogues remain C, including publications; no inferred experiment joins.
        catalog = team / "clean/campaigns.csv"
        checksum = digest(catalog)
        for accession, row in campaigns.items():
            sid = "catalog-" + accession.lower()
            register_source(
                evidence,
                sid,
                catalog,
                row["title"],
                psi_landing_url(accession),
                "team PSI catalogue",
                row["doi"],
            )
            passage(
                evidence,
                sid,
                catalog,
                checksum,
                {"kind": "catalog", "accession": accession},
                json.dumps(row),
            )
            sources.append({"source_id": sid, "depth": "C", "scope": "catalog"})
        evidence.db.close()
        # N-Triples is also valid Turtle. Sort complete triples for byte-stable
        # serialization across processes and hash seeds (this graph has no blanks).
        triples = store.graph.serialize(format="nt").splitlines()
        (temporary / "graph.ttl").write_text("\n".join(sorted(triples)) + "\n")
        manifest = {
            "version": VERSION,
            "evidence_path_contract": "root-relative-v1",
            "quantity_role_contract": "reported-table-roles-v2",
            "snapshot_id": snapshot_id,
            "inputs": inputs,
            "sources": sources,
            "depth_counts": dict(Counter(s["depth"] for s in sources)),
            "subjects": dict(Counter(c for s in store.entities() for c in store.classes(s))),
            "rdf_triples": len(store.graph),
            "artifacts": {n: digest(temporary / n) for n in ["evidence.sqlite", "graph.ttl"]},
            "limitations": [
                "No gravity inherited from campaign or document headings",
                "Table roles preserve conditions, reported duration and extinction diameter; no inferred flame spread",
                "FLEX-2 has configuration-summary scope; no fabricated runs",
                "Curated ontology extension: ontology/psi_science.ttl",
                "Run and sample counts describe records, not independently verified distinct physical subjects",
                "Task Book not ingested; ACME day summaries retain session scope",
                "Team processed rows are discovery-only; their normalized values and units are not canonical observations",
            ],
        }
        (temporary / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
        temporary.rename(output)
        return manifest
    except BaseException:
        evidence.db.close()
        shutil.rmtree(temporary)
        raise


def verify_snapshot(output, root):
    manifest = json.loads((output / "manifest.json").read_text())
    for name, expected in manifest["artifacts"].items():
        if digest(output / name) != expected:
            raise ValueError("Snapshot artifact checksum mismatch: " + name)
    for name, expected in manifest["inputs"].items():
        if name.startswith("src/nasa_fire_ai/") and manifest.get("version") != VERSION:
            # Historical snapshots retain their own code digest in the
            # manifest. Runtime compatibility checks original bytes and
            # artifacts, while the old builder source is no longer current.
            continue
        if digest(root / name) != expected:
            raise ValueError("Snapshot input checksum mismatch: " + name)
    return manifest
