"""SCIENCE_MISSING_FACT_REPORT: the uncovered printed terms, report only (invented records)."""

from nasa_fire_ai.ingestion.scientific_coverage import (
    missing_fact_report,
    missing_fact_report_enabled,
)

DOCUMENT = {"segments": [], "sections": []}


def candidate(label, start, coverage="UNCOVERED", **extra):
    return {
        "id": "c-" + label,
        "label": label,
        "coverage": coverage,
        "evidence": [
            {"evidence_id": "E1", "quote": label, "start": start, "end": start + len(label)}
        ],
        **extra,
    }


def record(i, start, end, status="SOURCE_SUPPORTED", label=None):
    return {
        "id": i,
        "kind": "statements",
        "status": status,
        "proposal": {"label": label} if label else {},
        "support_spans": [{"evidence_id": "E1", "start": start, "end": end}],
    }


def report(records, candidates):
    return missing_fact_report(records, candidates, DOCUMENT, {"E1": "src-1"})


def test_an_uncovered_term_no_record_covers_is_reported():
    out = report([record("r1", 0, 40)], [candidate("tube furnace", 300)])
    assert out["count"] == 1 and out["per_source"] == {"src-1": 1}
    item = out["items"][0]
    assert item["printed"] == "tube furnace" and item["start"] == 300
    assert item["nearest_record_ids"] == ["r1"]


def test_a_term_under_a_support_span_or_a_label_is_not_reported():
    assert report([record("r1", 290, 330)], [candidate("tube furnace", 300)])["count"] == 0
    assert (
        report([record("r1", 0, 5, label="Tube Furnace")], [candidate("tube furnace", 300)])[
            "count"
        ]
        == 0
    )


def test_a_rejected_record_covers_nothing():
    assert (
        report([record("r1", 290, 330, status="REJECTED")], [candidate("tube furnace", 300)])[
            "count"
        ]
        == 1
    )


def test_a_candidate_already_covered_or_qualified_is_not_reported():
    assert report([], [candidate("tube furnace", 300, coverage="COVERED")])["count"] == 0
    assert report([], [candidate("tube furnace", 300, coverage="QUALIFIES")])["count"] == 0


def test_the_report_changes_nothing():
    records = [record("r1", 0, 40)]
    candidates = [candidate("tube furnace", 300)]
    before = (repr(records), repr(candidates))
    report(records, candidates)
    assert (repr(records), repr(candidates)) == before


def test_the_flag_is_off_by_default(monkeypatch):
    monkeypatch.delenv("SCIENCE_MISSING_FACT_REPORT", raising=False)
    assert not missing_fact_report_enabled()
