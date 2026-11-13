"""Bounded, read-only research views of the existing scientific store.

No new facts or graph edges are inferred. Study-level feature inventories say
that a study contains source records with a property, never that every run has it.
"""

import json
from collections import Counter

from nasa_fire_ai.query.native import NS, canonical_record, identity, node

FEATURE_RELATIONS = (
    "belongsToExperimentFamily",
    "hasMaterial",
    "hasMaterialDescription",
    "hasPhenomenon",
    "hasGravityCondition",
    "usesApparatus",
    "usesInstrument",
    "hasDocumentedMethod",
)
PRIORITY = (
    "usesApparatus",
    "hasInstrument",
    "usesInstrument",
    "hasReportedFinding",
    "hasDocumentedMethod",
    "hasObjective",
    "hasHypothesis",
    *FEATURE_RELATIONS,
    "hasDocumentation",
    "belongsToInvestigation",
    "hasInvestigation",
)


def label(store, subject):
    payload = store.payload(subject)
    text = payload.get("text", "")
    if isinstance(text, str) and text.lstrip().startswith("{"):
        text = ""
    aliases = store.registry.entity_mentions.get(subject, {}).get("aliases", [])
    return (
        payload.get("title")
        or payload.get("reported_identifier")
        or text
        or payload.get("qualifiers", {}).get("source_header")
        or next(iter(aliases), None)
        or "Registered " + ", ".join(sorted(store.classes(subject)))
    )


def card(search, subject):
    if subject not in search.store.registry.entities:
        raise LookupError(subject)
    payload = search.store.payload(subject)
    result = {
        "id": subject,
        "title": str(label(search.store, subject)),
        "classes": sorted(search.store.classes(subject)),
        **{
            k: payload[k]
            for k in (
                "text",
                "reported_identifier",
                "instrument_attributes",
                "property_id",
                "value",
                "qualifiers",
            )
            if k in payload
        },
        "evidence_ids": search.store.evidence(subject),
    }
    text = payload.get("text", "")
    if isinstance(text, str) and text.lstrip().startswith("{"):
        try:
            fields = json.loads(text)
        except ValueError:
            fields = {}
        result.pop("text", None)
        result["source_fields"] = (
            [
                {"label": key, "value": value}
                for key, value in fields.items()
                if isinstance(value, (str, int, float))
            ]
            if isinstance(fields, dict)
            else []
        )
        if not payload.get("title") and not payload.get("reported_identifier"):
            original = (
                search.registry.resolve(result["evidence_ids"][0]) if result["evidence_ids"] else {}
            )
            ordinal = (original or {}).get("structured_location", {}).get("row_ordinal")
            result["title"] = f"Source row {ordinal}" if ordinal else "Source record"
    return result


def relation_edges(search, subject):
    store = search.store
    graph = store.graph
    records = set(graph.subjects(NS.subject, node(subject))) | set(
        graph.subjects(NS.object, node(subject))
    )
    edges = []
    for record in records:
        if not canonical_record(graph, record):
            continue
        relation = graph.value(record, NS.relation)
        if relation is None:
            continue
        rel = identity(relation)
        meta = store.registry.relations.get(rel)
        if meta is None or meta.status != "CANONICAL":
            continue
        left, right = graph.value(record, NS.subject), graph.value(record, NS.object)
        if left is None or right is None:
            continue
        refs = sorted(str(e) for e in graph.objects(record, NS.evidenceRef))
        if not refs or any(search.registry.resolve(e) is None for e in refs):
            continue
        edges.append(
            {
                "from": identity(left),
                "to": identity(right),
                "relation": rel,
                "evidence_ids": refs,
                "classification": "RELATED",
                "semantics": "Registered association; not causality or experimental equivalence",
            }
        )
    return sorted(
        edges,
        key=lambda e: (
            PRIORITY.index(e["relation"]) if e["relation"] in PRIORITY else len(PRIORITY),
            e["relation"],
            e["from"],
            e["to"],
        ),
    )


class ResearchConsole:
    def __init__(self, search):
        self.search = search
        self.store = search.store
        self._profiles = None

    def profiles(self):
        if self._profiles is not None:
            return self._profiles
        profiles = {}
        for subject in self.store.entities():
            if "Investigation" not in self.store.classes(subject):
                continue
            records = self.search._investigation_records(subject)
            features = {r: {} for r in FEATURE_RELATIONS if r in self.store.registry.relations}
            properties, classes = Counter(), Counter()
            for owner in [subject, *sorted(records)]:
                classes.update(self.store.classes(owner) if owner != subject else [])
                for record in self.store.graph.subjects(NS.subject, node(owner)):
                    if not canonical_record(self.store.graph, record):
                        continue
                    rel_node = self.store.graph.value(record, NS.relation)
                    pid = self.store.graph.value(record, NS.measuredProperty)
                    if pid is not None:
                        properties[identity(pid)] += 1
                    if rel_node is None or identity(rel_node) not in features:
                        continue
                    rel = identity(rel_node)
                    for target in self.store.graph.objects(record, NS.object):
                        target_id = identity(target)
                        refs = sorted(
                            str(e) for e in self.store.graph.objects(record, NS.evidenceRef)
                        )
                        if not refs or any(self.search.registry.resolve(e) is None for e in refs):
                            continue
                        features[rel].setdefault(
                            target_id,
                            {
                                **card(self.search, target_id),
                                "relation": rel,
                                "scope_subject": owner,
                                "scope_label": card(self.search, owner)["title"],
                                "association_evidence_ids": refs,
                            },
                        )
                for rel in ("hasCondition", "hasMeasurement", "hasRecordedField"):
                    for value_id in self.store.relations(owner, rel):
                        payload = self.store.payload(value_id)
                        if pid := payload.get("property_id"):
                            properties[pid] += 1
            profiles[subject] = {
                **card(self.search, subject),
                "record_count": len(records),
                "record_classes": dict(classes),
                "properties": sorted(properties),
                "features": {r: list(values.values()) for r, values in features.items()},
                "measurement_count": sum(
                    len(self.store.relations(record, "hasMeasurement")) for record in records
                ),
                "scope": "Inventory of documented records; conditions are not inherited by every run.",
            }
        self._profiles = profiles
        return profiles

    def summary(self):
        profiles = self.profiles()
        facets = {r: {} for r in FEATURE_RELATIONS}
        for profile in profiles.values():
            for rel, values in profile["features"].items():
                for value in values:
                    title = value["title"]
                    if rel == "hasDocumentedMethod":
                        description = " ".join(str(value.get("text") or title).split())
                        title = f"{profile['id'].upper()} · {description[:160]}"
                    facets[rel][value["id"]] = {"id": value["id"], "title": title}
        definitions = self.store.registry.properties
        sources = self.search.manifest["sources"]
        return {
            "investigations": len(profiles),
            "source_records": sum(p["record_count"] for p in profiles.values()),
            "measurements": sum(p["measurement_count"] for p in profiles.values()),
            "registered_sources": len(sources),
            "facets": {
                r: sorted(
                    {
                        str(item["title"]).casefold(): {"id": item["title"], "title": item["title"]}
                        for item in v.values()
                    }.values(),
                    key=lambda x: x["title"],
                )
                if r == "hasMaterialDescription"
                else sorted(v.values(), key=lambda x: x["title"])
                for r, v in facets.items()
            },
            "properties": [
                {
                    "id": pid,
                    "label": (meta.aliases or [pid])[0],
                    "unit": meta.canonical_unit,
                    "dimension": meta.dimension,
                    "datatype": meta.datatype,
                }
                for pid, meta in definitions.items()
            ],
            "relation_options": [
                key
                for key, meta in self.store.registry.relations.items()
                if meta.status == "CANONICAL"
            ],
            "record_classes": sorted({c for p in profiles.values() for c in p["record_classes"]}),
            "scope": "Counts describe this registered library, not all NASA research.",
        }

    def investigations(
        self,
        *,
        query="",
        family=None,
        material=None,
        instrument=None,
        method=None,
        property_id=None,
        record_class=None,
        measurements=False,
        offset=0,
        limit=20,
    ):
        matches = []
        for profile in self.profiles().values():
            features = profile["features"]
            if (
                query
                and query.casefold() not in (profile["id"] + " " + profile["title"]).casefold()
            ):
                aliases = self.store.registry.entity_mentions.get(profile["id"], {}).get(
                    "aliases", []
                )
                if not any(query.casefold() in a.casefold() for a in aliases):
                    continue
            if family and family not in {
                v["id"] for v in features.get("belongsToExperimentFamily", [])
            }:
                continue
            if material and not any(
                material == v["id"] or material.casefold() == str(v["title"]).casefold()
                for rel in ("hasMaterial", "hasMaterialDescription")
                for v in features.get(rel, [])
            ):
                continue
            if instrument and instrument not in {
                v["id"] for v in features.get("usesInstrument", [])
            }:
                continue
            if method and method not in {v["id"] for v in features.get("hasDocumentedMethod", [])}:
                continue
            if property_id and property_id not in profile["properties"]:
                continue
            if record_class and record_class not in profile["record_classes"]:
                continue
            if measurements and not profile["measurement_count"]:
                continue
            matches.append(profile)
        matches.sort(key=lambda p: p["title"])
        return {
            "items": [self.compact(p) for p in matches[offset : offset + limit]],
            "total": len(matches),
            "offset": offset,
            "limit": limit,
        }

    @staticmethod
    def compact(profile):
        return {
            **profile,
            "evidence_ids": profile["evidence_ids"][:8],
            "features": {r: values[:12] for r, values in profile["features"].items()},
        }

    def investigation(self, subject):
        profile = self.profiles().get(subject)
        if profile is None:
            raise LookupError(subject)
        sections = []
        for rel in self.store.registry.relations:
            if rel in ("hasRun", "hasSourceRecord"):
                continue
            targets = sorted(self.store.relations(subject, rel))
            if not targets:
                continue
            items = []
            for target in targets[:24]:
                item = card(self.search, target)
                if "Apparatus" in item["classes"]:
                    item["instruments"] = [
                        card(self.search, i)
                        for i in sorted(self.store.relations(target, "hasInstrument"))
                    ]
                items.append(item)
            sections.append({"relation": rel, "items": items, "total": len(targets)})
        return {
            **self.compact(profile),
            "sections": sections,
            "sources": sorted(self.store.sources(subject)),
            "related": self.related(subject),
        }

    def related(self, subject):
        profiles = self.profiles()
        if subject not in profiles:
            raise LookupError(subject)
        result = []
        source = profiles[subject]
        for other, profile in profiles.items():
            if other == subject:
                continue
            shared = []
            for rel in FEATURE_RELATIONS:
                left = {v["id"]: v for v in source["features"].get(rel, [])}
                right = {v["id"]: v for v in profile["features"].get(rel, [])}
                for target in sorted(left.keys() & right.keys()):
                    shared.append(
                        {
                            "relation": rel,
                            "entity": card(self.search, target),
                            "left_scope": left[target]["scope_subject"],
                            "right_scope": right[target]["scope_subject"],
                            "evidence_ids": sorted(
                                set(
                                    left[target]["association_evidence_ids"]
                                    + right[target]["association_evidence_ids"]
                                )
                            ),
                        }
                    )
            if shared:
                result.append(
                    {
                        "id": other,
                        "title": profile["title"],
                        "classification": "RELATED",
                        "shared": shared,
                        "reason": "Shares registered entities; this does not establish equivalent experimental conditions.",
                    }
                )
        return sorted(result, key=lambda r: (-len(r["shared"]), r["title"]))[:12]

    def neighbors(self, subject, *, offset=0, limit=20, relation=None):
        center = card(self.search, subject)
        edges = relation_edges(self.search, subject)
        if relation:
            if relation not in self.store.registry.relations:
                raise ValueError("Unregistered relation")
            edges = [e for e in edges if e["relation"] == relation]
        selected = edges[offset : offset + limit]
        ids = sorted({subject} | {e[k] for e in selected for k in ("from", "to")})
        return {
            "center": center,
            "nodes": [card(self.search, i) for i in ids],
            "edges": selected,
            "total": len(edges),
            "offset": offset,
            "limit": limit,
        }

    def compare(self, subjects, dimensions=None):
        if len(set(subjects)) != len(subjects):
            raise ValueError("Distinct investigations required")
        profiles = self.profiles()
        if any(s not in profiles for s in subjects):
            raise LookupError("Unknown investigation")
        dimensions = dimensions or list(FEATURE_RELATIONS)
        if any(
            d not in FEATURE_RELATIONS or d not in self.store.registry.relations for d in dimensions
        ):
            raise ValueError("Unregistered investigation feature")
        rows = []
        for dimension in dimensions:
            values = {s: profiles[s]["features"].get(dimension, []) for s in subjects}
            sets = [{v["id"] for v in value} for value in values.values()]
            shared = set.intersection(*sets)
            status = (
                "UNAVAILABLE"
                if not any(sets)
                else "PARTIAL"
                if not all(sets)
                else "SHARED"
                if shared
                else "DISTINCT_ENTRIES"
            )
            rows.append(
                {
                    "dimension": dimension,
                    "status": status,
                    "shared": [card(self.search, i) for i in sorted(shared)],
                    "values": {s: rows[:24] for s, rows in values.items()},
                    "value_counts": {s: len(rows) for s, rows in values.items()},
                    "limits": "Source-record inventories, not universal study conditions. Distinct entries do not prove different physical composition. Shared entities do not establish experimental equivalence.",
                }
            )
        return {
            "subjects": [card(self.search, s) for s in subjects],
            "rows": rows,
            "dimensions": [r for r in FEATURE_RELATIONS if r in self.store.registry.relations],
        }
