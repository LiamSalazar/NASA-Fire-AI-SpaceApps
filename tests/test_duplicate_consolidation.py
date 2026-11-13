"""One assertion per printed value and per printed name; synthetic text, never NASA data."""

from test_document_extraction import entity, submitted, support, validate
from test_document_extraction import service as _service

from nasa_fire_ai.ingestion.document_extraction import Output

service = _service

TEXT = (
    "II. Methods\nThe Alpha drum is the sample. The Alpha drum impact energy was 98 Joules. "
    "The Alpha drum impact energy was then 98 Joules again.\n"
    "III. Discussion\nMany spacecraft materials (Nomex) char.\n"
    "References\n[1] Nomex char tests, 1990.\n"
)
FIRST = "The Alpha drum impact energy was 98 Joules."
SECOND = "The Alpha drum impact energy was then 98 Joules again."


def active(records, kind):
    return [
        r
        for r in records
        if r["kind"] == kind and r["status"] != "REJECTED" and not r.get("duplicate_of")
    ]


def quantities(service, supports):
    p = submitted(service, TEXT)
    o = Output().model_dump()
    o["entities"] = [entity(p, "d", "Alpha drum", "Sample", "The Alpha drum is the sample.")]
    o["quantities"] = [
        {
            "subject": "d",
            "label": "impact energy",
            "expression": "98",
            "unit": "Joules",
            "epistemic": "experimental_configuration",
            "support": [s for quote in quotes for s in support(p, quote)],
        }
        for quotes in supports
    ]
    return active(validate(service, p, o)["records"], "quantities")


def test_two_proposals_sharing_one_printed_value_are_one_quantity(service):
    assert len(quantities(service, [[FIRST, SECOND], [FIRST]])) == 1


def test_the_same_value_printed_in_two_places_without_overlap_stays_two(service):
    # Metamorphic negative: no printed value is shared.
    assert len(quantities(service, [[FIRST], [SECOND]])) == 2


def nomex(service, quotes):
    p = submitted(service, TEXT)
    o = Output().model_dump()
    o["entities"] = [
        entity(p, f"n{i}", "Nomex", "Material", quote, study=study)
        for i, (quote, study) in enumerate(quotes)
    ]
    return [r for r in validate(service, p, o)["records"] if r["kind"] == "entities"]


def test_one_printed_name_read_as_current_and_cited_is_one_open_entity(service):
    records = nomex(
        service,
        [
            ("Many spacecraft materials (Nomex) char.", "current"),
            ("Many spacecraft materials (Nomex) char.", "cited"),
        ],
    )
    (owner,) = active(records, "entities")
    assert owner["status"] == "UNRESOLVED"
    assert "CURRENT_OR_CITED_STUDY_CONFLICT_FOR_SAME_SOURCE_SPAN" in owner["reasons"]


def test_a_cited_and_a_current_name_printed_in_different_places_stay_two(service):
    records = nomex(
        service,
        [
            ("Many spacecraft materials (Nomex) char.", "current"),
            ("[1] Nomex char tests, 1990.", "cited"),
        ],
    )
    assert not any("CURRENT_OR_CITED_STUDY_CONFLICT" in str(r["reasons"]) for r in records)
