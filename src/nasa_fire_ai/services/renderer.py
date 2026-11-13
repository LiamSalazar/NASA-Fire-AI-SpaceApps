from nasa_fire_ai.models import EvidenceBundle, ScientificAnswer


def render(bundle: EvidenceBundle) -> str:
    lines = []
    sections = [
        ("Direct Experimental Evidence", bundle.direct_evidence),
        ("Experimental Interventions", bundle.interventions),
        ("NASA Observations", bundle.experimental_observations),
        ("NASA Conclusions", bundle.nasa_conclusions),
        ("Safety Implications", bundle.safety_implications),
        (
            "Requirements and Guidance",
            bundle.requirements + bundle.guidance + bundle.design_test_criteria,
        ),
        ("NASA-Identified Open Questions", bundle.nasa_identified_open_questions),
        ("Related Evidence", bundle.related_evidence),
    ]
    if bundle.no_direct_evidence:
        lines.append("No direct matching evidence was found in the indexed NASA corpus.")
    for title, items in sections:
        if items:
            lines.append(f"\n{title}")
            for item in items:
                text = item.get(
                    "normalized_text", item.get("text", item.get("description", item.get("id")))
                )
                evidence = ", ".join(
                    ref["evidence_id"] for ref in item.get("evidence_refs", [])
                ) or ", ".join(item.get("evidence_ids", []))
                detail = ""
                if item.get("differs"):
                    detail = f"; matches: {', '.join(item.get('matches', []))}; differs: {', '.join(item['differs'])}; unknown: {', '.join(item.get('unknown', []))}"
                lines.append(f"- {text} [evidence: {evidence}]{detail}")
    if bundle.evidence_passages:
        lines.extend(
            ["\nSources"]
            + [
                f"- {p['evidence_id']} — {p['document_id']}, p. {p['page']}: {p['text'][:240]}"
                for p in bundle.evidence_passages
            ]
        )
    return "\n".join(lines)


def render_answer(answer: ScientificAnswer) -> str:
    if answer.direct_evidence_status == "NO_DIRECT_EVIDENCE":
        prefix = "No direct matching evidence was found in the indexed NASA corpus.\n"
    else:
        prefix = ""
    return prefix + "\n".join(
        [f"Coverage: {note}" for note in answer.coverage_notes]
        + [
            f"Sources: {source['evidence_id']} — {source['document_id']}"
            for source in answer.sources
        ]
    )


def render_grounded(draft, answer: ScientificAnswer, detail_level: str = "standard") -> str:
    """Render an already validated draft; this function adds no scientific content."""
    lines = [draft.answer_summary]
    if answer.direct_evidence_status == "NO_DIRECT_EVIDENCE":
        lines.append(
            "No direct evidence matching all requested conditions is indexed in the current corpus."
        )
    claims = draft.claims[:2] if detail_level == "concise" else draft.claims
    for claim in claims:
        citations = ", ".join(claim.evidence_ids)
        lines.append(f"- {claim.text} [{citations}]")
    if draft.limitations:
        lines.append("Limitations: " + " ".join(draft.limitations))
    if answer.coverage_notes:
        lines.append("Coverage: " + " ".join(answer.coverage_notes))
    return "\n".join(lines)
