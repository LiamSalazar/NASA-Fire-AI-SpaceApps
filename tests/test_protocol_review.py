"""Protocol v2 review of 03d1c84: each finding reproduced before its fix; synthetic."""

import pytest
from test_phase1_protocol import QUOTE, TARGET, record

from nasa_fire_ai.evaluation.phase1_protocol import ambiguity, candidates, evaluate


def staged(rid="s", **extra):
    return record(
        rid,
        state="PROPOSED_ONTOLOGY_EXTENSION",
        reasons=["UNREGISTERED_INFORMATION_CLASS"],
        expression="34",
        unit="kPa",
        class_id="PlannedActivity",
        **extra,
    )


def test_a_record_that_can_be_recall_is_also_in_precision_and_critical_counts():
    result = evaluate([TARGET], [staged()], judgments={"s": "critical"})
    assert result["precision"]["supported_records"] == 1
    assert result["precision"]["critical"] == 1


@pytest.mark.parametrize(
    ("target_unit", "record_unit", "same"),
    [
        ("% O2", "%", True),
        ("%", "% O2", True),
        ("mm OD", "mm", True),
        ("% O2", "% N2", False),
        # Prefix case is meaning: mega is not milli.
        ("MPa", "mPa", False),
        ("kPa", "kpa", True),
    ],
)
def test_a_unit_matches_its_printed_qualified_form_but_never_another_prefix(
    target_unit, record_unit, same
):
    target = {**TARGET, "unit": target_unit}
    found = candidates(target, [record("a", expression="34", unit=record_unit)])
    assert bool(found) is same


def test_a_versioned_target_correction_applies_without_touching_the_frozen_target():
    noted = {**TARGET, "unit": "the printed column header; keep its glyphs"}
    frozen = dict(noted)
    corrections = {"quantities-01": {"unit": "kPa", "rationale": "the unit field holds a note"}}
    result = evaluate(
        [noted],
        [record("a", expression="34", unit="kPa")],
        judgments={"a": "correct"},
        corrections=corrections,
    )
    assert noted == frozen
    assert result["counts"]["recalled"] == 1
    assert result["targets"][0]["correction"] == "the unit field holds a note"
    # Without the versioned correction the note never matches a unit.
    assert evaluate([noted], [record("a", expression="34", unit="kPa")])["counts"]["recalled"] == 0


def test_a_record_shared_by_two_targets_is_assigned_when_the_other_target_has_its_own():
    first = {**TARGET, "id": "q-a"}
    second = {**TARGET, "id": "q-b"}
    both = record("x", expression="34", unit="kPa")
    # "y" reads only the first target: it has another value form the second rejects.
    only_first = record("y", expression="34", unit="kPa")
    second_strict = {**second, "quote": QUOTE}
    result = evaluate(
        [first, second_strict],
        [both, only_first],
        judgments={"x": "correct", "y": "correct"},
    )
    # Two records, two targets: a real assignment credits both.
    assert result["counts"]["recalled"] == 2
    assert not [r for r in result["targets"] if r["ambiguity"] == "SHARED_RECORD"]


def test_assignment_is_deterministic_whatever_the_record_order():
    targets = [{**TARGET, "id": "q-a"}, {**TARGET, "id": "q-b"}]
    records = [record("x", expression="34", unit="kPa"), record("y", expression="34", unit="kPa")]
    one = evaluate(targets, records, judgments={"x": "correct", "y": "correct"})
    two = evaluate(targets, records[::-1], judgments={"x": "correct", "y": "correct"})
    assert one["targets"] == two["targets"]


@pytest.mark.parametrize("value", ["Critical", "critical ", " CORRECT"])
def test_judgments_are_normalized(value):
    result = evaluate([TARGET], [record("a", expression="34", unit="kPa")], judgments={"a": value})
    assert result["precision"]["judged"] == 1
    assert result["precision"]["critical"] + result["precision"]["correct"] == 1


def test_an_unknown_judgment_is_refused():
    with pytest.raises(ValueError):
        evaluate([TARGET], [record("a", expression="34", unit="kPa")], judgments={"a": "ok"})


def test_precision_has_one_value_only_when_every_supported_record_is_judged():
    good = record("g", expression="34", unit="kPa")
    bad = record("b", start=900, expression="7", unit="cm")
    partial = evaluate([TARGET], [good, bad], judgments={"g": "correct"})
    assert partial["precision"]["value"] is None
    full = evaluate([TARGET], [good, bad], judgments={"g": "correct", "b": "incorrect"})
    assert full["precision"]["value"] == 0.5


def test_historical_judgments_must_name_the_run_that_is_evaluated():
    held = record("h", expression="34", unit="kPa")
    with pytest.raises(ValueError):
        evaluate(
            [TARGET],
            [held],
            historical_correct_targets={"quantities-01"},
            historical_run_id="r1",
            run_id="r2",
        )
    named = evaluate(
        [TARGET],
        [held],
        historical_correct_targets={"quantities-01"},
        historical_run_id="r1",
        run_id="r1",
    )
    assert named["counts"]["recalled"] == 1


def test_a_target_without_candidates_has_no_ambiguity_group():
    relation = {**TARGET, "kind": "relations"}
    assert ambiguity(relation, []) is None


def test_a_value_is_not_counted_inside_a_longer_decimal():
    thirty = {**TARGET, "expression": "30"}
    assert ambiguity(thirty, [], document_text="30 kPa, then 30.5 kPa") is None
