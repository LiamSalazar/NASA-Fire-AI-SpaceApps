from nasa_fire_ai.ingestion.generic import profile_table, propose_table_role, resolve_column
from nasa_fire_ai.query.v2 import PropertyDefinition, SemanticRegistry


def test_generic_profiler_does_not_need_source_identity():
    columns = profile_table([{"Flow Vel. (cm/s)": "20", "Novel Value": "x"}])
    assert columns[0].raw_unit == "cm/s" and columns[0].datatype == "numeric"
    assert columns[1].datatype == "categorical"


def test_generic_profiler_and_resolver_do_not_use_source_identity():
    profile = profile_table([{"Temperature (K)": "300", "Unseen value": "9"}])[0]
    registry = SemanticRegistry(
        [PropertyDefinition("TestTemperature", "temperature", "K", aliases=["temperature"])]
    )
    resolved = resolve_column(profile, registry)
    assert resolved.status == "CANONICAL" and resolved.property_id == "TestTemperature"


def test_run_like_table_headers_only_propose_unreviewed_role():
    profiles = profile_table([{"Run ID": "1", "Temperature (K)": "300"}])
    role = propose_table_role(profiles)
    assert role == {
        "proposed_role": "ExperimentalRun",
        "authority": "UNREVIEWED_STRUCTURAL_HINT",
        "canonical": False,
    }
