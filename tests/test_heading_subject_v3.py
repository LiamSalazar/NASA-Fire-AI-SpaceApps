"""SCIENCE_HEADING_SUBJECT_V3 (on by default; "0" turns it off), "conflict only": the current rule (the
governing major heading names the proposed subject) stays; the record is held with
HEADING_SUBJECT_CONFLICT only when a real subsection heading between that major heading
and the span names a different validated entity. A list lead, an inline label or a
caption naming another entity is not a heading and changes nothing; a subsection that
names no entity changes nothing; nothing is ever substituted. Invented text only (B8).
"""

import ast
import glob
import gzip
import json
from pathlib import Path

import pytest
from test_document_extraction import entity, submitted, support, validate
from test_document_extraction import service as _service
from test_new_prompt_text_b8 import V4, long_phrases
from test_prompt_has_no_source_phrases import phrases

from nasa_fire_ai.ingestion import document_extraction as de
from nasa_fire_ai.ingestion.document_extraction import Output

service = _service
FLAG = "SCIENCE_HEADING_SUBJECT_V3"
BASIS = "GOVERNING_HEADING_NAMES_PROPOSED_SUBJECT"
HELD = "STATEMENT_SUBJECT_APPLICABILITY_UNRESOLVED"
CONFLICT = "HEADING_SUBJECT_CONFLICT"

STRUT = "Tension Strut (TS) 6, unit 22"
CLEVIS = "Clevis Block (CB) 3"

# Statements, each under a different structural position of the fixture.
UNDER_MAJOR = "The end fitting kept its preload."
AFTER_CAPTION = "The paint near the eyelet stayed intact."
AFTER_LEAD = "The cotter pin sat flush."
NEUTRAL_SUB = "The threads showed no galling."
CONFLICT_SUB = "The bore showed shallow scoring."
CLOSED_SUB = "The rod stayed within tolerance."
SUBJECT_SUB = "The jam nut held its torque mark."
ENUMERATED = "The end cap stayed seated."


def document(
    primary=STRUT,
    primary_short="TS 6",
    other=CLEVIS,
    other_short="CB 3",
    conflict_heading=True,
    swap=False,
    conflict_line=None,
):
    neutral_body, conflict_body = (
        (CONFLICT_SUB, NEUTRAL_SUB) if swap else (NEUTRAL_SUB, CONFLICT_SUB)
    )
    return "".join(
        [
            "Synthetic Strut Study\n",
            "I. Introduction\n",
            "Struts of this kind hold radiator panels.\n",
            "II. Specimens\n",
            f"The {primary} was cycled five hundred times.\n",
            f"The {other} was cycled two hundred times.\n",
            f"III. {primary_short} Cycling Results\n",
            f"{UNDER_MAJOR}\n",
            # A caption naming the other entity: not a heading (mirrors the shape that
            # held the earlier stricter rule).
            f"Plot 2 - {other_short} Strain During the Second Cycling Block\n",
            f"{AFTER_CAPTION}\n",
            # A list lead naming the other entity: not a heading either.
            f"Checks made on the {other_short} side:\n",
            f"- {AFTER_LEAD}\n",
            "Two loading steps were run in order:\n",
            f"1. {other_short} preload step\n",
            "2. Rod alignment step\n",
            f"{ENUMERATED}\n",
            "A. Thread Condition\n",
            f"{neutral_body}\n",
            ((conflict_line or f"B. {other_short} Wear") + chr(10)) if conflict_heading else "",
            f"{conflict_body}\n",
            "C. Rod Straightness\n",
            f"{CLOSED_SUB}\n",
            f"D. {primary_short} Locking Hardware\n",
            f"{SUBJECT_SUB}\n",
            "IV. Discussion\n",
            "The coating had dulled at both ends.\n",
        ]
    )


def statement_record(service, text, subject="primary", **shape):
    p = submitted(service, document(**shape))
    primary = shape.get("primary", STRUT)
    other = shape.get("other", CLEVIS)
    o = Output().model_dump()
    o["entities"] = [
        entity(p, "primary", primary, "Sample", primary),
        entity(p, "other", other, "Sample", other),
    ]
    o["statements"] = [
        {
            "subjects": [subject],
            "text": text,
            "class_id": "ReportedObservation",
            "epistemic": "measured_observation",
            "study": "current",
            "support": support(p, text),
        }
    ]
    (record,) = [r for r in validate(service, p, o)["records"] if r["kind"] == "statements"]
    return record


def flag(monkeypatch, value):
    if value is None:
        monkeypatch.delenv(FLAG, raising=False)
    else:
        monkeypatch.setenv(FLAG, value)


def accepted(record):
    basis = (record.get("scope_context") or {}).get("basis")
    return HELD not in record["reasons"] and basis == BASIS


def conflicted(record):
    return HELD in record["reasons"] and CONFLICT in record["reasons"]


# The audit case, flag on.


def test_a_subsection_naming_another_entity_holds_the_record(service, monkeypatch):
    flag(monkeypatch, "1")
    record = statement_record(service, CONFLICT_SUB)
    assert conflicted(record)
    assert record["heading_subject_conflict"] == "B. CB 3 Wear"
    # Held, never re-attributed to the entity the subsection names.
    assert (record.get("scope_context") or {}).get("basis") != BASIS
    assert record["status"] == "UNRESOLVED"


# Accepted as by the current rule, flag on.


@pytest.mark.parametrize(
    "text",
    [UNDER_MAJOR, NEUTRAL_SUB, CLOSED_SUB, SUBJECT_SUB],
    ids=["under-major", "neutral-subsection", "closed-sibling", "subsection-names-subject"],
)
def test_no_conflicting_subsection_keeps_the_current_rule(service, monkeypatch, text):
    flag(monkeypatch, "1")
    record = statement_record(service, text)
    assert accepted(record)
    assert record["scope_context"]["heading"] == "III. TS 6 Cycling Results"
    assert CONFLICT not in record["reasons"]


@pytest.mark.parametrize(
    "text",
    [AFTER_CAPTION, AFTER_LEAD, ENUMERATED],
    ids=["caption", "list-lead", "numbered-item"],
)
def test_a_line_naming_another_entity_that_is_not_a_heading_changes_nothing(
    service, monkeypatch, text
):
    # The earlier stricter rule held these; a caption, a list lead or an enumerated item
    # is not a subsection heading.
    flag(monkeypatch, "1")
    assert accepted(statement_record(service, text))


# Negatives, flag on: what the current rule already holds stays held, without the new
# reason when no subsection is involved.


def test_never_a_substitute_for_the_heading_subject(service, monkeypatch):
    flag(monkeypatch, "1")
    # The major heading names the strut; the model proposed the clevis. The subsection
    # names the clevis, but the current rule's precondition fails first.
    record = statement_record(service, CONFLICT_SUB, subject="other")
    assert HELD in record["reasons"]
    assert (record.get("scope_context") or {}).get("basis") != BASIS


def test_a_major_heading_naming_nothing_stays_held(service, monkeypatch):
    flag(monkeypatch, "1")
    record = statement_record(service, "The coating had dulled at both ends.")
    assert HELD in record["reasons"]
    assert CONFLICT not in record["reasons"]


def test_a_competitor_in_the_passage_stays_held(service, monkeypatch):
    flag(monkeypatch, "1")
    record = statement_record(service, f"The {CLEVIS} was cycled two hundred times.")
    assert HELD in record["reasons"]


# Metamorphic, flag on.


@pytest.mark.parametrize(
    "text,held",
    [
        (UNDER_MAJOR, False),
        (AFTER_CAPTION, False),
        (NEUTRAL_SUB, False),
        (CONFLICT_SUB, True),
        (CLOSED_SUB, False),
    ],
)
def test_renaming_either_entity_keeps_every_outcome(service, monkeypatch, text, held):
    flag(monkeypatch, "1")
    original = statement_record(service, text)
    renamed = statement_record(
        service,
        text,
        primary="Drag Link (DL) 4, unit 9",
        primary_short="DL 4",
        other="Pivot Lug (PL) 7",
        other_short="PL 7",
    )
    assert conflicted(original) == conflicted(renamed) == held
    assert accepted(original) == accepted(renamed) == (not held)


def test_removing_the_conflicting_subsection_accepts_the_record(service, monkeypatch):
    flag(monkeypatch, "1")
    with_heading = statement_record(service, CONFLICT_SUB)
    without = statement_record(service, CONFLICT_SUB, conflict_heading=False)
    assert conflicted(with_heading) and accepted(without)


def test_moving_the_passage_under_another_subsection_moves_the_outcome(service, monkeypatch):
    flag(monkeypatch, "1")
    # The two bodies trade places: the bore sentence now sits under the neutral
    # subsection, the thread sentence under the conflicting one.
    assert accepted(statement_record(service, CONFLICT_SUB, swap=True))
    assert conflicted(statement_record(service, NEUTRAL_SUB, swap=True))


# Flags off: the current rule, byte for byte.


def test_flag_is_on_by_default(service, monkeypatch):
    flag(monkeypatch, None)
    assert de.heading_subject_v3_enabled()
    assert conflicted(statement_record(service, CONFLICT_SUB))


def test_flags_off_keeps_the_audit_false_acceptance(service, monkeypatch):
    flag(monkeypatch, "0")
    record = statement_record(service, CONFLICT_SUB)
    assert accepted(record) and CONFLICT not in record["reasons"]


@pytest.mark.parametrize(
    "text",
    [UNDER_MAJOR, AFTER_CAPTION, AFTER_LEAD, NEUTRAL_SUB, CONFLICT_SUB, CLOSED_SUB],
)
def test_flags_off_output_is_byte_identical(service, monkeypatch, text):
    flag(monkeypatch, "0")
    zero = statement_record(service, text)
    monkeypatch.setenv(FLAG, "0")
    again = statement_record(service, text)
    assert json.dumps(again, sort_keys=True) == json.dumps(zero, sort_keys=True)


@pytest.mark.parametrize("text", [UNDER_MAJOR, AFTER_CAPTION, NEUTRAL_SUB, CLOSED_SUB])
def test_flag_on_differs_only_where_a_subsection_conflicts(service, monkeypatch, text):
    flag(monkeypatch, "0")
    off = statement_record(service, text)
    flag(monkeypatch, "1")
    on = statement_record(service, text)
    assert json.dumps(off, sort_keys=True) == json.dumps(on, sort_keys=True)


# B8: every literal of this module is invented.


def literals():
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            yield node.value
        elif isinstance(node, ast.JoinedStr):
            yield "".join(v.value for v in node.values if isinstance(v, ast.Constant))


def all_texts():
    yield from literals()
    for shape in ({}, {"swap": True}, {"conflict_heading": False}):
        yield document(**shape)


def test_no_three_word_phrase_of_a_target_quote():
    quotes = []
    for path in glob.glob(f"{V4}/*/source_reference.json"):
        with open(path, encoding="utf-8") as handle:
            quotes += [t["quote"] for t in json.load(handle)["targets"]]
    assert len(quotes) >= 124
    target = set().union(*(phrases(q) for q in quotes))
    assert sorted({" ".join(p) for t in all_texts() for p in phrases(t) & target}) == []


def test_no_five_word_phrase_of_the_development_documents():
    documents = set()
    for path in glob.glob(f"{V4}/independent_*/prepared_1.json.gz"):
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            package = json.load(handle)["package"]
        documents |= long_phrases("\n".join(e["text"] for e in package["evidence"]))
    assert len(documents) > 1000
    assert sorted({" ".join(p) for t in all_texts() for p in long_phrases(t) & documents}) == []


# A numbered or lettered sentence or list item is not a subsection heading.


@pytest.mark.parametrize(
    "line",
    [
        "A. CB 3 was preloaded first.",
        "3.1. CB 3 was preloaded first.",
        "A) CB 3 was preloaded first",
        "b. CB 3 preload is complete!",
        "C. Was CB 3 preloaded?",
    ],
    ids=["letter-sentence", "outline-sentence", "paren-verb", "exclaim", "question"],
)
def test_a_numbered_sentence_is_not_a_subsection_heading(service, monkeypatch, line):
    flag(monkeypatch, None)
    off = statement_record(service, CONFLICT_SUB, conflict_line=line)
    flag(monkeypatch, "1")
    on = statement_record(service, CONFLICT_SUB, conflict_line=line)
    # The veto never reads the line as a heading: the outcome is the current rule's.
    assert CONFLICT not in on["reasons"], on.get("heading_subject_conflict")
    assert "heading_subject_conflict" not in on
    assert accepted(on) == accepted(off) and on["status"] == off["status"]


def test_the_reason_is_added_only_where_the_base_rule_would_accept(service, monkeypatch):
    flag(monkeypatch, "1")
    # Held for another reason: the span sits under a major heading naming nothing.
    p = submitted(service, document().replace("III. TS 6 Cycling Results", "III. Results"))
    o = Output().model_dump()
    o["entities"] = [
        entity(p, "primary", STRUT, "Sample", STRUT),
        entity(p, "other", CLEVIS, "Sample", CLEVIS),
    ]
    o["statements"] = [
        {
            "subjects": ["primary"],
            "text": CONFLICT_SUB,
            "class_id": "ReportedObservation",
            "epistemic": "measured_observation",
            "study": "current",
            "support": support(p, CONFLICT_SUB),
        }
    ]
    (record,) = [r for r in validate(service, p, o)["records"] if r["kind"] == "statements"]
    assert HELD in record["reasons"] and CONFLICT not in record["reasons"]
    assert "heading_subject_conflict" not in record


def test_a_short_form_followed_by_a_decimal_is_not_a_mention():
    # "Hinge Pin (HP) 2" is not named by "HP 2.1": the heading is about another unit.
    subject = {"label": "Hinge Pin (HP) 2"}
    assert not de.names_entity(subject, "HP 2.1 Load Results")
    assert de.names_entity(subject, "HP 2 Load Results")
    assert de.names_entity(subject, "the load on HP 2. Then")
