from nasa_fire_ai.models import NumericFilter, QueryIntent
from nasa_fire_ai.query import build_sparql, classify_runs


def test_deterministic_sparql():
    q = build_sparql(
        QueryIntent(materials=["PMMA"], oxygen=NumericFilter(operator="<", value=18, unit="%"))
    )
    assert "PMMA" in q and "0.18" in q


def test_context_isolation_direct_related_no_direct():
    runs = [
        {"id": "A", "material": "PMMA", "gravity": "microgravity", "oxygen_fraction": 0.17},
        {"id": "B", "material": "PMMA", "gravity": "microgravity", "oxygen_fraction": 0.21},
    ]
    i = QueryIntent(
        materials=["PMMA"],
        gravity_conditions=["microgravity"],
        oxygen=NumericFilter(operator="<", value=18, unit="%"),
    )
    direct, related = classify_runs(i, runs)
    assert [x.run["id"] for x in direct] == ["A"]
    assert [x.run["id"] for x in related] == ["B"]
    i2 = QueryIntent(materials=["nylon"])
    d, r = classify_runs(i2, runs)
    assert not d and not r


def test_related_is_not_open_question():
    d, r = classify_runs(
        QueryIntent(materials=["PMMA"], oxygen=NumericFilter(operator="<", value=10, unit="%")),
        [{"id": "A", "material": "PMMA", "oxygen_fraction": 0.21}],
    )
    assert not d and r and all("open" not in x.run for x in r)
