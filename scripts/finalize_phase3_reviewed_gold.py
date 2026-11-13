"""Promote user-approved Phase-3 review decisions; no model output is consulted."""

import json
from pathlib import Path

from nasa_fire_ai.evaluation.phase3 import gold_digest, write_artifact

ROOT = Path(__file__).resolve().parents[1]
source = json.loads((ROOT / "evals/phase3_query_interpreter_gold_candidate.json").read_text())
contract = {"qi28", "qi29", "qi30", "qi36", "qi38", "qi43", "qi46", "qi47"}
conversational = {"qi39", "qi40"}
context_gap = {"qi41"}
for case in source["cases"]:
    case["label_provenance"] = list(
        dict.fromkeys(case["label_provenance"] + ["USER_DOMAIN_REVIEW"])
    )
    case["review_status"] = "REVIEWED_SCORED"
    if case["id"] in contract:
        case["review_status"] = "CONTRACT_GAP"
    elif case["id"] in conversational:
        case["review_status"] = "REVIEWED_CONVERSATIONAL"
        case["context_fixture"] = {
            "current_investigation": "psi-98",
            "current_run_ids": ["psi-98-S1", "psi-98-S2"],
        }
    elif case["id"] in context_gap:
        case["review_status"] = "CONVERSATIONAL_CONTEXT_GAP"
    expected = case["expected"]
    if case["id"] in {"qi09", "qi10", "qi11", "qi34", "qi35", "qi50"}:
        expected["ambiguous_terms"] = []
        expected["clarification_required"] = False
    if case["id"] in {"qi19", "qi20", "qi21"}:
        term = {"qi19": "acrylic", "qi20": "velocity", "qi21": "flow"}[case["id"]]
        expected["materials"] = [] if case["id"] == "qi19" else expected["materials"]
        expected["unknown_terms"] = []
        expected["ambiguous_terms"] = [term]
        expected["clarification_required"] = True
    if case["id"] == "qi22":
        expected["unknown_terms"] = ["xenon"]
        expected["ambiguous_terms"] = []
    if case["id"] == "qi43":
        expected["query_mode"] = "compare"
        expected["phenomena"] = ["suppression", "extinction"]
        expected["safety_intents"] = []
    if case["id"] == "qi44":
        expected["requested_information"] = ["observations"]
    if case["id"] == "qi45":
        expected["query_mode"] = "general_search"
        expected["requested_information"] = ["conclusions"]
    if case["id"] == "qi49":
        expected["materials"] = ["PMMA"]
        expected["ambiguous_terms"] = ["acrylic"]
        expected["clarification_required"] = False
source["version"] = "reviewed-v1"
source["review_status"] = "USER_DOMAIN_REVIEWED"
source["digest"] = gold_digest(source["cases"])
write_artifact(ROOT / "evals/phase3_query_interpreter_gold_reviewed_v1.json", source)
print(source["digest"])
