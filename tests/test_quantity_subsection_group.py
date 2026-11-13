"""A value inside one group's own subsection belongs to that group; synthetic, never NASA data."""

from test_document_extraction import entity, submitted, support, validate
from test_document_extraction import service as _service

from nasa_fire_ai.ingestion.document_extraction import Output

service = _service

TEXT = (
    "# Synthetic study\n"
    "II. Methods\n"
    "The facility was prepared for both series.\n"
    "A. Alpha test series\n"
    "The chamber was operated at a 1 pph demand.\n"
    "B. Beta test series\n"
    "The chamber was operated at a 3 pph demand.\n"
)


def quantity_record(service, sentence, expression, subject="study", text=TEXT):
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [
        entity(p, "study", "Synthetic study", "Investigation", "# Synthetic study"),
        entity(p, "alpha", "Alpha test series", "ExperimentFamily", "A. Alpha test series"),
        entity(p, "beta", "Beta test series", "ExperimentFamily", "B. Beta test series"),
    ]
    o["quantities"] = [
        {
            "subject": subject,
            "label": "demand",
            "expression": expression,
            "unit": "pph",
            "epistemic": "experimental_configuration",
            "support": support(p, sentence),
        }
    ]
    result = validate(service, p, o)
    (record,) = [r for r in result["records"] if r["kind"] == "quantities"]
    return record, result["entities_by_key"]


def test_a_value_inside_a_groups_subsection_goes_to_that_group(service):
    # Metamorphic: the same sentence form under each heading goes to that heading's group.
    for expression, group in (("1", "alpha"), ("3", "beta")):
        sentence = f"The chamber was operated at a {expression} pph demand."
        record, entities = quantity_record(service, sentence, expression)
        assert record["subject"] == entities[group]["id"]
        recovery = record["subject_recovery"]
        assert recovery["method"] == "VALUE_INSIDE_GROUP_OWN_SUBSECTION_REVALIDATED"
        assert recovery["proposed_subject"] == entities["study"]["id"]


def test_a_value_that_names_another_group_is_never_moved_to_this_one(service):
    text = TEXT.replace(
        "The chamber was operated at a 1 pph demand.",
        "Beta test series was operated at a 1 pph demand.",
    )
    record, entities = quantity_record(
        service, "Beta test series was operated at a 1 pph demand.", "1", text=text
    )
    assert record["subject"] != entities["alpha"]["id"]


def test_a_value_outside_every_group_subsection_is_not_given_a_group(service):
    text = TEXT.replace(
        "The facility was prepared for both series.",
        "The facility was operated at a 2 pph demand.",
    )
    record, entities = quantity_record(
        service, "The facility was operated at a 2 pph demand.", "2", text=text
    )
    assert record.get("subject") not in {entities["alpha"]["id"], entities["beta"]["id"]}
    assert (record.get("subject_recovery") or {}).get("method") != (
        "VALUE_INSIDE_GROUP_OWN_SUBSECTION_REVALIDATED"
    )
