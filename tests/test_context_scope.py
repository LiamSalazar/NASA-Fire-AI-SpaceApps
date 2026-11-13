from nasa_fire_ai.context import (
    DEFAULT_CONTEXT_POLICY,
    ContextStatement,
    ContextStatus,
    ContextualProposal,
    ScopeResolver,
    SourceLocation,
    validate_proposal,
)


def statement(sid, value, entities, status, *, exceptions=None, scope="campaign"):
    return ContextStatement(
        statement_id=sid,
        context_type="gravity",
        value=value,
        entity_ids=entities,
        evidence_ids=[sid],
        original_text=f"The experiments were conducted in {value}.",
        source_location=SourceLocation(document_id="doc", section="Methods"),
        scope=scope,
        exceptions=exceptions or [],
        validation_status=status,
    )


def test_default_microgravity_is_preference_not_fact():
    assert DEFAULT_CONTEXT_POLICY.for_query()["default_preference"] == ["microgravity"]
    assert DEFAULT_CONTEXT_POLICY.for_query(["normal-gravity"])["default_preference"] is None
    assert DEFAULT_CONTEXT_POLICY.inheritance_enabled is False


def test_context_established_once_applies_only_to_linked_runs():
    resolver = ScopeResolver()
    resolver.add(
        statement(
            "E-campaign",
            "microgravity",
            ["run-1", "run-2"],
            ContextStatus.VERIFIED_APPLICABLE_CONTEXT,
        )
    )
    assert resolver.resolve("run-1", "gravity").status == ContextStatus.VERIFIED_APPLICABLE_CONTEXT
    assert resolver.resolve("unrelated", "gravity").status == ContextStatus.UNKNOWN


def test_explicit_local_precedes_campaign_context():
    resolver = ScopeResolver(
        [
            statement(
                "E-campaign", "microgravity", ["run-1"], ContextStatus.VERIFIED_APPLICABLE_CONTEXT
            ),
            statement(
                "E-local", "normal-gravity", ["run-1"], ContextStatus.EXPLICIT_LOCAL, scope="local"
            ),
        ]
    )
    result = resolver.resolve("run-1", "gravity")
    assert result.status == ContextStatus.EXPLICIT_LOCAL
    assert result.values == ["normal-gravity"]


def test_explicit_exception_is_not_silently_inherited():
    resolver = ScopeResolver(
        [
            statement(
                "E-campaign",
                "microgravity",
                ["run-1", "run-control"],
                ContextStatus.VERIFIED_APPLICABLE_CONTEXT,
                exceptions=["run-control"],
            ),
        ]
    )
    result = resolver.resolve("run-control", "gravity")
    assert result.status == ContextStatus.NOT_APPLICABLE


def test_candidate_context_is_not_verified():
    resolver = ScopeResolver(
        [statement("E-candidate", "microgravity", ["run-1"], ContextStatus.CONTEXTUAL_CANDIDATE)]
    )
    assert resolver.resolve("run-1", "gravity").status == ContextStatus.CONTEXTUAL_CANDIDATE


def test_model_proposal_requires_verbatim_known_evidence():
    proposal = ContextualProposal(
        subject_entity="run-1",
        candidate_predicate="hasGravityCondition",
        object_value="microgravity",
        source_statement="The experiments were conducted in microgravity.",
        supporting_text="conducted in microgravity",
        context_scope="campaign",
        evidence_ids=["E1"],
    )
    assert (
        validate_proposal(
            proposal, {"E1": {"passage": "The experiments were conducted in microgravity."}}
        ).validation_status
        == "ACCEPTED_FOR_REVIEW"
    )
    assert (
        validate_proposal(proposal, {"E1": {"passage": "terrestrial control"}}).validation_status
        == "REJECTED"
    )
