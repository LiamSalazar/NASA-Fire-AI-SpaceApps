"""Actual pinned-verifier preservation and mixed-answer controls; all synthetic."""

import argparse
import json
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nasa_fire_ai.services.conversation import ConversationService
from nasa_fire_ai.services.semantic_support import LocalEntailment, verify_paraphrase


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--nli", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output must be new")
    verifier = LocalEntailment(args.nli)
    cases = [
        (
            "faithful_order",
            "The synthetic camera recorded the specimen width over time.",
            "The specimen width over time was recorded by the synthetic camera.",
            True,
        ),
        (
            "quantity_punctuation",
            "The synthetic chamber pressure was 8-atm.",
            "The synthetic chamber pressure was 8 atm.",
            True,
        ),
        (
            "uncertainty_preserved",
            "The synthetic probe may respond differently at low pressure.",
            "At low pressure, the synthetic probe may respond differently.",
            True,
        ),
        (
            "intended_preserved",
            "The objective is to measure the synthetic specimen response.",
            "Measuring the synthetic specimen response is an objective.",
            True,
        ),
        (
            "faithful_remedy",
            "The synthetic sensor jitter was corrected by recalibration.",
            "The jitter in the synthetic sensor was corrected by recalibration.",
            True,
        ),
        (
            "number_fabricated",
            "The measured synthetic mass was 8 g.",
            "The measured synthetic mass was 9 g.",
            False,
        ),
        (
            "unit_substituted",
            "The measured synthetic mass was 8 g.",
            "The measured synthetic mass was 8 kg.",
            False,
        ),
        ("wrong_run", "Run SYN-417 used argon.", "Run SYN-418 used argon.", False),
        (
            "causal_invention",
            "The synthetic report described a correlation between pressure and response.",
            "Pressure caused the synthetic response.",
            False,
        ),
        (
            "goal_as_observation",
            "The objective is to measure the synthetic specimen response.",
            "The synthetic specimen response was measured.",
            False,
        ),
        (
            "unverified_discovery",
            "The catalogue title is Synthetic Pressure Study.",
            "The catalogue title is Synthetic Pressure Study.",
            False,
        ),
    ]
    results = []
    for name, source, text, expected in cases:
        registry = SimpleNamespace(resolve=lambda eid, original=source: {"text": original})
        a = {
            "support_id": "source",
            "text": source,
            "category": "DISCOVERY" if name == "unverified_discovery" else "DOCUMENTARY",
            "epistemic_type": "documentary_content",
            "conditions": [],
            "spans": [{"evidence_id": "source", "text": source}],
        }
        verdict = verify_paraphrase(text, [a], registry, verifier)
        results.append(
            {
                "id": name,
                "source": source,
                "statement": text,
                "synthetic": True,
                "expected": expected,
                "verdict": verdict,
                "passed": verdict["supported"] == expected,
            }
        )
    good = "The synthetic camera recorded the specimen width over time."
    unrelated = "The spare casing may be replaced later."
    registry = SimpleNamespace(resolve=lambda eid: {"text": good if eid == "good" else unrelated})
    anchors = {
        eid: {
            "support_id": eid,
            "text": text,
            "category": "DOCUMENTARY",
            "epistemic_type": "documentary_content",
            "conditions": [],
            "spans": [{"evidence_id": eid, "text": text}],
        }
        for eid, text in [("good", good), ("other", unrelated)]
    }
    service = ConversationService(
        SimpleNamespace(
            registry=registry,
            _evidence=lambda eid: {
                "evidence_id": eid,
                "text": anchors[eid]["text"],
                "source": {"source_id": eid},
            },
        ),
        entailment=verifier,
    )
    trace, citations = {"verification": []}, []
    kept, dropped = service._accept_segments(
        [
            {
                "text": good + " Pressure caused universal stability.",
                "support_ids": ["good", "other"],
            }
        ],
        anchors,
        trace,
        citations,
        {},
    )
    results.append(
        {
            "id": "mixed_answer_preservation",
            "synthetic": True,
            "accepted": kept,
            "rejected": dropped,
            "trace": trace,
            "passed": bool(kept) and "caused" not in " ".join(kept) and bool(dropped),
        }
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps({"scientific_adjudication": False, "cases": results}, indent=2) + "\n"
    )
    print(json.dumps({"passed": sum(r["passed"] for r in results), "total": len(results)}))
    if not all(r["passed"] for r in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
