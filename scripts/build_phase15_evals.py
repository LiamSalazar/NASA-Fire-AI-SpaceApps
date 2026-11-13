#!/usr/bin/env python3
"""Build frozen, source-backed Phase-1.5 evaluation fixtures.

These fixtures only name pre-existing evidence and reviewed decisions.  They do
not write to the registry, canonical exports, or RDF graph.
"""

import csv
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data/index/evidence.sqlite"
OUT = ROOT / "evals"


def main() -> None:
    safety = json.loads((ROOT / "data/canonical/safety_records.json").read_text())
    epistemic = []
    mapping = {
        "InterventionRecord": "Intervention",
        "ObservationRecord": "ReportedExperimentalObservation",
        "nasa_conclusion": "NASAConclusion",
        "open_question": "NASAIdentifiedOpenQuestion",
        "safety_implication": "SafetyImplication",
        "requirement": "Requirement",
        "guidance": "Guidance",
        "design_criterion": "DesignCriterion",
        "test_criterion": "TestCriterion",
    }
    for record in safety:
        label = mapping.get(record["type"], mapping.get(record.get("statement_type")))
        if not label:
            continue
        evidence = record["evidence_refs"][0]
        text = record.get("description") or record.get("text") or record["normalized_text"]
        epistemic.append(
            {
                "gold_case_id": f"reviewed-{record.get('id', record.get('statement_id'))}",
                "source_id": evidence["source_id"],
                "document_id": record["source_document"],
                "page": record.get("source_page"),
                "section": record.get("source_section"),
                "local_heading": record.get("source_section"),
                "passage": text,
                "gold_label": label,
                "reason_for_label": "Existing curated or human-reviewed NASA-backed canonical record.",
                "evidence_id": evidence["evidence_id"],
                "review_status": "REVIEWED_POSITIVE",
            }
        )
    db = sqlite3.connect(REGISTRY)
    db.row_factory = sqlite3.Row
    rows = db.execute(
        """select c.candidate_id,c.payload_json,c.evidence_id,q.reviewer_note
        from candidate_records c join review_queue q on q.candidate_id=c.candidate_id
        where q.status='REJECTED' order by c.candidate_id"""
    ).fetchall()
    for index, row in enumerate(rows, 1):
        payload = json.loads(row["payload_json"])
        passage = payload.get("evidence_span") or payload.get("normalized_text")
        if not passage:
            continue
        evidence = db.execute(
            "select document_id,page,section from passages where evidence_id=?",
            (row["evidence_id"],),
        ).fetchone()
        document_id = payload.get("source_document") or (
            evidence["document_id"] if evidence else None
        )
        source = db.execute(
            "select source_id from documents where document_id=?", (document_id,)
        ).fetchone()
        epistemic.append(
            {
                "gold_case_id": f"reviewed-negative-{index:02d}",
                "source_id": source[0] if source else None,
                "document_id": document_id,
                "page": payload.get("page") or (evidence["page"] if evidence else None),
                "section": payload.get("section") or (evidence["section"] if evidence else None),
                "local_heading": payload.get("local_heading"),
                "passage": passage,
                "gold_label": "NONE",
                "reason_for_label": "Human Phase-1 audit rejected this rhetorical or non-claim text: "
                + (row["reviewer_note"] or "not a scientific claim"),
                "evidence_id": row["evidence_id"],
                "review_status": "REVIEWED_NEGATIVE",
            }
        )
    # A document title is explicitly non-claim rhetoric under the Phase-1
    # policy.  This is a clear, source-backed negative rather than a guessed
    # scientific label.
    title_row = db.execute(
        """select d.document_id,d.source_id,d.title,p.evidence_id,p.page,p.section
        from documents d join passages p on p.document_id=d.document_id
        where d.document_id like 'ntrs-upstream-%' order by d.document_id limit 1"""
    ).fetchone()
    if title_row:
        epistemic.append(
            {
                "gold_case_id": "reviewed-negative-title-01",
                "source_id": title_row["source_id"],
                "document_id": title_row["document_id"],
                "page": title_row["page"],
                "section": title_row["section"],
                "local_heading": "document title",
                "passage": title_row["title"],
                "gold_label": "NONE",
                "reason_for_label": "Document title only; titles are not scientific claims under the reviewed Phase-1 policy.",
                "evidence_id": title_row["evidence_id"],
                "review_status": "POLICY_REVIEWED_NEGATIVE",
            }
        )
    # The 9 reviewed positives plus 20 audited negatives are all defensible;
    # do not pad the set with uncertain labels.
    (OUT / "phase1_5_epistemic_gold.json").write_text(
        json.dumps({"version": "phase1.5-frozen-2026-10-04", "cases": epistemic}, indent=2) + "\n"
    )

    catalog = ROOT / "data/raw/upstream_nasa_space_apps/ntrs/catalog.csv"
    with catalog.open(encoding="utf-8-sig", errors="replace", newline="") as handle:
        ntrs = list(csv.DictReader(handle))
    available = {r[0].removeprefix("ntrs-") for r in db.execute("select source_id from sources")}
    docs = [r for r in ntrs if r["id"] in available and r.get("title")]
    questions = []
    # Exact catalog-title lookups are provenance-backed documentary retrieval
    # cases, spanning all available upstream topic groups.
    seen_topics = set()
    for row in docs:
        if row["topic"] in seen_topics:
            continue
        seen_topics.add(row["topic"])
        questions.append(
            {
                "id": f"doc-{len(questions) + 1:02d}",
                "question": row["title"],
                "category": "documentary",
                "family": row["topic"],
                "expected_source_ids": [f"ntrs-{row['id']}"],
                "expected_direct": None,
                "acceptable_abstention": False,
            }
        )
    # Add additional different documents until documentary scale is represented.
    for row in docs:
        if len(questions) >= 35:
            break
        source_id = f"ntrs-{row['id']}"
        if any(source_id in q["expected_source_ids"] for q in questions):
            continue
        questions.append(
            {
                "id": f"doc-{len(questions) + 1:02d}",
                "question": row["title"],
                "category": "documentary",
                "family": row["topic"],
                "expected_source_ids": [source_id],
                "expected_direct": None,
                "acceptable_abstention": False,
            }
        )
    safety_questions = [
        ("active fire suppression early detection", "ntrs-20205007829", "safety"),
        ("spacecraft flammability configuration assessment guidance", "ntrs-20150020937", "safety"),
        ("NASA STD 6001 material tests", "nasa-std-6001", "safety"),
        ("additional focused tests fire suppression guidance", "ntrs-20205007829", "safety"),
        ("PMMA Saffire fire suppression", "ntrs-20205007829", "safety"),
    ]
    for text, source, category in safety_questions:
        questions.append(
            {
                "id": f"safety-{len(questions) + 1:02d}",
                "question": text,
                "category": category,
                "family": "safety",
                "expected_source_ids": [source],
                "expected_direct": None,
                "acceptable_abstention": False,
            }
        )
    structured = [
        ("Find Saffire-I", "DIRECT"),
        ("Compare Saffire runs", "DIRECT"),
        ("SIBAL Fabric airflow <= 0.10 m/s", "RELATED"),
        ("SIBAL Fabric microgravity airflow <= 0.10 m/s", "RELATED"),
        ("PMMA microgravity", "NO_DIRECT_EVIDENCE"),
        ("BASS-II", "NO_DIRECT_EVIDENCE"),
        ("unobtainium combustion", "NO_DIRECT_EVIDENCE"),
        ("PMMA suppression open question", "NO_DIRECT_EVIDENCE"),
    ]
    for text, status in structured:
        questions.append(
            {
                "id": f"structured-{len(questions) + 1:02d}",
                "question": text,
                "category": "structured",
                "family": "seed-kg",
                "expected_source_ids": [],
                "expected_direct": status,
                "acceptable_abstention": status == "NO_DIRECT_EVIDENCE",
            }
        )
    negatives = ["xenonium droplet combustion", "airflow velocity versus flame-spread velocity"]
    for text in negatives:
        questions.append(
            {
                "id": f"negative-{len(questions) + 1:02d}",
                "question": text,
                "category": "abstention",
                "family": "negative",
                "expected_source_ids": [],
                "expected_direct": "NO_DIRECT_EVIDENCE",
                "acceptable_abstention": True,
            }
        )
    assert len(questions) >= 50, len(questions)
    (OUT / "phase1_5_retrieval_gold.json").write_text(
        json.dumps({"version": "phase1.5-frozen-2026-10-04", "questions": questions}, indent=2)
        + "\n"
    )
    print(
        json.dumps(
            {"epistemic_cases": len(epistemic), "retrieval_questions": len(questions)}, indent=2
        )
    )


if __name__ == "__main__":
    main()
