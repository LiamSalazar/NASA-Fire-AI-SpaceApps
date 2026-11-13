from pathlib import Path
from unittest.mock import patch

import pytest
from pyshacl import validate

from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.query.native import SemanticGraph, execute_native
from nasa_fire_ai.query.v2 import (
    EntityConstraintV2,
    GenericValue,
    PropertyConstraintV2,
    PropertyDefinition,
    QueryIntentV2,
    RelationDefinition,
    SemanticRegistry,
    evaluate_constraint,
)


@pytest.fixture
def setup(tmp_path):
    registry = SemanticRegistry(
        [PropertyDefinition("UnseenProperty", "velocity", "m/s")],
        relations=[RelationDefinition("UnseenRelation")],
    )
    store = SemanticGraph(registry)
    evidence = EvidenceRegistry(tmp_path / "evidence.sqlite")
    for subject in ("a", "b", "c"):
        store.add_entity(subject, "ExperimentalRun", ["E-" + subject], ["source"])
    registry.entities.add("reviewed-entity")
    for subject, value in (("a", 0.2), ("b", 0.3)):
        store.add_relation(subject, "UnseenRelation", "reviewed-entity", ["E-" + subject])
        store.add_value(
            "value-" + subject,
            subject,
            "UnseenProperty",
            GenericValue(reported_value=value, reported_unit="m/s"),
            ["E-" + subject],
        )
    return store, evidence


def test_native_execution_cannot_call_legacy(setup):
    store, evidence = setup
    q = QueryIntentV2(
        targets=["ExperimentalRun"],
        entity_constraints=[
            EntityConstraintV2(relation="UnseenRelation", entity_id="reviewed-entity")
        ],
        property_constraints=[
            PropertyConstraintV2(
                property_id="UnseenProperty",
                operator="EQ",
                value=GenericValue(reported_value=20, reported_unit="cm/s"),
            )
        ],
    )
    with (
        patch(
            "nasa_fire_ai.services.pipeline.build_bundle", side_effect=AssertionError("V1 called")
        ),
        patch("nasa_fire_ai.query.matching.classify_runs", side_effect=AssertionError("V1 called")),
        patch(
            "nasa_fire_ai.query.v2_execution.build_bundle_from_v1_as_v2",
            side_effect=AssertionError("compat called"),
        ),
    ):
        result = execute_native(q, "unseen query", store, evidence)
    assert [x["id"] for x in result.bundle.direct_evidence] == ["a"]
    assert [x["id"] for x in result.bundle.related_evidence] == ["b"]
    assert result.bundle.related_evidence[0]["differs"] == ["UnseenProperty"]


def test_approximation_no_invented_tolerance(setup):
    store, _ = setup
    c = PropertyConstraintV2(
        property_id="UnseenProperty",
        operator="APPROX",
        value=GenericValue(reported_value=0.2, reported_unit="m/s", approximate=True),
    )
    actual = GenericValue(reported_value=0.2, reported_unit="m/s")
    assert evaluate_constraint(c, actual, store.registry) == "UNKNOWN"
    c.value.tolerance = 0.01
    assert evaluate_constraint(c, actual, store.registry) == "MATCH"
    assert (
        evaluate_constraint(
            c, GenericValue(reported_value=0.3, reported_unit="m/s"), store.registry
        )
        == "DIFFER"
    )


def test_unit_and_missing_value_safety(setup):
    store, evidence = setup
    c = PropertyConstraintV2(
        property_id="UnseenProperty",
        operator="EQ",
        value=GenericValue(reported_value=0.2, reported_unit="m/s"),
    )
    assert (
        evaluate_constraint(c, GenericValue(reported_value=0.2, reported_unit="Pa"), store.registry)
        == "INVALID"
    )
    q = QueryIntentV2(targets=["ExperimentalRun"], property_constraints=[c])
    assert "c" not in [
        x["id"] for x in execute_native(q, "q", store, evidence).bundle.direct_evidence
    ]
    store.registry.register(
        PropertyDefinition("Candidate", "velocity", "m/s", status="CANDIDATE_NEW_CONCEPT")
    )
    assert store.registry.resolve_property("Candidate")[0] == "UNKNOWN"


def test_generic_graph_shacl(setup):
    store, _ = setup
    root = Path(__file__).resolve().parents[1]
    assert validate(store.graph, shacl_graph=str(root / "ontology/semantic_shapes.ttl"))[0]
