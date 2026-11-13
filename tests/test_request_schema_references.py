"""Every stage request schema resolves its references; a refused request frees its reservation."""

import copy
import json

import httpx
import openai
import pytest
from test_document_extraction import client_for, entity, submitted
from test_document_extraction import service as _service

from nasa_fire_ai.config import Settings
from nasa_fire_ai.ingestion.document_extraction import (
    STAGES,
    ExtractionBudget,
    Output,
    focused_schema,
    referenced_definitions,
    stage_schema,
)

service = _service


def unresolved_references(schema):
    missing, stack = [], [schema]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            ref = node.get("$ref")
            if isinstance(ref, str) and ref.rsplit("/", 1)[1] not in schema.get("$defs", {}):
                missing.append(ref)
            stack.extend(node.values())
        elif isinstance(node, list):
            stack.extend(node)
    return missing


def test_every_stage_and_focus_schema_resolves_each_reference():
    for stage, kinds in STAGES.items():
        for compact in (False, True):
            schema = stage_schema(stage, compact)
            assert unresolved_references(schema) == [], (stage, compact)
            for kind in kinds:
                focused = focused_schema(copy.deepcopy(schema), kind)
                assert unresolved_references(focused) == [], (stage, compact, kind)


def test_a_nested_proposed_term_definition_is_kept():
    # The defect this guards: Entity and Relation reference ProposedTerm one level down.
    assert "ProposedTerm" in stage_schema("identity")["$defs"]
    relations = [s for s, kinds in STAGES.items() if "relations" in kinds]
    assert relations and all("ProposedTerm" in stage_schema(s)["$defs"] for s in relations)


def test_referenced_definitions_follow_chains_and_drop_the_rest():
    definitions = {
        "A": {"properties": {"b": {"$ref": "#/$defs/B"}}},
        "B": {"anyOf": [{"$ref": "#/$defs/C"}, {"type": "null"}]},
        "C": {"type": "string"},
        "Unused": {"type": "string"},
    }
    assert set(referenced_definitions(definitions, ["A"])) == {"A", "B", "C"}
    assert set(referenced_definitions(definitions, ["C"])) == {"C"}


TEXT = (
    "II. Methods\nRun A1 used the Beta igniter coil. Run A1 was ignited by the Beta igniter coil.\n"
)


def run(service, failure, with_entity=True):
    p = submitted(service, TEXT)
    o = Output().model_dump()
    if with_entity:
        o["entities"] = [entity(p, "a1", "A1", "ExperimentalRun", "Run A1 used")]
    client = client_for(o)
    create = client.client.with_options.return_value.chat.completions.create
    respond, failed = create.side_effect, []

    def first_fails(**kwargs):
        if not failed:
            failed.append(kwargs)
            raise failure
        return respond(**kwargs)

    create.side_effect = first_fails
    result = service.prepare_scientific(
        p["id"],
        Settings(root=service.root),
        model_enabled=True,
        budget=ExtractionBudget(max_model_calls=8),
        client=client,
    )
    sent = [kwargs for _args, kwargs in create.call_args_list]
    return result["processing"], sent


def counted(processing):
    # Each window ends on one accepted attempt here, whose reservation is the one recorded.
    return sum(
        o["reserved_tokens_per_attempt"] for o in processing["outcomes"] if o.get("attempts")
    )


def test_the_requests_sent_resolve_each_reference(service):
    _processing, sent = run(service, RuntimeError("Synthetic provider failure"))
    for kwargs in sent:
        payload = json.loads(kwargs["messages"][1]["content"])
        assert unresolved_references(payload["schema"]) == []
        response_format = kwargs.get("response_format") or {}
        schema = (response_format.get("json_schema") or {}).get("schema")
        if schema:
            assert unresolved_references(schema) == []


def test_a_request_refused_before_processing_releases_its_reservation(service):
    refused = openai.BadRequestError(
        "Invalid schema",
        response=httpx.Response(400, request=httpx.Request("POST", "https://example.invalid")),
        body=None,
    )
    processing, sent = run(service, refused, with_entity=False)
    assert [o["attempts"] for o in processing["outcomes"]] == [2, 1, 1]
    assert sent[0]["response_format"]["type"] == "json_schema"
    assert sent[1]["response_format"]["type"] == "json_object"
    assert processing["tokens_consumed_or_reserved"] == counted(processing)


def test_other_failures_keep_their_reservation(service):
    # Negative: a failure that may have been processed (and billed) stays counted.
    processing, _sent = run(service, RuntimeError("Synthetic provider failure"), with_entity=False)
    assert [o["attempts"] for o in processing["outcomes"]] == [2, 1, 1]
    assert processing["tokens_consumed_or_reserved"] > counted(processing)


def test_the_brake_still_defers_a_request_it_cannot_afford(service):
    p = submitted(service, TEXT)
    o = Output().model_dump()
    o["entities"] = [entity(p, "a1", "A1", "ExperimentalRun", "Run A1 used")]
    result = service.prepare_scientific(
        p["id"],
        Settings(root=service.root),
        model_enabled=True,
        budget=ExtractionBudget(max_total_tokens=10),
        client=client_for(o),
    )
    assert {x["model"] for x in result["processing"]["outcomes"]} == {"DEFERRED_BUDGET"}


def connection_error(cause):
    error = openai.APIConnectionError(request=httpx.Request("POST", "https://example.invalid"))
    error.__cause__ = cause
    return error


def test_a_connection_that_never_opened_releases_its_reservation(service):
    # Name resolution, a refused connection or a TLS failure: httpx.ConnectError,
    # raised before the request body is sent.
    never_sent = connection_error(httpx.ConnectError("[Errno 11001] getaddrinfo failed"))
    processing, _sent = run(service, never_sent, with_entity=False)
    assert [o["attempts"] for o in processing["outcomes"]] == [2, 1, 1]
    assert processing["tokens_consumed_or_reserved"] == counted(processing)


@pytest.mark.parametrize(
    "cause", [httpx.ReadError("connection reset by peer"), httpx.RemoteProtocolError("cut")]
)
def test_a_connection_cut_after_sending_keeps_its_reservation(service, cause):
    # Negative: a reset or a protocol error after the request went out may be billed,
    # even when no response byte arrived.
    processing, _sent = run(service, connection_error(cause), with_entity=False)
    assert [o["attempts"] for o in processing["outcomes"]] == [2, 1, 1]
    assert processing["tokens_consumed_or_reserved"] > counted(processing)


def test_a_timeout_keeps_its_reservation(service):
    # Negative: a request that timed out may have been processed and billed.
    timed_out = openai.APITimeoutError(request=httpx.Request("POST", "https://example.invalid"))
    processing, _sent = run(service, timed_out, with_entity=False)
    assert [o["attempts"] for o in processing["outcomes"]] == [2, 1, 1]
    assert processing["tokens_consumed_or_reserved"] > counted(processing)


def test_only_a_connect_error_in_the_chain_proves_the_request_never_left():
    from nasa_fire_ai.llm.scientific_provider import request_never_sent

    assert request_never_sent(connection_error(httpx.ConnectError("refused")))
    assert not request_never_sent(connection_error(httpx.ReadError("reset")))
    assert not request_never_sent(connection_error(None))
