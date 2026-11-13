"""Staged proposals are validated apart, and only curation reviews or publishes; synthetic data."""

import pytest
from test_curation import compatible
from test_curation import curator as _curator

from nasa_fire_ai.ingestion.proposal_states import structural_validation

curator = _curator
APPROVED = {"class": {"ExperimentalRun"}, "relation": {"hasMaterial"}}
EVIDENCE = [{"evidence_id": "E-1", "start": 0, "end": 10, "quote": "Beta coil"}]


def proposal(**changes):
    base = {
        "kind": "class",
        "term": "IgniterCoil",
        "definition": "NOT_ESTABLISHED_BY_SOURCE",
        "evidence": EVIDENCE,
        "activation": "NONE",
    }
    return {**base, **changes}


def test_a_new_term_with_evidence_is_well_formed_and_awaits_placement():
    check = structural_validation(proposal(), APPROVED)
    assert check["well_formed"] and check["errors"] == []
    assert check["placement"] == "PARENT_NOT_ESTABLISHED_REQUIRES_REVIEW"
    assert check["reuse_analysis"]["case"] == "C_NEW_VOCABULARY"


@pytest.mark.parametrize(
    "changes,error",
    [
        ({"term": "ExperimentalRun"}, "TERM_ALREADY_APPROVED"),
        ({"term": "experimentalrun"}, "TERM_DIFFERS_FROM_AN_APPROVED_TERM_ONLY_BY_CASE"),
        ({"term": "igniter coil"}, "TERM_IS_NOT_AN_IDENTIFIER"),
        ({"evidence": []}, "EVIDENCE_ANCHORS_MISSING"),
        ({"activation": "ACTIVE"}, "EXTENSION_ACTIVATED_OUTSIDE_REVIEW"),
        ({"definition": "A coil that ignites samples."}, "DEFINITION_WITHOUT_SOURCE_EVIDENCE"),
        ({"kind": "relation", "term": "ignitedBy"}, "RELATION_DOMAIN_OR_RANGE_UNKNOWN"),
    ],
)
def test_a_malformed_proposal_names_its_defect(changes, error):
    check = structural_validation(proposal(**changes), APPROVED)
    assert not check["well_formed"] and error in check["errors"]


def test_approving_an_unknown_extension_is_a_clear_error(curator):
    saved = compatible(curator)
    with pytest.raises(ValueError, match="No staged extension"):
        curator.approve_extension(saved["package"]["id"], "NoSuchTerm", "test-scientist")


def test_reviewed_and_published_states_come_only_from_curation(curator):
    saved = compatible(curator)
    package = saved["package"]
    package["scientific_extraction"] = {
        "records": [
            {
                "id": "r-supported",
                "kind": "entities",
                # A record the projection publishes: an entity of this package.
                "entity_id": package["entities"][1]["id"],
                "status": "SOURCE_SUPPORTED",
                "proposal_state": "SOURCE_SUPPORTED",
            },
            {
                "id": "r-extension",
                "status": "UNRESOLVED",
                "proposal_state": "PROPOSED_ONTOLOGY_EXTENSION",
            },
            {"id": "r-open", "status": "UNRESOLVED", "proposal_state": "STRUCTURALLY_WELL_FORMED"},
            {"id": "r-rejected", "status": "REJECTED", "proposal_state": "REJECTED"},
        ]
    }
    pid = curator.save(package, "test-scientist")["package"]["id"]
    digest = curator.get(pid)["digest"]
    db = curator.registry.db
    assert set(curator.proposal_states(pid).values()) == {
        "SOURCE_SUPPORTED",
        "PROPOSED_ONTOLOGY_EXTENSION",
        "STRUCTURALLY_WELL_FORMED",
        "REJECTED",
    }
    db.execute(
        "INSERT INTO research_approvals VALUES (?,?,?,?,?)",
        (digest, "test-scientist", "t", 1, "{}"),
    )
    reviewed = curator.proposal_states(pid)
    assert reviewed["r-supported"] == reviewed["r-extension"] == "SCIENTIFICALLY_REVIEWED"
    assert reviewed["r-open"] == "STRUCTURALLY_WELL_FORMED" and reviewed["r-rejected"] == "REJECTED"
    db.execute("INSERT INTO research_active VALUES (?,?)", (pid, digest))
    published = curator.proposal_states(pid)
    assert published["r-supported"] == "AUTHORIZED_PUBLISHED"
    # Staging is not publication: a record needing an unapproved term stays reviewed.
    assert published["r-extension"] == "SCIENTIFICALLY_REVIEWED"
    # Metamorphic: a changed draft is no longer the reviewed or published version.
    package["purpose"] += " Revised."
    curator.save(package, "test-scientist")
    assert curator.proposal_states(pid)["r-supported"] == "SOURCE_SUPPORTED"


def test_supported_knowledge_needing_new_vocabulary_stays_in_the_package_unpublished(curator):
    package = compatible(curator)["package"]
    span = {
        "evidence_id": package["evidence"][0]["evidence_id"],
        "start": 0,
        "end": 3,
        "quote": "Run",
    }

    def record(rid, kind, state, status, **proposal):
        return {
            "id": rid,
            "kind": kind,
            "status": status,
            "proposal_state": state,
            "reasons": [],
            "support_spans": [span],
            "entity_id": rid,
            "proposal": proposal,
        }

    package["scientific_extraction"] = {
        "entities_by_key": {},
        "records": [
            record(
                "e-new",
                "entities",
                "PROPOSED_ONTOLOGY_EXTENSION",
                "UNRESOLVED",
                label="Beta coil",
                class_id="IgniterCoil",
                study="current",
            ),
            record(
                "s-new",
                "statements",
                "PROPOSED_ONTOLOGY_EXTENSION",
                "UNRESOLVED",
                text="Run",
                class_id="ProcedureNote",
                epistemic="documentary_context",
                subjects=[],
                study="current",
            ),
            record(
                "e-known",
                "entities",
                "SOURCE_SUPPORTED",
                "SOURCE_SUPPORTED",
                label="A9",
                class_id="ExperimentalRun",
                study="current",
            ),
        ],
    }
    curator.attach_scientific_proposals(package)
    curator.attach_scientific_proposals(package)  # idempotent
    items = {p["id"]: p for p in package["proposed_extension_items"]}
    assert set(items) == {"e-new", "s-new"}
    assert items["e-new"]["extension_proposal_id"] == "class-proposal-IgniterCoil"
    assert items["s-new"]["extension_proposal_id"] == "information_class-proposal-ProcedureNote"
    assert not any(p["included"] for p in items.values())
    # Never projected as established knowledge; the registered entity still is.
    ids = {e["id"] for e in package["entities"]}
    assert "e-known" in ids and "e-new" not in ids
    assert not any(s.get("id") == "s-new" for s in package["statements"])
