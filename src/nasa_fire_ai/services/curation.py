"""Versioned scientific review over the established EvidenceRegistry and native graph.

Draft JSON is an operational proposal, never an alternative scientific truth store.
Active versions project through the same SemanticGraph as historical canonical inputs.
All visibility changes (records, evidence, FTS and active pointer) commit in SQLite.
"""

from __future__ import annotations

import copy
import csv
import hashlib
import io
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import pymupdf
import yaml
from pyshacl import validate as shacl_validate
from rdflib import OWL, RDF, RDFS, Graph, Literal, Namespace

from nasa_fire_ai.ingestion.generic import profile_table, resolve_column
from nasa_fire_ai.ingestion.relation_contracts import RELATION_ENDPOINTS, object_class
from nasa_fire_ai.ingestion.scientific_facets import (
    facets,
    not_done_configuration,
    not_done_value,
    stated_modality,
)
from nasa_fire_ai.ingestion.scientific_proposals import normative_instruction
from nasa_fire_ai.ingestion.semantic import (
    approved_ontology,
    class_ancestors,
    load_semantic_registry,
)
from nasa_fire_ai.query.native import NS, SemanticGraph, node
from nasa_fire_ai.query.v2 import (
    GenericValue,
    PropertyConstraintV2,
    PropertyDefinition,
    RelationDefinition,
)


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def now():
    return datetime.now(UTC).isoformat()


def decode_table(data):
    """Preserve source bytes; legacy PSI spreadsheet exports use Windows-1252."""
    try:
        return data.decode("utf-8-sig"), "utf-8-sig"
    except UnicodeDecodeError:
        text = data.decode("cp1252")
        if text.encode("cp1252") != data:
            raise ValueError("Table encoding could not be verified without changing source bytes")
        return text, "cp1252"


def scientific_focus(query, store):
    """A reviewed investigation title identifies scope, not extra topic constraints."""
    for entity, metadata in getattr(store.registry, "entity_mentions", {}).items():
        if entity.startswith("research-") and metadata.get("relation") == "belongsToInvestigation":
            for alias in metadata.get("aliases", []):
                query = re.sub(
                    r"(?<!\w)" + re.escape(alias) + r"(?!\w)", " ", query, flags=re.IGNORECASE
                )
    return query


@dataclass(frozen=True)
class ReviewPolicy:
    approvers: frozenset[str] = field(default_factory=frozenset)
    development: bool = False
    public_enabled: bool = False


class CurationService:
    def __init__(self, root, registry, policy=None):
        self.root = Path(root)
        self.registry = registry
        self.policy = policy or ReviewPolicy()
        self.semantic = load_semantic_registry(self.root / "domain/semantic_registry.yaml")
        self.presentation = yaml.safe_load((self.root / "domain/incorporation.yaml").read_text())
        # Every registered role and its class. ``statement_roles`` also names table
        # columns whose cells are statements; ``profile_roles`` (criteria) are roles
        # only: a "Test criterion" column holds results, not criteria.
        self.epistemic_roles = {
            **self.presentation["statement_roles"],
            **self.presentation.get("profile_roles", {}),
        }
        registry.db.executescript("""
        CREATE TABLE IF NOT EXISTS research_packages(package_id TEXT, version INTEGER,
          digest TEXT UNIQUE, creator TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT,
          PRIMARY KEY(package_id,version));
        CREATE TABLE IF NOT EXISTS research_approvals(digest TEXT PRIMARY KEY, principal TEXT,
          approved_at TEXT, development INTEGER, receipt TEXT);
        CREATE TABLE IF NOT EXISTS research_active(package_id TEXT PRIMARY KEY, digest TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS research_publications(digest TEXT PRIMARY KEY, status TEXT,
          published_at TEXT, receipt TEXT);
        CREATE TABLE IF NOT EXISTS research_events(event_id INTEGER PRIMARY KEY, package_id TEXT,
          digest TEXT, kind TEXT, principal TEXT, receipt TEXT, created_at TEXT);
        """)
        registry.db.commit()
        active_store = SemanticGraph(self.semantic)
        project_active(active_store, registry, self.root)
        self.semantic = active_store.registry
        self.entity_classes = {e: active_store.classes(e) for e in active_store.entities()}

    def templates(self, package=None):
        """Registry determines scientific forms; SHACL supplies graph constraints."""
        ontology = Graph().parse(self.root / "ontology/fire_safety.ttl")
        shapes = Graph().parse(self.root / "ontology/semantic_shapes.ttl")
        sh = Namespace("http://www.w3.org/ns/shacl#")
        semantic = self.property_registry(package) if package else self.semantic
        return {
            "classes": semantic.class_metadata,
            "properties": [asdict(p) for p in semantic.properties.values()],
            "relations": [asdict(r) for r in semantic.relations.values()],
            "ontology_classes": sorted(str(s) for s in ontology.subjects(RDF.type, OWL.Class)),
            "constraints": [
                {
                    "shape": str(shape),
                    "path": str(shapes.value(prop, sh.path)),
                    "minimum": str(shapes.value(prop, sh.minCount) or ""),
                    "maximum": str(shapes.value(prop, sh.maxCount) or ""),
                }
                for shape, _, prop in shapes.triples((None, sh.property, None))
            ],
            "epistemic_roles": self.epistemic_roles,
        }

    def event(self, package, kind, principal, receipt):
        self.registry.db.execute(
            "INSERT INTO research_events(package_id,digest,kind,principal,receipt,created_at) VALUES (?,?,?,?,?,?)",
            (package["id"], digest(package), kind, principal, json.dumps(receipt), now()),
        )
        self.registry.db.commit()

    def save(self, package, principal):
        package = copy.deepcopy(package)
        package["contract_digest"] = self.contract_digest()
        previous = self.registry.db.execute(
            "SELECT digest,payload FROM research_packages WHERE package_id=? ORDER BY version DESC LIMIT 1",
            (package["id"],),
        ).fetchone()
        if previous:
            old = json.loads(previous["payload"])
            if {k: v for k, v in old.items() if k != "version"} == {
                k: v for k, v in package.items() if k != "version"
            }:
                return {"package": old, "digest": previous["digest"]}
        package["version"] = self.registry.db.execute(
            "SELECT COALESCE(MAX(version),0)+1 FROM research_packages WHERE package_id=?",
            (package["id"],),
        ).fetchone()[0]
        value = digest(package)
        self.registry.db.execute(
            "INSERT INTO research_packages VALUES (?,?,?,?,?,?)",
            (package["id"], package["version"], value, principal, json.dumps(package), now()),
        )
        self.registry.db.commit()
        return {"package": package, "digest": value}

    def contract_digest(self):
        return digest(
            {
                str(path): hashlib.sha256((self.root / path).read_bytes()).hexdigest()
                for path in (
                    "domain/semantic_registry.yaml",
                    "domain/incorporation.yaml",
                    "ontology/fire_safety.ttl",
                    "ontology/semantic_shapes.ttl",
                )
            }
        )

    def validate_originals(self, package):
        errors = []
        expected = {}
        for manifest in package["inputs"]:
            path = (self.root / manifest["stored_input"]).resolve()
            if (
                not path.is_relative_to((self.root / "data/submissions").resolve())
                or not path.is_file()
            ):
                errors.append("Submitted original is unavailable: " + manifest["name"])
                continue
            data = path.read_bytes()
            if (
                hashlib.sha256(data).hexdigest() != manifest["sha256"]
                or len(data) != manifest["bytes"]
            ):
                errors.append("Submitted original checksum changed: " + manifest["name"])
                continue
            suffix = path.suffix
            if suffix == ".pdf":
                with pymupdf.open(stream=data, filetype="pdf") as doc:
                    units = [(i + 1, p.get_text("text")) for i, p in enumerate(doc)]
            elif suffix in {".csv", ".tsv"}:
                table_text, encoding = decode_table(data)
                if manifest.get("encoding", encoding) != encoding:
                    errors.append("Source table encoding differs from preparation")
                rows = list(
                    csv.DictReader(
                        io.StringIO(table_text),
                        delimiter="\t" if suffix == ".tsv" else ",",
                    )
                )
                rows = [
                    {k.strip(): (v or "").strip() for k, v in row.items() if k is not None}
                    for row in rows
                ]
                units = [(i + 1, json.dumps(row, ensure_ascii=False)) for i, row in enumerate(rows)]
                sid = package["id"] + ":" + manifest["sha256"][:16]
                submitted_table = next((t for t in package["tables"] if t["id"] == sid), None)
                if not submitted_table or submitted_table["rows"] != rows:
                    errors.append("Experimental rows differ from the submitted original table")
            else:
                units = [(1, data.decode("utf-8-sig"))]
            sid = package["id"] + ":" + manifest["sha256"][:16]
            for ordinal, text in units:
                eid = "E-" + digest([sid, ordinal, text])[:24]
                expected[eid] = (
                    text,
                    manifest["sha256"],
                    sid,
                    sid + ":document",
                    ordinal,
                    {
                        "file": manifest["name"],
                        "row" if suffix in {".csv", ".tsv"} else "page": ordinal,
                    },
                )
        supplied = {
            e["evidence_id"]: (
                e["text"],
                e["checksum"],
                e["source_id"],
                e.get("document_id"),
                e.get("page"),
                e.get("locator"),
            )
            for e in package["evidence"]
        }
        if supplied != expected:
            errors.append(
                "Evidence differs from original submitted source units; regenerate extraction"
            )
        return errors

    def validate_attribution(self, package):
        """Reconstruct applicability from original cells, never corrected extraction.

        These ephemeral anchors are not persisted scientific claims. Unknown prose
        applicability requires the existing explicit scope decision, not model prose.
        """
        errors = []
        refs = {e["evidence_id"]: e for e in package["evidence"]}
        excluded = {e["subject"] for e in package["exclusions"]}
        semantic = self.property_registry(package)
        runs, values, statements = {}, {}, {}
        narrative_runs, narrative_statements = {}, {}
        if package.get("scientific_extraction"):
            from nasa_fire_ai.ingestion.document_extraction import (
                extraction_semantic,
                validate_output,
            )
            from nasa_fire_ai.ingestion.document_structure import structure

            extraction = package["scientific_extraction"]
            checked = validate_output(
                extraction["raw_proposals"],
                package,
                structure(package, self.root, extraction["processing"]["budget"]["segment_chars"]),
                extraction_semantic(self, package),
            )
            narrative_runs = {
                r["entity_id"]: r
                for r in checked["records"]
                if r["kind"] == "entities"
                and r["status"] == "SOURCE_SUPPORTED"
                and r["proposal"]["class_id"] == "ExperimentalRun"
            }
            narrative_statements = {
                r["id"]: r
                for r in checked["records"]
                if r["kind"] == "statements" and r["status"] == "SOURCE_SUPPORTED"
            }
        for manifest in package["inputs"]:
            path = self.root / manifest["stored_input"]
            if path.suffix not in {".csv", ".tsv"} or not path.is_file():
                continue
            data = path.read_bytes()
            if hashlib.sha256(data).hexdigest() != manifest["sha256"]:
                continue  # validate_originals supplies the blocking checksum error.
            text, _ = decode_table(data)
            rows = list(
                csv.DictReader(io.StringIO(text), delimiter="\t" if path.suffix == ".tsv" else ",")
            )
            rows = [
                {k.strip(): (v or "").strip() for k, v in r.items() if k is not None} for r in rows
            ]
            profiles = profile_table(rows)
            sid = package["id"] + ":" + manifest["sha256"][:16]
            for i, row in enumerate(rows):
                eid = "E-" + digest([sid, i + 1, json.dumps(row, ensure_ascii=False)])[:24]
                rid = sid + ":run:" + str(i)
                roles = {
                    role: row[p.label]
                    for p in profiles
                    for role, aliases in self.presentation["column_roles"].items()
                    if p.normalized_label in aliases and row[p.label]
                }
                runs[rid] = {"eid": eid, "roles": roles, "sid": sid}
                for p in profiles:
                    if not row[p.label]:
                        continue
                    role = self.presentation["statement_roles"].get(p.normalized_label)
                    if role:
                        if normative_instruction(row[p.label]):
                            # A procedural sentence under an "Observation" header
                            # still needs a normative or documentary interpretation.
                            role = self.presentation["statement_roles"]["requirement"]
                        statements[rid + ":statement:" + p.label] = {
                            "run": rid,
                            "text": row[p.label],
                            "role": role,
                            "eid": eid,
                        }
                    else:
                        values[rid + ":value:" + p.label] = {
                            "run": rid,
                            "expression": row[p.label],
                            "unit": p.raw_unit,
                            "header": p.label,
                            "eid": eid,
                            "property_id": resolve_column(p, semantic).property_id
                            or package["decisions"]
                            .get("column:" + sid + ":" + p.label, {})
                            .get("selection"),
                        }
        for entity in package["entities"]:
            anchor = runs.get(entity["id"])
            if (
                entity["class_id"] == "ExperimentalRun"
                and not anchor
                and entity["id"] not in excluded
                and not (
                    entity["id"] in narrative_runs
                    and entity["label"] == narrative_runs[entity["id"]]["proposal"]["label"]
                    and set(entity["evidence_ids"])
                    == {s["evidence_id"] for s in narrative_runs[entity["id"]]["support_spans"]}
                )
            ):
                errors.append(
                    "Scientific review required: experimental run lacks original table-row identity: "
                    + entity["id"]
                )
            if (
                anchor
                and entity["id"] not in excluded
                and (
                    anchor["eid"] not in entity["evidence_ids"]
                    or entity["label"] != anchor["roles"].get("run", entity["label"])
                )
            ):
                errors.append(
                    "Source row/run identity differs from original evidence: " + entity["id"]
                )
        for relation in package["relations"]:
            if relation["subject"] in excluded:
                continue
            anchor = runs.get(relation["subject"])
            dimension = {
                "hasGravityCondition": "gravity",
                "hasMaterial": "material",
                "belongsToExperimentFamily": "group",
                "belongsToInvestigation": "investigation",
            }.get(relation["relation"])
            if not dimension:
                continue
            if not anchor and relation["subject"] in statements:
                anchor = runs[statements[relation["subject"]]["run"]]
            if not anchor:
                errors.append(
                    "Scientific review required: relationship "
                    + dimension
                    + " needs original experimental applicability for "
                    + relation["subject"]
                )
                continue
            raw = anchor["roles"].get(dimension)
            expected = None
            if dimension == "investigation":
                expected = package["id"]
            elif dimension == "group" and raw:
                expected = anchor["sid"] + ":group:" + raw
            elif raw:
                expected = self.resolve_identity(raw, relation["relation"])
                if not expected:
                    selection = package["decisions"].get(dimension + ":" + raw, {}).get("selection")
                    if selection == "distinct" and dimension == "material":
                        expected = anchor["sid"] + ":material:" + digest(raw)[:12]
                    elif selection not in {None, "documentary"}:
                        expected = selection
            if expected:
                if relation["object"] != expected or anchor["eid"] not in relation["evidence_ids"]:
                    errors.append(
                        "Source row "
                        + dimension
                        + " attribution contradicts original evidence: "
                        + relation["subject"]
                    )
            elif dimension == "gravity" and not raw:
                # Broader documentary context is permitted only after an explicit
                # applicability decision; local source conditions take precedence.
                supported = any(
                    c["value"] == relation["object"]
                    and package["decisions"].get(c["id"], {}).get("selection") == "campaign"
                    and any(
                        e in refs
                        and c["text"] in refs[e]["text"]
                        and re.search(
                            r"\b" + re.escape(c["value"]) + r"\b", refs[e]["text"], re.IGNORECASE
                        )
                        for e in c["evidence_ids"]
                    )
                    for c in package.get("contexts", [])
                )
                if not supported:
                    errors.append(
                        "Scientific review required: identify source-backed gravity context and its applicability to "
                        + relation["subject"]
                    )
            else:
                errors.append(
                    "Scientific review required: resolve original source "
                    + dimension
                    + " identity for "
                    + relation["subject"]
                )
        for value in package["values"]:
            if value["id"] in excluded or value["subject"] in excluded:
                continue
            anchor = values.get(value["id"])
            if not anchor:
                errors.append(
                    "Scientific review required: quantity needs an identified original table cell: "
                    + value["id"]
                )
                continue
            original_unit = anchor["unit"]
            # Existing reviewed percent header contract retains the original unit.
            if original_unit is None and "percent" in anchor["header"].lower():
                original_unit = "%"
            v = value["value"]
            if value["property_id"] != anchor["property_id"]:
                errors.append(
                    "Quantity semantics require original header or reviewed column mapping: "
                    + value["id"]
                )
            if value["subject"] != anchor["run"] or anchor["eid"] not in value["evidence_ids"]:
                errors.append(
                    "Quantity subject/table-row membership contradicts original source: "
                    + value["id"]
                )
            if (
                v.get("raw_expression") != anchor["expression"]
                or v.get("reported_unit") != original_unit
            ):
                errors.append(
                    "Quantity expression/unit differs from original source cell: " + value["id"]
                )
        for statement in package["statements"]:
            if not statement.get("included", True) or statement["id"] in excluded:
                continue
            ancestry = class_ancestors(
                statement["class_id"], semantic.class_metadata, approved_ontology(self.root)
            )
            expected_classes = {
                r["class_id"]
                for r in self.epistemic_roles.values()
                if r["epistemic"] == statement["epistemic"]
            }
            if expected_classes and not ancestry.intersection(expected_classes):
                errors.append(
                    "Scientific statement class/epistemic role disagrees with source-role contract: "
                    + statement["id"]
                )
            anchor = statements.get(statement["id"])
            if not anchor and any(
                e in {a["eid"] for a in runs.values()} for e in statement["evidence_ids"]
            ):
                errors.append(
                    "Scientific statement must retain original table cell/role identity: "
                    + statement["id"]
                )
            if anchor:
                role = anchor["role"]
                # Multiple rows can explicitly report the identical statement.
                permitted = {
                    a["run"]
                    for a in statements.values()
                    if a["text"] == anchor["text"] and a["role"] == role
                }
                if (
                    statement["text"] != anchor["text"]
                    or anchor["eid"] not in statement["evidence_ids"]
                    or not set(statement.get("scope", [])) <= permitted
                ):
                    errors.append(
                        "Statement applicability/table-row membership contradicts original source: "
                        + statement["id"]
                    )
                if statement["epistemic"] != role["epistemic"]:
                    prefix = (
                        "Uncertain source statements cannot become confirmed observations or conclusions; "
                        if role["epistemic"]
                        in {"hypothesis", "tentative_interpretation", "open_question"}
                        else ""
                    )
                    errors.append(
                        prefix
                        + "Source-backed statement role differs from original column ("
                        + role["epistemic"]
                        + "): "
                        + statement["id"]
                    )
                if role["class_id"] not in ancestry:
                    errors.append(
                        "Source-backed statement class differs from original column: "
                        + statement["id"]
                    )
            elif statement.get("scope"):
                reconstructed = narrative_statements.get(
                    statement.get("scientific_proposal_id", statement["id"])
                )
                grounded = bool(
                    reconstructed
                    and statement["text"] == reconstructed["proposal"]["text"]
                    and statement["class_id"] == reconstructed["proposal"]["class_id"]
                    and statement["epistemic"] == reconstructed["proposal"]["epistemic"]
                    and set(statement["scope"]) == set(reconstructed["scope"])
                    and set(statement["evidence_ids"])
                    == {s["evidence_id"] for s in reconstructed["support_spans"]}
                    and statement.get("support_spans") == reconstructed["support_spans"]
                )
                reviewed = grounded or any(
                    key.startswith("scope")
                    and d.get("explanation", "").strip()
                    and set(statement["evidence_ids"]) <= set(d.get("evidence_ids", []))
                    and set(statement["scope"])
                    <= set(d["selection"] if isinstance(d["selection"], list) else [d["selection"]])
                    for key, d in package["decisions"].items()
                )
                if not reviewed:
                    errors.append(
                        "Scientific review required: select source-supported narrative scope with evidence and an applicability explanation for "
                        + statement["id"]
                    )
                role_review = package["decisions"].get("role:" + statement["id"], {})
                reviewed_role = grounded or (
                    role_review.get("selection") == statement["epistemic"]
                    and role_review.get("principal") in self.policy.approvers
                    and role_review.get("explanation", "").strip()
                    and role_review.get("support_spans")
                    and all(
                        s.get("evidence_id") in refs
                        and s.get("text")
                        and s["text"] in refs[s["evidence_id"]]["text"]
                        and refs[s["evidence_id"]]["source_id"]
                        in {refs[e]["source_id"] for e in statement["evidence_ids"] if e in refs}
                        for s in role_review.get("support_spans", [])
                    )
                )
                if (
                    statement["epistemic"] == "author_reported_conclusion"
                    and not reviewed_role
                    and not re.search(
                        r"\b(?:results\s+(?:indicate|show)|authors?\s+conclude|concluded|conclusion|study\s+(?:showed|demonstrates)|demonstrated\s+that)\b",
                        statement["text"],
                        re.IGNORECASE,
                    )
                ):
                    errors.append(
                        "Scientific review required: author-conclusion role needs explicit original author attribution for "
                        + statement["id"]
                    )
                if statement["epistemic"] in {
                    "measured_observation",
                    "author_reported_conclusion",
                } and re.search(
                    r"\b(?:hypothes\w*|may|might|likely|not\s+clear|future\s+work)\b",
                    statement["text"],
                    re.IGNORECASE,
                ):
                    errors.append(
                        "Uncertain source statement requires tentative, hypothesis or open-question role: "
                        + statement["id"]
                    )
            if statement["epistemic"] in {
                "measured_observation",
                "reported_quantity",
            } and normative_instruction(statement["text"]):
                errors.append(
                    "Normative source instruction is not an experimental observation or measurement: "
                    + statement["id"]
                )
        return errors

    def review_statement_role(
        self, package_id, statement_id, epistemic, support_spans, explanation, principal
    ):
        """Authorized source-context adjudication in the existing review decisions.

        Context can span paragraphs/pages; this does not waive original table
        membership, uncertainty or normative safeguards.
        """
        self.authorize(principal)
        current = self.get(package_id)
        package = current["package"]
        statement = next(s for s in package["statements"] if s["id"] == statement_id)
        refs = {e["evidence_id"]: e for e in package["evidence"]}
        source_ids = {refs[e]["source_id"] for e in statement["evidence_ids"]}
        if (
            not explanation.strip()
            or not support_spans
            or not all(
                s.get("evidence_id") in refs
                and s.get("text")
                and s["text"] in refs[s["evidence_id"]]["text"]
                and refs[s["evidence_id"]]["source_id"] in source_ids
                for s in support_spans
            )
        ):
            raise ValueError(
                "Role review requires exact same-source context spans and a scientific explanation"
            )
        if epistemic not in {r["epistemic"] for r in self.epistemic_roles.values()}:
            raise ValueError("Choose a registered scientific epistemic classification")
        package["decisions"]["role:" + statement_id] = {
            "selection": epistemic,
            "principal": principal,
            "explanation": explanation,
            "support_spans": support_spans,
            "evidence_ids": statement["evidence_ids"],
            "affected_records": 1,
        }
        saved = self.save(package, principal)
        self.event(
            saved["package"],
            "SOURCE_ROLE_REVIEWED",
            principal,
            package["decisions"]["role:" + statement_id],
        )
        return saved

    def get(self, package_id, version=None):
        row = self.registry.db.execute(
            "SELECT payload,digest FROM research_packages WHERE package_id=? "
            + ("ORDER BY version DESC LIMIT 1" if version is None else "AND version=?"),
            (package_id,) if version is None else (package_id, version),
        ).fetchone()
        if not row:
            raise LookupError("Research package not found")
        return {"package": json.loads(row[0]), "digest": row[1]}

    def list_packages(self):
        return [
            dict(r)
            for r in self.registry.db.execute(
                "SELECT package_id,MAX(version) AS version FROM research_packages GROUP BY package_id"
            )
        ]

    def submit(self, title, purpose, files, creator):
        if not creator.strip() or not title.strip() or not files:
            raise ValueError("Title, creator and source materials are required")
        manifests = [
            {
                "name": Path(name).name,
                "sha256": hashlib.sha256(data).hexdigest(),
                "bytes": len(data),
            }
            for name, data in files
        ]
        # Filename/order independent duplicate detection; originals remain immutable.
        identity = digest({"title": title, "inputs": sorted(m["sha256"] for m in manifests)})[:20]
        package_id = "research-" + identity
        if self.registry.db.execute(
            "SELECT 1 FROM research_packages WHERE package_id=?", (package_id,)
        ).fetchone():
            return {**self.get(package_id), "duplicate": True}
        package = {
            "id": package_id,
            "version": 0,
            "title": title,
            "purpose": purpose,
            "creator": creator,
            "inputs": manifests,
            "evidence": [],
            "tables": [],
            "entities": [],
            "relations": [],
            "values": [],
            "statements": [],
            "extensions": [],
            "decisions": {},
            "corrections": [],
            "exclusions": [],
            "contexts": [],
        }
        for manifest, (name, data) in zip(manifests, files, strict=True):
            suffix = Path(name).suffix.lower()
            original = self.root / "data/submissions" / (manifest["sha256"] + suffix)
            original.parent.mkdir(parents=True, exist_ok=True)
            if original.exists():
                if hashlib.sha256(original.read_bytes()).hexdigest() != manifest["sha256"]:
                    raise ValueError("Submitted original checksum conflict")
            else:
                with original.open("xb") as handle:
                    handle.write(data)
            manifest["stored_input"] = str(original.relative_to(self.root))
            sid = package_id + ":" + manifest["sha256"][:16]
            if suffix == ".pdf":
                with pymupdf.open(stream=data, filetype="pdf") as doc:
                    units = [(i + 1, page.get_text("text")) for i, page in enumerate(doc)]
                rows = None
            elif suffix in {".csv", ".tsv"}:
                table_text, manifest["encoding"] = decode_table(data)
                rows = list(
                    csv.DictReader(
                        io.StringIO(table_text),
                        delimiter="\t" if suffix == ".tsv" else ",",
                    )
                )
                rows = [
                    {k.strip(): (v or "").strip() for k, v in row.items() if k is not None}
                    for row in rows
                ]
                units = [(i + 1, json.dumps(row, ensure_ascii=False)) for i, row in enumerate(rows)]
            elif suffix in {".txt", ".md", ".json"}:
                units = [(1, data.decode("utf-8-sig"))]
                rows = None
            else:
                raise ValueError(
                    f"Unsupported input {suffix}; supply an existing PDF/table/text representation"
                )
            evidence_ids = []
            for ordinal, text in units:
                eid = "E-" + digest([sid, ordinal, text])[:24]
                evidence_ids.append(eid)
                package["evidence"].append(
                    {
                        "evidence_id": eid,
                        "source_id": sid,
                        "document_id": sid + ":document",
                        "title": title,
                        "filename": manifest["name"],
                        "page": ordinal,
                        "text": text,
                        "checksum": manifest["sha256"],
                        "locator": {
                            "file": manifest["name"],
                            "row" if rows is not None else "page": ordinal,
                        },
                    }
                )
                if rows is None:
                    from nasa_fire_ai.ingestion.scientific_proposals import (
                        deterministic_propositions,
                    )

                    extracted = deterministic_propositions(
                        [{"text": text, "evidence_id": eid}], self.semantic, limit=1000
                    )
                    for item in extracted:
                        role = next(
                            (
                                r
                                for r in self.epistemic_roles.values()
                                if r["class_id"] == item["class_id"]
                            ),
                            None,
                        )
                        if role:
                            epistemic = role["epistemic"]
                            if epistemic != "open_question" and re.search(
                                r"\b(suggest|may|might|hypothes|likely)\w*\b|not clear",
                                item["quote"],
                                re.IGNORECASE,
                            ):
                                epistemic = "tentative_interpretation"
                            if epistemic != "open_question" and re.search(
                                r"\bhypothes\w*\b", item["quote"], re.IGNORECASE
                            ):
                                epistemic = "hypothesis"
                            package["statements"].append(
                                {
                                    "id": sid + ":statement:" + digest(item)[:16],
                                    "text": item["quote"],
                                    "class_id": "NASAConclusion"
                                    if epistemic in {"tentative_interpretation", "hypothesis"}
                                    else item["class_id"],
                                    "epistemic": epistemic,
                                    "scope": [],
                                    "origin": "prose",
                                    "evidence_ids": [eid],
                                    "included": True,
                                }
                            )
                    if re.search(r"\bmicrogravity\b", text, re.IGNORECASE):
                        package["contexts"].append(
                            {
                                "id": "context:" + eid,
                                "value": "microgravity",
                                "type": "gravity",
                                "evidence_ids": [eid],
                                "text": text,
                                "status": "CANDIDATE",
                            }
                        )
            if rows:
                profiles = profile_table(rows)
                columns = []
                for profile in profiles:
                    resolution = resolve_column(profile, self.semantic)
                    role = next(
                        (
                            r
                            for r, aliases in self.presentation["column_roles"].items()
                            if profile.normalized_label in aliases
                        ),
                        None,
                    )
                    statement = self.presentation["statement_roles"].get(profile.normalized_label)
                    columns.append(
                        {
                            "label": profile.label,
                            "unit": profile.raw_unit,
                            "property_id": resolution.property_id,
                            "role": role,
                            "statement_role": profile.normalized_label if statement else None,
                            "status": resolution.status,
                        }
                    )
                package["tables"].append(
                    {
                        "id": sid,
                        "rows": rows,
                        "evidence_ids": evidence_ids,
                        "columns": columns,
                        "class_id": "ExperimentalRun",
                    }
                )
        if not package["evidence"] or not any(e["text"].strip() for e in package["evidence"]):
            raise ValueError(
                "No extractable source text or table rows; supply a text-backed representation"
            )
        package["entities"].append(
            {
                "id": package_id,
                "label": title,
                "class_id": "Investigation",
                "evidence_ids": [package["evidence"][0]["evidence_id"]],
            }
        )
        self.regenerate(package)
        saved = self.save(package, creator)
        self.event(saved["package"], "SUBMITTED", creator, {"inputs": manifests})
        return saved

    def submit_ntrs(self, nasa_id, creator, *, adapter=None):
        """Acquire one eligible official NASA document into immutable submissions.

        Uses the existing NTRS adapter and public-download policy. Acquisition
        prepares a draft and never registers approved scientific knowledge.
        """
        import httpx

        from nasa_fire_ai.ingestion.autonomous import official_download
        from nasa_fire_ai.ingestion.phase1 import NTRSAdapter
        from nasa_fire_ai.ingestion.source_eligibility import assess, content_text, explanation

        metadata = (adapter or NTRSAdapter()).fetch_metadata(str(nasa_id))
        url = official_download(metadata)

        def fetch():
            with httpx.stream("GET", url, timeout=40, follow_redirects=False) as response:
                response.raise_for_status()
                chunks, size = [], 0
                for chunk in response.iter_bytes():
                    size += len(chunk)
                    if size > 50 * 1024 * 1024:
                        raise ValueError("Official submission exceeds 50 MiB acquisition limit")
                    chunks.append(chunk)
            return b"".join(chunks)

        # Identity, NASA involvement, domain relevance and accessibility are
        # judged separately: a short keyword list never decides alone, the
        # document's own first pages are read when the citation is not enough,
        # and uncertain relevance goes to review instead of rejection.
        data = None
        assessment = assess(metadata)
        if assessment["domain_relevance"]["status"] != "ESTABLISHED":
            data = fetch()
            assessment = assess(metadata, content_text(data))
        if assessment["extraction_eligibility"] == "INELIGIBLE":
            raise ValueError(
                "Citation does not establish relevant reduced-gravity combustion or spacecraft "
                "fire safety: " + explanation(assessment)
            )
        key = digest(["official-ntrs-submission-v1", str(nasa_id), url, metadata.get("modified")])
        cached = self.registry.get_phase3_cache(key, "official_submission")
        if cached:
            return {**self.get(cached["package_id"]), "duplicate": True}
        if data is None:
            data = fetch()
        saved = self.submit(
            metadata["title"],
            metadata.get("abstract", "Official NASA research submission"),
            [(str(nasa_id) + ".pdf", data)],
            creator,
        )
        package = saved["package"]
        package["source_provenance"] = {
            "publisher_origin": "NASA NTRS",
            "source_url": url,
            "nasa_id": str(nasa_id),
            "metadata": metadata,
            "sha256": hashlib.sha256(data).hexdigest(),
            "eligibility": assessment["eligibility"],
            "eligibility_assessment": assessment,
            "scientific_review": "NONE",
        }
        saved = self.save(package, creator)
        self.registry.set_phase3_cache(key, "official_submission", {"package_id": package["id"]})
        return saved

    def prepare_scientific(
        self, package_id, settings, *, model_enabled=False, budget=None, client=None
    ):
        """Prepare isolated candidates; successful segments resume from registry cache."""
        from nasa_fire_ai.ingestion.document_extraction import ExtractionBudget, extract_package

        package = self.get(package_id)["package"]
        if self.validate_originals(package):
            raise ValueError("Original source integrity failed before scientific preparation")
        extraction = extract_package(
            self, package, settings, budget or ExtractionBudget(), model_enabled, client
        )
        package["scientific_extraction"] = extraction
        self.regenerate(package)
        previous = copy.deepcopy(self.get(package_id)["package"])
        candidate = copy.deepcopy(package)
        for item in (previous, candidate):
            if item.get("scientific_extraction"):
                item["scientific_extraction"].pop("processing", None)
        if previous == candidate:
            return {
                **self.get(package_id),
                "processing": extraction["processing"],
                "duplicate": True,
            }
        saved = self.save(package, package["creator"])
        candidate_ids = set()
        for record in extraction["records"]:
            spans = record["support_spans"]
            item = record["proposal"]
            candidate_id = package_id + ":" + record["id"] + ":" + digest(record)[:12]
            if not record.get("duplicate_of"):
                candidate_ids.add(candidate_id)
            self.registry.stage_semantic_candidate(
                {
                    "candidate_id": candidate_id,
                    "candidate_type": record["kind"],
                    "raw_label": next(
                        (item[k] for k in ("label", "term", "text", "relation") if k in item), ""
                    ),
                    "source_id": spans[0]["source_id"] if spans else None,
                    "evidence_id": spans[0]["evidence_id"] if spans else None,
                    "resolution_status": "REJECTED"
                    if record["status"] == "REJECTED"
                    else "CANDIDATE_NEW_CONCEPT"
                    if record["kind"] == "concepts"
                    else "KNOWN_AMBIGUOUS",
                    "review_status": "SUPERSEDED"
                    if record.get("duplicate_of")
                    else "REJECTED"
                    if record["status"] == "REJECTED"
                    else "PENDING",
                    "proposal": {
                        "contract": extraction["contract"],
                        "package_id": package_id,
                        **record,
                    },
                }
            )
        sources = {e["evidence_id"]: e.get("source_id") for e in package["evidence"]}
        for kind, rows, label in (
            ("composition", extraction.get("composition_proposals", []), "relation_candidate"),
            ("ontology_extension", extraction.get("ontology_extension_proposals", []), "term"),
        ):
            # Composition the source states, and the vocabulary it would need:
            # staged for scientific and ontology review, never canonical.
            for row in rows:
                evidence_id = (row.get("evidence") or [{}])[0].get("evidence_id")
                candidate_id = package_id + ":" + row["id"] + ":" + digest(row)[:12]
                candidate_ids.add(candidate_id)
                self.registry.stage_semantic_candidate(
                    {
                        "candidate_id": candidate_id,
                        "candidate_type": kind,
                        "raw_label": row[label],
                        "source_id": sources.get(evidence_id),
                        "evidence_id": evidence_id,
                        "resolution_status": "CANDIDATE_NEW_CONCEPT"
                        if row.get("kind") in {"class", "information_class"}
                        else "CANDIDATE_RELATION",
                        "review_status": "PENDING",
                        "proposal": {
                            "contract": extraction["contract"],
                            "package_id": package_id,
                            **row,
                        },
                    }
                )
        for row in self.registry.db.execute(
            "SELECT candidate_id FROM semantic_staging WHERE json_extract(payload_json,'$.proposal.package_id')=? AND review_status='PENDING'",
            (package_id,),
        ).fetchall():
            if row[0] not in candidate_ids:
                self.registry.db.execute(
                    "UPDATE semantic_staging SET review_status='SUPERSEDED' WHERE candidate_id=?",
                    (row[0],),
                )
        self.registry.db.commit()
        self.event(
            saved["package"], "SCIENTIFIC_PREPARED", package["creator"], extraction["processing"]
        )
        return {**saved, "processing": extraction["processing"]}

    def attach_scientific_proposals(self, package):
        """Use established entities, statements and values for correction and export."""
        extraction = package.get("scientific_extraction")
        if not extraction:
            return
        records = sorted(
            [
                r
                for r in extraction["records"]
                if r["status"] != "REJECTED" and not r.get("duplicate_of")
            ],
            key=lambda r: r["status"] != "SOURCE_SUPPORTED",
        )
        semantic = self.property_registry(package)
        entity_keys = extraction["entities_by_key"]
        existing = {e["id"] for e in package["entities"]}
        # Supported knowledge that needs vocabulary the approved ontology lacks is
        # kept for Phase 2 review beside its staged extension proposal; it is never
        # projected or exported as established knowledge.
        proposed = package.setdefault("proposed_extension_items", [])
        kept = {p["id"] for p in proposed}
        from nasa_fire_ai.ingestion.proposal_states import (
            extension_proposal_id,
            term_of,
            vocabulary_terms,
        )

        for record in records:
            if (
                record.get("proposal_state") != "PROPOSED_ONTOLOGY_EXTENSION"
                or record["id"] in kept
                # A proposed concept is itself the staged proposal; there is no
                # knowledge item waiting for it.
                or record["kind"] == "concepts"
            ):
                continue
            item = record["proposal"]
            terms = vocabulary_terms(record) or [
                term_of(
                    record,
                    {"entities": "class", "statements": "information_class"}.get(
                        record["kind"], "relation"
                    ),
                )
            ]
            kind, term = terms[0]
            proposed.append(
                {
                    "id": record["id"],
                    "kind": record["kind"],
                    "label": item.get("label") or item.get("text"),
                    "term": term,
                    "extension_proposal_id": extension_proposal_id(kind, term),
                    **(
                        {"subject": record.get("subject"), "object": record.get("object")}
                        if record["kind"] == "relations"
                        else {}
                    ),
                    "evidence_ids": sorted({s["evidence_id"] for s in record["support_spans"]}),
                    "support_spans": record["support_spans"],
                    "proposal_state": "PROPOSED_ONTOLOGY_EXTENSION",
                    "included": False,
                }
            )
            kept.add(record["id"])
        for record in records:
            if record["kind"] != "entities":
                continue
            entity = record["proposal"]
            if entity["class_id"] not in semantic.class_metadata:
                continue
            if record["entity_id"] not in existing:
                package["entities"].append(
                    {
                        "id": record["entity_id"],
                        "label": entity["label"],
                        "class_id": entity["class_id"],
                        "evidence_ids": sorted({s["evidence_id"] for s in record["support_spans"]}),
                        "origin": "contextual",
                        "study": entity["study"],
                        "review_status": record["status"],
                    }
                )
                existing.add(record["entity_id"])

        def statement_key(statement):
            return (
                statement["text"],
                statement["epistemic"],
                statement.get("modality"),
                tuple(sorted(statement["evidence_ids"])),
                tuple(sorted(statement.get("scope", []))),
                tuple(
                    (s["evidence_id"], s["start"], s["end"])
                    for s in statement.get("support_spans", [])
                ),
            )

        statement_texts = {statement_key(s) for s in package["statements"]}
        for record in records:
            item, kind = record["proposal"], record["kind"]
            refs = sorted({s["evidence_id"] for s in record["support_spans"]})
            if kind == "statements" and item["class_id"] in semantic.information_classes:
                match = next(
                    (
                        s
                        for s in package["statements"]
                        if (s["text"], s["epistemic"]) == (item["text"], item["epistemic"])
                        and s.get("origin") == "prose"
                        and record["support_spans"][0]["evidence_id"] in s["evidence_ids"]
                        and (
                            not s.get("support_spans")
                            or s["support_spans"][0] == record["support_spans"][0]
                        )
                    ),
                    None,
                )
                scope = [
                    entity_keys[k]["id"]
                    for k in item["subjects"]
                    if k in entity_keys
                    and entity_keys[k]["class_id"]
                    in {"ExperimentalRun", "ExperimentFamily", "Investigation", "Sample"}
                ]
                if match and scope and record["status"] == "SOURCE_SUPPORTED":
                    if stated_modality(item):
                        match["modality"] = stated_modality(item)
                    if not_done_configuration(item):
                        match["included"] = False
                    match["scope"] = scope
                    match["support_spans"] = record["support_spans"]
                    match["scientific_proposal_id"] = record["id"]
                    match["evidence_ids"] = refs
                    statement_texts.add(statement_key(match))
                else:
                    # An unresolved proposal stays in the package for review but
                    # is never included as established, exported knowledge.
                    candidate = {
                        "id": record["id"],
                        "text": item["text"],
                        "class_id": item["class_id"],
                        "epistemic": item["epistemic"],
                        **({"modality": stated_modality(item)} if stated_modality(item) else {}),
                        "scope": scope,
                        "origin": "contextual",
                        "study": item["study"],
                        "evidence_ids": refs,
                        "support_spans": record["support_spans"],
                        # A configuration that was proposed, prescribed or
                        # conditional stays for review, like its value: never an
                        # executed condition.
                        "included": record["status"] == "SOURCE_SUPPORTED"
                        and not not_done_configuration(item),
                        "review_status": record["status"],
                        "review_reasons": list(record["reasons"]),
                        "scientific_proposal_id": record["id"],
                    }
                    if statement_key(candidate) not in statement_texts:
                        package["statements"].append(candidate)
                        statement_texts.add(statement_key(candidate))
            elif kind == "relations" and record["status"] == "SOURCE_SUPPORTED":
                package["relations"].append(
                    {
                        "subject": record["subject"],
                        "object": record["object"],
                        "relation": item["relation"],
                        "evidence_ids": refs,
                        "origin": "contextual",
                    }
                )
            elif (
                kind == "quantities"
                and record["status"] == "SOURCE_SUPPORTED"
                and not_done_value(item)
            ):
                # A criterion value, or a proposed, prescribed, conditional or
                # hypothetical one, is kept for review and never becomes a
                # measurement or an executed condition of its subject.
                package.setdefault("non_executed_values", []).append(
                    {
                        "id": record["id"],
                        "subject": record["subject"],
                        "label": item["label"],
                        "expression": item["expression"],
                        "unit": item["unit"],
                        "epistemic": item["epistemic"],
                        "modality": stated_modality(item),
                        "facets": facets("quantities", item),
                        "evidence_ids": refs,
                        "included": False,
                    }
                )
            elif (
                kind == "quantities"
                and record["status"] == "SOURCE_SUPPORTED"
                and record.get("mapping", {}).get("property_id")
                and record.get("native_value_compatible", True)
                and record.get("native_scope_compatible", True)
            ):
                prop = semantic.properties[record["mapping"]["property_id"]]
                package["values"].append(
                    {
                        "id": record["id"],
                        "subject": record["subject"],
                        "property_id": prop.property_id,
                        "value": self.parse_value(item["expression"], item["unit"], prop),
                        "column": item["label"],
                        "evidence_ids": refs,
                        "epistemic": item["epistemic"],
                        "origin": "contextual",
                    }
                )

    def resolve_identity(self, label, relation):
        matches = [
            eid
            for eid, meta in getattr(self.semantic, "entity_mentions", {}).items()
            if meta.get("relation") == relation
            and label.lower() in {a.lower() for a in [eid, *meta.get("aliases", [])]}
        ]
        expected = object_class(relation)
        if expected and expected in self.entity_classes.get(label, set()):
            matches.append(label)
        return next(iter(set(matches))) if len(set(matches)) == 1 else None

    def identity_alternatives(self, relation):
        known = {
            eid
            for eid, meta in getattr(self.semantic, "entity_mentions", {}).items()
            if meta.get("relation") == relation
        }
        cls = object_class(relation)
        known.update(eid for eid, classes in self.entity_classes.items() if cls in classes)
        return sorted(known)

    def questions(self, package):
        """One dependency per shared mapping/identity/scope; no row-by-row confirmations."""
        questions = []
        decisions = package["decisions"]
        excluded = {item["subject"] for item in package["exclusions"]}
        for table in package["tables"]:
            eligible = [
                (row, eid)
                for i, (row, eid) in enumerate(
                    zip(table["rows"], table["evidence_ids"], strict=True)
                )
                if table["id"] + ":run:" + str(i) not in excluded
            ]
            role_key = "table-role:" + table["id"]
            if decisions.get(role_key, {}).get("selection") == "documentary":
                continue
            if role_key not in decisions:
                questions.append(
                    {
                        "id": role_key,
                        "kind": "table_role",
                        "affected_records": len(table["rows"]),
                        "question": "Does this table report executed experimental runs, or only documentary/planned information? Identify any non-run rows using the exception controls.",
                        "alternatives": ["ExperimentalRun", "documentary"],
                        "evidence_ids": table["evidence_ids"][:3],
                    }
                )
            for column in table["columns"]:
                if column["role"] or column["statement_role"] or column["property_id"]:
                    continue
                key = f"column:{table['id']}:{column['label']}"
                if key in decisions:
                    continue
                count = sum(bool(row.get(column["label"])) for row, _ in eligible)
                if not count:
                    continue
                questions.append(
                    {
                        "id": key,
                        "kind": "mapping",
                        "affected_records": count,
                        "question": f"What does '{column['label']}' represent"
                        + (f" in {column['unit']}" if column["unit"] else "")
                        + "? Select a known quantity, propose its definition, or retain it only as source context.",
                        "alternatives": self.mapping_alternatives(package, column)
                        + ["documentary", "extension"],
                        "evidence_ids": table["evidence_ids"][:3],
                    }
                )
            material_column = next((c for c in table["columns"] if c["role"] == "material"), None)
            if material_column:
                for label in sorted(
                    {
                        r[material_column["label"]]
                        for r, _ in eligible
                        if r.get(material_column["label"])
                    }
                ):
                    if self.resolve_identity(label, "hasMaterial"):
                        continue
                    key = "material:" + label
                    if key not in decisions:
                        affected = [
                            eid
                            for row, eid in eligible
                            if row.get(material_column["label"]) == label
                        ]
                        questions.append(
                            {
                                "id": key,
                                "kind": "identity",
                                "affected_records": len(affected),
                                "question": f"Does '{label}' identify an established material or a distinct specimen/material? Select the source-supported identity; lexical similarity does not establish equivalence.",
                                "alternatives": self.identity_alternatives("hasMaterial")
                                + ["distinct", "documentary"],
                                "evidence_ids": affected[:3],
                            }
                        )
            gravity_column = next((c for c in table["columns"] if c["role"] == "gravity"), None)
            if gravity_column:
                for label in sorted(
                    {r.get(gravity_column["label"], "") for r, _ in eligible} - {""}
                ):
                    key = "gravity:" + label
                    if (
                        not self.resolve_identity(label, "hasGravityCondition")
                        and key not in decisions
                    ):
                        affected = [
                            eid for r, eid in eligible if r.get(gravity_column["label"]) == label
                        ]
                        questions.append(
                            {
                                "id": key,
                                "kind": "identity",
                                "affected_records": len(affected),
                                "question": f"Which established gravity environment does '{label}' identify? Retain documentary context if the source cannot establish it.",
                                "alternatives": self.identity_alternatives("hasGravityCondition")
                                + ["documentary"],
                                "evidence_ids": affected,
                            }
                        )
        for context in package.get("contexts", []):
            if context["id"] not in decisions:
                questions.append(
                    {
                        "id": context["id"],
                        "kind": "context",
                        "affected_records": sum(len(t["rows"]) for t in package["tables"]),
                        "question": "Does the source's microgravity context apply to this submitted campaign? Local terrestrial controls will remain explicit exceptions. Choose documentary if the passage does not establish applicability.",
                        "alternatives": ["campaign", "documentary"],
                        "evidence_ids": context["evidence_ids"],
                    }
                )
        for epistemic in sorted({s["epistemic"] for s in package["statements"]}):
            statements = [
                s
                for s in package["statements"]
                if s["epistemic"] == epistemic and not s.get("scope") and s.get("included", True)
            ]
            if statements:
                key = "scope-group:" + epistemic
                questions.append(
                    {
                        "id": key,
                        "kind": "scope",
                        "affected_records": len(statements),
                        "question": f"Which identified runs do these {epistemic.replace('_', ' ')} statements apply to? Review cited-study attribution and use individual scope controls for exceptions, or retain documentary context.",
                        "alternatives": [
                            e["id"]
                            for e in package["entities"]
                            if e["class_id"]
                            in {"ExperimentalRun", "Investigation", "ExperimentFamily", "Sample"}
                        ]
                        + ["documentary"],
                        "evidence_ids": sorted(
                            {eid for s in statements for eid in s["evidence_ids"]}
                        ),
                        "statement_ids": [s["id"] for s in statements],
                    }
                )
        labels = {e["id"]: e["label"] for e in package["entities"]}
        for question in questions:
            question["question_id"] = question["id"]
            question["affected_entities"] = question.get("statement_ids", []) or sorted(
                e["id"]
                for e in package["entities"]
                if set(e["evidence_ids"]) & set(question["evidence_ids"])
            )
            meanings = {
                "ExperimentalRun": "Executed experimental runs",
                "documentary": "Retain as documentary evidence without this scientific assertion",
                "extension": "Propose and review a scientific definition absent from the vocabulary",
                "distinct": "A distinct source-identified material",
                "campaign": "The stated environment applies to the campaign, preserving local exceptions",
            }
            question["options"] = [
                {
                    "selection": selection,
                    "label": meanings.get(selection, labels.get(selection, selection)),
                    "meaning": meanings.get(selection, labels.get(selection, selection)),
                    "operations": (
                        [
                            {
                                "action": "scope",
                                "subject": sid,
                                "objects": [] if selection == "documentary" else [selection],
                            }
                            for sid in question["statement_ids"]
                        ]
                    )
                    if question["kind"] == "scope"
                    else [
                        {
                            "action": "review_decision",
                            "question_id": question["id"],
                            "selection": selection,
                            "rebuild": "affected table/context dependencies",
                        }
                    ],
                    "requires_extension_review": selection == "extension",
                }
                for selection in question["alternatives"]
            ]
            question["options"].append(
                {
                    "selection": "another",
                    "label": "Another interpretation; explain briefly",
                    "meaning": "Prepare a typed correction preview; apply only after validation and review",
                    "operations": [],
                    "requires_preview": True,
                }
            )
            question["allows_multiple"] = question["kind"] == "scope"
            question["required_validation"] = [
                "entity identity",
                "source evidence",
                "scientific scope",
                "ontology contracts",
                "quantities and units",
                "epistemic consistency",
                "conflicts",
            ]
            question["dependent_issues"] = [question["id"]]
            question["readiness_implication"] = (
                "Resolve this incorporation dependency; revalidate remaining issues"
            )
            question["priority"] = question["affected_records"] + (
                10 if question["kind"] in {"scope", "identity"} else 0
            )
        return sorted(questions, key=lambda q: (-q["priority"], q["id"]))

    def mapping_alternatives(self, package, column):
        """Offer compatible quantity contracts; unit compatibility is not equivalence."""
        from nasa_fire_ai.normalization.units import normalize

        candidates = []
        for prop in self.property_registry(package).properties.values():
            unit = column["unit"] or ("%" if "percent" in column["label"].lower() else None)
            if unit:
                try:
                    _, canonical = normalize(1.0, unit)
                except ValueError:
                    continue
                if canonical != prop.canonical_unit:
                    continue
            elif prop.datatype == "numeric":
                # An absent unit cannot establish a quantitative interpretation.
                if not any(alias.lower() in column["label"].lower() for alias in prop.aliases):
                    continue
            candidates.append(prop.property_id)
        return candidates

    def regenerate(self, package):
        """Rebuild table-derived proposals, then replay approved typed corrections."""
        package["entities"] = package["entities"][:1]
        package["relations"] = []
        package["values"] = []
        # Rebuilt with the values; a kept copy would grow on every regeneration.
        package["non_executed_values"] = []
        package["statements"] = [s for s in package["statements"] if s.get("origin") == "prose"]
        for table in package["tables"]:
            for column in table["columns"]:
                # A column recorded as a statement role that is no longer a table
                # role (criteria are roles only) goes back to its mapping question.
                if (
                    column.get("statement_role")
                    and column["statement_role"] not in self.presentation["statement_roles"]
                ):
                    column["statement_role"] = None
        for table in package["tables"]:
            if (
                package["decisions"].get("table-role:" + table["id"], {}).get("selection")
                == "documentary"
            ):
                continue
            for i, (row, eid) in enumerate(zip(table["rows"], table["evidence_ids"], strict=True)):
                from nasa_fire_ai.ingestion.generic import documentary_row

                if (
                    documentary_row(row)
                    and package["decisions"].get("table-role:" + table["id"], {}).get("selection")
                    != "ExperimentalRun"
                ):
                    continue
                run_column = next((c for c in table["columns"] if c["role"] == "run"), None)
                label = row.get(run_column["label"], "") if run_column else str(i + 1)
                rid = table["id"] + ":run:" + str(i)
                package["entities"].append(
                    {
                        "id": rid,
                        "label": label,
                        "class_id": table["class_id"],
                        "evidence_ids": [eid],
                    }
                )
                package["relations"].append(
                    {
                        "subject": rid,
                        "relation": "belongsToInvestigation",
                        "object": package["id"],
                        "evidence_ids": [eid],
                    }
                )
                for column in table["columns"]:
                    raw = row.get(column["label"], "")
                    if not raw:
                        continue
                    key = f"column:{table['id']}:{column['label']}"
                    mapping = (
                        package["decisions"].get(key, {}).get("selection", column["property_id"])
                    )
                    role = column["role"]
                    if role == "material":
                        decision = package["decisions"].get("material:" + raw, {}).get("selection")
                        material = self.resolve_identity(raw, "hasMaterial") or decision
                        if material == "distinct":
                            material = table["id"] + ":material:" + digest(raw)[:12]
                            if not any(e["id"] == material for e in package["entities"]):
                                package["entities"].append(
                                    {
                                        "id": material,
                                        "label": raw,
                                        "class_id": "Material",
                                        "evidence_ids": [eid],
                                    }
                                )
                        if material and material != "documentary":
                            package["relations"].append(
                                {
                                    "subject": rid,
                                    "relation": "hasMaterial",
                                    "object": material,
                                    "evidence_ids": [eid],
                                }
                            )
                    elif role == "gravity":
                        # Only approved registered identities, never textual similarity.
                        gravity = self.resolve_identity(raw, "hasGravityCondition") or package[
                            "decisions"
                        ].get("gravity:" + raw, {}).get("selection")
                        if gravity and gravity != "documentary":
                            package["relations"].append(
                                {
                                    "subject": rid,
                                    "relation": "hasGravityCondition",
                                    "object": gravity,
                                    "evidence_ids": [eid],
                                }
                            )
                    elif role == "group":
                        gid = table["id"] + ":group:" + raw
                        if not any(e["id"] == gid for e in package["entities"]):
                            package["entities"].append(
                                {
                                    "id": gid,
                                    "label": raw,
                                    "class_id": "ExperimentFamily",
                                    "evidence_ids": [eid],
                                }
                            )
                        package["relations"].append(
                            {
                                "subject": rid,
                                "relation": "belongsToExperimentFamily",
                                "object": gid,
                                "evidence_ids": [eid],
                            }
                        )
                    elif column["statement_role"]:
                        contract = self.presentation["statement_roles"][column["statement_role"]]
                        package["statements"].append(
                            {
                                "id": rid + ":statement:" + column["label"],
                                "text": raw,
                                **contract,
                                "scope": [rid],
                                "evidence_ids": [eid],
                                "origin": "table",
                                "included": True,
                            }
                        )
                    elif mapping and mapping != "documentary":
                        prop = self.property_registry(package).properties.get(mapping)
                        value = self.parse_value(raw, column["unit"], prop)
                        package["values"].append(
                            {
                                "id": rid + ":value:" + column["label"],
                                "subject": rid,
                                "property_id": mapping,
                                "value": value,
                                "column": column["label"],
                                "evidence_ids": [eid],
                                "epistemic": prop.context
                                if prop
                                and prop.context
                                in {
                                    "derived_quantity",
                                    "reported_quantity",
                                    "experimental_configuration",
                                }
                                else "experimental_configuration",
                            }
                        )
        self.attach_scientific_proposals(package)
        for correction in package["corrections"]:
            self.apply_operations(package, correction["operations"])
        self.resolve_context(package)
        # Active proposals are sets of scientific identities, unlike append-only events.
        exclusions = {item["subject"]: item for item in package["exclusions"]}
        package["exclusions"] = [exclusions[key] for key in sorted(exclusions)]
        relations = {}
        for relation in package["relations"]:
            key = tuple(relation[k] for k in ("subject", "relation", "object"))
            if key not in relations:
                relations[key] = copy.deepcopy(relation)
            relations[key]["evidence_ids"] = sorted(
                set(relations[key]["evidence_ids"]) | set(relation["evidence_ids"])
            )
        package["relations"] = [relations[key] for key in sorted(relations)]

    def resolve_context(self, package):
        from nasa_fire_ai.context import ContextStatement, ContextStatus, ScopeResolver

        package["relations"] = [
            r for r in package["relations"] if r.get("scope_origin") != "campaign"
        ]
        resolver = ScopeResolver()
        evidence = {e["evidence_id"]: e for e in package["evidence"]}
        metadata = self.property_registry(package).class_metadata
        runs = [
            e["id"]
            for e in package["entities"]
            if e["class_id"] == "ExperimentalRun"
            or metadata.get(e["class_id"], {}).get("parent") == "ExperimentalRun"
        ]
        for context in package.get("contexts", []):
            if package["decisions"].get(context["id"], {}).get("selection") == "campaign":
                resolver.add(
                    ContextStatement(
                        statement_id=context["id"],
                        context_type="gravity",
                        value=context["value"],
                        entity_ids=runs,
                        evidence_ids=context["evidence_ids"],
                        original_text=context["text"],
                        source_location={
                            "document_id": evidence[context["evidence_ids"][0]]["document_id"]
                        },
                        scope="campaign",
                        quantifier="ALL",
                        validation_status=ContextStatus.VERIFIED_APPLICABLE_CONTEXT,
                    )
                )
        for relation in package["relations"]:
            if relation["relation"] == "hasGravityCondition":
                resolver.add(
                    ContextStatement(
                        statement_id=digest(relation),
                        context_type="gravity",
                        value=relation["object"],
                        entity_ids=[relation["subject"]],
                        evidence_ids=relation["evidence_ids"],
                        original_text=evidence[relation["evidence_ids"][0]]["text"],
                        source_location={
                            "document_id": evidence[relation["evidence_ids"][0]]["document_id"]
                        },
                        scope="run",
                        quantifier="IDENTIFIED",
                        validation_status=ContextStatus.EXPLICIT_LOCAL,
                    )
                )
        for run in runs:
            resolved = resolver.resolve(run, "gravity")
            if resolved.status == ContextStatus.VERIFIED_APPLICABLE_CONTEXT:
                for statement in resolved.statements:
                    rel = {
                        "subject": run,
                        "relation": "hasGravityCondition",
                        "object": statement.value,
                        "evidence_ids": statement.evidence_ids,
                        "scope_origin": "campaign",
                    }
                    if rel not in package["relations"]:
                        package["relations"].append(rel)

    @staticmethod
    def parse_value(raw, unit, prop):
        if prop and prop.datatype == "categorical":
            return GenericValue(reported_value=raw, raw_expression=raw).model_dump()
        from nasa_fire_ai.ingestion.numeric_expressions import parse_numeric_expression

        # The shared syntax-only grammar gives one reading or keeps the literal:
        # a bound such as ">425" or an unresolved "1,500" is never stored as an
        # exact number, and "−40" keeps its sign.
        parsed = parse_numeric_expression(str(raw).strip(), table_cell=True)
        ends = parsed.get("endpoints") or []
        if parsed["status"] == "PARSED" and all(
            len(e.get("value_candidates", [])) == 1
            and not (e.get("qualifier") or {}).get("operator")
            for e in ends
        ):
            values = [float(e["value_candidates"][0]) for e in ends]
            if parsed["form"] == "SCALAR":
                return GenericValue(
                    reported_value=values[0],
                    reported_unit=unit,
                    approximate=bool((ends[0].get("qualifier") or {}).get("approximate")),
                    raw_expression=raw,
                ).model_dump()
            if parsed["form"] in {"RANGE", "BETWEEN", "FROM_TO"} and values[0] <= values[1]:
                return GenericValue(
                    lower=values[0],
                    upper=values[1],
                    reported_unit=unit,
                    raw_expression=raw,
                ).model_dump()
        return GenericValue(reported_value=raw, reported_unit=unit, raw_expression=raw).model_dump()

    def property_registry(self, package):
        registry = copy.deepcopy(self.semantic)
        for extension in package["extensions"]:
            if extension.get("approved"):
                activate_extension(SemanticGraph(registry), extension)
        if package.get("scientific_extraction"):
            # Existing RDF declarations are reused in this draft-local registry;
            # proposed definitions remain inactive and the shared schema is untouched.
            ontology = approved_ontology(self.root)
            for cls, meta in ontology["classes"].items():
                registry.target_classes.add(cls)
                metadata = registry.class_metadata.setdefault(cls, {"target": True})
                metadata["approved_ontology_parents"] = list(meta["parents"])
            for relation in ontology["object_properties"]:
                if relation not in registry.relations:
                    registry.register_relation(RelationDefinition(relation))
        return registry

    def clarification(
        self, package_id, question_id, selection, explanation, principal, reported_unit=None
    ):
        base = self.get(package_id)
        package = base["package"]
        question = next((q for q in self.questions(package) if q["id"] == question_id), None)
        selections = selection if isinstance(selection, list) else [selection]
        if (
            question
            and question["kind"] == "mapping"
            and selection in self.property_registry(package).properties
            and selection not in question["alternatives"]
        ):
            raise ValueError("Quantity is incompatible with the source unit or header")
        if (
            not question
            or not selections
            or not set(selections) <= set(question["alternatives"])
            or (
                len(selections) > 1 and (question["kind"] != "scope" or "documentary" in selections)
            )
        ):
            raise ValueError("Choose a listed source-supported scientific alternative")
        if not explanation.strip():
            meanings = {o["selection"]: o["meaning"] for o in question["options"]}
            explanation = "Scientist selected the listed interpretation: " + "; ".join(
                meanings[s] for s in selections
            )
        if selection == "extension":
            raise ValueError("Define and review the new quantity before mapping this column")
        # Mapping dimension validation occurs before the draft changes.
        if question["kind"] == "mapping" and selection != "documentary":
            table = next(
                t for t in package["tables"] if question_id.startswith("column:" + t["id"] + ":")
            )
            column = next(c for c in table["columns"] if question_id.endswith(":" + c["label"]))
            if reported_unit:
                source_header = column["label"].lower()
                if reported_unit.lower() not in source_header and not (
                    reported_unit == "%" and "percent" in source_header
                ):
                    raise ValueError(
                        "Unit correction requires the original source header to state that unit"
                    )
                column["original_unit"] = column["unit"]
                column["unit"] = reported_unit
            prop = self.property_registry(package).properties[selection]
            for row in table["rows"]:
                if raw := row.get(column["label"]):
                    value = GenericValue(**self.parse_value(raw, column["unit"], prop))
                    self.property_registry(package).validate(
                        PropertyConstraintV2(
                            property_id=selection,
                            operator="BETWEEN" if value.lower is not None else "EQ",
                            value=value,
                        )
                    )
        if question["kind"] == "scope":
            operations = [
                {
                    "action": "scope",
                    "subject": sid,
                    "objects": [] if selection == "documentary" else selections,
                }
                for sid in question["statement_ids"]
            ]
            package["corrections"].append(
                {
                    "instruction": explanation,
                    "operations": operations,
                    "principal": principal,
                    "approved_at": now(),
                    "question_id": question_id,
                }
            )
        package["decisions"][question_id] = {
            "selection": selection,
            "explanation": explanation,
            "principal": principal,
            "affected_records": question["affected_records"],
            "evidence_ids": question["evidence_ids"],
            "reported_unit": reported_unit,
        }
        self.regenerate(package)
        saved = self.save(package, principal)
        self.event(
            saved["package"], "CLARIFICATION_APPLIED", principal, package["decisions"][question_id]
        )
        return saved

    def reopen_decision(self, package_id, question_id, explanation, principal):
        current = self.get(package_id)
        decision = current["package"]["decisions"].pop(question_id, None)
        if not decision or not explanation.strip():
            raise ValueError(
                "Select an existing scientific decision and explain why it needs revision"
            )
        current["package"]["corrections"] = [
            c for c in current["package"]["corrections"] if c.get("question_id") != question_id
        ]
        if question_id.startswith("scope-group:"):
            epistemic = question_id.removeprefix("scope-group:")
            for statement in current["package"]["statements"]:
                if statement["epistemic"] == epistemic and statement.get("origin") == "prose":
                    statement["scope"] = []
                    statement["included"] = True
        self.regenerate(current["package"])
        revised = self.save(current["package"], principal)
        self.event(
            revised["package"],
            "DECISION_REOPENED",
            principal,
            {"question_id": question_id, "previous_decision": decision, "explanation": explanation},
        )
        return revised

    @staticmethod
    def apply_operations(package, operations):
        for op in operations:
            if op["action"] == "add_relation":
                rel = {k: op[k] for k in ("subject", "relation", "object", "evidence_ids")}
                if rel not in package["relations"]:
                    package["relations"].append(rel)
            elif op["action"] == "remove_relation":
                package["relations"] = [
                    r
                    for r in package["relations"]
                    if not all(r.get(k) == op.get(k) for k in ("subject", "relation", "object"))
                ]
            elif op["action"] == "scope":
                statement = next(s for s in package["statements"] if s["id"] == op["subject"])
                statement["scope"] = op["objects"]
                statement["included"] = bool(op["objects"])
            elif op["action"] == "value":
                value = next(v for v in package["values"] if v["id"] == op["subject"])
                # Source value is immutable; correction replaces semantics/scope only.
                value["subject"] = op.get("object", value["subject"])
                value["property_id"] = op.get("property_id", value["property_id"])
                if "value" in op:
                    value["value"] = op["value"]
                    value["evidence_ids"] = op["evidence_ids"]
            elif op["action"] == "entity_label":
                entity = next(e for e in package["entities"] if e["id"] == op["subject"])
                entity["label"] = op["label"]
            elif op["action"] == "entity_class":
                entity = next(e for e in package["entities"] if e["id"] == op["subject"])
                entity["class_id"] = op["class_id"]
            elif op["action"] == "classify_statement":
                statement = next(s for s in package["statements"] if s["id"] == op["subject"])
                statement["class_id"] = op["class_id"]
                statement["epistemic"] = op["epistemic"]
            elif op["action"] == "exclude":
                package["exclusions"] = [
                    item for item in package["exclusions"] if item["subject"] != op["subject"]
                ]
                package["exclusions"].append({"subject": op["subject"], "reason": op["reason"]})
                for statement in package["statements"]:
                    if statement["id"] == op["subject"]:
                        statement["included"] = False
            else:
                raise ValueError("Unsupported correction action")

    def preview_correction(self, package_id, operations, instruction, principal):
        base = self.get(package_id)
        before = base["package"]
        draft = copy.deepcopy(before)
        editable = (
            {e["id"] for e in draft["entities"]}
            | {s["id"] for s in draft["statements"]}
            | {v["id"] for v in draft["values"]}
        )
        refs = {e["evidence_id"] for e in draft["evidence"]}
        for op in operations:
            typed_subjects = {
                "entity_label": {e["id"] for e in draft["entities"]},
                "entity_class": {e["id"] for e in draft["entities"]},
                "value": {v["id"] for v in draft["values"]},
                "classify_statement": {s["id"] for s in draft["statements"]},
                "scope": {s["id"] for s in draft["statements"]},
            }
            if (
                op["action"] in typed_subjects
                and op.get("subject") not in typed_subjects[op["action"]]
            ):
                raise ValueError("The correction targets the wrong kind of scientific item")
            if op["action"] == "classify_statement":
                metadata = self.property_registry(draft).class_metadata
                cls = op.get("class_id")
                parent = metadata.get(cls, {}).get("parent", cls)
                if not any(
                    parent == r["class_id"] and op.get("epistemic") == r["epistemic"]
                    for r in self.epistemic_roles.values()
                ):
                    raise ValueError("Choose a registered scientific epistemic classification")
            if op.get("subject") not in editable:
                raise ValueError(
                    "Published reference entities are read-only; create a separate change proposal"
                )
            if op["action"] in {"add_relation", "remove_relation"}:
                if op.get("relation") not in self.property_registry(draft).relations:
                    raise ValueError("Relationship is not in the approved scientific vocabulary")
                if op.get("object") not in editable | self.semantic.entities:
                    raise ValueError("Unknown relationship endpoint")
            if op["action"] == "scope" and (
                not set(op["objects"]) <= editable
                or op["subject"] not in {s["id"] for s in draft["statements"]}
            ):
                raise ValueError("Scope must identify draft scientific entities")
            if (
                op["action"] not in {"exclude", "scope"}
                and not set(op.get("evidence_ids", [])) <= refs
            ):
                raise ValueError("Correction evidence is not supplied by this research package")
            if op["action"] == "add_relation" and not op.get("evidence_ids"):
                raise ValueError("A new relationship needs original source evidence")
            if op["action"] == "value" and "value" in op:
                expression = op["value"].get("raw_expression")
                if not expression or not any(
                    expression in e["text"]
                    for e in draft["evidence"]
                    if e["evidence_id"] in op.get("evidence_ids", [])
                ):
                    raise ValueError(
                        "Corrected value must retain its exact original source expression"
                    )
            if op["action"] == "entity_label" and (
                not op.get("label")
                or not any(
                    op["label"] in e["text"]
                    for e in draft["evidence"]
                    if e["evidence_id"] in op.get("evidence_ids", [])
                )
            ):
                raise ValueError("Corrected entity label requires original source support")
        self.apply_operations(draft, operations)
        self.resolve_context(draft)
        errors = self.validate(draft)["errors"]
        introduced = [e for e in errors if e not in self.validate(before)["errors"]]
        if introduced:
            raise ValueError("; ".join(introduced))
        return {
            "base_digest": base["digest"],
            "package_id": package_id,
            "instruction": instruction,
            "principal": principal,
            "operations": operations,
            "before": {k: before[k] for k in ("relations", "values", "statements")},
            "after": {k: draft[k] for k in ("relations", "values", "statements")},
            "validation": self.validate(draft),
        }

    def apply_correction(self, proposal, principal):
        base = self.get(proposal["package_id"])
        if base["digest"] != proposal["base_digest"]:
            raise ValueError("Draft changed; regenerate the correction preview")
        # Revalidate, never trust caller-supplied preview or model validation.
        checked = self.preview_correction(
            proposal["package_id"], proposal["operations"], proposal["instruction"], principal
        )
        package = base["package"]
        correction = {
            "instruction": checked["instruction"],
            "operations": checked["operations"],
            "principal": principal,
            "approved_at": now(),
        }
        if not any(c["operations"] == correction["operations"] for c in package["corrections"]):
            package["corrections"].append(correction)
        self.regenerate(package)
        saved = self.save(package, principal)
        self.event(saved["package"], "CORRECTION_APPROVED", principal, checked)
        return saved

    def propose_extension(self, package_id, proposal, principal):
        if proposal.get("kind") in {"class", "object_property"}:
            return self.propose_concept(package_id, proposal, principal)
        required = {
            "property",
            "definition",
            "why_existing_insufficient",
            "domain",
            "range",
            "evidence_ids",
            "impact",
            "validation_contract",
        }
        if not required <= set(proposal) or not all(proposal[k] for k in required):
            raise ValueError(
                "Scientific definition, source, compatibility and validation contract are required"
            )
        base = self.get(package_id)
        prop = PropertyDefinition(**proposal["property"])
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9]*", prop.property_id):
            raise ValueError("Invalid property identity")
        if (
            prop.property_id in self.semantic.properties
            or proposal["domain"] not in self.semantic.target_classes
        ):
            raise ValueError("Only compatible new properties may use this extension path")
        if (
            proposal["range"] not in {"numeric", "categorical"}
            or proposal["range"] != prop.datatype
        ):
            raise ValueError("Property range and quantity contract conflict")
        if (
            prop.status != "CANONICAL"
            or proposal["validation_contract"] != "SemanticRegistry.validate"
        ):
            raise ValueError("Unsupported extension validation contract")
        if not set(proposal["evidence_ids"]) <= {
            e["evidence_id"] for e in base["package"]["evidence"]
        }:
            raise ValueError("Extension source evidence missing")
        proposal = {
            **proposal,
            "approved": False,
            "ontology_version": "curation-" + prop.property_id,
        }
        base["package"]["extensions"].append(proposal)
        return self.save(base["package"], principal)

    def propose_concept(self, package_id, proposal, principal):
        """Compatible declarative additions require evidence and explicit scientific review."""
        required = {
            "kind",
            "id",
            "name",
            "definition",
            "purpose",
            "why_existing_insufficient",
            "evidence_ids",
            "impact",
            "constraints",
        }
        if not required <= proposal.keys() or not all(
            proposal[k] for k in required - {"constraints"}
        ):
            raise ValueError(
                "Scientific meaning, evidence, reuse review and compatibility are required"
            )
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9]*", proposal["id"]):
            raise ValueError("Invalid scientific concept identity")
        base = self.get(package_id)
        package = base["package"]
        semantic = self.property_registry(package)
        known = semantic.target_classes | semantic.information_classes
        if not proposal["evidence_ids"] or not set(proposal["evidence_ids"]) <= {
            e["evidence_id"] for e in package["evidence"]
        }:
            raise ValueError("Concept requires original source evidence")
        ontology = Graph().parse(self.root / "ontology/fire_safety.ttl")
        existing_labels = {
            c.lower() for c in known | set(semantic.relations) | set(semantic.properties)
        }
        existing_labels.update(
            str(term).rsplit("/", 1)[-1].rsplit("#", 1)[-1].lower()
            for term in ontology.subjects(RDF.type, OWL.Class)
        )
        existing_labels.update(
            str(term).rsplit("/", 1)[-1].rsplit("#", 1)[-1].lower()
            for term in ontology.subjects(RDF.type, OWL.ObjectProperty)
        )
        existing_labels.update(str(label).lower() for label in ontology.objects(None, RDFS.label))
        existing_labels.update(
            a.lower()
            for meta in semantic.class_metadata.values()
            for a in meta.get("query_terms", [])
        )
        existing_labels.update(
            a.lower() for prop in semantic.properties.values() for a in prop.aliases
        )
        if proposal["id"].lower() in existing_labels or proposal["name"].lower() in existing_labels:
            raise ValueError("Reuse the existing scientific concept or propose an explicit alias")
        if set(proposal["constraints"]) - {"required_relations"}:
            raise ValueError("Unsupported constraints require an explicit modeling change")
        if (
            not set(proposal["constraints"].get("required_relations", []))
            <= semantic.relations.keys()
        ):
            raise ValueError("Required scientific relationships must already be approved")
        if proposal["kind"] == "class":
            if proposal.get("parent") not in known:
                raise ValueError("Parent class must already be approved")
            if not proposal.get("intended_instances") or not proposal.get("query_terms"):
                raise ValueError("Intended instances and scientific query terms are required")
            parent_meta = semantic.class_metadata.get(proposal["parent"], {})
            metadata = {
                **parent_meta,
                "query_terms": proposal["query_terms"],
                "parent": proposal["parent"],
            }
            proposal = {**proposal, "metadata": metadata}
        else:
            required_relation = {
                "domain",
                "range",
                "direction",
                "scope",
                "evidence_requirements",
                "transitive",
            }
            if not required_relation <= proposal.keys():
                raise ValueError(
                    "Relationship domain, range, direction, scope and evidence contract required"
                )
            if (
                not proposal["domain"]
                or not proposal["range"]
                or not set(proposal["domain"] + proposal["range"]) <= known
            ):
                raise ValueError("Relationship source and target classes must be approved")
            if (
                proposal["direction"] != "source_to_target"
                or proposal["transitive"]
                or proposal.get("inverse")
            ):
                raise ValueError(
                    "Transitivity/inverse changes require separate scientific migration review"
                )
            if proposal["constraints"].get("required_relations"):
                raise ValueError("Required relations are class constraints")
        proposal = {
            **proposal,
            "approved": False,
            "reuse_review": {
                "searched_classes": sorted(known),
                "searched_properties": sorted(semantic.properties),
                "searched_relations": sorted(semantic.relations),
                "ontology_sha256": hashlib.sha256(
                    (self.root / "ontology/fire_safety.ttl").read_bytes()
                ).hexdigest(),
            },
        }
        if any(e.get("id") == proposal["id"] for e in package["extensions"]):
            raise ValueError("A proposal with this identity already exists")
        package["extensions"].append(proposal)
        return self.save(package, principal)

    def approve_extension(self, package_id, property_id, principal):
        self.authorize(principal)
        base = self.get(package_id)
        extension = next(
            (
                e
                for e in base["package"]["extensions"]
                if e.get("id", e.get("property", {}).get("property_id")) == property_id
            ),
            None,
        )
        if extension is None:
            raise ValueError("No staged extension with this id in the package: " + property_id)
        extension["approved"] = True
        extension["approver"] = principal
        return self.save(base["package"], principal)

    def validate(self, package):
        errors = self.validate_originals(package)
        errors.extend(self.validate_attribution(package))
        if package.get("scientific_extraction"):
            from nasa_fire_ai.ingestion.document_extraction import (
                extraction_semantic,
                validate_output,
            )
            from nasa_fire_ai.ingestion.document_structure import structure

            extraction = package["scientific_extraction"]
            if not package.get("source_provenance"):
                errors.append(
                    "Scientific source eligibility review required: establish NASA involvement and domain relevance"
                )
            elif package["source_provenance"].get("eligibility") != "OFFICIAL_NASA_DOMAIN_DOCUMENT":
                errors.append(
                    "Scientific source eligibility review required: "
                    + str(package["source_provenance"].get("eligibility"))
                )
            if extraction["contract_digest"] != self.contract_digest():
                errors.append("Scientific extraction contracts changed; prepare a new version")
            rebuilt_document = structure(
                package, self.root, extraction["processing"]["budget"]["segment_chars"]
            )
            rebuilt = validate_output(
                extraction["raw_proposals"],
                package,
                rebuilt_document,
                extraction_semantic(self, package),
            )
            if rebuilt["records"] != extraction["records"]:
                errors.append(
                    "Scientific extraction validation differs from original source; regenerate"
                )
            from nasa_fire_ai.ingestion.document_extraction import (
                table_mapping_decisions,
                table_quantities,
                table_row_roles,
            )

            expected_mappings = table_mapping_decisions(
                self, package, extraction_semantic(self, package)
            )
            if table_quantities(self, package, expected_mappings) != extraction.get(
                "table_quantity_proposals", []
            ):
                errors.append(
                    "Structured table quantities differ from the original cells and mapping contracts"
                )
            if table_row_roles(package) != extraction.get("table_row_role_proposals"):
                errors.append("Table row roles differ from original source cells; regenerate")
            from nasa_fire_ai.ingestion.pdf_quantities import pdf_table_quantities

            expected_pdf_quantities = pdf_table_quantities(package, rebuilt_document)
            if expected_pdf_quantities != extraction.get("pdf_table_quantity_proposals", []):
                errors.append(
                    "PDF quantitative proposals differ from original cells, headers or page context; regenerate"
                )
            if expected_pdf_quantities:
                errors.append(
                    "Original PDF quantities retain unresolved role and experimental scope for scientific review"
                )
            errors.extend(
                "Scientific quantity native representation deferred; original literal retained: "
                + r["id"]
                for r in rebuilt["records"]
                if r.get("native_value_compatible") is False
                and r.get("mapping", {}).get("property_id")
            )
            errors.extend(
                "Scientific preparation review dependency: " + issue["kind"]
                for issue in rebuilt["review_requirements"]
            )
        if package.get("contract_digest") and package["contract_digest"] != self.contract_digest():
            errors.append(
                "Scientific contracts changed; regenerate and review a new prepared version"
            )
        semantic = self.property_registry(package)
        ids = {e["id"] for e in package["entities"]} | {
            s["id"] for s in package["statements"] if s.get("included", True)
        }
        kinds = {e["id"]: e["class_id"] for e in package["entities"] + package["statements"]}

        ontology = approved_ontology(self.root)

        def ancestors(class_id):
            # The same approved hierarchy extraction uses: registry parents and the
            # ontology's subclass parents, transitively.
            return class_ancestors(class_id, semantic.class_metadata, ontology)

        refs = {e["evidence_id"]: e for e in package["evidence"]}
        excluded = {e["subject"] for e in package["exclusions"]}
        for entity in package["entities"]:
            if entity["class_id"] not in semantic.target_classes | semantic.information_classes:
                errors.append("Unregistered scientific class: " + entity["class_id"])
            if not entity["evidence_ids"] or not set(entity["evidence_ids"]) <= refs.keys():
                errors.append("Missing entity evidence: " + entity["id"])
        for rel in package["relations"]:
            if rel["subject"] in excluded:
                continue
            if (
                rel["relation"] not in semantic.relations
                or rel["subject"] not in ids
                or rel["object"] not in ids | semantic.entities
            ):
                errors.append("Invalid relation endpoint or type: " + str(rel))
            if not rel["evidence_ids"] or not set(rel["evidence_ids"]) <= refs.keys():
                errors.append("Missing relationship evidence")
            contract = semantic.relations.get(rel["relation"])
            if contract:
                # The registry's own domain and range, or the endpoint contract
                # extraction enforces when the registry declares none.
                domain, range_ = RELATION_ENDPOINTS.get(rel["relation"], ((), ()))
                for endpoint, allowed in (
                    ("subject", contract.domain or domain),
                    ("object", contract.range or range_),
                ):
                    classes = (
                        ancestors(kinds.get(rel[endpoint], ""))
                        | self.entity_classes.get(rel[endpoint], set())
                    ) - {""}
                    # An endpoint whose class is not known here (a canonical literal)
                    # is checked by identity below, not refused for lacking a class.
                    if allowed and classes and not classes.intersection(allowed):
                        errors.append(
                            "Scientific relationship "
                            + endpoint
                            + " violates approved type contract"
                        )
            if rel["relation"] in IDENTITY_RELATIONS:
                required_class = object_class(rel["relation"])
                new_classes = {
                    e["class_id"] for e in package["entities"] if e["id"] == rel["object"]
                }
                if required_class not in new_classes and rel[
                    "object"
                ] not in self.identity_alternatives(rel["relation"]):
                    errors.append(
                        "Relationship object has the wrong scientific kind: " + rel["object"]
                    )
        # Opposing identities at equal scope are a scientific conflict, never a majority vote.
        for subject in ids:
            for dimension in ("hasMaterial", "hasGravityCondition", "belongsToInvestigation"):
                objects = {
                    r["object"]
                    for r in package["relations"]
                    if r["subject"] == subject and r["relation"] == dimension
                }
                if len(objects) > 1:
                    errors.append("Conflicting " + dimension + " for " + subject)
        for value in package["values"]:
            if value["subject"] in excluded or value["id"] in excluded:
                continue
            try:
                v = GenericValue(**value["value"])
                semantic.validate(
                    PropertyConstraintV2(
                        property_id=value["property_id"],
                        operator="BETWEEN" if v.lower is not None else "EQ",
                        value=v,
                    )
                )
                prop = semantic.properties[value["property_id"]]
                reconstructed = GenericValue(
                    **self.parse_value(v.raw_expression or "", v.reported_unit, prop)
                )
                if any(
                    getattr(v, key) != getattr(reconstructed, key)
                    for key in ("reported_value", "lower", "upper", "approximate")
                ):
                    raise ValueError("Reported numeric value differs from original expression")
                if not value["evidence_ids"] or not all(
                    eid in refs for eid in value["evidence_ids"]
                ):
                    raise ValueError("Quantity evidence is missing")
                if not any(
                    (v.raw_expression or "") in refs[eid]["text"] for eid in value["evidence_ids"]
                ):
                    raise ValueError("Quantity expression absent from original source")
                if value["subject"] not in ids:
                    raise ValueError("Unknown measured subject")
            except (ValueError, LookupError) as error:
                errors.append(value["id"] + ": " + str(error))
        for statement in package["statements"]:
            if not statement.get("included", True):
                continue
            if statement["class_id"] not in semantic.information_classes:
                errors.append("Unregistered statement classification")
            if statement["epistemic"] not in {
                r["epistemic"] for r in self.epistemic_roles.values()
            } | {"derived_quantity", "documentary_context", "experimental_configuration"}:
                errors.append("Missing scientific epistemic classification")
            scope_ids = {
                e["id"]
                for e in package["entities"]
                if ancestors(e["class_id"]).intersection(
                    {"ExperimentalRun", "Investigation", "ExperimentFamily", "Sample"}
                )
            }
            if not statement.get("scope") or not set(statement["scope"]) <= scope_ids:
                errors.append("Select source-supported scope for " + statement["id"])
            if not any(
                statement["text"] in refs.get(eid, {}).get("text", "")
                for eid in statement["evidence_ids"]
            ):
                errors.append("Statement is not an original source span: " + statement["id"])
        questions = self.questions(package)
        for extension in package["extensions"]:
            if extension.get("approved") and extension.get("kind") == "class":
                for entity in package["entities"] + package["statements"]:
                    if entity["class_id"] != extension["id"] or entity["id"] in excluded:
                        continue
                    for required_relation in extension["constraints"].get("required_relations", []):
                        if not any(
                            r["subject"] == entity["id"] and r["relation"] == required_relation
                            for r in package["relations"]
                        ):
                            errors.append(
                                "Missing required scientific relationship: " + required_relation
                            )
        errors.extend(q["question"] for q in questions)
        return {
            "ready": not errors,
            "errors": sorted(set(errors)),
            "questions": questions,
            "metrics": {
                "distinct_decisions": len(package["decisions"]),
                "records_resolved": sum(
                    d.get("affected_records", 0) for d in package["decisions"].values()
                ),
                "duplicate_questions_avoided": sum(
                    max(0, d.get("affected_records", 0) - 1) for d in package["decisions"].values()
                ),
                "automatic_mappings": sum(
                    bool(c["property_id"]) for t in package["tables"] for c in t["columns"]
                ),
                "manual_corrections": len(package["corrections"]),
                "ontology_extensions": len(package["extensions"]),
                "blockers": len(set(errors)),
            },
        }

    def preview_query(self, package_id, query):
        """Run the ordinary service on a discarded database copy, visibly marked draft."""
        import tempfile

        from nasa_fire_ai.config import Settings
        from nasa_fire_ai.services.phase3 import Phase3AssistantService

        current = self.get(package_id)
        package = current["package"]
        with tempfile.TemporaryDirectory(prefix="nasa-draft-preview-") as directory:
            preview_root = Path(directory)
            evidence = type(self.registry)(preview_root / "data/index/evidence.sqlite")
            self.registry.db.backup(evidence.db)
            for unit in package["evidence"]:
                evidence.add_source(
                    {
                        "source_id": unit["source_id"],
                        "title": package["title"],
                        "status": "DRAFT_PREVIEW",
                    }
                )
                evidence.add_document(unit["document_id"], unit["source_id"], package["title"])
                evidence.add_passage(
                    {
                        "evidence_id": unit["evidence_id"],
                        "document_id": unit["document_id"],
                        "page": unit["page"],
                        "section": "Draft preview",
                        "text": unit["text"],
                        "start_offset": 0,
                        "end_offset": len(unit["text"]),
                        "raw_file": None,
                        "checksum": unit["checksum"],
                    }
                )
            evidence.db.execute(
                "INSERT OR REPLACE INTO research_active VALUES (?,?)",
                (package_id, current["digest"]),
            )
            evidence.db.commit()
            assistant = Phase3AssistantService(
                root=self.root, settings=Settings(root=preview_root, nvidia_api_key=None)
            )
            from nasa_fire_ai.ingestion.semantic import project_legacy

            assistant._native_store = project_legacy(self.root, evidence)
            project_package(assistant._native_store, package)
            result = assistant._answer_native_query(query, None)
            result.rendered_answer = (
                "DRAFT PREVIEW — unapproved scientific representation.\n\n" + result.rendered_answer
            )
            result.evidence_bundle.retrieval_metadata["publication_status"] = "DRAFT_PREVIEW"
            assistant.registry.db.close()
            evidence.db.close()
            return result

    def export_package(self, package_id):
        """Portable original research inputs, proposal and RO-Crate provenance metadata."""
        import zipfile

        current = self.get(package_id)
        package = current["package"]
        if self.validate_originals(package):
            raise ValueError("Original input integrity must pass before export")
        entries = [
            {
                "@id": "ro-crate-metadata.json",
                "@type": "CreativeWork",
                "about": {"@id": "./"},
                "conformsTo": {"@id": "https://w3id.org/ro/crate/1.1"},
            },
            {
                "@id": "./",
                "@type": "Dataset",
                "name": package["title"],
                "description": package["purpose"],
                "hasPart": [
                    {"@id": m["sha256"] + Path(m["name"]).suffix} for m in package["inputs"]
                ],
            },
        ]
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as output:
            for manifest in package["inputs"]:
                name = manifest["sha256"] + Path(manifest["name"]).suffix
                output.writestr(name, (self.root / manifest["stored_input"]).read_bytes())
                entries.append(
                    {
                        "@id": name,
                        "@type": "File",
                        "name": manifest["name"],
                        "contentSize": manifest["bytes"],
                        "sha256": manifest["sha256"],
                    }
                )
            output.writestr(
                "ro-crate-metadata.json",
                json.dumps(
                    {"@context": "https://w3id.org/ro/crate/1.1/context", "@graph": entries},
                    indent=2,
                ),
            )
            output.writestr("prepared-package.json", json.dumps(current, indent=2))
        return archive.getvalue()

    def authorize(self, principal):
        if principal not in self.policy.approvers:
            raise PermissionError("This principal has no configured publication authority")
        if not self.policy.development and not self.policy.public_enabled:
            raise PermissionError(
                "Public publication is disabled; use an isolated development configuration"
            )

    def proposal_states(self, package_id):
        """Each record's proposal state, with the two states only curation can reach.

        A record supported by the source, or staged as a proposed extension, is
        scientifically reviewed once the exact current version is approved, and
        authorized published once that version is the active one. Nothing is written
        into the record, so the approved digest stays unchanged.
        """
        current = self.get(package_id)
        records = (current["package"].get("scientific_extraction") or {}).get("records", [])
        approved = self.registry.db.execute(
            "SELECT 1 FROM research_approvals WHERE digest=?", (current["digest"],)
        ).fetchone()
        active = self.registry.db.execute(
            "SELECT digest FROM research_active WHERE package_id=?", (package_id,)
        ).fetchone()
        published = bool(active and active[0] == current["digest"])
        projected = projected_record_ids(current["package"])
        states = {}
        for record in records:
            state = record.get("proposal_state", record["status"])
            if record.get("duplicate_of") or record.get("active_proposal") is False:
                states[record["id"]] = "DUPLICATE"
                continue
            if state == "SOURCE_SUPPORTED" and published and record["id"] in projected:
                state = "AUTHORIZED_PUBLISHED"
            elif state in {"SOURCE_SUPPORTED", "PROPOSED_ONTOLOGY_EXTENSION"} and (
                approved or published
            ):
                # A record that needs a staged term is reviewed with its version but
                # never published by it: staging is not publication.
                state = "SCIENTIFICALLY_REVIEWED"
            states[record["id"]] = state
        return states

    def state_dimensions(self, package_id):
        """Each record's separate completeness, evidence, structure, extension and
        publication states (``proposal_states.state_dimensions``), read from curation."""
        from nasa_fire_ai.ingestion.proposal_states import state_dimensions

        current = self.get(package_id)
        package = current["package"]
        records = (package.get("scientific_extraction") or {}).get("records", [])
        active = self.registry.db.execute(
            "SELECT digest FROM research_active WHERE package_id=?", (package_id,)
        ).fetchone()
        published = bool(active and active[0] == current["digest"])
        approved_terms = {
            e.get("id") for e in package.get("extensions", []) if e.get("approved") and e.get("id")
        }
        projected = projected_record_ids(package)
        return {
            r["id"]: state_dimensions(
                r, approved_terms=approved_terms, published=published and r["id"] in projected
            )
            for r in records
        }

    def approve(self, package_id, exact_digest, principal):
        self.authorize(principal)
        current = self.get(package_id)
        if current["digest"] != exact_digest:
            raise ValueError("Approval must name the exact latest prepared version")
        result = self.validate(current["package"])
        if not result["ready"]:
            raise ValueError("Publication blocked: " + "; ".join(result["errors"]))
        receipt = {
            "digest": exact_digest,
            "version": current["package"]["version"],
            "principal": principal,
            "approved_at": now(),
            "development": self.policy.development,
            "authority": "configured test approval"
            if self.policy.development
            else "deployment approval",
        }
        self.registry.db.execute(
            "INSERT OR IGNORE INTO research_approvals VALUES (?,?,?,?,?)",
            (
                exact_digest,
                principal,
                receipt["approved_at"],
                int(self.policy.development),
                json.dumps(receipt),
            ),
        )
        self.registry.db.commit()
        self.event(current["package"], "APPROVED", principal, receipt)
        return receipt

    def publish(self, package_id, exact_digest, principal, fail_at=None):
        self.authorize(principal)
        current = self.get(package_id)
        if current["digest"] != exact_digest:
            raise ValueError("The draft changed after approval; approve the revised digest")
        approval = self.registry.db.execute(
            "SELECT * FROM research_approvals WHERE digest=?", (exact_digest,)
        ).fetchone()
        if not approval or approval["principal"] not in self.policy.approvers:
            raise PermissionError("No currently authorized exact-version approval")
        if bool(approval["development"]) != self.policy.development:
            raise PermissionError("Development approval cannot authorize public publication")
        active = self.registry.db.execute(
            "SELECT digest FROM research_active WHERE package_id=?", (package_id,)
        ).fetchone()
        if active and active[0] == exact_digest:
            return {"status": "ALREADY_ACTIVE", "digest": exact_digest}
        package = current["package"]
        if not self.validate(package)["ready"]:
            raise ValueError("Approved package no longer validates")
        # Prepare native graph and SHACL BEFORE changing any visible store.
        store = SemanticGraph(self.property_registry(package))
        project_package(store, package)
        shapes = Graph().parse(self.root / "ontology/semantic_shapes.ttl")
        generated_shapes = extension_shapes(store)
        shapes += generated_shapes
        conforms, _, report = shacl_validate(store.graph, shacl_graph=shapes)
        if not conforms:
            raise ValueError("Graph validation blocked publication: " + str(report))
        store.graph += generated_shapes
        graph_data = "\n".join(sorted(store.graph.serialize(format="nt").splitlines())) + "\n"
        graph_file = self.root / "data/canonical/research" / f"{exact_digest}.nt"
        graph_file.parent.mkdir(parents=True, exist_ok=True)
        graph_sha = hashlib.sha256(graph_data.encode()).hexdigest()
        if graph_file.exists():
            if hashlib.sha256(graph_file.read_bytes()).hexdigest() != graph_sha:
                raise ValueError("Approved RDF version checksum conflict")
        else:
            # Binary mode keeps LF bytes on every platform so graph_sha256 stays valid.
            with graph_file.open("xb") as handle:
                handle.write(graph_data.encode())
        receipt = {
            "status": "ACTIVE",
            "digest": exact_digest,
            "version": package["version"],
            "previous_digest": active[0] if active else None,
            "development": self.policy.development,
            "entities": len(store.entities()),
            "triples": len(store.graph),
            "evidence": len(package["evidence"]),
            "shacl": True,
            "vector_status": "DISABLED; no vector completeness claim",
            "published_at": now(),
            "graph_path": str(graph_file.relative_to(self.root)),
            "graph_sha256": graph_sha,
        }
        db = self.registry.db
        try:
            db.execute("BEGIN IMMEDIATE")
            latest = db.execute(
                "SELECT digest FROM research_packages WHERE package_id=? ORDER BY version DESC LIMIT 1",
                (package_id,),
            ).fetchone()[0]
            if latest != exact_digest:
                raise ValueError(
                    "A concurrent correction changed the approved version; approve again"
                )
            # Recheck competing ontology additions under the activation lock.
            locked_registry = load_semantic_registry(self.root / "domain/semantic_registry.yaml")
            locked_store = SemanticGraph(locked_registry)
            for existing in db.execute(
                "SELECT p.payload FROM research_active a JOIN research_packages p USING(digest) WHERE a.package_id<>?",
                (package_id,),
            ):
                project_package(locked_store, json.loads(existing[0]))
            project_package(locked_store, package)
            for evidence in package["evidence"]:
                sid, did, eid = (
                    evidence["source_id"],
                    evidence["document_id"],
                    evidence["evidence_id"],
                )
                db.execute(
                    "INSERT OR IGNORE INTO sources(source_id,source_type,title,filename,sha256,status) VALUES (?,?,?,?,?,?)",
                    (
                        sid,
                        "reviewed-research-package",
                        package["title"],
                        evidence["filename"],
                        evidence["checksum"],
                        "REVIEWED",
                    ),
                )
                db.execute(
                    "INSERT OR IGNORE INTO documents VALUES (?,?,?)", (did, sid, package["title"])
                )
                db.execute(
                    "INSERT OR IGNORE INTO passages VALUES (?,?,?,?,?,?,?,?,?)",
                    (
                        eid,
                        did,
                        evidence["page"],
                        "submitted research",
                        evidence["text"],
                        0,
                        len(evidence["text"]),
                        None,
                        evidence["checksum"],
                    ),
                )
                db.execute("INSERT OR IGNORE INTO evidence_refs VALUES (?,?)", (eid, sid))
                db.execute(
                    "INSERT OR IGNORE INTO evidence_locations VALUES (?,?)",
                    (eid, json.dumps(evidence["locator"])),
                )
                db.execute("DELETE FROM passages_fts WHERE evidence_id=?", (eid,))
                db.execute(
                    "INSERT INTO passages_fts(evidence_id,text) VALUES (?,?)",
                    (eid, evidence["text"]),
                )
            if fail_at == "index":
                raise RuntimeError("Injected index failure")
            db.execute(
                "INSERT OR REPLACE INTO research_active VALUES (?,?)", (package_id, exact_digest)
            )
            if fail_at == "graph":
                raise RuntimeError("Injected graph activation failure")
            db.execute(
                "INSERT OR REPLACE INTO research_publications VALUES (?,?,?,?)",
                (exact_digest, "ACTIVE", now(), json.dumps(receipt)),
            )
            db.execute("DELETE FROM phase3_cache")
            if (
                db.execute("PRAGMA integrity_check").fetchone()[0] != "ok"
                or db.execute("PRAGMA foreign_key_check").fetchall()
            ):
                raise RuntimeError("Evidence registry integrity failure")
            db.commit()
        except Exception as error:
            db.rollback()
            self.event(
                package,
                "PUBLICATION_FAILED",
                principal,
                {
                    "digest": exact_digest,
                    "error_type": type(error).__name__,
                    "previous_digest": active[0] if active else None,
                },
            )
            raise
        self.event(package, "PUBLISHED", principal, receipt)
        return receipt

    def approve_and_publish(self, package_id, exact_digest, principal):
        approval = self.approve(package_id, exact_digest, principal)
        return {
            "approval": approval,
            "publication": self.publish(package_id, exact_digest, principal),
        }

    def rollback(self, package_id, principal):
        self.authorize(principal)
        row = self.registry.db.execute(
            "SELECT p.receipt FROM research_publications p JOIN research_active a USING(digest) WHERE a.package_id=?",
            (package_id,),
        ).fetchone()
        if not row:
            raise ValueError("No active package")
        previous = json.loads(row[0])["previous_digest"]
        with self.registry.db:
            if previous:
                self.registry.db.execute(
                    "UPDATE research_active SET digest=? WHERE package_id=?", (previous, package_id)
                )
            else:
                self.registry.db.execute(
                    "DELETE FROM research_active WHERE package_id=?", (package_id,)
                )
            self.registry.db.execute("DELETE FROM phase3_cache")
        return {"status": "ROLLED_BACK", "restored_digest": previous}


def activate_extension(store, extension):
    """Activate one approved declarative contract in the existing RDF/registry."""
    if not extension.get("approved"):
        return
    kind = extension.get("kind", "quantity")
    if kind == "class":
        term = node(extension["id"])
        meta = extension["metadata"]
        existing = store.registry.class_metadata.get(extension["id"])
        if existing and existing != meta:
            raise ValueError("Ontology extension conflicts with an active class contract")
        store.registry.class_metadata[extension["id"]] = meta
        if meta.get("target"):
            store.registry.register_target_class(extension["id"])
        if meta.get("information"):
            store.registry.register_information_class(extension["id"])
        store.graph.add((term, RDF.type, OWL.Class))
        store.graph.add((term, RDFS.subClassOf, node(extension["parent"])))
    elif kind == "object_property":
        definition = RelationDefinition(
            relation_id=extension["id"],
            domain=extension["domain"],
            range=extension["range"],
            aliases=extension.get("aliases", [extension["name"]]),
            direction=extension["direction"],
        )
        existing = store.registry.relations.get(definition.relation_id)
        if existing and existing != definition:
            raise ValueError("Ontology extension conflicts with an active relationship contract")
        store.registry.register_relation(definition)
        term = node(extension["id"])
        store.graph.add((term, RDF.type, OWL.ObjectProperty))
        for domain in extension["domain"]:
            store.graph.add((term, RDFS.domain, node(domain)))
        for range_class in extension["range"]:
            store.graph.add((term, RDFS.range, node(range_class)))
    else:
        prop = PropertyDefinition(**extension["property"])
        existing = store.registry.properties.get(prop.property_id)
        if existing and existing != prop:
            raise ValueError("Ontology extension conflicts with an active quantity contract")
        store.registry.register(prop)
        term = node(prop.property_id)
        store.graph.add((term, RDF.type, OWL.DatatypeProperty))
        store.graph.add((term, RDFS.domain, node(extension["domain"])))
        store.graph.add(
            (
                term,
                NS.payload,
                Literal(json.dumps({"quantity_contract": extension["property"]}, sort_keys=True)),
            )
        )
    store.graph.add((term, RDFS.comment, Literal(extension["definition"])))
    for eid in extension.get("evidence_ids", []):
        store.graph.add((term, NS.evidenceRef, Literal(eid)))
    if kind in {"class", "object_property"}:
        # Scientific contract only; operational locators/reviewer identity stay in SQLite.
        contract = {
            k: v
            for k, v in extension.items()
            if k not in {"evidence_ids", "approver", "reuse_review"}
        }
        store.graph.add(
            (term, NS.payload, Literal(json.dumps({"ontology_contract": contract}, sort_keys=True)))
        )


def extension_shapes(store):
    """Generate deterministic native SHACL constraints from approved contracts."""
    sh = Namespace("http://www.w3.org/ns/shacl#")
    shapes = Graph()
    for term in store.graph.subjects(RDF.type, OWL.Class):
        payload = store.graph.value(term, NS.payload)
        contract = json.loads(str(payload)).get("ontology_contract", {}) if payload else {}
        required = contract.get("constraints", {}).get("required_relations", [])
        for relation_id in required:
            shape = node("shape:class:" + contract["id"] + ":" + relation_id)
            prop = node(str(shape) + ":property")
            path = node(str(shape) + ":inverse")
            qualified = node(str(shape) + ":qualified")
            predicate = node(str(shape) + ":predicate")
            for triple in (
                (shape, RDF.type, sh.NodeShape),
                (shape, sh.targetClass, term),
                (shape, sh.property, prop),
                (prop, sh.path, path),
                (path, sh.inversePath, NS.subject),
                (prop, sh.qualifiedValueShape, qualified),
                (prop, sh.qualifiedMinCount, Literal(1)),
                (qualified, sh.property, predicate),
                (predicate, sh.path, NS.relation),
                (predicate, sh.hasValue, node(relation_id)),
            ):
                shapes.add(triple)
    for relation in store.registry.relations.values():
        if not relation.domain and not relation.range:
            continue
        for record in store.graph.subjects(NS.relation, node(relation.relation_id)):
            for side, allowed in ((NS.subject, relation.domain), (NS.object, relation.range)):
                if not allowed:
                    continue
                shape = node("shape:" + str(record) + ":" + str(side))
                shapes.add((shape, RDF.type, sh.NodeShape))
                shapes.add((shape, sh.targetNode, store.graph.value(record, side)))
                head = node(str(shape) + ":or:0")
                shapes.add((shape, sh["or"], head))
                for index, cls in enumerate(allowed):
                    cell = node(str(shape) + ":or:" + str(index))
                    choice = node(str(shape) + ":class:" + cls)
                    shapes.add((cell, RDF.first, choice))
                    shapes.add(
                        (
                            cell,
                            RDF.rest,
                            RDF.nil
                            if index + 1 == len(allowed)
                            else node(str(shape) + ":or:" + str(index + 1)),
                        )
                    )
                    shapes.add((choice, sh["class"], node(cls)))
    return shapes


# Relations whose object is resolved as a known identity (a material, a gravity
# condition) before it can be a relationship object.
IDENTITY_RELATIONS = frozenset({"hasMaterial", "hasGravityCondition"})


def projected_record_ids(package):
    """The scientific records ``project_package`` would publish from this package:
    the same exclusions, included statements and done values, so a state report
    never calls published what the projection skips."""
    excluded = {e["subject"] for e in package["exclusions"]}
    records = (package.get("scientific_extraction") or {}).get("records", [])
    entity_ids = {
        e["id"]
        for e in package["entities"]
        if e["id"] not in excluded and e.get("review_status") in (None, "SOURCE_SUPPORTED")
    }
    statement_ids = {
        s.get("scientific_proposal_id")
        for s in package["statements"]
        if s.get("included", True) and s.get("id") not in excluded
    }
    value_ids = {
        v["id"]
        for v in package["values"]
        if not not_done_value(v) and v["id"] not in excluded and v["subject"] not in excluded
    }
    relations = {
        (r["subject"], r["relation"], r["object"])
        for r in package["relations"]
        if r["subject"] in entity_ids and r["object"] in entity_ids
    }
    projected = set()
    for record in records:
        item, kind = record.get("proposal") or {}, record.get("kind")
        if (
            (kind == "entities" and record.get("entity_id") in entity_ids)
            or (kind == "statements" and record["id"] in statement_ids)
            or (kind == "quantities" and record["id"] in value_ids)
            or (
                kind == "relations"
                and (record.get("subject"), item.get("relation"), record.get("object")) in relations
            )
        ):
            projected.add(record["id"])
    return projected


def project_package(store, package):
    """One graph; provenance locators/checksums never enter scientific payloads."""
    refs = {e["evidence_id"]: e for e in package["evidence"]}
    excluded = {e["subject"] for e in package["exclusions"]}
    for extension in package["extensions"]:
        activate_extension(store, extension)
    for entity in package["entities"]:
        if entity["id"] in excluded or entity.get("review_status") not in (
            None,
            "SOURCE_SUPPORTED",
        ):
            continue
        store.add_entity(
            entity["id"],
            entity["class_id"],
            entity["evidence_ids"],
            sorted({refs[e]["source_id"] for e in entity["evidence_ids"]}),
            {
                "id": entity["id"],
                "label": entity["label"],
                "text": entity["label"],
                "review_status": "APPROVED",
            },
        )
        if entity["class_id"] == "Investigation":
            store.registry.entity_mentions = getattr(store.registry, "entity_mentions", {})
            store.registry.entity_mentions[entity["id"]] = {
                "relation": "belongsToInvestigation",
                "aliases": [package["title"]],
            }
    for value in package["values"]:
        if not_done_value(value):
            # Never published as a measurement or an executed condition, whatever
            # version of the package carried it here.
            continue
        if value["id"] not in excluded and value["subject"] not in excluded:
            store.add_value(
                value["id"],
                value["subject"],
                value["property_id"],
                GenericValue(**value["value"]),
                value["evidence_ids"],
                {
                    "context": "reported_condition",
                    "epistemic": value["epistemic"],
                    "curation_authority": "RESEARCHER_CURATED",
                },
                class_id="ExperimentalCondition"
                if value["epistemic"] == "experimental_configuration"
                else "Measurement",
            )
            payload = store.payload(value["id"])
            payload["scope_applicability"] = package["title"]
            payload["description"] = value["column"] + " = " + str(value["value"]["raw_expression"])
            store.graph.set(
                (node(value["id"]), NS.payload, Literal(json.dumps(payload, sort_keys=True)))
            )
            for relation in package["relations"]:
                if (
                    relation["subject"] == value["subject"]
                    and relation["object"] not in excluded
                    and not store.registry.relations[relation["relation"]].domain
                ):
                    store.add_relation(
                        value["id"],
                        relation["relation"],
                        relation["object"],
                        value["evidence_ids"] + relation["evidence_ids"],
                    )
    for statement in package["statements"]:
        if not statement.get("included", True):
            continue
        payload = {
            "id": statement["id"],
            "text": statement["text"],
            "epistemic": statement["epistemic"],
            **({"modality": statement["modality"]} if statement.get("modality") else {}),
            "execution_status": (facets("statements", statement) or {}).get("execution_status"),
            "scope": statement["scope"],
            "review_status": "APPROVED",
            "evidence_ids": statement["evidence_ids"],
            "scope_applicability": package["title"],
            "authority": "RESEARCHER_CURATED",
        }
        store.add_entity(
            statement["id"],
            statement["class_id"],
            statement["evidence_ids"],
            sorted({refs[e]["source_id"] for e in statement["evidence_ids"]}),
            payload,
        )
        # Explicit selected scope supplies experiment applicability, not conclusion support.
        for target in statement["scope"]:
            if target == package["id"]:
                store.add_relation(
                    statement["id"],
                    "belongsToInvestigation",
                    package["id"],
                    statement["evidence_ids"],
                )
            for rel in package["relations"]:
                if (
                    rel["subject"] == target
                    and not store.registry.relations[rel["relation"]].domain
                ):
                    store.add_relation(
                        statement["id"],
                        rel["relation"],
                        rel["object"],
                        statement["evidence_ids"] + rel["evidence_ids"],
                    )
    for rel in package["relations"]:
        if rel["subject"] not in excluded and rel["object"] not in excluded:
            store.add_relation(rel["subject"], rel["relation"], rel["object"], rel["evidence_ids"])
    prov = Namespace("http://www.w3.org/ns/prov#")
    for entity in package["entities"]:
        if entity["id"] not in excluded:
            for eid in entity["evidence_ids"]:
                store.graph.add(
                    (node(entity["id"]), prov.wasDerivedFrom, node(refs[eid]["document_id"]))
                )


def project_active(store, registry, root=None):
    tables = {
        r[0] for r in registry.db.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    if "research_active" not in tables:
        return
    rows = list(
        registry.db.execute(
            "SELECT a.digest,p.receipt FROM research_active a JOIN research_publications p USING(digest) ORDER BY a.package_id"
        )
    )
    root = root or Path(registry.db.execute("PRAGMA database_list").fetchone()[2]).parents[2]
    for row in rows:
        receipt = json.loads(row["receipt"])
        graph_file = root / receipt["graph_path"]
        data = graph_file.read_bytes()
        if hashlib.sha256(data).hexdigest() != receipt["graph_sha256"]:
            raise ValueError("Active scientific RDF checksum mismatch")
        approved = Graph().parse(data=data, format="nt")
        contracts = []
        for payload in approved.objects(None, NS.payload):
            contract = json.loads(str(payload)).get("ontology_contract")
            if contract:
                contracts.append(contract)
        # Classes before relation contracts; persisted metadata supplies ancestry.
        for contract in sorted(contracts, key=lambda c: c["kind"] != "class"):
            activate_extension(store, contract)
        for term in approved.subjects(RDF.type, OWL.DatatypeProperty):
            payload = approved.value(term, NS.payload)
            if payload:
                contract = json.loads(str(payload)).get("quantity_contract")
                if contract:
                    definition = PropertyDefinition(**contract)
                    existing = store.registry.properties.get(definition.property_id)
                    if existing and existing != definition:
                        raise ValueError("Active ontology contracts conflict")
                    store.registry.register(definition)
        store.graph += approved
        store.registry.entities.update(store.entities())
        for entity in approved.subjects(RDF.type, node("Investigation")):
            payload = json.loads(str(approved.value(entity, NS.payload)))
            from nasa_fire_ai.query.native import identity

            eid = identity(entity)
            store.registry.entity_mentions = getattr(store.registry, "entity_mentions", {})
            store.registry.entity_mentions[eid] = {
                "relation": "belongsToInvestigation",
                "aliases": [payload["label"]],
            }
