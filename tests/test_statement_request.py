"""The propositions request defines every statement role; synthetic."""

import typing

from test_document_extraction import service as _service

from nasa_fire_ai.ingestion.document_extraction import (
    STAGE_INSTRUCTIONS,
    Statement,
)

service = _service

TEXT = "II. Methods\nRun A1 used the Beta igniter coil. Run A1 burned for a short time.\n"


def test_the_role_card_defines_every_statement_role():
    roles = typing.get_args(Statement.model_fields["epistemic"].annotation)
    card = STAGE_INSTRUCTIONS["propositions"]
    assert len(roles) == 15
    # The data-provenance role is defined only in the request that its flag adds
    # (SCIENCE_STRUCTURED_PROVENANCE), so the card is unchanged with the flag off.
    assert "- data_provenance:" not in card
    assert all(f"- {role}:" in card for role in roles if role != "data_provenance")
    # Every role is a profile over the scientific facets, the old ten included.
    from nasa_fire_ai.ingestion.scientific_facets import STATEMENT_PROFILES

    assert set(roles) == set(STATEMENT_PROFILES)
    assert "never documentary_context" in card
