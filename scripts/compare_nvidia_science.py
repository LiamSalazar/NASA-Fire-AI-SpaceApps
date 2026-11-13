"""Matched, source-only NVIDIA diagnostics; never writes scientific knowledge.

Input is an existing service package. Receipts contain original task text and
responses, never request headers, credentials, or image data URLs.
"""

import argparse
import base64
import hashlib
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nasa_fire_ai.config import Settings
from nasa_fire_ai.llm.interfaces import NvidiaStructuredClient
from nasa_fire_ai.llm.scientific_provider import ScientificTransportError, complete_scientific

MODELS = (
    "nvidia/nemotron-3-super-120b-a12b",
    "nvidia/nemotron-3.5-super-vl-120b-a12b",
)
SYSTEM = """Interpret only supplied original NASA evidence. Return JSON with keys
entities, quantities, statements. Each is an array of objects. Entities: label,
kind, page, quote. Quantities: label, expression, unit, subject, epistemic, page,
quote. Statements: text, subject, epistemic, page, quote. Every quote must be an
exact contiguous original span. Preserve approximate values, original units,
scope and uncertainty. Separate experimental_configuration, reported_quantity,
derived_quantity, measured_observation, author_conclusion, tentative_interpretation,
planned_work. A linear fit is derived, not a direct measurement. Do not infer
causes, executed runs, or distribute group results to other groups. Recover all
scientifically meaningful content, omit diagram-symbol fragments."""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path)
    parser.add_argument("--pages", type=int, nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--models", nargs="+", default=MODELS)
    parser.add_argument("--image", type=Path)
    parser.add_argument("--timeout", type=float, default=120)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    p = json.loads(args.package.read_text())["package"]
    source = [
        {"page": e["page"], "text": e["text"]} for e in p["evidence"] if e["page"] in args.pages
    ]
    payload = json.dumps({"title": p["title"], "original_pages": source}, ensure_ascii=False)
    content = payload
    image_meta = None
    if args.image:
        data = args.image.read_bytes()
        image_meta = {
            "sha256": hashlib.sha256(data).hexdigest(),
            "bytes": len(data),
            "page": args.pages,
        }
        content = [
            {"type": "text", "text": payload},
            {
                "type": "image_url",
                "image_url": {"url": "data:image/png;base64," + base64.b64encode(data).decode()},
            },
        ]
    settings = Settings()

    def probe(model):
        path = args.output / (model.split("/")[-1] + ".json")
        if path.exists():
            return {"model": model, "cached_receipt": str(path)}
        receipt = {
            "model": model,
            "endpoint": settings.nvidia_base_url,
            "task": json.loads(payload),
            "image": image_meta,
            "system": SYSTEM,
        }
        client = NvidiaStructuredClient(settings.nvidia_api_key, settings.nvidia_base_url, model)
        try:
            r = complete_scientific(
                client,
                model=model,
                system=SYSTEM,
                payload=content,
                max_tokens=8192,
                timeout=args.timeout,
                reasoning_budget=0,
            )
            receipt.update(
                state="COMPLETED",
                content=r.content,
                finish_reason=r.finish_reason,
                usage=r.usage,
                transport=r.metadata,
            )
            try:
                receipt["parsed"] = json.loads(r.content)
            except ValueError:
                receipt["parse_failure"] = True
        except ScientificTransportError as e:
            receipt.update(state="FAILED", error=e.kind, content=e.content, transport=e.metadata)
        with path.open("x") as f:
            json.dump(receipt, f, ensure_ascii=False, indent=2)
        return {
            "model": model,
            "state": receipt["state"],
            "error": receipt.get("error"),
            "seconds": receipt["transport"]["duration_seconds"],
        }

    with ThreadPoolExecutor(max_workers=2) as pool:
        for result in pool.map(probe, args.models):
            print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
