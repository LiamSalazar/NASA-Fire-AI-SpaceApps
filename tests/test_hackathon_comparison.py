"""Real NASA comparisons plus explicitly synthetic compatibility adversaries."""

from pathlib import Path

import pytest

from nasa_fire_ai.ingestion.hackathon import build_snapshot, make_store
from nasa_fire_ai.query.native import compare_native
from nasa_fire_ai.query.scenario import ScenarioInput
from nasa_fire_ai.query.v2 import EntityConstraintV2, GenericValue
from nasa_fire_ai.services.claim_verification import verify_claim
from nasa_fire_ai.services.search import ScientificSearchService

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def engine(tmp_path_factory):
    path = tmp_path_factory.mktemp("comparison") / "snapshot"
    build_snapshot(ROOT, path)
    service = ScientificSearchService(path, ROOT)
    yield service
    service.close()


def test_real_saffire_matrix_preserves_originals_and_evidence(engine):
    result = engine.search("Compare Saffire I S1 and S2", assist=True)
    rows = {r["dimension"]: r for r in result.comparison["matrix"]}
    assert rows["AirflowVelocity"]["status"] == "MATCH"
    assert rows["FlowDirection"]["status"] == "DIFFER"
    assert rows["source:burn_time"]["status"] == "DIFFER"
    assert rows["OxygenConcentration"]["status"] == "UNKNOWN"  # explicit approximation
    assert rows["hasGravityCondition"]["status"] == "UNKNOWN"
    burns = rows["source:burn_time"]["values"]
    assert burns["psi-98-S1"][0]["qualifiers"]["original_value"] == "420"
    assert burns["psi-98-S2"][0]["qualifiers"]["original_value"] == "70"
    assert burns["psi-98-S1"][0]["value"]["reported_unit"] == "s"
    for cell in rows.values():
        for values in cell["values"].values():
            for record in values:
                assert record["evidence_ids"]
                assert all(engine.registry.resolve(eid) for eid in record["evidence_ids"])
    assert any(c["epistemic_type"] == "comparison_result" for c in result.claims)
    assert all(v["status"].startswith("SUPPORTED") for v in result.verification)


def test_real_initial_and_final_values_are_separate(engine):
    comparison = compare_native(engine.store, ["psi-25-B1", "psi-25-B2"], ["OxygenConcentration"])
    assert {r["context"] for r in comparison.matrix} == {"initial", "final"}
    assert all(
        {v["qualifiers"]["context"] for values in r["values"].values() for v in values}
        <= {r["context"]}
        for r in comparison.matrix
    )


def synthetic_store():
    """Logical data invented for unit compatibility tests, never NASA evidence."""
    store = make_store(ROOT)
    for subject in ("synthetic-a", "synthetic-b"):
        store.add_entity(subject, "ExperimentalRun", ["SYNTHETIC"])
    return store


@pytest.mark.parametrize(
    "case, expected",
    [
        ("units", "MATCH"),
        ("modality", "NOT_COMPARABLE"),
        ("conflict", "CONFLICT"),
        ("missing", "UNKNOWN"),
    ],
)
def test_synthetic_comparison_compatibility(case, expected):
    store = synthetic_store()
    store.add_value(
        "a-value",
        "synthetic-a",
        "AirflowVelocity",
        GenericValue(reported_value=20, reported_unit="cm/s"),
        ["SYNTHETIC"],
        {"modality": "reported_condition"},
    )
    if case != "missing":
        store.add_value(
            "b-value",
            "synthetic-b",
            "AirflowVelocity",
            GenericValue(reported_value=0.2, reported_unit="m/s"),
            ["SYNTHETIC"],
            {"modality": "simulated" if case == "modality" else "reported_condition"},
        )
    if case == "conflict":
        store.add_value(
            "b-conflict",
            "synthetic-b",
            "AirflowVelocity",
            GenericValue(reported_value=0.3, reported_unit="m/s"),
            ["SYNTHETIC"],
            {"modality": "reported_condition"},
        )
    assert (
        compare_native(store, ["synthetic-a", "synthetic-b"], ["AirflowVelocity"]).matrix[0][
            "status"
        ]
        == expected
    )


def test_identity_levels_and_partial_gravity_not_equated(engine):
    matrix = compare_native(
        engine.store, ["psi-98-S1", "psi-98-S1-value-9"], ["source:burn_time"]
    ).matrix
    assert matrix[0]["status"] == "NOT_COMPARABLE"
    result = engine.analyze_scenario(
        ScenarioInput(
            scenario_id="lunar",
            question="PMMA oxygen 22.2 %",
            provenance="team_simulator",
            entity_constraints=[
                EntityConstraintV2(relation="hasGravityCondition", entity_id="lunar")
            ],
            simulator_results=[{"burn_time": 99, "origin": "team_simulator"}],
        )
    )
    assert not result.evidence["direct"]
    assert "hasGravityCondition=lunar" in result.uncertainties
    assert any(c.get("entity_id") == "lunar" for c in result.provided_conditions)
    assert "hasGravityCondition" not in result.unspecified_conditions
    assert not result.accredited_observations
    assert result.scenario.simulator_results
    assert "lunar" not in engine.store.registry.entities


def test_simulator_output_stays_separate_and_ranking_reconstructs(engine):
    result = engine.analyze_scenario(
        ScenarioInput(
            scenario_id="airflow",
            question="Saffire I airflow 20 cm/s",
            provenance="team_simulator",
            simulator_results=[{"invented_prediction": 987654}],
        )
    )
    assert result.evidence["direct"]
    assert result.accredited_observations
    assert result.unspecified_conditions
    for row in result.evidence["direct"] + result.evidence["related"]:
        weights = row["ranking_features"]["scientific_relevance"]["weights"]
        assert row["ranking_score"] == sum(weights[r["status"]] for r in row["constraints"])
        assert "987654" not in str(row)
    assert any(path for row in result.evidence["direct"] for path in row["ontology_paths"])


def test_comparison_claim_is_recomputed_and_tampering_rejected(engine):
    from nasa_fire_ai.models import GroundedClaim
    from nasa_fire_ai.query.native import execute_native
    from nasa_fire_ai.services.scientific_synthesis import select_claims

    intent = engine.interpret("Compare Saffire I S1 and S2")
    execution = execute_native(
        intent,
        "Compare Saffire I S1 and S2",
        engine.store,
        engine.registry,
        hierarchical=True,
        relational=True,
        schema_hierarchical=True,
    )
    claims, _ = select_claims(execution.bundle)
    claim = next(c for _, c in claims if c.epistemic_type == "comparison_result")
    assert verify_claim(claim, execution.bundle, engine.registry, store=engine.store)[
        "status"
    ].startswith("SUPPORTED")
    bad = GroundedClaim.model_validate(claim.model_dump())
    bad.support_spans[0]["comparison_row"]["status"] = (
        "DIFFER" if bad.support_spans[0]["comparison_row"]["status"] == "MATCH" else "MATCH"
    )
    assert (
        verify_claim(bad, execution.bundle, engine.registry, store=engine.store)["status"]
        == "UNSUPPORTED"
    )


def test_missing_evidence_cannot_be_direct(engine, monkeypatch):
    from nasa_fire_ai.query.v2 import PropertyConstraintV2, QueryIntentV2

    store = synthetic_store()
    store.add_value(
        "synthetic-value",
        "synthetic-a",
        "AirflowVelocity",
        GenericValue(reported_value=20, reported_unit="cm/s"),
        ["MISSING-EVIDENCE"],
    )
    monkeypatch.setattr(engine, "store", store)
    result = engine.search(
        "logical fixture",
        intent=QueryIntentV2(
            targets=["ExperimentalRun"],
            property_constraints=[
                PropertyConstraintV2(
                    property_id="AirflowVelocity",
                    operator="EQ",
                    value=GenericValue(reported_value=20, reported_unit="cm/s"),
                )
            ],
        ),
    )
    assert not result.direct
