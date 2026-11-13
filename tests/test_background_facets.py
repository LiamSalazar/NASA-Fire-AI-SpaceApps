"""Background facets (SCIENCE_BACKGROUND_FACETS): a statement may carry scope "background"
(the state of the art or prior knowledge of the field) or execution "ongoing" (an activity
under way). Off by default: the schema, the parser and the requests are as before.
Synthetic text."""

from test_document_extraction import entity, submitted, support, validate
from test_document_extraction import service as _service

from nasa_fire_ai.ingestion.document_extraction import (
    Output,
    parse_model_output,
    stage_schema,
)
from nasa_fire_ai.ingestion.scientific_facets import facets

service = _service
FLAG = "SCIENCE_BACKGROUND_FACETS"
BACKGROUND = "Few existing coatings can be rated for use in enriched air."
ONGOING = "The team has been modifying existing coatings and developing new ones."


CLASSES = {
    "author_reported_conclusion": "NASAConclusion",
    "measured_observation": "ReportedObservation",
    "planned_activity": "PlannedActivity",
    "tentative_interpretation": "NASAConclusion",
    "experimental_configuration": "ExperimentalCondition",
}


def statement(text, epistemic, **extra):
    return {
        "subjects": ["inv"],
        "text": text,
        "class_id": CLASSES[epistemic],
        "epistemic": epistemic,
        "study": "current",
        **extra,
    }


def records(service, items):
    p = submitted(service, f"Synthetic Coating Study\nI. Introduction\n{BACKGROUND}\n{ONGOING}\n")
    o = Output().model_dump()
    o["entities"] = [
        entity(p, "inv", "Synthetic Coating Study", "Investigation", "Synthetic Coating Study")
    ]
    o["statements"] = [{**i, "support": support(p, i["text"])} for i in items]
    return [r for r in validate(service, p, o)["records"] if r["kind"] == "statements"]


def test_off_by_default_the_contract_is_unchanged(monkeypatch):
    monkeypatch.delenv(FLAG, raising=False)
    props = stage_schema("propositions", compact=True)["$defs"]["Statement"]["properties"]
    assert "scope" not in props and "execution" not in props
    result, errors = parse_model_output(
        '{"statements": [{"text": "x", "class_id": "NASAConclusion", "epistemic": "hypothesis",'
        ' "support": [{"evidence_id": "E1", "quote": "x", "start": 0}], "scope": "background"}]}'
    )
    assert not result["statements"] and errors


def test_off_by_default_parsed_items_carry_no_new_field(monkeypatch):
    monkeypatch.delenv(FLAG, raising=False)
    result, _ = parse_model_output(
        '{"statements": [{"text": "x", "class_id": "NASAConclusion", "epistemic": "hypothesis",'
        ' "support": [{"evidence_id": "E1", "quote": "x", "start": 0}]}]}'
    )
    assert result["statements"] and not {"scope", "execution"} & set(result["statements"][0])


def test_on_the_schema_offers_both_values(monkeypatch):
    monkeypatch.setenv(FLAG, "1")
    props = stage_schema("propositions", compact=True)["$defs"]["Statement"]["properties"]
    assert props["scope"]["anyOf"][0]["const"] == "background"
    assert props["execution"]["anyOf"][0]["const"] == "ongoing"


def test_a_background_statement_needs_no_experimental_subject(service, monkeypatch):
    monkeypatch.setenv(FLAG, "1")
    (record,) = records(
        service, [statement(BACKGROUND, "author_reported_conclusion", scope="background")]
    )
    assert "STATEMENT_REQUIRES_EXPERIMENTAL_SCOPE" not in record["reasons"]
    assert record["scope_context"]["basis"] == "SOURCE_STATES_BACKGROUND_OF_THE_FIELD"
    assert facets("statements", record["proposal"])["temporal_scope"] == "background"


def test_background_never_types_an_observation(service, monkeypatch):
    monkeypatch.setenv(FLAG, "1")
    (record,) = records(
        service, [statement(BACKGROUND, "measured_observation", scope="background")]
    )
    assert record["status"] == "REJECTED"
    assert "BACKGROUND_SCOPE_CONTRADICTS_ROLE" in " ".join(record["reasons"])


def test_ongoing_is_neither_executed_nor_planned(service, monkeypatch):
    monkeypatch.setenv(FLAG, "1")
    item = statement(ONGOING, "author_reported_conclusion", execution="ongoing")
    assert facets("statements", item)["execution_status"] == "ongoing"
    item = statement(ONGOING, "tentative_interpretation", execution="ongoing")
    (record,) = records(service, [item])
    assert record["status"] == "REJECTED"
    assert "ONGOING_EXECUTION_CONTRADICTS_ROLE" in " ".join(record["reasons"])


def test_old_records_read_as_before():
    item = statement(BACKGROUND, "author_reported_conclusion")
    assert facets("statements", item)["temporal_scope"] == "current"
    assert facets("statements", item)["execution_status"] == "executed"


def test_a_background_statement_is_held_by_neither_subject_nor_author_checks(service, monkeypatch):
    monkeypatch.setenv(FLAG, "1")
    (record,) = records(
        service, [statement(BACKGROUND, "author_reported_conclusion", scope="background")]
    )
    assert "STATEMENT_SUBJECT_APPLICABILITY_UNRESOLVED" not in record["reasons"]
    assert "AUTHOR_ROLE_REQUIRES_CONTEXT_REVIEW" not in record["reasons"]
    assert record["status"] == "SOURCE_SUPPORTED"


def test_the_same_statement_without_the_mark_is_still_held(service, monkeypatch):
    # Metamorphic: only the model's mark changes the outcome, never the text.
    monkeypatch.setenv(FLAG, "1")
    (record,) = records(service, [statement(BACKGROUND, "author_reported_conclusion")])
    assert record["status"] == "UNRESOLVED"
    assert "AUTHOR_ROLE_REQUIRES_CONTEXT_REVIEW" in record["reasons"]


def test_an_ongoing_activity_keeps_the_author_check(service, monkeypatch):
    monkeypatch.setenv(FLAG, "1")
    (record,) = records(
        service, [statement(ONGOING, "author_reported_conclusion", execution="ongoing")]
    )
    assert "AUTHOR_ROLE_REQUIRES_CONTEXT_REVIEW" in record["reasons"]


# ---- V2 (SCIENCE_ONGOING_ACTIVITY_ROLES): an activity under way is an activity role, not a conclusion
V2 = "SCIENCE_ONGOING_ACTIVITY_ROLES"


def test_v2_is_off_by_default_and_changes_the_roles(monkeypatch):
    from nasa_fire_ai.ingestion.scientific_facets import ongoing_roles

    monkeypatch.delenv(V2, raising=False)
    assert ongoing_roles() == {"author_reported_conclusion"}
    monkeypatch.setenv(V2, "1")
    assert ongoing_roles() == {"experimental_configuration", "planned_activity"}


def test_v2_moves_ongoing_from_the_conclusion_to_the_activity_roles(service, monkeypatch):
    monkeypatch.setenv(FLAG, "1")
    monkeypatch.setenv(V2, "1")
    items = [
        statement(ONGOING, "author_reported_conclusion", execution="ongoing"),
        statement(ONGOING, "planned_activity", execution="ongoing"),
    ]
    out = records(service, items)
    assert out[0]["status"] == "REJECTED"
    assert "ONGOING_EXECUTION_CONTRADICTS_ROLE" in out[0]["reasons"]
    assert "ONGOING_EXECUTION_CONTRADICTS_ROLE" not in out[1]["reasons"]
    assert "ONGOING_EXECUTION_NOT_PROGRESSIVE_IN_SOURCE" not in out[1]["reasons"]


def test_v2_requires_a_progressive_governing_clause(service, monkeypatch):
    monkeypatch.setenv(FLAG, "1")
    monkeypatch.setenv(V2, "1")
    out = records(
        service, [statement(BACKGROUND, "experimental_configuration", execution="ongoing")]
    )
    assert out[0]["status"] == "REJECTED"
    assert "ONGOING_EXECUTION_NOT_PROGRESSIVE_IN_SOURCE" in out[0]["reasons"]


def test_without_v2_a_conclusion_may_still_state_ongoing(service, monkeypatch):
    monkeypatch.setenv(FLAG, "1")
    monkeypatch.delenv(V2, raising=False)
    out = records(service, [statement(ONGOING, "author_reported_conclusion", execution="ongoing")])
    assert "ONGOING_EXECUTION_CONTRADICTS_ROLE" not in out[0]["reasons"]
