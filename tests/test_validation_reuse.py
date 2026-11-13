"""An unchanged output is validated once; synthetic text, never NASA data."""

from test_document_extraction import entity, submitted, support
from test_document_extraction import service as _service

from nasa_fire_ai.ingestion import document_extraction, extraction_validation
from nasa_fire_ai.ingestion.document_extraction import Output, extraction_semantic, structure

service = _service


def setup(service):
    p = submitted(service, "II. Methods\nRun A1 was tested in microgravity.\n")
    o = Output().model_dump()
    o["entities"] = [entity(p, "a1", "A1", "ExperimentalRun", "Run A1 was tested")]
    o["statements"] = [
        {
            "text": "Run A1 was tested in microgravity.",
            "class_id": "ExperimentalCondition",
            "epistemic": "experimental_configuration",
            "subjects": ["a1"],
            "study": "current",
            "support": support(p, "Run A1 was tested in microgravity."),
        }
    ]
    return p, o, structure(p, service.root), extraction_semantic(service, p)


def test_an_unchanged_output_is_validated_once_and_each_caller_gets_its_copy(service, monkeypatch):
    p, o, d, semantic = setup(service)
    calls = []
    # validate_output reads validated_output from the globals of extraction_validation,
    # so the patch is made there (document_extraction.validate_output is the same function).
    original = extraction_validation.validated_output
    monkeypatch.setattr(
        extraction_validation,
        "validated_output",
        lambda *a, **k: calls.append(1) or original(*a, **k),
    )
    first = document_extraction.validate_output(o, p, d, semantic)
    first["records"].clear()  # a caller changing its copy changes nothing cached
    second = document_extraction.validate_output(o, p, d, semantic)
    assert len(calls) == 1 and second["records"]
    # Metamorphic: a changed output is validated again and matches a fresh validation.
    o["statements"][0]["epistemic"] = "measured_observation"
    third = document_extraction.validate_output(o, p, d, semantic)
    assert len(calls) == 2 and third == original(o, p, d, semantic)
