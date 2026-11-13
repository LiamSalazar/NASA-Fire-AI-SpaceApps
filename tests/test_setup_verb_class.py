"""SCIENCE_CONTRACT_C2 set-up verbs as a referenced class (clause_cues.SETUP_VERBS):
VIM JCGM 200:2012 2.39 and 3.11 (calibrated, adjusted) and Levin 1993, English Verb
Classes and Alternations, class 9.1 (the putting verbs).

Synthetic text only (B8): an invented domain.
"""

import pytest
from test_contract_candidates import configuration_reasons
from test_document_extraction import service as _service

from nasa_fire_ai.ingestion import clause_cues

service = _service

NOT_CONFIGURATION = "CONFIGURATION_ROLE_NOT_ESTABLISHED_IN_ORIGINAL_PASSAGE"
MEMBERS = sorted(clause_cues.SETUP_VERBS)
DROPPED = ["switched", "connected"]


@pytest.fixture
def on(monkeypatch):
    monkeypatch.setenv("SCIENCE_PURPOSE_READER", "1")
    monkeypatch.setenv("SCIENCE_CONTRACT_C2", "1")
    return monkeypatch


def sentence(verb):
    return f"The zorvex cell of Run Q9 was {verb} on the quellin rail."


def test_the_class_is_the_referenced_members():
    assert set(MEMBERS) == {
        "calibrated",
        "adjusted",
        "placed",
        "positioned",
        "mounted",
        "installed",
        "set",
        "put",
        "arranged",
        "situated",
        "lodged",
    }


@pytest.mark.parametrize("verb", MEMBERS)
def test_a_member_as_a_passive_set_up_step_reads_as_configuration(service, on, verb):
    assert NOT_CONFIGURATION not in configuration_reasons(service, sentence(verb))


def test_the_cue_is_built_from_the_class():
    for verb in MEMBERS:
        assert clause_cues.SETUP_PASSIVE.count(verb) >= 1


@pytest.mark.parametrize("verb", DROPPED)
def test_a_dropped_verb_no_longer_reads_as_configuration(service, on, verb):
    assert NOT_CONFIGURATION in configuration_reasons(service, sentence(verb))


@pytest.mark.parametrize("verb", ["weighed", "examined", "observed", "tested"])
def test_a_non_set_up_passive_does_not(service, on, verb):
    assert NOT_CONFIGURATION in configuration_reasons(service, sentence(verb))


@pytest.mark.parametrize("a", MEMBERS)
@pytest.mark.parametrize("b", ["placed", "adjusted", "lodged"])
def test_swapping_one_member_for_another_keeps_the_result(service, on, a, b):
    assert configuration_reasons(service, sentence(a)) == configuration_reasons(
        service, sentence(b)
    )


def test_the_class_is_off_without_the_reader(service, monkeypatch):
    monkeypatch.setenv("SCIENCE_PURPOSE_READER", "0")
    monkeypatch.setenv("SCIENCE_CONTRACT_C2", "1")
    assert NOT_CONFIGURATION in configuration_reasons(service, sentence("lodged"))
