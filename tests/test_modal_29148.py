"""SCIENCE_MODAL_29148: modal verbs read by their normative verbal forms.

ISO/IEC/IEEE 29148 and the NASA Systems Engineering Handbook (NASA/SP-2016-6105 Rev 2,
appendix C): "shall" (and "must") a requirement, "should" a recommendation, "may" a
permission, "will" a statement of fact or intent. ISO/IEC Directives Part 2 (clause 7)
also separates "can", possibility and capability, from "may", permission. So:

- "may be used / applied / employed" and "is permitted" are guidance (permission);
- "can ..." is capability: never guidance, never a permission;
- "may" reads as a hypothesis except where it is a permission;
- a permission, like a requirement, reports nothing done.

Synthetic text only (B8): an invented domain (concrete, seals, welds, ovens).
"""

import json

import pytest
from test_prompt_has_no_source_phrases import phrases

from nasa_fire_ai.ingestion import clause_cues
from nasa_fire_ai.ingestion import document_extraction as de
from nasa_fire_ai.ingestion.document_extraction import role_errors
from nasa_fire_ai.ingestion.scientific_facets import modality_review

FLAG = "SCIENCE_MODAL_29148"
GUIDANCE = "GUIDANCE_NOT_EXPLICIT_IN_SOURCE"
NOT_SUPPORTED = "MODALITY_NOT_SUPPORTED_BY_SOURCE"


@pytest.fixture
def on(monkeypatch):
    monkeypatch.setenv(FLAG, "1")
    return monkeypatch


def guidance_errors(text):
    return role_errors({"text": text, "epistemic": "guidance"})


# --- positive -------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "A thinner gasket may be used when the flange runs cold.",
        "A second primer may be applied on porous slabs.",
        "Two primers are permitted on porous slabs.",
        "Operators should vent the oven before opening it.",
    ],
)
def test_a_permission_or_a_recommendation_is_guidance(on, text):
    assert GUIDANCE not in guidance_errors(text)


def test_will_states_an_intent(on):
    assert modality_review("The cylinders will be cured for 28 days.", "intended") == ([], [])


def test_a_hedging_may_is_still_a_hypothesis(on):
    assert modality_review("The bond may weaken at low humidity.", "hypothetical") == ([], [])


@pytest.mark.parametrize(
    "text",
    [
        "A thinner gasket may be used when the flange runs cold.",
        "Two primers are permitted on porous slabs.",
    ],
)
def test_a_permission_reports_nothing_done(on, text):
    # Like "shall", a permission prescribes; it never reads as an executed step.
    assert clause_cues.execution(text) == "not_done"


# --- negative -------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "A thinner gasket can be employed when the flange runs cold.",
        "The fitted curve can be applied to estimate wall loss.",
        "The same clamp can be employed for the larger cylinders.",
        "The results can be applied to predict the remaining life of the seal.",
    ],
)
def test_can_is_capability_never_guidance(on, text):
    assert GUIDANCE in guidance_errors(text)


@pytest.mark.parametrize(
    "text",
    [
        "A thinner gasket may be used when the flange runs cold.",
        "A second primer may be applied on porous slabs.",
    ],
)
def test_a_permission_is_not_a_hypothesis(on, text):
    assert modality_review(text, "hypothetical")[0] == [NOT_SUPPORTED]


def test_a_done_use_is_still_not_guidance(on):
    assert GUIDANCE in guidance_errors("A thinner gasket was used on the cold flange.")


def test_a_permission_is_not_an_intention(on):
    assert modality_review("A second primer may be applied on porous slabs.", "intended")[0]


# --- metamorphic ----------------------------------------------------------------------


@pytest.mark.parametrize("verb", ["applied", "employed"])
def test_only_the_modal_decides_between_permission_and_capability(on, verb):
    may = f"A thinner gasket may be {verb} on cold flanges."
    can = f"A thinner gasket can be {verb} on cold flanges."
    assert GUIDANCE not in guidance_errors(may)
    assert GUIDANCE in guidance_errors(can)


@pytest.mark.parametrize(
    ("subject", "other"), [("A thinner gasket", "A softer washer"), ("Operators", "Technicians")]
)
def test_renaming_the_subject_keeps_the_reading(on, subject, other):
    for text in (
        f"{subject} may be used when the flange runs cold.",
        f"{subject} should vent the oven before opening it.",
        f"{subject} can be employed when the flange runs cold.",
    ):
        assert (GUIDANCE in guidance_errors(text)) == (
            GUIDANCE in guidance_errors(text.replace(subject, other))
        )


def test_the_same_may_is_a_hypothesis_or_a_permission_by_its_verb(on):
    hedged = "The seal may leak at low temperature."
    permitted = "A second seal may be used at low temperature."
    assert modality_review(hedged, "hypothetical") == ([], [])
    assert modality_review(permitted, "hypothetical")[0] == [NOT_SUPPORTED]
    assert GUIDANCE in guidance_errors(hedged)
    assert GUIDANCE not in guidance_errors(permitted)


def test_flag_on_and_off_differ_only_where_can_or_a_permission_is_printed(monkeypatch):
    unchanged = [
        "Operators should vent the oven before opening it.",
        "A thinner gasket was used on the cold flange.",
        "The cylinders will be cured for 28 days.",
        "The bond may weaken at low humidity.",
    ]
    for text in unchanged:
        before = {}
        for value in ("0", "1"):
            monkeypatch.setenv(FLAG, value)
            before[value] = (
                guidance_errors(text),
                modality_review(text, "hypothetical"),
                modality_review(text, "intended"),
            )
        assert before["0"] == before["1"], text


# --- the request: one dictionary, no source phrase -------------------------------------


def test_the_request_vocabulary_reads_the_same_dictionary(on):
    vocabulary = de.request_role_vocabulary()
    text = json.dumps(vocabulary["modal_verbs"], ensure_ascii=False)
    # "can" has its own entry (capability); it is never listed with the permission.
    assert not any(
        "can" in key.split() and "may" in key.split() for key in vocabulary["modal_verbs"]
    )
    assert "capability" in vocabulary["modal_verbs"]["can"]
    for modal in ("shall", "should", "may", "will", "can"):
        assert modal in text


def test_the_flag_is_on_by_default(monkeypatch):
    monkeypatch.delenv(FLAG, raising=False)
    assert de.request_role_vocabulary() is not de.ROLE_VOCABULARY
    assert "GUIDANCE_NOT_EXPLICIT_IN_SOURCE" in guidance_errors(
        "A steel clamp can hold the coupon edge."
    )


def test_the_request_vocabulary_is_unchanged_with_the_flag_off(monkeypatch):
    monkeypatch.setenv(FLAG, "0")
    assert de.request_role_vocabulary() == de.ROLE_VOCABULARY


def test_the_added_vocabulary_copies_no_target_quote(on):
    import glob

    quotes = []
    for path in glob.glob("artifacts/phase1_generalizable_ingestion/v4/*/source_reference.json"):
        with open(path, encoding="utf-8") as handle:
            quotes += [t["quote"] for t in json.load(handle)["targets"]]
    assert len(quotes) >= 124
    target = set().union(*(phrases(q) for q in quotes))
    text = json.dumps(de.request_role_vocabulary()["modal_verbs"], ensure_ascii=False)
    assert sorted(" ".join(p) for p in phrases(text) & target) == []
