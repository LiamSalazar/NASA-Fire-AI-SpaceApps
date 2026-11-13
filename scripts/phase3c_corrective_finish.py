"""Persist final quality, composition novelty and closure checkpoint offline."""

import ast
import json
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from phase3c_corrective_live import check_freeze

from nasa_fire_ai.evaluation.phase3c import digest, freeze_json, proportion
from nasa_fire_ai.evidence import EvidenceRegistry


def load(name):
    return json.loads((ROOT / name).read_text())


def signature(intent):
    return (
        intent["operation"],
        tuple(sorted(intent["targets"])),
        tuple(sorted(x["relation"] for x in intent["entity_constraints"])),
        tuple(sorted((x["property_id"], x["operator"]) for x in intent["property_constraints"])),
        tuple(sorted(intent["requested_information"])),
        bool(intent["comparison"]),
        bool(intent["source_constraints"]),
        bool(intent["unresolved_mentions"]),
        bool(intent["ambiguities"]),
    )


def main():
    check_freeze()
    completed = ROOT / "artifacts/phase3c_corrective_benchmark_summary_v3.json"
    if (
        completed.exists()
        and load("artifacts/phase3c_progress.json")["status"]
        == "CORRECTIVE_EVALUATION_CLOSED_WITH_FAILED_READINESS_GATES"
    ):
        print(
            "Compatible closure retained. Re-run Ruff/pytest directly for fresh local checks; new benchmark versions must not overwrite immutable results."
        )
        return
    old = [
        c
        for n in ("phase3c_queryintent_v2_gold_v1.json", "phase3c_compositional_gold_v1.json")
        for c in load("evals/" + n)["cases"]
        if c.get("expected")
    ]
    known = {signature(c["expected"]) for c in old}
    new = load("evals/phase3c_corrective_compositional_gold_v1.json")["cases"]
    unseen = [c for c in new if signature(c["expected"]) not in known]
    novelty = {
        "cases": len(new),
        "template_families": 10,
        "previously_unseen_combination_cases": len(unseen),
        "previously_unseen_composition_signatures": len({signature(c["expected"]) for c in unseen}),
        "reused_individual_concepts": sorted(
            {
                x
                for c in new
                for x in [
                    *c["expected"]["targets"],
                    *c["expected"]["requested_information"],
                    *[e["entity_id"] for e in c["expected"]["entity_constraints"]],
                    *[p["property_id"] for p in c["expected"]["property_constraints"]],
                ]
            }
        ),
        "signature_definition": "Operation, target classes, relation multiset, property/operator pairs, information classes and comparison/source/unknown/ambiguity presence; ignores numeric literals and entity vocabulary substitutions.",
        "gold_digest": digest(ROOT / "evals/phase3c_corrective_compositional_gold_v1.json"),
    }
    freeze_json(ROOT / "artifacts/phase3c_corrective_compositional_novelty_v1.json", novelty)
    commands = ["uv run ruff format --check .", "uv run ruff check .", "uv run pytest -q"]
    quality = {command: {} for command in commands}
    for command in commands:
        result = subprocess.run(
            command.split(), cwd=ROOT, capture_output=True, text=True, check=False
        )
        quality[command] = {"exit_code": result.returncode, "output": result.stdout + result.stderr}
    er = EvidenceRegistry(ROOT / "data/index/evidence.sqlite")
    staging = er.db.execute(
        "SELECT source_id,evidence_id,payload_json,review_status FROM semantic_staging"
    ).fetchall()
    integrity = load("artifacts/phase3c_corrective_final_integrity_v2.json")
    quality["scientific_integrity"] = integrity
    quality["baseline_staging_provenance"] = proportion(sum(all(r) for r in staging), len(staging))
    quality["baseline_staging_policy"] = (
        "Historical holdout namespace references are not promoted to canonical scientific facts; original staging digests retained."
    )
    quality["fts_integrity_check"] = "PASS"
    try:
        er.db.execute("INSERT INTO passages_fts(passages_fts) VALUES('integrity-check')")
    except sqlite3.Error as error:
        quality["fts_integrity_check"] = type(error).__name__
    branch_hits = []
    paths = [
        "src/nasa_fire_ai/query/native.py",
        "src/nasa_fire_ai/query/native_interpreter.py",
        "src/nasa_fire_ai/query/v2.py",
        "src/nasa_fire_ai/ingestion/generic.py",
        "src/nasa_fire_ai/services/native.py",
    ]
    for name in paths:
        for node in ast.walk(ast.parse((ROOT / name).read_text())):
            if isinstance(node, (ast.If, ast.IfExp, ast.Compare)):
                target = node.test if hasattr(node, "test") else node
                for literal in ast.walk(target):
                    if (
                        isinstance(literal, ast.Constant)
                        and isinstance(literal.value, str)
                        and re.fullmatch(
                            r"(?:psi-\d+|\d{11}|qi\d+|(?:new)?comp\d+)",
                            literal.value,
                            re.IGNORECASE,
                        )
                    ):
                        branch_hits.append(
                            {"file": name, "line": node.lineno, "literal": literal.value}
                        )
    quality["source_or_evaluation_specific_native_branch_count"] = len(branch_hits)
    quality["source_or_evaluation_specific_native_branches"] = branch_hits
    quality["static_audit_scope"] = paths
    freeze_json(ROOT / "artifacts/phase3c_corrective_quality_v1.json", quality)
    final = load("artifacts/phase3c_corrective_benchmark_summary_v2.json")
    composition_summary = "artifacts/phase3c_corrective_compositional_summary_v2.json"
    if not (ROOT / composition_summary).exists():
        composition_summary = "artifacts/phase3c_corrective_compositional_summary_v1.json"
    final["novel_compositions"] = load(composition_summary)
    final["novel_composition_summary_path"] = composition_summary
    final["composition_novelty"] = novelty
    final["unmeasured_gates"] = [
        g for g in final["unmeasured_gates"] if not g.startswith("New compositional")
    ]
    final["quality_pass"] = all(v["exit_code"] == 0 for k, v in quality.items() if k in commands)
    final["final_integrity_digest"] = digest(
        ROOT / "artifacts/phase3c_corrective_final_integrity_v2.json"
    )
    freeze_json(ROOT / "artifacts/phase3c_corrective_benchmark_summary_v3.json", final)
    # Mutable checkpoint is the one explicitly allowed replacement artifact.
    progress = load("artifacts/phase3c_progress.json")
    progress["status"] = "CORRECTIVE_EVALUATION_CLOSED_WITH_FAILED_READINESS_GATES"
    progress["historical_phase3c_checkpoint"] = {
        "benchmark_progress": progress["benchmark_progress"],
        "holdout_status": progress["holdout_status"],
        "architecture_digests": progress["architecture_digests"],
        "pending_tasks": progress["pending_tasks"],
    }
    progress["pending_tasks"] = [
        "generic_genre_topic_retrieval_repair",
        "requested_information_and_qualified_operand_resolution",
        "measurement_context_selection_and_supported_unit_review",
        "independent_relevance_and_paraphrase_review",
        "meaningful_new_structured_combustion_holdout",
    ]
    corrective = progress["corrective_phase"]
    corrective["status"] = "EVALUATION_CLOSED_WITH_FAILED_READINESS_GATES"
    corrective["pending"] = progress["pending_tasks"]
    corrective["completed"].extend(
        [
            "71_live_interpreter_cases",
            "20_native_end_to_end_cases_two_versioned_passes",
            "bounded_live_synthesis",
            "metadata_selected_holdout_first_pass",
            "30_novel_compositions",
            "field_error_matrix",
            "review_packet",
            "final_quality_gates",
            "closure_decisions",
        ]
    )
    corrective["architecture_freeze"] = "artifacts/phase3c_corrective_native_freeze_v6.json"
    corrective["benchmark_summary"] = "artifacts/phase3c_corrective_benchmark_summary_v3.json"
    corrective["decisions"] = final["decisions"]
    corrective["next_action"] = (
        "Repair generic genre/topic retrieval and qualified operands; freeze a new corrective pass before re-evaluation. Phase 4 must not begin."
    )
    corrective["verification_command"] = "uv run python scripts/phase3c_corrective_finish.py"
    progress["benchmark_progress"] = {
        "corrective_summary": corrective["benchmark_summary"],
        "historical_results": "historical_phase3c_checkpoint",
    }
    progress["holdout_status"] = (
        "ONE_NEW_UNRELATED_DOCUMENT; NO_NEW_STRUCTURED_EXPERIMENTAL_HOLDOUT"
    )
    progress["architecture_digests"]["corrective_final"] = digest(
        ROOT / corrective["architecture_freeze"]
    )
    progress["evaluation_digests"]["corrective_summary"] = digest(
        ROOT / corrective["benchmark_summary"]
    )
    (ROOT / "artifacts/phase3c_progress.json").write_text(json.dumps(progress, indent=2) + "\n")
    print(
        json.dumps(
            {"quality": final["quality_pass"], "novelty": novelty, "decisions": final["decisions"]}
        )
    )


if __name__ == "__main__":
    main()
