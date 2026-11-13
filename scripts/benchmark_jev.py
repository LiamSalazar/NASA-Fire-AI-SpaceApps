#!/usr/bin/env python3
"""Run the read-only live Jev epistemic routing benchmark when configured."""

import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nasa_fire_ai.llm.jev import JevSettings, ask, decision_value, list_models


def rule_label(case: dict) -> str:
    text = case["passage"].lower()
    if case["local_heading"] == "document title" or len(text.split()) <= 5:
        return "NONE"
    if "turned off the flow" in text:
        return "Intervention"
    if "didn’t extinguish" in text or "didn't extinguish" in text:
        return "ReportedExperimentalObservation"
    if "additional focused tests" in text:
        return "NASAIdentifiedOpenQuestion"
    if "shall" in text and "standard" in text:
        return "Requirement"
    if "guidance" in text:
        return "Guidance"
    if "possibility" in text and "suppression" in text:
        return "SafetyImplication"
    return "NONE"


def macro_f1(gold: list[str], predicted: list[str]) -> dict:
    labels = sorted(set(gold) | set(predicted))
    per_class = {}
    for label in labels:
        tp = sum(g == label and p == label for g, p in zip(gold, predicted))
        fp = sum(g != label and p == label for g, p in zip(gold, predicted))
        fn = sum(g == label and p != label for g, p in zip(gold, predicted))
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        per_class[label] = {
            "support": sum(g == label for g in gold),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(2 * precision * recall / (precision + recall), 4)
            if precision + recall
            else 0.0,
        }
    confusion = {
        expected: {
            actual: sum(g == expected and p == actual for g, p in zip(gold, predicted))
            for actual in labels
        }
        for expected in labels
    }
    return {
        "accuracy": round(sum(g == p for g, p in zip(gold, predicted)) / len(gold), 4),
        "macro_precision": round(statistics.mean(x["precision"] for x in per_class.values()), 4),
        "macro_recall": round(statistics.mean(x["recall"] for x in per_class.values()), 4),
        "macro_f1": round(statistics.mean(x["f1"] for x in per_class.values()), 4),
        "per_class": per_class,
        "confusion_matrix": confusion,
    }


def binary_metrics(gold: list[bool], predicted: list[bool]) -> dict:
    tp = sum(g and p for g, p in zip(gold, predicted))
    fp = sum(not g and p for g, p in zip(gold, predicted))
    tn = sum(not g and not p for g, p in zip(gold, predicted))
    fn = sum(g and not p for g, p in zip(gold, predicted))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {
        "accuracy": round((tp + tn) / len(gold), 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(2 * precision * recall / (precision + recall), 4)
        if precision + recall
        else 0.0,
        "false_positive_rate": round(fp / (fp + tn), 4) if fp + tn else None,
        "false_negative_rate": round(fn / (fn + tp), 4) if fn + tp else None,
        "counts": {"tp": tp, "fp": fp, "tn": tn, "fn": fn},
    }


def main() -> None:
    settings = JevSettings()
    output_path = ROOT / "data/eda/phase15_jev_benchmark.json"
    cases = json.loads((ROOT / "evals/phase1_5_epistemic_gold.json").read_text())["cases"]
    rule = [rule_label(case) for case in cases]
    gold = [case["gold_label"] for case in cases]
    base = {"gold_cases": len(cases), "rule_baseline": macro_f1(gold, rule)}
    if not settings.api_key:
        base.update(
            {
                "status": "NOT_EXECUTED_CONFIG_MISSING",
                "reason": "TYPESAFE_API_KEY is not configured",
            }
        )
        output_path.write_text(json.dumps(base, indent=2) + "\n")
        print(json.dumps(base, indent=2))
        return
    models = list_models(settings)
    outputs, predictions, confidences, triage_scores, latencies, usages = [], [], [], [], [], []
    triage_gold, triage_predictions = [], []
    for case in cases:
        state = {
            "source_type": "NASA documentary source",
            "document_id": case["document_id"],
            "page": case["page"],
            "section": case["section"],
            "local_heading": case["local_heading"],
            "passage": case["passage"],
        }
        started = time.monotonic()
        response = ask(
            state,
            {
                "contains_candidate_claim": {
                    "type": "noul",
                    "instructions": (
                        "Does this passage explicitly contain a scientific or experimental claim suitable "
                        "for candidate extraction? Count only an actual intervention, observation, conclusion, "
                        "safety implication, normative statement, or explicit unresolved research need."
                    ),
                    "criteria": {
                        "true": "An explicit supported candidate claim is present.",
                        "false": "Title, project/theme, objective, approach, infrastructure, relevance/impact, noun phrase, or background only.",
                    },
                },
                "epistemic_type": {
                    "type": "choice",
                    "instructions": "Classify rhetorical function only; choose NONE for non-claim rhetoric and never infer science.",
                    "criteria": {
                        "Intervention": "an action explicitly performed in an experiment",
                        "ReportedExperimentalObservation": "an explicitly observed experimental event",
                        "NASAConclusion": "an explicit NASA conclusion",
                        "SafetyImplication": "an explicit operational/safety implication",
                        "Requirement": "an explicit normative requirement",
                        "Guidance": "explicit guidance",
                        "DesignCriterion": "explicit design criterion",
                        "TestCriterion": "explicit test criterion",
                        "NASAIdentifiedOpenQuestion": "explicit unresolved research need",
                        "NONE": "no supported epistemic claim",
                    },
                },
            },
            settings,
        )
        latency = time.monotonic() - started
        label, confidence = decision_value(response, "epistemic_type")
        predictions.append(label or "UNPARSEABLE")
        if confidence is not None:
            confidences.append(confidence)
        triage_answer = response.get("answers", {}).get("contains_candidate_claim", {})
        triage_score = triage_answer.get("noul") if isinstance(triage_answer, dict) else None
        triage_scores.append(triage_score)
        triage_gold.append(case["gold_label"] != "NONE")
        triage_predictions.append(bool(triage_score is not None and triage_score >= 0.5))
        if response.get("usage"):
            usages.append(response["usage"])
        latencies.append(latency)
        outputs.append(
            {
                "gold_case_id": case["gold_case_id"],
                "prediction": label,
                "confidence": confidence,
                "triage_probability": triage_score,
                "latency_seconds": round(latency, 3),
                "response": response,
            }
        )
    classification = macro_f1(gold, predictions)
    correct_confidences = [c for c, g, p in zip(confidences, gold, predictions) if g == p]
    incorrect_confidences = [c for c, g, p in zip(confidences, gold, predictions) if g != p]
    per_class = classification["per_class"]
    result = {
        **base,
        "status": "EXECUTED",
        "requested_model": settings.model,
        "models_response": models,
        "jev": classification,
        "triage": binary_metrics(triage_gold, triage_predictions),
        "api_calls": len(cases) + 1,
        "latency_seconds": {
            "median": round(statistics.median(latencies), 3),
            "max": round(max(latencies), 3),
        },
        "usage": {
            "input_tokens": sum(x.get("input_tokens", 0) for x in usages),
            "output_tokens": sum(x.get("output_tokens", 0) for x in usages),
        },
        "confidence": {
            "count": len(confidences),
            "mean": round(statistics.mean(confidences), 4) if confidences else None,
            "correct_mean": round(statistics.mean(correct_confidences), 4)
            if correct_confidences
            else None,
            "incorrect_mean": round(statistics.mean(incorrect_confidences), 4)
            if incorrect_confidences
            else None,
            "high_confidence_errors": sum(c >= 0.8 for c in incorrect_confidences),
        },
        "class_specific": {
            "open_question_false_positive_rate": round(
                1 - per_class.get("NASAIdentifiedOpenQuestion", {}).get("precision", 0), 4
            ),
            "reported_observation_false_positive_rate": round(
                1 - per_class.get("ReportedExperimentalObservation", {}).get("precision", 0), 4
            ),
            "safety_implication_precision": per_class.get("SafetyImplication", {}).get("precision"),
            "none_precision": per_class.get("NONE", {}).get("precision"),
            "none_recall": per_class.get("NONE", {}).get("recall"),
        },
        "outputs": outputs,
    }
    output_path.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "outputs"}, indent=2))


if __name__ == "__main__":
    main()
