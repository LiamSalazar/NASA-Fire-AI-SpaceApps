"""Launch the scientific API locally; optional diagnostics stay server-side."""

import argparse
import json
import os
import sys
from pathlib import Path
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Source consultation without generation, embeddings or NLI",
    )
    parser.add_argument(
        "--diagnostics",
        type=Path,
        help="New private evaluation directory; never served to the browser",
    )
    args = parser.parse_args()
    os.environ["NASA_SONNET_EVAL_ENABLED"] = "1"
    if args.offline:
        os.environ.update(
            NVIDIA_API_KEY="", ANTHROPIC_API_KEY="", OPENAI_API_KEY="", NASA_NLI_DIRECTORY=""
        )
    elif (ROOT / "data/index/models/nasa-nli/model.onnx").exists():
        os.environ.setdefault("NASA_NLI_DIRECTORY", str(ROOT / "data/index/models/nasa-nli"))
    if args.diagnostics:
        args.diagnostics.mkdir(parents=True, exist_ok=False, mode=0o700)
        if not args.offline:
            os.environ["NASA_GENERATION_ARCHIVE"] = str(args.diagnostics / "provider_archive")
    import uvicorn

    from nasa_fire_ai.api import create_app, default_service

    def factory():
        service = default_service()
        if not args.diagnostics:
            return service
        timings = {}
        for owner, method, name in [
            (service.search, "search", "retrieval_seconds"),
            (service.entailment, "check", "nli_seconds"),
        ]:
            if owner is None:
                continue
            original = getattr(owner, method)

            def measured(*a, _original=original, _name=name, **kw):
                began = monotonic()
                try:
                    return _original(*a, **kw)
                finally:
                    timings[_name] = timings.get(_name, 0) + monotonic() - began

            setattr(owner, method, measured)
        original_chat = service.chat
        turn = 0

        def chat(request):
            nonlocal turn
            timings.clear()
            began = monotonic()
            response = original_chat(request)
            trace = service.traces[response.trace_id]
            calls = trace.get("provider_calls", [])
            turn += 1
            record = {
                "request": request.model_dump(mode="json"),
                "body": response.model_dump(mode="json"),
                "chat_seconds": monotonic() - began,
                "timings": dict(timings),
                "provider_seconds": sum(c.get("latency_ms", 0) for c in calls) / 1000,
                "provider_calls": calls,
                "repair_rounds": len(trace.get("repairs", [])),
                "actual_billed_cost_usd": None,
                "cost_boundary": "Provider usage is observed, actual billed cost requires a billing receipt.",
            }
            path = args.diagnostics / f"turn-{turn:02}.json"
            path.write_text(json.dumps(record, indent=2) + "\n")
            path.chmod(0o600)
            return response

        service.chat = chat
        return service

    uvicorn.run(
        create_app(factory, read_service_factory=lambda: default_service(readonly=True)),
        host="127.0.0.1",
        port=args.port,
        log_level="warning",
    )


if __name__ == "__main__":
    main()
