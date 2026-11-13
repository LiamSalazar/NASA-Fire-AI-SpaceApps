"""Completeness, evidence, structure, extension approval and publication are separate.

Synthetic records; the curation part goes through the production service.
"""

from test_proposal_states import compatible, curator  # noqa: F401

from nasa_fire_ai.ingestion.proposal_states import state_dimensions


def record(state, status, reasons=(), kind="statements", **proposal):
    return {
        "id": "r",
        "kind": kind,
        "status": status,
        "proposal_state": state,
        "reasons": list(reasons),
        "proposal": proposal,
    }


SUPPORTED = record("SOURCE_SUPPORTED", "SOURCE_SUPPORTED", epistemic="measured_observation")
STAGED = record(
    "PROPOSED_ONTOLOGY_EXTENSION",
    "UNRESOLVED",
    ["UNREGISTERED_INFORMATION_CLASS"],
    epistemic="planned_activity",
    class_id="PlannedActivity",
)


def test_a_staged_complete_record_is_complete_but_never_published():
    dims = state_dimensions(STAGED, published=True)
    assert dims["completeness"] == "COMPLETE" and dims["evidence"] == "SOURCE_SUPPORTED"
    assert dims["extension"] == "STAGED"
    # The active version does not publish a term nobody approved.
    assert dims["publication"] == "NOT_AUTHORIZED"


def test_an_approved_workspace_term_lets_the_active_version_publish_the_record():
    dims = state_dimensions(STAGED, approved_terms={"PlannedActivity"}, published=True)
    assert dims["extension"] == "APPROVED_IN_WORKSPACE" and dims["publication"] == "AUTHORIZED"
    # Metamorphic: approving another term changes nothing for this one.
    other = state_dimensions(STAGED, approved_terms={"ResearchGoal"}, published=True)
    assert other["extension"] == "STAGED" and other["publication"] == "NOT_AUTHORIZED"


def test_retained_context_is_not_a_complete_extraction():
    retained = record("SOURCE_SUPPORTED", "SOURCE_SUPPORTED", epistemic="documentary_context")
    assert state_dimensions(retained)["completeness"] == "EVIDENCE_RETAINED"
    assert state_dimensions(SUPPORTED)["completeness"] == "COMPLETE"


def test_an_open_question_is_incomplete_and_unpublishable():
    held = record(
        "STRUCTURALLY_WELL_FORMED",
        "UNRESOLVED",
        ["STATEMENT_SUBJECT_APPLICABILITY_UNRESOLVED", "UNREGISTERED_INFORMATION_CLASS"],
        epistemic="stated_goal",
        class_id="ResearchGoal",
    )
    dims = state_dimensions(held, published=True)
    assert dims["completeness"] == "INCOMPLETE" and dims["evidence"] == "OPEN"
    assert dims["extension"] == "STAGED" and dims["publication"] == "NOT_AUTHORIZED"


def test_unsupported_science_and_malformed_output_are_told_apart():
    unsupported = record("REJECTED", "REJECTED", ["PLANNED_OR_COUNTERFACTUAL_IS_NOT_OBSERVATION"])
    malformed = record("REJECTED", "REJECTED", ["UNKNOWN_STATEMENT_ENDPOINT"])
    assert state_dimensions(unsupported)["evidence"] == "UNSUPPORTED"
    assert state_dimensions(unsupported)["structure"] == "VALID"
    assert state_dimensions(malformed)["structure"] == "INVALID"


def test_curation_never_reports_a_staged_extension_record_as_published(curator):  # noqa: F811
    saved = compatible(curator)
    package = saved["package"]
    entity = package["entities"][1]["id"]
    supported = {**SUPPORTED, "id": "s", "kind": "entities", "entity_id": entity}
    package["scientific_extraction"] = {"records": [STAGED, supported]}
    pid = curator.save(package, "test-scientist")["package"]["id"]
    digest = curator.get(pid)["digest"]
    db = curator.registry.db
    db.execute(
        "INSERT INTO research_approvals VALUES (?,?,?,?,?)",
        (digest, "test-scientist", "t", 1, "{}"),
    )
    db.execute("INSERT INTO research_active VALUES (?,?)", (pid, digest))
    states = curator.proposal_states(pid)
    assert states["s"] == "AUTHORIZED_PUBLISHED"
    assert states["r"] == "SCIENTIFICALLY_REVIEWED"
    dims = curator.state_dimensions(pid)
    assert dims["r"]["publication"] == "NOT_AUTHORIZED" and dims["s"]["publication"] == "AUTHORIZED"


def test_a_record_the_projection_skips_is_never_reported_published(curator):  # noqa: F811
    saved = compatible(curator)
    package = saved["package"]
    entity = package["entities"][1]["id"]
    supported = {**SUPPORTED, "id": "s", "kind": "entities", "entity_id": entity}
    package["scientific_extraction"] = {"records": [supported]}
    # Metamorphic: the same record, excluded by curation, is not published.
    package["exclusions"].append({"subject": entity, "reason": "synthetic exclusion"})
    pid = curator.save(package, "test-scientist")["package"]["id"]
    digest = curator.get(pid)["digest"]
    db = curator.registry.db
    db.execute(
        "INSERT INTO research_approvals VALUES (?,?,?,?,?)",
        (digest, "test-scientist", "t", 1, "{}"),
    )
    db.execute("INSERT INTO research_active VALUES (?,?)", (pid, digest))
    assert curator.proposal_states(pid)["s"] == "SCIENTIFICALLY_REVIEWED"
    assert curator.state_dimensions(pid)["s"]["publication"] == "NOT_AUTHORIZED"


def test_a_duplicate_or_losing_reading_is_never_complete():
    loser = {
        **SUPPORTED,
        "id": "e-cited",
        "duplicate_of": "e-current",
        "active_proposal": False,
        "proposal": {"study": "cited"},
    }
    dims = state_dimensions(loser, published=True)
    assert dims["completeness"] == "DUPLICATE" and dims["evidence"] == "OPEN"
    assert dims["publication"] == "NOT_AUTHORIZED"


def test_a_proposed_concept_is_a_staging_proposal_whatever_its_stored_state():
    concept = {
        "id": "c",
        "kind": "concepts",
        "status": "UNRESOLVED",
        "reasons": ["ONTOLOGY_EXTENSION_REVIEW"],
        "proposal": {"kind": "class", "term": "porous shield"},
    }
    old = state_dimensions(
        {**concept, "proposal_state": "STRUCTURALLY_WELL_FORMED"}, published=True
    )
    new = state_dimensions(
        {**concept, "proposal_state": "PROPOSED_ONTOLOGY_EXTENSION"},
        approved_terms={"PorousShield"},
        published=True,
    )
    assert old == new
    assert new["completeness"] == "STAGED_PROPOSAL" and new["publication"] == "NOT_AUTHORIZED"


def test_an_unreviewed_unregistered_relation_is_not_supported():
    relation = {
        "id": "r",
        "kind": "relations",
        "status": "UNRESOLVED",
        "proposal_state": "PROPOSED_ONTOLOGY_EXTENSION",
        "reasons": ["UNREGISTERED_RELATION", "RELATION_ENTAILMENT_REQUIRES_REVIEW"],
        "proposal": {"relation": "shields"},
    }
    dims = state_dimensions(relation, published=True)
    assert dims["completeness"] == "INCOMPLETE" and dims["evidence"] == "OPEN"
