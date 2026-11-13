from nasa_fire_ai.models import EvidenceBundle, QueryIntent
from nasa_fire_ai.services.scientific_synthesis import (
    render_scientific,
    select_claims,
    validate_selected_claim,
)


def bundle():
    row = {
        "id": "run-observation",
        "text": "No flame was observed at 21% oxygen.",
        "evidence_ids": ["E1"],
    }
    return EvidenceBundle(
        query_intent=QueryIntent(),
        direct_evidence=[row],
        experimental_observations=[row],
        evidence_passages=[{"evidence_id": "E1", "text": row["text"]}],
    )


def test_exact_statement_and_numeric_fidelity():
    data = bundle()
    selected, receipt = select_claims(data)
    assert len(selected) == 1 and not receipt["rejected"]
    claim = selected[0][1]
    assert not validate_selected_claim(claim, data)
    for text in (
        "Flame was observed at 21% oxygen.",
        "No flame was observed at 22% oxygen.",
        "No flame was observed.",
    ):
        assert validate_selected_claim(claim.model_copy(update={"text": text}), data)


def test_valid_citation_with_wrong_experiment_rejected():
    data = bundle()
    claim = select_claims(data)[0][0][1]
    assert validate_selected_claim(
        claim.model_copy(update={"scientific_entities": ["other-run"]}), data
    )
    assert validate_selected_claim(
        claim.model_copy(update={"epistemic_type": "nasa_conclusion"}), data
    )
    assert validate_selected_claim(
        claim.model_copy(update={"relationship_status": "RELATED"}), data
    )


def test_source_span_required_even_for_known_citation():
    data = bundle()
    data.evidence_passages[0]["text"] = "The campaign used 21% oxygen."
    assert not select_claims(data)[0]


def test_duplicate_paths_and_unrelated_passages_not_rendered():
    data = bundle()
    data.experimental_observations.append(dict(data.experimental_observations[0]))
    data.evidence_passages.append({"evidence_id": "E2", "text": "irrelevant " * 5000})
    answer = render_scientific(data)
    assert answer.count("No flame was observed") == 1
    assert "irrelevant" not in answer
    assert len(data.experimental_observations) == 2


def test_exception_context_preserved_not_campaign_inherited():
    data = bundle()
    data.direct_evidence[0]["research_context"] = {
        "values": ["normal-gravity"],
        "status": "EXPLICIT_LOCAL",
    }
    answer = render_scientific(data)
    assert "normal-gravity" in answer
    assert "microgravity" not in answer.lower()


def test_missing_observation_is_not_invented_from_conditions():
    data = bundle()
    data.experimental_observations = []
    assert "do not establish" in render_scientific(data)
