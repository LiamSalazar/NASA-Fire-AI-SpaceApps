import hashlib
import json

from nasa_fire_ai.services.claim_ledger import persist_claim_ledger


def test_claim_ledger_keeps_rejection_and_accepted_repair_without_source_document(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("NASA_CLAIM_LEDGER_DIR", str(tmp_path))
    trace = {
        "trace_id": "synthetic-turn",
        "queries": ["What was present?"],
        "support_inventory": [
            {
                "support_id": "registered-anchor",
                "spans": [{"evidence_id": "original-passage"}],
                "document_id": "original-document",
                "source_id": "original-source",
                "information_need_ids": ["need-1"],
            }
        ],
        "evidence_examination": {
            "retrieved_evidence_ids": ["original-passage"],
            "available_evidence_ids": ["original-passage"],
            "supplied_evidence_ids": ["original-passage"],
        },
        "verification": [
            {
                "statement_id": "draft-0",
                "stage": "draft",
                "text": "Unsupported synthetic claim.",
                "supported": False,
                "reason": "No verified evidence",
            },
            {
                "statement_id": "repair-1-0",
                "stage": "repair-1",
                "repair_of": "draft-0",
                "text": "The synthetic chamber contained argon.",
                "supported": True,
                "support_ids": ["registered-anchor"],
            },
        ],
    }
    answer = "The synthetic chamber contained argon. [1]"
    path = persist_claim_ledger(
        trace,
        conversation_id="conversation",
        response_id="response",
        question="What was present?",
        answer=answer,
        citations=[
            {
                "number": 1,
                "evidence_ids": ["original-passage"],
                "supports": [
                    {
                        "claim_text": "The synthetic chamber contained argon.",
                        "evidence_id": "original-passage",
                    }
                ],
            }
        ],
    )
    saved = json.loads(path.read_text())
    assert [c["supported"] for c in saved["claims"]] == [False, True]
    assert saved["claims"][1]["repair_of"] == "draft-0"
    assert saved["claims"][1]["communicated"]
    assert saved["claims"][1]["verified_evidence_ids"] == ["original-passage"]
    assert saved["claims"][1]["cited_evidence_ids"] == ["original-passage"]
    assert saved["queries"] == ["What was present?"]
    assert saved["answer_sha256"] == hashlib.sha256(answer.encode()).hexdigest()
    assert saved["citations"][0]["evidence_ids"] == ["original-passage"]
    assert path.stat().st_mode & 0o777 == 0o600


def test_line_wrapped_source_quote_is_recorded_as_communicated(tmp_path, monkeypatch):
    monkeypatch.setenv("NASA_CLAIM_LEDGER_DIR", str(tmp_path))
    text = "The vessel contains\nneon."
    trace = {
        "trace_id": "wrapped",
        "verification": [
            {"statement_id": "source-0", "text": text, "supported": True, "support_ids": []},
            {
                "statement_id": "source-1",
                "text": "The vessel contains argon.",
                "supported": True,
                "support_ids": [],
            },
        ],
    }
    path = persist_claim_ledger(
        trace,
        conversation_id="conversation",
        response_id="response",
        question="What is recorded?",
        answer="The vessel contains neon. [1]",
        citations=[],
    )
    rows = json.loads(path.read_text())["claims"]
    assert rows[0]["communicated"]
    assert not rows[1]["communicated"]


def test_literal_representation_counts_only_when_its_verified_representative_is_emitted(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("NASA_CLAIM_LEDGER_DIR", str(tmp_path))
    old = "For VEGA, The detector records brightness."
    new = "For study-a, The detector records brightness. It records images."
    trace = {
        "trace_id": "literal-representation",
        "verification": [
            {"statement_id": "draft-0", "text": old, "supported": True, "support_ids": ["a"]}
        ],
        "support_inventory": [{"support_id": "a", "spans": [{"evidence_id": "page"}]}],
        "redundancy_review": {
            "omissions": [
                {"text": old, "represented_by": new, "reason": "source_scoped_literal_containment"}
            ]
        },
    }
    for emitted in [True, False]:
        path = persist_claim_ledger(
            trace,
            conversation_id="c",
            response_id="r",
            question="What was recorded?",
            answer=new if emitted else "Another response.",
            citations=[{"evidence_ids": ["page"]}] if emitted else [],
        )
        claim = json.loads(path.read_text())["claims"][0]
        assert claim["communicated"] is emitted
        assert claim["represented_by"] == (new if emitted else None)
        assert claim["cited_evidence_ids"] == (["page"] if emitted else [])
