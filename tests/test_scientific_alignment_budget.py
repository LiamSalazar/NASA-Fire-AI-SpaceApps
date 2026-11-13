"""Bounded verification must give later independent claims a fair check."""

from types import SimpleNamespace

from nasa_fire_ai.services.conversation import ConversationService, paragraph_spans


def test_quantified_alignment_reaches_values_before_generic_instrument_descriptions():
    from nasa_fire_ai.services.conversation import rank_alignment_candidates

    descriptions = [
        {
            "support_id": f"description-{i}",
            "text": "The violet camera records a signal and an image.",
            "source_roles": ["Instrument"],
            "scientific_subjects": ["vega"],
        }
        for i in range(12)
    ]
    target = {
        "support_id": "quantified",
        "text": "The size uncertainty was estimated as ±0.073 mm.",
        "scientific_subjects": ["vega"],
    }
    metadata = {
        "support_id": "identifier",
        "text": "The violet camera report identifier is 73.",
        "source_roles": ["Instrument"],
        "scientific_subjects": ["vega"],
    }
    wrong_owner = {**target, "support_id": "wrong-owner", "scientific_subjects": ["lyra"]}
    ranked = rank_alignment_candidates(
        "VEGA camera size uncertainty was ±73 µm.",
        [*descriptions, metadata, wrong_owner, target],
        "vega",
    )
    assert ranked[0]["support_id"] == "quantified"
    assert ranked[-1]["support_id"] == "wrong-owner"


def test_later_claim_is_checked_after_earlier_alignment_budget_exhaustion():
    texts = {"a": "The vessel contains neon.", "b": "The sensor records luminosity."}
    registry = SimpleNamespace(resolve=lambda eid: {"text": texts[eid]})
    search = SimpleNamespace(registry=registry)
    service = ConversationService(
        search,
        entailment=SimpleNamespace(check=lambda p, h: {"supported": h in p}),
        max_alignment_checks=1,
    )
    anchors = {
        k: {
            "support_id": k,
            "text": v,
            "spans": [{"evidence_id": k, "text": v}],
            "category": "DOCUMENTARY",
            "epistemic_type": "documentary_content",
            "conditions": [],
        }
        for k, v in texts.items()
    }
    _, first = service._align_claim("A fabricated mechanism changes the vessel.", [], anchors)
    assert not first["supported"]
    _, second = service._align_claim("The sensor records luminosity.", [], anchors)
    assert second["supported"]
    assert service._alignment_exhausted


def test_long_inventory_preserves_complete_original_lines():
    text = "Recorded optical channels\n" + "\n".join(
        f"Channel {i} records an independent spectral band with its original context"
        for i in range(40)
    )
    spans = list(paragraph_spans(text))
    assert len(spans) > 1
    assert all(s in text for s in spans)
    assert all(f"Channel {i} records" in "\n".join(spans) for i in range(40))


def test_lexical_need_overlap_never_establishes_communication():
    service = ConversationService(SimpleNamespace())
    assert not service._need_is_communicated(
        {"need": "sensor measured spectral temperature"},
        [{"text": "The sensor did not measure spectral temperature."}],
    )


def test_redundancy_does_not_merge_equal_values_from_distinct_phases_or_studies():
    service = ConversationService(
        SimpleNamespace(), entailment=SimpleNamespace(check=lambda p, h: {"supported": True})
    )
    paragraphs = [
        "Study Vega initial pressure was 4 Pa.",
        "Study Vega final pressure was 4 Pa.",
        "Study Lyra initial pressure was 4 Pa.",
    ]
    trace = {
        "support_inventory": [
            {"support_id": str(i), "document_id": source}
            for i, source in enumerate(("vega", "vega", "lyra"))
        ],
        "accepted_statements": [
            {"text": text, "support_ids": [str(i)]} for i, text in enumerate(paragraphs)
        ],
    }
    assert service._deduplicate_answer(paragraphs, trace) == paragraphs


def test_missing_abbreviation_cannot_be_expanded_by_permissive_nli():
    from nasa_fire_ai.services.semantic_support import verify_paraphrase

    source = "Channel offset: n/a"
    registry = SimpleNamespace(resolve=lambda eid: {"text": source})
    anchor = {
        "text": source,
        "spans": [{"evidence_id": "a", "text": source}],
        "category": "DOCUMENTARY",
        "epistemic_type": "documentary_content",
        "conditions": [],
    }
    optimistic = SimpleNamespace(check=lambda p, h: {"supported": True})
    assert not verify_paraphrase(
        "The channel offset is not applicable.", [anchor], registry, optimistic
    )["supported"]
    assert verify_paraphrase(source, [anchor], registry, optimistic)["supported"]


def test_property_alignment_rejects_same_number_from_unrelated_optical_field_before_nli():
    from nasa_fire_ai.query.v2 import PropertyDefinition
    from nasa_fire_ai.services.semantic_support import verify_paraphrase

    definition = PropertyDefinition(
        "LensAperture", "length", "m", aliases=["lens aperture", "optical opening"]
    )
    source = "The display annotation is 2 mm."
    registry = SimpleNamespace(
        resolve=lambda eid: {"text": source}, scientific_properties={"LensAperture": definition}
    )
    anchor = {
        "text": source,
        "spans": [{"evidence_id": "a", "text": source}],
        "category": "DOCUMENTARY",
        "epistemic_type": "documentary_content",
        "conditions": [],
    }

    def unexpected(premise, hypothesis):
        raise AssertionError("A known property mismatch must not invoke NLI")

    result = verify_paraphrase(
        "The lens aperture is 2 mm.", [anchor], registry, SimpleNamespace(check=unexpected)
    )
    assert not result["supported"]
    source = "The optical opening is 2 mm."
    anchor["text"] = source
    anchor["spans"][0]["text"] = source
    assert verify_paraphrase(
        "The lens aperture is 2 mm.",
        [anchor],
        registry,
        SimpleNamespace(check=lambda p, h: {"supported": True}),
    )["supported"]


def test_simulation_is_not_an_observation_even_with_permissive_nli():
    from nasa_fire_ai.services.semantic_support import verify_paraphrase

    source = "The numerical model predicted an emission peak at 9 nm."
    registry = SimpleNamespace(resolve=lambda eid: {"text": source})
    anchor = {
        "text": source,
        "spans": [{"evidence_id": "a", "text": source}],
        "category": "DOCUMENTARY",
        "epistemic_type": "documentary_content",
        "conditions": [],
    }
    optimistic = SimpleNamespace(check=lambda p, h: {"supported": True})
    assert not verify_paraphrase(
        "The sensor observed an emission peak at 9 nm.", [anchor], registry, optimistic
    )["supported"]
    assert verify_paraphrase(
        "The model predicted an emission peak at 9 nm.", [anchor], registry, optimistic
    )["supported"]


def test_named_materials_and_categorical_percentages_cannot_borrow_other_field_values():
    from nasa_fire_ai.query.v2 import PropertyDefinition
    from nasa_fire_ai.services.semantic_support import verify_paraphrase

    source = "Panel material: Astrafloss. Bottle label: 100% CH4. Fuel concentration: 70%."
    definitions = {
        "MaterialLabel": PropertyDefinition(
            "MaterialLabel", "none", None, datatype="categorical", aliases=["panel material"]
        ),
        "BottleLabel": PropertyDefinition(
            "BottleLabel", "none", None, datatype="categorical", aliases=["bottle label"]
        ),
    }
    registry = SimpleNamespace(
        resolve=lambda eid: {"text": source},
        scientific_properties=definitions,
        scientific_entities={
            "astra": {"relation": "hasMaterial", "aliases": ["Astrafloss", "AFLEX"]},
            "nexo": {"relation": "hasMaterial", "aliases": ["Nexofiber"]},
        },
    )
    anchor = {
        "text": source,
        "spans": [{"evidence_id": "a", "text": source}],
        "category": "DOCUMENTARY",
        "epistemic_type": "documentary_content",
        "conditions": [],
        "typed_fields": [
            {
                "property_id": "BottleLabel",
                "aliases": ["bottle label"],
                "role": "reported_material_description",
                "value": {"reported_value": "100% CH4"},
            }
        ],
    }
    optimistic = SimpleNamespace(check=lambda p, h: {"supported": True})
    for invalid in ("The panel material is Nexofiber.", "The bottle label is 70% CH4."):
        assert not verify_paraphrase(invalid, [anchor], registry, optimistic)["supported"]
    for valid in ("The panel material is AFLEX.", "The bottle label is 100% CH4."):
        assert verify_paraphrase(valid, [anchor], registry, optimistic)["supported"]


def test_source_roles_and_report_identifiers_remain_distinct_from_observations():
    from nasa_fire_ai.services.semantic_support import verify_paraphrase

    statement = "The lumen filter reduces unwanted glare."
    registry = SimpleNamespace(
        resolve=lambda eid: {"text": statement, "structured_location": {"field": "Hypothesis"}}
    )
    anchor = {
        "text": statement,
        "spans": [{"evidence_id": "a", "text": statement}],
        "category": "DOCUMENTARY",
        "epistemic_type": "documentary_content",
        "conditions": [],
    }
    optimistic = SimpleNamespace(check=lambda p, h: {"supported": True})
    assert not verify_paraphrase(statement, [anchor], registry, optimistic)["supported"]
    assert verify_paraphrase(
        "The stated hypothesis is that the lumen filter reduces unwanted glare.",
        [anchor],
        registry,
        optimistic,
    )["supported"]
    source = "NASA/TM-20201234567\n" + statement
    registry = SimpleNamespace(resolve=lambda eid: {"text": source})
    assert verify_paraphrase(
        "NASA/TM-20201234567 reports that the lumen filter reduces unwanted glare.",
        [anchor],
        registry,
        optimistic,
    )["supported"]
    assert not verify_paraphrase(
        "The pressure was 20201234567 Pa.", [anchor], registry, optimistic
    )["supported"]


def test_bibliographic_reference_cannot_certify_an_experimental_finding():
    from nasa_fire_ai.services.semantic_support import verify_paraphrase

    reference = "[1] Vega et al., Optical variability, 2020."
    source = "A preliminary discussion.\nReferences\n" + reference
    registry = SimpleNamespace(resolve=lambda eid: {"text": source})
    anchor = {
        "text": reference,
        "spans": [{"evidence_id": "a", "text": reference}],
        "category": "DOCUMENTARY",
        "epistemic_type": "documentary_content",
        "conditions": [],
    }
    assert not verify_paraphrase(
        "The reference demonstrates optical variability.",
        [anchor],
        registry,
        SimpleNamespace(check=lambda p, h: {"supported": True}),
    )["supported"]


def test_observed_response_is_not_an_author_recommendation():
    from nasa_fire_ai.services.semantic_support import verify_paraphrase

    source = "The synthetic detector recorded a stronger signal."
    registry = SimpleNamespace(resolve=lambda eid: {"text": source})
    anchor = {
        "text": source,
        "spans": [{"evidence_id": "a", "text": source}],
        "category": "DOCUMENTARY",
        "epistemic_type": "documentary_content",
        "conditions": [],
    }
    assert not verify_paraphrase(
        "Operators should increase the signal.",
        [anchor],
        registry,
        SimpleNamespace(check=lambda p, h: {"supported": True}),
    )["supported"]


def test_typed_compound_can_subsume_its_atomic_field_but_not_another_record():
    store = SimpleNamespace(
        payload=lambda rid: {"subject": "trial-" + rid, "property_id": "Pressure"}
    )
    service = ConversationService(
        SimpleNamespace(store=store),
        entailment=SimpleNamespace(check=lambda p, h: {"supported": True}),
    )
    texts = [
        "Trial A initial pressure 4 Pa and final pressure 7 Pa.",
        "Trial A final pressure 7 Pa.",
        "Trial B final pressure 7 Pa.",
    ]
    trace = {
        "support_inventory": [
            {"support_id": "a", "structured_record_id": "a", "document_id": "report"},
            {"support_id": "b", "structured_record_id": "b", "document_id": "report"},
        ],
        "accepted_statements": [
            {"text": text, "support_ids": ["a" if i < 2 else "b"]} for i, text in enumerate(texts)
        ],
    }
    assert service._deduplicate_answer(texts, trace) == [texts[0], texts[2]]


def test_documentation_absence_cannot_expand_one_instrument_limitation():
    from nasa_fire_ai.services.semantic_support import verify_paraphrase

    source = "The sensor did not report radiance because its calibration failed."
    claim = "The documentation does not state what the camera and sensor measure."

    # Simulate the observed one-way false entailment. Reverse scope must survive too.
    class Directional:
        def check(self, premise, hypothesis):
            return {"supported": premise == source}

    registry = SimpleNamespace(resolve=lambda eid: {"text": source})
    anchor = {
        "text": source,
        "spans": [{"evidence_id": "s", "text": source}],
        "category": "DOCUMENTARY",
        "epistemic_type": "documentary_content",
        "conditions": [],
    }
    assert not verify_paraphrase(claim, [anchor], registry, Directional())["supported"]


def test_unit_equivalence_preserves_rejection_of_changed_values_and_dimensions():
    from nasa_fire_ai.services.semantic_support import numeric_tokens

    assert numeric_tokens("Pressure 1 atm") == numeric_tokens("Pressure 101325 Pa")
    assert numeric_tokens("Diameter 250 micrometers") == numeric_tokens("Diameter 0.25 mm")
    assert numeric_tokens("Pressure 1 Pa") != numeric_tokens("Pressure 1 atm")
    assert numeric_tokens("Duration 250 ms") != numeric_tokens("Diameter 250 micrometers")


def test_typed_source_formula_and_run_identifier_survive_permissive_nli():
    from nasa_fire_ai.services.semantic_support import verify_paraphrase

    source = "Fuel: C3H8 | Camera: Q6C8 | Run: f019a02"
    registry = SimpleNamespace(resolve=lambda eid: {"text": source})
    anchor = {
        "text": source,
        "category": "DOCUMENTARY",
        "epistemic_type": "documentary_content",
        "spans": [{"evidence_id": "s", "text": source}],
        "typed_fields": [{"role": "reported_material_description", "aliases": ["fuel"]}],
        "conditions": [],
    }
    optimistic = SimpleNamespace(check=lambda premise, hypothesis: {"supported": True})
    assert verify_paraphrase("The recorded fuel is C3H8.", [anchor], registry, optimistic)[
        "supported"
    ]
    for bad in ["The recorded fuel is C4H10.", "The camera is Q6C9.", "The run is f019a03."]:
        assert not verify_paraphrase(bad, [anchor], registry, optimistic)["supported"]


def test_joint_table_rows_do_not_transfer_conditions_and_parallel_facts_do_not_prove_cause():
    from nasa_fire_ai.services.semantic_support import verify_paraphrase

    texts = {"a": "Trial A7 used argon at 4 atm.", "b": "Trial B8 used neon at 7 atm."}
    registry = SimpleNamespace(resolve=lambda eid: {"text": texts[eid]})
    anchors = [
        {
            "text": v,
            "category": "DOCUMENTARY",
            "epistemic_type": "documentary_content",
            "spans": [{"evidence_id": k, "text": v}],
            "typed_fields": [{"role": "reported_condition", "aliases": ["pressure"]}],
            "conditions": [],
        }
        for k, v in texts.items()
    ]
    optimistic = SimpleNamespace(check=lambda p, h: {"supported": True})
    assert not verify_paraphrase("Trial A7 used argon at 7 atm.", anchors, registry, optimistic)[
        "supported"
    ]
    plain = {**anchors[0], "typed_fields": []}
    assert not verify_paraphrase(
        "Argon caused the vessel to stabilize.", [plain], registry, optimistic
    )["supported"]


def test_original_header_routing_keeps_complementary_fields_without_identifier_tokens():
    from nasa_fire_ai.query.v2 import PropertyDefinition
    from nasa_fire_ai.services.structured_alignment import route_need_properties

    definitions = {
        "Speed": PropertyDefinition("Speed", "speed", "m/s", aliases=["Inlet velocity (cm/s)"]),
        "Duration": PropertyDefinition("Duration", "time", "s", aliases=["Duration (sec)"]),
        "Age": PropertyDefinition("Age", "time", "s", aliases=["Net aging time (sec)"]),
        "Counter": PropertyDefinition("Counter", "none", None, aliases=["Aster Test #"]),
    }
    assert route_need_properties(
        "recorded inlet velocity and net aging time for Aster test 81b", definitions
    ) == {"Speed", "Age"}
    assert route_need_properties("duration of Aster test 81b", definitions) == {"Duration"}


def test_complete_calendar_dates_never_decode_experiment_counters():
    from datetime import date

    from nasa_fire_ai.query.record_identity import calendar_mentions

    for phrase in ["20 February 2037", "February 20, 2037", "2037-02-20", "2037-FEB-20"]:
        assert calendar_mentions(phrase)[0][0] == date(2037, 2, 20)
    assert not calendar_mentions("test day 37051")
    assert not calendar_mentions("30 February 2037")
    assert calendar_mentions("30 February 2037", retain_invalid=True)[0][0] is None


def test_source_column_aliases_do_not_type_ordinary_documentary_words():
    from nasa_fire_ai.query.v2 import PropertyDefinition
    from nasa_fire_ai.services.semantic_support import verify_paraphrase

    source = "The report explicitly separates the methods from the results."
    registry = SimpleNamespace(
        resolve=lambda eid: {"text": source},
        scientific_properties={
            "source:notes": PropertyDefinition(
                "source:notes",
                "none",
                None,
                datatype="categorical",
                aliases=["notes", "explicitly"],
            )
        },
    )
    anchor = {
        "text": source,
        "spans": [{"evidence_id": "a", "text": source}],
        "category": "DOCUMENTARY",
        "epistemic_type": "documentary_content",
        "conditions": [],
    }
    model = SimpleNamespace(check=lambda premise, hypothesis: {"supported": hypothesis in premise})
    assert verify_paraphrase(source, [anchor], registry, model)["supported"]
    # This exemption is about prose interpretation, never numeric permission.
    assert not verify_paraphrase(source + " The pressure was 9 Pa.", [anchor], registry, model)[
        "supported"
    ]


def test_context_window_recovers_a_documentary_relation_without_borrowing_another_source():
    source = "The ORION instrument measures brightness. It uses a violet filter."
    registry = SimpleNamespace(resolve=lambda eid: {"text": source})
    service = ConversationService(
        SimpleNamespace(registry=registry),
        entailment=SimpleNamespace(
            check=lambda p, h: {
                "supported": "ORION" in p and "violet" in p and h == "ORION uses a violet filter."
            }
        ),
    )
    anchor = {
        "support_id": "a",
        "text": "It uses a violet filter.",
        "context_window": source,
        "spans": [{"evidence_id": "a", "text": "It uses a violet filter."}],
        "category": "DOCUMENTARY",
        "epistemic_type": "documentary_content",
        "conditions": [],
    }
    anchors, verdict = service._align_claim("ORION uses a violet filter.", [], {"a": anchor})
    assert verdict["supported"]
    assert anchors[0]["spans"][0]["text"] == source
    assert anchors[0]["spans"][0]["evidence_id"] == "a"


def test_overlapping_context_cannot_amplify_a_contradicted_claim():
    from nasa_fire_ai.services.semantic_support import verify_paraphrase

    original = "The vessel is opaque. Its window is amber."
    registry = SimpleNamespace(resolve=lambda eid: {"text": original})
    anchors = [
        {
            "support_id": str(i),
            "text": text,
            "spans": [{"evidence_id": "p", "text": text}],
            "category": "DOCUMENTARY",
            "epistemic_type": "documentary_content",
            "conditions": [],
        }
        for i, text in enumerate(["The vessel is opaque.", original])
    ]

    def check(premise, hypothesis):
        repeated = premise.count("The vessel is opaque.") > 1
        return {
            "supported": repeated,
            "probabilities": {
                "entailment": 0.99 if repeated else 0.01,
                "contradiction": 0.01 if repeated else 0.99,
            },
        }

    result = verify_paraphrase(
        "The vessel is transparent.", anchors, registry, SimpleNamespace(check=check)
    )
    assert not result["supported"]


def test_joint_entailment_cannot_override_a_same_location_contradiction():
    from nasa_fire_ai.services.semantic_support import verify_paraphrase

    original = "The vessel is opaque. Its window is amber."
    registry = SimpleNamespace(resolve=lambda eid: {"text": original})
    anchors = [
        {
            "support_id": str(i),
            "text": text,
            "spans": [{"evidence_id": "p", "text": text}],
            "category": "DOCUMENTARY",
            "epistemic_type": "documentary_content",
            "conditions": [],
        }
        for i, text in enumerate(["The vessel is opaque.", "Its window is amber."])
    ]

    def check(premise, hypothesis):
        joint = "opaque" in premise and "amber" in premise
        contradicted = "opaque" in premise and not joint
        return {
            "supported": joint,
            "probabilities": {
                "entailment": 0.99 if joint else 0.01,
                "contradiction": 0.99 if contradicted else 0.01,
            },
        }

    result = verify_paraphrase(
        "The vessel is transparent.", anchors, registry, SimpleNamespace(check=check)
    )
    assert not result["supported"]
    assert "source-local contradiction" in result["errors"][0]


def test_source_bound_attribution_preserves_exact_scientific_proposition():
    from nasa_fire_ai.services.semantic_support import verify_paraphrase

    source = "The sensor reported an offset of 3 Pa."
    registry = SimpleNamespace(resolve=lambda eid: {"text": source})
    anchor = {
        "text": source,
        "spans": [{"evidence_id": "a", "text": source}],
        "category": "DOCUMENTARY",
        "epistemic_type": "documentary_content",
        "conditions": [],
        "scientific_subjects": ["study-a"],
        "source_aliases": ["STUDY-A"],
    }
    uncertain_model = SimpleNamespace(check=lambda p, h: {"supported": False})
    result = verify_paraphrase("For STUDY-A, " + source, [anchor], registry, uncertain_model)
    assert result["supported"]
    assert result["verification_mechanism"] == "source_scoped_registered_quotation"
    for claim in ["For STUDY-B, " + source, "For STUDY-A, The sensor reported an offset of 4 Pa."]:
        assert not verify_paraphrase(claim, [anchor], registry, uncertain_model)["supported"]


def test_source_conditional_hypothesis_is_preserved_without_certifying_observation():
    from nasa_fire_ai.services.semantic_support import verify_paraphrase

    source = "The spectral contrast would increase under the proposed conditions."
    registry = SimpleNamespace(
        resolve=lambda eid: {"text": source, "structured_location": {"field": "Hypothesis"}}
    )
    anchor = {
        "text": source,
        "spans": [{"evidence_id": "a", "text": source}],
        "category": "DOCUMENTARY",
        "epistemic_type": "documentary_content",
        "conditions": [],
        "scientific_subjects": ["study-a"],
        "source_aliases": ["STUDY-A"],
    }
    model = SimpleNamespace(check=lambda p, h: {"supported": False})
    assert verify_paraphrase("For STUDY-A, " + source, [anchor], registry, model)["supported"]
    assert not verify_paraphrase(
        "For STUDY-A, The spectral contrast increased.", [anchor], registry, model
    )["supported"]


def test_reexamined_original_sentence_remains_available_for_targeted_repair():
    original = "The prism selects a violet band. The detector stores the spectral trace."
    source = {"evidence_id": "p", "text": original, "section": "document"}
    registry = SimpleNamespace(
        resolve=lambda eid: {"text": original},
        source_metadata=lambda eid: {"source_id": "report-a"},
        db=SimpleNamespace(execute=lambda query, args: [source]),
    )
    anchor = {
        "support_id": "initial",
        "text": "The detector stores the spectral trace.",
        "spans": [{"evidence_id": "p", "text": "The detector stores the spectral trace."}],
        "category": "DOCUMENTARY",
        "epistemic_type": "documentary_content",
        "document_id": "report-a",
        "conditions": [],
    }
    service = ConversationService(
        SimpleNamespace(registry=registry),
        entailment=SimpleNamespace(check=lambda p, h: {"supported": False}),
    )
    inventory = {"initial": anchor}
    assert (
        service._realign_documentary("The prism produces an unseen red band.", [anchor], inventory)
        is None
    )
    assert any(item["text"] == "The prism selects a violet band." for item in inventory.values())
    assert all(item["category"] == "DOCUMENTARY" for item in inventory.values())


def test_geometry_routing_uses_curated_specimen_facets_without_measured_extinction():
    from nasa_fire_ai.query.v2 import PropertyDefinition
    from nasa_fire_ai.services.structured_alignment import route_need_properties

    definitions = {
        name: PropertyDefinition(name, "length", "m", aliases=[name])
        for name in ["panel_width", "panel_thickness", "extinction_distance"]
    }
    roles = {
        "panel_width": {"SPECIMEN_CHARACTERISTIC"},
        "panel_thickness": {"SPECIMEN_CHARACTERISTIC"},
        "extinction_distance": {"REPORTED_EXTINCTION_CONTEXT"},
    }
    matched = route_need_properties("original specimen dimensions", definitions, field_roles=roles)
    assert matched == {"panel_width", "panel_thickness"}
    assert route_need_properties("sensor dimensions", definitions, field_roles=roles) == set()


def test_column_header_units_support_composite_original_values_without_unit_or_value_transfer():
    from nasa_fire_ai.normalization.units import normalize
    from nasa_fire_ai.query.v2 import PropertyDefinition
    from nasa_fire_ai.services.semantic_support import verify_paraphrase

    source = "Flow (cm/s): 5 | Loss (mg/min): 2 | Duration (minutes): 3"
    definitions = {
        "Flow": PropertyDefinition("Flow", "velocity", "m/s", aliases=["flow"]),
        "Loss": PropertyDefinition("Loss", "mass_flow", "kg/s", aliases=["loss"]),
        "Duration": PropertyDefinition("Duration", "time", "s", aliases=["duration"]),
    }
    registry = SimpleNamespace(
        resolve=lambda eid: {"text": source}, scientific_properties=definitions
    )
    fields = [
        {
            "id": key,
            "property_id": key,
            "aliases": [key.lower()],
            "role": "reported_condition",
            "value": {
                "reported_value": value,
                "reported_unit": unit,
                "raw_expression": str(value),
                "canonical_value": normalize(value, unit)[0],
                "canonical_unit": normalize(value, unit)[1],
            },
        }
        for key, value, unit in [("Flow", 5, "cm/s"), ("Loss", 2, "mg/min"), ("Duration", 3, "min")]
    ]
    candidate = {
        "text": source,
        "spans": [{"evidence_id": "row", "text": source}],
        "category": "DOCUMENTARY",
        "epistemic_type": "documentary_content",
        "conditions": [],
        "typed_fields": fields,
    }
    optimistic = SimpleNamespace(check=lambda p, h: {"supported": True})
    correct = "Flow is 5 cm/s, loss is 2 mg/min, and duration is 3 minutes."
    assert verify_paraphrase(correct, [candidate], registry, optimistic)["supported"]
    for changed in [
        correct.replace("2 mg/min", "5 mg/min"),
        correct.replace("2 mg/min", "2 mg/s"),
        correct.replace("3 minutes", "2 minutes"),
    ]:
        assert not verify_paraphrase(changed, [candidate], registry, optimistic)["supported"]
    assert not verify_paraphrase(correct, [candidate], registry, None)["supported"]


def test_dimensional_routing_does_not_match_shared_exponent_fragments():
    from nasa_fire_ai.services.semantic_support import numeric_tokens

    assert numeric_tokens('±73 µm') == numeric_tokens('±0.073 mm')
    assert not numeric_tokens('±73 µm') & numeric_tokens('±74 µm')
