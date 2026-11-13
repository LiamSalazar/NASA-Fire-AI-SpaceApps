from pathlib import Path

from nasa_fire_ai.config import Settings
from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.models import NumericFilter, QueryIntent
from nasa_fire_ai.query.v2_execution import build_bundle_from_v1_as_v2
from nasa_fire_ai.services.pipeline import build_bundle


def test_v2_execution_uses_real_runs_and_evidence_bundle():
    root = Path(__file__).resolve().parents[1]
    registry = EvidenceRegistry(Settings(root=root).registry_path)
    intent = QueryIntent(
        materials=["PMMA"], flow_velocity=NumericFilter(operator="<=", value=20, unit="cm/s")
    )
    v1 = build_bundle(intent, "PMMA airflow <= 20 cm/s", root, registry)
    v2 = build_bundle_from_v1_as_v2(intent, "PMMA airflow <= 20 cm/s", root, registry)
    assert v2.bundle.query_intent == intent
    assert {x["id"] for x in v2.bundle.direct_evidence} == {x["id"] for x in v1.direct_evidence}
    assert all(
        registry.resolve(eid) for item in v2.bundle.direct_evidence for eid in item["evidence_ids"]
    )
