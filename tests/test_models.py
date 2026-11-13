import pytest
from pydantic import ValidationError

from nasa_fire_ai.models import (
    Claim,
    InvestigationRecord,
    NumericFilter,
    OpenQuestionRecord,
    QueryIntent,
)


def test_evidence_required():
    with pytest.raises(ValidationError):
        InvestigationRecord(id="x", title="x", evidence_refs=[])


def test_claim_rejects_unsupported():
    with pytest.raises(ValidationError):
        Claim(claim_id="c", claim_type="observed_result", text="x")


def test_no_direct_notice_allowed():
    assert (
        Claim(claim_id="c", claim_type="no_direct_evidence_notice", text="none").evidence_ids == []
    )


def test_open_question_requires_explicit_evidence():
    with pytest.raises(ValidationError):
        OpenQuestionRecord(id="q", text="unresolved", evidence_refs=[])


def test_intent_is_strictly_typed():
    assert QueryIntent(oxygen=NumericFilter(operator="<", value=18, unit="%")).oxygen.value == 18
