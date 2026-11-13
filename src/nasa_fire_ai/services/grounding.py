"""Deterministic validation of a generated draft against one EvidenceBundle."""

from dataclasses import dataclass

from nasa_fire_ai.models import EvidenceBundle, GroundedAnswerDraft


@dataclass(frozen=True)
class GroundingResult:
    valid: bool
    errors: list[str]


def _ids(item: dict) -> set[str]:
    return set(item.get("evidence_ids", [])) | {
        ref["evidence_id"] for ref in item.get("evidence_refs", []) if "evidence_id" in ref
    }


class GroundingValidator:
    """Metadata checks are deliberately deterministic; prose cannot confer authority."""

    def validate(self, draft: GroundedAnswerDraft, bundle: EvidenceBundle) -> GroundingResult:
        allowed = {p["evidence_id"] for p in bundle.evidence_passages}
        categories: dict[str, set[str]] = {}
        for name, items in {
            "observed_result": bundle.experimental_observations,
            "tested_intervention": bundle.interventions,
            "nasa_conclusion": bundle.nasa_conclusions,
            "safety_implication": bundle.safety_implications,
            "requirement": bundle.requirements,
            "guidance": bundle.guidance,
            "design_criterion": bundle.design_test_criteria,
            "test_criterion": bundle.design_test_criteria,
            "open_question": bundle.nasa_identified_open_questions,
        }.items():
            for item in items:
                for evidence_id in _ids(item):
                    allowed.add(evidence_id)
                    categories.setdefault(evidence_id, set()).add(name)
        direct_ids = {eid for item in bundle.direct_evidence for eid in _ids(item)}
        related_ids = {eid for item in bundle.related_evidence for eid in _ids(item)}
        allowed |= direct_ids | related_ids
        errors: list[str] = []
        for claim in draft.claims:
            # The model supplies prose plus IDs only.  All scientific metadata is
            # reconstructed from the bundle before validation/rendering.
            claim.authority = "NASA_BACKED"
            cited_types = set().union(*(categories.get(eid, set()) for eid in claim.evidence_ids))
            if len(cited_types) == 1:
                claim.epistemic_type = next(iter(cited_types))
            if claim.evidence_ids and set(claim.evidence_ids) <= direct_ids:
                claim.relationship_status = "DIRECT"
            elif claim.evidence_ids and set(claim.evidence_ids) <= related_ids:
                claim.relationship_status = "RELATED"
            elif bundle.no_direct_evidence and not claim.evidence_ids:
                claim.relationship_status = "NO_DIRECT"
            else:
                claim.relationship_status = "SAFETY"
            unknown = set(claim.evidence_ids) - allowed
            if unknown:
                errors.append(
                    f"{claim.claim_id}: evidence outside EvidenceBundle: {sorted(unknown)}"
                )
            if claim.epistemic_type != "no_direct_evidence_notice" and not claim.evidence_ids:
                errors.append(f"{claim.claim_id}: scientific claim has no evidence")
            if claim.epistemic_type == "open_question" and (
                not claim.evidence_ids
                or not all(
                    "open_question" in categories.get(eid, set()) for eid in claim.evidence_ids
                )
            ):
                errors.append(f"{claim.claim_id}: NASA open question was not explicitly supplied")
            if (
                claim.epistemic_type in {"requirement", "guidance"}
                and claim.evidence_ids
                and not all(
                    claim.epistemic_type in categories.get(eid, set()) for eid in claim.evidence_ids
                )
            ):
                errors.append(f"{claim.claim_id}: requirement/guidance type mismatch")
            if claim.relationship_status == "DIRECT" and not set(claim.evidence_ids) <= direct_ids:
                errors.append(
                    f"{claim.claim_id}: DIRECT status is not supported by direct evidence"
                )
            if (
                claim.relationship_status == "RELATED"
                and not set(claim.evidence_ids) <= related_ids
            ):
                errors.append(
                    f"{claim.claim_id}: RELATED status is not supported by related evidence"
                )
            if claim.relationship_status == "NO_DIRECT" and not bundle.no_direct_evidence:
                errors.append(f"{claim.claim_id}: NO_DIRECT conflicts with bundle")
            if claim.authority != "NASA_BACKED":
                errors.append(
                    f"{claim.claim_id}: non-NASA authority cannot be rendered as scientific answer"
                )
        return GroundingResult(valid=not errors, errors=errors)
