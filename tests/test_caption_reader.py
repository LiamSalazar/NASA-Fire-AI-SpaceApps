"""One caption reader (SCIENCE_CAPTION_READER, on by default; =0 turns it off). Invented text only (B8)."""

import pytest

from nasa_fire_ai.ingestion import printed_layout as pl
from nasa_fire_ai.ingestion.statement_integrity import fragment_context


@pytest.mark.parametrize(
    "line, kind, number",
    [
        ("Figure 2 - Rig layout", "figure", "2"),
        ("FIGURE 2 – Rig layout", "figure", "2"),
        ("Fig.3: Rig layout", "figure", "3"),
        ("Figure – 1 Coupon before the burn", "figure", "1"),
        ("Table IV. Runs per coupon", "table", "IV"),
        ("Table 2 Results of the screening", "table", "2"),
        ("TABLE 5—Felt coupons", "table", "5"),
    ],
)
def test_a_caption_head_is_read_in_every_printed_form(line, kind, number):
    head = pl.caption_head(line)
    assert head and (head.kind, head.number) == (kind, number)


@pytest.mark.parametrize(
    "line",
    [
        "Figure 3 shows the coupon.",
        "Table 4 lists the runs.",
        "Table 2 results were kept.",
        "Figures are below.",
    ],
)
def test_an_element_reference_is_not_a_caption(line):
    assert pl.caption_head(line) is None


def test_caption_lines_run_to_a_blank_line_or_the_next_head():
    text = "Intro\nFigure 1: Rig\nwrapped part\n\nbody\nTable 2 Runs\nFigure 3. Next"
    found = pl.caption_lines(text)
    assert [(c["kind"], c["number"]) for c in found] == [
        ("figure", "1"),
        ("table", "2"),
        ("figure", "3"),
    ]
    assert found[0]["quote"] == "Figure 1: Rig\nwrapped part"
    assert text[found[1]["start"] : found[1]["end"]] == "Table 2 Runs"


def test_element_references_list_their_numbers():
    found = pl.element_references("See Figures 11 and 12 and Fig. 3a, Tables 1-3.")
    assert [(r["kind"], r["numbers"]) for r in found] == [
        ("figure", ["11", "12"]),
        ("figure", ["3a"]),
        ("table", ["1", "3"]),
    ]


GLUED = [
    "If the rod melted within two seconds, it was\n\nFigure 2.",
    "The upper bound\nFigure 5: Felt coupon, 30 kPa screening values",
    "The upper bound\nFIG. 5 – Felt coupon, 30 kPa screening values",
]
NOT_GLUED = [
    "The approach was to map the limits given in\n\nFigure 3.",
    "The approach was to map the limits given in\nFigure 3.",
    "Figure 3 shows the coupon after the burn.",
    "Figure – 1 Coupon before the burn",
    "The coupon passed.\nTable 4 lists the runs.",
]


@pytest.mark.parametrize("text", GLUED)
def test_a_caption_glued_into_a_statement_is_found(text):
    assert pl.statement_caption(text)


@pytest.mark.parametrize("text", NOT_GLUED)
def test_a_wrapped_reference_or_a_caption_alone_is_not_a_glued_caption(text):
    assert pl.statement_caption(text) is None


def test_a_blank_line_before_a_wrapped_reference_keeps_no_hold():
    assert pl.statement_caption("Limits are given in\n\n\nFigure 3.") is None


def evidence(text):
    return {"e": {"evidence_id": "e", "source_id": "s", "text": text, "page": 1}}


def hold(text, flag, monkeypatch):
    monkeypatch.setenv("SCIENCE_CAPTION_READER", flag)
    return fragment_context(
        text, {"evidence_id": "e", "start": 0, "end": len(text)}, evidence(text)
    )


@pytest.mark.parametrize("text", GLUED)
def test_a_glued_caption_is_held_only_with_the_flag(text, monkeypatch):
    assert hold(text, "0", monkeypatch) is None
    assert hold(text, "1", monkeypatch)["basis"] == "STATEMENT_INCLUDES_A_CAPTION_LINE"


@pytest.mark.parametrize("text", NOT_GLUED)
def test_a_wrapped_reference_is_never_held(text, monkeypatch):
    for flag in ("0", "1"):
        result = hold(text, flag, monkeypatch)
        assert not result or result["basis"] != "STATEMENT_INCLUDES_A_CAPTION_LINE"


@pytest.mark.parametrize(
    "line",
    [
        "Figure 8 - Pre-test photo",
        "Fig. 4: Rig",
        "Table 3. Runs",
        "FIGURE 2 – Rig",
        "Table 2 Results",
        "Figure 3 shows the coupon",
        "Figure 3.",
        "plain text",
    ],
)
def test_flag_off_keeps_the_old_pattern(line, monkeypatch):  # SCIENCE_CAPTION_READER=0
    monkeypatch.setenv("SCIENCE_CAPTION_READER", "0")
    assert pl.is_caption_line(line) == bool(pl.PRINTED_CAPTION_LINE.match(line))


@pytest.mark.parametrize(
    "line, expected",
    [
        ("Figure 8 - Pre-test photo", True),
        ("FIGURE 2 – Rig", True),
        ("Table 2 Results", True),
        ("Figure 3 shows the coupon", False),
        ("Figure 3.", False),
    ],
)
def test_flag_on_reads_a_caption_line_with_text(line, expected, monkeypatch):
    monkeypatch.setenv("SCIENCE_CAPTION_READER", "1")
    assert pl.is_caption_line(line) is expected


def test_flag_on_agrees_with_the_old_pattern_where_it_matched(monkeypatch):
    monkeypatch.setenv("SCIENCE_CAPTION_READER", "1")
    for line in ("Figure 8 - Pre-test photo", "Fig. 4: Rig", "Table 3. Runs", " Table 12a: Burn"):
        assert pl.PRINTED_CAPTION_LINE.match(line) and pl.is_caption_line(line)


def test_caption_prefixed_reads_the_inline_form():
    text = "figure 4: wool blend cloth data"
    assert pl.caption_prefixed("wool blend cloth", text)
    assert not pl.caption_prefixed("felt", text)


def test_opens_with_float_label(monkeypatch):
    monkeypatch.setenv("SCIENCE_CAPTION_READER", "1")
    assert pl.opens_with_float_label("Figure 4 shows the data")
    assert pl.opens_with_float_label("Table IV. Runs")
    assert not pl.opens_with_float_label("The data in Figure 4")


def test_the_flag_is_on_by_default(monkeypatch):
    monkeypatch.delenv("SCIENCE_CAPTION_READER", raising=False)
    assert pl.caption_reader_enabled()
    monkeypatch.setenv("SCIENCE_CAPTION_READER", "0")
    assert not pl.caption_reader_enabled()
