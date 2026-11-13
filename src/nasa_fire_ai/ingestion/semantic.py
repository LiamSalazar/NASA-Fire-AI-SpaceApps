"""Generic canonical ingestion and explicit one-time legacy projection.

Only this projection module knows legacy field names. Native ingestion takes generic
records; unknown column semantics enter the persistent review queue.
"""

import json
import os
from pathlib import Path

import yaml

from nasa_fire_ai.ingestion.generic import profile_table, propose_table_role, resolve_column

ONTOLOGY_PREFIX = "https://example.org/nasa-fire-safety#"
_ONTOLOGY = {}


def approved_ontology(root):
    """The approved ontology's classes, object and datatype properties, parsed once.

    The one reading of ``ontology/fire_safety.ttl`` that extraction and curation
    share: classes with their sorted ``rdfs:subClassOf`` parents, definition and
    label; object properties; datatype properties with definition and ranges. Read
    again only when the file changes. Callers must not modify what it returns.
    """
    from rdflib import OWL, RDF, RDFS, Graph

    path = Path(root) / "ontology/fire_safety.ttl"
    stat = path.stat()
    key = (str(path.resolve()), stat.st_mtime_ns, stat.st_size)
    if key not in _ONTOLOGY:
        graph = Graph().parse(path)

        def short(node):
            return str(node).removeprefix(ONTOLOGY_PREFIX)

        _ONTOLOGY.clear()
        _ONTOLOGY[key] = {
            "classes": {
                short(s): {
                    "parents": sorted(short(p) for p in graph.objects(s, RDFS.subClassOf)),
                    "definition": str(graph.value(s, RDFS.comment) or ""),
                    "label": str(graph.value(s, RDFS.label) or short(s)),
                }
                for s in graph.subjects(RDF.type, OWL.Class)
            },
            "object_properties": sorted(
                short(s) for s in graph.subjects(RDF.type, OWL.ObjectProperty)
            ),
            "datatype_properties": {
                short(s): {
                    "definition": str(graph.value(s, RDFS.comment) or ""),
                    "ranges": sorted(str(v) for v in graph.objects(s, RDFS.range)),
                }
                for s in graph.subjects(RDF.type, OWL.DatatypeProperty)
            },
        }
    return _ONTOLOGY[key]


def approved_parents(class_id, class_metadata, ontology=None):
    """The approved parents of a class: the registry's own ``parent``, the ontology
    ``rdfs:subClassOf`` parents carried in its metadata, and, when given, those of
    the approved ontology itself. A parent a model only proposed is never here."""
    meta = class_metadata.get(class_id, {})
    found = set(meta.get("approved_ontology_parents") or [])
    if meta.get("parent"):
        found.add(meta["parent"])
    if ontology:
        found.update(ontology["classes"].get(class_id, {}).get("parents", []))
    return sorted(found)


def class_ancestors(class_id, class_metadata, ontology=None):
    """A class and every approved ancestor, transitively; cycle-safe."""
    seen, pending = set(), [class_id]
    while pending:
        current = pending.pop()
        if not current or current in seen:
            continue
        seen.add(current)
        pending.extend(approved_parents(current, class_metadata, ontology))
    return seen


from nasa_fire_ai.query.native import SemanticGraph
from nasa_fire_ai.query.v2 import (
    GenericValue,
    PropertyDefinition,
    RelationDefinition,
    SemanticRegistry,
)


def load_semantic_registry(path: Path) -> SemanticRegistry:
    data = yaml.safe_load(path.read_text())
    registry = SemanticRegistry(
        [PropertyDefinition(**row) for row in data["properties"]],
        target_classes={key for key, meta in data["classes"].items() if meta.get("target")},
        information_classes={
            key for key, meta in data["classes"].items() if meta.get("information")
        },
        relations=[RelationDefinition(**row) for row in data["relations"]],
    )
    registry.class_metadata = data["classes"]
    registry.selection_policy = data.get("selection_policy", {})
    registry.entities.update(data.get("entities", []))
    language_path = path.with_name("query_language_v2.yaml")
    if language_path.exists():
        language = yaml.safe_load(language_path.read_text())
        registry.entity_mentions = language.get("entity_mentions", {})
        # The words that name each target class ("Sample": sample, specimen, ...).
        registry.target_mentions = language.get("target_mentions", {})
    return registry


def project_legacy(root: Path, evidence_registry) -> SemanticGraph:
    """Deterministic additive projection. Never writes canonical or raw inputs."""
    registry = load_semantic_registry(root / "domain/semantic_registry.yaml")
    store = SemanticGraph(registry)
    config = yaml.safe_load((root / "domain/legacy_semantic_projection.yaml").read_text())
    records = json.loads((root / "data/canonical/records.json").read_text())
    store.legacy_statement_staging = []
    for record in records:
        cls = config["record_classes"].get(record["type"])
        if record["type"] == "SafetyStatementRecord":
            cls = config["statement_classes"][record["statement_type"]]
        elif record["type"] in config["statement_classes"]:
            cls = config["statement_classes"][record["type"]]
        if cls is None:
            continue
        meta = registry.class_metadata.get(cls, {})
        if (
            meta.get("bundle_field")
            and not meta.get("documentary")
            and record["type"] not in config.get("reviewed_epistemic_record_types", [])
        ):
            store.legacy_statement_staging.append(
                {
                    "original_record": record,
                    "reason": "legacy epistemic classification has no reviewed publication authority",
                }
            )
            continue
        refs = record["evidence_refs"]
        store.add_entity(
            record.get("id", record.get("statement_id")),
            cls,
            [r["evidence_id"] for r in refs],
            [r["source_id"] for r in refs],
            record,
        )
    project_canonical_conditions(store, records, config, evidence_registry)
    # Every registered document remains queryable as a document independently of runs.
    for row in evidence_registry.db.execute(
        "SELECT d.document_id,d.source_id,d.title FROM documents d LEFT JOIN sources s USING(source_id) WHERE COALESCE(s.status,'') NOT IN ('SUPERSEDED_DOCUMENT','ROLLED_BACK_DOCUMENT')"
    ):
        refs = [
            r[0]
            for r in evidence_registry.db.execute(
                "SELECT evidence_id FROM passages WHERE document_id=?", (row[0],)
            )
        ]
        if refs:
            store.add_entity(
                row[0],
                "Document",
                refs,
                [row[1]],
                {"id": row[0], "title": row[2], "source_id": row[1]},
            )
            store.add_entity(row[0], "Publication", refs, [row[1]])
    from nasa_fire_ai.query.hierarchy import load_taxonomy

    taxonomy_file = root / "domain/semantic_taxonomy.yaml"
    store.taxonomy_proposals = []
    store.taxonomy_load_errors = []
    if taxonomy_file.exists():
        try:
            load_taxonomy(store, yaml.safe_load(taxonomy_file.read_text()))
        except (yaml.YAMLError, ValueError, TypeError) as exc:
            store.taxonomy_load_errors.append({"reason": type(exc).__name__})
    if (
        os.getenv("ONTOLOGY_GRAPH_ENRICHMENT_ENABLED", "false").lower() == "true"
        or os.getenv("SCIENTIFIC_CONTEXT_RESOLUTION_ENABLED", "false").lower() == "true"
    ):
        from nasa_fire_ai.ingestion.knowledge import enrich_native

        language = yaml.safe_load((root / "domain/query_language_v2.yaml").read_text())
        mentions = {
            key: value.get("aliases", [key])
            for key, value in language.get("entity_mentions", {}).items()
            if value.get("relation") == "hasMaterial"
        }
        enrich_native(
            store, records, evidence_registry, root / "ontology/fire_safety.ttl", mentions
        )
        if os.getenv("SOURCE_KNOWLEDGE_ENRICHMENT_ENABLED", "false").lower() == "true":
            from nasa_fire_ai.ingestion.enrichment import enrich_source_fields

            enrich_source_fields(store, records, evidence_registry, root, mentions)
    if os.getenv("PSI_STRUCTURED_PUBLICATION_ENABLED", "false").lower() == "true":
        from nasa_fire_ai.ingestion.validated_psi import project_validated_psi

        project_validated_psi(store, evidence_registry, root)
    if os.getenv("FLEX_SOURCE_CORRECTIONS_ENABLED", "false").lower() == "true":
        from nasa_fire_ai.ingestion.source_corrections import project_source_corrections

        project_source_corrections(store, evidence_registry, root, records)
    if os.getenv("SCIENTIFIC_CONTEXT_RESOLUTION_ENABLED", "false").lower() == "true":
        from nasa_fire_ai.query.contextual import attach_context_layer

        attach_context_layer(
            store,
            evidence_registry,
            os.getenv(
                "SCIENTIFIC_CONTEXT_INDEX", str(root / "data/index/scientific_context_v2.json")
            ),
        )
    if os.getenv("SOURCE_KNOWLEDGE_ENRICHMENT_ENABLED", "false").lower() == "true":
        from nasa_fire_ai.ingestion.scientific_proposals import project_eligible, project_staged

        project_eligible(store, evidence_registry, root)
        project_staged(store, evidence_registry)
    from nasa_fire_ai.services.curation import project_active

    project_active(store, evidence_registry, root)
    return store


def project_canonical_conditions(store, records, config, evidence_registry):
    """All canonical runs, using condition links rather than the two-run view.

    Configuration resolves only existing reviewed semantics. Unmapped fields and
    unsupported units remain provenance-complete candidates, not new vocabulary.
    A reported condition is not asserted to be an observed measurement.
    """
    indexed = {r.get("id", r.get("statement_id")): r for r in records}
    report = {
        key: 0
        for key in (
            "total_runs",
            "eligible_runs",
            "projected_runs",
            "runs_without_values",
            "runs_with_unresolved",
            "conditions",
            "measurements",
            "relations",
            "invalid_units",
            "missing_original_values",
            "broken_evidence_refs",
        )
    }
    staged = []
    for run in records:
        if run["type"] != "ExperimentalRunRecord":
            continue
        report["total_runs"] += 1
        subject = run["id"]
        refs = [r["evidence_id"] for r in run["evidence_refs"]]
        if not refs or any(evidence_registry.resolve(e) is None for e in refs):
            report["broken_evidence_refs"] += 1
            continue
        report["eligible_runs"] += 1
        report["projected_runs"] += 1
        if subject not in store.registry.entities:
            store.add_entity(
                subject,
                "ExperimentalRun",
                refs,
                [r["source_id"] for r in run["evidence_refs"]],
                run,
            )
        sample = indexed.get(run.get("sample_id"), {})
        for obj, relation in (
            (run.get("investigation_id"), "belongsToInvestigation"),
            (sample.get("material"), "hasMaterial"),
        ):
            if obj:
                store.registry.entities.add(obj)
                store.add_relation(subject, relation, obj, refs)
                report["relations"] += 1
        count, unresolved = 0, False
        for cid in run.get("condition_ids", []):
            condition = indexed.get(cid)
            if not condition:
                unresolved = True
                continue
            kind = condition["kind"]
            crefs = [r["evidence_id"] for r in condition["evidence_refs"]]
            candidate = {
                "candidate_id": f"projection:{cid}",
                "candidate_type": "VALUE",
                "raw_label": kind,
                "source_id": condition["evidence_refs"][0]["source_id"],
                "evidence_id": crefs[0] if crefs else None,
                "resolution_status": "UNKNOWN",
                "provenance": condition,
                "subject": subject,
            }
            if not crefs or any(evidence_registry.resolve(e) is None for e in crefs):
                candidate["reason"] = "broken_evidence_reference"
                report["broken_evidence_refs"] += 1
            elif (
                kind in config.get("condition_relations", {})
                and condition.get("reported_value") is not None
            ):
                obj = str(condition["reported_value"])
                if (
                    os.getenv("NATIVE_SOURCE_CONTEXT_VALIDATION_ENABLED", "false").lower() == "true"
                    or os.getenv("SCIENTIFIC_CONTEXT_RESOLUTION_ENABLED", "false").lower() == "true"
                ) and config["condition_relations"][kind] == "hasGravityCondition":
                    explicit = any(
                        cell["original_header"].strip().lower() in {"gravity", "gravity condition"}
                        and cell["original_value"].strip().lower() == obj.lower()
                        for e in crefs
                        for cell in evidence_registry.resolve(e).get("source_cells", [])
                    )
                    if not explicit:
                        candidate["reason"] = (
                            "gravity declaration lacks supporting source span or validated execution context"
                        )
                        staged.append(candidate)
                        unresolved = True
                        continue
                store.registry.entities.add(obj)
                store.add_relation(subject, config["condition_relations"][kind], obj, crefs)
                report["relations"] += 1
                continue
            elif meta := config.get("condition_properties", {}).get(kind):
                try:
                    value = GenericValue(
                        reported_value=condition.get("reported_value"),
                        reported_unit=condition.get("reported_unit"),
                        canonical_value=condition.get("canonical_value"),
                        canonical_unit=condition.get("canonical_unit"),
                        lower=condition.get("reported_lower_value"),
                        upper=condition.get("reported_upper_value"),
                        approximate=condition.get("is_approximate", False),
                    )
                    if store.registry.properties[
                        meta["property_id"]
                    ].datatype == "numeric" and isinstance(value.reported_value, str):
                        from nasa_fire_ai.query.native_interpreter import parse_expression

                        _, value = parse_expression(
                            value.reported_value + " " + (value.reported_unit or ""), "numeric", {}
                        )
                    if value.reported_value is None and value.lower is None:
                        report["missing_original_values"] += 1
                        raise ValueError("no original value")
                    store.add_value(
                        cid,
                        subject,
                        meta["property_id"],
                        value,
                        crefs,
                        {
                            "origin": "canonical_condition_projection",
                            "role": "reported_condition",
                            "context": meta["context"],
                            "original_record": condition,
                        },
                        class_id="ExperimentalCondition",
                    )
                    count += 1
                    report["conditions"] += 1
                    continue
                except (ValueError, LookupError) as error:
                    candidate["reason"] = str(error)
                    report["invalid_units"] += 1
            else:
                candidate["reason"] = "no approved property mapping"
            staged.append(candidate)
            unresolved = True
        report["runs_without_values"] += count == 0
        report["runs_with_unresolved"] += unresolved
    report["unknown_fields_staged"] = len(staged)
    report["evidence_refs_retained"] = len(
        {r["evidence_id"] for x in records for r in x.get("evidence_refs", [])}
    )
    store.projection_report = report
    store.projection_staging = staged


def ingest_generic_table(
    rows, source_id, evidence_ids, store, evidence_registry, reviewed_role=None, role_authority=None
):
    """Authority comes only from the frozen registry; source IDs affect provenance only."""
    if len(rows) != len(evidence_ids):
        raise ValueError("one evidence reference is required per row")
    profiles = profile_table(rows)
    role = propose_table_role(profiles)
    if reviewed_role is not None:
        if not role_authority or reviewed_role not in store.registry.target_classes:
            raise ValueError(
                "canonical table role requires reviewed authority and registered class"
            )
        if any(evidence_registry.resolve(e) is None for e in evidence_ids):
            raise ValueError("canonical table role requires registered evidence")
    resolutions = [resolve_column(p, store.registry) for p in profiles]
    canonical_records = 0
    staging = []
    for profile, resolution in zip(profiles, resolutions, strict=True):
        if resolution.status != "CANONICAL":
            candidate = {
                "candidate_id": f"semantic:{source_id}:{profile.label}",
                "candidate_type": "PROPERTY",
                "raw_label": profile.label,
                "source_id": source_id,
                "evidence_id": evidence_ids[0] if evidence_ids else None,
                "resolution_status": "KNOWN_AMBIGUOUS"
                if resolution.status == "AMBIGUOUS"
                else "UNKNOWN",
                "provenance": {
                    "profiler": "generic-v1",
                    "column": profile.label,
                    "datatype": profile.datatype,
                    "unit": profile.raw_unit,
                },
            }
            evidence_registry.stage_semantic_candidate(candidate)
            staging.append(candidate)
    for i, (row, evidence_id) in enumerate(zip(rows, evidence_ids, strict=True)):
        subject = f"{source_id}:row:{i}"
        if reviewed_role is None:
            candidate = {
                "candidate_id": subject,
                "candidate_type": "ROW",
                "raw_label": subject,
                "source_id": source_id,
                "evidence_id": evidence_id,
                "resolution_status": "UNKNOWN",
                "provenance": {"row_index": i, "row": row, "table_role": role},
            }
            evidence_registry.stage_semantic_candidate(candidate)
            staging.append(candidate)
            continue
        store.add_entity(
            subject,
            reviewed_role,
            [evidence_id],
            [source_id],
            {"id": subject, "role_authority": role_authority, "reported_row": row},
        )
        for profile, resolution in zip(profiles, resolutions, strict=True):
            if resolution.status != "CANONICAL" or not str(row.get(profile.label, "")).strip():
                continue
            definition = store.registry.properties[resolution.property_id]
            raw = str(row[profile.label]).strip()
            try:
                value = GenericValue(
                    reported_value=float(raw) if definition.datatype == "numeric" else raw,
                    reported_unit=profile.raw_unit,
                    raw_expression=raw,
                )
                store.add_value(
                    f"{subject}:{profile.label}",
                    subject,
                    resolution.property_id,
                    value,
                    [evidence_id],
                    {"column": profile.label},
                )
                canonical_records += 1
            except ValueError:
                candidate = {
                    "candidate_id": f"value:{subject}:{profile.label}",
                    "candidate_type": "VALUE",
                    "raw_label": raw,
                    "source_id": source_id,
                    "evidence_id": evidence_id,
                    "resolution_status": "UNKNOWN",
                    "provenance": {"column": profile.label, "reason": "incompatible value/unit"},
                }
                evidence_registry.stage_semantic_candidate(candidate)
                staging.append(candidate)
    return {
        "rows": len(rows),
        "table_role": role
        if reviewed_role is None
        else {"canonical": True, "reviewed_role": reviewed_role, "authority": role_authority},
        "columns": len(profiles),
        "canonical_records": canonical_records,
        "canonical_mappings": sum(r.status == "CANONICAL" for r in resolutions),
        "staging_records": len(staging),
        "resolutions": [r.__dict__ for r in resolutions],
    }
