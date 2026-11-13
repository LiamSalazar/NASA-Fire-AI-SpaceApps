"""A caption that prints its data as taken during a named test series names that group; synthetic."""

from test_document_extraction import entity, submitted
from test_document_extraction import service as _service

from nasa_fire_ai.ingestion.document_extraction import Output, structure_entity_candidates
from nasa_fire_ai.ingestion.document_structure import structure

service = _service

TEXT = (
    "II. Methods\nThe Alpha valve was impacted in oxygen.\n"
    "Figure 3 - Valve Pressures During the First Wetted Alpha Impact Test Series (~90 ms)\n"
    "Figure 5 - Valve Pressures During the second Wetted Alpha Impact Test\n"
    "Series at ~40 ms\n"
    "Figure 6 - Seal Temperature During the Twenty Dry Alpha Impact Tests to 30 MPa\n"
)


def candidates(service, text=TEXT, entities=()):
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [entity(p, k, label, cls, quote) for k, label, cls, quote in entities]
    return {
        c["label"]: c
        for c in structure_entity_candidates(o, p, structure(p, service.root))
        if c["class_id"] == "ExperimentFamily"
    }


def test_each_series_a_caption_names_is_a_group_candidate(service):
    found = candidates(service)
    assert set(found) == {
        "First Wetted Alpha Impact Test Series",
        "second Wetted Alpha Impact Test Series",  # wrapped onto the caption's next line
        "Twenty Dry Alpha Impact Tests",
    }
    assert all(c["study"] == "current" for c in found.values())


def test_a_cited_caption_or_a_caption_without_a_series_names_no_group(service):
    text = (
        "II. Methods\nThe Alpha valve was impacted in oxygen.\n"
        "Figure 3 - Valve Pressures During the First Wetted Alpha Impact Test Series (3)\n"
        "Figure 4 - Valve Pressures of the First Wetted Alpha Impact Test Series\n"
        "Figure 5 - Seal Temperature During Impact Tests\n"
    )
    assert candidates(service, text) == {}


def test_a_group_already_proposed_keeps_its_record(service):
    proposed = [
        ("g", "Twenty Dry Alpha Impact Tests", "ExperimentFamily", "Twenty Dry Alpha Impact Tests")
    ]
    assert "Twenty Dry Alpha Impact Tests" not in candidates(service, entities=proposed)


def test_a_name_two_printed_series_share_does_not_hide_them(service):
    # Metamorphic: a proposed group named "Wetted Alpha Impact Test Series" is
    # shared by the first and second series, so both stay distinct candidates;
    # a name only one printed series contains is that series.
    shared = [
        (
            "g",
            "Wetted Alpha Impact Test Series",
            "ExperimentFamily",
            "Wetted Alpha Impact Test Series",
        )
    ]
    found = candidates(service, entities=shared)
    assert {"First Wetted Alpha Impact Test Series", "second Wetted Alpha Impact Test Series"} <= (
        set(found)
    )
    single = [("g", "Dry Alpha Impact Tests", "ExperimentFamily", "Dry Alpha Impact Tests")]
    assert "Twenty Dry Alpha Impact Tests" not in candidates(service, entities=single)
