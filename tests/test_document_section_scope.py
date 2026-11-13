"""Procedure scope and provenance identifiers cannot become experimental values."""

from types import SimpleNamespace

import pytest

from nasa_fire_ai.services.document_sections import (
    add_section_context,
    registered_document_references,
)
from nasa_fire_ai.services.semantic_support import verify_paraphrase


def source_registry():
    rows = [
        {
            "evidence_id": "a",
            "page": 12,
            "text": "8.2 Violet Response (Test 6)\n8.2.1 Purpose\nThe sensor records violet light.",
        },
        {
            "evidence_id": "b",
            "page": 13,
            "text": "8.2.2 Criteria\nThe specimen shall emit no debris.",
        },
        {
            "evidence_id": "c",
            "page": 14,
            "text": "8.3 Amber Response (Test 9)\n8.3.1 Purpose\nThe sensor records amber light.",
        },
    ]
    return SimpleNamespace(
        db=SimpleNamespace(execute=lambda query, args: rows),
        resolve=lambda eid: next(row for row in rows if row["evidence_id"] == eid),
        source_metadata=lambda eid: {"title": "NASA-STD-9876Z with Change 8"},
    )


def anchor(eid, text):
    return {
        "document_id": "fictional-standard",
        "text": text,
        "category": "DOCUMENTARY",
        "epistemic_type": "documentary_content",
        "conditions": [],
        "spans": [{"evidence_id": eid, "text": text}],
    }


def test_child_criterion_keeps_its_original_parent_procedure_across_pages():
    registry = source_registry()
    candidate = anchor("b", "The specimen shall emit no debris.")
    add_section_context(candidate, registry, {})
    assert candidate["method_references"] == ["6"]
    assert candidate["spans"][1]["evidence_id"] == "a"
    assert candidate["spans"][1]["text"] == "8.2 Violet Response (Test 6)"


@pytest.mark.parametrize("clause,expected", [("8.2.3a", "6"), ("8.3.1b", "9")])
def test_checklist_clause_reference_uses_its_own_original_method(clause, expected):
    registry = source_registry()
    rows = list(registry.db.execute("", ()))
    text = clause + "\nTest Criteria\nThe specimen shall emit no debris."
    rows.append({"evidence_id": "checklist", "page": 30, "text": text})
    registry.db.execute = lambda *args: rows
    registry.resolve = lambda eid: next(row for row in rows if row["evidence_id"] == eid)
    candidate = anchor("checklist", text)
    add_section_context(candidate, registry, {})
    assert candidate["method_references"] == [expected]
    heading = next(span for span in candidate["spans"] if span.get("scope") == "section_heading")
    assert heading["evidence_id"] == ("a" if expected == "6" else "c")
    assert heading["text"] in registry.resolve(heading["evidence_id"])["text"]


def test_other_procedure_cannot_supply_the_requested_test_identity():
    registry = source_registry()
    candidate = anchor("c", "The sensor records amber light.")
    add_section_context(candidate, registry, {})
    result = verify_paraphrase(
        "Test 6 records amber light.",
        [candidate],
        registry,
        SimpleNamespace(check=lambda p, h: {"supported": True}),
    )
    assert not result["supported"]
    assert any("section scope" in error for error in result["errors"])


def test_conversation_method_scope_also_applies_when_a_clause_omits_the_test_number():
    from nasa_fire_ai.services.conversation import ConversationService

    registry = source_registry()
    service = ConversationService(
        SimpleNamespace(registry=registry),
        entailment=SimpleNamespace(check=lambda p, h: {"supported": True}),
    )
    service._requested_method_documents = {"fictional-standard": {"6"}}
    wrong = anchor("c", "The sensor records amber light.")
    add_section_context(wrong, registry, {})
    assert not service._source_semantic_verdict(wrong["text"], [wrong])["supported"]
    right = anchor("b", "The specimen shall emit no debris.")
    add_section_context(right, registry, {})
    assert service._source_semantic_verdict(right["text"], [right])["supported"]
    service._requested_method_documents = {"fictional-standard": {"6", "9"}}
    assert service._source_semantic_verdict(wrong["text"], [wrong])["supported"]


def test_method_completion_cannot_repair_a_need_from_another_procedure():
    from nasa_fire_ai.services.conversation import ConversationService

    registry = source_registry()
    service = ConversationService(SimpleNamespace(registry=registry))
    service._requested_method_documents = {"fictional-standard": {"6"}}
    service._need_is_communicated = lambda need, accepted: False
    inventory = {}
    for eid, text in [
        ("a", "The sensor records violet light."),
        ("c", "The sensor records amber light."),
    ]:
        candidate = anchor(eid, text)
        candidate["support_id"] = eid
        add_section_context(candidate, registry, {})
        inventory[eid] = candidate
    result = service._documentary_need_completion(
        [{"need": "Explain what light the sensor records"}], inventory, []
    )
    assert result and result[0]["support_ids"] == ["a"]
    assert "amber" not in result[0]["text"]


def test_criterion_lead_in_keeps_the_conditions_that_follow_it():
    from nasa_fire_ai.services.conversation import ConversationService

    lead = "To pass, both conditions shall be satisfied:"
    body = lead + "\n(1) The violet flash must cease.\n(2) No debris may remain."
    row = {
        "evidence_id": "criteria",
        "page": 1,
        "text": "8.2 Violet Response (Test 6)\n8.2.3 Criteria\n" + body,
    }
    registry = SimpleNamespace(
        db=SimpleNamespace(execute=lambda *args: [row]), resolve=lambda eid: row
    )
    candidate = anchor("criteria", lead)
    candidate["support_id"] = "criterion"
    service = ConversationService(SimpleNamespace(registry=registry))
    service._need_is_communicated = lambda *args: False
    result = service._documentary_need_completion(
        [{"need": "conditions to pass"}], {"criterion": candidate}, []
    )
    assert result
    assert "The violet flash must cease." in result[0]["text"]
    assert "No debris may remain." in result[0]["text"]


def test_registered_version_is_a_reference_while_altered_version_and_values_remain():
    registry = source_registry()
    candidate = anchor("a", "The sensor records violet light.")
    assert (
        registered_document_references(
            "NASA-STD-9876Z Change 8 records 23 Pa.", [candidate], registry
        ).strip()
        == "records 23 Pa."
    )
    assert "Change 7" in registered_document_references(
        "NASA-STD-9876Z Change 7 records 23 Pa.", [candidate], registry
    )


def test_exact_quote_keeps_registered_heading_without_becoming_a_new_observation():
    registry = source_registry()
    candidate = anchor("b", "The specimen shall emit no debris.")
    add_section_context(candidate, registry, {})
    assert verify_paraphrase(candidate["text"], [candidate], registry, None)["supported"]
    result = verify_paraphrase(
        "The criterion is an experimental observation.",
        [candidate],
        registry,
        SimpleNamespace(check=lambda p, h: {"supported": True}),
    )
    assert not result["supported"]
    assert any("normative criterion" in error for error in result["errors"])


def test_report_cross_reference_does_not_split_a_scientific_sentence():
    from nasa_fire_ai.services.conversation import paragraph_spans

    text = (
        "The violet response is shown in Fig. 8 with a narrow band. The sensor records amber light."
    )
    assert list(paragraph_spans(text)) == [
        "The violet response is shown in Fig. 8 with a narrow band.",
        "The sensor records amber light.",
    ]


def test_requested_method_expansion_keeps_sibling_fields_and_page_continuation():
    from nasa_fire_ai.services.document_sections import requested_method_passages

    registry = source_registry()
    selected = requested_method_passages(registry, {"fictional-standard"}, "Explain Test 6", {})
    assert {row["evidence_id"] for row in selected} == {"a", "b"}
    assert "The sensor records violet light." in selected[0]["text"]
    assert "The specimen shall emit no debris." in selected[1]["text"]
    assert not any("amber light" in row["text"] for row in selected)
    assert requested_method_passages(registry, {"fictional-standard"}, "Explain Test 8", {}) == []
