"""SCIENCE_CANDIDATE_HYGIENE: the printed terms worth offering (invented document and candidates)."""

from nasa_fire_ai.ingestion.semantic_candidates import (
    candidate_hygiene_enabled,
    candidate_hygiene_request_enabled,
    clean_candidates,
)

PAGE = (
    "Ana Moreno, Sol Duarte\n"
    "Institute of Dry Systems\n"
    "Abstract\n"
    "Tests used a tube furnace and a high auto-ignition temperature probe. "
    "The tube furnace held the Rack Char Study sample near the wall of the glass "
    "chamber and the long chamber door\nstayed shut.\n"
    "References\n[1] Moreno, A., Furnace work, 1990.\n"
)
DOCUMENT = {
    "segments": [
        {
            "evidence_id": "E1",
            "source_id": "S1",
            "section": "Body",
            "start": 0,
            "end": len(PAGE),
            "text": PAGE,
        }
    ]
}


def candidate(label, coverage="UNCOVERED", n=1, **extra):
    places = []
    start = -1
    for _ in range(n):
        start = PAGE.index(label, start + 1)
        places.append(
            {"evidence_id": "E1", "quote": label, "start": start, "end": start + len(label)}
        )
    return {"id": "c-" + label, "label": label, "coverage": coverage, "evidence": places, **extra}


def clean(*candidates):
    dropped = []
    return clean_candidates(list(candidates), DOCUMENT, dropped), dropped


def test_a_term_printed_only_in_the_byline_is_dropped():
    kept, dropped = clean(candidate("Institute of Dry Systems"), candidate("tube furnace", n=2))
    assert [c["label"] for c in kept] == ["tube furnace"]
    assert dropped[0]["hygiene"] == "H1_ZONE"


def test_a_term_only_inside_a_longer_candidate_is_a_fragment():
    kept, dropped = clean(candidate("tube furnace"), candidate("tube"))
    assert [c["label"] for c in kept] == ["tube furnace"]
    assert dropped[0]["hygiene"] == "H2_FRAGMENT"


def test_a_term_cut_at_a_wrapped_line_end_is_a_fragment():
    kept, dropped = clean(candidate("long chamber door"))
    assert kept == [] and dropped[0]["hygiene"] == "H2_FRAGMENT"


def test_a_premodifier_does_not_qualify_a_class_by_its_last_word():
    kept, _ = clean(candidate("high auto-ignition", coverage="QUALIFIES"))
    assert kept[0]["coverage"] == "UNCOVERED" and kept[0]["hygiene"] == "H3_NOT_THE_HEAD"


def test_a_head_followed_by_a_preposition_still_qualifies():
    kept, _ = clean(candidate("glass chamber", coverage="QUALIFIES"))
    assert kept[0]["coverage"] == "QUALIFIES" and "hygiene" not in kept[0]


def test_a_capitalised_name_qualifies_no_class():
    kept, _ = clean(candidate("Rack Char Study", coverage="QUALIFIES"))
    assert kept[0]["coverage"] == "UNCOVERED" and kept[0]["hygiene"] == "H4_PROPER_NAME"


def test_the_input_is_not_changed_and_the_flags_are_off(monkeypatch):
    one = candidate("Rack Char Study", coverage="QUALIFIES")
    before = repr(one)
    clean_candidates([one], DOCUMENT)
    assert repr(one) == before
    monkeypatch.delenv("SCIENCE_CANDIDATE_HYGIENE", raising=False)
    monkeypatch.delenv("SCIENCE_CANDIDATE_HYGIENE_REQUEST", raising=False)
    assert not candidate_hygiene_enabled() and not candidate_hygiene_request_enabled()
