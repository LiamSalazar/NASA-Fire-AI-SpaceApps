"""The three provenance classes (SCIENCE_STRUCTURED_PROVENANCE) read by class, not by list:
self-referring determiners, endophoric markers, and the structural rule that the label heads
the noun phrase after "from". Synthetic text."""

import pytest
from test_document_extraction import service as _service
from test_structured_provenance import V2, build, flags, nothing_counts, statement

from nasa_fire_ai.ingestion.clause_cues import (
    ENDOPHORIC_MARKER,
    SELF_DEIXIS,
    heads_object_of_from,
)
from nasa_fire_ai.ingestion.document_extraction import provenance_clause_ok, self_source

service = _service


def selfish(label):
    return self_source("k", {"k": {"label": label, "class_id": "Publication", "study": "cited"}})


# ---------------------------------------------------------------- positive


@pytest.mark.parametrize(
    "text",
    [
        "Values were obtained from the Quessel ledger.",
        "Values were obtained from the quellin and zorvex ledger.",
        "Values were obtained from a large Marlow panel survey.",
    ],
)
def test_a_noun_phrase_head_after_from_is_a_source(text):
    label = text.rsplit("from ", 1)[1].rstrip(".")
    label = label.split(" ", 1)[1] if label.startswith(("the ", "a ")) else label
    assert provenance_clause_ok(label.replace("large ", ""), text)


def test_the_label_may_be_the_whole_phrase_after_from():
    assert provenance_clause_ok("Quessel ledger", "Values were obtained from the Quessel ledger.")


@pytest.mark.parametrize(
    "label",
    [
        "our earlier campaign",
        "this zorvex",
        "the present zorvex",
        "present zorvex",
        "the current quellin rig",
        "Our arden bench",
    ],
)
def test_a_self_referring_determiner_makes_the_label_the_document_itself(label):
    assert SELF_DEIXIS.search(label)
    assert selfish(label)


@pytest.mark.parametrize(
    "label", ["Table 4", "Figure 2", "Fig. 3", "Section 4", "Chapter 2", "Page 7", "pp. 12"]
)
def test_endophoric_markers_are_pointers(label):
    assert ENDOPHORIC_MARKER.search(label)
    assert not provenance_clause_ok(label, f"Values were obtained from {label}.")


# ---------------------------------------------------------------- negative


@pytest.mark.parametrize(
    ("label", "text"),
    [
        ("Arden", "Values were obtained from the method of Arden."),
        ("Orlan rig", "Values were obtained from tests using the Orlan rig."),
        ("Quessel ledger", "Values were obtained from the data in the Quessel ledger."),
        ("Quessel ledger", "Values were obtained from records kept by the Quessel ledger."),
        ("Quessel ledger", "Values were obtained from tests during the Quessel ledger."),
    ],
)
def test_a_dependent_label_is_not_a_source(label, text):
    assert not provenance_clause_ok(label, text)


@pytest.mark.parametrize(
    "label",
    ["these tests", "the Marlow panel survey", "Presently ledger", "p-type quellin", "ch4 table"],
)
def test_other_labels_are_neither_self_nor_pointer(label):
    assert not SELF_DEIXIS.search(label)
    assert not ENDOPHORIC_MARKER.search(label)


# ---------------------------------------------------------------- metamorphic


@pytest.mark.parametrize("adjectives", ["", "large ", "old quellin ", "large old quellin "])
def test_adjectives_between_from_and_the_label_change_nothing(adjectives):
    text = f"Values were obtained from the {adjectives}Quessel ledger."
    assert provenance_clause_ok("Quessel ledger", text)
    assert heads_object_of_from(f"the {adjectives}")


@pytest.mark.parametrize("prep", ["of", "in", "during", "upon", "against", "toward", "with"])
def test_a_preposition_before_the_label_flips_it_to_rejected(prep):
    text = f"Values were obtained from the data {prep} the Quessel ledger."
    assert not provenance_clause_ok("Quessel ledger", text)


@pytest.mark.parametrize("participle", ["using", "following", "based", "taken", "recorded"])
def test_a_participle_before_the_label_flips_it_to_rejected(participle):
    text = f"Values were obtained from tests {participle} the Quessel ledger."
    assert not provenance_clause_ok("Quessel ledger", text)


@pytest.mark.parametrize("det", ["this", "our", "the present", "the current", "present"])
def test_every_determiner_of_the_class_gives_the_same_reading(det):
    assert selfish(f"{det} quellin ledger")


@pytest.mark.parametrize(
    "noun", ["figure", "table", "section", "chapter", "page", "example", "part"]
)
def test_every_noun_of_the_marker_class_is_a_pointer(noun):
    assert ENDOPHORIC_MARKER.search(f"{noun.upper()} 3")
    assert ENDOPHORIC_MARKER.search(f"{noun.capitalize()}s 3")


# ---------------------------------------------------------------- end to end


def test_the_invented_ledger_counts_end_to_end(service, monkeypatch):
    flags(monkeypatch, V2)
    result = build(
        service,
        text="The probe values were obtained from the Quessel ledger.",
        source="Quessel ledger",
    )
    assert statement(result)["status"] == "SOURCE_SUPPORTED"


@pytest.mark.parametrize(
    ("text", "source"),
    [
        ("The probe values were obtained from the present zorvex.", "present zorvex"),
        ("The probe values were obtained from our earlier campaign.", "our earlier campaign"),
        ("The probe values were obtained from the method of Arden.", "Arden"),
        ("The probe values were obtained from tests using the Orlan rig.", "Orlan rig"),
    ],
)
def test_self_and_dependent_labels_count_zero_end_to_end(service, monkeypatch, text, source):
    flags(monkeypatch, V2)
    assert nothing_counts(build(service, text=text, source=source))
