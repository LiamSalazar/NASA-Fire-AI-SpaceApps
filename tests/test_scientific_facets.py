"""Scientific facets: legacy roles as profiles, plans, goals, criteria and proposed values.

Synthetic text only, through the production validator; no model call, no NASA data.
"""

import pytest
from test_document_extraction import entity, submitted, support, validate
from test_document_extraction import service as _service

from nasa_fire_ai.ingestion.document_extraction import Output, proposal_identity
from nasa_fire_ai.ingestion.scientific_facets import (
    QUANTITY_PROFILES,
    STATEMENT_PROFILES,
    facets,
    facets_of,
)

service = _service

LEGACY_STATEMENT_ROLES = (
    "measured_observation",
    "author_reported_conclusion",
    "tentative_interpretation",
    "hypothesis",
    "open_question",
    "normative_requirement",
    "guidance",
    "experimental_configuration",
    "derived_quantity",
    "documentary_context",
)


def statement(package, text, role, cls, subjects, study="current", modality=None):
    item = {
        "text": text,
        "class_id": cls,
        "epistemic": role,
        "subjects": subjects,
        "study": study,
        "support": support(package, text),
    }
    if modality:
        item["modality"] = modality
    return item


def quantity(package, quote, subject, label, expression, unit, role, modality=None):
    item = {
        "subject": subject,
        "label": label,
        "expression": expression,
        "unit": unit,
        "epistemic": role,
        "support": support(package, quote),
        "printed_name": None,
    }
    if modality:
        item["modality"] = modality
    return item


def only(records, kind):
    (record,) = [r for r in records if r["kind"] == kind]
    return record


def test_every_legacy_role_reads_as_its_profile_without_a_modality():
    for role in LEGACY_STATEMENT_ROLES:
        assert (
            facets("statements", {"epistemic": role, "study": "current"})["modality"]
            == (STATEMENT_PROFILES[role]["modality"])
        )
    for role in ("reported_quantity", "derived_quantity", "experimental_configuration"):
        assert facets("quantities", {"epistemic": role}) == {
            **QUANTITY_PROFILES[role],
            "temporal_scope": "current",
            "attribution": "current_study",
        }


def test_an_unset_modality_keeps_the_proposal_id_old_records_have():
    old = {"text": "A1 charred.", "epistemic": "measured_observation", "subjects": ["a1"]}
    assert proposal_identity("statements", old) == proposal_identity(
        "statements", {**old, "modality": None}
    )
    # A stated modality is a different proposal, and so is another subject.
    assert proposal_identity("statements", old) != proposal_identity(
        "statements", {**old, "modality": "proposed"}
    )
    assert proposal_identity("statements", old) != proposal_identity(
        "statements", {**old, "subjects": ["a2"]}
    )


def test_a_cited_result_stays_historical():
    cited = facets("statements", {"epistemic": "measured_observation", "study": "cited"})
    assert cited["temporal_scope"] == "historical" and cited["attribution"] == "cited_study"
    assert cited["execution_status"] == "executed"


STUDY = "Panel Char Study"
PLAN = STUDY + "\nII. Methods\nRun B7 will drop each panel twice at reduced pressure.\n"
PLAN_SENTENCE = "Run B7 will drop each panel twice at reduced pressure."


def test_a_plan_is_kept_as_a_plan_and_its_class_is_staged(service):
    p = submitted(service, PLAN)
    o = Output().model_dump()
    o["entities"] = [entity(p, "inv", STUDY, "Investigation", STUDY)]
    o["statements"] = [statement(p, PLAN_SENTENCE, "planned_activity", "PlannedActivity", ["inv"])]
    record = only(validate(service, p, o)["records"], "statements")
    assert record["status"] != "REJECTED", record["reasons"]
    assert "UNREGISTERED_INFORMATION_CLASS" in record["reasons"]
    found = facets_of(record)
    assert found["statement_type"] == "plan" and found["execution_status"] == "planned"
    assert found["modality"] == "proposed" and found["temporal_scope"] == "future"


@pytest.mark.parametrize(
    ("role", "cls", "subject_class", "reason"),
    [
        # Metamorphic: the same planned sentence, read as what happened.
        (
            "measured_observation",
            "ReportedObservation",
            "ExperimentalRun",
            "PLANNED_OR_COUNTERFACTUAL_IS_NOT_OBSERVATION",
        ),
        # A plan cannot name an executed run as its subject.
        (
            "planned_activity",
            "PlannedActivity",
            "ExperimentalRun",
            "PLANNED_STATEMENT_ATTRIBUTED_TO_EXECUTED_RUN",
        ),
    ],
)
def test_a_proposed_experiment_is_not_represented_as_executed(
    service, role, cls, subject_class, reason
):
    p = submitted(service, PLAN)
    o = Output().model_dump()
    o["entities"] = [entity(p, "r", "B7", subject_class, PLAN_SENTENCE)]
    o["statements"] = [statement(p, PLAN_SENTENCE, role, cls, ["r"])]
    record = only(validate(service, p, o)["records"], "statements")
    assert record["status"] == "REJECTED", record["reasons"]
    assert any(reason in r for r in record["reasons"])


def test_an_observation_cannot_be_given_a_modality_that_says_it_did_not_happen(service):
    text = "II. Results\nRun A1 charred along its upper edge.\n"
    sentence = "Run A1 charred along its upper edge."
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [entity(p, "a1", "A1", "ExperimentalRun", sentence)]
    o["statements"] = [
        statement(
            p, sentence, "measured_observation", "ReportedObservation", ["a1"], modality="proposed"
        )
    ]
    record = only(validate(service, p, o)["records"], "statements")
    assert record["status"] == "REJECTED"
    assert any("MODALITY_CONTRADICTS_ROLE" in r for r in record["reasons"])


CRITERIA = STUDY + "\nIII. Test Method\nA panel passes when its char length stays below 9 cm.\n"
CRITERION = "A panel passes when its char length stays below 9 cm."


def test_a_printed_criterion_reuses_the_approved_criterion_class(service):
    p = submitted(service, CRITERIA)
    o = Output().model_dump()
    o["entities"] = [entity(p, "inv", STUDY, "Investigation", STUDY)]
    o["statements"] = [statement(p, CRITERION, "test_criterion", "TestCriterion", ["inv"])]
    record = only(validate(service, p, o)["records"], "statements")
    assert record["status"] != "REJECTED", record["reasons"]
    # TestCriterion is approved vocabulary: nothing is staged for it.
    assert "UNREGISTERED_INFORMATION_CLASS" not in record["reasons"]
    assert facets_of(record)["statement_type"] == "test_criterion"


@pytest.mark.parametrize(
    "text",
    [
        # A list of what was measured does not say that it is a pass criterion.
        "Char length and afterflame time were recorded for each panel.",
        # Nor does a bare number.
        "Char length was 7 cm on the second panel.",
    ],
)
def test_a_criterion_is_never_read_into_a_sentence_that_does_not_state_one(service, text):
    p = submitted(service, STUDY + "\nIII. Test Method\n" + text + "\n")
    o = Output().model_dump()
    o["entities"] = [entity(p, "inv", STUDY, "Investigation", STUDY)]
    o["statements"] = [statement(p, text, "test_criterion", "TestCriterion", ["inv"])]
    record = only(validate(service, p, o)["records"], "statements")
    assert record["status"] == "REJECTED"
    assert any("CRITERION_NOT_EXPLICIT_IN_SOURCE" in r for r in record["reasons"])


def test_a_criterion_class_with_a_requirement_role_still_contradicts():
    # A test criterion is not a requirement: the role-to-class check keeps them apart.
    from nasa_fire_ai.ingestion.document_extraction import STATEMENT_CLASSES

    assert STATEMENT_CLASSES["test_criterion"] == "TestCriterion"
    assert STATEMENT_CLASSES["normative_requirement"] == "Requirement"


PROPOSED = STUDY + "\nII. Approach\nRun B7 will hold oxygen at 34 % for each panel.\n"
PROPOSED_SENTENCE = "Run B7 will hold oxygen at 34 % for each panel."


def test_a_proposed_setting_is_never_attributed_to_an_executed_run(service):
    p = submitted(service, PROPOSED)
    o = Output().model_dump()
    o["entities"] = [entity(p, "r", "B7", "ExperimentalRun", PROPOSED_SENTENCE)]
    o["quantities"] = [
        quantity(
            p,
            PROPOSED_SENTENCE,
            "r",
            "oxygen",
            "34",
            "%",
            "experimental_configuration",
            modality="proposed",
        )
    ]
    record = only(validate(service, p, o)["records"], "quantities")
    assert record["status"] != "SOURCE_SUPPORTED", record
    assert record["proposal"].get("subject") != "r" or record["status"] == "REJECTED"


def test_a_modality_the_source_does_not_print_is_refused(service):
    text = STUDY + "\nII. Methods\nThe chamber held oxygen at 34 % for each panel.\n"
    sentence = "The chamber held oxygen at 34 % for each panel."
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [entity(p, "inv", STUDY, "Investigation", STUDY)]
    o["quantities"] = [
        quantity(
            p,
            sentence,
            "inv",
            "oxygen",
            "34",
            "%",
            "experimental_configuration",
            modality="proposed",
        )
    ]
    record = only(validate(service, p, o)["records"], "quantities")
    assert record["status"] != "SOURCE_SUPPORTED", record
    assert any("MODALITY_NOT_SUPPORTED_BY_SOURCE" in r for r in record["reasons"])


def test_a_reported_measurement_cannot_be_proposed(service):
    p = submitted(service, PROPOSED)
    o = Output().model_dump()
    o["entities"] = [entity(p, "inv", STUDY, "Investigation", STUDY)]
    o["quantities"] = [
        quantity(
            p,
            PROPOSED_SENTENCE,
            "inv",
            "oxygen",
            "34",
            "%",
            "reported_quantity",
            modality="proposed",
        )
    ]
    record = only(validate(service, p, o)["records"], "quantities")
    assert record["status"] != "SOURCE_SUPPORTED", record
    assert any("MODALITY_CONTRADICTS_ROLE" in r for r in record["reasons"])


OWN = "Synthetic study"


@pytest.mark.parametrize(
    ("section", "admitted"),
    [
        # Outside the methods section, where a configuration already takes the
        # investigation, a proposed value of the study's own text still does.
        ("III. Results and Discussion", True),
        # Metamorphic: the same proposed value printed as background is not the
        # study's own; it gets no investigation scope.
        ("I. Background", False),
    ],
)
def test_a_proposed_value_of_the_study_takes_the_study_as_its_subject(service, section, admitted):
    sentence = "The follow-on tests will hold oxygen at 34 % for each panel."
    p = submitted(service, f"{OWN}\n{section}\n{sentence}\n")
    o = Output().model_dump()
    o["entities"] = [entity(p, "inv", OWN, "Investigation", OWN)]
    o["quantities"] = [
        quantity(p, sentence, "inv", "oxygen", "34", "%", "experimental_configuration", "proposed")
    ]
    record = only(validate(service, p, o)["records"], "quantities")
    basis = (record.get("scope_context") or {}).get("basis")
    if admitted:
        assert basis == "STUDY_OWN_NON_EXECUTED_VALUE_AT_INVESTIGATION_SCOPE", record["reasons"]
        assert record["status"] != "REJECTED"
    else:
        assert basis != "STUDY_OWN_NON_EXECUTED_VALUE_AT_INVESTIGATION_SCOPE"


def test_a_caption_without_an_outcome_is_not_an_observation():
    from nasa_fire_ai.ingestion.document_extraction import role_errors

    caption = {
        "text": "Figure 8 - Pre-Impact Functional Test with GN2",
        "epistemic": "measured_observation",
    }
    assert "FIGURE_CAPTION_IS_NOT_OBSERVATION" in role_errors(caption)
    # Metamorphic: a caption that reports an outcome is not refused for being a caption.
    burned = {**caption, "text": "Figure 8 - The coupon burned to the clamp"}
    assert "FIGURE_CAPTION_IS_NOT_OBSERVATION" not in role_errors(burned)


def test_a_reported_value_in_a_caption_title_is_held(service):
    caption = "Figure 9 - Valve Inlet Pressure During the Dry Impact Tests to 3750 psia"
    p = submitted(service, f"{OWN}\nIII. Results\n{caption}\nThe valve held pressure.\n")
    o = Output().model_dump()
    o["entities"] = [entity(p, "inv", OWN, "Investigation", OWN)]
    o["quantities"] = [quantity(p, caption, "inv", "Pressure", "3750", "psia", "reported_quantity")]
    record = only(validate(service, p, o)["records"], "quantities")
    assert record["status"] != "SOURCE_SUPPORTED"
