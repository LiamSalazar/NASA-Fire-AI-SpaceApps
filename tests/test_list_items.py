"""List items (SCIENCE_LIST_ITEMS, default mode 2; 0 turns it off). Invented text only (B8)."""

import pytest
from test_document_extraction import entity, submitted, support, validate
from test_document_extraction import service as _service

from nasa_fire_ai.ingestion import printed_layout as pl
from nasa_fire_ai.ingestion.document_extraction import Output

service = _service
CLASSES = {
    "documentary_context": "Publication",
    "experimental_configuration": "ExperimentalCondition",
}


@pytest.mark.parametrize("glyph", ["•", "▪", "", "1.", "a)"])
def test_a_verbless_item_has_no_clause_whatever_its_marker(glyph):
    text = f"{glyph} 40% wool felt for seat covers"
    assert len(pl.list_items(text)) == 1 and not pl.item_has_clause(text)


@pytest.mark.parametrize(
    "text",
    [
        "• Coupons were weighed before burning",
        "• The felt is self-extinguishing",
        "• Panels will be retested",
    ],
)
def test_an_item_with_a_finite_auxiliary_or_past_form_has_a_clause(text):
    assert pl.item_has_clause(text)


def test_a_marker_alone_on_its_line_marks_the_next_line():
    items = pl.list_items("\n40% wool felt\n\nfoam panel")
    assert len(items) == 2 and items[0]["marker"] == ""


def test_items_run_to_the_next_marker_or_a_blank_line():
    text = "• Cut coupons\n  to size\n• Weigh coupons\n\nNot an item"
    items = pl.list_items(text)
    assert [text[i["start"] : i["end"]] for i in items] == [
        "• Cut coupons\n  to size",
        "• Weigh coupons",
    ]


@pytest.mark.parametrize(
    "text",
    [
        "Selected screening steps:\n• Cut coupons\n• Weigh coupons",
        "Selected screening steps:\n1. Cut coupons\n2. Weigh coupons",
        "Selected screening steps:\n▪ Cut coupons\n▪ Weigh coupons",
        "Selected screening steps:\n\n•\nCut coupons\n•\nWeigh coupons",
        "Typical sequence:\nPrepare\nBurn chamber\nInspect",
    ],
)
def test_a_lead_with_its_items_is_found(text):
    assert pl.list_lead_with_items(text)


@pytest.mark.parametrize(
    "text",
    [
        "Results were as follows: the felt passed and the foam failed.",
        "The panel was tested twice:\n\n“The panel shall not ignite.”\n\nThat panel was then cut.",
        "Selected screening steps:\n• Cut coupons",
        "Cut coupons, weigh coupons and inspect them.",
    ],
)
def test_a_colon_in_prose_or_before_a_quotation_is_not_a_list(text):
    assert pl.list_lead_with_items(text) is None


TEXT = (
    "II. Methods\nRun A1 used three coupon types.\n"
    "• 40% wool felt for seat covers\n"
    "Selected screening steps:\n• Cut coupons\n• Weigh coupons\n"
    "• Goal to reduce panel mass\n"
    "• Coupons were weighed before burning\n"
)


def verdict(service, text, role, monkeypatch, flag):
    monkeypatch.setenv("SCIENCE_LIST_ITEMS", flag)
    p = submitted(service, TEXT)
    o = Output().model_dump()
    o["entities"] = [entity(p, "a1", "A1", "ExperimentFamily", "Run A1 used")]
    o["statements"] = [
        {
            "class_id": CLASSES[role],
            "subjects": ["a1"],
            "text": text,
            "epistemic": role,
            "study": "current",
            "support": support(p, text),
        }
    ]
    (record,) = [r for r in validate(service, p, o)["records"] if r["kind"] == "statements"]
    return record


def test_a_verbless_documentary_item_is_held_with_the_flag_only(service, monkeypatch):
    text = "• 40% wool felt for seat covers"
    off = verdict(service, text, "documentary_context", monkeypatch, "0")
    on = verdict(service, text, "documentary_context", monkeypatch, "1")
    assert "STATEMENT_LIST_ITEM_HAS_NO_CLAUSE" not in off["reasons"], off["reasons"]
    assert on["status"] == "UNRESOLVED", on["reasons"]
    assert "STATEMENT_LIST_ITEM_HAS_NO_CLAUSE" in on["reasons"]


@pytest.mark.parametrize(
    "text, role",
    [
        ("2022 Bottom ignition test", "experimental_configuration"),
        ("• Coupons were weighed before burning", "documentary_context"),
    ],
)
def test_other_roles_and_items_with_a_clause_are_unchanged(service, monkeypatch, text, role):
    off = verdict(service, text, role, monkeypatch, "0")
    on = verdict(service, text, role, monkeypatch, "1")
    assert (off["status"], off["reasons"]) == (on["status"], on["reasons"])


def test_a_lead_with_its_items_is_rejected_with_the_flag_only(service, monkeypatch):
    text = "Selected screening steps:\n• Cut coupons\n• Weigh coupons"
    off = verdict(service, text, "documentary_context", monkeypatch, "0")
    on = verdict(service, text, "documentary_context", monkeypatch, "1")
    assert "STATEMENT_IS_A_LIST_LEAD" not in off["reasons"]
    assert on["status"] == "REJECTED" and "STATEMENT_IS_A_LIST_LEAD" in on["reasons"]


def test_front_matter_label_lines_are_not_a_list():
    text = "Report 7\nDocument ID:\nAvailable online at the portal\nPublished 2020\nAuthors listed here"
    assert pl.list_lead_with_items(text) is None


MIXED = (
    "Additional factors and limits include:\n•\nInlet pressure of 40 bar\n•\n"
    "Wall temperature near 90 C\n\nWhile the modelled seal temperatures stayed low, the results\n"
    "suggest the elastomer could soften because the rated limit is 20 C higher."
)


def test_only_lead_leaves_a_statement_that_asserts_more_than_the_list():
    assert pl.list_lead_with_items(MIXED)
    assert pl.list_lead_with_items(MIXED, only_lead=True) is None
    before = "The seal may soften under load.\nAdditional factors include:\n• Inlet pressure\n• Wall heat"
    assert pl.list_lead_with_items(before, only_lead=True) is None


def test_only_lead_still_finds_a_pure_lead_with_its_items():
    text = "Selected screening steps:\n• Cut coupons\n• Weigh coupons"
    assert pl.list_lead_with_items(text, only_lead=True)


def test_version_two_rejects_a_pure_lead_and_leaves_a_mixed_statement(service, monkeypatch):
    pure = "Selected screening steps:\n• Cut coupons\n• Weigh coupons"
    for text, rejected in ((pure, True), (MIXED, False)):
        off = verdict(service, text, "documentary_context", monkeypatch, "0")
        two = verdict(service, text, "documentary_context", monkeypatch, "2")
        assert ("STATEMENT_IS_A_LIST_LEAD" in two["reasons"]) is rejected
        if not rejected:
            assert (off["status"], off["reasons"]) == (two["status"], two["reasons"])


def test_front_matter_stays_untouched_in_version_two(service, monkeypatch):
    text = "Report 7\nDocument ID:\nAvailable online at the portal\nPublished 2020"
    two = verdict(service, text, "documentary_context", monkeypatch, "2")
    assert "STATEMENT_IS_A_LIST_LEAD" not in two["reasons"]


def test_only_lead_keeps_a_flowchart_with_a_label_that_has_an_auxiliary():
    text = "Typical sequence:\nPrepare\nSample being weighed\nInspect"
    assert pl.list_lead_with_items(text, only_lead=True)


def test_the_default_mode_is_two(monkeypatch):
    from nasa_fire_ai.ingestion import printed_layout as pl

    monkeypatch.delenv("SCIENCE_LIST_ITEMS", raising=False)
    assert pl.list_items_mode() == "2"
    for value, mode in (("0", "0"), ("1", "1"), ("2", "2"), ("junk", "0")):
        monkeypatch.setenv("SCIENCE_LIST_ITEMS", value)
        assert pl.list_items_mode() == mode
