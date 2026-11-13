"""Role vocabulary (SCIENCE_ROLE_VOCABULARY) and role check (SCIENCE_ROLE_CHECK): the roles
defined from open ontologies and modal-verb conventions travel with the propositions request,
and a proposal held or rejected for its role is asked for once more with a closed list of
roles; the answers are validated as any proposal. On by default, "0" turns each off;
synthetic text."""

import json
from types import SimpleNamespace
from unittest.mock import Mock

from test_document_extraction import service as _service
from test_document_extraction import submitted

from nasa_fire_ai.config import Settings
from nasa_fire_ai.ingestion.clause_cues import NORMATIVE_MODALS
from nasa_fire_ai.ingestion.document_extraction import (
    ROLE_OPTIONS,
    ROLE_VOCABULARY,
    STAGES,
    ExtractionBudget,
    request_role_vocabulary,
)

service = _service
TEXT = "II. Methods\nRun A1 burned the liner.\nThe liner was coated with paste.\n"


def run(service, monkeypatch, flags=()):
    monkeypatch.setenv("SCIENCE_ONTOLOGY_CONTEXT", "0")
    for flag in ("SCIENCE_ROLE_VOCABULARY", "SCIENCE_ROLE_CHECK"):
        monkeypatch.setenv(flag, "1" if flag in flags else "0")
    p = submitted(service, TEXT)
    payloads = []

    def respond(**kwargs):
        payload = json.loads(kwargs["messages"][1]["content"])
        payloads.append(payload)
        result = {k: [] for k in STAGES[payload["stage"]]}
        if payload["stage"] == "identity":
            anchor = next(a["id"] for a in payload["source_anchors"] if "Run A1" in a["quote"])
            result["entities"] = [
                {
                    "key": "a1",
                    "label": "A1",
                    "class_id": "ExperimentalRun",
                    "study": "current",
                    "support": [anchor],
                }
            ]
        if payload["stage"] == "propositions" and "role_check" not in payload:
            # A done step typed as a plan: rejected for its role.
            anchor = next(a["id"] for a in payload["source_anchors"] if "coated" in a["quote"])
            known = [k["key"] for k in payload["known_entities"] if k["label"] == "A1"]
            result["statements"] = [
                {
                    "anchor": anchor,
                    "epistemic": "planned_activity",
                    "subjects": known,
                    "study": "current",
                }
            ]
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=json.dumps(result)), finish_reason="stop"
                )
            ],
            usage=None,
        )

    client = Mock()
    client.client.with_options.return_value.chat.completions.create.side_effect = respond
    service.prepare_scientific(
        p["id"],
        Settings(root=service.root),
        model_enabled=True,
        budget=ExtractionBudget(max_model_calls=40),
        client=client,
    )
    return payloads


def test_off_when_set_to_zero(service, monkeypatch):
    payloads = run(service, monkeypatch)
    assert not any(k in p for p in payloads for k in ("role_vocabulary", "role_check"))


def test_on_by_default(service, monkeypatch):
    for flag in ("SCIENCE_ROLE_VOCABULARY", "SCIENCE_ROLE_CHECK"):
        monkeypatch.delenv(flag, raising=False)
    monkeypatch.setenv("SCIENCE_MODAL_29148", "0")
    monkeypatch.setenv("SCIENCE_ONTOLOGY_CONTEXT", "0")
    # A distinct package: the same text would restore the earlier one.
    p = submitted(service, TEXT + "Run 2.\n")
    payloads = []

    def respond(**kwargs):
        payload = json.loads(kwargs["messages"][1]["content"])
        payloads.append(payload)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=json.dumps({k: [] for k in STAGES[payload["stage"]]})
                    ),
                    finish_reason="stop",
                )
            ],
            usage=None,
        )

    client = Mock()
    client.client.with_options.return_value.chat.completions.create.side_effect = respond
    service.prepare_scientific(
        p["id"],
        Settings(root=service.root),
        model_enabled=True,
        budget=ExtractionBudget(max_model_calls=40),
        client=client,
    )
    propositions = [x for x in payloads if x["stage"] == "propositions"]
    assert propositions and all(x["role_vocabulary"] == ROLE_VOCABULARY for x in propositions)


def test_the_vocabulary_cites_its_sources_and_travels_with_propositions(service, monkeypatch):
    monkeypatch.setenv("SCIENCE_MODAL_29148", "0")
    payloads = run(service, monkeypatch, flags=("SCIENCE_ROLE_VOCABULARY",))
    propositions = [p for p in payloads if p["stage"] == "propositions"]
    assert propositions and all(p["role_vocabulary"] == ROLE_VOCABULARY for p in propositions)
    assert any("29148" in s for s in ROLE_VOCABULARY["sources"])
    assert any("IAO" in s for s in ROLE_VOCABULARY["sources"])


def test_the_modal_reading_sends_the_one_normative_dictionary(service, monkeypatch):
    monkeypatch.setenv("SCIENCE_MODAL_29148", "1")
    payloads = run(service, monkeypatch, flags=("SCIENCE_ROLE_VOCABULARY",))
    propositions = [p for p in payloads if p["stage"] == "propositions"]
    sent = request_role_vocabulary()
    assert sent is not ROLE_VOCABULARY and sent["modal_verbs"] == NORMATIVE_MODALS
    assert propositions and all(p["role_vocabulary"] == sent for p in propositions)
    assert any("29148" in s for s in sent["sources"])


def test_the_request_vocabulary_is_unchanged_with_the_modal_reading_off(monkeypatch):
    monkeypatch.setenv("SCIENCE_MODAL_29148", "0")
    assert request_role_vocabulary() is ROLE_VOCABULARY


def test_a_proposal_rejected_for_its_role_is_asked_with_a_closed_list(service, monkeypatch):
    payloads = run(service, monkeypatch, flags=("SCIENCE_ROLE_CHECK",))
    asked = [p for p in payloads if "role_check" in p]
    assert asked and all(p["role_options"] == ROLE_OPTIONS for p in asked)
    items = [i for p in asked for i in p["role_check"]]
    assert any("coated" in i["printed"] for i in items)
    assert all("role_check_contract" in p for p in asked)
    # The item says what was proposed; the lists include modalities and studies.
    assert all(i["proposed"]["epistemic"] == "planned_activity" for i in items)
    assert all(p["role_modalities"] and p["role_studies"] for p in asked)
    assert {"open_question", "tentative_interpretation"} <= set(ROLE_OPTIONS)
