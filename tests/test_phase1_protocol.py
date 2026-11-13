"""Evaluation protocol v2: evidence-anchored finders and separate outcome states; synthetic."""

import pytest

from nasa_fire_ai.evaluation.phase1_protocol import (
    ambiguity,
    candidates,
    evaluate,
    outcome,
    value_key,
)

QUOTE = "The coupon charred at 34 kPa."
TARGET = {
    "id": "quantities-01",
    "kind": "quantities",
    "evidence_id": "E-1",
    "start": 100,
    "end": 100 + len(QUOTE),
    "quote": QUOTE,
    "expression": "34",
    "unit": "kPa",
}


def record(rid, kind="quantities", state="SOURCE_SUPPORTED", start=100, reasons=(), **item):
    return {
        "id": rid,
        "kind": kind,
        "status": "REJECTED"
        if state == "REJECTED"
        else "SOURCE_SUPPORTED"
        if state == "SOURCE_SUPPORTED"
        else "UNRESOLVED",
        "proposal_state": state,
        "reasons": list(reasons),
        "support_spans": [{"evidence_id": "E-1", "start": start, "end": start + 20}],
        "proposal": item,
    }


def test_a_record_matches_by_its_original_passage_value_and_unit():
    same = record("a", expression="34", unit="kPa", subject="run")
    elsewhere = record("b", start=900, expression="34", unit="kPa", subject="run")
    other_value = record("c", expression="12", unit="kPa", subject="run")
    other_unit = record("d", expression="34", unit="psia", subject="run")
    found = candidates(TARGET, [same, elsewhere, other_value, other_unit])
    assert [r["id"] for r in found] == ["a"]


@pytest.mark.parametrize(
    ("a", "b"), [("34±2", "34 +/- 2"), ("1,000", "1000"), ("10–20", "10-20"), ("< 6", "<6")]
)
def test_printed_value_forms_are_normalized(a, b):
    assert value_key(a) == value_key(b)


def test_an_entity_matches_whole_words_of_its_printed_identity():
    target = {**TARGET, "id": "entities-01", "kind": "entities", "quote": "Panel C30 Study"}
    longer = record("a", kind="entities", label="Panel C30 Study for Exploration Cabins")
    inside_a_word = record("b", kind="entities", label="C3")
    assert [r["id"] for r in candidates(target, [longer, inside_a_word])] == ["a"]


def test_retained_context_and_unresolved_records_are_not_recall():
    retained = record(
        "r", kind="statements", epistemic="documentary_context", text=QUOTE, subjects=[]
    )
    held = record("h", state="STRUCTURALLY_WELL_FORMED", reasons=["X"], expression="34")
    assert outcome([retained]) == "EVIDENCE_RETAINED"
    assert outcome([held]) == "INCOMPLETE"
    assert outcome([]) == "OMITTED"


def test_a_complete_staged_extraction_is_complete_but_still_needs_adjudication():
    staged = record(
        "s",
        state="PROPOSED_ONTOLOGY_EXTENSION",
        reasons=["UNREGISTERED_INFORMATION_CLASS"],
        expression="34",
        unit="kPa",
        class_id="PlannedActivity",
    )
    (row,) = evaluate([TARGET], [staged])["targets"]
    assert row["outcome"] == "COMPLETE_WITH_STAGED_EXTENSION"
    assert row["correctness"] == "PENDING_ADJUDICATION"
    assert evaluate([TARGET], [staged], judgments={"s": "correct"})["counts"]["recalled"] == 1
    # A term approved in the run's ontology version is approved, not staged.
    approved = evaluate([TARGET], [staged], approved_terms={"PlannedActivity"})
    assert approved["targets"][0]["outcome"] == "COMPLETE"


def test_one_record_credits_one_target_only():
    # Two targets of one passage that a single record matches: review, not two recalls.
    q05 = {**TARGET, "id": "q05"}
    q06 = {**TARGET, "id": "q06"}
    shared = record("s", expression="34", unit="kPa", subject="run")
    result = evaluate([q05, q06], [shared], judgments={"s": "correct"})
    assert result["counts"]["recalled"] == 0
    assert {r["ambiguity"] for r in result["targets"]} == {"SHARED_RECORD"}


def test_duplicates_and_inactive_readings_never_count():
    inactive = {**record("i", expression="34", unit="kPa"), "active_proposal": False}
    duplicate = {**record("d", expression="34", unit="kPa"), "duplicate_of": "x"}
    result = evaluate([TARGET], [inactive, duplicate], judgments={"i": "correct", "d": "correct"})
    assert result["counts"]["recalled"] == 0 and result["targets"][0]["outcome"] == "OMITTED"


def test_historical_target_judgments_must_name_their_run():
    held = record("h", expression="34", unit="kPa")
    with pytest.raises(ValueError):
        evaluate([TARGET], [held], historical_correct_targets={"quantities-01"})
    named = evaluate(
        [TARGET],
        [held],
        historical_correct_targets={"quantities-01"},
        historical_run_id="r1",
        run_id="r1",
    )
    assert named["counts"]["recalled"] == 1 and named["historical_run_id"] == "r1"


def test_ambiguity_groups_follow_the_target_not_the_passage():
    # A figure number or a unit exponent in the passage is not a second value.
    figure = {**TARGET, "quote": "1200 kg/m3 (Figure 4)", "expression": "1200", "unit": "kg/m3"}
    assert ambiguity(figure, [record("a", expression="1200", unit="kg/m3")]) is None
    # A value counts only as a whole number: 5 is not inside 15, 50 or 2025.
    five = {**TARGET, "expression": "5"}
    assert ambiguity(five, [], document_text="15 of 50 runs in 2025, 5 kPa") is None
    assert ambiguity(five, [], document_text="5 kPa here; 5 kPa there") == (
        "SAME_VALUE_IN_SEVERAL_PASSAGES"
    )
    thousand = {**TARGET, "expression": "1,000"}
    assert ambiguity(thousand, [], document_text="1,000 kPa and 1000 kPa") == (
        "SAME_VALUE_IN_SEVERAL_PASSAGES"
    )
    # Metamorphic: the same value given to two subjects is a subject question.
    two = [
        record("a", expression="34", unit="kPa", subject="run"),
        record("b", expression="34", unit="kPa", subject="cup"),
    ]
    assert ambiguity(TARGET, two) == "SUBJECT_OR_RELATION"


def test_a_relation_misses_endpoints_only_when_no_candidate_has_both():
    relation = {**TARGET, "kind": "relations"}
    with_both = {
        **record("a", kind="relations", relation="hasMaterial"),
        "subject": "s",
        "object": "m",
    }
    assert ambiguity(relation, [with_both]) is None
    without = {**record("b", kind="relations", relation="hasMaterial"), "subject": "s"}
    assert ambiguity(relation, [without]) == "MISSING_ENDPOINTS"
    # No candidate at all is an omission, not a missing endpoint.
    assert ambiguity(relation, []) is None


def test_precision_and_critical_errors_come_from_record_judgments():
    good = record("g", expression="34", unit="kPa")
    bad = record("b", start=900, expression="7", unit="cm")
    critical = record("c", start=900, expression="9", unit="cm")
    open_ = record("o", start=900, expression="2", unit="cm")
    result = evaluate(
        [TARGET],
        [good, bad, critical, open_],
        judgments={"g": "correct", "b": "incorrect", "c": "critical"},
    )
    assert result["precision"] == {
        "supported_records": 4,
        "judged": 3,
        "correct": 1,
        "critical": 1,
        "unjudged": 1,
        "unjudged_records": ["o"],
        "value": None,
    }


def test_inaccessible_targets_and_figures_are_outside_the_denominator():
    figure = {**TARGET, "id": "figures-01", "kind": "figures"}
    blocked = {**TARGET, "id": "quantities-02", "outcome": "inaccessible"}
    assert evaluate([figure, blocked], [])["counts"]["accessible"] == 0


def test_a_quantity_is_anchored_at_its_own_printed_value():
    # One support span holding two passages that print the same value: the value's
    # own position decides which target the record reads.
    first = {**TARGET, "id": "q-first", "start": 100, "end": 140}
    second = {**TARGET, "id": "q-second", "start": 141, "end": 180}
    wide = {
        **record("w", expression="34", unit="kPa"),
        "support_spans": [{"evidence_id": "E-1", "start": 90, "end": 190}],
        "quantity_value_spans": [{"evidence_id": "E-1", "start": 130, "end": 136}],
    }
    result = evaluate([first, second], [wide], judgments={"w": "correct"})
    rows = {r["target"]: r for r in result["targets"]}
    assert rows["q-first"]["correctness"] == "CORRECT"
    assert rows["q-second"]["outcome"] == "OMITTED"
