"""Shared report pages do not merge independently attributed experiment facts."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from nasa_fire_ai.ingestion.hackathon import make_store
from nasa_fire_ai.services.conversation import ConversationService
from nasa_fire_ai.services.search import ScientificSearchService


def service():
    store = make_store(Path(__file__).resolve().parents[1])
    for identity, label in [("study-a", "VEGA"), ("study-b", "LYRA")]:
        store.add_entity(identity, "Investigation", ["page"])
        store.registry.entity_mentions[identity] = {
            "relation": "belongsToInvestigation",
            "aliases": [label],
        }
    first = "The vessel contains neon."
    second = "The vessel contains krypton."
    original = first + " " + second
    registry = SimpleNamespace(
        resolve=lambda eid: {"evidence_id": eid, "document_id": "report", "text": original},
        source_metadata=lambda eid: {"title": "Vessel comparison", "source_id": "report"},
    )
    search = SimpleNamespace(
        store=store,
        registry=registry,
        evidence_subject_contexts={
            "page": [("study-a", first), ("study-b", second), ("study-a", None)]
        },
    )
    search.passage_scientific_subjects = lambda anchor: (
        ScientificSearchService.passage_scientific_subjects(search, anchor)
    )
    search.passage_scientific_contexts = lambda anchor: (
        ScientificSearchService.passage_scientific_contexts(search, anchor)
    )
    instance = ConversationService(
        search, entailment=SimpleNamespace(check=lambda p, h: {"supported": True})
    )
    return instance, first, second, original


def anchor(text):
    return {
        "support_id": "candidate",
        "text": text,
        "document_id": "report",
        "category": "DOCUMENTARY",
        "epistemic_type": "documentary_content",
        "conditions": [],
        "spans": [{"evidence_id": "page", "text": text}],
    }


def test_an_unscoped_graph_edge_cannot_lend_another_paragraph_its_subject():
    instance, _, second, _ = service()
    candidate = instance._attach_scientific_identity(anchor(second))
    assert candidate["scientific_subjects"] == ["study-b"]
    verdict = instance._source_semantic_verdict("For VEGA, " + second, [candidate])
    assert not verdict["supported"]
    assert verdict["scientific_status"] == "ONTOLOGY_INCOMPATIBLE"


def test_initial_and_reexamined_evidence_reject_the_same_wrong_attribution():
    instance, _, second, _ = service()
    candidate = instance._attach_scientific_identity(anchor(second))
    inventory = {candidate["support_id"]: candidate}
    assert instance._realign_documentary("For VEGA, " + second, [candidate], inventory) is None
    assert instance._source_semantic_verdict("For LYRA, " + second, [candidate])["supported"]


def test_a_mixed_page_requires_narrowing_before_single_investigation_attribution():
    instance, first, _, original = service()
    broad = instance._attach_scientific_identity(anchor(original))
    assert not instance._source_semantic_verdict("For VEGA, " + first, [broad])["supported"]
    narrow = instance._attach_scientific_identity(anchor(first))
    assert instance._source_semantic_verdict("For VEGA, " + first, [narrow])["supported"]


def test_one_shared_source_statement_keeps_both_legitimate_investigations():
    instance, first, _, _ = service()
    instance.search.evidence_subject_contexts = {"page": [("study-a", first), ("study-b", first)]}
    shared = instance._attach_scientific_identity(anchor(first))
    assert len(shared["scientific_context_groups"]) == 1
    assert instance._source_semantic_verdict("For VEGA, " + first, [shared])["supported"]
    assert instance._source_semantic_verdict("For LYRA, " + first, [shared])["supported"]


def test_comparison_retains_unique_source_owner_for_a_bare_supported_finding():
    instance, first, _, _ = service()
    instance.search._evidence = instance.search.registry.resolve
    instance._requested_investigations = {"study-a", "study-b"}
    candidate = instance._attach_scientific_identity(anchor(first))
    trace = {"verification": [], "accepted_statements": [], "support_inventory": []}
    accepted, rejected = instance._accept_segments(
        [{"text": first, "support_ids": [candidate["support_id"]]}],
        {candidate["support_id"]: candidate},
        trace,
        [],
        {},
    )
    assert accepted and not rejected
    assert trace["verification"][0]["text"] == "For VEGA, " + first
    assert trace["verification"][0]["contextual_subject"]["id"] == "study-a"


@pytest.mark.parametrize("antecedent_supported", [False, True])
def test_plural_reference_cannot_survive_removal_of_its_antecedent(antecedent_supported):
    instance, first, _, _ = service()
    instance.search._evidence = instance.search.registry.resolve
    candidate = instance._attach_scientific_identity(anchor(first))
    instance._align_claim = lambda text, ids, inventory: (
        [candidate],
        {"supported": antecedent_supported if text.startswith("VEGA") else True},
    )
    instance._realign_documentary = lambda *args: None
    trace = {"verification": [], "accepted_statements": [], "support_inventory": []}
    answers, rejected = instance._accept_segments(
        [
            {"text": "VEGA reported several signals.", "support_ids": ["candidate"]},
            {"text": "These are signals from the vessel.", "support_ids": ["candidate"]},
        ],
        {"candidate": candidate},
        trace,
        [],
        {},
    )
    assert bool(answers) is antecedent_supported
    assert trace["verification"][-1]["supported"] is antecedent_supported
    if not antecedent_supported:
        assert len(rejected) == 2


def test_normative_procedure_number_does_not_resolve_to_an_experimental_run():
    from nasa_fire_ai.query.record_identity import resolve_record_mentions

    root = Path(__file__).resolve().parents[1]
    store = make_store(root)
    store.add_entity("psi-39", "Investigation", ["table"])
    store.add_entity("run-four", "ExperimentalRun", ["table"], payload={"reported_identifier": "4"})
    store.add_relation("run-four", "belongsToInvestigation", "psi-39", ["table"])
    assert resolve_record_mentions("CFI Test 4", store, root)[0] == ["run-four"]
    assert not resolve_record_mentions(
        "Test 4 in NASA-STD-6001B specimen requirements", store, root
    )[0]


@pytest.mark.parametrize(
    "label,text",
    [
        ("ISS", "İSS"),
        ("ISS", "ıss"),
        ("SOOT", "ſoot"),
        ("KELVIN", "Kelvin"),
        ("CAFÉ", "café"),
        ("BASS", "BASS-II"),
    ],
)
def test_mention_prefilter_preserves_regex_identity_and_live_classes(label, text):
    from nasa_fire_ai.services.ontology_support import _mention_pattern, _mentions

    root = Path(__file__).resolve().parents[1]
    store = make_store(root)
    store.add_entity("example-study", "Investigation", ["source"])
    store.registry.entity_mentions["example-study"] = {"aliases": [label]}
    assert bool(_mention_pattern(label).search(text))
    assert "example-study" in _mentions(text, store)
    store.registry.entity_mentions["example-study"]["aliases"] = ["UNMENTIONED"]
    assert "example-study" not in _mentions(text, store)


def test_source_sentences_keep_author_initials_and_scholarly_abbreviations():
    from nasa_fire_ai.services.conversation import paragraph_spans

    text = "The report was written by Elena Q. Harper. Figure 2 describes the optical system."
    assert list(paragraph_spans(text)) == [
        "The report was written by Elena Q. Harper.",
        "Figure 2 describes the optical system.",
    ]
    assert list(paragraph_spans("The view is shown in Fig. 2. Another camera records light.")) == [
        "The view is shown in Fig. 2.",
        "Another camera records light.",
    ]


@pytest.mark.parametrize("different_scope", [None, "study", "page", "record"])
def test_exact_source_presentation_subsumes_only_the_same_scoped_statement(different_scope):
    instance, first, _, _ = service()
    instance.max_redundancy_checks = 0
    short = "For VEGA, " + first
    full = "For study-a, " + first + " The optical sensor records brightness."
    a = {
        "support_id": "a",
        "document_id": "report",
        "scientific_subjects": ["study-a"],
        "spans": [{"evidence_id": "page", "text": first}],
    }
    b = {**a, "support_id": "b"}
    if different_scope == "study":
        b = {**b, "scientific_subjects": ["study-b"]}
    elif different_scope == "page":
        b = {**b, "spans": [{"evidence_id": "another-page", "text": first}]}
    elif different_scope == "record":
        b = {**b, "structured_record_id": "another-record"}
    trace = {
        "support_inventory": [a, b],
        "accepted_statements": [
            {"text": short, "support_ids": ["a"]},
            {"text": full, "support_ids": ["b"]},
        ],
    }
    actual = instance._deduplicate_answer([short, full], trace)
    assert actual == ([full] if different_scope is None else [short, full])
    if different_scope is None:
        assert (
            trace["redundancy_review"]["omissions"][0]["reason"]
            == "source_scoped_literal_containment"
        )


@pytest.mark.parametrize(
    "question", ["What findings does VEGA report?", "What behavior did VEGA report?"]
)
def test_graph_recovery_reaches_the_normal_verifier_with_a_valid_ledger_target(question):
    instance, first, _, _ = service()
    store = instance.search.store
    store.add_entity("finding-a", "SourceReportedFinding", ["page"], payload={"text": first})
    store.add_relation("study-a", "hasReportedFinding", "finding-a", ["page"])
    instance.search._evidence = instance.search.registry.resolve
    instance._requested_investigations = {"study-a"}
    inventory = {}
    proposals = instance._graph_source_completion(question, inventory, [])
    assert proposals
    trace = {
        "verification": [],
        "accepted_statements": [],
        "support_inventory": [],
        "verification_stage": "repair-graph-context",
        "repair_targets": [proposal["repair_of"] for proposal in proposals],
    }
    answer, rejected = instance._accept_segments(proposals, inventory, trace, [], {})
    assert answer and not rejected
    assert trace["verification"][0]["supported"]
    assert trace["verification"][0]["repair_of"] == proposals[0]["repair_of"]


def test_grounded_identity_metadata_is_separate_from_scientific_entailment():
    from nasa_fire_ai.services.semantic_support import verify_paraphrase

    original = "The vessel contains neon, while the auxiliary sensor records brightness."
    candidate = anchor(original)
    candidate.update(
        scientific_subjects=["study-a"],
        source_aliases=["VEGA"],
        identity_context="Registered investigation aliases: VEGA, Violet Apparatus, Study A.",
    )
    registry = SimpleNamespace(resolve=lambda eid: {"text": original})
    model = SimpleNamespace(
        check=lambda premise, claim: {
            "supported": premise == original and claim == "the vessel contains neon.",
        }
    )
    assert verify_paraphrase("For VEGA, the vessel contains neon.", [candidate], registry, model)[
        "supported"
    ]
    assert not verify_paraphrase(
        "For LYRA, the vessel contains neon.", [candidate], registry, model
    )["supported"]


def test_identifier_column_name_does_not_become_another_investigation():
    from nasa_fire_ai.services.ontology_support import investigation_mentions, leading_investigation

    instance, _, _, _ = service()
    instance.search.store.registry.identifier_headers = ["VEGA Number"]
    assert investigation_mentions(
        "For LYRA, the VEGA Number field is 17.", instance.search.store
    ) == {"study-b"}
    assert leading_investigation("The VEGA Number field is 17.", instance.search.store) is None
    assert (
        leading_investigation("For VEGA, the vessel contains neon.", instance.search.store)["id"]
        == "study-a"
    )


def test_causal_boundary_is_assistant_policy_and_requires_verified_record_values():
    instance, _, _, _ = service()
    instance._explicit_record_subjects = {"record-a"}
    inventory = {
        "value": {
            "projection_verified": True,
            "structured_record_id": "value-a",
            "projection_kind": "reported_quantity",
        }
    }
    accepted = [{"text": "The recorded flow is 7 cm/s.", "support_ids": ["value"]}]
    assert instance._causal_analysis_boundary(
        "Does this justify attributing a cause?", inventory, accepted
    )
    assert (
        instance._causal_analysis_boundary("List the recorded flow.", inventory, accepted) is None
    )
    assert instance._causal_analysis_boundary("What caused this?", {}, accepted) is None
    assert (
        instance._causal_analysis_boundary(
            "What caused this?",
            inventory,
            accepted
            + [
                {"text": "The source attributes the change to the inlet.", "support_ids": ["value"]}
            ],
        )
        is None
    )


@pytest.mark.parametrize("prefix", ["study-a", "VEGA"])
def test_original_graph_paragraph_keeps_its_document_local_antecedent(prefix):
    instance, _, _, _ = service()
    original = "The purpose of this report is to archive the measurements. It is not intended to interpret them."
    instance.search.registry.resolve = lambda eid: {
        "evidence_id": eid,
        "document_id": "report",
        "text": original,
    }
    instance.search.evidence_subject_contexts = {"page": [("study-a", original)]}
    instance.search._evidence = instance.search.registry.resolve
    candidate = anchor(original)
    candidate["graph_context_id"] = "scope-description"
    instance._attach_scientific_identity(candidate)
    trace = {
        "verification": [],
        "accepted_statements": [],
        "support_inventory": [],
        "verification_stage": "repair-graph-context",
        "repair_targets": ["coverage-description"],
    }
    answers, rejected = instance._accept_segments(
        [
            {
                "text": f"For {prefix}, " + original,
                "support_ids": ["candidate"],
                "repair_of": "coverage-description",
            }
        ],
        {"candidate": candidate},
        trace,
        [],
        {},
    )
    assert answers and not rejected
    assert len(trace["accepted_statements"]) == 1
    assert "It is not intended" in answers[0]
    assert "study-a is not intended" not in answers[0]


def test_explicit_document_scope_does_not_recover_unrequested_document():
    instance, _, _, _ = service()
    original = "The cobalt containers were sealed and clean before the violet procedure."
    candidate = anchor(original)
    candidate.update(document_id="unrelated-document", source_id="unrelated-document")
    instance.search.registry.resolve = lambda eid: {"text": original}
    instance._requested_document_sources = {"requested-document"}
    instance._document_definition_cache = {"unrelated-document": []}
    assert not instance._documentary_need_completion(
        [{"need": "sealed clean cobalt containers"}], {"candidate": candidate}, []
    )
