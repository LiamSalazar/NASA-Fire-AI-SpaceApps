"""Which printed terms a window offers the model under the candidate contract; synthetic."""

import pytest
from test_document_extraction import service as _service
from test_document_extraction import submitted
from test_semantic_candidates import candidate_requests

from nasa_fire_ai.ingestion.document_extraction import extraction_semantic
from nasa_fire_ai.ingestion.semantic_candidates import (
    approved_vocabulary,
    candidate_inventory,
    reconcile,
    window_candidates,
)

service = _service


@pytest.fixture
def vocabulary(service):
    return approved_vocabulary(extraction_semantic(service, submitted(service, "Run A1.\n")))


def inventory_of(service, text):
    p = submitted(service, text)
    return p, candidate_inventory(p, {"detected_tables": []}, extraction_semantic(service, p))


def members(text):
    return [{"evidence_id": "e", "start": 0, "end": len(text), "text": text}]


def test_a_window_offers_the_terms_it_prints_most_not_the_first_in_the_alphabet(service):
    # Fifty terms printed once before the window and once in it; the window's own
    # term, late in the alphabet, printed three times.
    filler = "".join(f"The {a}{b}ite rod.\n" for a in "abcde" for b in "abcdefghij")
    local = (
        filler + "The zircon baffle cooled. The zircon baffle cracked. The zircon baffle shook.\n"
    )
    _, inventory = inventory_of(service, "II. Methods\n" + filler + local)
    chosen, eligible = window_candidates(inventory, members(local), limit=5)
    assert eligible > 5
    assert "zircon baffle" in [c["label"].lower() for c in chosen]


def test_a_term_printed_all_through_the_document_reaches_a_late_window(service):
    early = "The cobalt liner glowed. " * 6
    late = "Later the cobalt liner was cut."
    _, inventory = inventory_of(service, "II. Methods\n" + early + "\n" + late + "\n")
    chosen, _ = window_candidates(inventory, members(late))
    assert "cobalt liner" in [c["label"].lower() for c in chosen]


def test_a_window_offers_nothing_it_does_not_print(service):
    _, inventory = inventory_of(service, "II. Methods\nThe cobalt liner glowed. " * 2)
    chosen, eligible = window_candidates(inventory, members("Run A1 burned."))
    assert chosen == [] and eligible == 0


def structured_inventory(service, text):
    from nasa_fire_ai.ingestion.document_structure import structure

    p = submitted(service, text)
    return candidate_inventory(p, structure(p, service.root), extraction_semantic(service, p))


@pytest.mark.parametrize(
    "text, label",
    [
        # A word ending in -ed is not a verb form ("speed", "infrared").
        ("The flame speed rose. The flame speed fell. Flames slowed.", "flame speed"),
        ("The infrared camera ran. The infrared camera stopped. It scored.", "infrared camera"),
        # A plural is not a verb because the document prints its past form.
        ("The impact tests ran. Two impact tests passed. Each was tested.", "impact tests"),
        ("The test conditions held. The test conditions varied. It was tested.", "test conditions"),
        ("The heat flux rose. The heat flux fell. The rod heated.", "heat flux"),
        (
            "The flammability limit was low. The flammability limit held. Flow limited it.",
            "flammability limit",
        ),
        # A capitalized material printed only capitalized is a term, not a name.
        ("The Duroflex Gasket swelled. The Duroflex Gasket burned.", "duroflex gasket"),
    ],
)
def test_a_term_is_offered_whatever_its_form(service, text, label):
    inventory = structured_inventory(service, "Abstract\nA study.\n2. Methods\n" + text + "\n")
    chosen, _ = window_candidates(inventory, members(text))
    assert label in [c["label"].lower() for c in chosen]


FRONT = (
    "Synthetic Burner Study\n"
    "Jane Q. Morrow\nGlenwood Combustion Laboratory, Ridgefield, OH 44000\n"
    "Pavel Ostrin\nGlenwood Combustion Laboratory, Ridgefield, OH 44000\n"
)
BODY = "The cobalt liner glowed. The cobalt liner was cut.\n"
BACK = (
    "References\n"
    "[1] Morrow, J., Burner tests, Annals of Synthetic Combustion, 1999.\n"
    "[2] Ostrin, P., Liner tests, Annals of Synthetic Combustion, 2001.\n"
)


@pytest.mark.parametrize("opening", ["Abstract\nA study.\n", "1. Introduction\nA study.\n"])
def test_a_sequence_printed_only_in_the_byline_or_the_references_is_not_offered(service, opening):
    text = FRONT + opening + "2. Methods\n" + BODY + BACK
    inventory = structured_inventory(service, text)
    # Even a window that holds the front matter and the reference list.
    chosen, _ = window_candidates(inventory, members(text))
    offered = [c["label"].lower() for c in chosen]
    assert "cobalt liner" in offered
    assert not any(word in o for o in offered for word in ("glenwood", "ridgefield", "annals"))


def test_the_same_sequence_printed_in_the_body_is_offered(service):
    body = BODY + "Glenwood Combustion Laboratory built the rig.\n"
    text = FRONT + "Abstract\nA study.\n2. Methods\n" + body + BACK
    inventory = structured_inventory(service, text)
    chosen, _ = window_candidates(inventory, members(body))
    assert "glenwood combustion laboratory" in [c["label"].lower() for c in chosen]


def test_a_document_without_an_abstract_or_introduction_heading_has_no_front_matter(service):
    text = "Glenwood Combustion Laboratory\n2. Methods\nGlenwood Combustion Laboratory ran it.\n"
    inventory = structured_inventory(service, text)
    chosen, _ = window_candidates(inventory, members(text))
    assert "glenwood combustion laboratory" in [c["label"].lower() for c in chosen]


def test_an_unlabeled_abstract_before_the_introduction_is_body(service):
    abstract = "A rig for the zircon baffle is described, and the zircon baffle is cut.\n"
    text = FRONT + abstract + "1. Introduction\nA study.\n" + BACK
    inventory = structured_inventory(service, text)
    chosen, _ = window_candidates(inventory, members(text))
    offered = [c["label"].lower() for c in chosen]
    assert "zircon baffle" in offered
    assert not any("glenwood" in o or "ridgefield" in o for o in offered)


def test_a_nomenclature_list_before_the_introduction_is_body(service):
    listing = (
        "Symbols and Nomenclature\nZBR\n= Zircon Baffle Ring\nZBR-2\n= Zircon Baffle Ring, second\n"
    )
    text = FRONT + listing + "1. Introduction\nA study.\n" + BACK
    inventory = structured_inventory(service, text)
    chosen, _ = window_candidates(inventory, members(text))
    assert "zircon baffle ring" in [c["label"].lower() for c in chosen]


def test_a_capitalized_term_whose_words_the_document_also_prints_in_lowercase_is_kept(service):
    text = "The Control Module failed. The Control Module was reset. Control of the module held."
    _, inventory = inventory_of(service, "II. Methods\n" + text + "\n")
    chosen, _ = window_candidates(inventory, members(text))
    assert "control module" in [c["label"].lower() for c in chosen]


@pytest.mark.parametrize(
    ("label", "coverage", "term"),
    [
        # A one-word query term never makes a longer label a qualified form.
        ("nozzle tests", "UNCOVERED", None),
        # A head that names no approved term.
        ("energy required", "UNCOVERED", None),
        # The approved term named in full still qualifies.
        ("concurrent flame spread", "QUALIFIES", "FlameSpread"),
        ("porous material", "QUALIFIES", "Material"),
    ],
)
def test_qualification_needs_the_approved_term_named_in_full(vocabulary, label, coverage, term):
    found = reconcile(label, vocabulary)
    assert found["coverage"] == coverage and found.get("approved_term") == term


@pytest.mark.parametrize("head", ["flame speed", "infrared camera", "heat flux"])
def test_a_head_qualifies_whatever_its_form(head):
    # A synthetic vocabulary whose terms end in -ed or have a printed past form.
    vocabulary = {head: ("property", "Term", True)}
    found = reconcile("upward " + head, vocabulary)
    assert found["coverage"] == "QUALIFIES" and found["approved_term"] == "Term"


def test_the_request_names_the_kind_of_term_qualified_and_carries_no_unused_id(
    service, monkeypatch
):
    payloads = candidate_requests(service, monkeypatch, enabled=True)
    offered = [c for x in payloads for c in x["source_term_candidates"]]
    assert offered and all("id" not in c for c in offered)
    assert all(c.get("qualifies_kind") for c in offered if c["coverage"] == "QUALIFIES")
    assert all("CamelCase" in x["source_term_contract"] for x in payloads)


def test_each_window_records_how_many_terms_it_had_before_the_cut(service, monkeypatch):
    from test_document_extraction import client_for, entity

    from nasa_fire_ai.config import Settings
    from nasa_fire_ai.ingestion.document_extraction import ExtractionBudget, Output

    monkeypatch.setenv("SCIENCE_CANDIDATE_CONTRACT", "1")
    text = "II. Methods\nThe cobalt liner glowed. The cobalt liner was cut. Run A1 used it.\n"
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [entity(p, "a1", "A1", "ExperimentalRun", "Run A1 used")]
    result = service.prepare_scientific(
        p["id"],
        Settings(root=service.root),
        model_enabled=True,
        budget=ExtractionBudget(max_model_calls=8),
        client=client_for(o),
    )

    def outcomes(node):
        if isinstance(node, dict):
            if "segment_id" in node and "stage" in node:
                yield node
            for value in node.values():
                yield from outcomes(value)
        elif isinstance(node, list):
            for value in node:
                yield from outcomes(value)

    counted = [
        x["source_term_candidates"]
        for x in outcomes(result["package"])
        if x["stage"] in {"identity", "propositions"} and "source_term_candidates" in x
    ]
    assert counted and all(c["eligible"] >= c["sent"] >= 1 for c in counted)


def test_a_line_printed_on_every_page_is_page_furniture_not_body():
    from nasa_fire_ai.ingestion.semantic_candidates import in_body

    footer = "Annual Meeting of the Synthetic Combustion Society"
    texts = {f"p{i}": f"The cobalt liner held on page {i}.\n{footer}\n" for i in range(4)}
    document = {
        "segments": [
            {
                "evidence_id": e,
                "source_id": "s",
                "start": 0,
                "end": len(t),
                "section": "II. Methods",
            }
            for e, t in texts.items()
        ]
    }

    def at(evidence_id, needle):
        start = texts[evidence_id].index(needle)
        return {"evidence_id": evidence_id, "start": start, "end": start + len(needle)}

    assert not in_body(at("p2", "Synthetic Combustion Society"), document, texts)
    assert in_body(at("p2", "cobalt liner"), document, texts)
    # A line on three of eight pages (a table cell, a repeated label) is body.
    texts["p0"] = texts["p1"] = "The cobalt liner held.\nSoot Mass\n"
    texts["p2"], texts["p3"] = "Soot Mass\n", "Nothing.\n"
    texts.update({f"q{i}": "Other page.\n" for i in range(4)})
    eight = {
        "segments": [
            {"evidence_id": e, "source_id": "s", "start": 0, "end": len(t), "section": "III."}
            for e, t in texts.items()
        ]
    }
    assert in_body(at("p2", "Soot Mass"), eight, texts)
