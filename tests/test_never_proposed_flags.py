"""Environment subjects (SCIENCE_ENVIRONMENT_SUBJECTS) and materials inside products
(SCIENCE_PRODUCT_MATERIALS): what the
model is asked changes only with each flag on. Off by default; synthetic text."""

import json
from types import SimpleNamespace
from unittest.mock import Mock

from test_document_extraction import service as _service
from test_document_extraction import submitted

from nasa_fire_ai.config import Settings
from nasa_fire_ai.ingestion.document_extraction import (
    ENVIRONMENT_VALUE_ROLES,
    STAGES,
    ExtractionBudget,
)

service = _service
FLAGS = ("SCIENCE_ENVIRONMENT_SUBJECTS", "SCIENCE_PRODUCT_MATERIALS")
TEXT = (
    "II. Methods\nSample S1 was tested in the burner.\n"
    "Sample S1 was tested in the burner with the Gamma paste.\n"
)
NEW_KEYS = (
    "environment_identity_contract",
    "environment_value_roles",
    "product_material_contract",
)


def run(
    service,
    monkeypatch,
    flags=(),
    text=TEXT,
    relate=False,
    names=("Sample S1", "Gamma paste"),
    systems=None,
):
    sample, material = sorted(names, key=lambda n: not n.startswith("Sample"))
    for flag in FLAGS:
        monkeypatch.delenv(flag, raising=False)
    for flag in flags:
        monkeypatch.setenv(flag, "1")
    p = submitted(service, text)
    payloads = []

    def respond(**kwargs):
        payload = json.loads(kwargs["messages"][1]["content"])
        payloads.append(payload)
        if systems is not None:
            systems.append(kwargs["messages"][0]["content"])
        result = {k: [] for k in STAGES[payload["stage"]]}
        anchors = {a["quote"]: a["id"] for a in payload.get("source_anchors", [])}
        used = next((i for q, i in anchors.items() if material.split()[0] in q), None)
        tested = next((i for q, i in anchors.items() if "was tested" in q), None)
        if payload["stage"] == "identity" and payload.get("focus") is None and used:
            result["entities"] = [
                {
                    "key": "a1",
                    "label": sample,
                    "class_id": "Sample",
                    "study": "current",
                    "support": [tested or used],
                },
                {
                    "key": "g",
                    "label": material,
                    "class_id": "Material",
                    "study": "current",
                    "support": [used],
                },
            ]
        if payload["stage"] == "propositions" and used:
            known = {k["label"]: k["key"] for k in payload["known_entities"]}
            if sample in known:
                result["statements"] = [
                    {
                        "anchor": used,
                        "epistemic": "experimental_configuration",
                        "subjects": [known[sample]],
                        "study": "current",
                    }
                ]
        if payload["stage"] == "relationships" and relate and used:
            known = {k["label"]: k["key"] for k in payload["known_entities"]}
            if {sample, material} <= set(known):
                result["relations"] = [
                    {
                        "subject": known[sample],
                        "relation": "hasMaterial",
                        "object": known[material],
                        "support": [used],
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
        budget=ExtractionBudget(max_model_calls=60),
        client=client,
    )
    return payloads


def test_off_by_default_nothing_new_is_asked(service, monkeypatch):
    payloads = run(service, monkeypatch)
    assert not any(k in p for p in payloads for k in NEW_KEYS)


def test_environment_subjects_travel_with_identity_and_propositions(service, monkeypatch):
    payloads = run(service, monkeypatch, flags=("SCIENCE_ENVIRONMENT_SUBJECTS",))
    identity = [p for p in payloads if p["stage"] == "identity"]
    propositions = [p for p in payloads if p["stage"] == "propositions"]
    assert identity and all("environment_identity_contract" in p for p in identity)
    assert propositions and all(
        p["environment_value_roles"] == ENVIRONMENT_VALUE_ROLES for p in propositions
    )
    assert not any("product_material_contract" in p for p in payloads)


def test_product_materials_travel_with_identity_only(service, monkeypatch):
    payloads = run(service, monkeypatch, flags=("SCIENCE_PRODUCT_MATERIALS",))
    assert all(("product_material_contract" in p) == (p["stage"] == "identity") for p in payloads)
