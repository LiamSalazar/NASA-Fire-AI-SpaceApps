"""A supported group the passage is not shown to belong to scopes it to the study, never a run;
synthetic text, never NASA data."""

from test_document_extraction import entity, submitted, support, validate
from test_document_extraction import service as _service

from nasa_fire_ai.config import Settings
from nasa_fire_ai.ingestion.document_extraction import ExtractionBudget, Output

service = _service

TEXT = (
    "# Synthetic study\n# Results\nThe Alpha series used a flow duct.\n"
    "The flame extinguished after the flow stopped.\nRun A1 was tested."
)
SENTENCE = "The flame extinguished after the flow stopped."


def observation(service, subject_entity):
    p = submitted(service, TEXT)
    prepared = service.prepare_scientific(
        p["id"],
        Settings(root=service.root, nvidia_api_key=None),
        budget=ExtractionBudget(max_model_calls=0),
    )
    (root,) = [
        e
        for e in prepared["package"]["scientific_extraction"]["raw_proposals"]["entities"]
        if e["class_id"] == "Investigation" and e["label"] == "Synthetic study"
    ]
    o = Output().model_dump()
    o["entities"] = [root, entity(p, *subject_entity)]
    s = {
        "text": SENTENCE,
        "class_id": "ReportedObservation",
        "epistemic": "measured_observation",
        "subjects": [subject_entity[0]],
        "study": "current",
        "support": support(p, SENTENCE),
    }
    s["support"][0]["start"] = TEXT.index(SENTENCE)
    o["statements"] = [s]
    return [r for r in validate(service, p, o)["records"] if r["kind"] == "statements"][-1]


def test_a_group_the_passage_does_not_belong_to_scopes_it_to_the_study(service):
    record = observation(
        service, ("alpha", "Alpha series", "ExperimentFamily", "The Alpha series used a flow duct.")
    )
    assert record["status"] == "SOURCE_SUPPORTED", record["reasons"]
    assert record["scope_context"]["basis"] == (
        "ORIGINAL_RESEARCH_SECTION_AT_DOCUMENT_INVESTIGATION_SCOPE"
    )
    assert record["scope_context"]["distributes_to_members"] is False
    assert record["proposed_subjects"] == ["alpha"]


def test_a_supported_run_the_passage_does_not_belong_to_is_never_rescoped(service):
    # Negative: an individual run keeps the existing contract.
    record = observation(service, ("a1", "A1", "ExperimentalRun", "Run A1 was tested."))
    assert record["status"] != "SOURCE_SUPPORTED"
