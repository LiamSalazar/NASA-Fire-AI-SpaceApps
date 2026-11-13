"""Repeated source labels bind to the intended investigation, without identity fusion."""

from pathlib import Path

import pytest

from nasa_fire_ai.query.native import SemanticGraph
from nasa_fire_ai.query.record_identity import resolve_record_mentions
from nasa_fire_ai.query.v2 import RelationDefinition, SemanticRegistry


@pytest.fixture
def records(monkeypatch):
    from nasa_fire_ai.ingestion import psi_scientific

    monkeypatch.setattr(
        psi_scientific,
        "mappings",
        lambda root: {
            "STUDY-A": {"identifier": "Label", "fields": {}},
            "STUDY-B": {"identifier": "Label", "fields": {}},
        },
    )
    registry = SemanticRegistry(relations=[RelationDefinition("belongsToInvestigation")])
    registry.entity_mentions = {}
    registry.register_target_class("SourceRecord")
    store = SemanticGraph(registry)
    for identity, alias in [("study-a", "VEGA"), ("study-b", "LYRA")]:
        store.add_entity(identity, "Investigation", ["E-source"])
        registry.entity_mentions[identity] = {
            "relation": "belongsToInvestigation",
            "aliases": [alias],
        }
        for label in ["R1", "R2"]:
            record = identity + "-" + label
            store.add_entity(
                record, "SourceRecord", ["E-source"], payload={"reported_identifier": label}
            )
            store.add_relation(record, "belongsToInvestigation", identity, ["E-source"])
    return store


@pytest.mark.parametrize(
    "question",
    [
        "Compare VEGA R1 and LYRA R2.",
        "Compare R1 in VEGA with R2 in LYRA.",
        "For VEGA record R1, compare it to LYRA record R2.",
    ],
)
def test_paired_record_references_do_not_form_a_cross_product(records, question):
    subjects, _ = resolve_record_mentions(question, records, Path("."))
    assert set(subjects) == {"study-a-R1", "study-b-R2"}


@pytest.mark.parametrize(
    "question",
    [
        "Compare R1 across VEGA and LYRA.",
        "Compare VEGA and LYRA record R1.",
    ],
)
def test_shared_investigation_scope_retains_both_source_records(records, question):
    subjects, _ = resolve_record_mentions(question, records, Path("."))
    assert set(subjects) == {"study-a-R1", "study-b-R1"}


def test_an_unresolved_pairing_keeps_the_source_ambiguity(records):
    subjects, _ = resolve_record_mentions("Compare R1 and R2 in VEGA and LYRA.", records, Path("."))
    assert len(subjects) == 4


def test_deictic_modifier_does_not_become_an_investigation_acronym(records):
    records.registry.entity_mentions["study-b"]["aliases"].append("SAME")
    subjects, _ = resolve_record_mentions("The same R1 record in VEGA.", records, Path("."))
    assert subjects == ["study-a-R1"]
    subjects, _ = resolve_record_mentions("SAME record R1.", records, Path("."))
    assert subjects == ["study-b-R1"]


def test_postposed_original_identifier_is_an_explicit_reference(records):
    subjects, _ = resolve_record_mentions(
        "For the R1 record in VEGA, quote its fields.", records, Path(".")
    )
    assert subjects == ["study-a-R1"]
