"""Track B ontology context: reviewed staged terms from a frozen snapshot (never for the
document they came from, by PDF sha256) and per-candidate snippets. Invented text only (B8)."""

import hashlib
import json
from typing import ClassVar

from test_never_proposed_flags import run
from test_never_proposed_flags import service as _service
from test_new_prompt_text_b8 import CANDIDATE_TEXT

from nasa_fire_ai.ingestion.ontology_context import (
    build_staged_snapshot,
    candidate_snippets,
    staged_terms_for,
)

service = _service
SHA_X, SHA_Y = "a" * 64, "b" * 64


def candidates():
    return [
        {
            "source_id": "doc-x",
            "review_status": "PENDING",
            "proposal": {"term": "PlateCoolingRate", "kind": "class", "parent": "Measurement"},
        },
        {
            "source_id": "doc-x",
            "review_status": "PENDING",
            "proposal": {"term": "UnreviewedTerm", "kind": "class", "parent": "Measurement"},
        },
        {
            "source_id": "doc-x",
            "review_status": "REJECTED",
            "proposal": {"term": "RejectedTerm", "kind": "class"},
        },
        {
            "source_id": "hand-seeded",
            "review_status": "PENDING",
            "proposal": {"term": "SeededTerm", "kind": "class"},
        },
    ]


def snapshot():
    return build_staged_snapshot(
        candidates(),
        {"doc-x": SHA_X}.get,
        version="t1",
        reviewed={"PlateCoolingRate", "RejectedTerm", "SeededTerm"},
    )


def test_the_snapshot_keeps_only_reviewed_pipeline_terms():
    assert [t["term"] for t in snapshot()["terms"]] == ["PlateCoolingRate"]
    assert snapshot()["terms"][0]["origins"] == [{"source_id": "doc-x", "pdf_sha256": SHA_X}]


def test_a_staged_term_never_reaches_its_origin_document():
    snap = snapshot()
    assert staged_terms_for({SHA_X}, snap) == []
    assert [t["term"] for t in staged_terms_for({SHA_Y}, snap)] == ["PlateCoolingRate"]
    # Metamorphic: a renamed copy of the origin PDF has the same digest.
    assert staged_terms_for(SHA_X, snap) == []
    assert all("origins" not in t for t in staged_terms_for({SHA_Y}, snap))


def test_the_digest_of_a_pdf_is_its_sha256():
    assert hashlib.sha256(b"pdf").hexdigest() != SHA_X


class Semantic:
    class_metadata: ClassVar = {"Measurement": {"query_terms": ["reading"]}, "Quantity": {}}
    relations: ClassVar = {}


def test_a_candidate_snippet_names_the_term_it_qualifies(monkeypatch):
    from nasa_fire_ai.ingestion import ontology_context as oc

    monkeypatch.setattr(oc, "lineage", lambda cls, semantic: [cls, "Quantity"])
    found = candidate_snippets(
        [
            {"printed": "plate rate", "coverage": "QUALIFIES", "qualifies": "Measurement"},
            {"printed": "other", "coverage": "UNCOVERED"},
        ],
        Semantic,
    )
    assert found == [{"class": "Measurement", "ancestors": ["Quantity"], "aliases": ["reading"]}]


def request_payloads(service, monkeypatch, tmp_path, sha, flags):
    path = tmp_path / "snapshot.json"
    snap = {
        "version": "t1",
        "terms": [
            {
                "term": "PlateCoolingRate",
                "kind": "class",
                "parent": "Measurement",
                "review_status": "REVIEWED",
                "origins": [{"source_id": "o", "pdf_sha256": sha}],
            }
        ],
    }
    path.write_text(json.dumps(snap), encoding="utf-8")
    monkeypatch.setenv("SCIENCE_STAGED_SNAPSHOT", str(path))
    for flag in flags:
        monkeypatch.setenv(flag, "1")
    return run(service, monkeypatch, flags=("SCIENCE_BACKGROUND_FACETS",), text=CANDIDATE_TEXT)


def staged_names(payloads):
    return {s["term"] for p in payloads for s in p.get("ontology_context", {}).get("staged", [])}


def test_the_request_carries_staged_terms_only_with_the_flag(service, monkeypatch, tmp_path):
    off = request_payloads(service, monkeypatch, tmp_path, "c" * 64, ())
    assert staged_names(off) == set()
    on = request_payloads(service, monkeypatch, tmp_path, "c" * 64, ("SCIENCE_STAGED_CONTEXT",))
    assert "PlateCoolingRate" in staged_names(on)
    assert all("candidate_snippets" not in p for p in on)


def test_the_request_leaves_out_a_term_staged_from_its_own_pdf(service, monkeypatch, tmp_path):
    from test_never_proposed_flags import submitted

    own = {e["checksum"] for e in submitted(service, CANDIDATE_TEXT)["evidence"]}
    sha = min(own)
    on = request_payloads(service, monkeypatch, tmp_path, sha, ("SCIENCE_STAGED_CONTEXT",))
    assert staged_names(on) == set()


def test_candidate_snippets_flag_changes_the_identity_block(service, monkeypatch, tmp_path):
    off = request_payloads(service, monkeypatch, tmp_path, "c" * 64, ())
    on = request_payloads(service, monkeypatch, tmp_path, "c" * 64, ("SCIENCE_CANDIDATE_SNIPPETS",))

    def size(payloads):
        return min(
            len(p["ontology_context"]["approved"])
            for p in payloads
            if "ontology_context" in p and p["stage"] == "identity"
        )

    assert size(on) < size(off)
