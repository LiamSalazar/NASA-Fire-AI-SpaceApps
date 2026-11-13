"""Synthetic numeric-syntax cases, not NASA measurements or expert gold.

Literal expressions mirror families rejected or mis-split in exposed Phase 1 v4
receipts (grouped thousands, reaction/test ratios, units copied into the value,
Unicode minus signs). No production module contains these strings.
"""

import re
import shutil
from pathlib import Path

import pytest

from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.document_extraction import Output, validate_output
from nasa_fire_ai.ingestion.document_structure import structure
from nasa_fire_ai.ingestion.numeric_expressions import (
    comparison_key,
    decimal_convention,
    legacy_quantity_pattern,
    parse_numeric_expression,
    source_numeric_matches,
    split_embedded_unit,
)
from nasa_fire_ai.services.curation import CurationService

ROOT = Path(__file__).resolve().parents[1]


def values(expression, **options):
    parsed = parse_numeric_expression(expression, **options)
    return [e["value_candidates"] for e in parsed["endpoints"]]


# --- Syntax: what the expression literally says -------------------------------------


@pytest.mark.parametrize(
    "expression,form,candidates",
    [
        ("1,250,000", "SCALAR", [["1250000"]]),
        ("1,250.5", "SCALAR", [["1250.5"]]),
        (".92", "SCALAR", [["0.92"]]),
        ("−40", "SCALAR", [["-40"]]),
        ("1.5e-3", "SCALAR", [["0.0015"]]),
        ("1.5 × 10^-3", "SCALAR", [["0.0015"]]),
        ("1.5×10⁻³", "SCALAR", [["0.0015"]]),
        ("0 to ~.6", "RANGE", [["0"], ["0.6"]]),
        ("between 5 and 10", "BETWEEN", [["5"], ["10"]]),
        ("3.2 ± 0.1", "PLUS_MINUS", [["3.2"], ["0.1"]]),
    ],
)
def test_expression_families_parse_to_exact_decimal_strings(expression, form, candidates):
    parsed = parse_numeric_expression(expression)
    assert parsed["status"] == "PARSED"
    assert parsed["form"] == form
    assert values(expression) == candidates
    assert parsed["scientific_role"] == "NOT_DETERMINED_BY_SYNTAX"


def test_comma_and_point_are_not_interchangeable_without_document_convention():
    grouped, decimal = parse_numeric_expression("1,250"), parse_numeric_expression("1.250")
    assert grouped["status"] == "AMBIGUOUS"
    assert grouped["endpoints"][0]["value_candidates"] == ["1250", "1.250"]
    assert "DIGIT_GROUPING_OR_DECIMAL_COMMA_UNRESOLVED" in grouped["ambiguities"]
    assert decimal["status"] == "PARSED"
    assert decimal["endpoints"][0]["value_candidates"] == ["1.250"]
    assert values("1,250", convention="POINT") == [["1250"]]
    assert values("1,250", convention="COMMA") == [["1.250"]]
    assert values("1.250", convention="COMMA") == [["1250"]]
    assert parse_numeric_expression("1,25")["status"] == "AMBIGUOUS"
    assert parse_numeric_expression("1,25", convention="COMMA")["status"] == "PARSED"
    contradicted = parse_numeric_expression("1,250.5", convention="COMMA")
    assert contradicted["status"] == "AMBIGUOUS"
    assert contradicted["endpoints"][0]["value_candidates"] == []


def test_inequality_and_approximation_are_preserved_not_dropped():
    bounded = parse_numeric_expression(">25")
    plain = parse_numeric_expression("25")
    assert bounded["endpoints"][0]["qualifier"]["operator"] == ">"
    assert plain["endpoints"][0]["qualifier"] is None
    assert parse_numeric_expression("at least 25")["endpoints"][0]["qualifier"]["operator"] == ">="
    assert parse_numeric_expression("≤ 25")["endpoints"][0]["qualifier"]["operator"] == "<="
    approximate = parse_numeric_expression("~3.95")["endpoints"][0]["qualifier"]
    assert approximate["approximate"] and approximate["operator"] is None
    word = parse_numeric_expression("Approximately 5")["endpoints"][0]["qualifier"]
    assert word["approximate"]
    upper = parse_numeric_expression("0 to ~.6")["endpoints"]
    assert upper[0]["qualifier"] is None and upper[1]["qualifier"]["approximate"]


def test_ratio_is_kept_as_written_and_never_divided():
    for expression, basis in (("0/20", "SLASH"), ("2 of 4", "OF")):
        parsed = parse_numeric_expression(expression)
        assert parsed["form"] == "RATIO"
        assert parsed["ratio_basis"] == basis
        assert parsed["scalar_value_asserted"] is False
        assert [e["role"] for e in parsed["endpoints"]] == ["numerator", "denominator"]
        assert "0.1" not in str(parsed) and "0.5" not in str(parsed)


def test_from_to_pair_is_ordered_but_its_meaning_is_left_to_semantics():
    parsed = parse_numeric_expression("from 20% to 14.3")
    assert parsed["form"] == "FROM_TO"
    assert parsed["ordered_pair_meaning"] == "INTERVAL_OR_CHANGE_NOT_DETERMINED_BY_SYNTAX"
    assert parsed["endpoints"][0]["unit_literal"] == "%"


def test_flattened_exponent_and_dash_sign_need_confirmation():
    flattened = parse_numeric_expression("1.5 x 10-3")
    assert flattened["status"] == "AMBIGUOUS"
    assert flattened["ambiguities"] == ["FLATTENED_EXPONENT_UNCONFIRMED"]
    cell = parse_numeric_expression("–40", table_cell=True)
    assert cell["status"] == "AMBIGUOUS"
    assert cell["ambiguities"] == ["DASH_GLYPH_SIGN_UNCONFIRMED"]
    assert parse_numeric_expression("–40")["status"] == "NOT_NUMERIC"


def test_superscript_exponent_flattened_by_pdf_text_is_kept_but_unconfirmed():
    from decimal import Decimal

    parsed = parse_numeric_expression("1350 ×103")
    assert parsed["status"] == "AMBIGUOUS"
    assert parsed["ambiguities"] == ["FLATTENED_EXPONENT_UNCONFIRMED"]
    assert [Decimal(v) for v in values("1350 ×103")[0]] == [Decimal(1350000)]
    # "x" is a dimension separator, and 10 followed by 0 is a literal number.
    assert parse_numeric_expression("5 x 103")["status"] == "NOT_NUMERIC"
    assert parse_numeric_expression("5 ×100")["status"] == "NOT_NUMERIC"
    assert [m.group() for m in source_numeric_matches("ΔHc = 1350 ×103 J/kg")] == ["1350 ×103"]


def test_bound_and_order_of_magnitude_words_keep_their_literal_qualifier():
    high = parse_numeric_expression("as high as ~700")["endpoints"][0]["qualifier"]
    assert high["operator"] == "<=" and high["approximate"]
    assert high["literal"] == "as high as ~"
    low = parse_numeric_expression("as low as -50")["endpoints"][0]["qualifier"]
    assert low["operator"] == ">="
    order = parse_numeric_expression("on the order of 150")["endpoints"][0]["qualifier"]
    assert order["approximate"] and order["literal"] == "on the order of"
    assert parse_numeric_expression("approximately a")["status"] == "NOT_NUMERIC"


def test_separate_values_printed_together_are_a_list_never_one_quantity():
    listed = parse_numeric_expression("~.9 and 4.3")
    assert (listed["status"], listed["form"]) == ("AMBIGUOUS", "LIST")
    assert "MULTIPLE_VALUES_IN_ONE_EXPRESSION" in listed["ambiguities"]
    assert [e["value_candidates"] for e in listed["endpoints"]] == [["0.9"], ["4.3"]]
    assert listed["endpoints"][0]["qualifier"]["approximate"]
    assert len(parse_numeric_expression("3, 4 and 5")["endpoints"]) == 3
    # Digit grouping and two-sided forms are not lists.
    assert parse_numeric_expression("1,500")["form"] == "SCALAR"
    assert parse_numeric_expression("between 2 and 3")["form"] == "BETWEEN"
    assert parse_numeric_expression("Alpha and Beta")["status"] == "NOT_NUMERIC"


def test_stored_values_never_turn_bounds_or_unresolved_grouping_into_exact_numbers():
    from nasa_fire_ai.services.curation import CurationService

    def stored(raw):
        value = CurationService.parse_value(raw, "kPa", None)
        assert value["raw_expression"] == raw
        return value["reported_value"], value["lower"], value["upper"], value["approximate"]

    assert stored("−40") == (-40.0, None, None, False)
    assert stored("about 25") == (25.0, None, None, True)
    assert stored("2 – 3") == (None, 2.0, 3.0, False)
    # Kept literally: a bound, a ratio, an uncertainty, unresolved grouping, a list.
    for raw in (">425", "< 5", "2/20", "1.5 ± 0.2", "1,500", "~.9 and 4.3"):
        assert stored(raw) == (raw, None, None, False)


def test_footnote_symbols_are_annotations_not_digits():
    parsed = parse_numeric_expression("12.5†")
    assert parsed["footnote_markers"] == ["†"]
    assert values("12.5†") == [["12.5"]]
    # A trailing letter may be a specimen identifier, so it is not stripped.
    assert parse_numeric_expression("12a")["status"] == "NOT_NUMERIC"


@pytest.mark.parametrize(
    "expression",
    [
        "over a minute",
        "drops",
        "normal pressure",
        "1-g",
        "4-mm",
        "~constant",
        "11 RPM with effective radius 1.22 m",
        "to 15.8%",
        "25e",
        "",
    ],
)
def test_non_numeric_model_output_stays_rejected(expression):
    assert parse_numeric_expression(expression)["status"] == "NOT_NUMERIC"


# --- Metamorphic: equivalent writings agree, different meanings differ --------------


@pytest.mark.parametrize(
    "a,b",
    [
        ("~ 3.95", "~3.95"),
        ("−40", "-40"),
        ("1.5e-3", "1.5 × 10^-3"),
        ("1.5E-3", "1.5×10⁻³"),
        ("5–10", "5 to 10"),
    ],
)
def test_equivalent_writings_have_equal_values(a, b):
    assert values(a) == values(b)


@pytest.mark.parametrize(
    "a,b",
    [
        (">25", "25"),
        ("~3.95", "3.95"),
        ("2/4", "0.5"),
        ("-40", "40"),
        ("1,250", "1.250"),
    ],
)
def test_scientifically_different_writings_stay_distinguishable(a, b):
    pa, pb = parse_numeric_expression(a), parse_numeric_expression(b)
    assert (pa["form"], values(a), pa["status"], str(pa["endpoints"][0].get("qualifier"))) != (
        pb["form"],
        values(b),
        pb["status"],
        str(pb["endpoints"][0].get("qualifier")),
    )


def test_every_expression_of_the_earlier_grammar_remains_numeric():
    for expression in [
        "20",
        "-3.5",
        "1e-3",
        "~ 20",
        "<20",
        "about 4",
        "greater than 7",
        "5-10",
        "5 to 10",
        "3 ± 1",
        "two and a half",
        "over 30",
    ]:
        assert re.fullmatch(legacy_quantity_pattern(), expression)
        assert parse_numeric_expression(expression)["status"] != "NOT_NUMERIC", expression


def test_comparison_key_unifies_only_glyph_variants():
    assert comparison_key("−40") == comparison_key("-40")
    assert comparison_key("∼5") == comparison_key("~5")
    assert comparison_key("1E-3") != comparison_key("1e-3")
    assert comparison_key("~ 5") != comparison_key("~5")


def test_document_decimal_convention_requires_dominant_evidence():
    assert decimal_convention("Rates were 3.95 mm/s and 0.5 cm at 10,000 psia.") == "POINT"
    assert decimal_convention("Velocidades de 3,95 mm/s y 0,5 cm.") == "COMMA"
    assert decimal_convention("Run 1,250 only") is None
    assert decimal_convention("3.95 and 0.5 but 3,95 and 0,5") is None


# --- Units copied into the expression ------------------------------------------------


@pytest.mark.parametrize(
    "expression,unit,value,split_unit",
    [
        ("~ 3.95 mm/s", "mm/s", "~ 3.95", "mm/s"),
        ("11 RPM", None, "11", "RPM"),
        ("20uL", None, "20", "uL"),
        ("~45 seconds", "seconds", "~45", "seconds"),
        ("4-mm", "mm", "4", "mm"),
        ("0 to ~.6 mm/s", "mm/s", "0 to ~.6", "mm/s"),
        (".92 mm/s", "mm/s", ".92", "mm/s"),
    ],
)
def test_embedded_original_unit_is_separated(expression, unit, value, split_unit):
    split = split_embedded_unit(expression, unit)
    assert split["status"] == "SPLIT"
    assert (split["expression"], split["unit"]) == (value, split_unit)


def test_author_equivalent_is_kept_but_not_used_as_a_conversion():
    split = split_embedded_unit("50 ft-lbs (68J)", "ft-lbs (68J)")
    assert (split["expression"], split["unit"]) == ("50", "ft-lbs")
    assert split["author_equivalent"]["original"] == "(68J)"
    assert split["author_equivalent"]["basis"] == "AUTHOR_STATED_EQUIVALENT_NOT_SYSTEM_CONVERSION"


def test_unit_split_refuses_ambiguous_or_contradicted_units():
    assert split_embedded_unit("1-g", None) is None
    assert split_embedded_unit("over two and a half minutes", "time") is None
    assert split_embedded_unit("11 RPM with effective radius 1.22 m", "m/s") is None
    mismatch = split_embedded_unit("from 20% to 14.3%", "fraction")
    assert mismatch["status"] == "UNIT_MISMATCH"


@pytest.mark.parametrize(
    "expression,unit,value",
    [
        ("299 l", "l", "299"),
        ("299l", "l", "299"),
        ("2 ml", "ml", "2"),
        ("50 ft3", "ft3", "50"),
        ("50 ft^3", "ft^3", "50"),
        ("12 ft²", "ft²", "12"),
    ],
)
def test_volume_and_area_units_the_unit_inventory_interprets_are_separated(expression, unit, value):
    # The grammar recognizes the litre and the cubic or square foot that
    # normalization.units interprets; spacing does not change the reading.
    split = split_embedded_unit(expression, unit)
    assert (split["status"], split["expression"], split["unit"]) == ("SPLIT", value, unit)


def test_a_compound_volume_keeps_its_author_equivalent():
    split = split_embedded_unit("1.4 m3 (50 ft3)", "m3")
    assert (split["expression"], split["unit"]) == ("1.4", "m3")
    assert split["author_equivalent"]["original"] == "(50 ft3)"


def test_the_lowercase_litre_needs_a_declared_unit_and_keeps_its_case():
    # "l" is a letter as often as a unit: it is never split without a declared
    # unit, and case is significant against a declared "L".
    assert split_embedded_unit("299 l", None) is None
    assert split_embedded_unit("299 l", "L")["status"] == "UNIT_MISMATCH"
    # Longer literals that begin with the letter are not read as litres.
    assert split_embedded_unit("5 lbs", "lbs")["unit"] == "lbs"
    assert split_embedded_unit("3 lm", "lm")["unit"] == "lm"
    assert split_embedded_unit("12 ft", "ft")["unit"] == "ft"


# --- Locating expressions in source text ---------------------------------------------


def located(text):
    return [m.group() for m in source_numeric_matches(text)]


def test_grouped_numbers_signs_and_exponents_are_never_split():
    assert located("tested at 10,000 psia and 5,000 psia") == ["10,000", "5,000"]
    assert located("temperature of −40 °C") == ["−40"]
    assert located("rate 1.5 × 10^-3 m/s") == ["1.5 × 10^-3"]
    assert located("reactions 2/20 and 0/20") == ["2/20", "0/20"]
    assert located("The value was 25.") == ["25"]


def test_dash_glyph_sign_is_not_silently_dropped():
    assert located("held at –40 °C") == []


def test_endpoints_of_ordered_pairs_remain_locatable():
    assert located("O2 fell from 20% to 14.3%.") == ["from 20% to 14.3", "20", "14.3"]


# --- Integration through the production validator ------------------------------------


@pytest.fixture
def service(tmp_path):
    for name in ("domain", "ontology", "data/canonical"):
        shutil.copytree(ROOT / name, tmp_path / name)
    registry = EvidenceRegistry(tmp_path / "data/index/evidence.sqlite")
    yield CurationService(tmp_path, registry)
    registry.db.close()


def submitted(service, text):
    return service.submit(
        "Synthetic study", "Labeled synthetic test", [("source.md", text.encode())], "tester"
    )["package"]


def support(package, quote):
    return [{"evidence_id": package["evidence"][0]["evidence_id"], "quote": quote}]


def quantity_record(service, text, expression, unit, label="pressure"):
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [
        {
            "key": "a1",
            "label": "A1",
            "class_id": "ExperimentalRun",
            "study": "current",
            "support": support(p, text),
        }
    ]
    o["quantities"] = [
        {
            "subject": "a1",
            "label": label,
            "expression": expression,
            "unit": unit,
            "epistemic": "experimental_configuration",
            "support": support(p, text),
        }
    ]
    records = validate_output(o, p, structure(p, service.root), service.semantic)["records"]
    return next(r for r in records if r["kind"] == "quantities")


POINT_CONTEXT = "Specimens were 0.25 cm thick and 1.27 cm wide. "


def test_grouped_thousands_are_accepted_when_the_document_uses_decimal_points(service):
    record = quantity_record(
        service, POINT_CONTEXT + "Run A1 was tested at pressure 10,000 psia.", "10,000", "psia"
    )
    assert record["status"] != "REJECTED", record["reasons"]
    assert record["numeric_expression"]["status"] == "PARSED"
    assert record["numeric_expression"]["endpoints"][0]["value_candidates"] == ["10000"]


def test_grouped_thousands_stay_unresolved_without_document_convention(service):
    record = quantity_record(
        service, "Run A1 was tested at pressure 10,000 psia.", "10,000", "psia"
    )
    assert record["status"] == "UNRESOLVED"
    assert "NUMERIC_EXPRESSION_AMBIGUOUS" in record["reasons"]


def test_fragment_of_a_grouped_number_is_not_a_source_value(service):
    record = quantity_record(
        service, POINT_CONTEXT + "Run A1 was tested at pressure 10,000 psia.", "000", "psia"
    )
    assert record["status"] == "REJECTED"
    assert "QUANTITY_EXPRESSION_ABSENT" in record["reasons"]


def test_unicode_minus_sign_cannot_be_dropped(service):
    text = POINT_CONTEXT + "Run A1 was tested at pressure −40 psia."
    assert quantity_record(service, text, "40", "psia")["status"] == "REJECTED"
    signed = quantity_record(service, text, "-40", "psia")
    assert signed["status"] != "REJECTED", signed["reasons"]
    assert signed["numeric_expression"]["endpoints"][0]["value_candidates"] == ["-40"]
    # The proposal carries the original writing, not the model's glyph variant.
    assert signed["proposal"]["expression"] == "−40"
    assert signed["expression_normalization"]["model_expression"] == "-40"


def test_unit_copied_into_expression_is_recovered_and_recorded(service):
    text = POINT_CONTEXT + "Run A1 was tested at pressure ~ 3.95 psia."
    record = quantity_record(service, text, "~ 3.95 psia", "psia")
    assert "QUANTITY_NOT_ORIGINAL_NUMERIC_EXPRESSION" not in record["reasons"]
    assert record["status"] != "REJECTED", record["reasons"]
    assert record["proposal"]["expression"] == "~ 3.95"
    assert record["expression_normalization"]["original_expression"] == "~ 3.95 psia"
    contradicted = quantity_record(service, text, "~ 3.95 psia", "fraction")
    assert "QUANTITY_UNIT_NOT_BOUND_TO_EXPRESSION" in contradicted["reasons"]


def test_value_label_with_embedded_unit_is_not_a_quantity_name(service):
    text = "Run A1 was tested at 11 RPM."
    record = quantity_record(service, text, "11 RPM", None, label="11 RPM")
    assert record["status"] == "REJECTED"
    assert "QUANTITY_VALUE_OR_UNIT_IS_NOT_A_QUANTITY_NAME" in record["reasons"]


def test_ratio_is_retained_without_becoming_a_scalar(service):
    text = "Run A1 was tested with reactions 2/20."
    record = quantity_record(service, text, "2/20", None, label="reactions")
    assert record["status"] != "REJECTED", record["reasons"]
    assert record["numeric_expression"]["form"] == "RATIO"
    assert "QUANTITY_UNIT_UNSPECIFIED" not in record["reasons"]
    assert record["native_value_compatible"] is False
    denominator = quantity_record(service, text, "20", None, label="reactions")
    assert denominator["status"] == "REJECTED"


def test_pdf_table_cells_keep_grouped_values_and_ratios(service):
    import pymupdf

    from nasa_fire_ai.ingestion.pdf_quantities import pdf_table_quantities

    with pymupdf.open() as pdf:
        pdf.new_page().insert_text((50, 50), "Synthetic table\nRates 0.25 and 1.27 mm/s")
        data = pdf.tobytes()
    p = service.submit("Synthetic table", "Synthetic table test", [("t.pdf", data)], "tester")[
        "package"
    ]
    d = structure(p, service.root)
    d["detected_tables"] = [
        {
            "input_sha256": p["inputs"][0]["sha256"],
            "physical_pdf_page": 1,
            "bbox": [50, 50, 250, 150],
            "cells": [["Pressure (psia)", "Reactions/Tests"], ["10,000", "2/20"]],
            "header": ["Pressure (psia)", "Reactions/Tests"],
            "header_external": False,
        }
    ]
    candidates = pdf_table_quantities(p, d)
    assert [r["proposal"]["expression"] for r in candidates] == ["10,000", "2/20"]
    assert [r["proposal"]["numeric_expression"]["form"] for r in candidates] == [
        "SCALAR",
        "RATIO",
    ]
    assert all(
        r["status"] == "UNRESOLVED" and not r["scientific_execution_asserted"] for r in candidates
    )


def header_document(header, value, page=1):
    return {
        "detected_tables": [
            {
                "input_sha256": "synthetic",
                "physical_pdf_page": page,
                "bbox": [0, 0, 1, 1],
                "cells": [["Material", header], ["Sample A", value]],
                "header": ["Material", header],
                "header_external": False,
            }
        ]
    }


def test_table_value_inherits_only_its_own_column_header_unit():
    from nasa_fire_ai.ingestion.pdf_quantities import header_unit_binding

    spans = [{"page": 1}]
    document = header_document("System\nPressure (psia)", "10,000")
    binding = header_unit_binding("10,000", "psia", spans, document)
    assert binding["basis"] == "ORIGINAL_TABLE_COLUMN_HEADER_UNIT"
    assert (binding["page"], binding["column_index"], binding["conversion"]) == (1, 1, "NONE")
    # Another unit, another case, another page or another value never binds.
    assert header_unit_binding("10,000", "inches", spans, document) is None
    assert header_unit_binding("10,000", "PSIA", spans, document) is None
    assert header_unit_binding("10,000", "psia", [{"page": 2}], document) is None
    assert header_unit_binding("5,000", "psia", spans, document) is None
    # A header without a literal unit gives the cell no unit.
    assert (
        header_unit_binding("10,000", "psia", spans, header_document("Pressure", "10,000")) is None
    )
