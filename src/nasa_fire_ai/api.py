"""Versioned HTTP transport with independently owned read and conversation lanes."""

import asyncio
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path
from time import monotonic
from typing import Literal
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from nasa_fire_ai.query.scenario import ScenarioInput
from nasa_fire_ai.services.conversation import (
    ChatRequest,
    ChatResponse,
    ConversationService,
    public_evidence,
)

logger = logging.getLogger(__name__)


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=1, max_length=12000)
    limit: int = Field(default=12, ge=1, le=100)
    offset: int = Field(default=0, ge=0, le=100000)
    research: bool = False


class ComparisonRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    subjects: list[str] = Field(min_length=2, max_length=12)
    dimensions: list[str] = Field(default_factory=list, max_length=32)


class OntologyRouteStep(BaseModel):
    model_config = ConfigDict(extra="forbid")
    relation: str = Field(min_length=1, max_length=200)
    direction: Literal["FORWARD", "REVERSE"] = "FORWARD"


class OntologyNavigationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    start: str = Field(min_length=1, max_length=500)
    steps: list[OntologyRouteStep] = Field(min_length=1, max_length=5)
    budget: int = Field(default=128, ge=1, le=512)


def public_payload(value):
    """Transport views expose evidence IDs and source locators, not server paths."""
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    if isinstance(value, dict):
        return {
            key: public_payload(child)
            for key, child in value.items()
            if key not in {"raw_file", "relative_raw_file"}
        }
    if isinstance(value, list):
        return [public_payload(child) for child in value]
    return value


def default_service(*, readonly=False):
    from nasa_fire_ai.config import Settings
    from nasa_fire_ai.llm.conversation import NemotronConversation, SonnetConversation
    from nasa_fire_ai.services.search import ScientificSearchService
    from nasa_fire_ai.services.semantic_support import LocalEntailment

    settings = Settings()
    snapshot = Path(
        os.getenv(
            "NASA_SNAPSHOT",
            str(settings.root / "data/snapshots/hackathon-20261112-scientific-rc14"),
        )
    )
    from nasa_fire_ai.services.investigation import ResearchBudget

    search = ScientificSearchService(
        snapshot,
        settings.root,
        candidate_limit=int(os.getenv("NASA_CANDIDATE_LIMIT", "200")),
        research_budget=ResearchBudget(
            max_rounds=int(os.getenv("NASA_RESEARCH_ROUNDS", "3")),
            max_actions=int(os.getenv("NASA_RESEARCH_ACTIONS", "6")),
            max_candidates=int(os.getenv("NASA_RESEARCH_CANDIDATES", "32")),
            timeout_seconds=float(os.getenv("NASA_RESEARCH_SECONDS", "15")),
            max_model_calls=0,
        ),
    )
    from nasa_fire_ai.retrieval.semantic import NvidiaEmbeddingProvider
    from nasa_fire_ai.retrieval.snapshot_vectors import SnapshotVectors

    vector_directory = Path(
        os.getenv(
            "NASA_VECTOR_DIRECTORY",
            str(settings.root / "data/index" / (snapshot.name + "-vectors")),
        )
    )
    if (vector_directory / "documentary.metadata.json").exists() and settings.nvidia_api_key:
        search.semantic_candidates = SnapshotVectors(
            vector_directory,
            search.registry,
            search.manifest["snapshot_id"],
            NvidiaEmbeddingProvider(
                settings.nvidia_api_key,
                settings.nvidia_base_url or "https://integrate.api.nvidia.com/v1",
                settings.nvidia_embedding_model,
                retries=1,
            ),
        )
    elif os.getenv("NASA_VECTOR_REQUIRED") == "1":
        search.close()
        raise ValueError("Required vector index or NVIDIA embedding credential unavailable")
    provider = None
    if (
        not readonly
        and settings.scientific_llm_provider == "anthropic"
        and settings.anthropic_api_key
    ):
        provider = SonnetConversation(
            settings.anthropic_api_key,
            os.getenv("ANTHROPIC_SONNET_MODEL", settings.anthropic_science_model),
            timeout_seconds=float(os.getenv("NASA_PROVIDER_TIMEOUT_SECONDS", "120")),
        )
    elif not readonly and settings.scientific_llm_provider == "nvidia" and settings.nvidia_api_key:
        provider = NemotronConversation(
            settings.nvidia_api_key,
            settings.nvidia_base_url,
            settings.nvidia_phase3_model,
            timeout_seconds=float(os.getenv("NASA_PROVIDER_TIMEOUT_SECONDS", "120")),
        )
    entailment = None
    if not readonly and (directory := os.getenv("NASA_NLI_DIRECTORY")):
        try:
            entailment = LocalEntailment(Path(directory))
        except Exception:  # noqa: BLE001 - startup remains usable without verifier
            logger.warning("Semantic verifier could not be loaded")
    return ConversationService(
        search,
        provider=provider,
        entailment=entailment,
        max_repair_attempts=int(os.getenv("NASA_REPAIR_ATTEMPTS", "1")),
        source_characters=int(os.getenv("NASA_SOURCE_CHARACTERS", "60000")),
        max_alignment_checks=int(os.getenv("NASA_ALIGNMENT_CHECKS", "96")),
    )


def create_app(
    service_factory=default_service,
    *,
    read_service_factory=None,
    allowed_origins=None,
    max_body_bytes=200000,
):
    from nasa_fire_ai.services.operations import (
        Operation,
        OperationCanceled,
        current_operation,
        install_checkpoints,
    )

    workers = {
        lane: ThreadPoolExecutor(max_workers=1, thread_name_prefix="nasa-" + lane)
        for lane in ("read", "conversation")
    }
    services = {}
    locks = {lane: asyncio.Lock() for lane in workers}
    operations = {}
    conversation_limit = 8
    read_pending = 0

    def execute(action, lane, operation=None):
        if lane not in services:
            try:
                service = (
                    (
                        read_service_factory()
                        if read_service_factory
                        else default_service(readonly=True)
                    )
                    if lane == "read"
                    and (read_service_factory or service_factory is default_service)
                    else service_factory()
                )
            except Exception as exc:
                raise RuntimeError("Service initialization failed") from exc
            if lane == "conversation":
                install_checkpoints(service)
            services[lane] = service
        token = current_operation.set(operation)
        try:
            return action(services[lane])
        finally:
            current_operation.reset(token)

    async def run(action, lane="read", operation=None):
        nonlocal read_pending
        if lane == "read" and read_pending >= 16:
            raise HTTPException(503, "Source consultation queue is full; retry shortly")
        if lane == "read":
            read_pending += 1
        try:
            async with locks[lane]:
                future = asyncio.get_running_loop().run_in_executor(
                    workers[lane], execute, action, lane, operation
                )
                try:
                    return public_payload(await asyncio.shield(future))
                except asyncio.CancelledError:
                    await future
                    raise
                except LookupError:
                    raise HTTPException(404, "Resource or conversation not found") from None
                except ValueError:
                    raise HTTPException(422, "Invalid scientific request") from None
                except Exception as exc:  # noqa: BLE001 - redact HTTP errors
                    error_id = str(uuid4())
                    logger.error(
                        "Scientific request failed id=%s type=%s", error_id, type(exc).__name__
                    )
                    raise HTTPException(503, "Scientific service unavailable") from None
        finally:
            if lane == "read":
                read_pending -= 1

    def operation_view(op):
        queued = [o.id for o in operations.values() if o.status == "queued"]
        return op.view(queued.index(op.id) + 1 if op.id in queued else 0)

    async def process(op, request):
        try:
            # Acquire the conversation lane before setting running; cancellation
            # remains pending until the non-interruptible stage actually returns.
            async with conversation_slot:
                if op.cancel.is_set():
                    op.status = "canceled"
                    return
                op.status = "running"
                op.started = monotonic()
                op.result = await run(lambda svc: svc.chat(request), "conversation", op)
                op.status = "completed"
        except OperationCanceled:
            op.status = "canceled"
        except HTTPException as exc:
            op.status = "failed"
            op.error = {"status": exc.status_code, "message": str(exc.detail)}
        finally:
            op.finished = monotonic()

    conversation_slot = asyncio.Lock()

    def submit(request):
        for key, op in list(operations.items()):
            if op.finished and monotonic() - op.finished > 3600:
                del operations[key]
        active = [op for op in operations.values() if op.finished is None]
        if len(active) >= conversation_limit:
            raise HTTPException(503, "Question queue is full; please retry shortly")
        while len(operations) >= 64:
            terminal = next((key for key, op in operations.items() if op.finished), None)
            if terminal is None:
                break
            del operations[terminal]
        op = Operation()
        operations[op.id] = op
        op.status = "queued"
        op.task = asyncio.create_task(process(op, request))
        return op

    def cancel(op):
        if op.status in {"completed", "failed", "canceled"}:
            return
        op.cancel.set()
        if op.status in {"pending", "queued"}:
            op.task.cancel()
            op.status = "canceled"
            op.finished = monotonic()
        else:
            op.status = "cancellation_requested"

    @asynccontextmanager
    async def lifespan(app):
        yield
        for op in operations.values():
            cancel(op)
        await asyncio.gather(*(op.task for op in operations.values()), return_exceptions=True)
        for lane, service in services.items():
            await asyncio.get_running_loop().run_in_executor(workers[lane], service.search.close)
        for worker in workers.values():
            worker.shutdown(wait=True)

    app = FastAPI(title="NASA Fire AI", version="1.0.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins
        if allowed_origins is not None
        else [x for x in os.getenv("NASA_CORS_ORIGINS", "http://localhost:5173").split(",") if x],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @app.middleware("http")
    async def size_limit(request: Request, call_next):
        # Count streamed bytes, not just the untrusted Content-Length header.
        size = 0
        body = []
        async for chunk in request.stream():
            size += len(chunk)
            if size > max_body_bytes:
                return JSONResponse(status_code=413, content={"detail": "Request body too large"})
            body.append(chunk)
        request._body = b"".join(body)
        return await call_next(request)

    @app.get("/api/v1/health")
    async def health():
        return {
            "status": "ok",
            "loaded": bool(services),
            "schema_version": "scientific-chat-v1",
        }

    @app.get("/api/v1/capabilities")
    async def capabilities():
        return {
            "chat_contract": "scientific-chat-v1",
            "streaming": False,
            "conversation_scheduling": {"active": 1, "active_plus_queued": conversation_limit},
            "cancellation": "cooperative between stages; active calls finish safely",
            "evidence_categories": ["DIRECT", "RELATED", "DOCUMENTARY", "DISCOVERY"],
            "languages": ["en"],
            "provider_optional": True,
            "max_body_bytes": max_body_bytes,
            "max_queries": 6,
            "sessions": "process-local, bounded, expire after one hour",
            "scientific_validation": "source checks plus probabilistic independent NLI; human review required",
        }

    @app.get("/api/v1/readiness")
    async def readiness():
        def inspect(svc):
            vector = bool(svc.search.semantic_candidates)
            generation = svc.provider is not None
            verification = svc.entailment is not None
            return {
                "status": "ready",
                "snapshot_id": svc.search.manifest["snapshot_id"],
                "scientific_mode": "hybrid_conversational"
                if vector and generation and verification
                else "partial",
                "channels": {
                    "lexical": "PROVISIONED",
                    "structured": "PROVISIONED",
                    "graph": "PROVISIONED",
                    "vector": "PROVISIONED" if vector else "NOT_PROVISIONED",
                },
                "generation": "CONFIGURED" if generation else "NOT_CONFIGURED",
                "semantic_verifier": "PROVISIONED" if verification else "NOT_PROVISIONED",
                "boundary": "Asset readiness, not remote provider availability or scientific release acceptance",
            }

        return await run(inspect, "conversation")

    @app.post("/api/v1/chat/operations", status_code=202)
    async def start_chat(request: ChatRequest):
        return operation_view(submit(request))

    def find_operation(operation_id):
        if operation_id not in operations:
            raise HTTPException(404, "Question operation not found or expired")
        return operations[operation_id]

    @app.get("/api/v1/chat/operations/{operation_id}")
    async def get_operation(operation_id: UUID):
        return operation_view(find_operation(str(operation_id)))

    @app.post("/api/v1/chat/operations/{operation_id}/cancel")
    async def cancel_operation(operation_id: UUID):
        op = find_operation(str(operation_id))
        cancel(op)
        return operation_view(op)

    @app.post("/api/v1/chat", response_model=ChatResponse)
    async def chat(request: ChatRequest, http: Request):
        op = submit(request)
        try:
            while op.finished is None:
                if await http.is_disconnected():
                    cancel(op)
                    raise HTTPException(499, "Question abandoned")
                await asyncio.sleep(0.1)
            if op.status == "failed":
                raise HTTPException(op.error["status"], op.error["message"])
            if op.status == "canceled":
                raise HTTPException(409, "Question canceled")
            return op.result
        except asyncio.CancelledError:
            cancel(op)
            raise

    @app.get("/api/v1/conversations/{conversation_id}/candidates")
    async def candidates(
        conversation_id: UUID, offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100)
    ):
        return await run(lambda svc: svc.candidates(conversation_id, offset, limit), "conversation")

    @app.get("/api/v1/resolve")
    async def resolve(query: str = Query(min_length=1, max_length=500)):
        from nasa_fire_ai.services.identifier_lookup import resolve_identifier

        return await run(lambda svc: resolve_identifier(svc.search, query))

    @app.post("/api/v1/search")
    async def search(request: SearchRequest):
        return await run(lambda svc: svc.search.search(**request.model_dump()))

    @app.post("/api/v1/comparisons")
    async def comparisons(request: ComparisonRequest):
        def compare(svc):
            from nasa_fire_ai.query.native import compare_native

            if any(s not in svc.search.store.registry.entities for s in request.subjects):
                raise LookupError()
            if any(
                d not in svc.search.store.registry.properties
                and d not in svc.search.store.registry.relations
                for d in request.dimensions
            ):
                raise ValueError()
            return compare_native(svc.search.store, request.subjects, request.dimensions or None)

        return await run(compare)

    @app.post("/api/v1/scenarios")
    async def scenarios(request: ScenarioInput):
        return await run(lambda svc: svc.search.analyze_scenario(request))

    @app.get("/api/v1/catalog")
    async def catalog(offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100)):
        return await run(
            lambda svc: {
                "items": svc.search.manifest["sources"][offset : offset + limit],
                "offset": offset,
                "limit": limit,
                "total": len(svc.search.manifest["sources"]),
            }
        )

    @app.get("/api/v1/records")
    async def records(
        investigation: str,
        identifier: str | None = None,
        offset: int = Query(0, ge=0),
        limit: int = Query(20, ge=1, le=100),
    ):
        def lookup(svc):
            result = svc.search.source_records(
                investigation.lower(), identifier, offset=offset, limit=limit
            )
            for record in result["items"]:
                record["evidence"] = [public_evidence(row) for row in record["evidence"] if row]
            return result

        return await run(lookup)

    @app.get("/api/v1/ontology")
    async def ontology(offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100)):
        def items(svc):
            registry = svc.search.store.registry
            rows = [
                {"id": key, "kind": kind}
                for kind, keys in [
                    ("entity", registry.entities),
                    ("property", registry.properties),
                    ("relation", registry.relations),
                ]
                for key in sorted(keys)
            ]
            return {
                "items": rows[offset : offset + limit],
                "total": len(rows),
                "offset": offset,
                "limit": limit,
            }

        return await run(items)

    @app.post("/api/v1/ontology/navigate")
    async def ontology_navigation(request: OntologyNavigationRequest):
        def follow(svc):
            from nasa_fire_ai.query.ontology_navigation import RouteStep, navigate

            if request.start not in svc.search.store.registry.entities:
                raise LookupError(request.start)
            return navigate(
                svc.search.store,
                request.start,
                [RouteStep(step.relation, step.direction) for step in request.steps],
                svc.search.registry,
                budget=request.budget,
            )

        return await run(follow)

    @app.get("/api/v1/evidence/{evidence_id}")
    async def evidence(evidence_id: str):
        def lookup(svc):
            row = svc.search._evidence(evidence_id)
            if row is None:
                raise LookupError()
            return public_evidence(row)

        return await run(lookup)

    @app.get("/api/v1/sources/{source_id}")
    async def source(source_id: str):
        def lookup(svc):
            row = svc.search.registry.db.execute(
                "SELECT source_id,title,doi,url,source_type,nasa_id FROM sources WHERE source_id=?",
                (source_id,),
            ).fetchone()
            if row is None:
                raise LookupError()
            return dict(row)

        return await run(lookup)

    def research(svc):
        from nasa_fire_ai.services.research_console import ResearchConsole

        if not hasattr(svc, "_research_console"):
            svc._research_console = ResearchConsole(svc.search)
        return svc._research_console

    @app.get("/api/v1/research/overview")
    async def research_overview():
        return await run(lambda svc: research(svc).summary())

    @app.get("/api/v1/research/investigations")
    async def investigation_list(
        query: str = Query("", max_length=200),
        family: str | None = None,
        material: str | None = None,
        instrument: str | None = None,
        method: str | None = None,
        property_id: str | None = None,
        record_class: str | None = None,
        measurements: bool = False,
        offset: int = Query(0, ge=0, le=100000),
        limit: int = Query(20, ge=1, le=100),
    ):
        return await run(
            lambda svc: research(svc).investigations(
                query=query,
                family=family,
                material=material,
                instrument=instrument,
                method=method,
                property_id=property_id,
                record_class=record_class,
                measurements=measurements,
                offset=offset,
                limit=limit,
            )
        )

    @app.get("/api/v1/research/investigations/{investigation_id}")
    async def investigation_detail(investigation_id: str):
        return await run(lambda svc: research(svc).investigation(investigation_id))

    @app.get("/api/v1/research/entities/{entity_id}")
    async def entity_detail(entity_id: str):
        from nasa_fire_ai.services.research_console import card

        return await run(lambda svc: card(svc.search, entity_id))

    @app.get("/api/v1/research/entities/{entity_id}/neighbors")
    async def entity_neighbors(
        entity_id: str,
        offset: int = Query(0, ge=0, le=100000),
        limit: int = Query(12, ge=1, le=40),
        relation: str | None = None,
    ):
        return await run(
            lambda svc: research(svc).neighbors(
                entity_id,
                offset=offset,
                limit=limit,
                relation=relation,
            )
        )

    @app.post("/api/v1/research/investigation-comparison")
    async def investigation_comparison(request: ComparisonRequest):
        return await run(lambda svc: research(svc).compare(request.subjects, request.dimensions))

    return app


app = create_app()
