"""The split of the former SCIENCE_STRUCTURE_FIXES: two general structure flags, both off by
default, and the retired value-recovery offer of a heading-named subject. With both flags off
(unset, "0", or the retired flag set) every request is byte-identical. Synthetic (B8)."""

import json
from pathlib import Path

import pytest
from test_document_extraction import submitted
from test_slide_heading_scope import deck, deck_pdf, requests_for
from test_slide_heading_scope import fresh as _fresh

fresh = _fresh

SRC = Path(__file__).resolve().parents[1] / "src"

PAPER = (
    "Synthetic Tile Study\n"
    "II. Test Article\nThe Glazed Floor Tile (GFT) 2.3, kiln run 9 was fired at 1200 C.\n"
    "III. GFT 2.3 Post Firing Inspection\nThe surface temperature reached 412 K after cooling.\n"
    "References\n"
    "[1] A. Author, Kiln tests, 1999.\n"
    "\n"
    "Table 9: Crack widths\n"
    "Plate A 0.4 mm\n"
    "[2] B. Author, Glaze studies, 2001.\n"
)

OFF = [
    {},
    {"SCIENCE_SLIDE_HEADING_SCOPE": "0", "SCIENCE_TABLE_AFTER_REFERENCES": "0"},
    {"SCIENCE_STRUCTURE_FIXES": "1"},
]


def identity_answer(payload):
    # The identity stage names the tile, so value recovery has a subject to offer.
    if payload["stage"] == "identity" and payload.get("focus") is None:
        anchor = next(
            (a["id"] for a in payload["source_anchors"] if "Glazed Floor" in a["quote"]), None
        )
        if anchor is None:
            return {}
        return {
            "entities": [
                {
                    "key": "gft",
                    "label": "Glazed Floor Tile (GFT) 2.3, kiln run 9",
                    "class_id": "Sample",
                    "study": "current",
                    "support": [anchor],
                }
            ]
        }
    return {}


@pytest.mark.parametrize("make", ["paper", "deck"])
def test_flags_off_requests_are_byte_identical(fresh, monkeypatch, make):
    runs, data = [], deck_pdf()
    for env in OFF:
        service = fresh()
        package = submitted(service, PAPER) if make == "paper" else deck(service, data=data)
        sent = requests_for(service, monkeypatch, package, env=env, answer=identity_answer)
        runs.append(json.dumps(sent, sort_keys=True))
    assert runs[0] and runs[0] == runs[1] == runs[2]


def test_the_retired_flag_is_read_nowhere():
    for path in SRC.rglob("*.py"):
        assert "SCIENCE_STRUCTURE_FIXES" not in path.read_text(encoding="utf-8"), path


def test_value_recovery_offers_no_subject_on_a_heading_alone(fresh, monkeypatch):
    # Retired (c): the governing heading naming a subject is a validation reading only
    # (heading_names_subject); recovery never offers it, and the old flag has no effect.
    for flags in ([], ["SCIENCE_SLIDE_HEADING_SCOPE", "SCIENCE_TABLE_AFTER_REFERENCES"]):
        service = fresh()
        sent = requests_for(
            service,
            monkeypatch,
            submitted(service, PAPER),
            flags,
            env={"SCIENCE_STRUCTURE_FIXES": "1"},
            answer=identity_answer,
        )
        offered = [
            c
            for p in sent
            for c in p.get("unstructured_quantity_candidates", [])
            if "412" in json.dumps(c)
        ]
        assert offered, flags
        assert all(not c.get("source_applicable_subjects") for c in offered), flags


def test_both_flags_on_change_only_what_each_flag_owns(fresh, monkeypatch):
    # A paper with no back-matter table is not a slide deck: both flags leave it unchanged.
    text = PAPER.split("\nTable 9")[0] + "\n"
    off, on = fresh(), fresh()
    a = requests_for(off, monkeypatch, submitted(off, text), answer=identity_answer)
    b = requests_for(
        on,
        monkeypatch,
        submitted(on, text),
        ["SCIENCE_SLIDE_HEADING_SCOPE", "SCIENCE_TABLE_AFTER_REFERENCES"],
        answer=identity_answer,
    )
    assert a and json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
