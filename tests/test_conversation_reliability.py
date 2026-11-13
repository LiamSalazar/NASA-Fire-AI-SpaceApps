"""Evidence preservation, focused repair, independent status and coverage controls."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from nasa_fire_ai.services.conversation import ChatRequest, ConversationService
from nasa_fire_ai.services.search import ScientificSearchService
from nasa_fire_ai.services.semantic_support import verify_paraphrase

ROOT = Path(__file__).resolve().parents[1]


class ExactSupport:
    def check(self, premise, hypothesis):
        return {"supported": hypothesis.strip() in premise}


def anchor(identity, text, **extra):
    return {
        "support_id": identity,
        "text": text,
        "spans": [{"evidence_id": identity, "text": text}],
        "category": "DOCUMENTARY",
        "epistemic_type": "documentary_content",
        "conditions": [],
        **extra,
    }


def service_with_sources(anchors):
    by_id = {a["support_id"]: a for a in anchors}
    registry = SimpleNamespace(resolve=lambda eid: {"text": by_id[eid]["text"]})
    search = SimpleNamespace(
        registry=registry,
        _evidence=lambda eid: {
            "evidence_id": eid,
            "text": by_id[eid]["text"],
            "source": {"source_id": eid},
        },
    )
    return ConversationService(search, entailment=ExactSupport())


def test_compound_answer_keeps_supported_sentence_and_rejects_causal_invention():
    a = anchor("source", "The synthetic chamber contained argon.")
    service = service_with_sources([a])
    trace, citations = {"verification": []}, []
    accepted, rejected = service._accept_segments(
        [{"text": a["text"] + " Argon caused universal stability.", "support_ids": ["source"]}],
        {"source": a},
        trace,
        citations,
        {},
    )
    assert len(accepted) == 1 and len(rejected) == 1
    assert "caused" not in accepted[0]
    assert trace["verification"][0]["parent_segment"] == trace["verification"][1]["parent_segment"]


def test_original_csv_rows_keep_distinct_public_citation_locations():
    anchors = [
        anchor("row-a", "The synthetic vessel contains neon."),
        anchor("row-b", "The synthetic vessel contains krypton."),
    ]
    service = service_with_sources(anchors)
    original = service.search._evidence
    service.search._evidence = lambda eid: {
        **original(eid),
        "source": {"source_id": "one-table"},
        "checksum": "same-original-file",
        "structured_location": {"kind": "table_row", "row_ordinal": 8 if eid == "row-a" else 9},
    }
    citations = []
    accepted, rejected = service._accept_segments(
        [{"text": a["text"], "support_ids": [a["support_id"]]} for a in anchors],
        {a["support_id"]: a for a in anchors},
        {"verification": []},
        citations,
        {},
    )
    assert len(accepted) == 2 and not rejected
    assert len(citations) == 2
    assert {c["structured_location"]["row_ordinal"] for c in citations} == {8, 9}


def test_unrelated_modality_does_not_veto_sufficient_support_or_receive_citation():
    good = anchor("fact", "The synthetic chamber contained argon.")
    unrelated = anchor("plan", "The future sensor may detect a different signal.")
    service = service_with_sources([good, unrelated])
    citations = []
    accepted, rejected = service._accept_segments(
        [{"text": good["text"], "support_ids": ["fact", "plan"]}],
        {a["support_id"]: a for a in [good, unrelated]},
        {"verification": []},
        citations,
        {},
    )
    assert accepted and not rejected
    assert {eid for c in citations for eid in c["evidence_ids"]} == {"fact"}


def test_same_document_support_reexamination_does_not_cross_documents():
    hint = anchor("intro", "The synthetic report describes an apparatus.", document_id="doc-a")
    correct = anchor("method", "The synthetic chamber contained argon.", document_id="doc-a")
    foreign = anchor("foreign", "The synthetic chamber contained argon.", document_id="doc-b")
    service = service_with_sources([hint, correct, foreign])
    assert service._realign_documentary(correct["text"], [hint], {"foreign": foreign}) is None
    resolved = service._realign_documentary(correct["text"], [hint], {"method": correct})
    assert resolved[0][0]["support_id"] == "method"


def test_identifier_cannot_supply_measurement_or_wrong_run():
    a = anchor("record", "Run SYN-417 had a mass of 8 g.")
    registry = SimpleNamespace(resolve=lambda eid: {"text": a["text"]})
    assert not verify_paraphrase("Run SYN-418 had a mass of 8 g.", [a], registry, ExactSupport())[
        "supported"
    ]
    assert not verify_paraphrase("The mass was 417 g.", [a], registry, ExactSupport())["supported"]


def test_backend_source_identifier_is_attribution_not_a_measurement():
    text = "The synthetic report documents an argon chamber."
    a = anchor("record", text, source_id="report-482", document_id="report-482")
    registry = SimpleNamespace(resolve=lambda eid: {"text": text})

    class AttributionSupport:
        def check(self, premise, hypothesis):
            return {"supported": "argon chamber" in premise and "argon chamber" in hypothesis}

    assert verify_paraphrase(
        "Report report-482 documents an argon chamber.", [a], registry, AttributionSupport()
    )["supported"]
    assert not verify_paraphrase(
        "Report report-483 documents an argon chamber.", [a], registry, AttributionSupport()
    )["supported"]
    assert not verify_paraphrase(
        "Report report-482 measured 482 g.", [a], registry, AttributionSupport()
    )["supported"]


def test_remedy_cannot_bind_separate_measurements_through_joint_entailment():
    noise = "Synthetic sensor Alpha exhibited excess jitter."
    remedy = "Synthetic sensor Beta underwent recalibration."
    proposed = "Synthetic sensor Alpha exhibited excess jitter, addressed by recalibration."
    sources = {"alpha": noise, "beta": remedy, "combined": noise + " " + remedy}
    registry = SimpleNamespace(resolve=lambda eid: {"text": sources[eid]})

    class JointFalsePositive:
        def check(self, premise, hypothesis):
            return {"supported": noise in premise and remedy in premise}

    for anchors in [
        [anchor("alpha", noise), anchor("beta", remedy)],
        [anchor("combined", sources["combined"])],
    ]:
        verdict = verify_paraphrase(proposed, anchors, registry, JointFalsePositive())
        assert not verdict["supported"]
        assert "Remedy attribution" in verdict["errors"][0]

    faithful = "Synthetic sensor Alpha jitter was corrected by recalibration."
    registry = SimpleNamespace(resolve=lambda eid: {"text": faithful})
    assert verify_paraphrase(faithful, [anchor("faithful", faithful)], registry, ExactSupport())[
        "supported"
    ]


@pytest.fixture(scope="module")
def engine():
    search = ScientificSearchService(ROOT / "data/snapshots/hackathon-20261105-v9", ROOT)
    yield search
    search.close()


class RepairProvider:
    def plan(self, question, history, max_queries):
        self.history = history
        return {"resolved_question": question, "queries": [], "use_previous_sources": bool(history)}

    def explain(self, payload, max_tokens):
        source = next(
            a for a in payload["evidence"] if a["epistemic_type"] == "documentary_content"
        )
        if payload.get("rejected_segments"):
            self.repair_payload = payload
            return {
                "segments": [
                    {
                        "text": source["text"],
                        "support_ids": [source["support_id"]],
                        "repair_of": payload["rejected_segments"][0]["statement_id"],
                    }
                ]
            }
        self.initial = source
        return {
            "segments": [
                {"text": "FABRICATED causal result.", "support_ids": [source["support_id"]]}
            ],
            "answer_plan": [
                {
                    "need": "Source description",
                    "support_ids": [source["support_id"]],
                    "status": "documented",
                }
            ],
        }


def test_repair_preserves_identity_and_success_does_not_mean_provider_failure(engine):
    class NoFabrication:
        def check(self, premise, hypothesis):
            return {"supported": "FABRICATED" not in hypothesis}

    provider = RepairProvider()
    service = ConversationService(engine, provider=provider, entailment=NoFabrication())
    response = service.chat(ChatRequest(message="droplet combustion diagnostics", max_queries=1))
    assert "FABRICATED" not in response.answer
    assert response.provider_status["status"] == "AVAILABLE"
    assert response.generation_status["status"] == "SUCCEEDED"
    assert response.verification_status["status"] == "REPAIRED"
    assert response.verification_status["repaired_claim_count"] > 0
    assert response.generation_status["repair_attempts"] == 1
    trace = service.traces[response.trace_id]
    assert trace["repairs"][0]["permitted_support_ids"]
    assert trace["accepted_statements"][0]["repair_of"] == "draft-0"
    assert response.coverage_summary["communicated_evidence_ids"]
    assert "already_accepted" in provider.repair_payload


def test_repair_must_link_to_rejection_and_obey_budget(engine):
    provider = RepairProvider()
    service = ConversationService(
        engine, provider=provider, entailment=ExactSupport(), max_repair_attempts=0
    )
    response = service.chat(ChatRequest(message="droplet combustion diagnostics", max_queries=1))
    assert response.generation_status["repair_attempts"] == 0
    assert "FABRICATED" not in response.answer
    assert response.answer_completeness["status"] == "NO_VERIFIED_EXPLANATION"


def test_inventory_examines_retained_candidates_beyond_display_slice(engine):
    result = engine.search("droplet imaging diagnostics", limit=1)
    service = ConversationService(engine)
    inventory, omitted = service._inventory([result], question="droplet imaging diagnostics")
    supplied = {s["evidence_id"] for a in inventory for s in a["spans"]}
    assert supplied - {r["evidence_id"] for r in result.documentary}
    assert service.inventory_receipt["omitted_anchors"] == omitted
    assert service.inventory_receipt["context_characters"] <= service.source_characters


def test_relevance_omissions_are_separate_from_fidelity(engine):
    class Provider(RepairProvider):
        def explain(self, payload, max_tokens):
            a = next(a for a in payload["evidence"] if a["epistemic_type"] == "documentary_content")
            return {"segments": [{"text": a["text"], "support_ids": [a["support_id"]]}]}

        def organize(self, *args):
            return {"retained_indices": []}

    service = ConversationService(engine, provider=Provider(), entailment=ExactSupport())
    response = service.chat(ChatRequest(message="combustion diagnostics", max_queries=1))
    trace = service.traces[response.trace_id]
    assert trace["relevance_omissions"]
    assert trace["relevance_restored"] == trace["relevance_omissions"]
    assert response.verification_status["communicated_generated_claim_count"] == 1
    assert trace["relevance_review"]["retained_indices"] == []
    assert response.verification_status["retained_claim_count"] >= 1


def test_support_selection_cannot_hide_known_conflicted_conditions():
    first = anchor(
        "first", "The synthetic chamber contained argon.", conditions=[{"status": "CONFLICT"}]
    )
    second = anchor("second", first["text"])
    registry = SimpleNamespace(resolve=lambda eid: {"text": first["text"]})
    assert not verify_paraphrase(first["text"], [first, second], registry, ExactSupport())[
        "supported"
    ]


def test_hyphenated_quantity_is_typography_not_a_unit_conversion():
    a = anchor("record", "The synthetic chamber pressure was 8-atm.")
    registry = SimpleNamespace(resolve=lambda eid: {"text": a["text"]})

    class Meaning:
        def check(self, premise, hypothesis):
            return {"supported": True}

    assert verify_paraphrase("The synthetic chamber pressure was 8 atm.", [a], registry, Meaning())[
        "supported"
    ]
    assert not verify_paraphrase(
        "The synthetic chamber pressure was 8 kPa.", [a], registry, Meaning()
    )["supported"]


def test_nli_memoization_does_not_cache_source_integrity_authorization():
    import snowballstemmer

    from nasa_fire_ai.services.semantic_support import LocalEntailment

    verifier = LocalEntailment.__new__(LocalEntailment)
    verifier.stemmer = snowballstemmer.stemmer("english")
    calls = []
    verifier._infer = lambda source, text: calls.append((source, text)) or {"supported": True}
    source = {"text": "The synthetic chamber pressure was 8-atm."}
    registry = SimpleNamespace(resolve=lambda eid: source)
    a = anchor("record", source["text"])
    text = "The synthetic chamber pressure was 8 atm."
    assert verify_paraphrase(text, [a], registry, verifier)["supported"]
    assert verify_paraphrase(text, [a], registry, verifier)["supported"]
    assert len(calls) == 1
    source["text"] = "The synthetic chamber pressure was 9-atm."
    assert not verify_paraphrase(text, [a], registry, verifier)["supported"]


def test_empty_generation_receives_bounded_coverage_repair(engine):
    class Provider(RepairProvider):
        def explain(self, payload, max_tokens):
            if not payload.get("rejected_segments"):
                return {"segments": [], "answer_plan": []}
            assert payload["rejected_segments"][0]["kind"] == "coverage_gap"
            return super().explain(payload, max_tokens)

    class NoFabrication:
        def check(self, premise, hypothesis):
            return {"supported": "FABRICATED" not in hypothesis}

    service = ConversationService(engine, provider=Provider(), entailment=NoFabrication())
    result = service.chat(ChatRequest(message="droplet combustion diagnostics", max_queries=1))
    assert result.generation_status["repair_attempts"] == 1
    assert result.provider_status["response_mode"] == "generated"
    assert result.verification_status["communicated_generated_claim_count"] > 0
    assert service.traces[result.trace_id]["coverage_gaps"]


def test_known_inline_support_markers_are_not_scientific_measurements():
    a = anchor("d-synthetic7946", "The synthetic chamber contained argon.")
    service = service_with_sources([a])
    trace, citations = {"verification": []}, []
    accepted, rejected = service._accept_segments(
        [
            {"text": a["text"] + " [d-synthetic7946]", "support_ids": [a["support_id"]]},
            {
                "text": "The synthetic mass was 7946 g. [d-synthetic7946]",
                "support_ids": [a["support_id"]],
            },
            {"text": a["text"] + " [NASA-FAKE-999]", "support_ids": [a["support_id"]]},
        ],
        {a["support_id"]: a},
        trace,
        citations,
        {},
    )
    assert len(accepted) == 1 and len(rejected) == 2
    assert "7946" not in accepted[0]
    assert citations[0]["evidence_ids"] == [a["support_id"]]


def test_inline_proposed_locator_can_recover_correct_support_without_fabrication():
    right = anchor("d-correct417", "The synthetic chamber contained argon.")
    wrong = anchor("d-wrong418", "A future probe may inspect a separate specimen.")
    service = service_with_sources([right, wrong])
    citations = []
    accepted, rejected = service._accept_segments(
        [{"text": right["text"] + " [d-correct417]", "support_ids": [wrong["support_id"]]}],
        {a["support_id"]: a for a in [right, wrong]},
        {"verification": []},
        citations,
        {},
    )
    assert accepted and not rejected
    assert {eid for c in citations for eid in c["evidence_ids"]} == {right["support_id"]}


def test_backend_locates_uncited_claim_and_overrides_wrong_model_hint():
    right = anchor("registered-method", "The synthetic chamber contained argon.")
    wrong = anchor("registered-plan", "A future probe may inspect another specimen.")
    service = service_with_sources([right, wrong])
    for proposal in (
        {"text": right["text"]},
        {"text": right["text"], "support_ids": [wrong["support_id"]]},
        {"text": right["text"], "support_ids": ["invented-id"]},
    ):
        citations = []
        trace = {"verification": []}
        accepted, rejected = service._accept_segments(
            [proposal], {a["support_id"]: a for a in [right, wrong]}, trace, citations, {}
        )
        assert accepted and not rejected
        assert {eid for c in citations for eid in c["evidence_ids"]} == {right["support_id"]}
        assert trace["verification"][0]["matched_support_ids"]


def test_backend_rejects_uncited_invention_without_fabricating_citation():
    source = anchor("registered-method", "The synthetic chamber contained argon.")
    service = service_with_sources([source])
    citations = []
    accepted, rejected = service._accept_segments(
        [{"text": "The synthetic chamber contained neon."}],
        {source["support_id"]: source},
        {"verification": []},
        citations,
        {},
    )
    assert not accepted and rejected and not citations


def test_descriptive_clause_keeps_supported_parts_and_rejects_invented_dimension():
    material = anchor("material", "ASTRA uses argon canisters.")
    dimensions = anchor("dimensions", "ASTRA uses 8 g cylinders.")
    service = service_with_sources([material, dimensions])
    trace = {"verification": []}
    accepted, rejected = service._accept_segments(
        [{"text": "ASTRA uses argon canisters, described as 9 g cylinders."}],
        {a["support_id"]: a for a in [material, dimensions]},
        trace,
        [],
        {},
    )
    assert len(accepted) == 1 and len(rejected) == 1
    assert "argon canisters" in accepted[0] and "9 g" not in accepted[0]
    assert trace["verification"][0]["original_text"] == trace["verification"][1]["original_text"]


def test_bounded_package_absence_cannot_borrow_unrelated_negative_source():
    source = anchor("observation", "No visible vapor cloud formed after the synthetic test.")
    registry = SimpleNamespace(resolve=lambda eid: {"text": source["text"]})

    class FalsePositive:
        def check(self, premise, hypothesis):
            return {"supported": True, "probabilities": {"entailment": 0.99}}

    claim = "The supplied materials do not contain a document titled Synthetic Flame Study."
    verdict = verify_paraphrase(claim, [source], registry, FalsePositive())
    assert not verdict["supported"]
    assert "package-wide absence" in verdict["errors"][0]
    catalogue_claim = "No synthetic measurements appear in the supplied catalogue text."
    assert not verify_paraphrase(catalogue_claim, [source], registry, FalsePositive())["supported"]


def test_pronoun_only_subject_cannot_take_a_related_document_citation():
    source = anchor("standard", "The synthetic standard provides configuration criteria.")
    service = service_with_sources([source])
    citations = []
    accepted, rejected = service._accept_segments(
        [{"text": "It provides configuration criteria."}],
        {source["support_id"]: source},
        {"verification": [], "verification_stage": "draft"},
        citations,
        {},
    )
    assert not accepted and rejected and not citations


def test_catalogue_plan_keeps_selected_source_after_documentary_deduplication(engine, monkeypatch):
    original_search = engine.search

    def search(*args, **kwargs):
        result = original_search(*args, **kwargs)
        return result.model_copy(
            update={
                "candidates": [
                    {**row, "category": "DOCUMENTARY"}
                    if row.get("text", "").startswith('{"accession"')
                    else row
                    for row in result.candidates
                ]
            }
        )

    monkeypatch.setattr(engine, "search", search)

    class Provider:
        def plan(self, question, history, max_queries):
            return {"resolved_question": question, "queries": []}

        def explain(self, payload, max_tokens):
            source = next(
                r
                for r in payload["discovery_candidates"]
                if "catalog" in r.get("source", {}).get("source_type", "").lower()
            )
            return {
                "segments": [],
                "answer_plan": [
                    {
                        "need": "Inspect potential sources",
                        "support_ids": [source["evidence_id"]],
                        "status": "exploratory",
                    }
                ],
                "exploratory_source_ids": [source["evidence_id"]],
                "exploration_queries": ["additional combustion diagnostics investigations"],
            }

    service = ConversationService(engine, provider=Provider(), max_repair_attempts=0)
    result = service.chat(ChatRequest(message="FLEX extinction investigations", max_queries=1))
    assert result.provider_status["response_mode"] == "candidate_metadata"
    assert result.citations and result.citations[0]["category"] == "DISCOVERY"
    assert "additional combustion diagnostics investigations" in result.answer
    assert "Source excerpts" not in result.answer
    assert result.verification_status["communicated_generated_claim_count"] == 0
