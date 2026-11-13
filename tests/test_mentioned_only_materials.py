"""A material named only outside the study's own research, and used by nothing, is a mention;
synthetic text, never NASA data."""

from test_background_sections import records_for
from test_background_sections import service as _service

service = _service

PAPER = (
    "# Synthetic study\n"
    "I. Introduction\nEarlier rigs were lubricated with Gamma oil before the change.\n"
    "II. Methods\nAlpha test series used a flow duct wetted with Delta oil.\n"
    "III. Results\nAlpha test series flames went out at 18% oxygen.\n"
)

HELD = "MATERIAL_ONLY_MENTIONED_OUTSIDE_OWN_RESEARCH"


def entity_record(service, entities):
    records = records_for(service, PAPER, entities)
    return {r["proposal"]["key"]: r for r in records if r["kind"] == "entities"}


def test_a_material_named_only_in_the_introduction_is_held_as_a_mention(service):
    records = entity_record(
        service, [("g", "Gamma oil", "Material", "Earlier rigs were lubricated with Gamma oil")]
    )
    assert records["g"]["status"] == "UNRESOLVED" and HELD in records["g"]["reasons"]


def test_a_material_of_the_methods_is_not_held(service):
    # Metamorphic: the same kind of mention in the study's own methods is its material.
    records = entity_record(
        service, [("d", "Delta oil", "Material", "a flow duct wetted with Delta oil")]
    )
    assert HELD not in records["d"]["reasons"]


def test_a_cited_material_is_left_to_the_cited_study(service):
    records = records_for(
        service,
        PAPER,
        [("g", "Gamma oil", "Material", "Earlier rigs were lubricated with Gamma oil")],
    )
    (record,) = [r for r in records if r["kind"] == "entities"]
    record["proposal"]["study"] = "cited"
    from nasa_fire_ai.ingestion.document_extraction import hold_mentioned_only_materials

    record.update(status="SOURCE_SUPPORTED", reasons=[])
    hold_mentioned_only_materials([record], {"segments": [], "sections": []})
    assert record["status"] == "SOURCE_SUPPORTED"


def test_a_material_used_by_a_supported_statement_is_not_held():
    from nasa_fire_ai.ingestion.document_extraction import hold_mentioned_only_materials

    material = {
        "kind": "entities",
        "status": "SOURCE_SUPPORTED",
        "reasons": [],
        "proposal": {"key": "g", "class_id": "Material", "study": "current"},
        "support_spans": [{"evidence_id": "E-0", "start": 0, "quote": "Gamma oil"}],
    }
    statement = {
        "kind": "statements",
        "status": "SOURCE_SUPPORTED",
        "reasons": [],
        "proposal": {"subjects": ["study"]},
        "proposed_subjects": ["g"],
        "support_spans": [],
    }
    hold_mentioned_only_materials([material, statement], {"segments": [], "sections": []})
    assert material["status"] == "SOURCE_SUPPORTED"
