from nasa_fire_ai.models import Claim


def validate_claims(claims: list[Claim]) -> list[Claim]:
    return [
        claim
        for claim in claims
        if claim.evidence_ids or claim.claim_type == "no_direct_evidence_notice"
    ]
