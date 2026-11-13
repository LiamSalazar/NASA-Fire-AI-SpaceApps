"""SCIENCE_PURPOSE_READER: one reader of purpose clauses for every check that strips or
reads purpose (the change-verb exception of the configuration check, the observation
tense check, the clause frames, the facet "inside a purpose" reading, the observation
cue), and the configuration set-up verbs as one general class.

Purpose adjuncts (Quirk et al. 1985, adverbials of purpose; Huddleston & Pullum 2002,
purpose adjuncts): a fronted infinitive of purpose ("To X, ..."), a trailing one after a
comma (", to X"), the marked forms "in order to", "in order that", "so as to", "so that"
with a modal, and a participle of aiming ("aiming / seeking / intending / striving /
attempting to"). "so that" without a modal is a result clause, not a purpose.

Synthetic text only (B8): an invented domain (concrete, seals, welds, ovens).
"""

import pytest
from test_contract_candidates import configuration_reasons
from test_document_extraction import service as _service

from nasa_fire_ai.ingestion import clause_cues, statement_integrity
from nasa_fire_ai.ingestion.document_extraction import (
    article_subject_cue,
    article_terms,
    role_errors,
)
from nasa_fire_ai.ingestion.scientific_facets import modality_review

service = _service

FLAG = "SCIENCE_PURPOSE_READER"
CHANGE = "CHANGING_OBSERVATION_IS_NOT_ESTABLISHED_CONFIGURATION"
NOT_CONFIGURATION = "CONFIGURATION_ROLE_NOT_ESTABLISHED_IN_ORIGINAL_PASSAGE"
NOT_SUPPORTED = "MODALITY_NOT_SUPPORTED_BY_SOURCE"
PLANNED = "PLANNED_OR_COUNTERFACTUAL_IS_NOT_OBSERVATION"


@pytest.fixture
def on(monkeypatch):
    monkeypatch.setenv(FLAG, "1")
    monkeypatch.setenv("SCIENCE_CONTRACT_C2", "1")
    return monkeypatch


def spans_text(text):
    return [text[a:b] for a, b in clause_cues.purpose_spans(text)]


# --- the reader itself ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "purpose"),
    [
        ("To widen the margin, three cylinders were cured per batch.", "To widen the margin"),
        ("Three cylinders were cured per batch, to widen the margin.", "to widen the margin"),
        (
            "The oven was held at 120 C in order to determine the drift.",
            "in order to determine the drift",
        ),
        (
            "The lid was clamped so that the vapour could not escape.",
            "so that the vapour could not escape",
        ),
        ("Each panel was primed, aiming for a 40 um film.", "aiming for a 40 um film"),
        (
            "Each slab was troweled, seeking to reach a 5 mm screed.",
            "seeking to reach a 5 mm screed",
        ),
        ("The cell was cycled so as to age the anode.", "so as to age the anode"),
    ],
)
def test_each_purpose_form_is_read(text, purpose):
    assert any(purpose in found for found in spans_text(text))


@pytest.mark.parametrize(
    "text",
    [
        "To date, no seal has leaked.",
        "The rig was heated to 300 C and the seal held.",
        "The bond was found to be weak.",
        "The flow was observed to increase.",
        # A result clause: "so that" without a modal.
        "The joint cooled quickly, so that the solder cracked.",
        "The slab was exposed to rain for two days.",
    ],
)
def test_what_is_not_a_purpose_is_not_read_as_one(text):
    assert clause_cues.purpose_spans(text) == []


def test_stripping_is_idempotent_and_keeps_the_main_clause():
    text = "To widen the margin, three cylinders were cured per batch."
    once = clause_cues.strip_purpose(text)
    assert clause_cues.strip_purpose(once) == once
    assert "three cylinders were cured per batch" in once
    assert "widen" not in once


def test_a_value_inside_and_outside_a_purpose():
    text = "Each panel was primed with 20 um of sealer, aiming for a 40 um film."
    assert clause_cues.in_purpose(text, text.index("40"))
    assert not clause_cues.in_purpose(text, text.index("20"))


# --- positive (flag on) ---------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "To decrease scatter, four cylinders were cast and set in each mould of Run A1.",
        "Four cylinders were cast and set in each mould of Run A1, to decrease scatter.",
    ],
)
def test_a_change_verb_of_purpose_is_not_an_observed_change(service, on, text):
    assert CHANGE not in configuration_reasons(service, text)


@pytest.mark.parametrize(
    "text",
    [
        "The heater of Run A1 was adjusted between runs.",
        "Two shims were positioned under the base plate of Run A1.",
        "The load cell of Run A1 was calibrated before each series.",
        "Wall temperatures of Run A1 followed the schedule.",
    ],
)
def test_a_set_up_verb_or_a_plural_setting_states_a_configuration(service, on, text):
    assert NOT_CONFIGURATION not in configuration_reasons(service, text)


def test_a_value_the_done_step_aimed_at_is_an_intention(on):
    text = "Each panel was primed, aiming for a 40 um film."
    assert modality_review(text, "intended", "40") == ([], [])


def test_a_fronted_purpose_does_not_make_the_observation_counterfactual(on):
    text = "To check whether the seal would hold, the rig was pressurized and no leak was seen."
    assert PLANNED not in role_errors({"text": text, "epistemic": "measured_observation"})


def test_a_marked_purpose_is_a_procedure_not_an_observation(on):
    text = "A photo was taken so that the crack could be measured."
    assert not statement_integrity.observation_cue(text)


# --- negative (flag on) ---------------------------------------------------------------


def test_an_observed_change_after_a_purpose_stays_a_change(service, on):
    text = (
        "To decrease scatter, four cylinders were cast and set in Run A1, "
        "and the slump increased with each batch."
    )
    assert CHANGE in configuration_reasons(service, text)


@pytest.mark.parametrize(
    "text",
    ["Four alloys were tested in Run A1.", "Two blends were tested in Run A1 and both cracked."],
)
def test_tested_in_alone_is_not_a_configuration(service, on, text):
    # The phrase list of C2 is replaced by the set-up verb class; testing is execution.
    assert NOT_CONFIGURATION in configuration_reasons(service, text)


def test_the_value_of_a_done_step_before_its_purpose_is_not_an_intention(on):
    text = "Each panel was primed with 40 um of sealer, aiming for a smooth finish."
    assert modality_review(text, "intended", "40")[0] == [NOT_SUPPORTED]


def test_a_value_in_the_main_clause_after_a_fronted_purpose_is_done(on):
    # The purpose clause ends at its comma; the held temperature is the done step.
    text = "To determine the drift, the oven was held at 120 C."
    assert modality_review(text, "intended", "120")[0] == [NOT_SUPPORTED]


def test_a_counterfactual_main_clause_stays_counterfactual(on):
    text = "The rig would be pressurized to 3 bar in order to check the seal."
    assert PLANNED in role_errors({"text": text, "epistemic": "measured_observation"})


# --- metamorphic ----------------------------------------------------------------------


@pytest.mark.parametrize("verb", ["decrease scatter", "increase repeatability", "grow the batch"])
def test_fronted_and_trailing_purposes_read_alike(service, on, verb):
    fronted = f"To {verb}, four cylinders were cast and set in each mould of Run A1."
    trailing = f"Four cylinders were cast and set in each mould of Run A1, to {verb}."
    assert (CHANGE in configuration_reasons(service, fronted)) == (
        CHANGE in configuration_reasons(service, trailing)
    )


@pytest.mark.parametrize(("noun", "other"), [("cylinders", "prisms"), ("panel", "plate")])
def test_renaming_the_object_keeps_the_reading(on, noun, other):
    for text, value in (
        ("Each panel was primed, aiming for a 40 um film.", "40"),
        ("To decrease scatter, four cylinders were cast and set.", None),
    ):
        assert modality_review(text, "intended", value) == modality_review(
            text.replace(noun, other), "intended", value
        )
        assert clause_cues.strip_purpose(text).replace(noun, other) == clause_cues.strip_purpose(
            text.replace(noun, other)
        )


def test_the_step_purpose_reading_is_moved_not_changed(monkeypatch):
    texts = [
        "Each tube was flushed to remove the residue, and the wall thinned by 2 %.",
        "The heater was adjusted to lower the wall heat.",
        "The cell was heated to the point of venting.",
        "Each slab was exposed to rain and cracked.",
    ]
    found = {}
    for value in ("0", "1"):
        monkeypatch.setenv(FLAG, value)
        found[value] = [statement_integrity.procedure_without_outcome(t) for t in texts]
    assert found["0"] == found["1"]


def test_the_reader_is_the_only_purpose_definition(on):
    # One reader: the configuration check, the tense check and the facet reading agree
    # on where the purpose ends.
    text = "To decrease scatter, four cylinders were cast and set, and the slump increased."
    stripped = clause_cues.strip_purpose(text)
    assert "decrease" not in stripped
    assert "increased" in stripped


# --- metamorphic: the set-up decision follows the class, not a phrase ------------------

SET_UP_VERBS = [
    "set up",
    "configured",
    "installed",
    "adjusted",
    "calibrated",
    "mounted",
    "placed",
    "positioned",
]


@pytest.mark.parametrize("verb", SET_UP_VERBS)
def test_every_verb_of_the_set_up_class_decides_alike(service, on, verb):
    # Swap the verb for another of the class: the reading does not move.
    text = f"The strain gauge of Run A1 was {verb} on the rail."
    assert NOT_CONFIGURATION not in configuration_reasons(service, text)


@pytest.mark.parametrize("verb", ["tested", "measured", "weighed", "examined", "observed"])
def test_a_verb_outside_the_class_decides_alike(service, on, verb):
    # Testing and looking are execution: swapping among them never states a set-up.
    text = f"The strain gauge of Run A1 was {verb} on the rail."
    assert NOT_CONFIGURATION in configuration_reasons(service, text)


@pytest.mark.parametrize("subject", ["The ring", "The probe holder", "A pair of clamps"])
def test_the_set_up_decision_does_not_depend_on_the_object(service, on, subject):
    assert NOT_CONFIGURATION not in configuration_reasons(
        service, f"{subject} of Run A1 was calibrated twice."
    )
    assert NOT_CONFIGURATION in configuration_reasons(
        service, f"{subject} of Run A1 was weighed twice."
    )


@pytest.mark.parametrize(
    "text",
    [
        "Wall temperatures of Run A1 followed the schedule.",
        "The wall temperature of Run A1 followed the schedule.",
        "Wall temperature levels of Run A1 followed the schedule.",
        "Gas flows of Run A1 followed the schedule.",
        "The gas flow of Run A1 followed the schedule.",
        "Gas flow rates of Run A1 followed the schedule.",
        "Line pressures of Run A1 followed the schedule.",
        "The line pressure of Run A1 followed the schedule.",
    ],
)
def test_a_setting_noun_decides_alike_in_plural_singular_or_compound(service, on, text):
    assert NOT_CONFIGURATION not in configuration_reasons(service, text)


@pytest.mark.parametrize("noun", ["rails", "rail", "lids", "lid"])
def test_a_noun_that_is_not_a_setting_never_states_one(service, on, noun):
    assert NOT_CONFIGURATION in configuration_reasons(
        service, f"The {noun} of Run A1 followed the schedule."
    )


# --- purposes are anchored at a clause boundary; control verbs are not purposes --------


@pytest.mark.parametrize("verb", ["allowed", "permitted", "left", "used", "forced", "able"])
@pytest.mark.parametrize("inquiry", ["establish", "measure", "determine", "verify"])
def test_a_control_verb_with_an_infinitive_is_not_a_purpose(verb, inquiry):
    text = f"The burner was {verb} to {inquiry} and the flow was increased."
    assert clause_cues.purpose_spans(text) == []
    assert clause_cues.strip_purpose(text) == text


@pytest.mark.parametrize("verb", ["allowed", "left", "used"])
def test_a_control_verb_does_not_strip_a_change_verb(service, on, verb):
    text = f"The burner of Run A1 was {verb} to establish and the flow was increased."
    assert CHANGE in configuration_reasons(service, text)


@pytest.mark.parametrize(
    "text",
    [
        "To determine the drift, the oven was held at 120 C.",
        "The oven was held at 120 C, to determine the drift.",
        "The oven was held at 120 C; to determine the drift, it was logged.",
        "(a) To verify the seal, the lid was clamped.",
    ],
)
def test_an_inquiry_purpose_after_a_boundary_is_still_read(text):
    assert any("determine" in s or "verify" in s for s in spans_text(text))


# --- a test article and the passive of an applied step: classes, not strings ----------

ARTICLES = ("specimens", "samples")
STEPS = ("tested", "exposed", "subjected", "heated", "mounted", "placed")
BETWEEN = ["", " of the second pour", " from the lot", " cut from the slab", " of each type"]


def article_text(noun, between, verb):
    return f"Four {noun}{between} were {verb} in Run A1."


def test_the_nouns_come_from_the_registry_and_the_verbs_from_the_applied_steps(service):
    terms = article_terms(service.semantic)
    assert {"sample", "samples", "specimen", "specimens"} <= set(terms)
    assert "tested" in statement_integrity.APPLIED_STEP_VERBS
    assert statement_integrity.APPLIED_STEP.search("The rail was exposed to heat.")


@pytest.mark.parametrize("verb", STEPS)
@pytest.mark.parametrize("between", BETWEEN)
@pytest.mark.parametrize("noun", ARTICLES)
def test_a_registry_noun_and_an_applied_step_decide_alike(service, on, noun, between, verb):
    text = article_text(noun, between, verb)
    assert NOT_CONFIGURATION not in configuration_reasons(service, text)


def test_a_noun_added_to_the_registry_class_is_read_without_a_code_change(service, on):
    text = "Four coupons of the second pour were exposed in Run A1."
    assert NOT_CONFIGURATION in configuration_reasons(service, text)
    mentions = service.semantic.target_mentions
    on.setitem(mentions, "Sample", [*mentions["Sample"], "coupon", "coupons"])
    assert NOT_CONFIGURATION not in configuration_reasons(service, text)
    on.setitem(mentions, "Sample", [*mentions["Sample"], "article", "articles"])
    swapped = text.replace("coupons", "articles")
    assert NOT_CONFIGURATION not in configuration_reasons(service, swapped)


@pytest.mark.parametrize("noun", ["alloys", "blends", "rails"])
def test_a_noun_outside_the_class_is_not_widened(service, on, noun):
    text = f"Four {noun} of the second pour were tested in Run A1."
    assert NOT_CONFIGURATION in configuration_reasons(service, text)


@pytest.mark.parametrize("verb", ["weighed", "examined", "observed", "measured"])
def test_a_verb_outside_the_applied_steps_is_not_widened(service, on, verb):
    text = article_text("samples", " of the second pour", verb)
    assert NOT_CONFIGURATION in configuration_reasons(service, text)


@pytest.mark.parametrize(
    "text",
    [
        "Samples a b c d e f g were tested in Run A1.",
        "Samples of the lot, which were cut, were tested in Run A1.",
        "Samples were weighed, and the ovens were tested in Run A1.",
        "Samples that were cut from the slab were weighed in Run A1.",
        "Samples are weighed; the seals were tested in Run A1.",
        "Samples can be cut and the seals were tested in Run A1.",
    ],
)
def test_the_article_and_its_passive_must_be_one_plain_run_of_words(service, on, text):
    # The article does not head the subject of the passive in one clause: a run of words
    # that is no dependent of it, a comma, a semicolon or a finite verb: no cue.
    assert NOT_CONFIGURATION in configuration_reasons(service, text)


def test_the_article_cue_names_no_phrase_of_its_own():
    # The cue is assembled from the registry and the applied-step class: with no noun in
    # the registry there is no cue at all.
    class Bare:
        class_metadata: dict = {}  # noqa: RUF012

    assert article_terms(Bare()) == []
    assert article_subject_cue("Four specimens of slag were heated in Run A1.", Bare()) is False


@pytest.mark.parametrize("verb", ["allowed", "left"])
def test_ensuring_after_a_control_verb_is_not_a_purpose(verb):
    text = f"The burner was {verb} to ensure that the flow was increased."
    assert clause_cues.purpose_spans(text) == []


def test_ensuring_at_a_clause_start_is_a_purpose():
    text = "The oven was held at 120 C, to ensure that the drift was small."
    assert any("ensure that" in s for s in spans_text(text))
    assert any("ensure that" in s for s in spans_text("To ensure that it holds, we clamped it."))
