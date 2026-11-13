from types import SimpleNamespace

from nasa_fire_ai.query.native import SemanticGraph
from nasa_fire_ai.query.v2 import RelationDefinition, SemanticRegistry
from nasa_fire_ai.services.conversation import ConversationService
from nasa_fire_ai.services.ontology_support import audit_relation


def fixture():
    registry = SemanticRegistry(
        target_classes={"Investigation", "Material"},
        information_classes={"Investigation", "Material"},
        relations=[
            RelationDefinition(
                "usesMaterial",
                domain=["Investigation"],
                range=["Material"],
                aliases=["uses"],
            )
        ],
    )
    registry.entity_mentions = {
        "study-a": {"aliases": ["Study A"]},
        "alloy-b": {"aliases": ["Alloy B"]},
    }
    graph = SemanticGraph(registry)
    graph.add_entity("study-a", "Investigation", ["source-1"])
    graph.add_entity("alloy-b", "Material", ["source-1"])
    evidence = SimpleNamespace(
        resolve=lambda eid: {"text": "original"} if eid == "source-1" else None
    )
    anchor = {"spans": [{"evidence_id": "source-1", "text": "original"}]}
    return graph, evidence, anchor


def test_graph_relation_requires_registered_source_overlap():
    graph, evidence, anchor = fixture()
    graph.add_relation("study-a", "usesMaterial", "alloy-b", ["source-1"])
    supported = audit_relation("Study A uses Alloy B.", [anchor], graph, evidence)
    assert supported["scientific_status"] == "GRAPH_SUPPORTED_CANDIDATE"
    assert supported["graph_evidence_ids"] == ["source-1"]
    unrelated = audit_relation(
        "Study A uses Alloy B.", [{"spans": [{"evidence_id": "elsewhere"}]}], graph, evidence
    )
    assert unrelated["scientific_status"] == "DOCUMENTARY_CANDIDATE"


def test_open_world_documentary_relation_and_incompatible_endpoints():
    graph, evidence, anchor = fixture()
    assert (
        audit_relation("Study A uses Alloy B.", [anchor], graph, evidence)["scientific_status"]
        == "DOCUMENTARY_CANDIDATE"
    )
    assert (
        audit_relation("Alloy B uses Study A.", [anchor], graph, evidence)["scientific_status"]
        == "ONTOLOGY_INCOMPATIBLE"
    )


def test_pronoun_resolves_from_verified_same_segment_referent():
    graph, _, _ = fixture()
    texts = {"first": "Study A contains a vessel.", "second": "Study A uses Alloy B."}
    anchors = {
        key: {
            "support_id": key,
            "text": value,
            "spans": [{"evidence_id": key, "text": value}],
            "category": "DOCUMENTARY",
            "epistemic_type": "documentary_content",
            "conditions": [],
        }
        for key, value in texts.items()
    }
    registry = SimpleNamespace(resolve=lambda eid: {"text": texts[eid]})
    search = SimpleNamespace(
        store=graph,
        registry=registry,
        _evidence=lambda eid: {
            "evidence_id": eid,
            "text": texts[eid],
            "source": {"source_id": eid},
        },
    )
    entailment = SimpleNamespace(
        check=lambda premise, hypothesis: {"supported": hypothesis in premise}
    )
    service = ConversationService(search, entailment=entailment)
    trace = {"verification": []}
    accepted, rejected = service._accept_segments(
        [{"text": "Study A contains a vessel. It uses Alloy B."}], anchors, trace, [], {}
    )
    assert not rejected
    assert any("Study A uses Alloy B." in paragraph for paragraph in accepted)
    assert trace["verification"][1]["scientific_status"] == "DOCUMENT_SUPPORTED"


def test_incompatible_explicit_relation_cannot_pass_exact_documentary_match():
    graph, _, _ = fixture()
    text = "Alloy B uses Study A."
    evidence = SimpleNamespace(resolve=lambda eid: {"text": text})
    search = SimpleNamespace(store=graph, registry=evidence)
    service = ConversationService(
        search, entailment=SimpleNamespace(check=lambda p, h: {"supported": h in p})
    )
    anchor = {
        "support_id": "proof",
        "text": text,
        "spans": [{"evidence_id": "proof", "text": text}],
        "category": "DOCUMENTARY",
        "epistemic_type": "documentary_content",
        "conditions": [],
    }
    _, verdict = service._align_claim(text, [], {"proof": anchor})
    assert not verdict["supported"]


def test_relation_constraints_precede_entailment(monkeypatch):
    from nasa_fire_ai.services import conversation

    def forbidden(*args, **kwargs):
        raise AssertionError("Source entailment ran before relation constraints")

    monkeypatch.setattr(conversation, "verify_paraphrase", forbidden)
    test_incompatible_explicit_relation_cannot_pass_exact_documentary_match()


def test_context_identity_survives_an_unsupported_first_proposition():
    graph, _, _ = fixture()
    graph.registry.entity_mentions["study-a"]["relation"] = "belongsToInvestigation"
    source = "Study A records the vessel luminosity."
    registry = SimpleNamespace(resolve=lambda eid: {"text": source})
    search = SimpleNamespace(
        store=graph,
        registry=registry,
        _evidence=lambda eid: {"evidence_id": eid, "text": source, "source": {"source_id": "s"}},
    )
    service = ConversationService(search)
    anchor = {
        "support_id": "a",
        "text": source,
        "spans": [{"evidence_id": "e", "text": source}],
        "category": "DOCUMENTARY",
        "epistemic_type": "documentary_content",
        "conditions": [],
    }
    seen = []

    def align(text, proposed, inventory):
        seen.append(text)
        return [anchor], {"supported": False, "reason": "Independent scientific check"}

    service._align_claim = align
    trace = {"verification": []}
    service._accept_segments(
        [{"text": "Study A has an unsupported condition. The vessel records luminosity."}],
        {"a": anchor},
        trace,
        [],
        {},
    )
    assert seen == [
        "Study A has an unsupported condition.",
        "For Study A, The vessel records luminosity.",
    ]
    assert all(not item["supported"] for item in trace["verification"])


def test_leading_investigation_uses_longest_scientific_alias():
    from nasa_fire_ai.services.ontology_support import leading_investigation

    graph, _, _ = fixture()
    graph.registry.entity_mentions = {
        "alpha": {"relation": "belongsToInvestigation", "aliases": ["Study A"]},
        "beta": {"relation": "belongsToInvestigation", "aliases": ["Study A-2"]},
    }
    assert leading_investigation("Study A-2 reports a result.", graph)["id"] == "beta"


def test_deictic_record_reference_is_not_an_acronym_identity():
    from nasa_fire_ai.services.ontology_support import leading_investigation

    graph, _, _ = fixture()
    graph.registry.entity_mentions = {
        "synthetic-a": {"relation": "belongsToInvestigation", "aliases": ["FORMER"]}
    }
    assert leading_investigation("The former record gives a duration.", graph) is None
    assert (
        leading_investigation("FORMER describes its scientific objectives.", graph)["id"]
        == "synthetic-a"
    )


def test_typed_record_scope_rejects_another_investigation_before_entailment():
    graph, evidence, anchor = fixture()
    graph.registry.entity_mentions["study-a"]["relation"] = "belongsToInvestigation"
    anchor.update(
        scientific_subjects=["study-c"], typed_fields=[{"property_id": "SyntheticSignal"}]
    )
    result = audit_relation("Study A records a signal.", [anchor], graph, evidence)
    assert result["scientific_status"] == "ONTOLOGY_INCOMPATIBLE"
    anchor["scientific_subjects"] = ["study-a"]
    assert (
        audit_relation("Study A records a signal.", [anchor], graph, evidence)["scientific_status"]
        == "DOCUMENTARY_CANDIDATE"
    )
