"""A statement held for its subject is accepted when the one heading governing it names the
proposed subject (by label or by the short form its label defines), and nothing else
competes; never a substitute, never the investigation. Synthetic text."""

from test_document_extraction import entity, submitted, support, validate
from test_document_extraction import service as _service

from nasa_fire_ai.ingestion.document_extraction import Output

service = _service
TEXT = (
    "Synthetic Valve Study\n"
    "II. Test Article\nThe Main Feed Valve (MFV) 4.1, unit 17 was tested at 20 MPa.\n"
    "III. MFV 4.1 Post Test Inspection\n"
    "The seat had no visible soot under magnification.\n"
    "The spare housing seat had soot.\n"
)


def statement_record(service, text, subjects, extra=()):
    p = submitted(service, TEXT)
    o = Output().model_dump()
    o["entities"] = (
        [
            entity(
                p,
                "mfv",
                "Main Feed Valve (MFV) 4.1, unit 17",
                "Sample",
                "Main Feed Valve (MFV) 4.1, unit 17",
            ),
            *extra(p),
        ]
        if extra
        else [
            entity(
                p,
                "mfv",
                "Main Feed Valve (MFV) 4.1, unit 17",
                "Sample",
                "Main Feed Valve (MFV) 4.1, unit 17",
            )
        ]
    )
    o["statements"] = [
        {
            "subjects": subjects,
            "text": text,
            "class_id": "ReportedObservation",
            "epistemic": "measured_observation",
            "study": "current",
            "support": support(p, text),
        }
    ]
    (record,) = [r for r in validate(service, p, o)["records"] if r["kind"] == "statements"]
    return record


def test_the_heading_names_the_proposed_subject_by_its_short_form(service):
    record = statement_record(service, "The seat had no visible soot under magnification.", ["mfv"])
    assert "STATEMENT_SUBJECT_APPLICABILITY_UNRESOLVED" not in record["reasons"]
    assert record["scope_context"]["basis"] == "GOVERNING_HEADING_NAMES_PROPOSED_SUBJECT"


def test_another_entity_named_in_the_passage_keeps_the_hold(service):
    record = statement_record(
        service,
        "The spare housing seat had soot.",
        ["mfv"],
        extra=lambda p: [
            entity(p, "sh", "spare housing", "Sample", "The spare housing seat had soot.")
        ],
    )
    assert "STATEMENT_SUBJECT_APPLICABILITY_UNRESOLVED" in record["reasons"]
