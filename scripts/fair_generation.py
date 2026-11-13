"""Freeze identical pilot evidence and replay one provider explanation against it."""

import argparse
import hashlib
import json
import os
from pathlib import Path

from nasa_fire_ai.services.context_assembly import allocate_context, information_needs

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / "artifacts/scientific_engine_stabilization_v1"


def freeze(case_id):
    from nasa_fire_ai.services.search import ScientificSearchService

    case = next(
        q
        for q in json.loads((DIRECTORY / "pilot_questions.json").read_text())["questions"]
        if q["id"] == case_id
    )
    path = DIRECTORY / f"fair-package-{case_id}.json"
    if path.exists():
        raise SystemExit("Frozen package already exists")
    anchors = {}
    for provider in ("nvidia", "anthropic"):
        suffix = (
            "-attempt-2" if provider == "anthropic" and case_id == "geometry_regression" else ""
        )
        receipt = json.loads((DIRECTORY / f"{provider}-{case_id}{suffix}.json").read_text())
        for anchor in receipt["trace"]["support_inventory"]:
            anchors.setdefault(anchor["support_id"], anchor)
    search = ScientificSearchService(ROOT / "data/snapshots/hackathon-20261105-v9", ROOT)
    try:
        for anchor in anchors.values():
            for span in anchor["spans"]:
                original = search.registry.resolve(span["evidence_id"])
                if not original or " ".join(span["text"].split()) not in " ".join(
                    original["text"].split()
                ):
                    raise ValueError("Unregistered or altered pilot evidence span")
        needs = information_needs(case["question"])
        selected, allocation = allocate_context(
            list(anchors.values()), case["question"], needs, 60000
        )
        directory = {}
        for eid in {span["evidence_id"] for anchor in selected for span in anchor["spans"]}:
            source = search._evidence(eid)
            directory[eid] = {
                key: source.get(key) for key in ("source", "page", "section", "structured_location")
            }
        payload = {
            "question": case["question"],
            "resolved_question": case["question"],
            "history": [],
            "research_focus": {},
            "detail": "standard",
            "evidence": selected,
            "information_needs": allocation["allocation_needs"],
            "source_directory": directory,
            "related_differences": [],
            "comparison": None,
            "coverage_limits": [],
            "discovery_candidates": [],
        }
        record = {
            "case": case,
            "payload": payload,
            "selection": allocation,
            "source_receipts": ["nvidia", "anthropic"],
        }
        serialized = json.dumps(record, ensure_ascii=False, sort_keys=True)
        record["package_sha256"] = hashlib.sha256(serialized.encode()).hexdigest()
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2))
        print(
            json.dumps(
                {"case": case_id, "anchors": len(selected), "sha256": record["package_sha256"]}
            )
        )
    finally:
        search.close()


def run(provider_name, case_id):
    from nasa_fire_ai.api import default_service

    package = json.loads((DIRECTORY / f"fair-package-{case_id}.json").read_text())
    output = DIRECTORY / f"fair-{provider_name}-{case_id}.json"
    if output.exists():
        raise SystemExit("Saved provider response exists; do not repeat")
    service = default_service()
    if service.provider is None:
        raise RuntimeError("Selected provider is not configured")
    try:
        draft = service.provider.explain(package["payload"], 4000)
        trace = {"verification": [], "verification_stage": "draft"}
        inventory = {a["support_id"]: a for a in package["payload"]["evidence"]}
        accepted, rejected = service._accept_segments(
            draft.get("segments", []), inventory, trace, [], {}
        )
        result = {
            "case": package["case"],
            "package_sha256": package["package_sha256"],
            "provider": provider_name,
            "draft": draft,
            "accepted_paragraphs": accepted,
            "rejected": rejected,
            "verification": trace["verification"],
            "provider_calls": service.provider.receipts,
        }
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        print(
            json.dumps(
                {
                    "case": case_id,
                    "provider": provider_name,
                    "segments": len(draft.get("segments", [])),
                    "accepted": sum(v.get("supported", False) for v in trace["verification"]),
                }
            )
        )
    finally:
        service.search.close()


def replay(provider_name, case_id):
    """Recheck saved raw output after backend changes without a provider call."""
    from nasa_fire_ai.api import default_service

    package = json.loads((DIRECTORY / f"fair-package-{case_id}.json").read_text())
    original = json.loads((DIRECTORY / f"fair-{provider_name}-{case_id}.json").read_text())
    output = DIRECTORY / f"fair-replay-{provider_name}-{case_id}.json"
    if output.exists():
        raise SystemExit("Saved replay exists")
    service = default_service()
    try:
        trace = {"verification": [], "verification_stage": "draft"}
        inventory = {a["support_id"]: a for a in package["payload"]["evidence"]}
        accepted, rejected = service._accept_segments(
            original["draft"].get("segments", []), inventory, trace, [], {}
        )
        output.write_text(
            json.dumps(
                {
                    "case": package["case"],
                    "package_sha256": package["package_sha256"],
                    "original_response": f"fair-{provider_name}-{case_id}.json",
                    "accepted_paragraphs": accepted,
                    "rejected": rejected,
                    "verification": trace["verification"],
                    "provider_calls": 0,
                },
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )
        print(
            json.dumps(
                {
                    "case": case_id,
                    "provider": provider_name,
                    "accepted": sum(v.get("supported", False) for v in trace["verification"]),
                }
            )
        )
    finally:
        service.search.close()


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument(
        "action", choices=["freeze", "nvidia", "anthropic", "replay-nvidia", "replay-anthropic"]
    )
    parser.add_argument("case_id")
    args = parser.parse_args()
    if args.action == "freeze":
        freeze(args.case_id)
        return
    if args.action.startswith("replay-"):
        os.environ["NASA_NLI_DIRECTORY"] = str(ROOT / "data/index/models/nasa-nli")
        os.environ["NVIDIA_API_KEY"] = ""
        os.environ["ANTHROPIC_API_KEY"] = ""
        replay(args.action.removeprefix("replay-"), args.case_id)
        return
    os.environ["NASA_SCIENTIFIC_LLM_PROVIDER"] = args.action
    os.environ["NASA_NLI_DIRECTORY"] = str(ROOT / "data/index/models/nasa-nli")
    if args.action == "anthropic":
        os.environ["NASA_SONNET_EVAL_ENABLED"] = "1"
    run(args.action, args.case_id)


if __name__ == "__main__":
    main()
