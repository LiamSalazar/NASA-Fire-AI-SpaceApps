"""Document-local reference resolution preserves source and experimental scope."""

from types import SimpleNamespace

import snowballstemmer

from nasa_fire_ai.services.semantic_support import LocalEntailment
from nasa_fire_ai.services.source_definitions import add_source_definitions, document_definitions


def test_curated_quotation_keeps_distinct_original_pages_and_refuses_missing_content():
    from nasa_fire_ai.services.source_definitions import registered_quotation_fragments

    rows = {
        "a": {
            "evidence_id": "a",
            "document_id": "report",
            "page": 4,
            "text": "Header\nThe vessel contains neon at\n",
        },
        "b": {
            "evidence_id": "b",
            "document_id": "report",
            "page": 5,
            "text": "Header\nreduced pressure. Another topic follows.",
        },
    }
    source = SimpleNamespace(resolve=lambda eid: rows[eid])
    text = "The vessel contains neon at\nreduced pressure."
    spans = registered_quotation_fragments(text, ["b", "a"], source)
    assert [span["evidence_id"] for span in spans] == ["a", "b"]
    assert all(span["text"] in rows[span["evidence_id"]]["text"] for span in spans)
    assert not registered_quotation_fragments(text.replace("neon", "argon"), ["a", "b"], source)
    rows["b"]["document_id"] = "another-report"
    assert not registered_quotation_fragments(text, ["a", "b"], source)


def registry(rows):
    return SimpleNamespace(db=SimpleNamespace(execute=lambda query, args: rows))


def test_declared_same_page_fragments_preserve_gaps_and_validate_locators():
    import sqlite3

    from nasa_fire_ai.services.source_definitions import registered_quotation_fragments

    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.execute("""CREATE TABLE curated_quotation_parts (
        context_id, part_ordinal, evidence_id, part_text,
        passage_start, passage_end, source_checksum)""")
    original = (
        "First detector records light.\nFootnote on another subject.\nSecond detector records heat."
    )
    parts = ["First detector records light.", "Second detector records heat."]
    source = {
        "evidence_id": "p1",
        "document_id": "report",
        "page": 3,
        "text": original,
        "checksum": "source-sha",
    }
    for ordinal, part in enumerate(parts):
        start = original.index(part)
        db.execute(
            "INSERT INTO curated_quotation_parts VALUES (?,?,?,?,?,?,?)",
            ("curated", ordinal, "p1", part, start, start + len(part), "source-sha"),
        )
    registry = SimpleNamespace(db=db, resolve=lambda eid: source if eid == "p1" else None)
    quotation = "\n".join(parts)
    located = registered_quotation_fragments(quotation, ["p1"], registry, context_id="curated")
    assert [span["text"] for span in located] == parts
    assert not registered_quotation_fragments(quotation, ["p1"], registry)
    assert not registered_quotation_fragments(quotation, [], registry, context_id="curated")
    assert not registered_quotation_fragments(
        quotation.replace("heat", "pressure"), ["p1"], registry, context_id="curated"
    )
    db.execute("UPDATE curated_quotation_parts SET source_checksum='changed' WHERE part_ordinal=1")
    assert not registered_quotation_fragments(quotation, ["p1"], registry, context_id="curated")
    db.execute(
        "UPDATE curated_quotation_parts SET source_checksum='source-sha', passage_start=0 WHERE part_ordinal=1"
    )
    assert not registered_quotation_fragments(quotation, ["p1"], registry, context_id="curated")
    db.close()


def test_name_resolution_retains_exact_registered_definition_without_repeated_headers():
    rows = [
        {"evidence_id": "p1", "text": "The Optical Response Module (ORM) measures brightness."},
        {"evidence_id": "p2", "text": "Optical Response Module (ORM)"},
    ]
    source = registry(rows)
    definitions = document_definitions(source, "report-a")
    assert len(definitions) == 1
    anchor = {
        "document_id": "report-a",
        "epistemic_type": "documentary_content",
        "spans": [{"evidence_id": "p3", "text": "The ORM uses a violet filter."}],
    }
    add_source_definitions("The Optical Response Module uses a violet filter.", anchor, source, {})
    assert len(anchor["spans"]) == 2
    assert anchor["spans"][1]["text"] == "Optical Response Module (ORM)"
    assert anchor["spans"][1]["evidence_id"] == "p1"
    assert anchor["spans"][0]["evidence_id"] == "p3"


def test_ambiguous_local_acronym_is_not_reconciled():
    source = registry(
        [
            {
                "evidence_id": "p1",
                "text": "Optical Response Module (ORM). Orbital Research Microscope (ORM).",
            }
        ]
    )
    assert document_definitions(source, "report-a") == []


def test_definition_from_another_document_cannot_establish_this_name():
    calls = []

    def execute(query, args):
        calls.append(args)
        return (
            []
            if args[0] == "report-b"
            else [{"evidence_id": "p1", "text": "Optical Response Module (ORM)"}]
        )

    source = SimpleNamespace(db=SimpleNamespace(execute=execute))
    anchor = {
        "document_id": "report-b",
        "epistemic_type": "documentary_content",
        "spans": [{"evidence_id": "b1", "text": "The ORM records temperature."}],
    }
    add_source_definitions("The Optical Response Module records temperature.", anchor, source, {})
    assert len(anchor["spans"]) == 1
    assert calls == [("report-b",)]


def test_adjective_derivation_does_not_authorize_changed_fuel_identity():
    model = object.__new__(LocalEntailment)
    model.stemmer = snowballstemmer.stemmer("english")
    assert model._changed_terms("experimental setup", "experiment setup") == []
    assert model._changed_terms("methanol fuel", "ethanol fuel")


def test_calculated_field_negation_does_not_certify_a_measured_value():
    from nasa_fire_ai.services.semantic_support import verify_paraphrase

    original = "Tad is a calculated temperature parameter, not a measured temperature."
    source = SimpleNamespace(resolve=lambda eid: {"text": original})
    candidate = {
        "text": original,
        "category": "DIRECT",
        "epistemic_type": "reported_calculated_quantity",
        "conditions": [],
        "spans": [{"evidence_id": "field", "text": original}],
        "typed_fields": [{"role": "reported_calculated_quantity", "aliases": ["Tad"]}],
    }
    permissive = SimpleNamespace(check=lambda p, h: {"supported": True})
    assert verify_paraphrase(original, [candidate], source, permissive)["supported"]
    assert not verify_paraphrase(
        "Tad was measured during the test.", [candidate], source, permissive
    )["supported"]
    assert not verify_paraphrase(
        "Tad was not calculated but measured during the test.", [candidate], source, permissive
    )["supported"]


def test_recorded_identifier_does_not_establish_planning_status():
    from nasa_fire_ai.services.semantic_support import verify_paraphrase

    original = "Test identifier: 7"
    source = SimpleNamespace(resolve=lambda eid: {"text": original})
    candidate = {
        "text": original,
        "category": "DIRECT",
        "epistemic_type": "record_identifier",
        "conditions": [],
        "spans": [{"evidence_id": "field", "text": original}],
        "typed_fields": [{"role": "record_identifier", "aliases": ["Test identifier"]}],
    }
    permissive = SimpleNamespace(check=lambda p, h: {"supported": True})
    assert verify_paraphrase("The test identifier is 7.", [candidate], source, permissive)[
        "supported"
    ]
    assert not verify_paraphrase(
        "The planned test identifier is 7.", [candidate], source, permissive
    )["supported"]


def test_scope_guard_preserves_a_negative_identity_statement():
    from pathlib import Path

    from nasa_fire_ai.ingestion.hackathon import make_store
    from nasa_fire_ai.services.ontology_support import audit_relation

    store = make_store(Path(__file__).resolve().parents[1])
    store.add_entity("example-study", "Investigation", ["E-source"])
    store.registry.entity_mentions["example-study"] = {
        "relation": "belongsToInvestigation",
        "aliases": ["VEGA"],
    }
    store.add_entity("example-summary", "ConfigurationSummary", ["E-source"])
    store.add_relation("example-study", "hasSourceRecord", "example-summary", ["E-source"])
    positive = audit_relation(
        "Every VEGA condition alternative represents a distinct physical run.", [], store, None
    )
    assert positive["scientific_status"] == "ONTOLOGY_INCOMPATIBLE"
    negative = audit_relation(
        "VEGA condition alternatives do not represent identified physical runs.", [], store, None
    )
    assert negative["scientific_status"] != "ONTOLOGY_INCOMPATIBLE"
