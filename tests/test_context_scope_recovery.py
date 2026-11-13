"""Printed section ancestry and case locators constrain source interpretation."""

from types import SimpleNamespace

import pytest

from nasa_fire_ai.services.document_sections import add_section_context, record_caption_errors
from nasa_fire_ai.services.semantic_support import canonical_numeric_text, verify_paraphrase
from nasa_fire_ai.services.structured_alignment import missing_record_fields, record_anchor_allowed


def registered_pages():
    rows = [
        {
            "evidence_id": "r1",
            "page": 1,
            "text": "4.0\nOptical Analysis\n4.2\nViolet Camera Analysis\n4.2.1\nError Estimate\n",
        },
        {
            "evidence_id": "r2",
            "page": 2,
            "text": "The size error is ±73 µm.\n4.3\nAmber Camera\nAnalysis\n4.3.1\nError Estimate\nThe size error is ±91 µm.",
        },
        {
            "evidence_id": "r3",
            "page": 3,
            "text": "Figure 19.—Test VEGA−072.\nThe frame was cropped.",
        },
    ]
    return SimpleNamespace(
        db=SimpleNamespace(execute=lambda q, a: rows),
        resolve=lambda eid: next(row for row in rows if row["evidence_id"] == eid),
        source_metadata=lambda eid: {},
    )


def source_anchor(eid, text):
    return {
        "support_id": eid,
        "document_id": "fictional-optics",
        "text": text,
        "spans": [{"evidence_id": eid, "text": text}],
        "category": "DOCUMENTARY",
        "epistemic_type": "documentary_content",
    }


def test_parent_section_survives_page_boundary_without_borrowing_next_camera():
    registry = registered_pages()
    for text, expected, excluded in [
        ("The size error is ±73 µm.", "Violet", "Amber"),
        ("The size error is ±91 µm.", "Amber", "Violet"),
    ]:
        anchor = source_anchor("r2", text)
        add_section_context(anchor, registry, {})
        titles = " ".join(anchor["scientific_sections"])
        assert expected in titles and excluded not in titles
        for span in anchor["spans"]:
            assert span["text"] in registry.resolve(span["evidence_id"])["text"]


@pytest.mark.parametrize("dash", ["-", "‐", "‑", "–", "—", "−"])
def test_printed_dash_preserves_longer_investigation_identity(dash):
    from nasa_fire_ai.services.ontology_support import (
        investigation_mentions,
        leading_investigation,
    )

    store = SimpleNamespace(
        registry=SimpleNamespace(
            identifier_headers=[],
            entity_mentions={
                "base": {"relation": "belongsToInvestigation", "aliases": ["ORBIT"]},
                "second": {"relation": "belongsToInvestigation", "aliases": ["ORBIT-II"]},
                "third": {"relation": "belongsToInvestigation", "aliases": ["ORBIT-III"]},
            },
        )
    )
    assert investigation_mentions(f"The ORBIT{dash}II investigation", store) == {"second"}
    assert leading_investigation(f"ORBIT{dash}II investigated combustion.", store)["id"] == "second"
    assert investigation_mentions(f"ORBIT{dash}III", store) == {"third"}
    assert investigation_mentions("ORBIT investigated combustion.", store) == {"base"}


def test_figure_record_scope_cannot_be_removed_by_permissive_entailment():
    registry = registered_pages()
    anchor = source_anchor("r3", "The frame was cropped.")
    add_section_context(anchor, registry, {})
    assert anchor["source_record_references"] == ["VEGA−072"]
    assert record_caption_errors("The frames were cropped.", [anchor])
    assert not record_caption_errors("VEGA test 72 had a cropped frame.", [anchor])
    result = verify_paraphrase(
        "The frames were cropped.",
        [anchor],
        registry,
        SimpleNamespace(check=lambda p, h: {"supported": True}),
    )
    assert not result["supported"]


@pytest.mark.parametrize(
    "written,decimal", [("three-fourths", "0.75"), ("two fifths", "0.4"), ("one and a half", "1.5")]
)
def test_written_fraction_has_a_quantity_identity(written, decimal):
    assert canonical_numeric_text(written) == canonical_numeric_text(decimal)
    assert canonical_numeric_text(written) != canonical_numeric_text("0.83")
    assert canonical_numeric_text("third test") == "third test"


def test_record_repair_does_not_quote_an_unlabelled_numeric_table():
    anchor = source_anchor("r1", "\n".join(str(i) for i in range(15)))
    assert not record_anchor_allowed(anchor, SimpleNamespace(store=object()), {"rec"})
    assert record_anchor_allowed(anchor, SimpleNamespace(store=object()), set())


@pytest.mark.parametrize("field,expected", [("temperature", True), ("literal-pressure", False)])
def test_missing_lookup_checks_all_fields_and_preserves_unparsed_variables(field, expected):
    definitions = {
        "pressure": SimpleNamespace(aliases=["pressure"], datatype="numeric"),
        "temperature": SimpleNamespace(aliases=["temperature"], datatype="numeric"),
    }
    field_payload = {"subject": "rec", "property_id": field, "qualifiers": {}}
    if field == "literal-pressure":
        field_payload["qualifiers"]["intended_property"] = "pressure"
    store = SimpleNamespace(
        registry=SimpleNamespace(properties=definitions),
        evidence=lambda rid: ["original-row"],
        relations=lambda rid, rel: ["field"] if rel == "hasRecordedField" else [],
        payload=lambda rid: field_payload if rid == "field" else {"reported_identifier": "R-9"},
    )
    boundaries = missing_record_fields(
        "Give the pressure of this entry.", SimpleNamespace(store=store), {"rec"}
    )
    assert bool(boundaries) is expected
    if boundaries:
        assert boundaries[0]["source_record_ids"] == ["rec"]
        assert boundaries[0]["property_ids"] == ["pressure"]
        assert "NASA lacks" not in boundaries[0]["text"]


def test_section_quote_reconstructs_context_and_refuses_changed_source_words():
    from nasa_fire_ai.services.document_sections import section_quotation

    registry = registered_pages()
    anchor = source_anchor("r2", "The size error is ±73 µm.")
    result = section_quotation(anchor, registry)
    assert "Violet Camera Analysis" in result["text"]
    assert "Amber" not in result["text"]
    assert result["quoted_text"] == anchor["text"]
    anchor["spans"][0]["text"] = "The size error is ±74 µm."
    assert section_quotation(anchor, registry) is None
    figure = source_anchor("r3", "The frame was cropped.")
    assert section_quotation(figure, registry) is None


def test_source_quote_cannot_frame_two_camera_sections_as_one():
    from nasa_fire_ai.services.document_sections import section_quotation

    registry = registered_pages()
    anchor = source_anchor("r2", registry.resolve("r2")["text"])
    assert section_quotation(anchor, registry) is None


def test_identity_cache_reuses_only_the_same_snapshot_and_primary_span():
    from nasa_fire_ai.services.conversation import ConversationService

    calls = []
    registry = SimpleNamespace(
        resolve=lambda eid: {"text": "A fictional reading was recorded."},
        source_metadata=lambda eid: {"title": "Synthetic report"},
    )
    search = SimpleNamespace(
        manifest={"snapshot_id": "first"},
        registry=registry,
        store=SimpleNamespace(registry=SimpleNamespace(entity_mentions={})),
        passage_scientific_subjects=lambda anchor: calls.append(anchor["text"]) or [],
    )
    service = ConversationService(search)
    anchor = source_anchor("r", "A fictional reading was recorded.")
    service._attach_scientific_identity(anchor)
    service._attach_scientific_identity(dict(anchor))
    assert len(calls) == 1
    changed = {
        **anchor,
        "text": "A different fictional reading was recorded.",
        "spans": [{"evidence_id": "r", "text": "A different fictional reading was recorded."}],
    }
    service._attach_scientific_identity(changed)
    assert len(calls) == 2
    search.manifest["snapshot_id"] = "second"
    service._attach_scientific_identity(anchor)
    assert len(calls) == 3


def test_numeric_need_survives_lexically_similar_candidate_crowding():
    from nasa_fire_ai.services.conversation import ConversationService

    target = source_anchor("target", "Marker scores were 19, 27, 39 and 92.")
    distractors = [
        source_anchor(str(i), "Marker score values appear in an unrelated procedure.")
        for i in range(45)
    ]
    anchors = [*distractors, target]
    by_id = {a["support_id"]: a for a in anchors}
    registry = SimpleNamespace(
        db=SimpleNamespace(execute=lambda *args: []),
        resolve=lambda eid: {"text": by_id[eid]["text"]},
    )
    service = ConversationService(
        SimpleNamespace(registry=registry),
        entailment=SimpleNamespace(check=lambda *args: {"supported": False}),
    )
    proposals = service._documentary_need_completion(
        [{"need": "Marker score values for 19, 27, 39 and 92"}],
        {a["support_id"]: a for a in anchors},
        [],
    )
    assert len(proposals) == 1
    assert proposals[0]["text"] == target["text"]
    assert proposals[0]["support_ids"] == ["target"]


def test_universal_instrument_need_requires_each_scoped_observable():
    from nasa_fire_ai.services.conversation import ConversationService

    contexts = [
        {"graph_context_id": "amber", "text": "An amber unit records a violet signal."},
        {"graph_context_id": "silver", "text": "A silver unit records a green signal."},
    ]
    store = SimpleNamespace(
        classes=lambda rid: {"Instrument"},
        payload=lambda rid: {"title": rid.title() + " unit"},
        relations=lambda *args: {"amber", "silver"},
    )
    service = ConversationService(
        SimpleNamespace(store=store),
        entailment=SimpleNamespace(check=lambda *args: {"supported": True}),
    )
    service._requested_investigations = {"fictional-study"}
    service._graph_context_candidates = lambda *args: contexts
    service._active_support_inventory = {
        "a": {"graph_context_id": "amber"},
        "b": {"graph_context_id": "silver"},
    }
    need = {"need": "Observable output for all instruments"}
    rows = [{"text": contexts[0]["text"], "support_ids": ["a"]}]
    assert not service._need_is_communicated(need, rows)
    rows.append({"text": contexts[1]["text"], "support_ids": ["b"]})
    assert service._need_is_communicated(need, rows)


def test_pinned_investigation_catalogue_updates_on_new_snapshot_or_alias_entry():
    from nasa_fire_ai.services.ontology_support import investigation_labels

    store = SimpleNamespace(
        _approved_snapshot_id="one",
        registry=SimpleNamespace(
            entity_mentions={
                "orbit": {"relation": "belongsToInvestigation", "aliases": ["ORBIT-II"]},
            }
        ),
    )
    first = investigation_labels(store)
    assert investigation_labels(store) is first
    store.registry.entity_mentions["nebula"] = {
        "relation": "belongsToInvestigation",
        "aliases": ["NEBULA"],
    }
    assert ("nebula", "NEBULA") in investigation_labels(store)
    previous = investigation_labels(store)
    store.registry.entity_mentions["orbit"]["aliases"] = ["ORBIT-III"]
    store._approved_snapshot_id = "two"
    updated = investigation_labels(store)
    assert updated is not previous
    assert ("orbit", "ORBIT-III") in updated and ("orbit", "ORBIT-II") not in updated


def test_cached_entity_names_do_not_cache_scientific_class_assertions():
    from nasa_fire_ai.services.ontology_support import _mentions

    classes = {"Investigation"}
    store = SimpleNamespace(
        _approved_snapshot_id="fixed",
        registry=SimpleNamespace(
            entities={"orbit"},
            identifier_headers=[],
            entity_mentions={"orbit": {"aliases": ["ORBIT-II"]}},
        ),
        classes=lambda *args, **kwargs: classes,
    )
    assert _mentions("ORBIT-II", store) == {"orbit": ["Investigation"]}
    classes.clear()
    classes.add("Apparatus")
    assert _mentions("ORBIT-II", store) == {"orbit": ["Apparatus"]}


def test_section_identity_stays_in_its_explicit_parent_branch():
    from nasa_fire_ai.services.document_sections import add_section_subject_context

    rows = [
        {
            "evidence_id": "alpha",
            "document_id": "report",
            "page": 1,
            "text": "1.0\nFirst Study\nThe ORBIT–II study concerns synthetic optics.\n1.1\nResults\nThe recorded width is 73 µm.",
        },
        {
            "evidence_id": "beta",
            "document_id": "report",
            "page": 2,
            "text": "2.0\nSecond Study\nThe NEBULA study concerns synthetic optics.\n2.1\nResults\nThe recorded width is 91 µm.",
        },
    ]
    registry = SimpleNamespace(
        db=SimpleNamespace(execute=lambda *args: rows),
        resolve=lambda eid: next(r for r in rows if r["evidence_id"] == eid),
    )
    store = SimpleNamespace(
        registry=SimpleNamespace(
            identifier_headers=[],
            entity_mentions={
                "orbit": {"relation": "belongsToInvestigation", "aliases": ["ORBIT-II"]},
                "nebula": {"relation": "belongsToInvestigation", "aliases": ["NEBULA"]},
            },
        )
    )
    for row, expected, excluded in [(rows[0], "ORBIT", "NEBULA"), (rows[1], "NEBULA", "ORBIT")]:
        anchor = source_anchor(row["evidence_id"], row["text"].splitlines()[-1])
        anchor["document_id"] = "report"
        add_section_subject_context(anchor, registry, {}, store)
        identity = [s for s in anchor["spans"] if s.get("scope") == "source_subject_context"]
        assert len(identity) == 1
        assert expected in identity[0]["text"] and excluded not in identity[0]["text"]


def test_graph_completion_stops_when_all_needs_are_communicated():
    from nasa_fire_ai.services.conversation import ConversationService

    service = ConversationService(SimpleNamespace(), entailment=SimpleNamespace())
    service._need_is_communicated = lambda need, statements: True
    service._graph_context_candidates = lambda *args: (_ for _ in ()).throw(
        AssertionError("Unneeded graph padding")
    )
    assert (
        service._graph_source_completion(
            "Explain the observations.", {}, [], needs=[{"need": "A supported fact"}]
        )
        == []
    )


def test_record_locator_is_not_a_requested_day_measurement():
    from nasa_fire_ai.services.structured_alignment import record_need_text, route_need_properties

    store = SimpleNamespace(payload=lambda subject: {"reported_identifier": "R-9"})
    phrase = record_need_text("fuel concentration for VEGA entry R-9", store, {"record"})
    assert phrase == "fuel concentration"
    definitions = {
        "fuel": SimpleNamespace(aliases=["fuel"]),
        "mix": SimpleNamespace(aliases=["fuel concentration"]),
        "day": SimpleNamespace(aliases=["day"]),
    }
    assert route_need_properties(phrase, definitions) == {"mix"}


def test_redundancy_preserves_distinct_fields_using_one_shared_source_anchor():
    from nasa_fire_ai.services.conversation import ConversationService

    definitions = {
        "bottle": SimpleNamespace(aliases=["bottle entry"]),
        "concentration": SimpleNamespace(aliases=["concentration entry"]),
    }
    store = SimpleNamespace(
        registry=SimpleNamespace(properties=definitions),
        payload=lambda rid: {"subject": "rec", "property_id": "bottle"},
    )
    service = ConversationService(
        SimpleNamespace(store=store),
        entailment=SimpleNamespace(check=lambda p, h: {"supported": True}),
    )
    first = "The bottle entry is 31%."
    second = "The concentration entry is 31%."
    trace = {
        "support_inventory": [
            {"support_id": "shared", "document_id": "doc", "structured_record_id": "field"}
        ],
        "accepted_statements": [
            {"text": text, "support_ids": ["shared"]} for text in [first, second]
        ],
    }
    assert service._deduplicate_answer([first, second], trace) == [first, second]


def test_quantified_error_recovery_keeps_the_named_optical_section():
    from nasa_fire_ai.services.conversation import ConversationService

    registry = registered_pages()
    search = SimpleNamespace(registry=registry)
    service = ConversationService(search)
    service._need_is_communicated = lambda need, statements: False
    inventory = {
        "violet": source_anchor("r2", "The size error is ±73 µm."),
        "amber": source_anchor("r2", "The size error is ±91 µm."),
    }
    proposals = service._documentary_need_completion(
        [{"need": "uncertainty of Violet camera size analysis"}], inventory, []
    )
    assert len(proposals) == 1
    assert "±73" in proposals[0]["text"]
    assert "±91" not in proposals[0]["text"]
    assert "Violet Camera Analysis" in proposals[0]["text"]


def test_count_request_does_not_request_an_unspecified_identifier():
    from nasa_fire_ai.services.structured_alignment import route_need_properties

    definitions = {
        "identity": SimpleNamespace(aliases=["number", "test number"]),
        "observations": SimpleNamespace(aliases=["sparks detected"]),
    }
    assert route_need_properties("number of sparks detected", definitions) == {"observations"}
    assert route_need_properties("test number", definitions) == {"identity"}


def test_unsectioned_comparison_is_eligible_without_inventing_a_heading():
    from nasa_fire_ai.services.conversation import ConversationService

    text = "The violet reading is lower than the amber reading."
    row = {"evidence_id": "summary", "page": 1, "text": text}
    registry = SimpleNamespace(
        db=SimpleNamespace(execute=lambda q, a: [row]), resolve=lambda eid: row
    )
    anchor = source_anchor("summary", text)
    service = ConversationService(SimpleNamespace(registry=registry))
    service._need_is_communicated = lambda need, statements: False
    result = service._documentary_need_completion(
        [{"need": "comparison of violet and amber readings"}], {"summary": anchor}, []
    )
    assert result[0]["text"] == text
    assert "scientific_sections" not in anchor


def test_successful_wording_does_not_trigger_failed_source_repair():
    from nasa_fire_ai.services.conversation import ConversationService

    service = ConversationService(SimpleNamespace())
    service._documentary_need_completion = lambda *args: (_ for _ in ()).throw(
        AssertionError("Unneeded repair")
    )
    assert service._source_restatements([], {}, [], needs=[{"need": "A topic"}]) == []


@pytest.mark.parametrize("explicit_complementary_source", [False, True])
def test_generic_need_preserves_question_scope_and_explicit_complementary_sources(
    explicit_complementary_source,
):
    from nasa_fire_ai.services.conversation import ConversationService

    right = source_anchor("right", "The violet sensor measures a signal.")
    other = source_anchor("other", "The sensor measures a signal.")
    right.update(scientific_subjects=["study"], source_id="study-report")
    other.update(scientific_subjects=[], source_id="separate-standard")
    inventory = {a["support_id"]: a for a in [right, other]}
    registry = SimpleNamespace(
        db=SimpleNamespace(execute=lambda *args: []),
        resolve=lambda eid: {"text": inventory[eid]["text"]},
    )
    store = SimpleNamespace(registry=SimpleNamespace(entity_mentions={}))
    service = ConversationService(SimpleNamespace(registry=registry, store=store))
    service._requested_investigations = {"study"}
    service._requested_document_sources = (
        {"separate-standard"} if explicit_complementary_source else set()
    )
    service._attach_scientific_identity = lambda a: a
    service._need_is_communicated = lambda *args: False
    proposals = service._documentary_need_completion(
        [{"need": "Explain the signal the sensor measures"}], inventory, []
    )
    assert proposals[0]["support_ids"] == ["other" if explicit_complementary_source else "right"]


def test_dual_assertion_checks_cardinality_separately_from_the_relation():
    original = "The sensor records violet light."
    registry = SimpleNamespace(resolve=lambda eid: {"text": original})
    candidate = source_anchor("one", original)
    verdict = verify_paraphrase(
        "Both sensors are recording violet light.",
        [candidate],
        registry,
        SimpleNamespace(check=lambda p, h: {"supported": not h.startswith("There are two")}),
    )
    assert not verdict["supported"]
    assert "pair" in verdict["errors"][0]
    original = "Both sensors are recording violet light."
    registry = SimpleNamespace(resolve=lambda eid: {"text": original})
    assert verify_paraphrase(original, [source_anchor("two", original)], registry, None)[
        "supported"
    ]


def test_ordinal_record_reference_does_not_become_a_fraction():
    assert canonical_numeric_text("a third trial") == "a third trial"
    assert canonical_numeric_text("a third of the mixture") == "0.3333333333 of the mixture"


def test_record_locator_does_not_consume_the_requested_count_phrase():
    from nasa_fire_ai.services.structured_alignment import record_need_text

    store = SimpleNamespace(payload=lambda subject: {"reported_identifier": "R-9"})
    assert (
        record_need_text("number of sparks detected for VEGA entry R-9", store, {"record"})
        == "number of sparks detected"
    )


def test_quoted_section_attribution_cannot_be_forged_by_a_positive_nli():
    from nasa_fire_ai.services.conversation import ConversationService
    from nasa_fire_ai.services.document_sections import section_quotation

    registry = registered_pages()
    candidate = source_anchor("r2", "The size error is ±73 µm.")
    framed = section_quotation(candidate, registry)
    service = ConversationService(
        SimpleNamespace(registry=registry),
        entailment=SimpleNamespace(check=lambda p, h: {"supported": True}),
    )
    assert service._source_semantic_verdict(framed["text"], [candidate])["supported"]
    false_attribution = framed["text"].replace("Violet Camera Analysis", "Amber Camera Analysis")
    verdict = service._source_semantic_verdict(false_attribution, [candidate])
    assert not verdict["supported"]
    assert "attribution" in verdict["errors"][0]


def test_scoped_quotation_without_id_hints_is_located_by_its_body():
    from nasa_fire_ai.services.conversation import ConversationService, rank_alignment_candidates
    from nasa_fire_ai.services.document_sections import section_quotation

    registry = registered_pages()
    candidate = source_anchor("r2", "The size error is ±73 µm.")
    unrelated = source_anchor(
        "r1", "4.0\nOptical Analysis\n4.2\nViolet Camera Analysis\n4.2.1\nError Estimate\n"
    )
    framed = section_quotation(candidate, registry)
    ranked = rank_alignment_candidates(framed["text"], [unrelated, candidate])
    assert ranked[0] is candidate
    service = ConversationService(SimpleNamespace(registry=registry))
    anchors, verdict = service._align_claim(framed["text"], [], {"r2": candidate, "r1": unrelated})
    assert verdict["supported"]
    assert anchors == [candidate]
