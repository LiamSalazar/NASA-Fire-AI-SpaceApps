"""Evidence-linked candidate terms and their conservative reconciliation; synthetic text."""

import pytest
from test_concept_staging import prepare
from test_document_extraction import service as _service
from test_document_extraction import submitted

from nasa_fire_ai.ingestion.document_extraction import extraction_semantic
from nasa_fire_ai.ingestion.semantic_candidates import (
    acronym_definitions,
    approved_vocabulary,
    reconcile,
    repeated_terms,
)

service = _service


@pytest.fixture
def vocabulary(service):
    return approved_vocabulary(extraction_semantic(service, submitted(service, "Run A1.\n")))


def test_a_defined_acronym_keeps_exactly_its_printed_long_form():
    text = "Tests used the Main Burner Valve (MBV) and then a spare valve (QX)."
    found = [(long, short) for long, short, *_ in acronym_definitions(text)]
    assert ("Main Burner Valve", "MBV") in found
    # Initials that do not spell the acronym define nothing.
    assert all(short != "QX" for _, short in found)


@pytest.mark.parametrize(
    ("label", "coverage", "term"),
    [
        ("flame spread", "COVERED", "FlameSpread"),
        # Metamorphic: case and a plural do not make another term.
        ("Flame Spreads", "COVERED", "FlameSpread"),
        # A qualified approved term is a question for review, never an equivalence.
        ("concurrent flame spread", "QUALIFIES", "FlameSpread"),
        ("impact energy", "UNCOVERED", None),
    ],
)
def test_reconciliation_is_conservative(vocabulary, label, coverage, term):
    found = reconcile(label, vocabulary)
    assert found["coverage"] == coverage and found.get("approved_term") == term


def test_repeated_fragments_that_are_not_terms_are_not_candidates():
    text = (
        "The seal material was cleaned and refurbished. The seal material was cleaned and "
        "refurbished. Searching for better seals. Searching for better seals."
    )
    terms = repeated_terms(text)
    assert "seal material" in terms
    assert not any("refurbished" in t or t.startswith("searching") for t in terms)


TWICE = (
    "II. Methods\nRun A1 used a porous radiative shield above the sample.\n"
    "The porous radiative shield was replaced after each run.\n"
)


def test_a_staged_concept_links_to_the_printed_term_it_names(service):
    result = prepare(service, [("class", "porous radiative shield")], text=TWICE)
    extraction = result["package"]["scientific_extraction"]
    (proposal,) = [p for p in extraction["ontology_extension_proposals"] if p["kind"] == "class"]
    assert proposal["source_candidate"].startswith("candidate-")
    candidate = next(
        c for c in extraction["semantic_candidates"] if c["id"] == proposal["source_candidate"]
    )
    assert candidate["evidence"] and candidate["coverage"] == "UNCOVERED"
    assert {"proposal": proposal["id"], "decision": "LINKED", "candidate": candidate["id"]} in (
        extraction["candidate_link_trace"]
    )


def test_a_term_printed_once_stays_staged_but_is_flagged_unlinked(service):
    # Metamorphic: the same concept, printed once, is not a term the document
    # establishes; it is kept for review with the flag, never dropped.
    result = prepare(service, [("class", "porous radiative shield")])
    extraction = result["package"]["scientific_extraction"]
    (proposal,) = [p for p in extraction["ontology_extension_proposals"] if p["kind"] == "class"]
    assert "source_candidate" not in proposal
    assert "NOT_LINKED_TO_A_PRINTED_SOURCE_TERM" in proposal["structural_validation"]["warnings"]


def test_only_a_final_plural_is_normalized():
    from nasa_fire_ai.ingestion.semantic_candidates import normalize

    assert normalize("Radiative Shields") == normalize("radiative shield")
    assert normalize("porous apparatus analysis glass") == "porous apparatus analysis glass"


def candidate_requests(service, monkeypatch, enabled):
    from test_document_extraction import client_for, entity
    from test_phase1_closure import _requests

    from nasa_fire_ai.config import Settings
    from nasa_fire_ai.ingestion.document_extraction import ExtractionBudget, Output

    monkeypatch.setenv("SCIENCE_CANDIDATE_CONTRACT", "1" if enabled else "0")
    text = TWICE + "The flame spread was brief. The flame spread was slow.\n"
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [entity(p, "a1", "A1", "ExperimentalRun", "Run A1 used")]
    client = client_for(o)
    service.prepare_scientific(
        p["id"],
        Settings(root=service.root),
        model_enabled=True,
        budget=ExtractionBudget(max_model_calls=8),
        client=client,
    )
    return [x for _prompt, x in _requests(client) if x["stage"] in {"identity", "propositions"}]


def test_the_candidate_contract_is_off_by_default(service, monkeypatch):
    payloads = candidate_requests(service, monkeypatch, enabled=False)
    assert payloads and not any("source_term_candidates" in x for x in payloads)


def test_the_request_offers_only_uncovered_or_qualifying_printed_terms(service, monkeypatch):
    payloads = candidate_requests(service, monkeypatch, enabled=True)
    offered = {c["printed"].lower(): c for x in payloads for c in x["source_term_candidates"]}
    assert "porous radiative shield" in offered
    assert offered["porous radiative shield"]["coverage"] == "UNCOVERED"
    # An approved term ("flame spread") is covered: it is never offered as a gap.
    assert "flame spread" not in offered
    assert all("source_term_contract" in x for x in payloads)
