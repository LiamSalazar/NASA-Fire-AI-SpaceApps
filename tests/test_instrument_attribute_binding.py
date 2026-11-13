"""Scientific component descriptors cannot borrow each other's categorical facets."""

from types import SimpleNamespace

import pytest

from nasa_fire_ai.services.semantic_support import verify_paraphrase


def verify(text, modes=("spectral", "thermal")):
    original = (
        f"The setup used an encoded {modes[0]} detector and a continuous {modes[1]} detector."
    )
    descriptors = [
        {
            "id": "first",
            "attributes": {
                "instrumentCategory": "detector",
                "signalFormat": "encoded",
                "acquisitionMode": modes[0],
            },
        },
        {
            "id": "second",
            "attributes": {
                "instrumentCategory": "detector",
                "signalFormat": "continuous",
                "acquisitionMode": modes[1],
            },
        },
    ]
    registry = SimpleNamespace(
        resolve=lambda eid: {"text": original},
        scientific_instruments={"page": descriptors},
    )
    anchor = {
        "support_id": "source",
        "text": original,
        "spans": [{"evidence_id": "page", "text": original}],
        "category": "DOCUMENTARY",
        "epistemic_type": "documentary_content",
        "conditions": [],
    }
    return verify_paraphrase(
        text, [anchor], registry, SimpleNamespace(check=lambda p, h: {"supported": True})
    )


@pytest.mark.parametrize(
    "text",
    [
        "The setup used an encoded thermal detector.",
        "The detector provided thermal encoded data.",
        "A continuous spectral detector was present.",
    ],
)
def test_cross_component_joint_descriptors_fail_even_if_nli_entails(text):
    result = verify(text)
    assert not result["supported"]
    assert any("not jointly established" in error for error in result["errors"])


def test_two_legitimate_descriptions_are_not_combined_into_a_cross_product():
    assert verify("The setup used an encoded spectral detector and a continuous thermal detector.")[
        "supported"
    ]


def test_a_temporal_adverb_is_not_a_joint_instrument_descriptor():
    assert verify(
        "The continuous detector still records pulsed observations.", ("still", "pulsed")
    )["supported"]


def test_future_equipment_is_not_an_observed_past_configuration():
    original = "The cobalt detector will be fitted with an adjustable optical filter."
    registry = SimpleNamespace(resolve=lambda eid: {"text": original})
    anchor = {
        "support_id": "planned",
        "text": original,
        "spans": [{"evidence_id": "page", "text": original}],
        "category": "DOCUMENTARY",
        "epistemic_type": "documentary_content",
        "conditions": [],
    }
    model = SimpleNamespace(check=lambda p, h: {"supported": True})
    invalid = verify_paraphrase(
        "The cobalt detector was used with an adjustable optical filter.", [anchor], registry, model
    )
    assert not invalid["supported"]
    assert any("future equipment plan" in error for error in invalid["errors"])
    assert verify_paraphrase(
        "The cobalt detector was planned to be fitted with an adjustable optical filter.",
        [anchor],
        registry,
        model,
    )["supported"]
