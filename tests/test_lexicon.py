from nasa_fire_ai.query import parse_query
from nasa_fire_ai.query.lexicon import resolve


def test_alias_and_abbreviation_resolution():
    assert any(r.canonical_ids == ["material:pmma"] for r in resolve("polymethyl methacrylate"))
    assert any(r.canonical_ids == ["investigation:bass_ii"] for r in resolve("BASS"))


def test_ambiguous_and_unknown_are_not_silent():
    assert resolve("acrylic")[0].status == "ambiguous"
    assert resolve("unobtainium")[0].status == "unknown"


def test_parser_consumes_lexicon_and_distinguishes_flow():
    i = parse_query("polymethyl methacrylate microgravity airflow <= 20 cm/s")
    assert i.materials == ["PMMA"] and i.flow_velocity.unit == "cm/s"
    assert not parse_query("flame spread velocity").flow_velocity


def test_extinction_not_suppression_and_normative_types_distinct():
    assert not parse_query("extinction").safety_intents
    assert parse_query("guidance").safety_intents != parse_query("requirement").safety_intents
