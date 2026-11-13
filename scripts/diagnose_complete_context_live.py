"""Compare preserved automatic evidence with source inspected evidence using Nemotron.

This is a diagnostic generation comparison, not a scientific acceptance score.
"""
import argparse
import gzip
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output must be new")
    from nasa_fire_ai.config import Settings
    from nasa_fire_ai.llm.conversation import NemotronConversation
    from nasa_fire_ai.llm.interfaces import ProviderFailure

    settings = Settings()
    if not settings.nvidia_api_key:
        parser.error("NVIDIA_API_KEY is not configured")
    with gzip.open(ROOT / "artifacts/scientific_engine_release_v1/live-holdout-v1.json.gz", "rt") as handle:
        run = json.load(handle)
    case = next(c for c in run["cases"] if c["id"] == "solid_shapes")
    trace = case["trace"]
    inventory = {a["support_id"]: a for a in trace["support_inventory"]}
    selected = [d["support_id"] for d in trace["evidence_examination"]["selection_decisions"] if d["reason"] == "selected_marginal_coverage"]
    # Source inspected original passages: the presentation explicitly names
    # the three fuel geometries. These locators are diagnostic inputs only.
    source_ids = ["claim-ab4bebdc602843fc", "d-d48bef4667a1", "d-dac63f2447e0", "d-66c1600b52c2"]
    provider = NemotronConversation(settings.nvidia_api_key, settings.nvidia_base_url, settings.nvidia_phase3_model)
    report = {"case_id": case["id"], "question": case["message"], "source_run": "live-holdout-v1.json.gz", "modes": {}, "boundary": "Raw Nemotron drafts only; factual claims require independent source and final composition review."}
    for mode, ids in (("automatic", selected), ("source_inspected", source_ids)):
        evidence = [inventory[i] for i in ids if i in inventory]
        payload = {"question": case["message"], "resolved_question": trace["resolved_question"], "history": [], "detail": "standard", "evidence": evidence, "information_needs": trace["evidence_examination"]["allocation_needs"], "source_directory": {}, "discovery_candidates": []}
        try:
            draft = provider.explain(payload, 1800)
            report["modes"][mode] = {"support_ids": ids, "source_passages": [{"support_id": a["support_id"], "source_id": a.get("source_id"), "spans": a["spans"]} for a in evidence], "draft": draft, "provider_receipts": list(provider.receipts)}
        except ProviderFailure as exc:
            report["modes"][mode] = {"support_ids": ids, "error_type": type(exc).__name__, "provider_receipts": list(provider.receipts)}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"case_id": case["id"], "modes": {k: {"segments": len(v.get("draft", {}).get("segments", [])), "error_type": v.get("error_type")} for k, v in report["modes"].items()}}))


if __name__ == "__main__":
    main()
