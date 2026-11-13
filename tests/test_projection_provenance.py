from pathlib import Path

from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.semantic import project_legacy


def test_normalized_projection_never_labels_canonical_units_as_source_reported():
    root = Path(__file__).resolve().parents[1]
    store = project_legacy(root, EvidenceRegistry(root / "data/index/evidence.sqlite"))
    value = store.values("psi-98-S1", "AirflowVelocity")[0]
    assert value.canonical_value == 0.2 and value.canonical_unit == "m/s"
    assert value.reported_value == 20 and value.reported_unit == "cm/s"
