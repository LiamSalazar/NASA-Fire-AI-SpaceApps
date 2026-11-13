"""General routing controls with invented studies, unrelated to scientific targets."""

import json
from types import SimpleNamespace

from nasa_fire_ai.services.context_assembly import (
    allocate_context,
    generation_evidence,
    information_needs,
)
from nasa_fire_ai.services.conversation import ConversationService


def anchor(identity, text, document="synthetic-alpha"):
    return {
        "support_id": identity,
        "text": text,
        "document_id": document,
        "source_id": document,
        "source_title": document,
        "category": "DOCUMENTARY",
        "epistemic_type": "documentary_content",
        "spans": [{"evidence_id": identity, "text": text}],
        "conditions": [],
    }


def test_dimensions_survive_repetitive_source_and_input_permutation():
    captions = [
        anchor(f"repeat-{i}", f"Synthetic flow observation for specimen {i}.") for i in range(80)
    ]
    temperature = anchor("temperature", "Synthetic chamber temperature remained 617 K.", "beta")
    optics = anchor("optics", "Synthetic microscope recorded specimen geometry.", "gamma")
    pool = [*captions, temperature, optics]
    needs = information_needs(
        "Compare flow, temperature and microscope geometry",
        [
            {"need": "flow", "search_terms": []},
            {"need": "temperature", "search_terms": []},
            {"need": "microscope geometry", "search_terms": []},
        ],
    )
    a, receipt = allocate_context(pool, "flow temperature microscope geometry", needs, 2300)
    b, _ = allocate_context(
        list(reversed(pool)), "flow temperature microscope geometry", needs, 2300
    )
    assert {x["support_id"] for x in a} >= {"temperature", "optics"}
    assert [x["support_id"] for x in a] == [x["support_id"] for x in b]
    assert (
        receipt["context_characters"]
        == len(json.dumps([generation_evidence(x) for x in a], ensure_ascii=False))
        <= 2300
    )
    assert all(n["status"] == "CANDIDATES_SUPPLIED" for n in receipt["allocation_needs"])
    assert all("Not established" in n["sufficiency"] for n in receipt["allocation_needs"])


def test_no_match_or_insufficient_budget_is_explicit_not_a_scientific_absence():
    needs = information_needs("synthetic viscosity")
    selected, receipt = allocate_context(
        [anchor("a", "Synthetic optical detector.")], "viscosity", needs, 20
    )
    assert not selected
    assert receipt["allocation_needs"][0]["status"] == "UNRESOLVED_ROUTING"
    assert receipt["selection_decisions"][0]["reason"] == "context_budget_after_diversity_ranking"


def test_document_pages_after_early_overviews_remain_eligible():
    import sqlite3

    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.execute(
        "CREATE TABLE passages(evidence_id TEXT,document_id TEXT,page INTEGER,text TEXT,"
        "section TEXT DEFAULT 'document')"
    )
    rows = [
        (f"page-{i}", "synthetic", i, "Introduction\nSynthetic chamber overview.")
        for i in range(1, 9)
    ]
    rows.append(("late", "synthetic", 100, "The synthetic spectrometer records emission bands."))
    db.executemany("INSERT INTO passages(evidence_id,document_id,page,text) VALUES (?,?,?,?)", rows)
    resolve = lambda eid: dict(
        db.execute("SELECT * FROM passages WHERE evidence_id=?", (eid,)).fetchone()
    )
    registry = SimpleNamespace(
        db=db, resolve=resolve, source_metadata=lambda eid: {"source_id": "synthetic"}
    )
    service = ConversationService(SimpleNamespace(registry=registry), source_characters=1800)
    result = SimpleNamespace(
        claims=[],
        related=[],
        comparison=None,
        documentary=[resolve("page-1")],
        candidates=[],
        discovery=[],
    )
    selected, _ = service._inventory([result], question="spectrometer emission bands")
    assert any(a["spans"][0]["evidence_id"] == "late" for a in selected)
    assert "late" not in service.inventory_receipt["retrieved_evidence_ids"]
    assert "late" in service.inventory_receipt["available_evidence_ids"]
    assert all(a["category"] == "DOCUMENTARY" and not a.get("subject") for a in selected)
    db.close()


def test_needs_are_bounded_and_do_not_create_semantics():
    needs = information_needs("temperature and geometry", [{"need": None}, "bad"])
    assert len(needs) == 2
    assert len(information_needs("query", [{"need": "x", "search_terms": []}] * 50)) == 12
    assert information_needs("query", [{"need": "x", "search_terms": "bad"}])[0]["need"] == "query"


def test_unstructured_numeric_table_cannot_authorize_narrative_despite_nli():
    from nasa_fire_ai.services.semantic_support import verify_paraphrase

    table = "Synthetic Trial\n" + "\n".join(str(i) for i in range(12))
    a = anchor("table", table)
    registry = SimpleNamespace(resolve=lambda eid: {"text": table})

    class AlwaysEntails:
        def check(self, premise, hypothesis):
            return {"supported": True}

    check = verify_paraphrase(
        "Synthetic trials showed improved optical precision.", [a], registry, AlwaysEntails()
    )
    assert not check["supported"]
    assert "Unstructured numerical table" in check["errors"][0]
    assert verify_paraphrase(table, [a], registry, None)["supported"]


def test_unrelated_table_does_not_veto_separate_sufficient_prose():
    from nasa_fire_ai.services.semantic_support import verify_paraphrase

    table = anchor("table", "Synthetic Trial\n" + "\n".join(str(i) for i in range(12)))
    prose = anchor("prose", "The synthetic optical detector recorded emission.")
    originals = {a["support_id"]: a["text"] for a in [table, prose]}
    registry = SimpleNamespace(resolve=lambda eid: {"text": originals[eid]})
    check = verify_paraphrase(prose["text"], [table, prose], registry, None)
    assert check["supported"]
    assert check["selected_support_ids"] == ["prose"]


def test_unrelated_negative_event_cannot_establish_absence_from_a_report():
    from nasa_fire_ai.services.semantic_support import verify_paraphrase

    text = "The synthetic specimen did not emit an optical pulse."
    a = anchor("negative", text)
    registry = SimpleNamespace(resolve=lambda eid: {"text": text})

    class AlwaysEntails:
        def check(self, premise, hypothesis):
            return {"supported": True}

    proposed = "The report does not provide pressure measurements."
    check = verify_paraphrase(proposed, [a], registry, AlwaysEntails())
    assert not check["supported"]
    assert "reporting-absence" in check["errors"][0]
    original = "Pressure measurements are not reported for the synthetic trial."
    a = anchor("explicit", original)
    registry = SimpleNamespace(resolve=lambda eid: {"text": original})
    assert verify_paraphrase(proposed, [a], registry, AlwaysEntails())["supported"]


def test_modality_is_local_to_the_supporting_sentence():
    from nasa_fire_ai.services.semantic_support import verify_paraphrase

    text = "The apparatus measures droplet diameter. A future test may use an infrared camera."
    a = anchor("modal", text)
    registry = SimpleNamespace(resolve=lambda eid: {"text": text})

    class SentenceEntails:
        def check(self, premise, hypothesis):
            if "measures droplet diameter" in premise and "measures droplet diameter" in hypothesis:
                return {"supported": True}
            if "may use an infrared camera" in premise and "uses an infrared camera" in hypothesis:
                return {"supported": True}
            return {"supported": False}

    assert verify_paraphrase(
        "The apparatus measures droplet diameter.", [a], registry, SentenceEntails()
    )["supported"]
    uncertain = verify_paraphrase(
        "The apparatus uses an infrared camera.", [a], registry, SentenceEntails()
    )
    assert not uncertain["supported"]
    assert "possibility" in " ".join(uncertain["errors"])


def test_need_coverage_requires_emitted_proposition_content_not_shared_source_id():
    service = ConversationService.__new__(ConversationService)
    service.entailment = None
    need = {"need": "oxygen concentration", "support_ids": ["shared"]}
    pressure_only = [{"text": "The experiment used 2 kPa pressure.", "support_ids": ["shared"]}]
    oxygen = [
        {"text": "The experiment used 21 percent oxygen concentration.", "support_ids": ["shared"]}
    ]
    assert not service._need_is_communicated(need, pressure_only)
    # Source IDs and lexical overlap remain unconfirmed without a semantic verifier.
    assert not service._need_is_communicated(need, oxygen)
    service.entailment = SimpleNamespace(
        check=lambda premise, hypothesis: {
            "supported": premise == oxygen[0]["text"] and hypothesis == need["need"]
        }
    )
    assert not service._need_is_communicated(need, pressure_only)
    assert service._need_is_communicated(need, oxygen)


def test_generation_comparison_preserves_values_and_requested_unknown_dimensions():
    from nasa_fire_ai.query.v2 import PropertyDefinition
    from nasa_fire_ai.services.context_assembly import generation_comparison

    value_row = {
        "dimension": "Flow",
        "status": "DIFFERENT",
        "values": {
            "a": [
                {
                    "value": {"reported_value": "2", "reported_unit": "cm/s"},
                    "qualifiers": {"original_value": "2"},
                    "evidence_ids": ["E-a"],
                }
            ]
        },
    }
    requested_missing = {"dimension": "Pressure", "status": "UNKNOWN", "values": {}}
    unrelated_missing = {"dimension": "Length", "status": "UNKNOWN", "values": {}}
    comparison = {
        "run_ids": ["a", "b"],
        "matrix": [value_row, requested_missing, unrelated_missing],
        "unknown_or_unavailable_conditions": ["Pressure", "Length"],
        "limitations": ["One matching condition is not equivalence."],
    }
    properties = {
        "Pressure": PropertyDefinition(
            property_id="Pressure", dimension="pressure", canonical_unit="Pa", aliases=["pressure"]
        )
    }
    compact = generation_comparison(comparison, "Compare flow and pressure", properties)
    assert compact["matrix"] == [value_row, requested_missing]
    assert compact["matrix"][0] is value_row
    assert compact["unknown_or_unavailable_conditions"] == ["Pressure"]
    assert compact["limitations"] == comparison["limitations"]
    assert len(comparison["matrix"]) == 3
    assert "not a source-reported causal finding" in compact["epistemic_status"]
