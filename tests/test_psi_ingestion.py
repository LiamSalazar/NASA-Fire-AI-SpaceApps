import hashlib
from pathlib import Path

from nasa_fire_ai.ingestion import parse_experimental_table
from nasa_fire_ai.ingestion.psi_canonical import canonicalize_psi98

ROOT = Path(__file__).resolve().parents[1]
RAW_TABLE = ROOT / "data/raw/psi/PSI-98_experimental_table.csv"


def test_psi98_canonical_records_are_derived_from_cached_nasa_csv():
    assert RAW_TABLE.exists(), "Run scripts/ingest_psi.py to retrieve the NASA PSI table."
    raw_text = RAW_TABLE.read_text(encoding="utf-8-sig")
    assert "Sample Thickness (cm)" in raw_text
    entities, runs = canonicalize_psi98(parse_experimental_table(raw_text), RAW_TABLE)
    assert (
        hashlib.sha256(RAW_TABLE.read_bytes()).hexdigest()
        == "c01f29c62455f0a3b512290ab85e5687ecded326733189f002f580368402308d"
    )
    assert [run["id"] for run in runs] == ["psi-98-S1", "psi-98-S2"]
    s1, s2 = runs
    assert s1["material"] == s2["material"] == "SIBAL Fabric"
    assert s1["flow_velocity_m_s"] == s2["flow_velocity_m_s"] == 0.20
    assert s1["oxygen_range_fraction"] == [0.215, 0.217]
    assert s2["oxygen_fraction"] == 0.215
    assert s1["flow_direction"] == "Concurrent" and s2["flow_direction"] == "Opposed"
    assert s1["burn_time_s"] == 420 and s2["burn_time_s"] == 70
    oxygen_entities = [item for item in entities if item.get("kind") == "oxygen"]
    assert any(item["reported_value"] == "21.5 - 21.7" for item in oxygen_entities)
    assert any(
        item["reported_value"] == "~ 21.5" and item["is_approximate"] for item in oxygen_entities
    )
