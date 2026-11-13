"""One printed sentence proposed from two windows is one statement; synthetic, never NASA data."""

from test_document_extraction import entity, submitted, support, validate
from test_document_extraction import service as _service

from nasa_fire_ai.ingestion.document_extraction import Output

service = _service

TEXT = (
    "II. Methods\nThe Alpha rig and the Beta rig were run in air.\n"
    "III. Results\nForty runs were completed on both rigs.\n"
)
SENTENCE = "Forty runs were completed on both rigs."


def active_statements(service, statements):
    p = submitted(service, TEXT)
    o = Output().model_dump()
    o["entities"] = [
        entity(p, "a", "Alpha rig", "Sample", "The Alpha rig and the Beta rig were run in air."),
        entity(p, "b", "Beta rig", "Sample", "The Alpha rig and the Beta rig were run in air."),
    ]
    o["statements"] = []
    for subjects, epistemic in statements:
        o["statements"].append(
            {
                "text": SENTENCE,
                "class_id": "ExperimentalCondition"
                if epistemic == "experimental_configuration"
                else "ReportedObservation",
                "epistemic": epistemic,
                "subjects": subjects,
                "study": "current",
                "support": support(p, SENTENCE),
            }
        )
    result = validate(service, p, o)
    ids = {key: e["id"] for key, e in result["entities_by_key"].items()}
    active = [
        r
        for r in result["records"]
        if r["kind"] == "statements" and r["status"] != "REJECTED" and not r.get("duplicate_of")
    ]
    return active, ids


def test_the_same_sentence_from_two_windows_is_one_statement_with_both_scopes(service):
    active, ids = active_statements(
        service, [(["a"], "measured_observation"), (["a", "b"], "measured_observation")]
    )
    assert len(active) == 1
    assert set(active[0]["scope"]) == {ids["a"], ids["b"]}
    # Metamorphic: the order the windows arrive in does not change the result.
    swapped, ids = active_statements(
        service, [(["a", "b"], "measured_observation"), (["a"], "measured_observation")]
    )
    assert len(swapped) == 1 and set(swapped[0]["scope"]) == {ids["a"], ids["b"]}


def test_a_different_role_stays_its_own_statement(service):
    # Negative: identical text and position, but one is a configuration.
    active, _ = active_statements(
        service, [(["a"], "measured_observation"), (["a"], "experimental_configuration")]
    )
    assert len(active) == 2
