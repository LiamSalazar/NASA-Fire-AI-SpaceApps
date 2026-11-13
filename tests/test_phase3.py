from pathlib import Path

import pytest
from pydantic import ValidationError

from nasa_fire_ai.config import Settings
from nasa_fire_ai.models import (
    EvidenceBundle,
    GroundedAnswerDraft,
    GroundedClaim,
    ProposedEntityMention,
    ProposedQueryIntent,
    QueryIntent,
)
from nasa_fire_ai.query.phase3 import deterministic_proposal, validate_proposed_intent
from nasa_fire_ai.services.grounding import GroundingValidator
from nasa_fire_ai.services.phase3 import Phase3AssistantService

ROOT = Path(__file__).resolve().parents[1]


def test_proposed_and_validated_intents_are_distinct_and_alias_precedence_holds():
    proposal = ProposedQueryIntent(
        query_mode="experiment_search",
        materials=[
            ProposedEntityMention(
                raw_span="PMMA",
                entity_type_candidate="material",
                canonical_candidate="material:sibal_fabric",
            )
        ],
    )
    validated = validate_proposed_intent(proposal, "PMMA")
    assert validated.intent.materials == ["PMMA"]


@pytest.mark.parametrize(
    "query, phrase", [("What about acrylic fires?", "acrylic"), ("velocity effects", "flow")]
)
def test_ambiguity_is_preserved(query, phrase):
    validated = validate_proposed_intent(deterministic_proposal(query), query)
    assert validated.clarification_required
    assert phrase in " ".join(validated.raw_unresolved_terms + validated.ambiguities).lower()


def test_numeric_span_keeps_reported_unit_and_matcher_normalizes_later():
    validated = validate_proposed_intent(
        deterministic_proposal("microgravity airflow below 10 cm/s"),
        "microgravity airflow below 10 cm/s",
    )
    assert validated.intent.flow_velocity.value == 10
    assert validated.intent.flow_velocity.unit == "cm/s"
    assert validated.intent.flow_velocity.operator == "<"


def test_unknown_term_is_not_promoted_to_canonical_identity():
    validated = validate_proposed_intent(
        deterministic_proposal("xenon combustion"), "xenon combustion"
    )
    assert "xenon" in validated.raw_unresolved_terms
    assert not validated.intent.materials


def test_grounding_rejects_unknown_bundle_evidence_and_invented_open_question():
    bundle = EvidenceBundle(query_intent=QueryIntent())
    bad = GroundedAnswerDraft(
        answer_summary="x",
        claims=[
            GroundedClaim(
                claim_id="x",
                text="x",
                epistemic_type="open_question",
                relationship_status="SAFETY",
                evidence_ids=["invented"],
            )
        ],
    )
    result = GroundingValidator().validate(bad, bundle)
    assert not result.valid and "outside EvidenceBundle" in " ".join(result.errors)


def test_no_direct_claim_contract_allows_status_notice_only():
    assert GroundedClaim(
        claim_id="n",
        text="No direct evidence.",
        epistemic_type="no_direct_evidence_notice",
        relationship_status="NO_DIRECT",
    )
    with pytest.raises(ValidationError):
        GroundedClaim(
            claim_id="x", text="x", epistemic_type="nasa_conclusion", relationship_status="SAFETY"
        )


def test_provider_unavailable_uses_deterministic_and_extractive_fallback():
    settings = Settings()
    object.__setattr__(settings, "root", ROOT)
    object.__setattr__(settings, "nvidia_api_key", None)
    response = Phase3AssistantService(root=ROOT, settings=settings).answer_query(
        "Compare Saffire-I S1 and S2."
    )
    assert response.answer.direct_evidence_status == "DIRECT_EVIDENCE"
    assert response.draft is None
    assert "interpreter fallback" in " ".join(response.trace.fallback_status)
