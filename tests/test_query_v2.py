import pytest

from nasa_fire_ai.models import NumericFilter, QueryIntent
from nasa_fire_ai.query.v2 import (
    GenericMeasurement,
    GenericValue,
    PropertyConstraintV2,
    PropertyDefinition,
    QueryIntentV2,
    SemanticRegistry,
    classify_candidate_v2,
    evaluate_constraint,
    plan_v2,
    v1_to_v2,
)


def test_v1_maps_to_generic_constraints():
    q = v1_to_v2(
        QueryIntent(
            materials=["PMMA"], flow_velocity=NumericFilter(operator="<=", value=10, unit="cm/s")
        )
    )
    assert q.entity_constraints[0].relation == "hasMaterial"
    assert q.property_constraints[0].property_id == "AirflowVelocity"


def test_dynamic_property_needs_no_query_schema_change():
    registry = SemanticRegistry([PropertyDefinition("TestPropertyX", "temperature", "K")])
    assert (
        registry.validate(
            PropertyConstraintV2(
                property_id="TestPropertyX",
                operator="EQ",
                value=GenericValue(reported_value=300, reported_unit="K"),
            )
        ).reported_value
        == 300
    )
    with pytest.raises(ValueError):
        registry.validate(
            PropertyConstraintV2(
                property_id="TestPropertyX",
                operator="EQ",
                value=GenericValue(reported_value=2, reported_unit="m/s"),
            )
        )


def test_dynamic_temperature_range_and_generic_matching():
    registry = SemanticRegistry([PropertyDefinition("TestPropertyTemperature", "temperature", "K")])
    constraint = PropertyConstraintV2(
        property_id="TestPropertyTemperature",
        operator="BETWEEN",
        value=GenericValue(lower=20, upper=30, reported_unit="K"),
    )
    assert (
        evaluate_constraint(
            constraint, GenericValue(reported_value=25, reported_unit="K"), registry
        )
        == "MATCH"
    )


def test_dynamic_categorical_property_and_information_type():
    registry = SemanticRegistry(
        [PropertyDefinition("TestSurface", "none", None, datatype="categorical")]
    )
    registry.register_information_class("TestInformationObject")
    constraint = PropertyConstraintV2(
        property_id="TestSurface", operator="EQ", value=GenericValue(reported_value="rough")
    )
    assert (
        evaluate_constraint(constraint, GenericValue(reported_value="rough"), registry) == "MATCH"
    )
    registry.validate_intent(QueryIntentV2(requested_information=["TestInformationObject"]))


def test_generic_planner_and_staging_cannot_be_direct():
    registry = SemanticRegistry([PropertyDefinition("TestX", "temperature", "K")])
    constraint = PropertyConstraintV2(
        property_id="TestX",
        operator="EQ",
        value=GenericValue(reported_value=300, reported_unit="K"),
    )
    planned = plan_v2(QueryIntentV2(property_constraints=[constraint]), registry)
    assert planned.bm25_terms == ["TestX"]
    result, details = classify_candidate_v2(
        [constraint],
        [
            GenericMeasurement(
                "TestX",
                GenericValue(reported_value=300, reported_unit="K"),
                "x",
                "e",
                canonical=False,
            )
        ],
        registry,
    )
    assert result == "NO_DIRECT" and details["unknown"] == ["TestX"]
