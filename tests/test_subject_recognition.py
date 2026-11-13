"""A value's own sentence prints the subject the model proposed, in a form the plain label
match misses (package C, attribution recovery). Synthetic text unlike any source; the
rules only accept the proposed subject and never substitute one.
"""

import pytest
from test_document_extraction import entity, submitted, validate
from test_document_extraction import service as _service
from test_scientific_facets import quantity

from nasa_fire_ai.ingestion.document_extraction import Output

service = _service
STUDY = "Synthetic study"
HOLD = "QUANTITY_SUBJECT_NOT_IN_APPLICABLE_SOURCE"


def value_record(service, body, entities, value, subject):
    """Validate one value proposal for ``subject`` in ``body``; returns its record."""
    p = submitted(service, f"{STUDY}\nII. Results\n{body}\n")
    o = Output().model_dump()
    o["entities"] = [entity(p, key, label, cls, quote) for key, label, cls, quote in entities]
    quote, label, expression, unit, role = value
    o["quantities"] = [quantity(p, quote, subject, label, expression, unit, role)]
    records = validate(service, p, o)["records"]
    (record,) = [r for r in records if r["kind"] == "quantities"]
    return record


# A: a name split by the layout (a page number printed inside a hyphenated word).
TESTED = "The Kelvar-weave mat was tested in the drop rig."
SPLIT = (
    TESTED + " The ash content of the Kelvar-\n12\n"
    "weave mat was 4 % higher in ash content than the plain mat."
)
SPLIT_ENTITIES = [("mat", "Kelvar-weave mat", "Material", TESTED)]
SPLIT_VALUE = (
    "weave mat was 4 % higher in ash content than the plain mat.",
    "ash content",
    "4",
    "%",
    "reported_quantity",
)


def test_a_name_split_by_a_page_number_line_is_the_printed_subject(service):
    record = value_record(service, SPLIT, SPLIT_ENTITIES, SPLIT_VALUE, "mat")
    assert HOLD not in record["reasons"], record["reasons"]
    assert record["subject_recognition"] == "SUBJECT_NAME_SPLIT_BY_LAYOUT"


def test_a_heading_above_the_sentence_never_names_its_subject(service):
    # Metamorphic negative: the name printed only as a title line above a sentence
    # that does not name it.
    body = TESTED + "\nKelvar-weave mat\nThe ash content was 4 % higher than that of the plain mat."
    value = (
        "The ash content was 4 % higher than that of the plain mat.",
        "ash content",
        "4",
        "%",
        "reported_quantity",
    )
    record = value_record(service, body, SPLIT_ENTITIES, value, "mat")
    assert "subject_recognition" not in record


# A: a qualified name printed as its base name and its qualifier.
NAMES = "Resin-K (Lot #1) and Resin-K (Lot #2) were tested in the drop rig."
LOTS = "Charring of Resin-K was 9 % in lot 1 and 6 % in lot 2."
LOT_ENTITIES = [
    ("l1", "Resin-K (Lot #1)", "Sample", NAMES),
    ("l2", "Resin-K (Lot #2)", "Sample", NAMES),
]


@pytest.mark.parametrize(("expression", "subject"), [("9", "l1"), ("6", "l2")])
def test_a_qualified_name_is_recognized_by_the_qualifier_nearest_its_value(
    service, expression, subject
):
    value = (LOTS, "charring", expression, "%", "reported_quantity")
    record = value_record(service, NAMES + " " + LOTS, LOT_ENTITIES, value, subject)
    assert HOLD not in record["reasons"], record["reasons"]
    assert record["subject_recognition"] == "SUBJECT_PRINTED_AS_QUALIFIED_NAME"


def test_the_other_lots_value_is_not_this_lots(service):
    # Negative: 9 % is printed beside lot 1; proposed for lot 2 it stays held.
    value = (LOTS, "charring", "9", "%", "reported_quantity")
    record = value_record(service, NAMES + " " + LOTS, LOT_ENTITIES, value, "l2")
    assert HOLD in record["reasons"] and "subject_recognition" not in record


# A: a code-like short form of the name.
LOADED = "Vexal Q9 and Duran B were tested in the drop rig."
SHORT = LOADED + " The Q9 needed the load cut to 40 N to pass."
SHORT_ENTITIES = [
    ("q9", "Vexal Q9", "Sample", LOADED),
    ("db", "Duran B", "Sample", LOADED),
]
SHORT_VALUE = (
    "The Q9 needed the load cut to 40 N to pass.",
    "load",
    "40",
    "N",
    "reported_quantity",
)


def test_a_code_like_short_form_names_its_entity(service):
    record = value_record(service, SHORT, SHORT_ENTITIES, SHORT_VALUE, "q9")
    assert HOLD not in record["reasons"], record["reasons"]
    assert record["subject_recognition"] == "SUBJECT_PRINTED_AS_SHORT_FORM"


def test_a_short_form_two_entities_share_is_not_recognized(service):
    loaded = "Vexal Q9 and Q9 binder were tested in the drop rig."
    entities = [
        ("q9", "Vexal Q9", "Sample", loaded),
        ("qb", "Q9 binder", "Sample", loaded),
    ]
    body = loaded + " The Q9 needed the load cut to 40 N to pass."
    record = value_record(service, body, entities, SHORT_VALUE, "q9")
    assert HOLD in record["reasons"] and "subject_recognition" not in record


def test_a_short_form_never_moves_the_value_to_another_subject(service):
    # The model proposed the other material: the printed "Q9" does not justify it,
    # and nothing replaces the proposal.
    record = value_record(service, SHORT, SHORT_ENTITIES, SHORT_VALUE, "db")
    assert HOLD in record["reasons"]
    assert record["proposal"]["subject"] == "db"


# B: a pronoun that opens the value's sentence names the one subject of the sentence
# before it, in the same subsection.
CONE = "The Kordel foam was tested in the cone rig."
CONE_VALUE = (
    "It was exposed to a heat flux of 35 kW/m2 for 300 s.",
    "heat flux",
    "35",
    "kW/m2",
    "experimental_configuration",
)


def test_a_pronoun_names_the_one_subject_of_the_sentence_before(service):
    body = CONE + " It was exposed to a heat flux of 35 kW/m2 for 300 s."
    record = value_record(service, body, [("kf", "Kordel foam", "Sample", CONE)], CONE_VALUE, "kf")
    assert HOLD not in record["reasons"], record["reasons"]
    assert record["subject_antecedent"]["basis"] == "PRONOUN_SUBJECT_OF_PRECEDING_SENTENCE"


def test_a_pronoun_after_two_candidates_names_neither(service):
    both = "The Kordel foam and the Lira felt were tested in the cone rig."
    body = both + " It was exposed to a heat flux of 35 kW/m2 for 300 s."
    entities = [("kf", "Kordel foam", "Sample", both), ("lf", "Lira felt", "Sample", both)]
    record = value_record(service, body, entities, CONE_VALUE, "kf")
    assert HOLD in record["reasons"] and "subject_antecedent" not in record


def test_a_pronoun_never_reaches_across_a_subsection_heading(service):
    body = CONE + "\n## Second rig trials\nIt was exposed to a heat flux of 35 kW/m2 for 300 s."
    record = value_record(service, body, [("kf", "Kordel foam", "Sample", CONE)], CONE_VALUE, "kf")
    assert HOLD in record["reasons"] and "subject_antecedent" not in record


def test_a_pronoun_never_moves_the_value_to_the_antecedent(service):
    # The model proposed another specimen: the antecedent does not replace it.
    body = (
        "The Lira felt was set aside. "
        + CONE
        + " It was exposed to a heat flux of 35 kW/m2 for 300 s."
    )
    entities = [
        ("kf", "Kordel foam", "Sample", CONE),
        ("lf", "Lira felt", "Sample", "The Lira felt was set aside."),
    ]
    record = value_record(service, body, entities, CONE_VALUE, "lf")
    assert HOLD in record["reasons"] and record["proposal"]["subject"] == "lf"


def test_a_recovered_attribution_never_displaces_a_direct_one_as_canonical():
    # Two acceptances of one printed value for one subject: one named by its table
    # column, one through a pronoun. The direct one stays canonical, whatever the ids.
    from nasa_fire_ai.ingestion.scientific_scope import consolidate_validated_variants

    def value(rid, **extra):
        return {
            "id": rid,
            "kind": "quantities",
            "status": "SOURCE_SUPPORTED",
            "reasons": [],
            "subject": "mat",
            "proposal": {
                "subject": "m",
                "label": "pressure",
                "expression": "7,000",
                "unit": "kPa",
                "epistemic": "experimental_configuration",
            },
            "quantity_value_spans": [{"evidence_id": "E-1", "start": 40, "end": 49}],
            "support_spans": [{"evidence_id": "E-1", "start": 0, "end": 60}],
            **extra,
        }

    recovered = value(
        "proposal-aaaa", subject_antecedent={"basis": "PRONOUN_SUBJECT_OF_PRECEDING_SENTENCE"}
    )
    direct = value("proposal-zzzz")
    for records in ([recovered, direct], [direct, recovered]):
        fresh = [dict(r) for r in records]
        consolidate_validated_variants(fresh, {}, {}, {})
        by_id = {r["id"]: r for r in fresh}
        assert not by_id["proposal-zzzz"].get("duplicate_of")
        assert by_id["proposal-aaaa"]["duplicate_of"] == "proposal-zzzz"


def test_a_value_recovered_at_the_applicability_check_never_displaces_one_that_passed_it():
    # Both acceptances read the subject from a pronoun's antecedent, but only one
    # needed that recovery to pass the applicability check.
    from nasa_fire_ai.ingestion.scientific_scope import consolidate_validated_variants

    antecedent = {"basis": "PRONOUN_SUBJECT_OF_PRECEDING_SENTENCE"}

    def value(rid, **extra):
        return {
            "id": rid,
            "kind": "quantities",
            "status": "SOURCE_SUPPORTED",
            "reasons": [],
            "subject": "mat",
            "subject_antecedent": antecedent,
            "proposal": {
                "subject": "m",
                "label": "pressure",
                "expression": "7,000",
                "unit": "kPa",
                "epistemic": "experimental_configuration",
            },
            "quantity_value_spans": [{"evidence_id": "E-1", "start": 40, "end": 49}],
            "support_spans": [{"evidence_id": "E-1", "start": 0, "end": 60}],
            **extra,
        }

    late = value("proposal-aaaa", subject_applicability="RECOVERED")
    passed = value("proposal-zzzz")
    for records in ([late, passed], [passed, late]):
        fresh = [dict(r) for r in records]
        consolidate_validated_variants(fresh, {}, {}, {})
        by_id = {r["id"]: r for r in fresh}
        assert not by_id["proposal-zzzz"].get("duplicate_of")
        assert by_id["proposal-aaaa"]["duplicate_of"] == "proposal-zzzz"
