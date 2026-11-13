from pathlib import Path

import pytest
from rdflib import RDFS, Graph, Namespace

from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.knowledge import normalize_mention, validate_relation_proposal
from nasa_fire_ai.query.native import SemanticGraph
from nasa_fire_ai.query.ontology_navigation import RouteStep, navigate, schema_closure
from nasa_fire_ai.query.v2 import RelationDefinition, SemanticRegistry


def test_mentions_preserve_geometry_and_do_not_merge():
    aliases = {"MaterialA": ["A-polymer"], "MaterialB": ["B-polymer"]}
    assert normalize_mention("2 cm A-polymer cylinder", aliases)["identity"] == "MaterialA"
    assert normalize_mention("thin A-polymer film", aliases)["identity"] == "MaterialA"
    assert normalize_mention("A-polymer B-polymer mixture", aliases)["status"] == "AMBIGUOUS"
    assert normalize_mention("unclassified rod", aliases)["original"] == "unclassified rod"
    assert normalize_mention("notA-polymer", aliases)["identity"] is None


def test_schema_multiple_inheritance_properties_cycles():
    ns = Namespace("urn:synthetic:")
    g = Graph()
    for a, b in [
        (ns.Leaf, ns.Middle),
        (ns.Middle, ns.Root),
        (ns.Leaf, ns.Second),
        (ns.Root, ns.Leaf),
    ]:
        g.add((a, RDFS.subClassOf, b))
    g.add((ns.usesSpecial, RDFS.subPropertyOf, ns.uses))
    assert schema_closure(g, ns.Leaf, RDFS.subClassOf) == {ns.Leaf, ns.Middle, ns.Root, ns.Second}
    assert schema_closure(g, ns.usesSpecial, RDFS.subPropertyOf) == {ns.usesSpecial, ns.uses}
    assert len(schema_closure(g, ns.Leaf, RDFS.subClassOf, 2)) == 2
    with pytest.raises(ValueError):
        schema_closure(g, ns.Leaf, ns.uses)


def test_dynamic_associations_keep_semantics_and_provenance(tmp_path):
    evidence = EvidenceRegistry(tmp_path / "e.sqlite")
    evidence.add_source({"source_id": "synthetic", "title": "Synthetic fixture"})
    evidence.add_document("doc", "synthetic", "Synthetic fixture")
    evidence.add_passage(
        {
            "evidence_id": "E-synthetic",
            "document_id": "doc",
            "text": "A observed B.",
            "page": None,
            "section": None,
            "start_offset": 0,
            "end_offset": 13,
            "raw_file": "synthetic",
            "checksum": "synthetic",
        }
    )
    registry = SemanticRegistry(
        target_classes={"Thing"},
        relations=[
            RelationDefinition(x) for x in ["includes", "hasCondition", "reports", "supportedBy"]
        ],
    )
    store = SemanticGraph(registry)
    for x in ["Program", "Investigation", "Run", "Condition", "Observation", "Conclusion"]:
        store.add_entity(x, "Thing", ["E-synthetic"])
    for a, p, b in [
        ("Program", "includes", "Investigation"),
        ("Investigation", "includes", "Run"),
        ("Run", "hasCondition", "Condition"),
        ("Run", "reports", "Observation"),
        ("Observation", "supportedBy", "Conclusion"),
        ("Run", "includes", "Program"),
    ]:
        store.add_relation(a, p, b, ["E-synthetic"])
    result = navigate(
        store,
        "Program",
        [RouteStep("includes"), RouteStep("includes"), RouteStep("hasCondition")],
        evidence,
    )
    assert result["results"][0]["entity"] == "Condition"
    assert result["results"][0]["classification"] == "RELATED"
    assert all(p["semantics"] == "ASSOCIATION" for p in result["results"][0]["path"])
    assert navigate(store, "Program", [RouteStep("includes")] * 3, evidence)["results"] == []
    with pytest.raises(LookupError):
        navigate(store, "Run", [RouteStep("unknown")], evidence)
    proposal = {
        "source_id": "synthetic",
        "evidence_id": "E-synthetic",
        "subject_mention": "A",
        "object_mention": "B",
        "predicate_candidate": "observes",
        "supporting_span": "A observed B.",
    }
    assert validate_relation_proposal(proposal, evidence)["review_status"] == "PENDING"
    with pytest.raises(ValueError):
        validate_relation_proposal({**proposal, "supporting_span": "invented"}, evidence)


def test_original_generator_has_no_experiment_specific_association():
    text = (Path(__file__).resolve().parents[1] / "scripts/build_graph.py").read_text()
    assert 'FS["psi-98"]' not in text
    assert "FS.supportedBy" not in text


def test_staging_idempotence_conflict_preserves_review_state(tmp_path):
    registry = EvidenceRegistry(tmp_path / "stage.sqlite")
    row = {
        "candidate_id": "candidate",
        "candidate_type": "RELATION",
        "raw_label": "relation",
        "resolution_status": "CANDIDATE_RELATION",
        "review_status": "PENDING",
    }
    registry.stage_semantic_candidate(row)
    registry.stage_semantic_candidate(row)
    with pytest.raises(ValueError, match="identity conflict"):
        registry.stage_semantic_candidate({**row, "raw_label": "different relation"})
    assert registry.staged_semantic_candidates() == [row]


def test_native_class_navigation_is_additive():
    from nasa_fire_ai.query.native import compile_native, node
    from nasa_fire_ai.query.v2 import QueryIntentV2

    registry = SemanticRegistry(target_classes={"Root", "Middle", "Leaf", "Alternate"})
    store = SemanticGraph(registry)
    store.add_entity("specimen", "Leaf", ["E-synthetic"])
    for a, b in [("Leaf", "Middle"), ("Middle", "Root"), ("Leaf", "Alternate")]:
        store.graph.add((node(a), RDFS.subClassOf, node(b)))
    intent = QueryIntentV2(targets=["Root"])
    assert compile_native(intent, store).candidate_entity_ids == []
    assert compile_native(intent, store, schema_hierarchical=True).candidate_entity_ids == [
        "specimen"
    ]
    assert store.classes("specimen") == {"Leaf"}


def test_property_inheritance_and_rejected_edges(tmp_path):
    from nasa_fire_ai.query.native import NS, node

    evidence = EvidenceRegistry(tmp_path / "e.sqlite")
    evidence.add_source({"source_id": "s"})
    evidence.add_document("d", "s", "Synthetic")
    evidence.add_passage(
        {
            "evidence_id": "E",
            "document_id": "d",
            "text": "synthetic",
            "page": None,
            "section": None,
            "start_offset": 0,
            "end_offset": 9,
            "raw_file": "synthetic",
            "checksum": "synthetic",
        }
    )
    registry = SemanticRegistry(
        target_classes={"Thing"},
        relations=[RelationDefinition("uses"), RelationDefinition("usesSpecial")],
    )
    store = SemanticGraph(registry)
    for item in ["a", "b"]:
        store.add_entity(item, "Thing", ["E"])
    store.graph.add((node("usesSpecial"), RDFS.subPropertyOf, node("uses")))
    store.add_relation("a", "usesSpecial", "b", ["E"])
    result = store.explore_route("a", [RouteStep("uses")], evidence)
    assert result["results"][0]["path"][0]["relation"] == "usesSpecial"
    from rdflib import Literal

    store.graph.add((node("relation:a:usesSpecial:b"), NS.reviewState, Literal("CONTRADICTED")))
    assert not store.explore_route("a", [RouteStep("uses")], evidence)["results"]


def test_unknown_material_is_not_published_as_normalized_identity(tmp_path):
    from nasa_fire_ai.ingestion.knowledge import enrich_native

    evidence = EvidenceRegistry(tmp_path / "e.sqlite")
    evidence.add_source({"source_id": "s"})
    evidence.add_document("d", "s", "Synthetic")
    evidence.add_passage(
        {
            "evidence_id": "E",
            "document_id": "d",
            "text": "Unknown specimen.",
            "page": None,
            "section": None,
            "start_offset": 0,
            "end_offset": 17,
            "raw_file": "synthetic",
            "checksum": "synthetic",
        }
    )
    store = SemanticGraph(SemanticRegistry())
    sample = {
        "type": "SampleRecord",
        "id": "sample",
        "material": "unknown 2 cm rod",
        "evidence_refs": [{"evidence_id": "E", "source_id": "s"}],
    }
    enrich_native(
        store,
        [sample],
        evidence,
        Path(__file__).resolve().parents[1] / "ontology/fire_safety.ttl",
        {"MaterialA": ["A-polymer"]},
    )
    assert store.relations("sample", "madeOf") == set()
    assert store.payload("sample")["material"] == "unknown 2 cm rod"


def test_wide_first_hop_preserves_budget_for_later_scientific_context():
    from types import SimpleNamespace

    registry = SemanticRegistry(
        target_classes={"Thing"},
        relations=[RelationDefinition("includes"), RelationDefinition("hasCondition")]
    )
    store = SemanticGraph(registry)
    store.add_entity("investigation", "Thing", ["E-fixture"])
    for i in range(6):
        run, condition = f"record-{i}", f"condition-{i}"
        store.add_entity(run, "Thing", ["E-fixture"])
        store.add_entity(condition, "Thing", ["E-fixture"])
        store.add_relation("investigation", "includes", run, ["E-fixture"])
        store.add_relation(run, "hasCondition", condition, ["E-fixture"])
    evidence = SimpleNamespace(resolve=lambda eid: {"text": "Fixture relationship"})
    result = navigate(
        store,
        "investigation",
        [RouteStep("includes"), RouteStep("hasCondition")],
        evidence,
        budget=3,
    )
    assert len(result["results"]) == 3
    assert result["truncated"]
    assert result["examined"] <= 2 * result["budget_per_step"]
    assert all(len(row["path"]) == 2 for row in result["results"])
