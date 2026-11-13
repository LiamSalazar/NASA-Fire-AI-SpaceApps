"""Scalar cells in a documentary table do not declare scientific sections."""

from types import SimpleNamespace

from nasa_fire_ai.services.document_sections import section_index


def test_numeric_and_boolean_cells_do_not_establish_section_ancestry():
    rows = [
        {
            "evidence_id": "invented-page",
            "page": 2,
            "text": "4.1 Violet Results\n\nRecorded table\n77.82\nNo\n0.43\n\nThe violet sensor recorded a pulse.",
        }
    ]
    registry = SimpleNamespace(db=SimpleNamespace(execute=lambda *args: rows))
    assert [event["key"] for event in section_index(registry, "invented-report")] == ["4.1"]


def test_legitimate_heading_with_negative_word_is_retained():
    rows = [
        {
            "evidence_id": "invented-page",
            "page": 2,
            "text": "4.2 No Violet Signal\nThe detector remained silent.",
        }
    ]
    registry = SimpleNamespace(db=SimpleNamespace(execute=lambda *args: rows))
    assert [event["key"] for event in section_index(registry, "invented-report")] == ["4.2"]


def test_document_lookup_preserves_the_registered_version():
    from nasa_fire_ai.services.document_sections import named_source_ids

    rows = [{"source_id": "nasa-std-9876z-change8", "title": "NASA-STD-9876Z w/CHANGE 8"}]
    registry = SimpleNamespace(db=SimpleNamespace(execute=lambda *args: rows))
    assert named_source_ids("NASA-STD-9876Z with Change 8", registry) == {"nasa-std-9876z-change8"}
    assert not named_source_ids("NASA-STD-9876Z with Change 9", registry)
    assert named_source_ids("NASA-STD-9876Z", registry) == {"nasa-std-9876z-change8"}
