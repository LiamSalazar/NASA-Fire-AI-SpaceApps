"""R4 (SCIENCE_PLAN_GOAL_FACETS): a plan or a goal is a complete record on its staged class,
with its facets explicit, and never reads as executed. Invented text only; no model call."""

import pytest
from test_document_extraction import entity, submitted, validate
from test_document_extraction import service as _service
from test_scientific_facets import statement

from nasa_fire_ai.evaluation.phase1_protocol import outcome
from nasa_fire_ai.ingestion.document_extraction import Output
from nasa_fire_ai.ingestion.proposal_states import state_dimensions, vocabulary_extension_proposals
from nasa_fire_ai.ingestion.scientific_facets import describes_execution

service = _service
FLAG = "SCIENCE_PLAN_GOAL_FACETS"

STUDY = "Synthetic study"
PLAN_TEXT = (
    "Qualification firing of the copper spools will take place at the Ridgeline annex next spring."
)
DONE_TEXT = (
    "Qualification firing of the copper spools took place at the Ridgeline annex last spring."
)
GOAL_TEXT = "The aim of the program is to harden woven liners for longer crewed voyages."


def document(sentence, heading="II. Methods"):
    return f"{STUDY}\n{heading}\n{sentence}\n"


def run(
    service, sentence, role, cls, subject_class="Investigation", modalities=(None,), study=STUDY
):
    text = document(sentence)
    if study != STUDY:
        # The package title is the study's label; another name is printed beneath it.
        text = text.replace(f"{STUDY}\n", f"{STUDY}\n{study}\n", 1)
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [entity(p, "s", STUDY, subject_class, STUDY)]
    o["statements"] = [statement(p, sentence, role, cls, ["s"], modality=m) for m in modalities]
    return [r for r in validate(service, p, o)["records"] if r["kind"] == "statements"]


def shape(records):
    """What a flag may change, without the package-specific evidence ids."""
    return [
        (r["id"], r["status"], sorted(r["reasons"]), sorted(r), r.get("duplicate_of"))
        for r in records
    ]


def active(records):
    return [
        r for r in records if not r.get("duplicate_of") and r.get("active_proposal") is not False
    ]


@pytest.mark.parametrize(
    ("sentence", "role", "cls", "modality", "execution"),
    [
        (PLAN_TEXT, "planned_activity", "PlannedActivity", "proposed", "planned"),
        (GOAL_TEXT, "stated_goal", "ResearchGoal", "intended", "not_applicable"),
    ],
)
def test_a_plan_or_goal_is_complete_on_its_staged_class_with_explicit_facets(
    service, monkeypatch, sentence, role, cls, modality, execution
):
    monkeypatch.setenv(FLAG, "1")
    (record,) = active(run(service, sentence, role, cls))
    assert record["status"] != "REJECTED", record["reasons"]
    # The class stays staged: no approved term is borrowed or invented.
    assert set(record["reasons"]) == {"UNREGISTERED_INFORMATION_CLASS"}
    assert record["proposal"]["class_id"] == cls
    dims = state_dimensions(record)
    assert dims["completeness"] == "COMPLETE" and dims["extension"] == "STAGED"
    assert outcome([record]) == "COMPLETE_WITH_STAGED_EXTENSION"
    facets = record["facets"]
    assert facets["modality"] == modality
    assert facets["execution_status"] == execution
    assert facets["temporal_scope"] == "future"
    assert facets["attribution"] == "current_study"
    assert not describes_execution("statements", record["proposal"])


def test_a_done_clause_typed_as_a_plan_is_rejected(service, monkeypatch):
    monkeypatch.setenv(FLAG, "1")
    (record,) = run(service, DONE_TEXT, "planned_activity", "PlannedActivity")
    assert record["status"] == "REJECTED"
    assert any("PLAN_NOT_EXPLICIT_IN_SOURCE" in r for r in record["reasons"])
    assert "facets" not in record


def test_a_plan_never_names_an_executed_run(service, monkeypatch):
    monkeypatch.setenv(FLAG, "1")
    (record,) = run(
        service, PLAN_TEXT, "planned_activity", "PlannedActivity", subject_class="ExperimentalRun"
    )
    assert record["status"] == "REJECTED"
    assert any("PLANNED_STATEMENT_ATTRIBUTED_TO_EXECUTED_RUN" in r for r in record["reasons"])


def test_a_plan_stated_as_actual_still_reads_as_planned(service, monkeypatch):
    # "actual" means no modality: the profile's own facets apply, never "executed".
    monkeypatch.setenv(FLAG, "1")
    (record,) = active(
        run(service, PLAN_TEXT, "planned_activity", "PlannedActivity", modalities=("actual",))
    )
    assert record["facets"]["execution_status"] == "planned"


def test_the_goal_with_and_without_its_own_modality_is_one_assertion(service, monkeypatch):
    monkeypatch.setenv(FLAG, "1")
    records = run(service, GOAL_TEXT, "stated_goal", "ResearchGoal", modalities=(None, "intended"))
    assert len(records) == 2
    (owner,) = active(records)
    (copy,) = [r for r in records if r is not owner]
    assert copy["duplicate_of"] == owner["id"]


def test_a_plan_stated_as_intended_stays_a_separate_reading(service, monkeypatch):
    # "intended" is not the plan profile's own modality ("proposed"): not merged.
    monkeypatch.setenv(FLAG, "1")
    records = run(
        service, PLAN_TEXT, "planned_activity", "PlannedActivity", modalities=(None, "intended")
    )
    assert len(active(records)) == 2


@pytest.mark.parametrize("study", ["Lantern Weave Campaign", "Basalt Mesh Survey"])
def test_renaming_the_study_keeps_the_reading(service, monkeypatch, study):
    # Metamorphic: the study's name is not part of the rule.
    monkeypatch.setenv(FLAG, "1")
    (record,) = active(run(service, PLAN_TEXT, "planned_activity", "PlannedActivity", study=study))
    assert set(record["reasons"]) == {"UNREGISTERED_INFORMATION_CLASS"}
    assert record["facets"]["execution_status"] == "planned"


def test_only_the_tense_decides_plan_or_done(service, monkeypatch):
    # Metamorphic: the same sentence with its verb moved to the past is no longer a plan.
    monkeypatch.setenv(FLAG, "1")
    planned = active(run(service, PLAN_TEXT, "planned_activity", "PlannedActivity"))
    done = run(service, DONE_TEXT, "planned_activity", "PlannedActivity")
    assert planned and planned[0]["status"] != "REJECTED"
    assert done[0]["status"] == "REJECTED"


@pytest.mark.parametrize(
    ("sentence", "role", "cls", "modalities"),
    [
        (PLAN_TEXT, "planned_activity", "PlannedActivity", (None,)),
        (GOAL_TEXT, "stated_goal", "ResearchGoal", (None, "intended")),
        (DONE_TEXT, "planned_activity", "PlannedActivity", (None,)),
    ],
)
def test_flags_off_identity(service, monkeypatch, sentence, role, cls, modalities):
    monkeypatch.delenv(FLAG, raising=False)
    absent = run(service, sentence, role, cls, modalities=modalities)
    monkeypatch.setenv(FLAG, "0")
    off = run(service, sentence, role, cls, modalities=modalities)
    assert shape(absent) == shape(off)
    assert all("facets" not in r for r in off)
    # Today's behaviour, kept with the flag off: both goal readings stay active.
    assert len(active(off)) == len(modalities) or off[0]["status"] == "REJECTED"


def test_the_staged_class_profile_is_the_roles_not_the_first_records(service, monkeypatch):
    # The first supporting record states "intended"; the plan role's profile is "proposed".
    monkeypatch.setenv(FLAG, "1")
    records = run(
        service, PLAN_TEXT, "planned_activity", "PlannedActivity", modalities=("intended", None)
    )
    (staged,) = [
        p for p in vocabulary_extension_proposals(records, {}) if p["term"] == "PlannedActivity"
    ]
    assert staged["facet_profile"] == {
        "statement_type": "plan",
        "epistemic_role": "intended",
        "modality": "proposed",
        "execution_status": "planned",
    }
