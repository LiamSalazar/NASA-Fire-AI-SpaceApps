"""Process-local bounded conversation lifecycle and cooperative stage cancellation."""

from contextvars import ContextVar
from threading import Event
from time import monotonic
from uuid import uuid4


class OperationCanceled(BaseException):
    """Bypass scientific fallback handlers; an abandoned turn is never committed."""


current_operation = ContextVar("scientific_operation", default=None)


def checkpoint(stage=None):
    operation = current_operation.get()
    if operation is not None:
        if stage:
            operation.stage = stage
        if operation.cancel.is_set():
            raise OperationCanceled()


def guarded(method, stage):
    def call(*args, **kwargs):
        checkpoint(stage)
        result = method(*args, **kwargs)
        checkpoint()
        return result

    return call


def install_checkpoints(service):
    # These resources remain owned by the conversation thread. No model,
    # ranking, verification threshold or scientific argument is changed.
    for owner, methods, stage in (
        (service.search, ("search",), "retrieval"),
        (
            getattr(service, "provider", None),
            ("plan", "refine", "explain", "organize"),
            "generation",
        ),
        (getattr(service, "entailment", None), ("check",), "verification"),
    ):
        for name in methods:
            if owner is not None and hasattr(owner, name):
                setattr(owner, name, guarded(getattr(owner, name), stage))


class Operation:
    def __init__(self):
        self.id = str(uuid4())
        self.status = "pending"
        self.stage = "waiting"
        self.cancel = Event()
        self.created = monotonic()
        self.started = None
        self.finished = None
        self.result = None
        self.error = None
        self.task = None

    def view(self, position=0):
        now = self.finished or monotonic()
        return {
            "operation_id": self.id,
            "status": self.status,
            "stage": self.stage,
            "queue_position": position,
            "queue_seconds": (self.started or now) - self.created,
            "execution_seconds": now - self.started if self.started else 0,
            "result": self.result if self.status == "completed" else None,
            "error": self.error,
        }
