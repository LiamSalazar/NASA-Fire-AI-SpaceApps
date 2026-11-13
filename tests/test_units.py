import pytest

from nasa_fire_ai.normalization import normalize


def test_units():
    assert normalize(5, "cm/s") == (0.05, "m/s")
    assert normalize(17, "%") == (0.17, "fraction")
    assert normalize(10, "kPa") == (10000, "Pa")
    assert normalize(2, "mm") == (0.002, "m")
    assert normalize(1, "atm") == (101325, "Pa")
    assert normalize(1, "bar") == (100000, "Pa")


def test_unknown_unit():
    with pytest.raises(ValueError):
        normalize(1, "furlong")


def test_standard_controller_capacity_is_distinct_from_actual_volumetric_flow():
    from nasa_fire_ai.normalization.units import interpret

    assert normalize(0.1, "slpm")[0] == pytest.approx(normalize(0.1, "l/min")[0])
    assert interpret("slpm")["canonical_unit"] != interpret("l/min")["canonical_unit"]


def test_source_units_with_dimensions_and_pressure_reference():
    from nasa_fire_ai.normalization.units import interpret

    assert normalize(10000, "psia") == (pytest.approx(68947572.93), "Pa")
    assert normalize(98, "Joules") == (98, "J")
    assert normalize(72, "ft-lbf") == (pytest.approx(97.6189), "J")
    assert normalize(1332, "cal/g") == (pytest.approx(5573088), "J/kg")
    # Affine scales convert with their offset, never as a pure factor.
    assert normalize(425, "°C") == (pytest.approx(698.15), "K")
    assert normalize(32, "°F") == (pytest.approx(273.15), "K")
    assert interpret("psia")["pressure_reference"] == "ABSOLUTE"
    assert interpret("psi")["pressure_reference"] == "UNSPECIFIED"
    # Gauge pressure has no stated ambient; it is never an absolute pressure.
    assert interpret("psig")["canonical_unit"] == "Pa_gauge"
    assert interpret("°C")["conversion"] == "AFFINE"
    # One dimension covers distinct quantities; the unit names no property.
    assert interpret("J")["dimension"] == interpret("ft-lbf")["dimension"] == "energy"
    assert "property" not in interpret("J")
    assert interpret("furlong") is None and interpret(None) is None


def test_common_laboratory_units_have_explicit_dimensions():
    from nasa_fire_ai.normalization.units import interpret

    assert interpret("msec")["dimension"] == "time"
    assert interpret("uL")["dimension"] == "volume"
    assert interpret("RPM")["dimension"] == "rotational_speed"
    assert interpret("pph")["dimension"] == "mass_flow"
    assert interpret("slm")["canonical_unit"] == "m3/s_standard"
    # A differential pressure never becomes an absolute pressure.
    assert interpret("psid")["canonical_unit"] == "Pa_differential"
    # A bare "F" is ambiguous and stays unestablished.
    assert interpret("F") is None
