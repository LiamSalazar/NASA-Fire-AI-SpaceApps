import json
from pathlib import Path

from nasa_fire_ai.models import EvidenceBundle, ExperimentComparison, ScientificAnswer


def compare_runs(root: Path, ids: list[str]) -> ExperimentComparison | None:
    runs = [
        r for r in json.loads((root / "data/canonical/runs.json").read_text()) if r["id"] in ids
    ]
    if len(runs) < 2:
        return None
    keys = [
        "material",
        "gravity",
        "flow_velocity_m_s",
        "flow_direction",
        "burn_time_s",
        "oxygen_fraction",
        "oxygen_range_fraction",
    ]
    shared, different, unknown = {}, {}, []
    for key in keys:
        values = {r["id"]: r.get(key) for r in runs}
        if any(v is None for v in values.values()):
            unknown.append(key)
        elif len({str(v) for v in values.values()}) == 1:
            shared[key] = next(iter(values.values()))
        else:
            different[key] = values
    return ExperimentComparison(
        run_ids=ids,
        shared_conditions=shared,
        different_conditions=different,
        unknown_or_unavailable_conditions=unknown,
    )


def scientific_answer(query: str, bundle: EvidenceBundle, root: Path) -> ScientificAnswer:
    status = (
        "DIRECT_EVIDENCE"
        if bundle.direct_evidence
        else "RELATED_EVIDENCE"
        if bundle.related_evidence
        else "NO_DIRECT_EVIDENCE"
    )
    notes = []
    if bundle.no_direct_evidence:
        notes.append("The indexed corpus contains no direct matching experimental run.")
    if bundle.related_evidence:
        notes.append(
            "Related evidence was found with explicit differing or unavailable conditions."
        )
    if not bundle.nasa_identified_open_questions:
        notes.append("No NASA-identified open question was retrieved for this query.")
    run_ids = [x["id"] for x in bundle.direct_evidence if x["id"].startswith("psi-")]
    return ScientificAnswer(
        query=query,
        query_intent=bundle.query_intent,
        direct_evidence_status=status,
        direct_evidence=bundle.direct_evidence,
        related_evidence=bundle.related_evidence,
        experimental_interventions=bundle.interventions,
        observations=bundle.experimental_observations,
        nasa_conclusions=bundle.nasa_conclusions,
        safety_implications=bundle.safety_implications,
        requirements=bundle.requirements,
        guidance=bundle.guidance,
        design_test_criteria=bundle.design_test_criteria,
        nasa_identified_open_questions=bundle.nasa_identified_open_questions,
        publications=bundle.publications,
        sources=bundle.evidence_passages,
        coverage_notes=notes,
        comparison=compare_runs(root, run_ids),
    )
