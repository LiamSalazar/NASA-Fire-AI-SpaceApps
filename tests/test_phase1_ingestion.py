import json

from nasa_fire_ai.evidence import EvidenceRegistry
from nasa_fire_ai.ingestion.phase1 import (
    CandidateRecord,
    SourceAdapter,
    publish_validated,
    segment_document,
    structured_csv_candidates,
    validate_candidate,
)


def test_adapter_is_an_explicit_interface():
    assert set(SourceAdapter.__abstractmethods__) == {
        "discover",
        "fetch_metadata",
        "list_artifacts",
        "fetch_artifact",
        "fingerprint",
    }


def test_candidate_cannot_publish_without_resolvable_evidence(tmp_path):
    registry = EvidenceRegistry(tmp_path / "e.sqlite")
    candidate = CandidateRecord(
        candidate_id="c",
        candidate_type="CandidateMeasurementObservation",
        normalized_text="{}",
        evidence_id="missing",
        source_document="d",
        extraction_method="structured",
    )
    assert validate_candidate(candidate, registry)[0] == "REJECTED"
    assert publish_validated([candidate], registry, tmp_path / "published.json") == 0


def test_unknown_or_ambiguous_term_requires_review(tmp_path):
    registry = EvidenceRegistry(tmp_path / "e.sqlite")
    registry.add_passage(
        {
            "evidence_id": "E",
            "document_id": "d",
            "page": 1,
            "section": None,
            "text": "source",
            "start_offset": 0,
            "end_offset": 6,
            "raw_file": "x",
            "checksum": "x",
        }
    )
    candidate = CandidateRecord(
        candidate_id="c",
        candidate_type="CandidateOntologyConcept",
        evidence_id="E",
        source_document="d",
        extraction_method="llm",
        term="new term",
        evidence_span="source",
    )
    assert validate_candidate(candidate, registry)[0] == "REVIEW_REQUIRED"


def test_high_risk_requirement_requires_source_context(tmp_path):
    registry = EvidenceRegistry(tmp_path / "e.sqlite")
    registry.add_passage(
        {
            "evidence_id": "E",
            "document_id": "d",
            "page": 1,
            "section": None,
            "text": "shall",
            "start_offset": 0,
            "end_offset": 5,
            "raw_file": "x",
            "checksum": "x",
        }
    )
    candidate = CandidateRecord(
        candidate_id="r",
        candidate_type="CandidateRequirement",
        normalized_text="shall",
        evidence_id="E",
        source_document="d",
        extraction_method="llm",
        evidence_span="shall",
    )
    assert validate_candidate(candidate, registry)[0] == "REVIEW_REQUIRED"


def test_segmentation_preserves_page_and_offsets(tmp_path):
    path = tmp_path / "nasa.txt"
    path.write_text("Abstract\n" + "NASA documented passage. " * 10)
    registry = EvidenceRegistry(tmp_path / "e.sqlite")
    ids = segment_document(path, "s", "d", registry)
    assert (
        ids
        and registry.resolve(ids[0])["page"] == 1
        and registry.resolve(ids[0])["start_offset"] == 0
    )


def test_generic_structured_csv_and_duplicate_publish(tmp_path):
    path = tmp_path / "table.csv"
    path.write_text("Test #,Fuel Sample Material,Calibrated  initial O2 % by vol\nA1,PMMA,21.5\n")
    registry = EvidenceRegistry(tmp_path / "e.sqlite")
    candidates = structured_csv_candidates(path, "psi-x", "psi-x", registry)
    output = tmp_path / "published.json"
    assert publish_validated(candidates, registry, output) == 1
    assert publish_validated(candidates, registry, output) == 0
    assert json.loads(output.read_text())[-1]["id"] == "psi-x-A1"
