"""Structured provenance (SCIENCE_STRUCTURED_PROVENANCE): a data_provenance statement
counts only with its structure: a source entity (the registered Publication or Document
class, or a staged class under one of them) printed in the statement, a provenance
relation from the current study to that source (approved, or staged through the
existing proposed-term path, never approved here), and applicability. A statement
lacking the structure is held and counts 0. Off by default. Synthetic text."""

import copy

import pytest
from test_document_extraction import entity, submitted, support, validate
from test_document_extraction import service as _service

from nasa_fire_ai.evaluation.phase1_protocol import outcome
from nasa_fire_ai.ingestion.document_extraction import (
    PROPOSE_NEW_CLASS,
    PROPOSE_NEW_RELATION,
    PROVENANCE_EXAMPLE,
    Output,
    parse_model_output,
    stage_schema,
)

service = _service
V2 = "SCIENCE_STRUCTURED_PROVENANCE"
OWN = "Synthetic study"  # the package title: the document's own investigation
SOURCE = "Marlow panel survey"
TEXT = "The reference char depth values were obtained from the Marlow panel survey."
OTHER = "Corbin vendor note"
ASIDE = "A Corbin vendor note describes the same panels."
POINTER = "Table 3 lists the reference char depth values."
MENTION = "The Marlow panel survey is discussed in Section 4."
TERM = "obtainsDataFrom"


def flags(monkeypatch, *on):
    for name in (V2,):
        monkeypatch.delenv(name, raising=False)
    for name in on:
        monkeypatch.setenv(name, "1")


def build(
    service,
    text=TEXT,
    extra="",
    source=SOURCE,
    source_quote=None,
    source_study="cited",
    relate_to="src",
    relation_text=None,
    term=TERM,
    with_source=True,
    with_relation=True,
    role="data_provenance",
    section="II. Methods",
    statement_study="current",
    subject_class="Investigation",
    source_class="Publication",
    proposed_class=None,
):
    p = submitted(service, f"{OWN}\nII. Methods\n{text}\n{extra}\n")
    o = Output().model_dump()
    o["entities"] = [entity(p, "inv", OWN, subject_class, OWN)]
    if with_source:
        src = entity(p, "src", source, source_class, source_quote or text, study=source_study)
        if proposed_class:
            src["proposed_class"] = {"term": proposed_class, "parent": "Publication"}
        o["entities"].append(src)
    if extra and OTHER in extra:
        o["entities"].append(entity(p, "oth", OTHER, "Publication", extra, study="cited"))
    o["statements"] = [
        {
            "subjects": ["inv"],
            "text": text,
            "class_id": "Publication",
            "epistemic": role,
            "study": statement_study,
            "support": support(p, text),
        }
    ]
    if with_relation:
        o["relations"] = [
            {
                "subject": "inv",
                "relation": PROPOSE_NEW_RELATION,
                "proposed_relation": {"term": term, "parent": "NONE"},
                "object": relate_to,
                "support": support(p, relation_text or text),
            }
        ]
    return validate(service, p, o)


def statement(result):
    (r,) = [x for x in result["records"] if x["kind"] == "statements"]
    return r


def relation(result):
    (r,) = [x for x in result["records"] if x["kind"] == "relations"]
    return r


def missing(record):
    return set(record.get("provenance_structure_missing", []))


# ---------------------------------------------------------------- flags off


def test_flags_off_the_role_is_not_in_the_contract(monkeypatch):
    flags(monkeypatch)
    roles = stage_schema("propositions")["$defs"]["Statement"]["properties"]["epistemic"]["enum"]
    assert "data_provenance" not in roles
    result, errors = parse_model_output(
        '{"statements": [{"text": "x", "class_id": "Publication", "epistemic": "data_provenance",'
        ' "support": [{"evidence_id": "E1", "quote": "x", "start": 0}]}]}'
    )
    assert not result["statements"] and errors


# ---------------------------------------------------------------- flag on


def test_on_the_role_is_in_the_contract_with_only_the_new_flag(monkeypatch):
    flags(monkeypatch, V2)
    roles = stage_schema("propositions")["$defs"]["Statement"]["properties"]["epistemic"]["enum"]
    assert "data_provenance" in roles


# ---------------------------------------------------------------- positive


def test_a_source_entity_and_a_staged_relation_make_it_count(service, monkeypatch):
    flags(monkeypatch, V2)
    result = build(service)
    st, rel = statement(result), relation(result)
    assert st["status"] == "SOURCE_SUPPORTED", st["reasons"]
    structure = st["provenance_structure"]
    assert structure["relation_state"] == "STAGED"
    assert structure["source_class"] == "Publication"
    assert outcome([st]) == "COMPLETE_WITH_STAGED_EXTENSION"
    # The relation is staged for review, never approved vocabulary.
    assert rel["reasons"] == ["UNREGISTERED_RELATION"]
    assert rel["proposal_state"] == "PROPOSED_ONTOLOGY_EXTENSION"
    assert TERM not in service.semantic.relations
    assert any(
        p["kind"] == "relation" and p["term"] == TERM
        for p in result["ontology_extension_proposals"]
    )


# ---------------------------------------------------------------- negative


def test_the_statement_alone_is_held_and_counts_zero(service, monkeypatch):
    flags(monkeypatch, V2)
    st = statement(build(service, with_source=False, with_relation=False))
    assert st["status"] == "UNRESOLVED"
    assert "PROVENANCE_STRUCTURE_MISSING" in st["reasons"]
    assert {"source_entity", "relation"} <= missing(st)
    assert outcome([st]) == "INCOMPLETE"


def test_a_source_entity_without_a_relation_is_held(service, monkeypatch):
    flags(monkeypatch, V2)
    st = statement(build(service, with_relation=False))
    assert "PROVENANCE_STRUCTURE_MISSING" in st["reasons"]
    assert missing(st) == {"relation"}


def test_a_relation_to_a_source_not_printed_in_the_statement_does_not_count(service, monkeypatch):
    flags(monkeypatch, V2)
    st = statement(
        build(service, extra=ASIDE, relate_to="oth", relation_text=ASIDE, with_source=False)
    )
    assert "PROVENANCE_STRUCTURE_MISSING" in st["reasons"]
    assert "source_entity" in missing(st)


def test_a_source_of_the_current_study_is_not_a_source_of_its_data(service, monkeypatch):
    flags(monkeypatch, V2)
    st = statement(build(service, source_study="current"))
    assert "PROVENANCE_STRUCTURE_MISSING" in st["reasons"]
    assert "source_entity" in missing(st)


def test_a_staged_relation_without_provenance_wording_is_not_bound(service, monkeypatch):
    # The relation's own span names the source but says nothing about where data come
    # from: it is not entailed, so it stays held and the statement does not count.
    flags(monkeypatch, V2)
    result = build(service, extra=MENTION, relation_text=MENTION)
    assert relation(result)["proposal_state"] != "PROPOSED_ONTOLOGY_EXTENSION"
    assert "PROVENANCE_STRUCTURE_MISSING" in statement(result)["reasons"]


def test_a_pointer_is_still_never_provenance(service, monkeypatch):
    flags(monkeypatch, V2)
    st = statement(build(service, text=POINTER, with_source=False, with_relation=False))
    assert st["status"] == "REJECTED"
    assert "DATA_PROVENANCE_NOT_EXPLICIT_IN_SOURCE" in " ".join(st["reasons"])


# ---------------------------------------------------------------- metamorphic


def test_renaming_the_source_and_the_staged_term_keeps_the_structure(service, monkeypatch):
    flags(monkeypatch, V2)
    shapes = []
    for name, term in ((SOURCE, TERM), ("Ashby coupon archive", "drawsValuesFrom")):
        st = statement(build(service, text=TEXT.replace(SOURCE, name), source=name, term=term))
        s = copy.deepcopy(st.get("provenance_structure") or {})
        shapes.append((st["status"], s.get("relation_state"), s.get("source_class")))
    assert shapes[0] == shapes[1] == ("SOURCE_SUPPORTED", "STAGED", "Publication")


def test_the_same_sentence_as_documentary_context_stays_retained(service, monkeypatch):
    flags(monkeypatch, V2)
    st = statement(build(service, role="documentary_context"))
    assert outcome([st]) == "EVIDENCE_RETAINED"
    assert not {"provenance_structure", "provenance_structure_missing"} & set(st)


# ------------------------------------------------- review probes (all count 0)


def counts(result):
    st = statement(result)
    return outcome([st]) in {"COMPLETE", "COMPLETE_WITH_STAGED_EXTENSION"}


def nothing_counts(result):
    return not any(
        outcome([r]) in {"COMPLETE", "COMPLETE_WITH_STAGED_EXTENSION"}
        for r in result["records"]
        if r["kind"] in {"statements", "relations"}
    )


@pytest.mark.parametrize(
    ("text", "source"),
    [
        ("The char depth values were taken from Table 3.", "Table 3"),
        ("The char depth values were obtained from Figure 4 of this paper.", "Figure 4"),
        (
            "The char depth values were obtained with the method of Okafor et al. [4].",
            "Okafor et al. [4]",
        ),
        (
            "The char depth values were obtained from the method of Okafor et al.",
            "Okafor et al.",
        ),
    ],
)
def test_a_pointer_or_a_method_is_not_a_data_source(service, monkeypatch, text, source):
    flags(monkeypatch, V2)
    result = build(service, text=text, source=source)
    assert nothing_counts(result)


@pytest.mark.parametrize(
    ("text", "source"),
    [
        ("The char depth values were taken from the present report.", "present report"),
        ("The char depth values were taken from this paper.", "this paper"),
        (
            "The char depth values were taken from the Synthetic study report.",
            "Synthetic study report",
        ),
    ],
)
def test_the_document_itself_is_never_the_source_even_marked_cited(
    service, monkeypatch, text, source
):
    flags(monkeypatch, V2)
    result = build(service, text=text, source=source, source_study="cited")
    assert nothing_counts(result)


def test_a_cited_works_provenance_is_not_the_current_studys(service, monkeypatch):
    flags(monkeypatch, V2)
    text = "Okafor et al. [4] report that their char depth values were obtained from the Marlow panel survey."
    assert nothing_counts(build(service, text=text))


def test_a_cited_introduction_sentence_counts_neither_statement_nor_relation(service, monkeypatch):
    flags(monkeypatch, V2)
    text = (
        "In the earlier Corbin campaign [2], the char depth values were obtained from the "
        "Marlow panel survey."
    )
    result = build(service, text=text, section="I. Introduction")
    assert nothing_counts(result)
    assert "provenance_structure" not in statement(result)


def test_a_statement_marked_cited_does_not_count(service, monkeypatch):
    flags(monkeypatch, V2)
    assert nothing_counts(build(service, statement_study="cited"))


def test_a_non_experiment_subject_does_not_count(service, monkeypatch):
    flags(monkeypatch, V2)
    assert nothing_counts(build(service, subject_class="Publication"))


@pytest.mark.parametrize(
    "relation", ["belongsToInvestigation", "belongsToExperimentFamily", "hasMaterial"]
)
def test_an_approved_relation_is_never_the_provenance_relation(service, monkeypatch, relation):
    flags(monkeypatch, V2)
    p_text = TEXT
    p = submitted(service, f"{OWN}\nII. Methods\n{p_text}\n")
    o = Output().model_dump()
    o["entities"] = [
        entity(p, "inv", OWN, "Investigation", OWN),
        entity(p, "src", SOURCE, "Publication", p_text, study="cited"),
    ]
    o["statements"] = [
        {
            "subjects": ["inv"],
            "text": p_text,
            "class_id": "Publication",
            "epistemic": "data_provenance",
            "study": "current",
            "support": support(p, p_text),
        }
    ]
    o["relations"] = [
        {"subject": "inv", "relation": relation, "object": "src", "support": support(p, p_text)}
    ]
    out = validate(service, p, o)
    assert outcome([statement(out)]) != "COMPLETE"
    assert not counts(out)


# ------------------------------------------------- prompt example and staged class


def test_the_prompt_example_passes_the_validators_own_reader():
    from nasa_fire_ai.ingestion.statement_integrity import DATA_PROVENANCE

    assert DATA_PROVENANCE.search(PROVENANCE_EXAMPLE)
    assert SOURCE in PROVENANCE_EXAMPLE


def test_a_staged_source_class_binds_and_stays_staged(service, monkeypatch):
    flags(monkeypatch, V2)
    result = build(service, source_class=PROPOSE_NEW_CLASS, proposed_class="SurveyDataset")
    st = statement(result)
    assert st["status"] == "SOURCE_SUPPORTED", st["reasons"]
    assert st["provenance_structure"]["source_state"] == "STAGED"
    assert outcome([st]) == "COMPLETE_WITH_STAGED_EXTENSION"
    from nasa_fire_ai.ingestion.proposal_states import state_dimensions

    assert state_dimensions(st)["publication"] == "NOT_AUTHORIZED"
    assert st["provenance_structure"]["source_class"] == "SurveyDataset"
