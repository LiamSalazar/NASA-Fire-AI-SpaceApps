"""Stable, credential-free consultation boundary over an immutable native snapshot."""

import re
from pathlib import Path
from time import perf_counter
from typing import Literal

import yaml
from pydantic import BaseModel, Field
from rdflib import RDF, Graph

from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.hackathon import TABLES, make_store, verify_snapshot
from nasa_fire_ai.ingestion.psi_scientific import mappings
from nasa_fire_ai.query.native import NS, execute_native, identity, measurement_scope, node
from nasa_fire_ai.query.native_interpreter import resolve_minimal
from nasa_fire_ai.query.numeric_mentions import (
    DeterministicMinimalInterpreter,
    literal_numeric_mentions,
)
from nasa_fire_ai.query.ontology_navigation import RouteStep, navigate
from nasa_fire_ai.query.v2 import QueryIntentV2, evaluate_constraint


def is_publication_metadata(source_type):
    source_type = (source_type or "").casefold()
    return "publication" in source_type and "metadata" in source_type


def publication_metadata_weight(query, source_type):
    """Titles/citations route discovery; content questions need original content.

    General source-authority rule motivated by publication-list expansion: an
    indexed bibliography must not displace full scientific evidence. Explicit
    bibliographic questions retain normal metadata ranking. No fact is certified.
    """
    metadata = is_publication_metadata(source_type)
    bibliographic = re.search(
        r"\b(?:publications?|citations?|references?|bibliograph\w*|authors?|doi)\b",
        query,
        re.IGNORECASE,
    )
    return 0.3 if metadata and not bibliographic else 1.0


class SearchResult(BaseModel):
    schema_version: str = "scientific-search-v1"
    snapshot_id: str
    intent: QueryIntentV2
    direct: list[dict] = Field(default_factory=list)
    related: list[dict] = Field(default_factory=list)
    discovery: list[dict] = Field(default_factory=list)
    documentary: list[dict] = Field(default_factory=list)
    candidates: list[dict] = Field(default_factory=list)
    continuation: dict = Field(default_factory=dict)
    comparison: dict | None = None
    claims: list[dict] = Field(default_factory=list)
    verification: list[dict] = Field(default_factory=list)
    provider: dict = Field(default_factory=lambda: {"status": "NOT_REQUESTED"})
    investigation: dict = Field(default_factory=dict)
    sufficiency: Literal["DIRECT_EVIDENCE", "NO_DIRECT_EVIDENCE"]
    limitations: list[str] = Field(default_factory=list)
    metrics: dict = Field(default_factory=dict)


def words(text):
    return set(re.findall(r"[\w-]+", text.casefold()))


class ScientificSearchService:
    """Uses QueryIntentV2, native execution, approved relations and EvidenceRegistry.

    No provider is constructed, and no environment flags are modified. Unknown text
    is retained as uncertainty instead of silently disappearing from eligibility.
    """

    def __init__(
        self,
        snapshot: Path,
        root: Path | None = None,
        *,
        interpreter=None,
        selector=None,
        semantic_verifier=None,
        candidate_limit=200,
        research_budget=None,
        research_planner=None,
        semantic_candidates=None,
    ):
        if not 20 <= candidate_limit <= 1000:
            raise ValueError("Candidate pool must be in 20..1000")
        self.candidate_limit = candidate_limit
        self.research_budget = research_budget
        self.research_planner = research_planner
        # Optional adapter over the existing LocalVectorIndex; never grants eligibility.
        self.semantic_candidates = semantic_candidates
        self.model_interpreter = interpreter
        self.selector = selector
        self.root = (root or Path(__file__).resolve().parents[3]).resolve()
        self.manifest = verify_snapshot(snapshot, self.root)
        self.store = make_store(self.root)
        self.store.graph = Graph().parse(snapshot / "graph.ttl")
        self.store.registry.entities.update(self.store.entities())
        self.store.registry.source_ids.update(row["source_id"] for row in self.manifest["sources"])
        self.store.registry.identifier_headers = sorted(
            {profile[0] for profile in TABLES.values()}
            | {
                profile["identifier"]
                for profile in mappings(self.root).values()
                if profile.get("identifier")
            }
            | {
                header
                for profile in mappings(self.root).values()
                for header, field in profile["fields"].items()
                if field.get("role") == "original_record_identifier"
            },
            key=len,
            reverse=True,
        )
        self.registry = EvidenceRegistry(
            snapshot / "evidence.sqlite", read_only=True, evidence_root=self.root
        )
        self.registry.scientific_properties = self.store.registry.properties
        self.registry.scientific_entities = self.store.registry.entity_mentions
        self.registry.scientific_instruments = {}
        for subject in self.store.graph.subjects(RDF.type, node("Instrument")):
            instrument = identity(subject)
            attributes = self.store.payload(instrument).get("instrument_attributes", {})
            if not attributes:
                continue
            if any(
                str(self.store.graph.value(subject, node(key))) != value
                for key, value in attributes.items()
            ):
                raise ValueError("Instrument description disagrees with its RDF attributes")
            for eid in self.store.evidence(instrument):
                self.registry.scientific_instruments.setdefault(eid, []).append(
                    {"id": instrument, "attributes": attributes}
                )
        self._corpus_terms = sorted(
            {
                word
                for row in self.registry.db.execute("SELECT text FROM passages")
                for word in re.findall(r"[A-Za-z]{4,}", row[0].lower())
            }
        )
        self.semantic_verifier = semantic_verifier
        if self.selector:
            self.selector.evidence_registry = self.registry
            self.selector.store = self.store
            self.selector.entailment = semantic_verifier
        self.language = yaml.safe_load((self.root / "domain/query_language_v2.yaml").read_text())
        self.depths = {row["source_id"]: row["depth"] for row in self.manifest["sources"]}
        # Campaign names come from the source catalogue, not query-specific dictionaries.
        import csv

        campaign_path = self.root / "data/raw/hackathon-team/data/clean/campaigns.csv"
        for row in csv.DictReader(campaign_path.open()):
            sid = row["accession"].lower()
            existing = self.store.registry.entity_mentions.get(sid, {}).get("aliases", [])
            self.store.registry.entity_mentions[sid] = {
                "relation": "belongsToInvestigation",
                "aliases": sorted(
                    {row["accession"], row["title"], row["campaign"], *existing} - {""}
                ),
            }
        from nasa_fire_ai.query.name_spellings import compound_spellings

        for sid, metadata in self.store.registry.entity_mentions.items():
            if metadata.get("relation") == "belongsToInvestigation":
                spellings = compound_spellings(
                    self.store.payload(sid).get("title", ""), metadata.get("aliases", [])
                )
                metadata["aliases"] = sorted(set(metadata.get("aliases", [])) | spellings)
        self.interpreter = DeterministicMinimalInterpreter(self.store.registry, self.language)
        self.source_scopes = {}
        self.evidence_subject_contexts = {}
        self.evidence_role_contexts = {}
        investigations = [
            subject
            for subject in self.store.entities()
            if "Investigation" in self.store.classes(subject)
        ]
        for investigation in investigations:
            subjects = {investigation}
            for relation in self.store.registry.relations:
                subjects.update(self.store.relations(investigation, relation))
            subjects.update(self._investigation_records(investigation))
            for subject in subjects:
                quote = self.store.payload(subject).get("text")
                for evidence_id in self.store.evidence(subject):
                    self.evidence_subject_contexts.setdefault(evidence_id, []).append(
                        (investigation, quote)
                    )
                    if quote:
                        self.evidence_role_contexts.setdefault(evidence_id, []).append(
                            (quote, sorted(self.store.classes(subject)))
                        )
                for source_id in self.store.sources(subject):
                    self.source_scopes.setdefault(source_id, set()).add(investigation)
        # Registered report titles supply topical scope for routing only. No
        # experimental relation or condition is inferred from a title mention.
        for source in self.registry.db.execute("SELECT source_id,title FROM sources"):
            if source["source_id"] in self.source_scopes:
                continue
            for investigation in investigations:
                aliases = self.store.registry.entity_mentions.get(investigation, {}).get(
                    "aliases", []
                )
                if any(
                    len(alias) >= 4
                    and re.search(
                        r"(?<!\w)" + re.escape(alias) + r"(?!\w)",
                        (source["title"] or "").replace("_", " "),
                        re.IGNORECASE,
                    )
                    for alias in aliases
                ):
                    self.source_scopes.setdefault(source["source_id"], set()).add(investigation)

        # The API exposes consultation only. Approved aliases change with a
        # rebuilt snapshot, not while a service is answering a question.
        self.store._approved_snapshot_id = self.manifest["snapshot_id"]

    def passage_scientific_subjects(self, anchor):
        """Evidence-backed investigation scope, separate from title-based routing."""
        subjects = set()
        for span in anchor.get("spans", []):
            text = " ".join(span.get("text", "").split())
            if span.get("scope") == "source_subject_context":
                from nasa_fire_ai.services.ontology_support import investigation_mentions

                source = self.registry.resolve(span["evidence_id"]) or {}
                if source.get("document_id") == anchor.get("document_id") and span.get(
                    "text", ""
                ) in source.get("text", ""):
                    subjects.update(investigation_mentions(span["text"], self.store))
            for investigation, quote in self.evidence_subject_contexts.get(span["evidence_id"], []):
                original = " ".join((quote or "").split())
                if (
                    text
                    and original
                    and (text in original or original in text)
                    or not original
                    and (self.registry.resolve(span["evidence_id"]) or {}).get("source_cells")
                ):
                    subjects.add(investigation)
        return sorted(subjects)

    def passage_scientific_contexts(self, anchor):
        """Independent attributed contexts must not become one page-wide subject."""
        groups = {}
        for span in anchor.get("spans", []):
            if span.get("scope") in {
                "section_heading",
                "source_local_name_definition",
                "source_subject_context",
            }:
                continue
            text = " ".join(span.get("text", "").split())
            for investigation, quote in self.evidence_subject_contexts.get(span["evidence_id"], []):
                original = " ".join((quote or "").split())
                if text and original and (text in original or original in text):
                    groups.setdefault(original, set()).add(investigation)
        return sorted({tuple(sorted(subjects)) for subjects in groups.values()})

    def passage_scientific_roles(self, anchor):
        """Route by the approved class of a matching, source-backed quotation."""
        roles = set()
        for span in anchor.get("spans", []):
            text = " ".join(span.get("text", "").split())
            for quote, classes in self.evidence_role_contexts.get(span["evidence_id"], []):
                original = " ".join(quote.split())
                if text and (text in original or original in text):
                    roles.update(classes)
        return sorted(roles)

    def _investigation_records(self, investigation):
        """Navigate both asserted directions without inferring experimental identity."""
        from nasa_fire_ai.query.native import canonical_record, identity

        subjects = self.store.relations(investigation, "hasSourceRecord") | self.store.relations(
            investigation, "hasRun"
        )
        subjects.update(
            identity(self.store.graph.value(link, NS.subject))
            for link in self.store.graph.subjects(NS.object, node(investigation))
            if canonical_record(self.store.graph, link)
            and self.store.graph.value(link, NS.relation) == node("belongsToInvestigation")
        )
        return subjects

    def source_records(self, investigation, identifier=None, *, offset=0, limit=20):
        """Exact source-scoped record lookup; labels never imply physical identity."""
        records = []
        subjects = self._investigation_records(investigation)

        def source_order(subject):
            refs = self.store.evidence(subject)
            original = self.registry.resolve(refs[0]) if refs else {}
            return (
                (original or {}).get("structured_location", {}).get("row_ordinal", 10**9),
                subject,
            )

        for subject in sorted(subjects, key=source_order):
            payload = self.store.payload(subject)
            if identifier is not None and payload.get("reported_identifier") != identifier:
                alternatives = [
                    self.store.payload(value_id)
                    for value_id in self.store.relations(subject, "hasRecordedField")
                ]
                if not any(
                    value.get("qualifiers", {}).get("scientific_role")
                    == "original_record_identifier"
                    and str(value.get("value", {}).get("reported_value", "")).strip() == identifier
                    for value in alternatives
                ):
                    continue
            fields = []
            for relation in ("hasCondition", "hasMeasurement", "hasRecordedField"):
                for value_id in sorted(self.store.relations(subject, relation)):
                    value = self.store.payload(value_id)
                    fields.append({**value, "relationship": relation})
            records.append(
                {
                    "id": subject,
                    "classes": sorted(self.store.classes(subject)),
                    "record": payload,
                    "fields": fields,
                    "evidence": [self._evidence(eid) for eid in self.store.evidence(subject)],
                }
            )
        return {
            "items": records[offset : offset + limit],
            "total": len(records),
            "offset": offset,
            "limit": limit,
            "snapshot_id": self.manifest["snapshot_id"],
        }

    def close(self):
        if close := getattr(self.semantic_candidates, "close", None):
            close()
        self.registry.db.close()

    def interpret(self, query, proposal=None):
        from nasa_fire_ai.query.record_identity import resolve_record_mentions

        subject_ids, interpreted_query = resolve_record_mentions(query, self.store, self.root)
        proposal = (
            self.interpreter.interpret_minimal(interpreted_query)
            if subject_ids
            else proposal or self.interpreter.interpret_minimal(query)
        )
        query = interpreted_query
        if re.search(r"\b(?:explain|why|how)\b", query, re.IGNORECASE):
            proposal.operation = "explain"
        intent = resolve_minimal(proposal, self.store.registry, self.language, query=query)
        # The default run target must not hide a source explicitly scoped to specimens.
        if intent.targets == ["ExperimentalRun"] and not re.search(
            r"\b(?:run|runs|experiment|experiments)\b", query, re.IGNORECASE
        ):
            intent.targets.extend(
                ["Sample", "SourceRecord", "ExperimentalSession", "ConfigurationSummary"]
            )
        # Preserve all unparsed content words. This deliberately trades recall for
        # explicit uncertainty until the next interpreter can ground those concepts.
        remaining = query.casefold()
        phrases = []
        for eid, meta in self.store.registry.entity_mentions.items():
            if eid in self.store.registry.entities:
                phrases.extend([eid, *meta["aliases"]])
        for section in ["target_mentions", "information_mentions", "context_mentions", "operators"]:
            for key, value in self.language.get(section, {}).items():
                phrases.extend(value if isinstance(value, list) else [key])
        for definition in self.store.registry.properties.values():
            phrases.extend([definition.property_id, *definition.aliases])
        for operand in intent.comparison.operands if intent.comparison else []:
            phrases.extend([operand, operand.rsplit("-", 1)[-1]])
        for mention in literal_numeric_mentions(query, self.store.registry):
            phrases.append(mention["expression"])
        for phrase in sorted(set(phrases), key=len, reverse=True):
            remaining = re.sub(
                r"(?<!\w)" + re.escape(phrase.casefold()) + r"(?!\w)", " ", remaining
            )
        ordinary = set(self.store.registry.selection_policy.get("stop_words", [])) | {
            "search",
            "please",
            "list",
            "which",
            "where",
            "that",
            "those",
            "these",
            "their",
            "evidence",
            "findings",
            "scientific",
            "research",
            "recorded",
            "documented",
            "compare",
            "comparison",
            "between",
            "versus",
            "vs",
            "explain",
            "why",
            "how",
            "at",
            "on",
            "using",
            "only",
            "all",
            "any",
            "than",
            "by",
            "can",
            "be",
            "satisfy",
        }
        residual = sorted(words(remaining) - ordinary)
        intent.unresolved_mentions = sorted(set(intent.unresolved_mentions + residual))
        if not intent.targets and not intent.requested_information:
            intent.targets = [
                "ExperimentalRun",
                "Sample",
                "SourceRecord",
                "ExperimentalSession",
                "ConfigurationSummary",
            ]
        if subject_ids:
            intent.subject_ids = subject_ids
            if intent.operation == "COMPARE" and len(subject_ids) >= 2 and not intent.comparison:
                from nasa_fire_ai.query.v2 import ComparisonV2

                intent.comparison = ComparisonV2(operands=subject_ids)
        return intent

    def _evidence(self, eid):
        row = self.registry.resolve(eid)
        if row is None:
            return None
        source = self.registry.source_metadata(eid) or {}
        if source.get("source_id"):
            doi = self.registry.db.execute(
                "SELECT doi FROM sources WHERE source_id=?", (source["source_id"],)
            ).fetchone()
            if doi and doi[0]:
                source["doi"] = doi[0]
        return {**row, "source": source, "depth": self.depths.get(source.get("source_id"), "C")}

    def _matrix(self, subject, intent):
        matrix = []
        scope_subject = measurement_scope(subject, self.store)
        for c in intent.entity_constraints:
            actual = sorted(self.store.relations(scope_subject, c.relation))
            # Exact source-backed relation only. Multiple different values remain
            # conflicted when the relation is not declared multi-valued by authority.
            status = "MATCH" if c.entity_id in actual else "DIFFER" if actual else "UNKNOWN"
            refs = []
            for record in self.store.graph.subjects(NS.subject, node(scope_subject)):
                if self.store.graph.value(record, NS.relation) == node(c.relation):
                    refs.extend(str(e) for e in self.store.graph.objects(record, NS.evidenceRef))
            if status == "MATCH" and (
                not refs or any(self.registry.resolve(eid) is None for eid in refs)
            ):
                status = "UNKNOWN"
            matrix.append(
                {
                    "scope_subject": scope_subject,
                    "dimension": c.relation,
                    "requested": c.entity_id,
                    "actual": actual,
                    "status": status,
                    "evidence_ids": sorted(set(refs)),
                }
            )
        for c in intent.property_constraints:
            records = [
                r
                for r in self.store.value_records(subject, c.property_id)
                or self.store.value_records(scope_subject, c.property_id)
                if all(r["qualifiers"].get(k) == v for k, v in c.qualifiers.items())
            ]
            states = {evaluate_constraint(c, row["value"], self.store.registry) for row in records}
            status = (
                "UNKNOWN"
                if not states or states == {"UNKNOWN"}
                else "CONFLICT"
                if "MATCH" in states and "DIFFER" in states
                else "NOT_COMPARABLE"
                if "INVALID" in states
                else next(iter(states))
                if len(states) == 1
                else "UNKNOWN"
            )
            if any(
                r["qualifiers"].get("modality")
                in {"simulated", "predicted", "derived", "hypothetical", "proposed", "planned"}
                for r in records
            ):
                status = "NOT_COMPARABLE"
            matrix.append(
                {
                    "dimension": c.property_id,
                    "requested": c.model_dump(mode="json"),
                    "status": status,
                    "actual": [{**r, "value": r["value"].model_dump(mode="json")} for r in records],
                }
            )
        matrix.extend(
            {
                "dimension": x,
                "status": "UNKNOWN",
                "actual": [],
                "reason": "unresolved query mention",
            }
            for x in intent.unresolved_mentions
        )
        return matrix

    def _item(self, item, intent, category):
        subject = item["id"]
        matrix = self._matrix(subject, intent)
        # Native selection is necessary but this boundary also enforces provenance
        # for every restriction and prevents documentary classes becoming DIRECT.
        classes = self.store.classes(subject)
        experimental = bool(
            self.store.classes(subject, include_ancestors=True)
            & {
                "ExperimentalRun",
                "Sample",
                "Measurement",
                "ReportedObservation",
                "ExperimentalCondition",
            }
        )
        if category == "DIRECT" and (
            not experimental or any(x["status"] != "MATCH" for x in matrix)
        ):
            category = "RELATED"
        points = {"MATCH": 3, "DIFFER": -2, "UNKNOWN": -1, "CONFLICT": -3, "NOT_COMPARABLE": -3}
        score = sum(points[r["status"]] for r in matrix)
        sources = [self._evidence(eid) for eid in self.store.evidence(subject)]
        sources = [r for r in sources if r]
        if not sources or len(sources) != len(self.store.evidence(subject)):
            category = "DISCOVERY"
        routes = []
        if "ExperimentalRun" in classes:
            for relation in ("usesSample", "hasMeasurement"):
                routes.extend(
                    navigate(self.store, subject, [RouteStep(relation)], self.registry)["results"]
                )
        elif "Measurement" in classes:
            routes = navigate(
                self.store,
                subject,
                [RouteStep("hasMeasurement", direction="REVERSE")],
                self.registry,
            )["results"]
        return {
            "id": subject,
            "category": category,
            "classes": sorted(classes),
            "approved_class_ancestors": sorted(self.store.classes(subject, include_ancestors=True)),
            "payload": self.store.payload(subject),
            "constraints": matrix,
            "matching_dimensions": [r["dimension"] for r in matrix if r["status"] == "MATCH"],
            "different_dimensions": [r["dimension"] for r in matrix if r["status"] == "DIFFER"],
            "unknown_dimensions": [r["dimension"] for r in matrix if r["status"] == "UNKNOWN"],
            "positive_relationships": [r for r in matrix if r["status"] == "MATCH"],
            "reason_not_direct": None
            if category == "DIRECT"
            else "Restrictions, subject role, or requested information are not fully established",
            "ranking_score": score,
            "ranking_features": {
                "scientific_relevance": {
                    "score": score,
                    "weights": points,
                    "matched": sum(r["status"] == "MATCH" for r in matrix),
                    "different": sum(r["status"] == "DIFFER" for r in matrix),
                },
                "requested_information_match": bool(
                    set(intent.requested_information) & set(classes)
                ),
                "support_level": sorted({r["depth"] for r in sources}),
                "resolvable_evidence_count": len(sources),
                "documentary_relevance": None,
                "boundary": "Separate scientific eligibility, support depth and documentary relevance; not confidence or risk",
            },
            "ranking_reasons": [
                f"{r['dimension']}: {r['status']} ({points[r['status']]:+d})" for r in matrix
            ],
            "evidence": sources,
            "ontology_paths": routes,
            "limitations": [
                "Connectivity does not establish experimental equivalence",
                "Relevance score is not a safety or fire-risk estimate",
            ],
        }

    def _passage_candidates(self, query, intent, allowed):
        """Fuse candidate ranks, retaining provenance independently of claim eligibility.

        General retrieval rule: approved aliases expand places to search only.
        Source round-robin prevents one long report monopolizing the first page.
        """
        from collections import defaultdict, deque

        from nasa_fire_ai.services.investigation import topic_terms

        focused = " ".join(topic_terms(query))
        searches = [("lexical", query)]
        if focused and focused.casefold() != query.casefold():
            searches.append(("focused_lexical", focused))
        for constraint in intent.entity_constraints:
            aliases = self.store.registry.entity_mentions.get(constraint.entity_id, {}).get(
                "aliases", []
            )
            if aliases:
                searches.append(("approved_alias", " ".join(aliases)))
        from nasa_fire_ai.query.lexicon import load_lexicon

        for entry in load_lexicon():
            labels = [entry["canonical_label"], *entry["aliases"], *entry.get("abbreviations", [])]
            if any(
                re.search(r"(?<!\w)" + re.escape(label) + r"(?!\w)", query, re.IGNORECASE)
                for label in labels
            ):
                # Expand only to word forms actually present in the corpus. This
                # proposes lexical candidates, never semantic equivalence.
                stems = {t.lower() for label in labels for t in re.findall(r"[A-Za-z]{4,}", label)}
                forms = [
                    word for word in self._corpus_terms if any(word.startswith(t) for t in stems)
                ]
                searches.append(("controlled_terminology", " ".join([*labels, *forms[:24]])))
        searches = list(dict.fromkeys(searches))[:6]
        provisional_ids = {
            row[0]
            for row in self.registry.db.execute(
                "SELECT evidence_id FROM evidence_refs WHERE source_id LIKE 'team-processed-%'"
            )
        }
        catalogue_ids = {
            row[0]
            for row in self.registry.db.execute(
                "SELECT evidence_id FROM evidence_refs WHERE source_id LIKE 'catalog-%'"
            )
        }
        # Publication lists and investigation identities are different kinds of
        # catalogue evidence. Preserve each pool before limiting lexical results;
        # scoring after truncation cannot recover displaced identity records.
        metadata_sources = {
            row[0]
            for row in self.registry.db.execute("SELECT source_id,source_type FROM sources")
            if is_publication_metadata(row[1])
        }
        metadata_ids = {
            row[0]
            for row in self.registry.db.execute("SELECT evidence_id,source_id FROM evidence_refs")
            if row[1] in metadata_sources
        }
        catalogue_ids -= metadata_ids
        original_allowed = [
            eid
            for eid in allowed
            if eid not in provisional_ids and eid not in catalogue_ids and eid not in metadata_ids
        ]
        catalogue_allowed = [eid for eid in allowed if eid in catalogue_ids]
        metadata_allowed = [eid for eid in allowed if eid in metadata_ids]
        processed_allowed = [eid for eid in allowed if eid in provisional_ids]
        pool, steps = {}, []

        def merge(rows, strategy, search_query):
            new = 0
            for rank, passage in enumerate(rows, 1):
                eid = passage["evidence_id"]
                if eid not in pool:
                    pool[eid] = {**passage, "retrieval_score": 0.0, "retrieval_routes": []}
                    new += 1
                pool[eid]["retrieval_score"] += 1 / (60 + rank)
                pool[eid]["retrieval_routes"].append(
                    {"strategy": strategy, "query": search_query, "rank": rank}
                )
            steps.append(
                {
                    "strategy": strategy,
                    "query": search_query,
                    "returned": len(rows),
                    "new_candidates": new,
                    "at_limit": len(rows) >= self.candidate_limit,
                }
            )

        for strategy, text in searches:
            merge(
                self.registry.search(
                    text,
                    eligible_ids=original_allowed,
                    limit=self.candidate_limit,
                ),
                strategy,
                text,
            )
            if catalogue_allowed:
                merge(
                    self.registry.search(
                        text,
                        eligible_ids=catalogue_allowed,
                        limit=min(40, self.candidate_limit),
                    ),
                    "catalogue_" + strategy,
                    text,
                )
            if metadata_allowed:
                merge(
                    self.registry.search(
                        text, eligible_ids=metadata_allowed, limit=min(40, self.candidate_limit)
                    ),
                    "bibliographic_" + strategy,
                    text,
                )
            if processed_allowed:
                merge(
                    self.registry.search(
                        text,
                        eligible_ids=processed_allowed,
                        limit=min(40, self.candidate_limit),
                    ),
                    "provisional_" + strategy,
                    text,
                )
        # Investigation-to-record navigation contributes source-scoped candidates.
        # A matching field is required; a named campaign alone is not relevance.
        from nasa_fire_ai.services.investigation import topic_terms

        typed_request = (
            bool(intent.subject_ids)
            or bool(
                re.search(
                    r"\b(?:tables?|records?|entries|summar(?:y|ies)|configurations?|ranges?|dimensions?|geometry|identity|scope)\b",
                    query,
                    re.IGNORECASE,
                )
            )
            or any(
                re.search(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", query, re.IGNORECASE)
                for definition in self.store.registry.properties.values()
                for alias in definition.aliases
                if len(alias) > 3
            )
        )
        field_terms = set(topic_terms(query))
        record_candidates = []
        explicit = set(intent.subject_ids)
        for constraint in intent.entity_constraints:
            if constraint.relation != "belongsToInvestigation":
                continue
            records = self._investigation_records(constraint.entity_id)
            for subject in records:
                for eid in self.store.evidence(subject):
                    row = self.registry.resolve(eid)
                    if row and (
                        subject in explicit
                        or typed_request
                        or field_terms & set(topic_terms(row["text"]))
                    ):
                        record_candidates.append(
                            (
                                subject in explicit,
                                len(field_terms & set(topic_terms(row["text"]))),
                                row,
                            )
                        )
        record_candidates.sort(
            key=lambda candidate: (-candidate[0], -candidate[1], candidate[2]["evidence_id"])
        )
        if record_candidates:
            # Keep complementary investigations in a multi-part question before
            # bounding the graph candidate pool. Ranking never grants applicability.
            record_groups = defaultdict(deque)
            for _, _, row in record_candidates:
                source = self.registry.source_metadata(row["evidence_id"]) or {}
                record_groups[source.get("source_id", row["evidence_id"])].append(row)
            balanced = []
            while record_groups and len(balanced) < self.candidate_limit:
                for source_id in list(record_groups):
                    balanced.append(record_groups[source_id].popleft())
                    if not record_groups[source_id]:
                        del record_groups[source_id]
                    if len(balanced) == self.candidate_limit:
                        break
            merge(balanced, "graph_record_fields", query)
        if self.semantic_candidates:
            rows = []
            try:
                for eid, score in self.semantic_candidates(
                    query, set(allowed), self.candidate_limit
                ):
                    if eid in allowed and (row := self.registry.resolve(eid)):
                        rows.append({**row, "semantic_similarity": score})
                merge(rows, "semantic", query)
            except (RuntimeError, OSError) as error:
                steps.append(
                    {
                        "strategy": "semantic",
                        "status": "UNAVAILABLE",
                        "error_type": type(error).__name__,
                        "returned": 0,
                        "new_candidates": 0,
                    }
                )
        requested_scopes = {
            constraint.entity_id
            for constraint in intent.entity_constraints
            if constraint.relation == "belongsToInvestigation"
        }
        # Catalogue aliases match many generic terms but cannot supply original
        # fields. Give the structured navigation channel additional weight when
        # the question actually requests a record, table, or curated quantity.
        # This is routing only; strict scientific eligibility remains separate.
        for candidate in pool.values():
            source = self.registry.source_metadata(candidate["evidence_id"]) or {}
            authority = publication_metadata_weight(query, source.get("source_type"))
            candidate["retrieval_score"] *= authority
            candidate["publication_metadata_routing_weight"] = authority
            if requested_scopes & self.source_scopes.get(source.get("source_id"), set()):
                candidate["retrieval_score"] *= 2
                candidate["routing_scope_match"] = True
                if typed_request and any(
                    route["strategy"] == "graph_record_fields"
                    for route in candidate["retrieval_routes"]
                ):
                    candidate["retrieval_score"] *= 3
                    candidate["routing_field_request"] = True
        ranked = sorted(pool.values(), key=lambda r: (-r["retrieval_score"], r["evidence_id"]))
        groups = defaultdict(deque)
        provisional = deque()
        duplicates, seen = 0, set()
        for row in ranked:
            # Same original page registered under multiple source IDs is one candidate.
            key = (row.get("checksum") or row["evidence_id"], row.get("page"), row.get("text"))
            if key in seen:
                duplicates += 1
                continue
            seen.add(key)
            source = self.registry.source_metadata(row["evidence_id"]) or {}
            if self.depths.get(source.get("source_id")) == "P":
                provisional.append(row)
                continue
            groups[source.get("source_id", row.get("document_id"))].append(row)
        diverse = []
        while groups:
            for sid in list(groups):
                diverse.append(groups[sid].popleft())
                if not groups[sid]:
                    del groups[sid]
        # Derived team tables remain searchable, but cannot crowd source
        # evidence and catalogue identity out of the bounded first page.
        diverse.extend(provisional)
        selected = diverse[: self.candidate_limit]
        for rank, row in enumerate(selected, 1):
            row["candidate_rank"] = rank
        return selected, {
            "steps": steps,
            "unique_retrieved": len(pool),
            "duplicates_suppressed": duplicates,
            "retained": len(selected),
            "pool_truncated": max(0, len(diverse) - len(selected)),
            "candidate_limit": self.candidate_limit,
            "examined_for_claims": "See claim verification and chat context receipts",
            "ranking": "reciprocal rank fusion followed by source round-robin",
            "boundary": "Retrieval relevance is separate from evidence fidelity and experimental applicability",
        }

    def search(
        self,
        query: str,
        *,
        intent: QueryIntentV2 | None = None,
        limit: int = 12,
        assist: bool = False,
        research: bool = False,
        offset: int = 0,
        complete_claims: bool = False,
    ):
        if not query.strip() or len(query) > 12000 or not 1 <= limit <= 100 or offset < 0:
            raise ValueError("Nonempty query and limit in 1..100 required")
        start = perf_counter()
        intent = intent.model_copy(deep=True) if intent is not None else self.interpret(query)
        provider = {"status": "UNAVAILABLE" if assist else "NOT_REQUESTED", "calls": []}
        if assist and self.model_interpreter and intent is not None:
            from nasa_fire_ai.llm.interfaces import ProviderFailure

            try:
                proposal = self.model_interpreter.interpret_minimal(query)
                # Model mentions must originate in the question. Familiar canonical
                # identities suggested without a literal mention cannot grant scope.
                for name in (
                    "targets",
                    "entities",
                    "requested_information",
                    "comparison_operands",
                    "sources",
                ):
                    if any(x.casefold() not in query.casefold() for x in getattr(proposal, name)):
                        raise ValueError("Model introduced a nonliteral mention")
                if intent.comparison:
                    # The approved investigation scope and exact operand identity
                    # can disambiguate a shorthand that the model marked ambiguous.
                    suffixes = {o.rsplit("-", 1)[-1].casefold() for o in intent.comparison.operands}
                    resolved = [m for m in proposal.ambiguous if m.casefold() in suffixes]
                    if resolved:
                        proposal.ambiguous = [m for m in proposal.ambiguous if m not in resolved]
                        provider["normalization_actions"] = [
                            {
                                "mention": m,
                                "reason": "Unique deterministic operand within the explicit investigation scope",
                            }
                            for m in resolved
                        ]
                candidate = self.interpret(query, proposal)
                if intent.comparison and candidate.comparison != intent.comparison:
                    raise ValueError("Model changed resolved comparison operands")
                if intent.comparison and set(candidate.unresolved_mentions) - set(
                    intent.unresolved_mentions
                ):
                    raise ValueError("Model introduced unresolved comparison mentions")
                for name in ("entity_constraints", "property_constraints"):
                    existing = {c.model_dump_json() for c in getattr(candidate, name)}
                    getattr(candidate, name).extend(
                        c for c in getattr(intent, name) if c.model_dump_json() not in existing
                    )
                candidate.unresolved_mentions = sorted(
                    set(candidate.unresolved_mentions + intent.unresolved_mentions)
                )
                candidate.ambiguities = sorted(set(candidate.ambiguities + intent.ambiguities))
                candidate.clarification_required |= intent.clarification_required
                self.store.registry.validate_intent(candidate)
                intent = candidate
                provider["status"] = "AVAILABLE"
            except (ProviderFailure, ValueError, LookupError, TypeError) as error:
                provider.update(status="DEGRADED", interpretation_error=type(error).__name__)
            provider["calls"].append(
                {"stage": "interpretation", **getattr(self.model_interpreter, "last_receipt", {})}
            )
        self.store.registry.validate_intent(intent)
        for constraint in intent.entity_constraints:
            if (
                constraint.relation not in self.store.registry.relations
                or constraint.entity_id not in self.store.registry.entities
            ):
                raise ValueError("Unapproved entity constraint")
        if set(intent.source_constraints) - self.store.registry.source_ids:
            raise ValueError("Unknown source restriction")
        interpreted = perf_counter()
        execution = execute_native(
            intent,
            query,
            self.store,
            self.registry,
            hierarchical=True,
            relational=True,
            schema_hierarchical=True,
            limit=self.candidate_limit,
        )
        research_receipt = {}
        if research:
            from nasa_fire_ai.services.investigation import ResearchBudget, investigate

            research_receipt = investigate(
                query,
                execution,
                self.store,
                self.registry,
                budget=self.research_budget
                or ResearchBudget(
                    max_rounds=3,
                    max_actions=6,
                    max_candidates=32,
                    timeout_seconds=15,
                    max_model_calls=0,
                ),
                planner=self.research_planner,
            )
        retrieved = perf_counter()
        buckets = {"DIRECT": [], "RELATED": [], "DISCOVERY": []}
        for category, rows in [
            ("DIRECT", execution.bundle.direct_evidence),
            ("RELATED", execution.bundle.related_evidence),
        ]:
            for row in rows:
                item = self._item(row, intent, category)
                # Campaign membership alone supports discovery of a phenomenon,
                # not scientific relevance to an unresolved requested outcome.
                positive = [r for r in item["constraints"] if r["status"] == "MATCH"]
                physical = [
                    r
                    for r in item["constraints"]
                    if isinstance(r.get("requested"), dict) and r["status"] in {"MATCH", "DIFFER"}
                ]
                anchors = {"hasMaterial", "hasPhenomenon"}
                membership_only = (
                    intent.property_constraints
                    and not intent.subject_ids
                    and not physical
                    and positive
                    and all(r["dimension"] == "belongsToInvestigation" for r in positive)
                )
                if item["category"] == "RELATED" and (
                    membership_only
                    or not positive
                    and not physical
                    or intent.unresolved_mentions
                    and not physical
                    and not any(r["dimension"] in anchors for r in positive)
                ):
                    item["category"] = "DISCOVERY"
                    item["reason_not_direct"] = (
                        "Investigation membership does not establish the requested scientific variables"
                        if membership_only
                        else "No verified relationship to the requested phenomenon; campaign membership only"
                    )
                buckets[item["category"]].append(item)
        counts = {key: len(value) for key, value in buckets.items()}
        for rows in buckets.values():
            rows.sort(
                key=lambda r: (
                    -r["ranking_score"],
                    -int(r["ranking_features"]["requested_information_match"]),
                    0 if "A" in r["ranking_features"]["support_level"] else 1,
                    r["id"],
                )
            )
        classified = perf_counter()
        documentary = []
        discovery_by_id = {}
        for candidate in buckets["DISCOVERY"]:
            for evidence in candidate["evidence"]:
                eid = evidence["evidence_id"]
                entry = discovery_by_id.setdefault(
                    eid,
                    {
                        **evidence,
                        "category": "DISCOVERY",
                        "candidate_subjects": [],
                        "limitations": candidate["limitations"],
                    },
                )
                entry["candidate_subjects"].append(
                    {"id": candidate["id"], "reason": candidate["reason_not_direct"]}
                )
        documentary_keys = {}
        # Source restrictions apply BEFORE lexical ranking. Unmapped topic words
        # remain searchable, but can never grant structured eligibility.
        allowed = [
            r["evidence_id"]
            for r in self.registry.db.execute(
                "SELECT p.evidence_id,d.source_id FROM passages p JOIN documents d USING(document_id)"
            )
            if not intent.source_constraints or r["source_id"] in intent.source_constraints
        ]
        passages, candidate_receipt = self._passage_candidates(query, intent, allowed)
        for passage in passages:
            source = self.registry.source_metadata(passage["evidence_id"]) or {}
            depth = self.depths.get(source.get("source_id"), "C")
            row = {
                **passage,
                "source": source,
                "depth": depth,
                "category": "DOCUMENTARY" if depth in {"A", "B"} else "DISCOVERY",
                "limitations": ["Text relevance alone does not satisfy experimental constraints"],
            }
            if depth in {"A", "B"}:
                key = (passage.get("checksum"), passage.get("page"), passage.get("text"))
                if key not in documentary_keys:
                    documentary_keys[key] = row
                    documentary.append(row)
                else:
                    documentary_keys[key].setdefault("duplicate_evidence_ids", []).append(
                        passage["evidence_id"]
                    )
            else:
                discovery_by_id.setdefault(passage["evidence_id"], row)
        discovery = list(discovery_by_id.values())
        candidates = [*buckets["DIRECT"], *buckets["RELATED"], *documentary, *discovery]
        for row in discovery:
            row.update(
                candidate_kind="retrieved_unaccredited_source",
                verified_relationship=False,
                relevance_reason="Retrieved by search or graph connectivity; scientific relevance remains unverified",
                uncertainty_reason="Term overlap or proximity does not establish the requested scientific meaning or conditions",
            )
        totals = {
            "direct": len(buckets["DIRECT"]),
            "related": len(buckets["RELATED"]),
            "documentary": len(documentary),
            "discovery": len(discovery),
        }
        documentary_ms = (perf_counter() - classified) * 1000
        bundle = execution.bundle
        # Reconcile the bundle with the stricter public eligibility gate before
        # claim selection. Research may add candidates, but cannot bypass it.
        for category, field in (("DIRECT", "direct_evidence"), ("RELATED", "related_evidence")):
            setattr(
                bundle,
                field,
                [
                    {
                        "id": row["id"],
                        "evidence_ids": [e["evidence_id"] for e in row["evidence"]],
                        "matches": row["matching_dimensions"],
                        "request_limits": row["limitations"] if category == "RELATED" else [],
                    }
                    for row in buckets[category]
                ],
            )
        bundle.no_direct_evidence = not bool(buckets["DIRECT"])
        bundle.retrieval_metadata["scientific_question"] = query
        bundle.retrieval_metadata["explicit_record_subjects"] = list(intent.subject_ids)
        bundle.retrieval_metadata["subject_identity_context"] = {
            subject: {
                "reported_identifier": self.store.payload(subject).get("reported_identifier"),
                "investigations": [
                    {
                        "id": investigation,
                        "title": self.store.payload(investigation).get("title", investigation),
                    }
                    for investigation in sorted(
                        self.store.relations(subject, "belongsToInvestigation")
                    )
                ],
            }
            for subject in {
                *(row["id"] for row in buckets["DIRECT"] + buckets["RELATED"]),
                *intent.subject_ids,
            }
        }
        claims, verification = [], []
        synthesis_ms = verification_ms = 0.0
        if assist:
            from nasa_fire_ai.services.claim_verification import verify_claim
            from nasa_fire_ai.services.scientific_synthesis import select_claims

            if self.selector:
                then = perf_counter()
                from nasa_fire_ai.llm.interfaces import ProviderFailure

                try:
                    receipt = self.selector.select(query, bundle, synthesis=True)
                except (ProviderFailure, ValueError, TypeError) as error:
                    receipt = {"execution": "FAILED", "error_type": type(error).__name__}
                synthesis_ms = (perf_counter() - then) * 1000
                provider["calls"].append({"stage": "synthesis", **receipt})
                bundle.retrieval_metadata["nemotron_scientific_selection"] = receipt
                if receipt.get("error_type") or receipt.get("rejected"):
                    provider["status"] = "DEGRADED"
            then = perf_counter()
            selected, _ = select_claims(bundle, complete=complete_claims)
            for _, claim in selected:
                proposed = next(
                    (
                        row
                        for row in bundle.retrieval_metadata.get(
                            "nemotron_scientific_selection", {}
                        ).get("accepted_synthesis", [])
                        if row["claim_id"] == claim.claim_id
                    ),
                    None,
                )
                if proposed and proposed["text"] != claim.text:
                    from nasa_fire_ai.models import GroundedClaim
                    from nasa_fire_ai.services.claim_verification import verify_reformulation

                    rewritten = GroundedClaim.model_validate(proposed)
                    check = verify_reformulation(
                        rewritten,
                        claim,
                        bundle,
                        self.registry,
                        store=self.store,
                        entailment=self.semantic_verifier,
                    )
                    if check["status"] in {"SUPPORTED", "SUPPORTED_WITH_LIMITATIONS"}:
                        claim = rewritten
                    else:
                        check = verify_claim(claim, bundle, self.registry, store=self.store)
                else:
                    check = verify_claim(claim, bundle, self.registry, store=self.store)
                verification.append(check)
                if check["status"] in {"SUPPORTED", "SUPPORTED_WITH_LIMITATIONS"}:
                    row = claim.model_dump(mode="json")
                    row["sources"] = [self._evidence(eid) for eid in claim.evidence_ids]
                    row["validation"] = check
                    record = next(
                        (
                            span.get("structured_record")
                            for span in claim.support_spans
                            if span.get("structured_record")
                        ),
                        {},
                    )
                    row["subject"] = record.get("subject")
                    row["modality"] = record.get("qualifiers", {}).get("modality")
                    row["conditions"] = [
                        self.store.payload(r)
                        for r in sorted(self.store.relations(row["subject"] or "", "hasCondition"))
                    ]
                    row["limitations"] = check.get("limitations", []) + (
                        [record["qualifiers"]["limitations"]]
                        if record.get("qualifiers", {}).get("limitations")
                        else []
                    )
                    claims.append(row)
            verification_ms = (perf_counter() - then) * 1000
            provider["synthesis_boundary"] = (
                "Source metadata and provenance checks; reformulations require an independent semantic verifier"
            )
        comparison = bundle.comparison
        return SearchResult(
            snapshot_id=self.manifest["snapshot_id"],
            claims=claims,
            verification=verification,
            provider=provider,
            investigation=research_receipt,
            intent=intent,
            candidates=candidates,
            continuation={
                "offset": offset,
                "limit": limit,
                "totals": totals,
                "next_offsets": {
                    k: offset + limit if offset + limit < n else None for k, n in totals.items()
                },
                "boundary": "Totals describe the bounded retrieved pool, not all NASA literature",
            },
            direct=buckets["DIRECT"][offset : offset + limit],
            related=buckets["RELATED"][offset : offset + limit],
            discovery=discovery[offset : offset + limit],
            documentary=documentary[offset : offset + limit],
            comparison=comparison.model_dump(mode="json") if comparison else None,
            sufficiency="DIRECT_EVIDENCE" if buckets["DIRECT"] else "NO_DIRECT_EVIDENCE",
            limitations=list(self.manifest["limitations"])
            + (
                [
                    "Semantic query embedding unavailable for this request; lexical, structured and graph evidence remain accessible."
                ]
                if any(
                    step.get("status") == "UNAVAILABLE"
                    for step in candidate_receipt.get("steps", [])
                )
                else []
            )
            + [
                "No direct evidence in this snapshot does not establish a NASA knowledge gap",
                "Deterministic interpretation preserves unsupported words as uncertainty",
            ],
            metrics={
                "interpretation_ms": (interpreted - start) * 1000,
                "retrieval_ms": execution.latency_ms["planning"]
                + execution.latency_ms["bm25_ranking"]
                + documentary_ms,
                "classification_ms": execution.latency_ms["kg_execution"]
                + (classified - retrieved) * 1000,
                "native_execution_ms": (retrieved - interpreted) * 1000,
                "total_ms": (perf_counter() - start) * 1000,
                "native_timings_ms": execution.latency_ms,
                "candidate_counts": {
                    **counts,
                    "DISCOVERY": len(discovery),
                    "DOCUMENTARY": len(documentary),
                },
                "candidate_generation": candidate_receipt,
                "retrieved_candidates": len(candidates),
                "classified_candidates": len(candidates),
                "returned_candidates": sum(min(limit, max(0, n - offset)) for n in totals.values()),
                "vectors_enabled": self.semantic_candidates is not None
                and not any(
                    step.get("status") == "UNAVAILABLE"
                    for step in candidate_receipt.get("steps", [])
                ),
                "vector_status": "UNAVAILABLE"
                if any(
                    step.get("status") == "UNAVAILABLE"
                    for step in candidate_receipt.get("steps", [])
                )
                else "ACTIVE"
                if self.semantic_candidates
                else "NOT_PROVISIONED",
                "llm_calls": sum(
                    c["stage"] == "interpretation"
                    or c.get("execution") in {"FRESH_INFERENCE", "FAILED"}
                    for c in provider["calls"]
                ),
                "planning_ms": execution.latency_ms["planning"],
                "rdf_ms": execution.latency_ms["kg_execution"],
                "documentary_ms": documentary_ms,
                "public_classification_ms": (classified - retrieved) * 1000,
                "synthesis_ms": synthesis_ms,
                "verification_ms": verification_ms,
                "research_ms": research_receipt.get("latency_ms", 0),
                "usage": [c.get("usage") for c in provider["calls"]],
                "offset": offset,
            },
        )

    def analyze_scenario(self, scenario, *, assist=False, research=False, limit=12):
        """Read-only comparison of user hypotheses with verified NASA records."""
        from nasa_fire_ai.query.scenario import ScenarioAnalysis, ScenarioInput

        scenario = ScenarioInput.model_validate(scenario)
        intent = scenario.intent()
        # Unknown simulator vocabulary is preserved as uncertainty, never registered.
        known_entities = []
        for c in intent.entity_constraints:
            if (
                c.relation in self.store.registry.relations
                and c.entity_id in self.store.registry.entities
            ):
                known_entities.append(c)
            else:
                intent.unresolved_mentions.append(c.relation + "=" + c.entity_id)
        intent.entity_constraints = known_entities
        known_properties = []
        for c in intent.property_constraints:
            if c.property_id in self.store.registry.properties:
                self.store.registry.validate(c)
                known_properties.append(c)
            else:
                intent.unresolved_mentions.append(c.property_id + "=" + c.value.model_dump_json())
        intent.property_constraints = known_properties
        # Natural-language conditions remain mandatory too. The structured input
        # cannot hide lunar gravity, simulation or unresolved source constraints.
        linguistic = self.interpret(scenario.question)
        for name in ("entity_constraints", "property_constraints"):
            existing = {c.model_dump_json() for c in getattr(intent, name)}
            getattr(intent, name).extend(
                c for c in getattr(linguistic, name) if c.model_dump_json() not in existing
            )
        intent.unresolved_mentions = sorted(
            set(intent.unresolved_mentions + linguistic.unresolved_mentions)
        )
        intent.ambiguities = linguistic.ambiguities
        intent.clarification_required = linguistic.clarification_required
        result = self.search(
            scenario.question, intent=intent, limit=limit, assist=assist, research=research
        )
        requested = {
            c.property_id for c in scenario.property_constraints + intent.property_constraints
        } | {c.relation for c in scenario.entity_constraints + intent.entity_constraints}
        expected = set(
            self.store.registry.selection_policy.get("context", {}).get("dimensions", {})
        )
        matrices = [
            {"subject": row["id"], **cell}
            for row in result.direct + result.related
            for cell in row["constraints"]
        ]
        sources = {
            e["evidence_id"]: e for row in result.direct + result.related for e in row["evidence"]
        }
        for row in result.documentary + result.discovery:
            if row.get("evidence_id"):
                sources[row["evidence_id"]] = self._evidence(row["evidence_id"])
        observations = [
            self.store.payload(value)
            for row in result.direct
            for value in sorted(self.store.relations(row["id"], "hasMeasurement"))
            if self.store.payload(value).get("qualifiers", {}).get("modality")
            == "reported_measurement"
        ]
        return ScenarioAnalysis(
            scenario=scenario,
            snapshot_id=result.snapshot_id,
            provided_conditions=list(
                {
                    c.model_dump_json(): c.model_dump(mode="json")
                    for c in scenario.entity_constraints
                    + scenario.property_constraints
                    + intent.entity_constraints
                    + intent.property_constraints
                }.values()
            ),
            unspecified_conditions=sorted(expected - requested),
            evidence=result.model_dump(mode="json"),
            comparable_variables=[r for r in matrices if r["status"] in {"MATCH", "DIFFER"}],
            experimental_differences=[
                r for r in matrices if r["status"] in {"DIFFER", "NOT_COMPARABLE", "CONFLICT"}
            ],
            accredited_observations=observations,
            uncertainties=intent.unresolved_mentions + intent.ambiguities,
            extrapolation_limits=[
                "Hypothetical or simulator parameters and outputs are not NASA observations",
                "No experimental equivalence between microgravity and partial gravity is inferred",
                "Unspecified conditions and unsupported phenomena limit applicability",
                "Ranking is not a fire risk prediction or certified safety recommendation",
            ],
            sources=list(sources.values()),
            additional_research=[
                {
                    "authority": "assistant_analysis",
                    "objective": "Retrieve source-backed scope for " + r,
                    "nasa_recommendation": False,
                }
                for r in sorted(set(intent.unresolved_mentions))
            ],
        )
