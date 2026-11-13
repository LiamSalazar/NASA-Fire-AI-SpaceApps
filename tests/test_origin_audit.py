"""processing.origin_audit: the queue and the control sample for the manual count (invented records)."""

from nasa_fire_ai.ingestion.value_origin import CONTROL_SAMPLE, origin_audit


def record(i, source, status="SOURCE_SUPPORTED", mark="current", anchors=(), decision="PASS"):
    return {
        "id": f"q{i}",
        "kind": "quantities",
        "status": status,
        "proposal": {"expression": str(i)},
        "support_spans": [{"source_id": source}],
        "origin": {
            "mark": mark,
            "mark_source": "quantity",
            "decision": decision,
            "occurrences": [{"anchors": [{"strength": a} for a in anchors]}],
        },
    }


def test_the_queue_holds_supported_current_values_with_an_anchor():
    rs = [
        record(1, "s1", anchors=("strong",)),
        record(2, "s1", anchors=("weak",)),
        record(3, "s1"),
        record(4, "s1", mark="cited", anchors=("strong",)),
        record(5, "s1", status="UNRESOLVED", anchors=("strong",), decision="HOLD"),
    ]
    audit = origin_audit(rs)
    assert [q["id"] for q in audit["review_queue"]] == ["q1", "q2"]
    assert [q["id"] for q in audit["control_sample"]] == ["q3"]
    assert audit["counts"]["SOURCE_SUPPORTED|current|quantity|strong|PASS"] == 1
    assert audit["counts"]["UNRESOLVED|current|quantity|strong|HOLD"] == 1


def test_the_control_sample_is_per_source_fixed_and_capped():
    rs = [record(i, "s1") for i in range(100)] + [record(100 + i, "s2") for i in range(5)]
    a, b = origin_audit(rs), origin_audit(rs)
    assert a == b
    sample = a["control_sample"]
    assert sum(q["source_id"] == "s1" for q in sample) == CONTROL_SAMPLE
    assert sum(q["source_id"] == "s2" for q in sample) == 5


def test_records_without_a_receipt_are_ignored():
    assert origin_audit([{"kind": "entities", "status": "SOURCE_SUPPORTED"}])["counts"] == {}
