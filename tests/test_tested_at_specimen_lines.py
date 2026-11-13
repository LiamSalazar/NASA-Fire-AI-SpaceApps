"""A material inside a printed "tested at" line never hides its specimen; synthetic, never NASA data."""

import pytest
from test_document_extraction import entity, submitted
from test_document_extraction import service as _service

from nasa_fire_ai.ingestion.document_extraction import (
    Output,
    structure_entity_candidates,
)
from nasa_fire_ai.ingestion.document_structure import structure

service = _service


SLIDE = (
    "# Synthetic study\nCOTS Solutions\n"
    "Custom fire-resistant patches sewn \nto outer jacket fabric tested at 37% \nO2 and 8.2 psia\n"
    "Next item on the slide\n"
)


@pytest.mark.parametrize(
    "text,material,expected",
    [
        (SLIDE, "outer jacket fabric", "Custom fire-resistant patches sewn to outer jacket fabric"),
        (
            SLIDE.replace("sewn \nto outer jacket fabric", "bonded \nto beta cloth"),
            "beta cloth",
            "Custom fire-resistant patches bonded to beta cloth",
        ),
    ],
)
def test_a_material_inside_a_tested_at_line_does_not_hide_its_specimen(
    service, text, material, expected
):
    # Metamorphic: another constituent material, same reading.
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [entity(p, "m", material, "Material", material)]
    labels = [e["label"] for e in structure_entity_candidates(o, p, structure(p, service.root))]
    assert expected in labels


def test_a_material_that_heads_the_line_or_a_proposed_specimen_still_hides_it(service):
    p = submitted(service, SLIDE)
    document = structure(p, service.root)
    o = Output().model_dump()
    o["entities"] = [entity(p, "m", "Custom fire-resistant patches", "Material", "Custom")]
    assert not structure_entity_candidates(o, p, document)
    o["entities"] = [
        entity(p, "s", "Custom fire-resistant patches", "Sample", "Custom fire-resistant patches")
    ]
    assert not structure_entity_candidates(o, p, document)


def test_a_bullet_heading_is_never_joined_into_a_specimen_headed_by_a_material(service):
    text = (
        "# Synthetic study\nCOTS Solutions\n• Fire-resistant patches\n"
        "100% PBI knit fabric coupons tested at 48% O2 and 8.2 psia\n"
    )
    p = submitted(service, text)
    o = Output().model_dump()
    o["entities"] = [entity(p, "m", "100% PBI knit fabric", "Material", "100% PBI knit fabric")]
    labels = [e["label"] for e in structure_entity_candidates(o, p, structure(p, service.root))]
    assert not any("Fire-resistant patches" in label for label in labels)
