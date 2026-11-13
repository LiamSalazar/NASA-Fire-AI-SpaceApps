"""Source-backed neutral development fixtures; these are not NASA observations."""

from dataclasses import replace

import pytest
from rdflib import RDFS, SKOS

from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.query.controlled_reasoning import validate_expansion
from nasa_fire_ai.query.expansion_contracts import (
    DiscoveryHypothesis,
    numeric_equivalence,
    validate_discovery,
)
from nasa_fire_ai.query.hierarchy import TaxonomyEdge, add_taxonomy_edge, traverse
from nasa_fire_ai.query.native import SemanticGraph, execute_native
from nasa_fire_ai.query.v2 import (
    EntityConstraintV2,
    GenericValue,
    PropertyConstraintV2,
    PropertyDefinition,
    QueryIntentV2,
    RelationDefinition,
    SemanticRegistry,
)


def fixture(tmp_path):
    registry = SemanticRegistry(
        [
            PropertyDefinition("SpeedX", "velocity", "m/s"),
            PropertyDefinition("PressureX", "pressure", "Pa"),
        ],
        relations=[RelationDefinition("usesX"), RelationDefinition("gravityX")],
    )
    registry.register_target_class("ExperimentalCondition")
    store = SemanticGraph(registry)
    evidence = EvidenceRegistry(tmp_path / "neutral.sqlite")
    evidence.add_source(
        {
            "source_id": "SyntheticAuthority",
            "title": "Neutral fixture",
            "url": "https://example.org/fixture",
        }
    )
    evidence.add_document("fixture", "SyntheticAuthority", "Neutral fixture")
    for eid in ("T-taxonomy", "E-a1", "E-a2", "E-b1", "E-family", "E-unknown"):
        evidence.add_passage(
            {
                "evidence_id": eid,
                "document_id": "fixture",
                "page": None,
                "section": "Synthetic fixture",
                "text": eid + " neutral test evidence",
                "raw_file": None,
                "checksum": None,
                "start_offset": None,
                "end_offset": None,
            }
        )
    registry.entities.update(
        {"FamilyA", "SubfamilyA", "MaterialA1", "MaterialA2", "FamilyB", "MaterialB1", "GravityX"}
    )
    edges = []
    for child, parent in [
        ("SubfamilyA", "FamilyA"),
        ("MaterialA1", "SubfamilyA"),
        ("MaterialA2", "SubfamilyA"),
        ("MaterialB1", "FamilyB"),
    ]:
        edge = TaxonomyEdge(
            child,
            str(RDFS.subClassOf),
            parent,
            "Synthetic reviewer",
            "APPROVED",
            "Neutral fixture taxonomy",
            "usesX",
            "1",
            ("T-taxonomy",),
            "class",
            "class",
        )
        add_taxonomy_edge(store, edge)
        edges.append(edge)
    for run, material, speed in [
        ("a1", "MaterialA1", 0.1),
        ("a2", "MaterialA2", 0.2),
        ("b1", "MaterialB1", 0.1),
        ("family", "FamilyA", None),
        ("unknown", "MaterialA1", None),
    ]:
        store.add_entity(run, "ExperimentalRun", ["E-" + run], ["SyntheticAuthority"])
        store.add_relation(run, "usesX", material, ["E-" + run])
        store.add_relation(run, "gravityX", "GravityX", ["E-" + run])
        if speed is not None:
            store.add_value(
                "speed-" + run,
                run,
                "SpeedX",
                GenericValue(reported_value=speed, reported_unit="m/s"),
                ["E-" + run],
                {"context": "design_target"},
                class_id="ExperimentalCondition",
            )
    return store, evidence, edges


def intent(material, speed=None):
    return QueryIntentV2(
        targets=["ExperimentalRun"],
        entity_constraints=[EntityConstraintV2(relation="usesX", entity_id=material)],
        property_constraints=[]
        if speed is None
        else [
            PropertyConstraintV2(
                property_id="SpeedX",
                operator="EQ",
                value=GenericValue(reported_value=speed, reported_unit="m/s"),
            )
        ],
    )


def test_broad_specific_sibling_and_family_provenance(tmp_path):
    store, evidence, _ = fixture(tmp_path)
    broad = execute_native(
        intent("FamilyA"), "FamilyA", store, evidence, hierarchical=True, relational=True
    ).bundle
    assert {x["id"] for x in broad.direct_evidence} == {"a1", "a2", "family", "unknown"}
    assert "b1" not in {x["id"] for x in broad.direct_evidence + broad.related_evidence}
    specific = execute_native(
        intent("MaterialA1"), "MaterialA1", store, evidence, hierarchical=True, relational=True
    ).bundle
    assert {x["id"] for x in specific.direct_evidence} == {"a1", "unknown"}
    assert {x["id"] for x in specific.related_evidence} == {"a2", "family"}
    sibling = next(x for x in specific.related_evidence if x["id"] == "a2")
    relation = sibling["relationship_explanation"]["dimensions"][0]["relationships"][0]
    assert relation["relationship_type"] == "SIBLING"
    assert relation["depth"] == 2
    assert relation["taxonomy_evidence_ids"] == ["T-taxonomy"]
    assert sibling["evidence_ids"] == ["E-a2"]
    assert "family behavior" in sibling["relationship_explanation"]["cannot_conclude"]


def test_conditions_unknown_design_context_and_default_rollback(tmp_path):
    store, evidence, _ = fixture(tmp_path)
    bundle = execute_native(
        intent("MaterialA1", 0.2), "q", store, evidence, hierarchical=True, relational=True
    ).bundle
    assert not bundle.direct_evidence
    a1 = next(x for x in bundle.related_evidence if x["id"] == "a1")
    unknown = next(x for x in bundle.related_evidence if x["id"] == "unknown")
    assert a1["differs"] == ["SpeedX"]
    assert unknown["unknown"] == ["SpeedX"] and not unknown["differs"]
    value = a1["relationship_explanation"]["dimensions"][1]["actual"][0]
    assert value["value"]["reported_value"] == 0.1
    assert value["qualifiers"]["context"] == "design_target"
    exact = execute_native(intent("FamilyA"), "q", store, evidence, hierarchical=False).bundle
    assert {x["id"] for x in exact.direct_evidence} == {"family"}


def test_cycles_duplicates_unreviewed_edges_and_dynamic_concepts(tmp_path):
    store, evidence, edges = fixture(tmp_path)
    add_taxonomy_edge(store, replace(edges[0], subject="FamilyA", object="SubfamilyA"))
    add_taxonomy_edge(store, edges[0])
    add_taxonomy_edge(
        store, replace(edges[0], subject="FamilyB", object="FamilyA", review_state="PENDING")
    )
    receipt = traverse(store, "FamilyA", "usesX", evidence)
    assert "FamilyB" not in receipt["paths"]
    assert receipt["visits"] <= 128
    assert all(p["depth"] <= 4 for p in receipt["paths"].values())
    store.registry.entities.add("DynamicNeutral")
    add_taxonomy_edge(store, replace(edges[0], subject="DynamicNeutral", object="FamilyA"))
    assert "DynamicNeutral" in traverse(store, "FamilyA", "usesX", evidence)["paths"]
    assert len(receipt["paths"]) == len(set(receipt["paths"]))
    assert traverse(store, "FamilyA", "wrong_scope", evidence)["paths"] == {}


def test_skos_broader_is_discovery_not_membership_and_missing_refs_fail_closed(tmp_path):
    store, evidence, edges = fixture(tmp_path)
    store.registry.entities.update({"ConceptX", "ConceptY"})
    edge = replace(
        edges[0],
        subject="ConceptX",
        object="ConceptY",
        predicate=str(SKOS.broader),
        subject_kind="concept",
        object_kind="concept",
    )
    add_taxonomy_edge(store, edge)
    assert not traverse(store, "ConceptY", "usesX", evidence)["paths"]["ConceptX"]["category_match"]
    add_taxonomy_edge(
        store, replace(edge, subject="FamilyB", object="FamilyA", evidence_ids=("E-absent",))
    )
    assert "FamilyB" not in traverse(store, "FamilyA", "usesX", evidence)["paths"]
    with pytest.raises(ValueError):
        add_taxonomy_edge(store, replace(edge, predicate=str(RDFS.subClassOf)))


@pytest.mark.parametrize(
    ("original", "expanded", "valid"),
    [
        ("airflow >= 20 cm/s", "airflow > 20 cm/s", False),
        ("airflow <= 20 cm/s", "airflow < 20 cm/s", False),
        ("airflow = 10 cm/s", "airflow = 0.10 m/s", True),
        ("airflow >= 20 cm/s", "airflow at least 0.2 m/s", True),
        ("airflow between 0.01 and 0.11 m/s", "airflow from 1 to 11 cm/s", True),
        (
            "airflow between 0.01 and 0.11 m/s inclusive",
            "airflow between 0.01 and 0.11 m/s exclusive",
            False,
        ),
        ("airflow 0.01 ± 0.005 m/s", "airflow 1 +/- 0.5 cm/s", True),
        ("airflow about 20 cm/s", "airflow 20 cm/s", False),
        ("airflow 0.01 ± 0.005 m/s", "airflow 0.01 m/s", False),
    ],
)
def test_numeric_equivalent_contract(original, expanded, valid):
    assert numeric_equivalence(original, expanded)[0] is valid


def test_discovery_never_changes_original_intent(tmp_path):
    store, evidence, _ = fixture(tmp_path)
    q = intent("MaterialA1", 0.1)
    before = q.model_dump_json()
    hypothesis = DiscoveryHypothesis(
        query="MaterialA2",
        relationship="SIBLING_DISCOVERY",
        requested_concept="MaterialA1",
        proposed_concept="MaterialA2",
    )
    assert validate_discovery(hypothesis, q, store, evidence)[0]
    assert not validate_discovery(
        hypothesis.model_copy(update={"proposed_concept": "MaterialB1"}), q, store, evidence
    )[0]
    assert q.model_dump_json() == before
    assert not validate_expansion(
        "speed >= 20 cm/s", "speed > 20 cm/s", QueryIntentV2(), store.registry
    )[0]
    assert (
        validate_expansion("speed = 10 cm/s", "speed = 0.10 m/s", QueryIntentV2(), store.registry)[
            0
        ]
        is True
    )


def test_range_uncertainty_preserved_at_boundary(tmp_path):
    from nasa_fire_ai.query.v2 import evaluate_constraint

    store, _, _ = fixture(tmp_path)
    q = PropertyConstraintV2(
        property_id="SpeedX",
        operator="BETWEEN",
        value=GenericValue(
            lower=0.1, upper=0.2, reported_unit="m/s", raw_expression="between 0.1 and 0.2 m/s"
        ),
    )
    value = GenericValue(reported_value=0.1, reported_unit="m/s")
    assert evaluate_constraint(q, value, store.registry) == "UNKNOWN"
    q.value.raw_expression += " inclusive"
    assert evaluate_constraint(q, value, store.registry) == "MATCH"
    q.value.raw_expression = "between 0.1 and 0.2 m/s exclusive"
    assert evaluate_constraint(q, value, store.registry) == "DIFFER"


def test_grouped_material_union_preserves_conjunctive_boundary(tmp_path):
    from nasa_fire_ai.query.controlled_reasoning import ControlledReasoningFlags
    from nasa_fire_ai.services.native import answer_native_controlled

    store, evidence, _ = fixture(tmp_path)
    q = intent("MaterialA1")
    q.entity_constraints.append(EntityConstraintV2(relation="usesX", entity_id="MaterialA2"))
    q.clarification_required = True
    q.ambiguities = ["multiple_values_for_relation:usesX"]
    response = answer_native_controlled(
        q,
        "MaterialA1 and MaterialA2",
        store,
        evidence,
        flags=ControlledReasoningFlags(hierarchical_retrieval=True, relational_related=True),
    )
    assert len(response.execution.bundle.retrieval_metadata["grouped_search"]) == 2
    assert q.clarification_required
    assert "do not establish a single experiment" in response.rendered_answer
    conjunctive = answer_native_controlled(
        q,
        "MaterialA1 and MaterialA2 in the same experiment",
        store,
        evidence,
        flags=ControlledReasoningFlags(hierarchical_retrieval=True),
    )
    assert not conjunctive.execution.bundle.retrieval_metadata.get("grouped_search")


def test_missing_experimental_provenance_and_malformed_taxonomy_fail_safely(tmp_path):
    from rdflib import RDF, Literal

    from nasa_fire_ai.query.native import NS, node

    store, evidence, _ = fixture(tmp_path)
    store.add_entity("broken-run", "ExperimentalRun", ["E-missing"], ["SyntheticAuthority"])
    store.add_relation("broken-run", "usesX", "MaterialA1", ["E-missing"])
    result = execute_native(intent("MaterialA1"), "q", store, evidence, hierarchical=True)
    assert "broken-run" not in {
        r["id"] for r in result.bundle.direct_evidence + result.bundle.related_evidence
    }
    assert result.bundle.retrieval_metadata["provenance_exclusions"]
    record = next(store.graph.subjects(RDF.type, RDF.Statement))
    store.graph.set((record, RDF.object, node("FamilyB")))
    result = execute_native(intent("MaterialA1"), "q", store, evidence, hierarchical=True)
    assert result.bundle.retrieval_metadata["hierarchical_retrieval"]["error"] == "ValueError"
    assert "a1" in {r["id"] for r in result.bundle.direct_evidence}
    store.graph.set((record, NS.payload, Literal("invalid json")))
    result = execute_native(intent("MaterialA1"), "q", store, evidence, hierarchical=True)
    assert result.bundle.direct_evidence


def test_selective_reranking_skips_adequate_exact_lookup(tmp_path):
    from nasa_fire_ai.query.controlled_reasoning import ControlledReasoningFlags, run_ablation

    store, evidence, _ = fixture(tmp_path)

    class NoCall:
        model_identity = "test-no-call"

        def rerank(self, *_args):
            raise AssertionError("unnecessary inference")

    q = intent("MaterialB1")
    trace = run_ablation(
        "MaterialB1",
        q,
        store,
        evidence,
        reasoner=NoCall(),
        flags=ControlledReasoningFlags(
            hierarchical_retrieval=True, contextual_reranking=True, selective_reranking=True
        ),
    )
    assert trace["selective_reranking"]["reason"] == "adequate_deterministic_evidence"
    assert trace["configurations"]["C"]["calls"] == 0


def test_family_document_is_not_a_subtype_experiment(tmp_path):
    store, evidence, _ = fixture(tmp_path)
    store.add_entity("family-document", "Publication", ["E-family"], ["SyntheticAuthority"])
    store.add_relation("family-document", "usesX", "FamilyA", ["E-family"])
    q = intent("MaterialA1")
    experiment_results = execute_native(q, "q", store, evidence, hierarchical=True).bundle
    assert "family-document" not in {
        r["id"] for r in experiment_results.direct_evidence + experiment_results.related_evidence
    }
    q.targets = ["Publication"]
    documentary = execute_native(q, "q", store, evidence, hierarchical=True).bundle
    assert not documentary.direct_evidence
    assert documentary.related_evidence[0]["id"] == "family-document"


def test_cache_receipts_do_not_count_replayed_calls():
    from test_controlled_reasoning import FakeClient

    from nasa_fire_ai.query.controlled_reasoning import NemotronControlledReasoner

    model = NemotronControlledReasoner(
        FakeClient({"queries": ["neutral document"]}), "test", SemanticRegistry()
    )
    first = model.expand("neutral evidence", QueryIntentV2())
    second = model.expand("neutral evidence", QueryIntentV2())
    assert first["new_calls"] == 1
    assert second["new_calls"] == 0
    assert second["execution_mode"] == "COMPATIBLE_CACHE_REPLAY"


@pytest.mark.parametrize(
    ("original", "expanded"), [("20 mph", "20 km/h"), ("20 psi", "20 atm"), ("20°C", "20°F")]
)
def test_unknown_numeric_units_cannot_establish_equivalence(original, expanded):
    assert not numeric_equivalence(original, expanded)[0]


def test_equivalent_query_cannot_drop_unresolved_scientific_concept():
    registry = SemanticRegistry()
    q = QueryIntentV2(unresolved_mentions=["NeutralUnknown"])
    assert not validate_expansion("NeutralUnknown fire at 20 cm/s", "fire at 20 cm/s", q, registry)[
        0
    ]


def test_invalid_declarative_taxonomy_does_not_break_exact_projection(tmp_path):
    from nasa_fire_ai.query.hierarchy import load_taxonomy

    store, evidence, _ = fixture(tmp_path)
    load_taxonomy(store, {"edges": [{"subject": "unregistered"}], "proposals": []})
    assert store.taxonomy_load_errors
    result = execute_native(intent("MaterialA1"), "q", store, evidence, hierarchical=True)
    assert "a1" in {r["id"] for r in result.bundle.direct_evidence}
