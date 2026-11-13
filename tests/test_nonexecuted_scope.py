"""Non-executed scope (SCIENCE_NONEXECUTED_SCOPE): a derived value, or one the model reads
as proposed, intended or conditional, takes the study's own investigation as its scope,
as a planned or criterion value already does. On by default, "0" turns it off; synthetic text."""

import pytest
from test_document_extraction import entity, submitted, validate
from test_document_extraction import service as _service
from test_scientific_facets import only, quantity

from nasa_fire_ai.ingestion.document_extraction import Output

service = _service
OWN = "Synthetic study"
BASIS = "STUDY_OWN_NON_EXECUTED_VALUE_AT_INVESTIGATION_SCOPE"
FLAG = "SCIENCE_NONEXECUTED_SCOPE"


def basis_of(service, sentence, role, modality=None, section="III. Results", extra=()):
    tested = "Coupon K7 was tested in the burner.\n" if extra else ""
    p = submitted(service, f"{OWN}\n{section}\n{tested}{sentence}\n")
    o = Output().model_dump()
    o["entities"] = [entity(p, "inv", OWN, "Investigation", OWN), *[e(p) for e in extra]]
    o["quantities"] = [quantity(p, sentence, "inv", "gas temperature", "640", "K", role, modality)]
    record = only(validate(service, p, o)["records"], "quantities")
    return (record.get("scope_context") or {}).get("basis")


SENTENCE = "A compression estimate gave a gas temperature of 640 K."


def test_off_when_set_to_zero_a_derived_value_takes_no_study_scope(service, monkeypatch):
    monkeypatch.setenv(FLAG, "0")
    assert basis_of(service, SENTENCE, "derived_quantity") != BASIS


def test_on_by_default_a_derived_value_takes_the_study_scope(service, monkeypatch):
    monkeypatch.delenv(FLAG, raising=False)
    assert basis_of(service, SENTENCE, "derived_quantity") == BASIS


def test_on_a_derived_value_takes_the_study_scope(service, monkeypatch):
    monkeypatch.setenv(FLAG, "1")
    assert basis_of(service, SENTENCE, "derived_quantity") == BASIS


@pytest.mark.parametrize("section", ["I. Background"])
def test_background_text_stays_excluded(service, monkeypatch, section):
    # Metamorphic: the same derived value printed as background is not the study's own.
    monkeypatch.setenv(FLAG, "1")
    assert basis_of(service, SENTENCE, "derived_quantity", section=section) != BASIS


def test_a_measured_value_is_never_given_the_study_scope(service, monkeypatch):
    monkeypatch.setenv(FLAG, "1")
    assert (
        basis_of(service, "The probe read a gas temperature of 640 K.", "reported_quantity")
        != BASIS
    )


def test_a_narrower_subject_named_in_the_clause_blocks_it(service, monkeypatch):
    # Negative: the clause names a validated sample; the investigation is not the value's scope.
    monkeypatch.setenv(FLAG, "1")
    sentence = "A compression estimate gave Coupon K7 a gas temperature of 640 K."
    sample = lambda p: entity(p, "k7", "Coupon K7", "Sample", "Coupon K7 was tested")
    assert basis_of(service, sentence, "derived_quantity", extra=(sample,)) != BASIS
