"""SCIENCE_PURPOSE_READER, V3 of the test-article set-up cue: the cue holds when a noun of
the registry's Sample class is the HEAD of the subject of the passive of an applied step
(statement_integrity.APPLIED_STEP_VERBS) in the SAME clause. No count of words decides
it: a clause boundary, a semicolon, another finite verb or an intervening subordinate or
relative clause breaks the relation; modifiers, numerals and "of"-complements do not.

No syntactic parser is installed; clause_cues.passive_subject_heads approximates the
relation clause by clause with closed word classes (Huddleston and Pullum 2002, ch. 4, 5
and 16). The purpose forms keep V2's clause-start anchoring and its negatives.

Synthetic text only (B8): an invented domain (concrete, mortar, kilns, trays).
"""

import glob
import gzip
import json

import pytest
from test_contract_candidates import configuration_reasons
from test_document_extraction import service as _service
from test_new_prompt_text_b8 import long_phrases
from test_prompt_has_no_source_phrases import phrases

from nasa_fire_ai.ingestion import (
    clause_cues,
    statement_integrity,
    statement_validation,
)
from nasa_fire_ai.ingestion.document_extraction import article_subject_cue

service = _service

FLAG = "SCIENCE_PURPOSE_READER"
CHANGE = "CHANGING_OBSERVATION_IS_NOT_ESTABLISHED_CONFIGURATION"
NOT_CONFIGURATION = "CONFIGURATION_ROLE_NOT_ESTABLISHED_IN_ORIGINAL_PASSAGE"
V4 = "artifacts/phase1_generalizable_ingestion/v4"
NOUNS = ("specimens", "specimen", "samples", "sample")
VERBS = statement_integrity.APPLIED_STEP_VERBS


@pytest.fixture
def on(monkeypatch):
    monkeypatch.setenv(FLAG, "1")
    monkeypatch.setenv("SCIENCE_CONTRACT_C2", "1")
    return monkeypatch


def heads(text):
    return clause_cues.passive_subject_heads(text, NOUNS, VERBS)


# --- one clause: the number of words between head and passive never decides ------------

# The words between the noun and its auxiliary: 2, 5, 8 and 12 of them, made of
# modifiers, numerals and "of"/"from" complements only.
SEPARATIONS = {
    2: "of slag",
    5: "of the third cured pour",
    8: "of the third pour of grey mortar mix",
    12: "of the third pour from 12 kiln trays of grey mortar mix",
}
STEPS = ("heated", "exposed", "mounted", "tested")


def one_clause(between, verb):
    return f"Four specimens {between} were {verb} in Run A1."


def test_the_separations_are_what_they_say():
    for size, between in SEPARATIONS.items():
        assert len(between.split()) == size


@pytest.mark.parametrize("verb", STEPS)
def test_every_separation_inside_one_clause_decides_alike(verb):
    decisions = {size: heads(one_clause(b, verb)) for size, b in SEPARATIONS.items()}
    assert set(decisions.values()) == {True}, decisions


@pytest.mark.parametrize("verb", ("heated", "exposed"))
@pytest.mark.parametrize("size", sorted(SEPARATIONS))
def test_every_separation_states_a_configuration(service, on, size, verb):
    text = one_clause(SEPARATIONS[size], verb)
    assert NOT_CONFIGURATION not in configuration_reasons(service, text)


@pytest.mark.parametrize(
    "text",
    [
        # A purpose clause before the comma; the subject of the passive after it.
        (
            "In order to widen the margin, an extra 30 specimens from one lot of grey mortar "
            "were heated in steam and in dry air."
        ),
        "To widen the margin, 30 more specimens of one pour were exposed in Run A1.",
        # Numerals, a numbered label, a participle that opens a complement.
        "Specimens 3 to 6 of the second pour were heated in Run A1.",
        "Twelve samples cut from the kiln slab were mounted in Run A1.",
        # An enumeration line break inside the sentence is no clause boundary.
        "Six samples of the\nthird pour were\nheated in Run A1.",
    ],
)
def test_the_head_of_the_subject_is_read_across_any_number_of_dependents(text):
    assert heads(text)


def test_a_coordinator_starts_the_subject_anew():
    # Conservative: "and" may join two clauses, so the subject restarts after it and
    # "4" heads no subject of the class.
    assert not heads("Specimens 3 and 4 were heated in Run A1.")


# --- crossing a boundary changes the decision ------------------------------------------

BASE = "Four specimens of the third pour of grey mortar mix were heated in Run A1."
CROSSED = [
    "Four specimens of the third pour, which came from grey mortar mix, were heated in Run A1.",
    "Four specimens of the third pour; the kiln trays of grey mortar mix were heated in Run A1.",
    "Four specimens that the crew took from grey mortar mix were heated in Run A1.",
    "Four specimens of the third pour were weighed and the kiln trays were heated in Run A1.",
    "Four specimens of the third pour were weighed while the kiln trays were heated in Run A1.",
    "Four specimens of the third pour can rest and the kiln trays were heated in Run A1.",
]


def test_the_uncrossed_sentence_holds():
    assert heads(BASE)


@pytest.mark.parametrize("text", CROSSED)
def test_a_clause_boundary_or_another_finite_verb_breaks_the_relation(text):
    assert not heads(text)


@pytest.mark.parametrize("text", CROSSED)
def test_a_broken_relation_states_no_configuration(service, on, text):
    assert NOT_CONFIGURATION in configuration_reasons(service, text)


@pytest.mark.parametrize(
    "text",
    [
        # The noun sits in a complement or a compound: it is not the head.
        "The rack of the specimens was heated in Run A1.",
        "Specimen trays were heated in Run A1.",
        "Specimens a b c d e f g were heated in Run A1.",
    ],
)
def test_a_class_noun_that_is_not_the_head_gives_no_cue(service, on, text):
    assert not heads(text)
    assert NOT_CONFIGURATION in configuration_reasons(service, text)


@pytest.mark.parametrize("verb", ["weighed", "examined", "observed"])
def test_a_verb_outside_the_applied_steps_is_not_widened(verb):
    assert not heads(one_clause(SEPARATIONS[8], verb))


# --- V2 negatives kept: a control verb with an infinitive is no purpose ----------------

CONTROL = [
    "The kiln was allowed to establish and the draft was increased.",
    "The kiln was able to reach 900 C and the draft was increased.",
    "The slab was left to cool and the load was increased.",
]


@pytest.mark.parametrize("text", CONTROL)
def test_a_control_verb_with_an_infinitive_is_still_not_a_purpose(text):
    assert clause_cues.purpose_spans(text) == []
    assert clause_cues.strip_purpose(text) == text


@pytest.mark.parametrize("text", CONTROL)
def test_a_control_verb_still_does_not_strip_a_change_verb(service, on, text):
    assert CHANGE in configuration_reasons(service, text)


@pytest.mark.parametrize(
    "text",
    [
        "Four specimens were allowed to rest and the kiln was heated in Run A1.",
        "Four specimens were left to cool before the trays were heated in Run A1.",
        "Four specimens were able to dry, and the trays were heated in Run A1.",
    ],
)
def test_a_control_verb_does_not_lend_its_subject_to_a_later_passive(text):
    assert not heads(text)


# --- false configurations: a denied, conditional, cited or reported test --------------

NOT_RUN = [
    # A negated subject.
    "No specimens were heated in Run A1.",
    "Neither samples were exposed in Run A1.",
    # A clause that opens with if / unless / whether / that.
    "If specimens were heated the kiln logged it.",
    "Unless samples were exposed the rig stayed idle.",
    "Whether the specimens were heated is not recorded.",
    "That samples were exposed is not recorded.",
    # A cited test.
    "Similar specimens were heated by Okafor et al. [3].",
    "Similar specimens were heated in a kiln [3].",
    "Similar samples were exposed by Lindqvist in a hall.",
    # A reporting or requiring verb before the noun.
    "Okafor reported specimens were heated in a kiln.",
    "Earlier data show samples were heated to failure.",
    "The method requires specimens were exposed in a rack.",
    # A present passive is a rule, not a test that was run.
    "In routine practice, specimens are heated in a kiln.",
]


@pytest.mark.parametrize("text", NOT_RUN)
def test_a_denied_conditional_cited_or_reported_test_gives_no_cue(text):
    assert not heads(text)


@pytest.mark.parametrize("text", NOT_RUN)
def test_such_a_test_states_no_configuration(service, on, text):
    assert NOT_CONFIGURATION in configuration_reasons(service, text)


def test_the_same_sentences_without_the_blocking_word_still_hold():
    assert heads("Four specimens were heated in Run A1.")
    assert heads("Eight samples of slag were exposed in Run A1.")


# --- false purposes: a purpose ends at "and"/"but", needs its form, and no degree word ---

MAIN_CLAUSE_HIDDEN = [
    "The crew was attempting to hold the load but it increased to 5 kN.",
    "Slabs were dried in order to weigh them and the mass decreased by 4 g.",
    "The kiln was heated, to dry the slab and the mass decreased by 4 g.",
    "The load was held near 2 kN, to nearly 6 kN the load increased.",
    "In all runs, to varying degrees the load increased.",
    "The load was held near 2 kN, to about 6 kN the load increased.",
    "Slabs were ranked in order to the left of the kiln and the load increased.",
]


@pytest.mark.parametrize("text", MAIN_CLAUSE_HIDDEN)
def test_a_main_clause_change_is_not_hidden_by_a_false_purpose(service, on, text):
    assert CHANGE in configuration_reasons(service, text)


def test_a_purpose_ends_before_a_coordinator():
    text = "Slabs were dried in order to weigh them and the mass decreased by 4 g."
    assert clause_cues.strip_purpose(text).endswith("and the mass decreased by 4 g.")


def test_a_progressive_main_verb_is_no_participle_of_aiming():
    assert clause_cues.purpose_spans("The crew was attempting to hold the load.") == []
    assert clause_cues.purpose_spans("Aiming to hold the load, the crew left.")


def test_a_real_purpose_still_strips_its_change_verb(service, on):
    text = "Aiming to increase the load, the crew heated Run A1."
    assert CHANGE not in configuration_reasons(service, text)


# --- flags off: the V3 reader is never consulted ---------------------------------------

ALL_TEXTS = [one_clause(b, v) for b in SEPARATIONS.values() for v in STEPS] + [BASE, *CROSSED]


def _refuse(*_args, **_kwargs):
    raise AssertionError("the V3 reader ran with its flag off")


@pytest.mark.parametrize(
    "env", [{FLAG: "0", "SCIENCE_CONTRACT_C2": "1"}, {FLAG: "1", "SCIENCE_CONTRACT_C2": "0"}]
)
def test_flags_off_the_reader_is_never_called(service, monkeypatch, env):
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    before = [configuration_reasons(service, t) for t in ALL_TEXTS]
    # the caller (validate_statement) reads article_subject_cue from statement_validation
    monkeypatch.setattr(statement_validation, "article_subject_cue", _refuse)
    monkeypatch.setattr(clause_cues, "passive_subject_heads", _refuse)
    assert [configuration_reasons(service, t) for t in ALL_TEXTS] == before


@pytest.mark.parametrize("env", [{FLAG: "1", "SCIENCE_CONTRACT_C2": "1"}])
def test_the_patch_target_is_reached_with_the_flags_on(service, monkeypatch, env):
    # Canary for the test above: patching statement_validation.article_subject_cue must
    # reach the real caller, or "never called" would hold vacuously.
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    reached = []
    original = statement_validation.article_subject_cue

    def counted(*args, **kwargs):
        reached.append(1)
        return original(*args, **kwargs)

    monkeypatch.setattr(statement_validation, "article_subject_cue", counted)
    for text in ALL_TEXTS:
        configuration_reasons(service, text)
    assert reached


def test_with_no_class_noun_in_the_registry_there_is_no_cue():
    class Bare:
        class_metadata: dict = {}  # noqa: RUF012

    assert article_subject_cue(BASE, Bare()) is False


# --- B8: invented text only -------------------------------------------------------------


def _module_texts():
    return [
        *ALL_TEXTS,
        *CONTROL,
        *SEPARATIONS.values(),
        (
            "In order to widen the margin, an extra 30 specimens from one lot of grey mortar "
            "were heated in steam and in dry air."
        ),
        "Twelve samples cut from the kiln slab were mounted in Run A1.",
        "The rack of the specimens was heated in Run A1.",
    ]


def test_no_text_here_copies_a_frozen_target_quote():
    quotes = []
    for path in glob.glob(f"{V4}/*/source_reference.json"):
        with open(path, encoding="utf-8") as handle:
            quotes += [t["quote"] for t in json.load(handle)["targets"]]
    assert len(quotes) >= 124
    target = set().union(*(phrases(q) for q in quotes))
    found = {" ".join(p) for t in _module_texts() for p in phrases(t) & target}
    assert sorted(found) == []


def test_no_text_here_copies_a_phrase_of_the_development_documents():
    documents = set()
    for path in glob.glob(f"{V4}/independent_*/prepared_1.json.gz"):
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            package = json.load(handle)["package"]
        documents |= long_phrases("\n".join(e["text"] for e in package["evidence"]))
    assert documents
    found = {" ".join(p) for t in _module_texts() for p in long_phrases(t) & documents}
    assert sorted(found) == []
