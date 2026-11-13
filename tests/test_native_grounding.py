from nasa_fire_ai.models import EvidenceBundle, GroundedAnswerDraft, GroundedClaim, QueryIntent
from nasa_fire_ai.services.native import validate_native_draft


def test_native_modality_strengthening_rejected():
    text = "Focused tests may be required within the reported scope."
    bundle = EvidenceBundle(
        query_intent=QueryIntent(),
        no_direct_evidence=True,
        evidence_passages=[{"evidence_id": "E1", "text": text}],
    )
    draft = GroundedAnswerDraft(
        answer_summary="organization",
        claims=[
            GroundedClaim(
                claim_id="c", text="Focused tests shall be required.", evidence_ids=["E1"]
            )
        ],
    )
    assert not validate_native_draft(draft, bundle).valid
    draft.claims[0].text = text
    assert validate_native_draft(draft, bundle).valid
    assert draft.claims[0].epistemic_type == "source_quotation"
    assert draft.claims[0].relationship_status == "DOCUMENTARY"
    draft.claims[0].evidence_ids = ["invented"]
    assert not validate_native_draft(draft, bundle).valid


def test_partial_quote_cannot_drop_negation():
    bundle = EvidenceBundle(
        query_intent=QueryIntent(),
        no_direct_evidence=True,
        evidence_passages=[{"evidence_id": "E1", "text": "No flame was observed."}],
    )
    draft = GroundedAnswerDraft(
        answer_summary="organization",
        claims=[GroundedClaim(claim_id="c", text="flame was observed.", evidence_ids=["E1"])],
    )
    assert not validate_native_draft(draft, bundle).valid


def test_open_question_cannot_be_invented_from_an_observation():
    bundle = EvidenceBundle(
        query_intent=QueryIntent(),
        experimental_observations=[{"text": "No flame was observed.", "evidence_ids": ["E1"]}],
        no_direct_evidence=True,
    )
    draft = GroundedAnswerDraft(
        answer_summary="organization",
        claims=[
            GroundedClaim(
                claim_id="c",
                text="NASA asks whether flame can occur.",
                epistemic_type="open_question",
                evidence_ids=["E1"],
            )
        ],
    )
    assert not validate_native_draft(draft, bundle).valid


def test_design_test_criterion_authority_is_not_an_observation():
    bundle = EvidenceBundle(
        query_intent=QueryIntent(),
        no_direct_evidence=True,
        design_test_criteria=[
            {
                "statement_type": "test_criterion",
                "normalized_text": "Test at the worst case condition.",
                "evidence_refs": [{"evidence_id": "E1"}],
            }
        ],
    )
    draft = GroundedAnswerDraft(
        answer_summary="organization",
        claims=[
            GroundedClaim(
                claim_id="c", text="Test at the worst case condition.", evidence_ids=["E1"]
            )
        ],
    )
    assert validate_native_draft(draft, bundle).valid
    assert draft.claims[0].epistemic_type == "test_criterion"
