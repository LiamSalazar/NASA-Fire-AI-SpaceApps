from nasa_fire_ai.query.name_spellings import compound_spellings


def test_acronym_suffix_can_use_its_registered_title_spelling():
    assert compound_spellings("Orbital Response Study—Return", ["ORION-R"]) == {"ORION-Return"}
    assert not compound_spellings("Orbital Response Study—Return", ["ORION"])
    assert not compound_spellings("Orbital Response Study—Return", ["ORION-X"])
    assert not compound_spellings("Orbital Response Study II", ["ORION-II"])
