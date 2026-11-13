"""Re-examine fields of already represented source records, preserving row scope."""

from nasa_fire_ai.ingestion.scientific_facets import REPORTED_QUANTITY_ROLE
from nasa_fire_ai.services.structured_facts import record_scope_fact, structured_fact


def record_subjects(results, question):
    """Explicit record focus, with broader comparison requests kept exploratory."""
    import re

    if re.search(
        r"\b(?:other|remaining|all other|across all)\s+(?:(?:source|experimental|physical)\s+)?(?:records?|runs?|samples?|sessions?|entries|experiments?|investigations?|studies|tests?(?!\s+(?:numbers?|identifiers?|codes?|labels?)))\b",
        question,
        re.IGNORECASE,
    ):
        return set()
    return {
        subject
        for result in results
        for subject in getattr(getattr(result, "intent", None), "subject_ids", [])
    }


def record_anchor_allowed(anchor, search, subjects, investigations=None):
    """A table-wide definition cannot lend another row's experimental values."""
    if not getattr(search, "store", None):
        return True
    from nasa_fire_ai.services.semantic_support import unstructured_numeric_table

    if subjects and unstructured_numeric_table(anchor):
        return False
    rid = anchor.get("structured_record_id")
    if rid:
        record = search.store.payload(rid)
        owner = record.get("subject") or rid
        annotation_targets = (
            search.store.relations(owner, "referencesSourceRecord")
            if hasattr(search.store, "relations")
            else set()
        )
        if annotation_targets:
            if subjects and set(subjects).isdisjoint(annotation_targets):
                return False
            return not (
                investigations
                and set(investigations).isdisjoint(
                    search.store.relations(owner, "belongsToInvestigation")
                )
            )
        if record.get("qualifiers", {}).get("scientific_role") == "source_field_definition":
            owner = record.get("subject") or rid
            if investigations:
                ownership = set(search.store.relations(owner, "belongsToInvestigation")) | {owner}
                if set(investigations).isdisjoint(ownership):
                    return False
            if not subjects:
                return True
            definition_sources = set(search.store.sources(rid)) | set(search.store.sources(owner))
            focused_sources = {
                source for subject in subjects for source in search.store.sources(subject)
            }
            if definition_sources and focused_sources:
                return bool(definition_sources & focused_sources)
            definition_investigations = set(search.store.relations(owner, "belongsToInvestigation"))
            focused_investigations = {
                inv
                for subject in subjects
                for inv in search.store.relations(subject, "belongsToInvestigation")
            }
            return bool(definition_investigations & focused_investigations)
        return not subjects or rid in subjects or record.get("subject") in subjects
    if not subjects:
        return True
    eids = {span["evidence_id"] for span in anchor.get("spans", [])}
    if anchor.get("typed_fields"):
        return any(eids & set(search.store.evidence(subject)) for subject in subjects)
    return True


def field_is_communicated(fact, record, statements, definitions, entailment):
    """Check actual field meaning/value in text tied to its original row.

    Same-valued fields and different records cannot certify one another. The
    source row and field identity only establish alignment; textual entailment
    of the field/value proposition remains necessary.
    """
    import re

    from nasa_fire_ai.services.semantic_support import aligned_properties

    pid = fact.get("property_id") or record.get("property_id")
    qualifiers = record.get("qualifiers", {})
    context = qualifiers.get("context")
    header = " ".join(re.findall(r"[a-z0-9]+", qualifiers.get("source_header", "").lower()))
    primary = set(fact.get("primary_evidence_ids") or fact.get("evidence_ids", [])[:1])
    for statement in statements:
        text = str(statement.get("text") or "")
        if " ".join(text.split()) == " ".join(fact["text"].split()):
            return True
        if not primary & set(statement.get("evidence_ids", [])):
            continue
        surface = " ".join(re.findall(r"[a-z0-9]+", text.lower()))
        named = pid in aligned_properties(text, definitions) or bool(
            header and re.search(r"(?<!\w)" + re.escape(header) + r"(?!\w)", surface)
        )
        if not named:
            continue
        phase_terms = {"initial": r"\b(?:initial|before)\b", "final": r"\b(?:final|after)\b"}
        if context in phase_terms and not re.search(phase_terms[context], text, re.IGNORECASE):
            continue
        if entailment and entailment.check(
            text, fact.get("field_text") or fact.get("core_text", fact["text"])
        ).get("supported"):
            return True
    return False


def field_property_id(record):
    """A literal unresolved value retains its curated variable, not a numeric value."""
    return record.get("qualifiers", {}).get("intended_property") or record.get("property_id")


def record_need_text(phrase, store, subjects):
    """Separate a trailing record locator from the requested scientific fields."""
    import re

    for subject in subjects:
        label = str(store.payload(subject).get("reported_identifier") or "")
        if not label:
            continue
        starts = [
            match.start() for match in re.finditer(r"\s+(?:for|of|in)\s+", phrase, re.IGNORECASE)
        ]
        for start in reversed(starts):
            if re.fullmatch(
                r"\s+(?:for|of|in)\s+[^.!?]*?(?<!\w)" + re.escape(label) + r"(?!\w)[.!?\s]*",
                phrase[start:],
                re.IGNORECASE,
            ):
                return phrase[:start]
    return phrase


def missing_record_fields(question, search, subjects):
    """Report only the result of a selected-record lookup, never corpus absence.

    Inspect all registered fields, including literal unresolved quantities. A
    partial retrieval window is insufficient to decide whether a field exists.
    """
    store = getattr(search, "store", None)
    if store is None:
        return []
    definitions = store.registry.properties
    requested = route_need_properties(record_need_text(question, store, subjects), definitions)
    requested = {pid for pid in requested if definitions[pid].datatype == "numeric"}
    boundaries = []
    for subject in sorted(subjects):
        if not store.evidence(subject):
            continue
        fields = {
            rid
            for relation in ("hasCondition", "hasMeasurement", "hasRecordedField")
            for rid in store.relations(subject, relation)
        }
        if not fields:
            continue
        available = {field_property_id(store.payload(rid)) for rid in fields}
        absent = requested - available
        # A broad alias can name several curated properties. If one is present,
        # do not call that alias unavailable on account of its other meanings.
        present_aliases = {
            alias.casefold() for pid in requested & available for alias in definitions[pid].aliases
        }
        aliases = sorted(
            {
                alias
                for pid in absent
                for alias in definitions[pid].aliases
                if alias.casefold() in question.casefold()
                and alias.casefold() not in present_aliases
            },
            key=lambda alias: (-len(alias), alias),
        )
        selected = []
        for alias in aliases:
            if not any(alias.casefold() in other.casefold() for other in selected):
                selected.append(alias)
        label = store.payload(subject).get("reported_identifier") or subject
        for alias in selected:
            boundaries.append(
                {
                    "kind": "registered_record_lookup",
                    "source_record_ids": [subject],
                    "property_ids": sorted(
                        pid for pid in absent if alias in definitions[pid].aliases
                    ),
                    "text": f"For selected source record {label}, the registered lookup did not yield a verified {alias} value.",
                    "boundary": "Selected registered record only; not a NASA finding or a claim that NASA lacks evidence",
                }
            )
    return boundaries


def source_field_roles(search):
    """Read the already curated variable facets; these only route candidates."""
    from functools import lru_cache
    from pathlib import Path

    import yaml

    @lru_cache(maxsize=8)
    def load(root):
        roles = {}
        accessor = Path(root) / "domain/source_field_accessors.yaml"
        if accessor.exists():
            for key, metadata in yaml.safe_load(accessor.read_text())["fields"].items():
                roles.setdefault("source:" + key, set()).add(metadata.get("role", "").upper())
        return roles

    root = getattr(search, "root", None)
    if root is None:
        return {}
    # Keep the cache on this function, independently of request lifetime.
    if not hasattr(source_field_roles, "_load"):
        source_field_roles._load = load
    return source_field_roles._load(str(root))


def route_need_properties(phrase, definitions, *, field_roles=None, available_properties=None):
    """Field-candidate routing only. Coverage still requires communicated facts."""
    import re

    import snowballstemmer

    stemmer = snowballstemmer.stemmer("english")
    generic = {
        "record",
        "report",
        "original",
        "entry",
        "label",
        "value",
        "source",
        "table",
        "condition",
        "number",
    }

    def tokens(text):
        text = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", text)
        return stemmer.stemWords(re.findall(r"[a-z][a-z0-9]*", text.lower()))

    requested = tokens(phrase)
    matched = set()
    # A source's declared specimen-characteristic facet supplies dimensions,
    # while measured flame/extinction lengths remain separate outcomes.
    if re.search(r"\b(?:specimen|sample|droplet)s?\b", phrase, re.IGNORECASE) and re.search(
        r"\b(?:dimensions?|geometr(?:y|ies))\b", phrase, re.IGNORECASE
    ):
        geometric = {
            pid
            for pid, roles in (field_roles or {}).items()
            if pid in definitions
            and definitions[pid].dimension == "length"
            and any(role.endswith("SPECIMEN_CHARACTERISTIC") for role in roles)
        }
        # A generic facet asks for this source's available dimensions, not the
        # geometry of unrelated experimental families. An empty intersection
        # remains unresolved rather than silently satisfying the request.
        if available_properties is not None and geometric & available_properties:
            geometric &= available_properties
        matched.update(geometric)
    candidates = []
    for pid, definition in definitions.items():
        for alias in definition.aliases:
            if (
                "#" in alias
                and "#" not in phrase
                and not re.search(r"\b(?:number|identifier|counter|id)\b", phrase, re.IGNORECASE)
            ):
                continue
            # Parenthetical units and printed footnote markers describe a field;
            # they need not occur in an unfamiliar natural-language question.
            variants = [alias, re.sub(r"\([^)]*\)|\[[^]]*\]", " ", alias)]
            for variant in variants:
                words = tokens(variant)
                if not words or (len(words) == 1 and words[0] in generic):
                    continue
                for i in range(len(requested) - len(words) + 1):
                    if requested[i : i + len(words)] == words:
                        candidates.append((i, i + len(words), pid))
    occupied = []
    for start, end, pid in sorted(candidates, key=lambda item: -(item[1] - item[0])):
        if any(
            left <= start and right >= end and (left, right) != (start, end)
            for left, right in occupied
        ):
            continue
        occupied.append((start, end))
        matched.add(pid)
    return matched


def complete_record_fields(needs, inventory, search, accepted, subjects, entailment):
    """Route missing needs to exact source cells; routing never certifies coverage.

    Only already scoped records contribute. Every proposed sentence must still
    pass the production renderer/provenance verifier before reaching the answer.
    """
    import re

    if not getattr(search, "store", None) or entailment is None:
        return []
    store = search.store
    subjects = set(subjects or [])
    if not subjects:
        for statement in accepted:
            for sid in statement.get("support_ids", []):
                rid = inventory.get(sid, {}).get("structured_record_id")
                if rid:
                    subject = (
                        rid
                        if inventory[sid].get("projection_kind") == "record_scope"
                        else store.payload(rid).get("subject")
                    )
                    if subject:
                        subjects.add(subject)
    if not subjects:
        return []
    expand_source_fields(inventory, search, subjects)
    definitions = store.registry.properties
    proposals, seen, size = [], set(), 0
    for index, need in enumerate(needs):
        phrase = str(need.get("need") or "")
        if re.search(
            r"\b(?:why|how|caus\w*|mean\w*|defin\w*|interpret\w*|compar\w*|whether|uncertain\w*|methods?|objectives?)\b",
            phrase,
            re.IGNORECASE,
        ):
            continue
        available = {
            field_property_id(store.payload(a["structured_record_id"]))
            for a in inventory.values()
            if a.get("structured_record_id")
            and store.payload(a["structured_record_id"]).get("subject") in subjects
        }
        wanted = route_need_properties(
            record_need_text(phrase, store, subjects),
            definitions,
            field_roles=source_field_roles(search),
            available_properties=available,
        )
        phases = {
            phase
            for phase in ("initial", "final")
            if re.search(r"\b" + phase + r"\b", phrase, re.IGNORECASE)
        }
        for anchor in list(inventory.values()):
            rid = anchor.get("structured_record_id")
            if not rid or not anchor.get("deterministic_text"):
                continue
            record = store.payload(rid)
            if record.get("subject") not in subjects or field_property_id(record) not in wanted:
                continue
            context = record.get("qualifiers", {}).get("context")
            if phases and context in {"initial", "final"} and context not in phases:
                continue
            fact = structured_fact(rid, store, search.registry)
            if not fact or fact["text"] in seen:
                continue
            if field_is_communicated(fact, record, accepted, definitions, entailment):
                continue
            if len(proposals) >= 12 or size + len(fact["text"]) > 6000:
                return proposals
            proposals.append(
                {
                    "text": fact["text"],
                    "support_ids": [anchor["support_id"]],
                    "repair_of": f"coverage-source-{index}",
                }
            )
            seen.add(fact["text"])
            size += len(fact["text"])
    return proposals


def expand_source_fields(
    inventory, search, subjects=None, *, definitions_only=False, investigations=None
):
    """Expose typed alternatives from the same original rows, never another run."""
    if not getattr(search, "store", None) or not getattr(search.registry, "db", None):
        return 0
    if not search.registry.db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='value_cells'"
    ).fetchone():
        return 0
    eligible = []
    for anchor in inventory.values():
        if anchor.get("projection_verified") and anchor.get("structured_record_id"):
            renderer = (
                record_scope_fact
                if anchor.get("projection_kind") == "record_scope"
                else structured_fact
            )
            proof = renderer(anchor["structured_record_id"], search.store, search.registry)
            if not proof or proof["text"] != anchor.get("deterministic_text"):
                continue
            if proof.get("role") == "source_field_definition":
                anchor["definition_scope"] = "same_original_table"
                anchor["source_roles"] = sorted(
                    set(anchor.get("source_roles", [])) | {"SourceFieldDefinition"}
                )
                anchor["spans"] = [proof["primary_span"], *proof.get("definition_spans", [])]
                anchor["typed_fields"] = [
                    field
                    for field in anchor.get("typed_fields", [])
                    if field["id"] == anchor["structured_record_id"]
                ]
        eligible.append(anchor)
    context_eids = {span["evidence_id"] for anchor in eligible for span in anchor.get("spans", [])}
    eids = {
        span["evidence_id"]
        for anchor in eligible
        for span in anchor.get("spans", [])
        if span.get("scope")
        not in {
            "table_field_definition",
            "section_heading",
            "source_local_name_definition",
            "source_subject_context",
            "source_record_heading",
            "source_record_annotation",
        }
        and anchor.get("definition_scope") != "same_original_table"
    }
    original_eids = set(eids)
    source_documents = {
        source["document_id"] for eid in context_eids if (source := search.registry.resolve(eid))
    }
    for investigation in investigations or []:
        for relation in ("hasSourceRecord", "hasRun"):
            for record in search.store.relations(investigation, relation):
                source_documents.update(search.store.sources(record))
    # These are curator-classified table field definitions, not conditions of
    # their carrier row. Navigate the same original source to recover them
    # without borrowing the carrier row's experimental values.
    from rdflib import RDF

    from nasa_fire_ai.query.native import identity, node

    definition_ids = {}
    annotation_ids = {}
    focused = set(subjects or [])
    focused.update(
        search.store.payload(a.get("structured_record_id")).get("subject")
        for a in eligible
        if a.get("structured_record_id")
    )
    for record in focused - {None}:
        for annotation in search.store.relations(record, "hasSourceAnnotation"):
            for rid in search.store.relations(annotation, "hasRecordedField"):
                for eid in search.store.evidence(rid):
                    annotation_ids.setdefault(eid, set()).add(rid)
                    eids.add(eid)
    graph = getattr(search.store, "graph", None)
    candidates = (
        graph.subjects(RDF.type, node("SourceFieldDefinition")) if graph is not None else []
    )
    for candidate in candidates:
        rid = identity(candidate)
        if not source_documents & set(search.store.sources(rid)):
            continue
        if (
            search.store.payload(rid).get("qualifiers", {}).get("scientific_role")
            != "source_field_definition"
        ):
            continue
        for eid in search.store.evidence(rid):
            definition_ids.setdefault(eid, set()).add(rid)
            eids.add(eid)
    additions = {}
    for eid in eids:
        source = search.registry.resolve(eid)
        if not source or not source.get("source_cells"):
            continue
        metadata = search.registry.source_metadata(eid) or {}
        row_fields = []
        for linked in search.registry.db.execute(
            "SELECT value_id FROM value_cells WHERE evidence_id=?", (eid,)
        ):
            payload = search.store.payload(linked[0])
            definition = search.store.registry.properties.get(payload.get("property_id"))
            if definition:
                row_fields.append(
                    {
                        "id": linked[0],
                        "property_id": payload["property_id"],
                        "aliases": definition.aliases,
                        "role": payload.get("qualifiers", {}).get("scientific_role"),
                        "value": payload.get("value"),
                    }
                )
        for cell in search.registry.db.execute(
            "SELECT value_id FROM value_cells WHERE evidence_id=?", (eid,)
        ):
            rid = cell[0]
            contextual = definition_ids.get(eid, set()) | annotation_ids.get(eid, set())
            if definitions_only and rid not in contextual:
                continue
            if eid not in original_eids and rid not in contextual:
                continue
            key = "value-" + rid
            if key in inventory or key in additions:
                continue
            fact = structured_fact(rid, search.store, search.registry)
            if not fact:
                continue
            record = search.store.payload(rid)
            if (
                subjects
                and record.get("subject") not in subjects
                and record.get("qualifiers", {}).get("scientific_role") != "source_field_definition"
                and rid not in annotation_ids.get(eid, set())
            ):
                continue
            additions[key] = {
                "support_id": key,
                "text": fact["text"],
                "deterministic_text": fact["text"],
                "verified_context": fact["text"],
                "structured_record_id": rid,
                "subject": fact["subject"],
                "category": "DOCUMENTARY",
                "epistemic_type": REPORTED_QUANTITY_ROLE,
                "projection_verified": True,
                "document_id": source["document_id"],
                "source_id": metadata.get("source_id"),
                "source_title": metadata.get("title"),
                "conditions": [],
                "required_scope": [],
                "spans": [
                    fact.get("primary_span") or {"evidence_id": eid, "text": source["text"]},
                    *fact.get("definition_spans", []),
                ],
                "identity_context": "Registered identity: "
                + str(metadata.get("title") or metadata.get("source_id"))
                + "; aliases: "
                + ", ".join(
                    search.store.registry.entity_mentions.get(metadata.get("source_id"), {}).get(
                        "aliases", []
                    )
                ),
                "typed_fields": [field for field in row_fields if field["id"] == rid]
                if record.get("qualifiers", {}).get("scientific_role") == "source_field_definition"
                else row_fields,
                "examination_role": "same_original_table_field_definition"
                if record.get("qualifiers", {}).get("scientific_role") == "source_field_definition"
                else "same_source_record_field_reexamination",
            }
            definition = (
                record.get("qualifiers", {}).get("scientific_role") == "source_field_definition"
            )
            if definition:
                additions[key]["source_roles"] = ["SourceFieldDefinition"]
                additions[key]["definition_scope"] = "same_original_table"
            if rid in annotation_ids.get(eid, set()):
                additions[key]["source_roles"] = ["SourceAnnotation"]
                additions[key]["annotation_record_ids"] = sorted(
                    search.store.relations(record["subject"], "referencesSourceRecord")
                )
                additions[key]["annotation_reference_scope"] = search.store.payload(
                    record["subject"]
                ).get("reference_scope", [])
            scope = (
                None
                if definition
                else record_scope_fact(record["subject"], search.store, search.registry)
            )
            scope_key = "scope-" + record["subject"]
            if (
                scope
                and scope_key not in inventory
                and (not subjects or record["subject"] in subjects)
            ):
                additions[scope_key] = {
                    **additions[key],
                    "support_id": scope_key,
                    "text": scope["text"],
                    "deterministic_text": scope["text"],
                    "verified_context": scope["text"],
                    "structured_record_id": record["subject"],
                    "projection_kind": "record_scope",
                    "typed_fields": [],
                }
    inventory.update(additions)
    return len(additions)
