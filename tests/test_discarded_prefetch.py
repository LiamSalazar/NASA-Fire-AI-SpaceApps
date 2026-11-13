"""A request sent ahead and then discarded is recorded with its usage; one never sent is not."""

from concurrent.futures import Future
from types import SimpleNamespace

from nasa_fire_ai.ingestion.document_extraction import record_discarded_prefetch
from nasa_fire_ai.llm.scientific_provider import ScientificTransportError


class Registry:
    def __init__(self):
        self.rows = []

    def set_phase3_cache(self, key, kind, payload):
        self.rows.append((kind, payload))


CALL = {"model": "claude-sonnet-5-5", "max_tokens": 8192}


def sent(result=None, error=None):
    ahead = Future()
    ahead.set_running_or_notify_cancel()
    if error is not None:
        ahead.set_exception(error)
    else:
        ahead.set_result(result)
    return ahead


def test_a_sent_and_answered_request_is_recorded_with_its_usage():
    registry = Registry()
    response = SimpleNamespace(usage={"total_tokens": 1500}, metadata={"provider": "x"})
    settled = record_discarded_prefetch(registry, "propositions", CALL, sent(response))
    assert settled == {"usage_tokens": 1500, "never_sent": False}
    ((kind, payload),) = registry.rows
    assert kind == "scientific_document_attempt" and payload["state"] == "FINISHED"
    assert payload["outcome"]["prefetch"] == "DISCARDED"
    assert payload["outcome"]["usage"]["total_tokens"] == 1500


def test_a_failed_request_sent_ahead_keeps_its_reservation():
    # It may have been billed: no usage is known, and it is not proven unsent.
    registry = Registry()
    error = ScientificTransportError("network", metadata={"provider": "x"})
    settled = record_discarded_prefetch(registry, "identity", CALL, sent(error=error))
    assert settled == {"usage_tokens": None, "never_sent": False}
    ((_kind, payload),) = registry.rows
    assert payload["outcome"]["transport"]["error_type"] == "network"


def test_a_request_proven_never_sent_releases_its_reservation():
    error = ScientificTransportError("network", metadata={"request_not_sent": True})
    settled = record_discarded_prefetch(Registry(), "identity", CALL, sent(error=error))
    assert settled["never_sent"] is True


def test_a_request_never_sent_is_cancelled_and_not_recorded():
    registry = Registry()
    assert record_discarded_prefetch(registry, "identity", CALL, Future()) is None
    assert registry.rows == []
