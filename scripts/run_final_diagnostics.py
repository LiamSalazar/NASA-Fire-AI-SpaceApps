"""Run the required pre-release diagnostics without overwriting prior receipts.

The report separates offline routing/composition evidence from provider-dependent
generation.  It never treats a page hit or a model score as scientific truth.
"""

import argparse
import gzip
import json
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def load_json(path):
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            return json.load(handle)
    return json.loads(path.read_text())


class StructuralEntailment:
    """Deterministic control used only for known positive/negative safeguards."""

    def check(self, premise, hypothesis):
        p, h = premise.lower(), hypothesis.lower()
        if "measures droplet diameter" in p and "measures droplet diameter" in h:
            return {"supported": True, "control": "known_positive"}
        if "may use an infrared camera" in p and "uses an infrared camera" in h:
            return {"supported": True, "control": "known_negative_modality"}
        if "pressure measurements are not reported" in p and "pressure measurements" in h:
            return {"supported": True, "control": "known_positive_absence"}
        return {"supported": False, "control": "unmatched"}


def known_proposition_controls():
    from nasa_fire_ai.services.semantic_support import verify_paraphrase

    def anchor(key, text):
        return {
            "support_id": key,
            "text": text,
            "category": "DOCUMENTARY",
            "epistemic_type": "documentary_content",
            "spans": [{"evidence_id": key, "text": text}],
            "conditions": [],
        }

    cases = [
        ("faithful_local_modality", "The apparatus measures droplet diameter.", "The apparatus measures droplet diameter.", True),
        ("certainty_upgrade", "The apparatus measures droplet diameter. A future test may use an infrared camera.", "The apparatus uses an infrared camera.", False),
        ("unrelated_absence", "The synthetic specimen did not emit an optical pulse.", "The report does not provide pressure measurements.", False),
        ("explicit_absence", "Pressure measurements are not reported for the synthetic trial.", "The report does not provide pressure measurements.", True),
        ("table_narrative", "Synthetic Trial\n" + "\n".join(str(i) for i in range(12)), "Synthetic trials showed improved optical precision.", False),
    ]
    rows = []
    for case_id, premise, hypothesis, expected in cases:
        a = anchor(case_id, premise)
        registry = SimpleNamespace(resolve=lambda eid, value=premise: {"text": value})
        verdict = verify_paraphrase(hypothesis, [a], registry, StructuralEntailment())
        rows.append({"id": case_id, "expected_supported": expected, "supported": bool(verdict.get("supported")), "errors": verdict.get("errors", [])})
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--run", type=Path, default=ROOT / "artifacts/scientific_engine_release_v1/live-holdout-v1.json.gz")
    parser.add_argument("--context", type=Path, default=ROOT / "artifacts/scientific_engine_release_v1/context-release.json")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output must be new; historical receipts are immutable")
    run = load_json(args.run)
    context = load_json(args.context)
    a1 = []
    for case in run.get("cases", []):
        trace = case.get("trace", {})
        examination = trace.get("evidence_examination", {})
        a1.append({
            "id": case.get("id"),
            "question": case.get("message"),
            "needs": trace.get("answer_plan", []),
            "retrieved": len(examination.get("available_evidence_ids", [])),
            "supplied": len(examination.get("supplied_evidence_ids", [])),
            "final_answer": case.get("response", {}).get("answer", ""),
            "rejected": len(trace.get("initial_rejections", [])) + len(trace.get("unrepaired_statements", [])),
        })
    selected = [c for c in context.get("cases", [])]
    positives = known_proposition_controls()
    report = {
        "protocol": "final-diagnostics-v1",
        "A1_automatic_context": {
            "status": "executed_from_preserved_live_receipt",
            "source_receipt": args.run.name,
            "cases": a1,
            "boundary": "Historical provider run; not a new scientific adjudication",
        },
        "A2_complete_verified_context": {
            "status": "not_executed_provider_unavailable",
            "provider_required": True,
            "automatic_context_receipt_cases": len(selected),
            "reason": "No NVIDIA/Nemotron credentials are configured in this environment; no synthetic answer was substituted.",
            "boundary": "A2 remains a release blocker until the same questions receive a provider run with source-only diagnostic context.",
        },
        "A3_known_propositions": {
            "status": "executed_structural_controls",
            "cases": positives,
            "accepted_expected": sum(r["expected_supported"] for r in positives),
            "accepted_actual": sum(r["supported"] for r in positives),
            "false_acceptances": [r["id"] for r in positives if r["supported"] and not r["expected_supported"]],
            "false_rejections": [r["id"] for r in positives if not r["supported"] and r["expected_supported"]],
            "boundary": "Deterministic source-local controls, not a precision estimate for the NLI model.",
        },
        "cause_attribution": {
            "retrieval": "Historical receipts show exact-page misses in some cases.",
            "context": "Automatic context routing supplies anchors by need and lexical/content novelty, but does not prove proposition sufficiency.",
            "generation": "Preserved live traces show relevant evidence can reach generation and still be omitted.",
            "verification": "Preserved traces show both false acceptance and false rejection risks; local controls reduce, but do not eliminate, them.",
            "composition": "Accepted-but-not-communicated statements remain observable after organization; final answer coverage is therefore measured separately.",
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"output": str(args.output), "A1": len(a1), "A2": report["A2_complete_verified_context"]["status"], "A3": report["A3_known_propositions"]["false_acceptances"]}))


if __name__ == "__main__":
    main()
